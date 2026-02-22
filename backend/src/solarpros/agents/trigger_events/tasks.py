"""Celery tasks for the Trigger Event Monitoring Agent."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select

from solarpros.agents.trigger_events.agent import TriggerEventAgent
from solarpros.celery_app.app import celery_app
from solarpros.db.session import async_session_factory
from solarpros.models.property import Property

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.trigger_events.tasks.scan_property_triggers",
    acks_late=True,
    max_retries=3,
    default_retry_delay=60,
    queue="trigger_events",
)
def scan_property_triggers(self, property_id: str) -> dict:
    """Scan for trigger events for a single property."""
    logger.info("celery_trigger_scan_start", property_id=property_id, task_id=self.request.id)

    try:
        agent = TriggerEventAgent()
        result = asyncio.run(agent.run(property_id=property_id))
        logger.info(
            "celery_trigger_scan_complete",
            property_id=property_id,
            events_found=result.get("events_found"),
        )
        return result

    except Exception as exc:
        logger.error(
            "celery_trigger_scan_failed",
            property_id=property_id,
            error=str(exc),
            attempt=self.request.retries + 1,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="solarpros.agents.trigger_events.tasks.daily_trigger_scan",
    acks_late=True,
    queue="trigger_events",
)
def daily_trigger_scan(self) -> dict:
    """Daily beat task: scan all qualifying properties for trigger events."""
    logger.info("daily_trigger_scan_start", task_id=self.request.id)

    async def _get_property_ids() -> list[str]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Property.id).where(
                    Property.is_commercial.is_(True),
                    Property.meets_roof_min.is_(True),
                )
            )
            return [str(row[0]) for row in result.all()]

    property_ids = asyncio.run(_get_property_ids())

    dispatched = 0
    for pid in property_ids:
        scan_property_triggers.delay(pid)
        dispatched += 1

    logger.info("daily_trigger_scan_dispatched", count=dispatched)
    return {"dispatched": dispatched}
