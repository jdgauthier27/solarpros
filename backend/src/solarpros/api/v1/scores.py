"""Prospect score listing and distribution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import ProspectScore
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


@router.get("/", response_model=list[ProspectScoreRead])
async def list_scores(
    tier: str | None = Query(None),
    min_score: float | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ProspectScoreRead]:
    """List scored prospects with optional tier and min_score filters."""
    stmt = select(ProspectScore)

    if tier:
        stmt = stmt.where(ProspectScore.tier == tier)
    if min_score is not None:
        stmt = stmt.where(ProspectScore.composite_score >= min_score)

    stmt = stmt.order_by(ProspectScore.composite_score.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)

    return [ProspectScoreRead.model_validate(s) for s in result.scalars().all()]
