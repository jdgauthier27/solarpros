import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class Contact(Base):
    """Individual stakeholder contact (1-5 per owner/property)."""

    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_owner_id", "owner_id"),
        Index("ix_contacts_email", "email"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="CASCADE"), nullable=False
    )

    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(200))
    last_name: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(300))
    buying_role: Mapped[str | None] = mapped_column(
        String(50)
    )  # economic_buyer / champion / technical_evaluator / financial_evaluator / influencer

    email: Mapped[str | None] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_source: Mapped[str | None] = mapped_column(
        String(50)
    )  # apollo / hunter / google_search / sos

    phone: Mapped[str | None] = mapped_column(String(20))
    phone_type: Mapped[str | None] = mapped_column(String(20))  # direct / mobile / office
    phone_source: Mapped[str | None] = mapped_column(String(50))

    linkedin_url: Mapped[str | None] = mapped_column(String(500))

    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    enrichment_sources: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    owner: Mapped["Owner"] = relationship(back_populates="contact_records")

    def __repr__(self) -> str:
        return f"<Contact {self.full_name} ({self.buying_role})>"


from solarpros.models.owner import Owner  # noqa: E402
