"""Celery tasks for property discovery."""

from __future__ import annotations

import asyncio

import structlog

from solarpros.celery_app.app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.property_discovery.tasks.discover_properties_for_county",
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
)
def discover_properties_for_county(self, county: str, max_pages: int = 10) -> dict:
    """Discover commercial properties for a single county.

    Instantiates a :class:`PropertyDiscoveryAgent` and runs it
    asynchronously inside the Celery worker process.

    Args:
        county: County name (e.g. ``"Los Angeles"``).
        max_pages: Maximum number of pages to scrape.

    Returns:
        Result summary dict from the agent.
    """
    from solarpros.agents.property_discovery.agent import PropertyDiscoveryAgent

    logger.info("task_discover_properties_starting", county=county, task_id=self.request.id)

    try:
        agent = PropertyDiscoveryAgent()
        result = asyncio.run(agent.run(county=county, max_pages=max_pages))
        logger.info("task_discover_properties_complete", county=county, result=result)
        return result
    except Exception as exc:
        logger.exception("task_discover_properties_failed", county=county)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="solarpros.agents.property_discovery.tasks.discover_all_properties",
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
)
def discover_all_properties(self, counties: list[str], max_pages: int = 10) -> dict:
    """Dispatch property discovery tasks for multiple counties.

    Creates a Celery :func:`~celery.group` of
    :func:`discover_properties_for_county` tasks, one per county, and
    dispatches them for parallel execution.

    Args:
        counties: List of county names.
        max_pages: Maximum pages to scrape per county.

    Returns:
        Dict with ``task_ids`` mapping county names to their task IDs.
    """
    from celery import group

    logger.info(
        "task_discover_all_starting",
        counties=counties,
        task_id=self.request.id,
    )

    try:
        job = group(
            discover_properties_for_county.s(county, max_pages) for county in counties
        )
        group_result = job.apply_async()

        # Build a mapping of county -> child task id
        task_ids: dict[str, str | None] = {}
        for county, async_result in zip(counties, group_result.children or []):
            task_ids[county] = async_result.id if async_result else None

        logger.info("task_discover_all_dispatched", task_ids=task_ids)
        return {"counties": counties, "task_ids": task_ids}
    except Exception as exc:
        logger.exception("task_discover_all_failed", counties=counties)
        raise self.retry(exc=exc)
