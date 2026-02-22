"""Base interface for trigger event sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTriggerSource(ABC):
    """Abstract interface for trigger event data sources."""

    source_name: str = "base"

    @abstractmethod
    async def scan(self, **kwargs) -> list[dict]:
        """Scan for trigger events.

        Parameters
        ----------
        company_name : str
            Company name to search for.
        city : str
            City to narrow the search.
        address : str
            Property address.

        Returns
        -------
        list[dict]
            List of trigger event dicts with keys:
            event_type, title, source, source_url, event_date,
            relevance_score, raw_data.
        """
