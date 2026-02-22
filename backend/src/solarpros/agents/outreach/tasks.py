"""Celery tasks for the Multi-Channel Outreach Agent."""

from __future__ import annotations

import asyncio

import structlog

from solarpros.agents.outreach.agent import OutreachAgent
from solarpros.celery_app.app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="solarpros.agents.outreach.tasks.execute_outreach_step",
    acks_late=True,
    max_retries=3,
    default_retry_delay=120,
    queue="email",
)
def execute_outreach_step(
    self,
    campaign_id: str | None = None,
    campaign_name: str | None = None,
    tier_filter: str = "A,B",
    min_score: float = 50.0,
    step_number: int = 1,
) -> dict:
    """Execute a single outreach step for a campaign."""
    logger.info(
        "celery_outreach_step_start",
        campaign_id=campaign_id,
        step=step_number,
        task_id=self.request.id,
    )

    try:
        agent = OutreachAgent()
        result = asyncio.run(
            agent.run(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                tier_filter=tier_filter,
                min_score=min_score,
                step_number=step_number,
            )
        )
        logger.info("celery_outreach_step_complete", **result)
        return result

    except Exception as exc:
        logger.error(
            "celery_outreach_step_failed",
            campaign_id=campaign_id,
            step=step_number,
            error=str(exc),
        )
        raise self.retry(exc=exc)
