import asyncio

import structlog

from solarpros.agents.scoring.agent import ScoringAgent
from solarpros.celery_app.app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, acks_late=True, name="solarpros.agents.scoring.tasks.score_property")
def score_property(self, property_id: str) -> dict:
    """Score a single property and persist the result."""
    logger.info("task_score_property", property_id=property_id)
    agent = ScoringAgent()
    return asyncio.run(agent.run(property_id=property_id))


@celery_app.task(bind=True, acks_late=True, name="solarpros.agents.scoring.tasks.score_batch")
def score_batch(self, property_ids: list[str]) -> dict:
    """Score a batch of properties sequentially."""
    logger.info("task_score_batch", count=len(property_ids))
    results = []
    failed = 0
    for pid in property_ids:
        try:
            agent = ScoringAgent()
            result = asyncio.run(agent.run(property_id=pid))
            results.append(result)
        except Exception as exc:
            logger.error("task_score_batch_item_failed", property_id=pid, error=str(exc))
            failed += 1
    return {
        "items_processed": len(results),
        "items_failed": failed,
        "results": results,
    }
