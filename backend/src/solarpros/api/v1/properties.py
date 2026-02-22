"""Property listing, detail, map, and stats endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from solarpros.db.session import get_db
from solarpros.models import Owner, Property, ProspectScore, SolarAnalysis
from solarpros.schemas import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    PropertyDetail,
    PropertyRead,
    PropertyStats,
)

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/map", response_model=GeoJSONFeatureCollection)
async def get_properties_map(
    county: str | None = Query(None),
    tier: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> GeoJSONFeatureCollection:
    """Return a GeoJSON FeatureCollection of properties with lat/lng."""
    stmt = (
        select(Property, ProspectScore, Owner, SolarAnalysis)
        .outerjoin(ProspectScore, ProspectScore.property_id == Property.id)
        .outerjoin(Owner, Owner.property_id == Property.id)
        .outerjoin(SolarAnalysis, SolarAnalysis.property_id == Property.id)
        .where(
            Property.latitude.isnot(None),
            Property.longitude.isnot(None),
        )
    )

    if county:
        stmt = stmt.where(Property.county == county)

    if tier:
        stmt = stmt.where(ProspectScore.tier == tier)

    result = await db.execute(stmt)
    rows = result.all()

    features: list[GeoJSONFeature] = []
    for prop, score, owner, solar in rows:
        feature = GeoJSONFeature(
            geometry={
                "type": "Point",
                "coordinates": [prop.longitude, prop.latitude],
            },
            properties={
                "id": str(prop.id),
                "apn": prop.apn,
                "county": prop.county,
                "address": prop.address,
                "is_commercial": prop.is_commercial,
                "roof_sqft": prop.roof_sqft,
                "tier": score.tier if score else None,
                "score": round(score.composite_score, 1) if score else None,
                "owner_name": owner.owner_name_clean if owner else prop.owner_name_raw,
                "system_size_kw": round(solar.system_size_kw, 1) if solar else None,
            },
        )
        features.append(feature)

    return GeoJSONFeatureCollection(features=features)


@router.get("/stats", response_model=list[PropertyStats])
async def get_property_stats(
    db: AsyncSession = Depends(get_db),
) -> list[PropertyStats]:
    """Return property count aggregates grouped by county and tier."""
    # Base county counts
    county_stmt = (
        select(Property.county, func.count(Property.id).label("count"))
        .group_by(Property.county)
        .order_by(Property.county)
    )
    county_result = await db.execute(county_stmt)
    county_rows = county_result.all()

    # Avg score per county
    avg_stmt = (
        select(
            Property.county,
            func.avg(ProspectScore.composite_score).label("avg_score"),
        )
        .join(ProspectScore, ProspectScore.property_id == Property.id, isouter=True)
        .group_by(Property.county)
    )
    avg_result = await db.execute(avg_stmt)
    avg_map: dict[str, float | None] = {
        row.county: round(row.avg_score, 2) if row.avg_score is not None else None
        for row in avg_result.all()
    }

    # Tier counts per county
    tier_stmt = (
        select(
            Property.county,
            ProspectScore.tier,
            func.count(ProspectScore.id).label("cnt"),
        )
        .join(ProspectScore, ProspectScore.property_id == Property.id)
        .group_by(Property.county, ProspectScore.tier)
    )
    tier_result = await db.execute(tier_stmt)
    tier_map: dict[str, dict[str, int]] = {}
    for row in tier_result.all():
        tier_map.setdefault(row.county, {})[row.tier] = row.cnt

    stats: list[PropertyStats] = []
    for row in county_rows:
        stats.append(
            PropertyStats(
                county=row.county,
                count=row.count,
                avg_score=avg_map.get(row.county),
                tier_counts=tier_map.get(row.county, {}),
            )
        )

    return stats


@router.get("/", response_model=list[PropertyRead])
async def list_properties(
    county: str | None = Query(None),
    is_commercial: bool | None = Query(None),
    min_roof_sqft: float | None = Query(None),
    tier: str | None = Query(None),
    min_score: float | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[PropertyRead]:
    """List properties with optional filters."""
    stmt = select(Property)

    if county:
        stmt = stmt.where(Property.county == county)
    if is_commercial is not None:
        stmt = stmt.where(Property.is_commercial == is_commercial)
    if min_roof_sqft is not None:
        stmt = stmt.where(Property.roof_sqft >= min_roof_sqft)

    # Tier / score filters require a join to prospect_scores
    if tier or min_score is not None:
        stmt = stmt.join(ProspectScore, ProspectScore.property_id == Property.id)
        if tier:
            stmt = stmt.where(ProspectScore.tier == tier)
        if min_score is not None:
            stmt = stmt.where(ProspectScore.composite_score >= min_score)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [PropertyRead.model_validate(p) for p in result.scalars().all()]


@router.get("/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    """Get property detail by UUID with owners, solar analyses, and scores."""
    stmt = (
        select(Property)
        .where(Property.id == property_id)
        .options(
            selectinload(Property.owners),
            selectinload(Property.solar_analyses),
            selectinload(Property.scores),
        )
    )
    result = await db.execute(stmt)
    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")

    return PropertyDetail.model_validate(prop)
