"""Email Outreach Agent - Phase 6.

Orchestrates personalized email campaigns for scored commercial solar
prospects. For each qualifying prospect the agent:
  1. Checks opt-out / unsubscribe status
  2. Personalizes the email template using Claude (or mock)
  3. Verifies CAN-SPAM compliance
  4. Sends via SendGrid (or mock)
  5. Persists an EmailSend record
"""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from solarpros.agents.base import BaseAgent
from solarpros.agents.email_outreach.compliance import (
    build_unsubscribe_link,
    check_compliance,
    generate_unsubscribe_token,
)
from solarpros.agents.email_outreach.personalization import get_personalizer
from solarpros.agents.email_outreach.sendgrid_client import get_sendgrid_client
from solarpros.agents.email_outreach.templates import EMAIL_SEQUENCES
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.email_campaign import EmailCampaign, EmailSend, EmailSequence
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.score import ProspectScore
from solarpros.models.solar_analysis import SolarAnalysis

logger = structlog.get_logger()


class EmailOutreachAgent(BaseAgent):
    agent_type: str = "email_outreach"

    async def execute(self, **kwargs) -> dict:
        """Run the email outreach agent.

        Kwargs:
            campaign_id: Optional UUID of an existing campaign. If not
                provided a new campaign is created.
            campaign_name: Name for a new campaign (default: auto-generated).
            tier_filter: Comma-separated tiers to target, e.g. "A,B".
            min_score: Minimum composite score to include.
            step_number: Which sequence step to send (default: 1).

        Returns:
            Result summary dict.
        """
        campaign_id = kwargs.get("campaign_id")
        campaign_name = kwargs.get("campaign_name", f"Campaign {datetime.now(UTC).isoformat()}")
        tier_filter = kwargs.get("tier_filter", "A,B")
        min_score = kwargs.get("min_score", 50.0)
        step_number = kwargs.get("step_number", 1)

        sendgrid = get_sendgrid_client()
        personalizer = get_personalizer()

        async with async_session_factory() as session:
            # Load or create campaign
            campaign = await self._get_or_create_campaign(
                session, campaign_id, campaign_name, tier_filter, min_score
            )

            # Ensure sequences exist on the campaign
            await self._ensure_sequences(session, campaign)

            # Find the sequence for the requested step
            sequence = next(
                (s for s in campaign.sequences if s.step_number == step_number), None
            )
            if not sequence:
                raise ValueError(f"No sequence found for step {step_number}")

            # Load qualifying prospects
            prospects = await self._load_prospects(
                session, tier_filter, min_score
            )

            self.log.info(
                "outreach_starting",
                campaign_id=str(campaign.id),
                step=step_number,
                prospect_count=len(prospects),
            )

            sent = 0
            skipped = 0
            failed = 0

            for score in prospects:
                owner = score.owner
                if not owner or not owner.email:
                    skipped += 1
                    continue

                # Check opt-out
                if owner.opted_out:
                    self.log.debug("prospect_opted_out", owner_id=str(owner.id))
                    skipped += 1
                    continue

                # Check if already unsubscribed via a previous send
                existing_unsub = await self._is_unsubscribed(
                    session, campaign.id, owner.id
                )
                if existing_unsub:
                    skipped += 1
                    continue

                # Build context for personalization
                prop = score.property
                solar = score.solar_analysis
                context = self._build_context(owner, prop, solar)

                try:
                    # Personalize
                    subject, body = await personalizer.personalize(
                        sequence.subject_template,
                        sequence.body_template,
                        context,
                    )

                    # Compliance
                    unsub_token = generate_unsubscribe_token()
                    unsub_link = build_unsubscribe_link(
                        settings.app_base_url, unsub_token
                    )
                    physical_address = settings.company_physical_address

                    # Replace compliance placeholders
                    subject = subject.replace("{{unsubscribe_link}}", unsub_link)
                    body = body.replace("{{unsubscribe_link}}", unsub_link)
                    body = body.replace("{{physical_address}}", physical_address)

                    is_compliant, issues = check_compliance(
                        body, unsub_token, physical_address
                    )
                    if not is_compliant:
                        self.log.warning(
                            "email_not_compliant",
                            owner_id=str(owner.id),
                            issues=issues,
                        )
                        failed += 1
                        continue

                    # Send
                    message_id = await sendgrid.send_email(
                        to_email=owner.email,
                        subject=subject,
                        html_body=body,
                        custom_args={
                            "campaign_id": str(campaign.id),
                            "owner_id": str(owner.id),
                        },
                    )

                    # Record the send
                    email_send = EmailSend(
                        campaign_id=campaign.id,
                        sequence_id=sequence.id,
                        prospect_score_id=score.id,
                        owner_id=owner.id,
                        sendgrid_message_id=message_id,
                        status="sent",
                        sent_at=datetime.now(UTC),
                        unsubscribe_token=unsub_token,
                        physical_address=physical_address,
                    )
                    session.add(email_send)
                    sent += 1

                except Exception as e:
                    self.log.error(
                        "email_send_error",
                        owner_id=str(owner.id),
                        error=str(e),
                    )
                    failed += 1

            await session.commit()

        result = {
            "campaign_id": str(campaign.id),
            "step_number": step_number,
            "items_processed": sent + skipped + failed,
            "items_sent": sent,
            "items_skipped": skipped,
            "items_failed": failed,
        }
        self.log.info("outreach_complete", **result)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_or_create_campaign(
        self,
        session,
        campaign_id: str | uuid.UUID | None,
        name: str,
        tier_filter: str,
        min_score: float,
    ) -> EmailCampaign:
        if campaign_id:
            cid = uuid.UUID(str(campaign_id)) if isinstance(campaign_id, str) else campaign_id
            result = await session.execute(
                select(EmailCampaign)
                .options(joinedload(EmailCampaign.sequences))
                .where(EmailCampaign.id == cid)
            )
            campaign = result.unique().scalar_one_or_none()
            if campaign:
                return campaign

        campaign = EmailCampaign(
            name=name,
            status="active",
            tier_filter=tier_filter,
            min_score=min_score,
        )
        session.add(campaign)
        await session.flush()
        return campaign

    async def _ensure_sequences(self, session, campaign: EmailCampaign) -> None:
        """Create email sequences on the campaign if none exist yet."""
        if campaign.sequences:
            return
        for seq_data in EMAIL_SEQUENCES:
            seq = EmailSequence(
                campaign_id=campaign.id,
                step_number=seq_data["step_number"],
                delay_days=seq_data["delay_days"],
                subject_template=seq_data["subject_template"],
                body_template=seq_data["body_template"],
            )
            session.add(seq)
        await session.flush()
        # Reload sequences
        result = await session.execute(
            select(EmailSequence)
            .where(EmailSequence.campaign_id == campaign.id)
            .order_by(EmailSequence.step_number)
        )
        campaign.sequences = list(result.scalars().all())

    async def _load_prospects(
        self,
        session,
        tier_filter: str,
        min_score: float,
    ) -> list[ProspectScore]:
        """Load scored prospects matching the tier and score filters."""
        tiers = [t.strip() for t in tier_filter.split(",")]
        query = (
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
        result = await session.execute(query)
        return list(result.unique().scalars().all())

    async def _is_unsubscribed(
        self, session, campaign_id: uuid.UUID, owner_id: uuid.UUID
    ) -> bool:
        """Check if owner has unsubscribed from this campaign."""
        result = await session.execute(
            select(EmailSend.id).where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.owner_id == owner_id,
                EmailSend.is_unsubscribed.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _build_context(
        owner: Owner,
        prop: Property | None,
        solar: SolarAnalysis | None,
    ) -> dict:
        """Build the template context dict from model instances."""
        annual_savings = ""
        system_size = ""
        payback_years = ""
        if solar:
            annual_savings = f"${solar.annual_savings:,.0f}" if solar.annual_savings else ""
            system_size = f"{solar.system_size_kw:.1f}" if solar.system_size_kw else ""
            payback_years = f"{solar.payback_years:.1f}" if solar.payback_years else ""

        contact_name = owner.officer_name or owner.owner_name_clean
        company_name = owner.sos_entity_name or owner.owner_name_clean

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
        }
