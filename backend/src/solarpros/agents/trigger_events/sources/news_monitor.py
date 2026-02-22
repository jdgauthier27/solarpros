"""News monitoring trigger event source.

Searches Google News for sustainability pledges, leadership changes,
and other news signals relevant to solar adoption.
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.trigger_events.sources.base import BaseTriggerSource
from solarpros.config import settings

logger = structlog.get_logger()

# News event types and relevance
NEWS_TYPES = {
    "sustainability_pledge": {
        "keywords": ["sustainability", "carbon neutral", "net zero", "renewable energy", "solar", "green building"],
        "score": 0.90,
    },
    "leadership_change": {
        "keywords": ["new CEO", "new president", "appointed", "named", "promoted to"],
        "score": 0.60,
    },
    "expansion": {
        "keywords": ["expansion", "new location", "new facility", "relocating", "growing"],
        "score": 0.50,
    },
}


class NewsMonitorSource(BaseTriggerSource):
    """Searches Google News for company-related trigger events."""

    source_name = "google_news"

    TIMEOUT = 15.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.serper_api_key

    async def scan(self, **kwargs) -> list[dict]:
        company_name = kwargs.get("company_name", "")
        if not company_name or not self.api_key:
            return []

        query = f'"{company_name}" (sustainability OR "net zero" OR solar OR expansion OR "new CEO" OR appointed)'

        logger.info("news_scan_start", company_name=company_name)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    "https://google.serper.dev/news",
                    headers={"X-API-KEY": self.api_key},
                    json={"q": query, "num": 10},
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                news = data.get("news", [])

                events = []
                for item in news:
                    title = item.get("title", "").lower()
                    snippet = item.get("snippet", "").lower()
                    combined = f"{title} {snippet}"

                    for event_type, config in NEWS_TYPES.items():
                        if any(kw.lower() in combined for kw in config["keywords"]):
                            events.append({
                                "event_type": event_type,
                                "title": item.get("title", ""),
                                "source": "google_news",
                                "source_url": item.get("link", ""),
                                "event_date": None,  # Would parse item.get("date")
                                "relevance_score": config["score"],
                                "raw_data": {
                                    "title": item.get("title"),
                                    "snippet": item.get("snippet"),
                                    "link": item.get("link"),
                                    "date": item.get("date"),
                                    "source": item.get("source"),
                                },
                            })
                            break

                return events

        except Exception as exc:
            logger.warning("news_scan_error", company_name=company_name, error=str(exc))
            return []
