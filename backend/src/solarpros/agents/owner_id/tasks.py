"""Celery tasks for the Owner Identification Agent.

Provides two tasks:
- ``identify_owner``  -- process a single property.
- ``identify_owners_batch`` -- fan-out processing for multiple properties.
"""

from __future__ import annotations

import asyncio

import structlog

from solarpros.agents.owner_id.agent import OwnerIDAgent
from solarpros.celery_app.app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.owner_id.tasks.identify_owner",
    acks_late=True,
    max_retries=5,
    default_retry_delay=60,
)
def identify_owner(self, property_id: str) -> dict:
    """Identify the owner of a single property.

    Parameters
    ----------
    property_id : str
        UUID string of the property to process.

    Returns
    -------
    dict
        Result summary from :meth:`OwnerIDAgent.run`.
    """
    logger.info(
        "celery_identify_owner_start",
        property_id=property_id,
        task_id=self.request.id,
    )

    try:
        agent = OwnerIDAgent()
        result = asyncio.run(agent.run(property_id=property_id))
        logger.info(
            "celery_identify_owner_complete",
            property_id=property_id,
            owner_id=result.get("owner_id"),
            confidence_score=result.get("confidence_score"),
        )
        return result

    except Exception as exc:
        logger.error(
            "celery_identify_owner_failed",
            property_id=property_id,
            error=str(exc),
            attempt=self.request.retries + 1,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="solarpros.agents.owner_id.tasks.identify_owners_batch",
    acks_late=True,
    max_retries=5,
    default_retry_delay=120,
)
def identify_owners_batch(self, property_ids: list[str]) -> dict:
    """Fan-out owner identification for a batch of properties.

    Dispatches individual ``identify_owner`` tasks for each property
    and returns a summary.

    Parameters
    ----------
    property_ids : list[str]
        List of property UUID strings to process.

    Returns
    -------
    dict
        Summary with dispatched count and task IDs.
    """
    logger.info(
        "celery_identify_owners_batch_start",
        count=len(property_ids),
        task_id=self.request.id,
    )

    try:
        dispatched_tasks = []
        for pid in property_ids:
            task = identify_owner.delay(pid)
            dispatched_tasks.append(
                {"property_id": pid, "task_id": task.id}
            )

        result = {
            "batch_size": len(property_ids),
            "dispatched": len(dispatched_tasks),
            "tasks": dispatched_tasks,
        }

        logger.info(
            "celery_identify_owners_batch_dispatched",
            batch_size=len(property_ids),
            dispatched=len(dispatched_tasks),
        )
        return result

    except Exception as exc:
        logger.error(
            "celery_identify_owners_batch_failed",
            count=len(property_ids),
            error=str(exc),
            attempt=self.request.retries + 1,
        )
        raise self.retry(exc=exc)
