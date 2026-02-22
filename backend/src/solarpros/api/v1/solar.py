"""Solar analysis endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import SolarAnalysis
from solarpros.schemas import SolarAnalysisRead

router = APIRouter(prefix="/solar", tags=["solar"])


@router.get("/{property_id}", response_model=SolarAnalysisRead)
async def get_solar_analysis(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SolarAnalysisRead:
    """Get solar analysis for a property. Returns the most recent analysis."""
    stmt = (
        select(SolarAnalysis)
        .where(SolarAnalysis.property_id == property_id)
        .order_by(SolarAnalysis.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(status_code=404, detail="Solar analysis not found for this property")

    return SolarAnalysisRead.model_validate(analysis)
