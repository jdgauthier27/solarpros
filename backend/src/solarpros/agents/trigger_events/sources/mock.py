"""Mock trigger event sources for development and testing."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

import structlog

from solarpros.agents.trigger_events.sources.base import BaseTriggerSource

logger = structlog.get_logger()


class MockBuildingPermitSource(BaseTriggerSource):
    """Mock building permit source."""

    source_name = "city_permits_mock"

    async def scan(self, **kwargs) -> list[dict]:
        address = kwargs.get("address", "")
        if not address:
            return []

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(address.lower().encode()).hexdigest()[:8], 16)

        # ~40% of properties have a permit trigger
        if seed % 5 < 2:
            return []

        permit_types = [
            ("roof_replacement", "Roof replacement permit issued", 1.0),
            ("hvac_permit", "HVAC system replacement permit", 0.85),
            ("renovation_permit", "Commercial renovation permit", 0.75),
        ]
        event_type, title, score = permit_types[seed % len(permit_types)]

        # Event date: between 1 and 120 days ago
        days_ago = seed % 120 + 1
        event_date = datetime.now(UTC) - timedelta(days=days_ago)

        return [{
            "event_type": event_type,
            "title": f"{title} at {address}",
            "source": "city_permits",
            "source_url": f"https://permits.example.gov/{seed}",
            "event_date": event_date.isoformat(),
            "relevance_score": score,
            "raw_data": {"address": address, "permit_number": f"P-{seed % 100000}"},
        }]


class MockJobPostingSource(BaseTriggerSource):
    """Mock job posting source."""

    source_name = "indeed_jobs_mock"

    async def scan(self, **kwargs) -> list[dict]:
        company_name = kwargs.get("company_name", "")
        if not company_name:
            return []

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(company_name.lower().encode()).hexdigest()[:8], 16)

        # ~30% of companies have a job trigger
        if seed % 10 < 7:
            return []

        job_types = [
            ("sustainability_hire", f"{company_name} hiring Sustainability Manager", 0.95),
            ("facilities_manager_hire", f"{company_name} hiring Facilities Manager", 0.70),
            ("leadership_change", f"{company_name} hiring VP of Operations", 0.60),
        ]
        event_type, title, score = job_types[seed % len(job_types)]

        days_ago = seed % 30 + 1
        event_date = datetime.now(UTC) - timedelta(days=days_ago)

        return [{
            "event_type": event_type,
            "title": title,
            "source": "indeed_jobs",
            "source_url": f"https://indeed.com/job/{seed}",
            "event_date": event_date.isoformat(),
            "relevance_score": score,
            "raw_data": {"company": company_name, "job_id": str(seed)},
        }]


class MockNewsMonitorSource(BaseTriggerSource):
    """Mock news monitor source."""

    source_name = "google_news_mock"

    async def scan(self, **kwargs) -> list[dict]:
        company_name = kwargs.get("company_name", "")
        if not company_name:
            return []

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(f"news_{company_name}".lower().encode()).hexdigest()[:8], 16)

        # ~20% of companies have a news trigger
        if seed % 5 < 4:
            return []

        news_types = [
            ("sustainability_pledge", f"{company_name} announces carbon neutrality commitment", 0.90),
            ("leadership_change", f"{company_name} appoints new CEO", 0.60),
        ]
        event_type, title, score = news_types[seed % len(news_types)]

        days_ago = seed % 60 + 1
        event_date = datetime.now(UTC) - timedelta(days=days_ago)

        return [{
            "event_type": event_type,
            "title": title,
            "source": "google_news",
            "source_url": f"https://news.example.com/{seed}",
            "event_date": event_date.isoformat(),
            "relevance_score": score,
            "raw_data": {"company": company_name, "article_id": str(seed)},
        }]
