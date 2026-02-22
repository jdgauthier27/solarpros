"""Central Controller -- Phase 7 orchestrator for the SolarPros pipeline.

Wires the five agents together using Celery canvas primitives (chain, chord,
group) so that the full discovery-to-outreach pipeline can be executed with a
single ``run_full_pipeline`` call.

Pipeline stages
---------------
1. **Discovery** -- fan-out one task per county (group).
2. **Post-discovery** -- query DB for qualifying properties, dispatch solar
   analysis + owner identification in parallel for each property (chord).
3. **Post-analysis** -- dispatch scoring for every property (group inside a
   chord callback).
4. **Post-scoring** -- optionally create an email campaign and dispatch
   outreach.
5. **Finalize** -- mark the controller ``AgentRun`` as completed.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from celery import chain, chord, group
from sqlalchemy import select

from solarpros.celery_app.app import celery_app
from solarpros.db.session import async_session_factory
from solarpros.models.agent_run import AgentRun
from solarpros.models.property import Property

# Lazy imports of downstream tasks happen inside each function to avoid
# circular-import issues that arise when autodiscovery loads this module before
# the agent packages are fully initialised.

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STALLED_THRESHOLD_MINUTES = 120


async def _create_agent_run(
    agent_type: str,
    *,
    parent_run_id: uuid.UUID | None = None,
    celery_task_id: str | None = None,
    config: dict | None = None,
    status: str = "running",
) -> AgentRun:
    """Persist a new ``AgentRun`` row and return it."""
    async with async_session_factory() as session:
        run = AgentRun(
            agent_type=agent_type,
            parent_run_id=parent_run_id,
            celery_task_id=celery_task_id,
            config=config,
            status=status,
            started_at=datetime.now(UTC) if status == "running" else None,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run


async def _update_agent_run(
    run_id: uuid.UUID,
    *,
    status: str | None = None,
    items_processed: int | None = None,
    items_failed: int | None = None,
    error_message: str | None = None,
    error_details: dict | None = None,
    result_summary: dict | None = None,
) -> None:
    """Update an existing ``AgentRun`` row."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            logger.warning("agent_run_not_found", run_id=str(run_id))
            return

        if status is not None:
            run.status = status
        if items_processed is not None:
            run.items_processed = items_processed
        if items_failed is not None:
            run.items_failed = items_failed
        if error_message is not None:
            run.error_message = error_message
            run.error_details = error_details
        if result_summary is not None:
            run.result_summary = result_summary

        if status == "running" and not run.started_at:
            run.started_at = datetime.now(UTC)
        if status in ("completed", "failed"):
            run.completed_at = datetime.now(UTC)

        await session.commit()


async def _get_qualifying_property_ids() -> list[str]:
    """Return stringified UUIDs for all commercial, roof-qualifying properties."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Property.id).where(
                Property.is_commercial.is_(True),
                Property.meets_roof_min.is_(True),
            )
        )
        return [str(row[0]) for row in result.all()]


# ---------------------------------------------------------------------------
# Main pipeline entry-point
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.run_full_pipeline",
    queue="orchestration",
)
def run_full_pipeline(
    self,
    counties: list[str],
    use_mock: bool = True,
    campaign_name: str | None = None,
) -> dict:
    """Kick off the full SolarPros pipeline.

    Creates a controller-level ``AgentRun``, then builds a Celery canvas
    that chains together the five agent stages.

    Parameters
    ----------
    counties:
        List of county names to run discovery against.
    use_mock:
        Whether downstream agents should use mock data sources.
    campaign_name:
        Optional name for the email campaign created at the end of the
        pipeline.  When ``None`` no campaign is dispatched.

    Returns
    -------
    dict
        Summary dict with the ``parent_run_id`` and dispatched task info.
    """
    from solarpros.agents.property_discovery.tasks import discover_properties_for_county

    logger.info(
        "controller_run_full_pipeline_start",
        counties=counties,
        use_mock=use_mock,
        campaign_name=campaign_name,
        task_id=self.request.id,
    )

    # 1. Create the top-level controller AgentRun -------------------------
    parent_run = asyncio.run(
        _create_agent_run(
            "controller",
            celery_task_id=self.request.id,
            config={
                "counties": counties,
                "use_mock": use_mock,
                "campaign_name": campaign_name,
            },
        )
    )
    parent_run_id = str(parent_run.id)

    try:
        # 2. Build the canvas ---------------------------------------------
        # Step 1 -- discovery group (one task per county)
        discovery_group = group(
            discover_properties_for_county.s(county) for county in counties
        )

        # Steps 2-5 are linked via callbacks that themselves dispatch the
        # next stage; this avoids serialising live DB objects through the
        # broker.
        pipeline = chain(
            # Step 1 -> Step 2
            chord(discovery_group, process_post_discovery.s(parent_run_id)),
            # Step 3 (solar + owner) -> Step 4 (scoring)
            # process_post_discovery returns a chord that feeds into
            # process_post_analysis, which then dispatches scoring via
            # process_post_scoring.  Because these intermediate steps are
            # themselves tasks the chain continues automatically.
        )

        async_result = pipeline.apply_async()

        logger.info(
            "controller_pipeline_dispatched",
            parent_run_id=parent_run_id,
            root_task_id=async_result.id,
        )

        return {
            "parent_run_id": parent_run_id,
            "root_task_id": async_result.id,
            "counties": counties,
            "campaign_name": campaign_name,
        }

    except Exception as exc:
        logger.exception("controller_run_full_pipeline_failed")
        asyncio.run(
            _update_agent_run(
                uuid.UUID(parent_run_id),
                status="failed",
                error_message=str(exc),
                error_details={"type": type(exc).__name__},
            )
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Stage callbacks
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.process_post_discovery",
    queue="orchestration",
)
def process_post_discovery(self, results, parent_run_id: str) -> dict:
    """Called after the discovery group completes.

    Queries the DB for qualifying properties (``is_commercial=True`` and
    ``meets_roof_min=True``), then dispatches solar-analysis + owner-ID
    tasks in parallel for each property via a chord whose callback is
    :func:`process_post_analysis`.

    Parameters
    ----------
    results:
        Aggregated results from the discovery group (list of dicts).
    parent_run_id:
        UUID string of the controller ``AgentRun``.

    Returns
    -------
    dict
        Summary of what was dispatched.
    """
    from solarpros.agents.owner_id.tasks import identify_owner
    from solarpros.agents.solar_analysis.tasks import analyze_property_solar

    logger.info(
        "controller_post_discovery",
        parent_run_id=parent_run_id,
        discovery_results_count=len(results) if isinstance(results, list) else 0,
        task_id=self.request.id,
    )

    # Create a child AgentRun for this orchestration step
    asyncio.run(
        _create_agent_run(
            "controller",
            parent_run_id=uuid.UUID(parent_run_id),
            celery_task_id=self.request.id,
            config={"stage": "post_discovery"},
        )
    )

    try:
        property_ids = asyncio.run(_get_qualifying_property_ids())
        logger.info(
            "controller_qualifying_properties",
            parent_run_id=parent_run_id,
            qualifying_count=len(property_ids),
        )

        if not property_ids:
            logger.warning(
                "controller_no_qualifying_properties",
                parent_run_id=parent_run_id,
            )
            asyncio.run(
                _update_agent_run(
                    uuid.UUID(parent_run_id),
                    status="completed",
                    result_summary={
                        "stage": "post_discovery",
                        "qualifying_properties": 0,
                        "message": "No qualifying properties found",
                    },
                )
            )
            return {
                "parent_run_id": parent_run_id,
                "qualifying_properties": 0,
                "dispatched": 0,
            }

        # For each property, run solar analysis and owner ID in parallel
        analysis_owner_tasks = group(
            group(
                analyze_property_solar.si(pid),
                identify_owner.si(pid),
            )
            for pid in property_ids
        )

        # Chord: when all solar+owner tasks finish, run post-analysis
        callback = process_post_analysis.s(parent_run_id)
        analysis_chord = chord(analysis_owner_tasks, callback)
        analysis_chord.apply_async()

        logger.info(
            "controller_solar_owner_dispatched",
            parent_run_id=parent_run_id,
            property_count=len(property_ids),
        )

        return {
            "parent_run_id": parent_run_id,
            "qualifying_properties": len(property_ids),
            "dispatched": len(property_ids) * 2,  # solar + owner per property
        }

    except Exception as exc:
        logger.exception("controller_post_discovery_failed", parent_run_id=parent_run_id)
        asyncio.run(
            _update_agent_run(
                uuid.UUID(parent_run_id),
                status="failed",
                error_message=f"post_discovery failed: {exc}",
                error_details={"type": type(exc).__name__, "stage": "post_discovery"},
            )
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.process_post_analysis",
    queue="orchestration",
)
def process_post_analysis(self, results, parent_run_id: str) -> dict:
    """Called after the solar+owner chord completes.

    Dispatches scoring tasks for every qualifying property as a chord
    whose callback is :func:`process_post_scoring`.

    Parameters
    ----------
    results:
        Aggregated results from the solar+owner chord.
    parent_run_id:
        UUID string of the controller ``AgentRun``.

    Returns
    -------
    dict
        Summary of scoring tasks dispatched.
    """
    from solarpros.agents.scoring.tasks import score_property

    logger.info(
        "controller_post_analysis",
        parent_run_id=parent_run_id,
        analysis_results_count=len(results) if isinstance(results, list) else 0,
        task_id=self.request.id,
    )

    # Create a child AgentRun for this orchestration step
    asyncio.run(
        _create_agent_run(
            "controller",
            parent_run_id=uuid.UUID(parent_run_id),
            celery_task_id=self.request.id,
            config={"stage": "post_analysis"},
        )
    )

    try:
        property_ids = asyncio.run(_get_qualifying_property_ids())

        if not property_ids:
            logger.warning(
                "controller_no_properties_to_score",
                parent_run_id=parent_run_id,
            )
            asyncio.run(
                _update_agent_run(
                    uuid.UUID(parent_run_id),
                    status="completed",
                    result_summary={
                        "stage": "post_analysis",
                        "properties_scored": 0,
                    },
                )
            )
            return {
                "parent_run_id": parent_run_id,
                "properties_scored": 0,
            }

        # Retrieve the campaign_name from the parent run config
        campaign_name = asyncio.run(_get_parent_campaign_name(parent_run_id))

        scoring_tasks = group(score_property.si(pid) for pid in property_ids)

        callback = process_post_scoring.s(parent_run_id, campaign_name)
        scoring_chord = chord(scoring_tasks, callback)
        scoring_chord.apply_async()

        logger.info(
            "controller_scoring_dispatched",
            parent_run_id=parent_run_id,
            property_count=len(property_ids),
        )

        return {
            "parent_run_id": parent_run_id,
            "scoring_dispatched": len(property_ids),
        }

    except Exception as exc:
        logger.exception("controller_post_analysis_failed", parent_run_id=parent_run_id)
        asyncio.run(
            _update_agent_run(
                uuid.UUID(parent_run_id),
                status="failed",
                error_message=f"post_analysis failed: {exc}",
                error_details={"type": type(exc).__name__, "stage": "post_analysis"},
            )
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.process_post_scoring",
    queue="orchestration",
)
def process_post_scoring(
    self,
    results,
    parent_run_id: str,
    campaign_name: str | None = None,
) -> dict:
    """Called after scoring completes.

    If ``campaign_name`` is provided, creates an ``EmailCampaign`` record
    and dispatches :func:`send_campaign_emails`.  Otherwise skips straight
    to :func:`finalize_pipeline`.

    Parameters
    ----------
    results:
        Aggregated scoring results.
    parent_run_id:
        UUID string of the controller ``AgentRun``.
    campaign_name:
        Optional campaign name.  ``None`` means skip email outreach.

    Returns
    -------
    dict
        Summary including campaign info if created.
    """
    from solarpros.agents.email_outreach.tasks import send_campaign_emails

    logger.info(
        "controller_post_scoring",
        parent_run_id=parent_run_id,
        scoring_results_count=len(results) if isinstance(results, list) else 0,
        campaign_name=campaign_name,
        task_id=self.request.id,
    )

    # Create a child AgentRun for this orchestration step
    asyncio.run(
        _create_agent_run(
            "controller",
            parent_run_id=uuid.UUID(parent_run_id),
            celery_task_id=self.request.id,
            config={"stage": "post_scoring", "campaign_name": campaign_name},
        )
    )

    try:
        if campaign_name:
            campaign_id = asyncio.run(_create_email_campaign(campaign_name))
            logger.info(
                "controller_campaign_created",
                parent_run_id=parent_run_id,
                campaign_id=campaign_id,
            )

            # Chain: send emails then finalize the pipeline
            email_chain = chain(
                send_campaign_emails.si(campaign_id),
                finalize_pipeline.si(parent_run_id),
            )
            email_chain.apply_async()

            return {
                "parent_run_id": parent_run_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "email_dispatched": True,
            }
        else:
            # No campaign requested -- finalize immediately
            finalize_pipeline.delay(parent_run_id)

            return {
                "parent_run_id": parent_run_id,
                "email_dispatched": False,
            }

    except Exception as exc:
        logger.exception("controller_post_scoring_failed", parent_run_id=parent_run_id)
        asyncio.run(
            _update_agent_run(
                uuid.UUID(parent_run_id),
                status="failed",
                error_message=f"post_scoring failed: {exc}",
                error_details={"type": type(exc).__name__, "stage": "post_scoring"},
            )
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.finalize_pipeline",
    queue="orchestration",
)
def finalize_pipeline(self, result_or_run_id, parent_run_id: str | None = None) -> dict:
    """Mark the controller ``AgentRun`` as completed.

    Accepts either:
    - ``(result, parent_run_id)`` when used as a chord/chain callback, or
    - ``(parent_run_id,)`` when called directly via ``.delay()``.

    Parameters
    ----------
    result_or_run_id:
        Either the upstream task result (ignored) or the parent_run_id
        string when called standalone.
    parent_run_id:
        UUID string of the controller ``AgentRun``.  If ``None``,
        ``result_or_run_id`` is treated as the run ID.

    Returns
    -------
    dict
        Final summary.
    """
    run_id = parent_run_id if parent_run_id is not None else result_or_run_id

    logger.info(
        "controller_finalize_pipeline",
        parent_run_id=run_id,
        task_id=self.request.id,
    )

    try:
        summary = asyncio.run(_build_pipeline_summary(run_id))

        asyncio.run(
            _update_agent_run(
                uuid.UUID(run_id),
                status="completed",
                items_processed=summary.get("total_properties", 0),
                result_summary=summary,
            )
        )

        logger.info(
            "controller_pipeline_completed",
            parent_run_id=run_id,
            summary=summary,
        )

        return {
            "parent_run_id": run_id,
            "status": "completed",
            "summary": summary,
        }

    except Exception as exc:
        logger.exception("controller_finalize_failed", parent_run_id=run_id)
        asyncio.run(
            _update_agent_run(
                uuid.UUID(run_id),
                status="failed",
                error_message=f"finalize failed: {exc}",
                error_details={"type": type(exc).__name__, "stage": "finalize"},
            )
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Beat task -- pipeline health check
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    acks_late=True,
    name="solarpros.agents.controller.check_pipeline_health",
    queue="orchestration",
)
def check_pipeline_health(self) -> dict:
    """Periodic beat task that detects stalled controller runs.

    A run is considered stalled when it has been in ``running`` status for
    longer than :data:`STALLED_THRESHOLD_MINUTES` without progressing.

    Returns
    -------
    dict
        Summary with stalled run IDs and counts.
    """
    logger.info("controller_health_check_start", task_id=self.request.id)

    try:
        result = asyncio.run(_check_stalled_runs())
        logger.info("controller_health_check_complete", **result)
        return result
    except Exception as exc:
        logger.exception("controller_health_check_failed")
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async helpers used by the tasks above
# ---------------------------------------------------------------------------


async def _get_parent_campaign_name(parent_run_id: str) -> str | None:
    """Retrieve the ``campaign_name`` stored in the parent run's config."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentRun).where(AgentRun.id == uuid.UUID(parent_run_id))
        )
        run = result.scalar_one_or_none()
        if run and run.config:
            return run.config.get("campaign_name")
        return None


async def _create_email_campaign(campaign_name: str) -> str:
    """Create a new ``EmailCampaign`` row and return its UUID string."""
    from solarpros.models.email_campaign import EmailCampaign

    async with async_session_factory() as session:
        campaign = EmailCampaign(
            name=campaign_name,
            status="active",
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)
        return str(campaign.id)


async def _build_pipeline_summary(parent_run_id: str) -> dict:
    """Build a summary dict of the entire pipeline run."""
    async with async_session_factory() as session:
        # Count child runs by status
        child_runs_result = await session.execute(
            select(AgentRun).where(
                AgentRun.parent_run_id == uuid.UUID(parent_run_id),
            )
        )
        child_runs = list(child_runs_result.scalars().all())

        completed = sum(1 for r in child_runs if r.status == "completed")
        failed = sum(1 for r in child_runs if r.status == "failed")
        running = sum(1 for r in child_runs if r.status == "running")

        # Count qualifying properties
        prop_result = await session.execute(
            select(Property.id).where(
                Property.is_commercial.is_(True),
                Property.meets_roof_min.is_(True),
            )
        )
        total_properties = len(prop_result.all())

    return {
        "total_properties": total_properties,
        "child_runs_completed": completed,
        "child_runs_failed": failed,
        "child_runs_running": running,
        "child_runs_total": len(child_runs),
    }


async def _check_stalled_runs() -> dict:
    """Find controller runs stuck in ``running`` beyond the threshold."""
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(minutes=STALLED_THRESHOLD_MINUTES)

    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentRun).where(
                AgentRun.agent_type == "controller",
                AgentRun.status == "running",
                AgentRun.started_at < cutoff,
            )
        )
        stalled_runs = list(result.scalars().all())

        stalled_ids = []
        for run in stalled_runs:
            run.status = "failed"
            run.completed_at = datetime.now(UTC)
            run.error_message = (
                f"Pipeline stalled -- no progress for {STALLED_THRESHOLD_MINUTES} minutes"
            )
            stalled_ids.append(str(run.id))

        if stalled_runs:
            await session.commit()

    return {
        "stalled_count": len(stalled_ids),
        "stalled_run_ids": stalled_ids,
    }
