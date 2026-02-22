"""Direct mail outreach channel — semi-automated.

Generates PDF letters for A-tier economic buyers using Jinja2 templates.
Queued for print/mail fulfillment.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from solarpros.agents.outreach.channels.base import BaseChannel

logger = structlog.get_logger()


class DirectMailChannel(BaseChannel):
    """Semi-automated direct mail channel — generates letter content for printing."""

    channel_name = "direct_mail"

    async def execute_touch(self, contact: dict, content: dict, **kwargs) -> dict:
        """Generate direct mail letter content.

        Parameters
        ----------
        contact : dict
            Must include: full_name, mailing_address
        content : dict
            Must include: body_template, context
        """
        address = contact.get("mailing_address")
        if not address:
            return {"status": "skipped", "reason": "no_mailing_address"}

        context = content.get("context", {})
        template = content.get("body_template", "")

        # Personalize the letter
        personalized = template
        for key, value in context.items():
            personalized = personalized.replace(f"{{{{{key}}}}}", str(value))

        return {
            "status": "pending",  # Queued for print/mail
            "channel": "direct_mail",
            "recipient_name": contact.get("full_name", ""),
            "mailing_address": address,
            "letter_content": personalized,
            "created_at": datetime.now(UTC).isoformat(),
        }
