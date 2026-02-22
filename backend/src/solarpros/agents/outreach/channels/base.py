"""Base interface for outreach channels."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseChannel(ABC):
    """Abstract interface for outreach channels."""

    channel_name: str = "base"

    @abstractmethod
    async def execute_touch(self, contact: dict, content: dict, **kwargs) -> dict:
        """Execute a single outreach touch.

        Parameters
        ----------
        contact : dict
            Contact info (name, email, phone, linkedin_url, etc.)
        content : dict
            Content for the touch (subject, body, script, etc.)

        Returns
        -------
        dict
            Result with status, message_id (if applicable), and metadata.
        """
