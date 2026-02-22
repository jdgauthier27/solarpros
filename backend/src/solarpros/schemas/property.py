"""Request/response schemas for property endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base / Create / Read
# ---------------------------------------------------------------------------


class PropertyBase(BaseModel):
    apn: str
    county: str
    address: str
    city: str | None = None
    state: str = "CA"
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zoning: str | None = None
    building_type: str | None = None
    building_sqft: float | None = None
    roof_sqft: float | None = None
    year_built: int | None = None
    owner_name_raw: str | None = None
    is_commercial: bool = False
    meets_roof_min: bool = False


class PropertyCreate(PropertyBase):
    pass


class PropertyRead(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PropertyDetail(PropertyRead):
    """PropertyRead with nested related objects."""

    # Forward references resolved at import time via __init__.py
    owners: list[OwnerRead] = Field(default_factory=list)
    solar_analyses: list[SolarAnalysisRead] = Field(default_factory=list)
    scores: list[ProspectScoreRead] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Filtering / Stats
# ---------------------------------------------------------------------------


class PropertyFilter(BaseModel):
    county: str | None = None
    is_commercial: bool | None = None
    min_roof_sqft: float | None = None
    tier: str | None = None
    min_score: float | None = None
    bbox: list[float] | None = Field(
        default=None,
        description="Bounding box for geo filtering [min_lng, min_lat, max_lng, max_lat]",
        min_length=4,
        max_length=4,
    )


class PropertyStats(BaseModel):
    county: str
    count: int
    avg_score: float | None = None
    tier_counts: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deferred imports to resolve forward references
# ---------------------------------------------------------------------------
from solarpros.schemas.owner import OwnerRead  # noqa: E402
from solarpros.schemas.score import ProspectScoreRead  # noqa: E402
from solarpros.schemas.solar import SolarAnalysisRead  # noqa: E402

PropertyDetail.model_rebuild()
