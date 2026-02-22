"""Phone outreach channel — semi-automated.

Generates personalized call scripts with solar data + trigger events.
The frontend shows a "call list" with scripts. Outcomes logged manually.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from solarpros.agents.outreach.channels.base import BaseChannel

logger = structlog.get_logger()


class PhoneChannel(BaseChannel):
    """Semi-automated phone channel — generates call scripts for human execution."""

    channel_name = "phone"

    async def execute_touch(self, contact: dict, content: dict, **kwargs) -> dict:
        """Generate a personalized call script.

        Parameters
        ----------
        contact : dict
            Must include: phone, full_name, job_title
        content : dict
            Must include: instructions (call script template), context
        """
        phone = contact.get("phone")
        if not phone:
            return {"status": "skipped", "reason": "no_phone"}

        context = content.get("context", {})
        script = content.get("instructions", "")

        # Personalize the call script
        personalized = script
        for key, value in context.items():
            personalized = personalized.replace(f"{{{{{key}}}}}", str(value))

        return {
            "status": "pending",  # Queued for human execution
            "channel": "phone",
            "phone": phone,
            "contact_name": contact.get("full_name", ""),
            "job_title": contact.get("job_title", ""),
            "call_script": personalized,
            "created_at": datetime.now(UTC).isoformat(),
        }
