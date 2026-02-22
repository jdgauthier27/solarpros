"""Request/response schemas for solar analysis endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SolarAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    data_source: str
    usable_roof_sqft: float | None = None
    pitch: float | None = None
    azimuth: float | None = None
    sunshine_hours: float | None = None
    system_size_kw: float | None = None
    annual_kwh: float | None = None
    utility_rate: float | None = None
    annual_savings: float | None = None
    system_cost: float | None = None
    net_cost: float | None = None
    payback_years: float | None = None
    raw_response: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
