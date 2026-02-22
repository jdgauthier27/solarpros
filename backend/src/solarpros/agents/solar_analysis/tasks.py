"""Celery tasks for the Solar Analysis agent.

These tasks wrap the async :class:`SolarAnalysisAgent` so that the solar
analysis pipeline can be triggered from anywhere that has access to the
Celery broker (API endpoints, the orchestration controller, or the CLI).
"""

from __future__ import annotations

import asyncio

import structlog

from solarpros.celery_app.app import celery_app

from .agent import SolarAnalysisAgent

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.solar_analysis.tasks.analyze_property_solar",
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
)
def analyze_property_solar(self, property_id: str) -> dict:
    """Analyse solar potential for a single property.

    Parameters
    ----------
    self:
        Celery task instance (``bind=True``).
    property_id:
        UUID string of the property to analyse.

    Returns
    -------
    dict
        Result summary from the agent.
    """
    logger.info("task_analyze_property_solar", property_id=property_id)
    try:
        agent = SolarAnalysisAgent()
        result = asyncio.run(agent.run(property_id=property_id))
        return result
    except Exception as exc:
        logger.error(
            "task_analyze_property_solar_failed",
            property_id=property_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="solarpros.agents.solar_analysis.tasks.analyze_batch_solar",
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
)
def analyze_batch_solar(self, property_ids: list[str]) -> dict:
    """Analyse solar potential for a batch of properties.

    Dispatches individual :func:`analyze_property_solar` tasks so that each
    property is processed independently and can be retried on its own.

    Parameters
    ----------
    self:
        Celery task instance (``bind=True``).
    property_ids:
        List of UUID strings for properties to analyse.

    Returns
    -------
    dict
        Summary with total, dispatched, and failed counts.
    """
    logger.info(
        "task_analyze_batch_solar",
        batch_size=len(property_ids),
    )
    dispatched = 0
    failed = 0

    for pid in property_ids:
        try:
            analyze_property_solar.delay(pid)
            dispatched += 1
        except Exception as exc:
            logger.error(
                "task_batch_dispatch_failed",
                property_id=pid,
                error=str(exc),
            )
            failed += 1

    result = {
        "total": len(property_ids),
        "dispatched": dispatched,
        "failed": failed,
    }

    logger.info("task_analyze_batch_solar_complete", **result)
    return result
