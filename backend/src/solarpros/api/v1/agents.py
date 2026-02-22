"""Agent pipeline control and run history endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import AgentRun
from solarpros.schemas import AgentRunRead, PipelineStartRequest, PipelineStatusResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/pipeline/start", response_model=AgentRunRead, status_code=202)
async def start_pipeline(
    payload: PipelineStartRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentRunRead:
    """Accept a PipelineStartRequest, create an AgentRun, and dispatch the Celery task."""
    # Create the controller agent run
    run = AgentRun(
        agent_type="controller",
        status="pending",
        config={
            "counties": payload.counties,
            "use_mock": payload.use_mock,
        },
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # Dispatch the Celery task (lazy import to avoid circular deps)
    from solarpros.agents.controller import run_pipeline_task

    task = run_pipeline_task.delay(str(run.id), payload.counties, payload.use_mock)

    # Store the Celery task ID back on the run
    run.celery_task_id = task.id
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.add(run)
    await db.flush()
    await db.refresh(run)

    return AgentRunRead.model_validate(run)


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    db: AsyncSession = Depends(get_db),
) -> PipelineStatusResponse:
    """Get the latest pipeline run status along with its child agent runs."""
    # Get the latest controller run
    stmt = (
        select(AgentRun)
        .where(AgentRun.agent_type == "controller")
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    controller_run = result.scalar_one_or_none()

    if controller_run is None:
        return PipelineStatusResponse(status="no_runs", runs=[], progress={})

    # Get child runs for this pipeline
    children_stmt = (
        select(AgentRun)
        .where(AgentRun.parent_run_id == controller_run.id)
        .order_by(AgentRun.created_at.asc())
    )
    children_result = await db.execute(children_stmt)
    child_runs = children_result.scalars().all()

    all_runs = [controller_run, *child_runs]
    run_schemas = [AgentRunRead.model_validate(r) for r in all_runs]

    # Build progress summary
    progress: dict[str, str] = {}
    for r in all_runs:
        progress[r.agent_type] = r.status

    return PipelineStatusResponse(
        status=controller_run.status,
        runs=run_schemas,
        progress=progress,
    )


@router.get("/runs", response_model=list[AgentRunRead])
async def list_agent_runs(
    agent_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[AgentRunRead]:
    """List agent runs with optional agent_type filter."""
    stmt = select(AgentRun)

    if agent_type:
        stmt = stmt.where(AgentRun.agent_type == agent_type)

    stmt = stmt.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)

    return [AgentRunRead.model_validate(r) for r in result.scalars().all()]
