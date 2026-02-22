"""LinkedIn outreach channel — semi-automated.

Generates connection notes and InMail text for human execution.
The frontend shows a "LinkedIn actions queue" that reps work through.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from solarpros.agents.outreach.channels.base import BaseChannel

logger = structlog.get_logger()


class LinkedInChannel(BaseChannel):
    """Semi-automated LinkedIn channel — generates content for human execution."""

    channel_name = "linkedin"

    async def execute_touch(self, contact: dict, content: dict, **kwargs) -> dict:
        """Generate LinkedIn outreach content (human executes via browser).

        Parameters
        ----------
        contact : dict
            Must include: linkedin_url, full_name
        content : dict
            Must include: instructions (connection note or InMail text), context
        """
        linkedin_url = contact.get("linkedin_url")
        if not linkedin_url:
            return {"status": "skipped", "reason": "no_linkedin_url"}

        context = content.get("context", {})
        instructions = content.get("instructions", "")

        # Personalize the connection note/InMail
        personalized = instructions
        for key, value in context.items():
            personalized = personalized.replace(f"{{{{{key}}}}}", str(value))

        return {
            "status": "pending",  # Queued for human execution
            "channel": "linkedin",
            "linkedin_url": linkedin_url,
            "contact_name": contact.get("full_name", ""),
            "action_type": content.get("action_type", "connection_request"),
            "message": personalized,
            "created_at": datetime.now(UTC).isoformat(),
        }
