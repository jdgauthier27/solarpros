"""Owner lookup and opt-out endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import Owner
from solarpros.schemas import OwnerRead

router = APIRouter(prefix="/owners", tags=["owners"])


@router.get("/{owner_id}", response_model=OwnerRead)
async def get_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OwnerRead:
    """Get owner detail by UUID."""
    stmt = select(Owner).where(Owner.id == owner_id)
    result = await db.execute(stmt)
    owner = result.scalar_one_or_none()

    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")

    return OwnerRead.model_validate(owner)


@router.post("/{owner_id}/opt-out")
async def opt_out_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark an owner as opted out."""
    stmt = select(Owner).where(Owner.id == owner_id)
    result = await db.execute(stmt)
    owner = result.scalar_one_or_none()

    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")

    owner.opted_out = True
    db.add(owner)
    await db.flush()

    return {"status": "opted_out"}
