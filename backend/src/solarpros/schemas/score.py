"""Request/response schemas for prospect score endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProspectScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    solar_analysis_id: uuid.UUID | None = None
    solar_potential_score: float = 0.0
    roof_size_score: float = 0.0
    savings_score: float = 0.0
    utility_zone_score: float = 0.0
    owner_type_score: float = 0.0
    contact_quality_score: float = 0.0
    building_age_score: float = 0.0
    composite_score: float = 0.0
    tier: str = "C"
    scoring_version: int = 1
    weight_config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ScoreDistribution(BaseModel):
    bucket: str
    count: int
