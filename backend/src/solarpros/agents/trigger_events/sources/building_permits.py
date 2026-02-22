"""Building permit trigger event source.

Searches city permit APIs for roof replacement, HVAC, and renovation permits.
Uses Serper.dev to search for permit records when direct API is unavailable.
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.trigger_events.sources.base import BaseTriggerSource
from solarpros.config import settings

logger = structlog.get_logger()

# Permit types and their relevance scores
PERMIT_TYPES = {
    "roof_replacement": {"keywords": ["roof", "roofing", "re-roof", "reroof"], "score": 1.0},
    "hvac_permit": {"keywords": ["hvac", "heating", "cooling", "air conditioning"], "score": 0.85},
    "renovation_permit": {"keywords": ["renovation", "remodel", "tenant improvement", "build-out"], "score": 0.75},
}


class BuildingPermitSource(BaseTriggerSource):
    """Searches for building permits via Serper.dev Google Search."""

    source_name = "city_permits"

    TIMEOUT = 15.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.serper_api_key

    async def scan(self, **kwargs) -> list[dict]:
        address = kwargs.get("address", "")
        city = kwargs.get("city", "")
        if not address or not self.api_key:
            return []

        query = f'building permit "{address}" OR "{city}" site:*.gov'

        logger.info("permit_scan_start", address=address, city=city)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self.api_key},
                    json={"q": query, "num": 10},
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                organic = data.get("organic", [])

                events = []
                for item in organic:
                    title = item.get("title", "").lower()
                    snippet = item.get("snippet", "").lower()
                    combined = f"{title} {snippet}"

                    for event_type, config in PERMIT_TYPES.items():
                        if any(kw in combined for kw in config["keywords"]):
                            events.append({
                                "event_type": event_type,
                                "title": item.get("title", ""),
                                "source": "city_permits",
                                "source_url": item.get("link", ""),
                                "event_date": None,  # Would need parsing from snippet
                                "relevance_score": config["score"],
                                "raw_data": {
                                    "title": item.get("title"),
                                    "snippet": item.get("snippet"),
                                    "link": item.get("link"),
                                },
                            })
                            break  # Only one match per search result

                return events

        except Exception as exc:
            logger.warning("permit_scan_error", address=address, error=str(exc))
            return []
