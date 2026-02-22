"""Email outreach channel — reuses existing SendGrid + personalization logic."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from solarpros.agents.email_outreach.compliance import (
    build_unsubscribe_link,
    check_compliance,
    generate_unsubscribe_token,
)
from solarpros.agents.email_outreach.personalization import get_personalizer
from solarpros.agents.email_outreach.sendgrid_client import get_sendgrid_client
from solarpros.agents.outreach.channels.base import BaseChannel
from solarpros.config import settings

logger = structlog.get_logger()


class EmailChannel(BaseChannel):
    """Fully automated email channel via SendGrid."""

    channel_name = "email"

    def __init__(self) -> None:
        self.sendgrid = get_sendgrid_client()
        self.personalizer = get_personalizer()

    async def execute_touch(self, contact: dict, content: dict, **kwargs) -> dict:
        """Send a personalized email to a contact.

        Parameters
        ----------
        contact : dict
            Must include: email, full_name, company_name
        content : dict
            Must include: subject_template, body_template, context
        """
        email = contact.get("email")
        if not email:
            return {"status": "skipped", "reason": "no_email"}

        context = content.get("context", {})

        try:
            # Personalize
            subject, body = await self.personalizer.personalize(
                content["subject_template"],
                content["body_template"],
                context,
            )

            # CAN-SPAM compliance
            unsub_token = generate_unsubscribe_token()
            unsub_link = build_unsubscribe_link(settings.app_base_url, unsub_token)
            physical_address = settings.company_physical_address

            subject = subject.replace("{{unsubscribe_link}}", unsub_link)
            body = body.replace("{{unsubscribe_link}}", unsub_link)
            body = body.replace("{{physical_address}}", physical_address)

            is_compliant, issues = check_compliance(body, unsub_token, physical_address)
            if not is_compliant:
                return {"status": "failed", "reason": f"compliance: {issues}"}

            # Send
            message_id = await self.sendgrid.send_email(
                to_email=email,
                subject=subject,
                html_body=body,
                custom_args=kwargs.get("custom_args", {}),
            )

            return {
                "status": "sent",
                "sendgrid_message_id": message_id,
                "sent_at": datetime.now(UTC).isoformat(),
                "unsubscribe_token": unsub_token,
            }

        except Exception as exc:
            logger.error("email_channel_error", email=email, error=str(exc))
            return {"status": "failed", "reason": str(exc)}
