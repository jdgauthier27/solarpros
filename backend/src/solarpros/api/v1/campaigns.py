"""Email campaign CRUD, metrics, and SendGrid webhook endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import EmailCampaign, EmailSend
from solarpros.schemas import (
    CampaignMetrics,
    EmailCampaignCreate,
    EmailCampaignRead,
    EmailCampaignUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[EmailCampaignRead])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
) -> list[EmailCampaignRead]:
    """List all email campaigns."""
    stmt = select(EmailCampaign).order_by(EmailCampaign.created_at.desc())
    result = await db.execute(stmt)
    return [EmailCampaignRead.model_validate(c) for c in result.scalars().all()]


@router.post("/", response_model=EmailCampaignRead, status_code=201)
async def create_campaign(
    payload: EmailCampaignCreate,
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignRead:
    """Create a new email campaign."""
    campaign = EmailCampaign(
        name=payload.name,
        tier_filter=payload.tier_filter,
        min_score=payload.min_score,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return EmailCampaignRead.model_validate(campaign)


@router.get("/{campaign_id}", response_model=EmailCampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignRead:
    """Get a single campaign by ID."""
    stmt = select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return EmailCampaignRead.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=EmailCampaignRead)
async def update_campaign(
    campaign_id: uuid.UUID,
    payload: EmailCampaignUpdate,
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignRead:
    """Update campaign fields."""
    stmt = select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return EmailCampaignRead.model_validate(campaign)


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_campaign_metrics(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CampaignMetrics:
    """Compute aggregate metrics from email sends for a campaign."""
    # Verify campaign exists
    camp_stmt = select(EmailCampaign.id).where(EmailCampaign.id == campaign_id)
    camp_result = await db.execute(camp_stmt)
    if camp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    stmt = select(
        func.count(EmailSend.id).label("total_sent"),
        func.count(EmailSend.delivered_at).label("delivered"),
        func.count(EmailSend.opened_at).label("opened"),
        func.count(EmailSend.clicked_at).label("clicked"),
        func.count(EmailSend.replied_at).label("replied"),
    ).where(EmailSend.campaign_id == campaign_id)

    result = await db.execute(stmt)
    row = result.one()

    total_sent = row.total_sent or 0
    delivered = row.delivered or 0
    opened = row.opened or 0
    clicked = row.clicked or 0
    replied = row.replied or 0

    bounced_stmt = (
        select(func.count(EmailSend.id))
        .where(EmailSend.campaign_id == campaign_id)
        .where(EmailSend.status == "bounced")
    )
    bounced = (await db.execute(bounced_stmt)).scalar() or 0

    return CampaignMetrics(
        total_sent=total_sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        replied=replied,
        bounced=bounced,
        open_rate=round(opened / delivered, 4) if delivered > 0 else 0.0,
        click_rate=round(clicked / delivered, 4) if delivered > 0 else 0.0,
        reply_rate=round(replied / delivered, 4) if delivered > 0 else 0.0,
    )


@router.post("/webhooks/sendgrid")
async def sendgrid_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle SendGrid event webhook (accepts raw JSON body).

    SendGrid sends an array of event objects. Each event has a ``sg_message_id``
    and an ``event`` type (delivered, open, click, bounce, etc.).
    """
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(events, list):
        events = [events]

    for event in events:
        sg_message_id = event.get("sg_message_id")
        event_type = event.get("event")

        if not sg_message_id or not event_type:
            continue

        # Strip the filter ID suffix SendGrid appends (e.g., "abc123.filter...")
        base_message_id = sg_message_id.split(".")[0] if "." in sg_message_id else sg_message_id

        stmt = select(EmailSend).where(
            EmailSend.sendgrid_message_id.like(f"{base_message_id}%")
        )
        result = await db.execute(stmt)
        send = result.scalar_one_or_none()

        if send is None:
            logger.warning("SendGrid event for unknown message_id: %s", sg_message_id)
            continue

        if event_type == "delivered":
            send.status = "delivered"
            send.delivered_at = func.now()
        elif event_type == "open":
            send.open_count += 1
            if send.opened_at is None:
                send.opened_at = func.now()
        elif event_type == "click":
            send.click_count += 1
            if send.clicked_at is None:
                send.clicked_at = func.now()
        elif event_type == "bounce":
            send.status = "bounced"
        elif event_type == "spamreport":
            send.is_unsubscribed = True

        db.add(send)

    await db.flush()
    return {"status": "ok"}
