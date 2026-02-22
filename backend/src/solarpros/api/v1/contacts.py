"""Contact CRUD + search endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models.contact import Contact

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    owner_id: uuid.UUID
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    buying_role: str | None = None
    email: str | None = None
    email_verified: bool = False
    email_source: str | None = None
    phone: str | None = None
    phone_type: str | None = None
    phone_source: str | None = None
    linkedin_url: str | None = None
    confidence_score: float = 0.0
    is_primary: bool = False
    opted_out: bool = False
    enrichment_sources: dict | None = None
    created_at: str | None = None


@router.get("/", response_model=list[ContactRead])
async def list_contacts(
    owner_id: uuid.UUID | None = Query(None),
    buying_role: str | None = Query(None),
    has_email: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[ContactRead]:
    """List contacts with optional filters."""
    stmt = select(Contact)

    if owner_id:
        stmt = stmt.where(Contact.owner_id == owner_id)
    if buying_role:
        stmt = stmt.where(Contact.buying_role == buying_role)
    if has_email is True:
        stmt = stmt.where(Contact.email.isnot(None))
    if has_email is False:
        stmt = stmt.where(Contact.email.is_(None))

    stmt = stmt.order_by(Contact.is_primary.desc(), Contact.confidence_score.desc())
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [ContactRead.model_validate(c) for c in result.scalars().all()]


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContactRead:
    """Get a single contact by ID."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactRead.model_validate(contact)


class ContactOptOut(BaseModel):
    opted_out: bool = True


@router.post("/{contact_id}/opt-out", response_model=ContactRead)
async def opt_out_contact(
    contact_id: uuid.UUID,
    payload: ContactOptOut,
    db: AsyncSession = Depends(get_db),
) -> ContactRead:
    """Opt a contact out of outreach."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.opted_out = payload.opted_out
    await db.flush()
    await db.refresh(contact)
    return ContactRead.model_validate(contact)
