"""Trigger Event Monitoring Agent.

Scans for timing signals indicating a property is ready for solar:
  - Building permits (roof replacement, HVAC, renovation)
  - Job postings (sustainability hires, facilities managers)
  - News (sustainability pledges, leadership changes)

Events are scored with recency decay: full value within 30 days,
linear decay to 0 over 180 days.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Sequence

import structlog
from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.agents.trigger_events.sources.base import BaseTriggerSource
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.trigger_event import TriggerEvent

logger = structlog.get_logger()

# Recency decay parameters
FULL_VALUE_DAYS = 30
DECAY_PERIOD_DAYS = 180


def compute_recency_decay(event_date: datetime | None) -> float:
    """Compute recency decay factor (0.0-1.0) for a trigger event.

    Events within FULL_VALUE_DAYS get full value (1.0).
    Linear decay to 0.0 over DECAY_PERIOD_DAYS.
    """
    if event_date is None:
        return 0.5  # Unknown date gets moderate value

    now = datetime.now(UTC)
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=UTC)

    age_days = (now - event_date).days

    if age_days <= FULL_VALUE_DAYS:
        return 1.0
    if age_days >= DECAY_PERIOD_DAYS:
        return 0.0

    # Linear decay between FULL_VALUE_DAYS and DECAY_PERIOD_DAYS
    remaining = DECAY_PERIOD_DAYS - FULL_VALUE_DAYS
    elapsed = age_days - FULL_VALUE_DAYS
    return max(0.0, 1.0 - (elapsed / remaining))


# Base scores for each event type (before recency decay)
EVENT_BASE_SCORES: dict[str, float] = {
    "roof_replacement": 100.0,
    "hvac_permit": 85.0,
    "renovation_permit": 75.0,
    "sustainability_hire": 95.0,
    "facilities_manager_hire": 70.0,
    "leadership_change": 60.0,
    "sustainability_pledge": 90.0,
    "expansion": 50.0,
}


class TriggerEventAgent(BaseAgent):
    """Agent that scans for trigger events for a property."""

    agent_type: str = "trigger_events"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sources = self._build_sources()

    def _build_sources(self) -> list[BaseTriggerSource]:
        """Build trigger event sources (real or mock)."""
        if settings.triggers_use_mock:
            from solarpros.agents.trigger_events.sources.mock import (
                MockBuildingPermitSource,
                MockJobPostingSource,
                MockNewsMonitorSource,
            )
            return [
                MockBuildingPermitSource(),
                MockJobPostingSource(),
                MockNewsMonitorSource(),
            ]
        else:
            from solarpros.agents.trigger_events.sources.building_permits import BuildingPermitSource
            from solarpros.agents.trigger_events.sources.job_postings import JobPostingSource
            from solarpros.agents.trigger_events.sources.news_monitor import NewsMonitorSource
            return [
                BuildingPermitSource(),
                JobPostingSource(),
                NewsMonitorSource(),
            ]

    async def execute(self, **kwargs) -> dict:
        """Scan for trigger events for a single property.

        Parameters
        ----------
        property_id : str
            UUID of the property to scan.
        """
        property_id = kwargs.get("property_id")
        if not property_id:
            raise ValueError("property_id is required")

        property_uuid = uuid.UUID(str(property_id))
        self.log.info("trigger_scan_start", property_id=str(property_uuid))

        # Load property and owner
        async with async_session_factory() as session:
            result = await session.execute(
                select(Property).where(Property.id == property_uuid)
            )
            prop = result.scalar_one_or_none()

            if not prop:
                raise ValueError(f"Property {property_uuid} not found")

            result = await session.execute(
                select(Owner)
                .where(Owner.property_id == property_uuid, Owner.opted_out.is_(False))
                .limit(1)
            )
            owner = result.scalar_one_or_none()

        company_name = ""
        if owner:
            company_name = owner.sos_entity_name or owner.owner_name_clean

        # Scan all sources
        all_events: list[dict] = []
        for source in self.sources:
            try:
                events = await source.scan(
                    company_name=company_name,
                    city=prop.city or "",
                    address=prop.address or "",
                )
                all_events.extend(events)
            except Exception as exc:
                logger.warning(
                    "trigger_source_error",
                    source=source.source_name,
                    property_id=str(property_uuid),
                    error=str(exc),
                )

        # Persist trigger events
        saved_count = 0
        async with async_session_factory() as session:
            for event_data in all_events:
                event_date = None
                if event_data.get("event_date"):
                    if isinstance(event_data["event_date"], str):
                        try:
                            event_date = datetime.fromisoformat(event_data["event_date"])
                        except ValueError:
                            event_date = None
                    elif isinstance(event_data["event_date"], datetime):
                        event_date = event_data["event_date"]

                trigger = TriggerEvent(
                    property_id=property_uuid,
                    owner_id=owner.id if owner else None,
                    event_type=event_data["event_type"],
                    title=event_data["title"],
                    source=event_data["source"],
                    source_url=event_data.get("source_url"),
                    detected_at=datetime.now(UTC),
                    event_date=event_date,
                    relevance_score=event_data.get("relevance_score", 0.0),
                    raw_data=event_data.get("raw_data"),
                )
                session.add(trigger)
                saved_count += 1

            await session.commit()

        self.log.info(
            "trigger_scan_complete",
            property_id=str(property_uuid),
            events_found=len(all_events),
            events_saved=saved_count,
        )

        return {
            "property_id": str(property_uuid),
            "events_found": len(all_events),
            "events_saved": saved_count,
            "event_types": [e["event_type"] for e in all_events],
            "items_processed": 1,
            "items_failed": 0,
        }
