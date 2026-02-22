"""Celery tasks for the Email Outreach Agent.

Provides async-safe wrappers around the email outreach agent and
individual email send operations.
"""

import asyncio

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from solarpros.agents.email_outreach.agent import EmailOutreachAgent
from solarpros.agents.email_outreach.compliance import (
    build_unsubscribe_link,
    check_compliance,
    generate_unsubscribe_token,
)
from solarpros.agents.email_outreach.personalization import get_personalizer
from solarpros.agents.email_outreach.sendgrid_client import get_sendgrid_client
from solarpros.celery_app.app import celery_app
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.email_campaign import EmailCampaign, EmailSend, EmailSequence

logger = structlog.get_logger()

RESPONSE_CLASSIFICATION_PROMPT = """\
You are a sales email response classifier. Classify the following email
response into exactly one of these categories:

- interested: The recipient expresses interest in learning more, scheduling a
  call, or getting a proposal.
- not_interested: The recipient declines, says no, or asks to stop contact.
- question: The recipient asks a question about the product, pricing, or
  process without clearly expressing interest or disinterest.
- out_of_office: The response is an automated out-of-office / vacation reply.

Response text:
{response_text}

Reply with ONLY the category name (one of: interested, not_interested,
question, out_of_office).
"""


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=5,
    default_retry_delay=120,
    name="solarpros.agents.email_outreach.tasks.send_campaign_emails",
)
def send_campaign_emails(self, campaign_id: str) -> dict:
    """Process and send all pending emails for a campaign.

    Args:
        campaign_id: UUID string of the campaign to process.

    Returns:
        Result summary dict from the agent.
    """
    try:
        agent = EmailOutreachAgent()
        result = asyncio.run(agent.run(campaign_id=campaign_id))
        return result
    except Exception as exc:
        logger.error("send_campaign_emails_failed", campaign_id=campaign_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
    name="solarpros.agents.email_outreach.tasks.send_single_email",
)
def send_single_email(self, send_id: str) -> dict:
    """Send a single pending email by its EmailSend ID.

    Args:
        send_id: UUID string of the EmailSend record.

    Returns:
        Dict with send status and message ID.
    """
    try:
        return asyncio.run(_send_single_email_async(send_id))
    except Exception as exc:
        logger.error("send_single_email_failed", send_id=send_id, error=str(exc))
        raise self.retry(exc=exc)


async def _send_single_email_async(send_id: str) -> dict:
    """Async implementation for sending a single email."""
    from datetime import UTC, datetime

    sendgrid = get_sendgrid_client()
    personalizer = get_personalizer()

    async with async_session_factory() as session:
        result = await session.execute(
            select(EmailSend)
            .options(joinedload(EmailSend.campaign))
            .where(EmailSend.id == send_id)
        )
        email_send = result.unique().scalar_one_or_none()

        if not email_send:
            return {"status": "not_found", "send_id": send_id}

        if email_send.status != "pending":
            return {"status": "already_processed", "send_id": send_id}

        # Load the sequence
        seq_result = await session.execute(
            select(EmailSequence).where(EmailSequence.id == email_send.sequence_id)
        )
        sequence = seq_result.scalar_one_or_none()
        if not sequence:
            return {"status": "sequence_not_found", "send_id": send_id}

        # Load owner and property info
        from solarpros.models.owner import Owner
        from solarpros.models.score import ProspectScore

        score_result = await session.execute(
            select(ProspectScore)
            .options(
                joinedload(ProspectScore.owner),
                joinedload(ProspectScore.property),
                joinedload(ProspectScore.solar_analysis),
            )
            .where(ProspectScore.id == email_send.prospect_score_id)
        )
        score = score_result.unique().scalar_one_or_none()

        if not score or not score.owner or not score.owner.email:
            email_send.status = "failed"
            await session.commit()
            return {"status": "no_owner_email", "send_id": send_id}

        owner = score.owner
        prop = score.property
        solar = score.solar_analysis

        context = EmailOutreachAgent._build_context(owner, prop, solar)

        # Personalize
        subject, body = await personalizer.personalize(
            sequence.subject_template,
            sequence.body_template,
            context,
        )

        # Compliance
        unsub_token = email_send.unsubscribe_token or generate_unsubscribe_token()
        unsub_link = build_unsubscribe_link(settings.app_base_url, unsub_token)
        physical_address = settings.company_physical_address

        subject = subject.replace("{{unsubscribe_link}}", unsub_link)
        body = body.replace("{{unsubscribe_link}}", unsub_link)
        body = body.replace("{{physical_address}}", physical_address)

        is_compliant, issues = check_compliance(body, unsub_token, physical_address)
        if not is_compliant:
            email_send.status = "failed"
            await session.commit()
            return {"status": "not_compliant", "issues": issues, "send_id": send_id}

        # Send
        message_id = await sendgrid.send_email(
            to_email=owner.email,
            subject=subject,
            html_body=body,
            custom_args={
                "campaign_id": str(email_send.campaign_id),
                "owner_id": str(owner.id),
                "send_id": send_id,
            },
        )

        email_send.sendgrid_message_id = message_id
        email_send.status = "sent"
        email_send.sent_at = datetime.now(UTC)
        email_send.unsubscribe_token = unsub_token
        email_send.physical_address = physical_address

        await session.commit()

    return {
        "status": "sent",
        "send_id": send_id,
        "message_id": message_id,
    }


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
    name="solarpros.agents.email_outreach.tasks.process_pending_sends",
)
def process_pending_sends(self) -> dict:
    """Beat task: find and send all pending EmailSend records whose
    scheduled time has arrived.

    Returns:
        Summary dict with counts.
    """
    try:
        return asyncio.run(_process_pending_sends_async())
    except Exception as exc:
        logger.error("process_pending_sends_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _process_pending_sends_async() -> dict:
    """Async implementation for processing pending sends."""
    from datetime import UTC, datetime

    async with async_session_factory() as session:
        result = await session.execute(
            select(EmailSend)
            .where(EmailSend.status == "pending")
            .order_by(EmailSend.created_at)
            .limit(50)
        )
        pending_sends = list(result.scalars().all())

    dispatched = 0
    for email_send in pending_sends:
        send_single_email.delay(str(email_send.id))
        dispatched += 1

    summary = {
        "pending_found": len(pending_sends),
        "dispatched": dispatched,
    }
    logger.info("pending_sends_processed", **summary)
    return summary


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=5,
    default_retry_delay=30,
    name="solarpros.agents.email_outreach.tasks.classify_response",
)
def classify_response(self, send_id: str, response_text: str) -> dict:
    """Classify an email response using Claude.

    Args:
        send_id: UUID string of the EmailSend record that received a reply.
        response_text: The text content of the reply.

    Returns:
        Dict with the classification result.
    """
    try:
        return asyncio.run(_classify_response_async(send_id, response_text))
    except Exception as exc:
        logger.error("classify_response_failed", send_id=send_id, error=str(exc))
        raise self.retry(exc=exc)


async def _classify_response_async(send_id: str, response_text: str) -> dict:
    """Async implementation for response classification."""
    from datetime import UTC, datetime

    # Classify with Claude
    if settings.use_mock_apis:
        classification = _mock_classify(response_text)
    else:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": RESPONSE_CLASSIFICATION_PROMPT.format(
                        response_text=response_text
                    ),
                }
            ],
        )
        classification = response.content[0].text.strip().lower()

    valid_types = {"interested", "not_interested", "question", "out_of_office"}
    if classification not in valid_types:
        classification = "question"  # Safe default

    # Update the EmailSend record
    async with async_session_factory() as session:
        result = await session.execute(
            select(EmailSend).where(EmailSend.id == send_id)
        )
        email_send = result.scalar_one_or_none()

        if email_send:
            email_send.response_type = classification
            email_send.replied_at = datetime.now(UTC)

            # If not interested, mark as opted out
            if classification == "not_interested":
                from solarpros.models.owner import Owner

                owner_result = await session.execute(
                    select(Owner).where(Owner.id == email_send.owner_id)
                )
                owner = owner_result.scalar_one_or_none()
                if owner:
                    owner.opted_out = True

            await session.commit()

    logger.info(
        "response_classified",
        send_id=send_id,
        classification=classification,
    )

    return {
        "send_id": send_id,
        "classification": classification,
    }


def _mock_classify(response_text: str) -> str:
    """Simple keyword-based classification for mock mode."""
    text_lower = response_text.lower()
    if any(kw in text_lower for kw in ["out of office", "vacation", "away", "auto-reply"]):
        return "out_of_office"
    if any(kw in text_lower for kw in ["not interested", "no thanks", "remove", "stop", "unsubscribe"]):
        return "not_interested"
    if any(kw in text_lower for kw in ["interested", "tell me more", "schedule", "call me", "proposal"]):
        return "interested"
    return "question"
