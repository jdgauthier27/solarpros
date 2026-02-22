"""Outreach queue endpoints — LinkedIn actions, phone call list, direct mail queue."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models.outreach import OutreachTouch

router = APIRouter(prefix="/outreach", tags=["outreach"])


class OutreachTouchRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    channel: str
    status: str
    sendgrid_message_id: str | None = None
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    replied_at: datetime | None = None
    call_duration_seconds: int | None = None
    call_outcome: str | None = None
    linkedin_connection_status: str | None = None
    response_type: str | None = None
    notes: str | None = None
    created_at: datetime | None = None


class OutreachTouchUpdate(BaseModel):
    status: str | None = None
    call_duration_seconds: int | None = None
    call_outcome: str | None = None
    linkedin_connection_status: str | None = None
    response_type: str | None = None
    notes: str | None = None


@router.get("/queue", response_model=list[OutreachTouchRead])
async def list_outreach_queue(
    channel: str | None = Query(None),
    status: str | None = Query(None, description="Filter by status (pending, sent, etc.)"),
    campaign_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[OutreachTouchRead]:
    """List outreach touches with optional filters.

    Use channel=linkedin for LinkedIn actions queue,
    channel=phone for call list, channel=direct_mail for mail queue.
    """
    stmt = select(OutreachTouch)

    if channel:
        stmt = stmt.where(OutreachTouch.channel == channel)
    if status:
        stmt = stmt.where(OutreachTouch.status == status)
    if campaign_id:
        stmt = stmt.where(OutreachTouch.campaign_id == campaign_id)

    stmt = stmt.order_by(OutreachTouch.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [OutreachTouchRead.model_validate(t) for t in result.scalars().all()]


@router.get("/linkedin-actions", response_model=list[OutreachTouchRead])
async def list_linkedin_actions(
    status: str = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[OutreachTouchRead]:
    """List LinkedIn actions queue."""
    stmt = (
        select(OutreachTouch)
        .where(OutreachTouch.channel == "linkedin", OutreachTouch.status == status)
        .order_by(OutreachTouch.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [OutreachTouchRead.model_validate(t) for t in result.scalars().all()]


@router.get("/call-list", response_model=list[OutreachTouchRead])
async def list_call_list(
    status: str = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[OutreachTouchRead]:
    """List phone call queue with scripts."""
    stmt = (
        select(OutreachTouch)
        .where(OutreachTouch.channel == "phone", OutreachTouch.status == status)
        .order_by(OutreachTouch.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [OutreachTouchRead.model_validate(t) for t in result.scalars().all()]


@router.get("/direct-mail", response_model=list[OutreachTouchRead])
async def list_direct_mail(
    status: str = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[OutreachTouchRead]:
    """List direct mail queue."""
    stmt = (
        select(OutreachTouch)
        .where(OutreachTouch.channel == "direct_mail", OutreachTouch.status == status)
        .order_by(OutreachTouch.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [OutreachTouchRead.model_validate(t) for t in result.scalars().all()]


@router.patch("/{touch_id}", response_model=OutreachTouchRead)
async def update_outreach_touch(
    touch_id: uuid.UUID,
    payload: OutreachTouchUpdate,
    db: AsyncSession = Depends(get_db),
) -> OutreachTouchRead:
    """Update an outreach touch (e.g., log call outcome, LinkedIn status)."""
    result = await db.execute(
        select(OutreachTouch).where(OutreachTouch.id == touch_id)
    )
    touch = result.scalar_one_or_none()
    if not touch:
        raise HTTPException(status_code=404, detail="Outreach touch not found")

    if payload.status is not None:
        touch.status = payload.status
    if payload.call_duration_seconds is not None:
        touch.call_duration_seconds = payload.call_duration_seconds
    if payload.call_outcome is not None:
        touch.call_outcome = payload.call_outcome
    if payload.linkedin_connection_status is not None:
        touch.linkedin_connection_status = payload.linkedin_connection_status
    if payload.response_type is not None:
        touch.response_type = payload.response_type
    if payload.notes is not None:
        touch.notes = payload.notes

    await db.flush()
    await db.refresh(touch)
    return OutreachTouchRead.model_validate(touch)
