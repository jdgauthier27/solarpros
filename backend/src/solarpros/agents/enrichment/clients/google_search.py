"""Google Search via Serper.dev API — last-resort contact finder.

Searches Google for phone/email patterns associated with a company.
"""

from __future__ import annotations

import re

import httpx
import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient
from solarpros.config import settings

logger = structlog.get_logger()

# Regex patterns for extracting contact info from search snippets
_PHONE_PATTERN = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class GoogleSearchClient(BaseEnrichmentClient):
    """Serper.dev Google Search API client."""

    source_name = "google_search"

    BASE_URL = "https://google.serper.dev/search"
    TIMEOUT = 15.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.serper_api_key

    async def search(self, **kwargs) -> dict | None:
        """Search Google for contact information.

        Parameters
        ----------
        query : str
            Search query (e.g. "Acme Properties LLC contact phone email").

        Returns
        -------
        dict | None
            Dict with query, results list (each with extracted phone/email).
        """
        query = kwargs.get("query", "")
        if not query or not self.api_key:
            return None

        logger.info("google_search_start", query=query)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.BASE_URL,
                    headers={"X-API-KEY": self.api_key},
                    json={"q": query, "num": 5},
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                organic = data.get("organic", [])

                results = []
                for item in organic[:5]:
                    snippet = item.get("snippet", "")
                    title = item.get("title", "")
                    combined = f"{title} {snippet}"

                    phones = _PHONE_PATTERN.findall(combined)
                    emails = _EMAIL_PATTERN.findall(combined)

                    results.append({
                        "title": title,
                        "link": item.get("link", ""),
                        "snippet": snippet,
                        "extracted_phone": phones[0] if phones else None,
                        "extracted_email": emails[0] if emails else None,
                    })

                return {"query": query, "results": results}

        except httpx.TimeoutException:
            logger.warning("google_search_timeout", query=query)
            return None
        except Exception as exc:
            logger.warning("google_search_error", query=query, error=str(exc))
            return None
