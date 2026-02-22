"""Request/response schemas for agent / pipeline endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_type: str
    celery_task_id: str | None = None
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items_processed: int = 0
    items_failed: int = 0
    error_message: str | None = None
    error_details: dict[str, Any] | None = None
    parent_run_id: uuid.UUID | None = None
    config: dict[str, Any] | None = None
    result_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class PipelineStartRequest(BaseModel):
    counties: list[str]
    use_mock: bool = True


class PipelineStatusResponse(BaseModel):
    status: str
    runs: list[AgentRunRead] = Field(default_factory=list)
    progress: dict[str, Any] = Field(default_factory=dict)
