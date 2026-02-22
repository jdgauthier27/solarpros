"""Multi-Channel Outreach Agent.

Replaces email-only outreach with tiered multi-channel sequences:
  A-Tier (>=75): Full multi-channel (email + LinkedIn + phone + direct mail)
  B-Tier (50-74): Email + LinkedIn + phone
  C-Tier (<50): Email only

For each prospect:
  1. Determine tier from score
  2. Load sequence for tier
  3. Select contacts by buying role for each step
  4. Execute channel-specific touches
  5. Persist OutreachTouch + OutreachSequence records
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from solarpros.agents.base import BaseAgent
from solarpros.agents.outreach.channels.direct_mail import DirectMailChannel
from solarpros.agents.outreach.channels.email import EmailChannel
from solarpros.agents.outreach.channels.linkedin import LinkedInChannel
from solarpros.agents.outreach.channels.phone import PhoneChannel
from solarpros.agents.outreach.sequence_builder import get_sequence_for_tier
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.contact import Contact
from solarpros.models.email_campaign import EmailCampaign
from solarpros.models.outreach import OutreachSequence, OutreachTouch
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.score import ProspectScore
from solarpros.models.solar_analysis import SolarAnalysis

logger = structlog.get_logger()


class OutreachAgent(BaseAgent):
    """Agent that orchestrates multi-channel outreach sequences."""

    agent_type: str = "outreach"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.channels = {
            "email": EmailChannel(),
            "linkedin": LinkedInChannel(),
            "phone": PhoneChannel(),
            "direct_mail": DirectMailChannel(),
        }

    async def execute(self, **kwargs) -> dict:
        """Execute multi-channel outreach for a campaign.

        Parameters
        ----------
        campaign_id : str
            UUID of the campaign.
        campaign_name : str
            Name for a new campaign (if campaign_id not provided).
        tier_filter : str
            Comma-separated tiers to target, e.g. "A,B".
        min_score : float
            Minimum composite score.
        step_number : int
            Which sequence step to execute (default: 1).
        """
        campaign_id = kwargs.get("campaign_id")
        campaign_name = kwargs.get("campaign_name", f"V2 Campaign {datetime.now(UTC).isoformat()}")
        tier_filter = kwargs.get("tier_filter", "A,B")
        min_score = kwargs.get("min_score", 50.0)
        step_number = kwargs.get("step_number", 1)

        async with async_session_factory() as session:
            # Get or create campaign
            campaign = await self._get_or_create_campaign(
                session, campaign_id, campaign_name
            )

            # Load prospects
            tiers = [t.strip() for t in tier_filter.split(",")]
            result = await session.execute(
                select(ProspectScore)
                .options(
                    joinedload(ProspectScore.owner),
                    joinedload(ProspectScore.property),
                    joinedload(ProspectScore.solar_analysis),
                )
                .where(
                    ProspectScore.tier.in_(tiers),
                    ProspectScore.composite_score >= min_score,
                )
                .order_by(ProspectScore.composite_score.desc())
            )
            prospects = list(result.unique().scalars().all())

            self.log.info(
                "outreach_starting",
                campaign_id=str(campaign.id),
                step=step_number,
                prospect_count=len(prospects),
            )

            total_sent = 0
            total_queued = 0
            total_skipped = 0
            total_failed = 0

            for score in prospects:
                owner = score.owner
                if not owner or owner.opted_out:
                    total_skipped += 1
                    continue

                # Load contacts for this owner
                contacts_result = await session.execute(
                    select(Contact)
                    .where(Contact.owner_id == owner.id, Contact.opted_out.is_(False))
                    .order_by(Contact.is_primary.desc())
                )
                contacts = list(contacts_result.scalars().all())

                if not contacts:
                    total_skipped += 1
                    continue

                # Get sequence for this prospect's tier
                sequence = get_sequence_for_tier(score.tier)

                # Find the step to execute
                step = None
                for s in sequence:
                    if s["step_number"] == step_number:
                        step = s
                        break

                if not step:
                    continue

                # Find target contacts by buying role
                target_roles = step.get("target_roles", [])
                target_contacts = [
                    c for c in contacts
                    if c.buying_role in target_roles
                ] or contacts[:1]  # Fallback to primary contact

                # Build context for template personalization
                context = self._build_context(owner, score.property, score.solar_analysis, score)

                # Ensure sequence record exists
                await self._ensure_outreach_sequence(session, campaign.id, step)

                # Execute touch for each target contact
                channel = self.channels.get(step["channel"])
                if not channel:
                    total_failed += 1
                    continue

                for contact in target_contacts:
                    contact_dict = {
                        "email": contact.email,
                        "phone": contact.phone,
                        "full_name": contact.full_name,
                        "job_title": contact.job_title,
                        "linkedin_url": contact.linkedin_url,
                        "buying_role": contact.buying_role,
                        "mailing_address": owner.mailing_address,
                    }
                    content = {
                        "subject_template": step.get("subject_template", ""),
                        "body_template": step.get("body_template", ""),
                        "instructions": step.get("instructions", ""),
                        "context": context,
                        "action_type": "connection_request" if step_number <= 2 else "inmail",
                    }

                    touch_result = await channel.execute_touch(
                        contact_dict, content,
                        custom_args={"campaign_id": str(campaign.id), "contact_id": str(contact.id)},
                    )

                    # Persist OutreachTouch
                    touch = OutreachTouch(
                        campaign_id=campaign.id,
                        contact_id=contact.id,
                        channel=step["channel"],
                        status=touch_result.get("status", "pending"),
                        sendgrid_message_id=touch_result.get("sendgrid_message_id"),
                        sent_at=datetime.now(UTC) if touch_result.get("status") == "sent" else None,
                        notes=touch_result.get("call_script") or touch_result.get("message") or touch_result.get("letter_content"),
                    )
                    session.add(touch)

                    if touch_result["status"] == "sent":
                        total_sent += 1
                    elif touch_result["status"] == "pending":
                        total_queued += 1
                    elif touch_result["status"] == "skipped":
                        total_skipped += 1
                    else:
                        total_failed += 1

            await session.commit()

        result = {
            "campaign_id": str(campaign.id),
            "step_number": step_number,
            "items_processed": total_sent + total_queued + total_skipped + total_failed,
            "items_sent": total_sent,
            "items_queued": total_queued,
            "items_skipped": total_skipped,
            "items_failed": total_failed,
        }
        self.log.info("outreach_complete", **result)
        return result

    async def _get_or_create_campaign(
        self, session, campaign_id: str | uuid.UUID | None, name: str
    ) -> EmailCampaign:
        if campaign_id:
            cid = uuid.UUID(str(campaign_id)) if isinstance(campaign_id, str) else campaign_id
            result = await session.execute(
                select(EmailCampaign).where(EmailCampaign.id == cid)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                return campaign

        campaign = EmailCampaign(name=name, status="active")
        session.add(campaign)
        await session.flush()
        return campaign

    async def _ensure_outreach_sequence(
        self, session, campaign_id: uuid.UUID, step: dict
    ) -> None:
        """Create OutreachSequence record if it doesn't exist."""
        result = await session.execute(
            select(OutreachSequence).where(
                OutreachSequence.campaign_id == campaign_id,
                OutreachSequence.step_number == step["step_number"],
                OutreachSequence.channel == step["channel"],
            )
        )
        if result.scalar_one_or_none():
            return

        seq = OutreachSequence(
            campaign_id=campaign_id,
            step_number=step["step_number"],
            channel=step["channel"],
            delay_days=step.get("delay_days", 0),
            subject_template=step.get("subject_template"),
            body_template=step.get("body_template"),
            instructions=step.get("instructions"),
        )
        session.add(seq)
        await session.flush()

    @staticmethod
    def _build_context(
        owner: Owner,
        prop: Property | None,
        solar: SolarAnalysis | None,
        score: ProspectScore | None,
    ) -> dict:
        """Build the template context dict from model instances."""
        annual_savings = ""
        system_size = ""
        payback_years = ""
        if solar:
            annual_savings = f"{solar.annual_savings:,.0f}" if solar.annual_savings else ""
            system_size = f"{solar.system_size_kw:.1f}" if solar.system_size_kw else ""
            payback_years = f"{solar.payback_years:.1f}" if solar.payback_years else ""

        contact_name = owner.officer_name or owner.owner_name_clean
        company_name = owner.sos_entity_name or owner.owner_name_clean

        # Include trigger event info if available
        trigger_event = ""
        if score and score.trigger_event_score > 0:
            trigger_event = (
                "<p><em>We also noticed recent activity suggesting your property "
                "may be well-timed for solar — let us show you the numbers.</em></p>"
            )

        return {
            "company_name": company_name,
            "contact_name": contact_name,
            "annual_savings": annual_savings,
            "system_size": system_size,
            "payback_years": payback_years,
            "county": prop.county if prop else "",
            "building_type": prop.building_type or "commercial" if prop else "commercial",
            "entity_type": owner.entity_type or "",
            "roof_sqft": f"{prop.roof_sqft:,.0f}" if prop and prop.roof_sqft else "",
            "trigger_event": trigger_event,
            "buying_role": "",
        }
