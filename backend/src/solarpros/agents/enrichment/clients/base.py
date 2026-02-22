"""Base interface for enrichment data source clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEnrichmentClient(ABC):
    """Abstract interface that all enrichment source clients implement."""

    source_name: str = "base"

    @abstractmethod
    async def search(self, **kwargs) -> dict | None:
        """Search for enrichment data.

        Returns a dict of enrichment results or None if not found.
        """
