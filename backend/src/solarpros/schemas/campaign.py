"""Request/response schemas for email campaign endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Email Sequence
# ---------------------------------------------------------------------------


class EmailSequenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    step_number: int
    delay_days: int = 0
    subject_template: str
    body_template: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Email Campaign
# ---------------------------------------------------------------------------


class EmailCampaignCreate(BaseModel):
    name: str
    tier_filter: str | None = None
    min_score: float | None = None


class EmailCampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str = "draft"
    tier_filter: str | None = None
    min_score: float | None = None
    sequences: list[EmailSequenceRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EmailCampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    tier_filter: str | None = None
    min_score: float | None = None


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class CampaignMetrics(BaseModel):
    total_sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    reply_rate: float = 0.0
