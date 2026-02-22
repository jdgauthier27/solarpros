"""Request/response schemas for owner endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


class OwnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    owner_name_clean: str
    entity_type: str | None = None
    sos_entity_name: str | None = None
    sos_entity_number: str | None = None
    officer_name: str | None = None
    email: str | None = None
    email_verified: bool = False
    phone: str | None = None
    mailing_address: str | None = None
    confidence_score: float = 0.0
    confidence_factors: dict[str, Any] | None = None
    opted_out: bool = False
    created_at: datetime
    updated_at: datetime


class OptOutRequest(BaseModel):
    email: EmailStr
