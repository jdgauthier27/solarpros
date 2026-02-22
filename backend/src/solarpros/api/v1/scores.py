"""Prospect score listing and distribution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import Owner, Property, ProspectScore, SolarAnalysis
from solarpros.schemas import ProspectScoreRead, ScoreDistribution

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/distribution", response_model=list[ScoreDistribution])
async def get_score_distribution(
    db: AsyncSession = Depends(get_db),
) -> list[ScoreDistribution]:
    """Return score distribution as histogram buckets (0-10, 10-20, ..., 90-100)."""
    buckets: list[ScoreDistribution] = []
    bucket_ranges = [
        (0, 10),
        (10, 20),
        (20, 30),
        (30, 40),
        (40, 50),
        (50, 60),
        (60, 70),
        (70, 80),
        (80, 90),
        (90, 100),
    ]

    # Build a CASE expression to assign each score to a bucket label
    whens = []
    for low, high in bucket_ranges:
        if high == 100:
            # Include 100 in the last bucket
            whens.append(
                (
                    (ProspectScore.composite_score >= low)
                    & (ProspectScore.composite_score <= high),
                    f"{low}-{high}",
                )
            )
        else:
            whens.append(
                (
                    (ProspectScore.composite_score >= low)
                    & (ProspectScore.composite_score < high),
                    f"{low}-{high}",
                )
            )

    bucket_label = case(*whens, else_="unknown").label("bucket")

    stmt = (
        select(bucket_label, func.count().label("count"))
        .group_by(bucket_label)
    )
    result = await db.execute(stmt)
    db_buckets = {row.bucket: row.count for row in result.all()}

    # Return all buckets, filling in zero for any missing
    for low, high in bucket_ranges:
        label = f"{low}-{high}"
        buckets.append(ScoreDistribution(bucket=label, count=db_buckets.get(label, 0)))

    return buckets


@router.get("/", response_model=list[dict])
async def list_scores(
    tier: str | None = Query(None),
    min_score: float | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List scored prospects with property/owner context."""
    stmt = (
        select(ProspectScore, Property, Owner, SolarAnalysis)
        .join(Property, Property.id == ProspectScore.property_id)
        .outerjoin(Owner, Owner.id == ProspectScore.owner_id)
        .outerjoin(SolarAnalysis, SolarAnalysis.id == ProspectScore.solar_analysis_id)
    )

    if tier:
        stmt = stmt.where(ProspectScore.tier == tier)
    if min_score is not None:
        stmt = stmt.where(ProspectScore.composite_score >= min_score)

    stmt = stmt.order_by(ProspectScore.composite_score.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)

    rows = []
    for score, prop, owner, solar in result.all():
        rows.append({
            "id": str(score.id),
            "property_id": str(score.property_id),
            "address": prop.address,
            "city": prop.city,
            "county": prop.county,
            "building_type": prop.building_type,
            "roof_sqft": prop.roof_sqft,
            "year_built": prop.year_built,
            "owner_name": owner.owner_name_clean if owner else prop.owner_name_raw,
            "entity_type": owner.entity_type if owner else None,
            "contact_name": owner.officer_name if owner else None,
            "contact_title": owner.contact_title if owner else None,
            "email": owner.email if owner else None,
            "email_verified": owner.email_verified if owner else False,
            "phone": owner.phone if owner else None,
            "contacts": owner.contacts if owner else None,
            "system_size_kw": round(solar.system_size_kw, 1) if solar else None,
            "annual_savings": round(solar.annual_savings) if solar else None,
            "payback_years": round(solar.payback_years, 1) if solar else None,
            "composite_score": round(score.composite_score, 1),
            "tier": score.tier,
            "solar_potential_score": round(score.solar_potential_score),
            "roof_size_score": round(score.roof_size_score),
            "savings_score": round(score.savings_score),
            "utility_zone_score": round(score.utility_zone_score),
            "owner_type_score": round(score.owner_type_score),
            "contact_quality_score": round(score.contact_quality_score),
            "building_age_score": round(score.building_age_score),
        })
    return rows
