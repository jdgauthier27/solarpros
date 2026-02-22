"""SendGrid webhook event handler.

Processes SendGrid Event Webhook payloads to update EmailSend records
with delivery, engagement, and compliance events.
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import async_session_factory
from solarpros.models.email_campaign import EmailSend

logger = structlog.get_logger()

# Map SendGrid event types to the handler behaviour
EVENT_TYPE_MAP = {
    "delivered": "delivered",
    "open": "open",
    "click": "click",
    "bounce": "bounce",
    "spamreport": "spamreport",
    "unsubscribe": "unsubscribe",
}


async def process_events(events: list[dict]) -> dict:
    """Process a batch of SendGrid webhook events.

    Each event dict should contain at minimum:
        - event: the event type (delivered, open, click, bounce, etc.)
        - sg_message_id: the SendGrid message ID

    Args:
        events: List of event dicts from the SendGrid webhook payload.

    Returns:
        Summary dict with counts per event type and total processed.
    """
    summary: dict[str, int] = {
        "total": 0,
        "delivered": 0,
        "open": 0,
        "click": 0,
        "bounce": 0,
        "spamreport": 0,
        "unsubscribe": 0,
        "skipped": 0,
        "not_found": 0,
    }

    async with async_session_factory() as session:
        for event in events:
            event_type = event.get("event", "").lower()
            sg_message_id = event.get("sg_message_id", "")

            if not sg_message_id:
                summary["skipped"] += 1
                continue

            # SendGrid message IDs in events sometimes include a filter suffix
            # e.g. "abc123.filter0001" - strip it
            base_message_id = sg_message_id.split(".")[0] if "." in sg_message_id else sg_message_id

            if event_type not in EVENT_TYPE_MAP:
                summary["skipped"] += 1
                logger.debug("unknown_event_type", event_type=event_type)
                continue

            email_send = await _find_email_send(session, base_message_id)
            if not email_send:
                summary["not_found"] += 1
                logger.warning(
                    "email_send_not_found",
                    sg_message_id=base_message_id,
                    event_type=event_type,
                )
                continue

            timestamp = _event_timestamp(event)

            await _apply_event(session, email_send, event_type, timestamp)

            summary[event_type] += 1
            summary["total"] += 1

            logger.info(
                "webhook_event_processed",
                event_type=event_type,
                sg_message_id=base_message_id,
                email_send_id=str(email_send.id),
            )

        await session.commit()

    return summary


async def _find_email_send(
    session: AsyncSession, sg_message_id: str
) -> EmailSend | None:
    """Look up an EmailSend by its SendGrid message ID."""
    result = await session.execute(
        select(EmailSend).where(EmailSend.sendgrid_message_id == sg_message_id)
    )
    return result.scalar_one_or_none()


async def _apply_event(
    session: AsyncSession,
    email_send: EmailSend,
    event_type: str,
    timestamp: datetime,
) -> None:
    """Apply a webhook event to an EmailSend record."""
    if event_type == "delivered":
        email_send.status = "delivered"
        if not email_send.delivered_at:
            email_send.delivered_at = timestamp

    elif event_type == "open":
        email_send.open_count += 1
        if not email_send.opened_at:
            email_send.opened_at = timestamp

    elif event_type == "click":
        email_send.click_count += 1
        if not email_send.clicked_at:
            email_send.clicked_at = timestamp

    elif event_type == "bounce":
        email_send.status = "bounced"

    elif event_type == "spamreport":
        email_send.is_unsubscribed = True
        email_send.status = "bounced"

    elif event_type == "unsubscribe":
        email_send.is_unsubscribed = True

    await session.flush()


def _event_timestamp(event: dict) -> datetime:
    """Extract a UTC datetime from a SendGrid event's timestamp field."""
    ts = event.get("timestamp")
    if ts is not None:
        try:
            return datetime.fromtimestamp(int(ts), tz=UTC)
        except (ValueError, TypeError, OSError):
            pass
    return datetime.now(UTC)
