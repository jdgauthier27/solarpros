"""Job posting trigger event source.

Searches for sustainability hires, facilities manager roles, and
other hiring signals that indicate readiness for solar.
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.trigger_events.sources.base import BaseTriggerSource
from solarpros.config import settings

logger = structlog.get_logger()

# Job types and their relevance scores
JOB_TYPES = {
    "sustainability_hire": {
        "keywords": ["sustainability", "environmental", "ESG", "green energy", "renewable"],
        "score": 0.95,
    },
    "facilities_manager_hire": {
        "keywords": ["facilities manager", "facilities director", "building manager", "property manager"],
        "score": 0.70,
    },
    "leadership_change": {
        "keywords": ["VP operations", "director operations", "COO", "chief operating"],
        "score": 0.60,
    },
}


class JobPostingSource(BaseTriggerSource):
    """Searches for relevant job postings via Serper.dev."""

    source_name = "indeed_jobs"

    TIMEOUT = 15.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.serper_api_key

    async def scan(self, **kwargs) -> list[dict]:
        company_name = kwargs.get("company_name", "")
        city = kwargs.get("city", "")
        if not company_name or not self.api_key:
            return []

        # Search for job postings on Indeed and LinkedIn via Google
        query = f'"{company_name}" hiring (sustainability OR facilities OR operations) site:indeed.com OR site:linkedin.com/jobs {city}'

        logger.info("job_scan_start", company_name=company_name, city=city)

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

                    for event_type, config in JOB_TYPES.items():
                        if any(kw.lower() in combined for kw in config["keywords"]):
                            events.append({
                                "event_type": event_type,
                                "title": f"Job posting: {item.get('title', '')}",
                                "source": "indeed_jobs",
                                "source_url": item.get("link", ""),
                                "event_date": None,
                                "relevance_score": config["score"],
                                "raw_data": {
                                    "title": item.get("title"),
                                    "snippet": item.get("snippet"),
                                    "link": item.get("link"),
                                },
                            })
                            break

                return events

        except Exception as exc:
            logger.warning("job_scan_error", company_name=company_name, error=str(exc))
            return []
