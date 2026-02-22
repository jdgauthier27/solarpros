"""Celery tasks for the Enrichment Agent."""

from __future__ import annotations

import asyncio

import structlog

from solarpros.agents.enrichment.agent import EnrichmentAgent
from solarpros.celery_app.app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.enrichment.tasks.enrich_property",
    acks_late=True,
    max_retries=3,
    default_retry_delay=60,
    queue="enrichment",
)
def enrich_property(self, property_id: str) -> dict:
    """Enrich a single property with multi-source contact data.

    Parameters
    ----------
    property_id : str
        UUID string of the property to enrich.
    """
    logger.info("celery_enrich_property_start", property_id=property_id, task_id=self.request.id)

    try:
        agent = EnrichmentAgent()
        result = asyncio.run(agent.run(property_id=property_id))
        logger.info(
            "celery_enrich_property_complete",
            property_id=property_id,
            owner_id=result.get("owner_id"),
            contact_count=result.get("contact_count"),
        )
        return result

    except Exception as exc:
        logger.error(
            "celery_enrich_property_failed",
            property_id=property_id,
            error=str(exc),
            attempt=self.request.retries + 1,
        )
        raise self.retry(exc=exc)
