"""Trigger event list endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models.trigger_event import TriggerEvent

router = APIRouter(prefix="/trigger-events", tags=["trigger_events"])


class TriggerEventRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    property_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    event_type: str
    title: str
    source: str
    source_url: str | None = None
    detected_at: datetime
    event_date: datetime | None = None
    relevance_score: float = 0.0
    raw_data: dict | None = None
    created_at: datetime | None = None


@router.get("/", response_model=list[TriggerEventRead])
async def list_trigger_events(
    property_id: uuid.UUID | None = Query(None),
    event_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[TriggerEventRead]:
    """List trigger events with optional filters."""
    stmt = select(TriggerEvent)

    if property_id:
        stmt = stmt.where(TriggerEvent.property_id == property_id)
    if event_type:
        stmt = stmt.where(TriggerEvent.event_type == event_type)

    stmt = stmt.order_by(TriggerEvent.detected_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [TriggerEventRead.model_validate(e) for e in result.scalars().all()]
