import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import async_session_factory
from solarpros.models.agent_run import AgentRun

logger = structlog.get_logger()


class BaseAgent(ABC):
    agent_type: str = "base"

    def __init__(self, run_id: uuid.UUID | None = None, parent_run_id: uuid.UUID | None = None):
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.log = logger.bind(agent_type=self.agent_type)

    async def create_run(self, config: dict | None = None) -> AgentRun:
        async with async_session_factory() as session:
            run = AgentRun(
                agent_type=self.agent_type,
                status="pending",
                parent_run_id=self.parent_run_id,
                config=config,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            self.run_id = run.id
            return run

    async def update_run_status(
        self,
        status: str,
        items_processed: int = 0,
        items_failed: int = 0,
        error_message: str | None = None,
        error_details: dict | None = None,
        result_summary: dict | None = None,
    ) -> None:
        if not self.run_id:
            return
        async with async_session_factory() as session:
            result = await session.execute(
                select(AgentRun).where(AgentRun.id == self.run_id)
            )
            run = result.scalar_one_or_none()
            if not run:
                return
            run.status = status
            run.items_processed = items_processed
            run.items_failed = items_failed
            if status == "running" and not run.started_at:
                run.started_at = datetime.now(UTC)
            if status in ("completed", "failed"):
                run.completed_at = datetime.now(UTC)
            if error_message:
                run.error_message = error_message
                run.error_details = error_details
            if result_summary:
                run.result_summary = result_summary
            await session.commit()

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Execute the agent's main logic. Returns a result summary dict."""

    async def run(self, **kwargs) -> dict:
        await self.create_run(config=kwargs)
        await self.update_run_status("running")
        try:
            result = await self.execute(**kwargs)
            await self.update_run_status(
                "completed",
                items_processed=result.get("items_processed", 0),
                items_failed=result.get("items_failed", 0),
                result_summary=result,
            )
            return result
        except Exception as e:
            self.log.error("agent_failed", error=str(e))
            await self.update_run_status(
                "failed",
                error_message=str(e),
                error_details={"type": type(e).__name__},
            )
            raise
