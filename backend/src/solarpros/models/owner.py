import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class Owner(Base):
    __tablename__ = "owners"
    __table_args__ = (
        Index(
            "ix_owners_name_trgm",
            "owner_name_clean",
            postgresql_using="gin",
            postgresql_ops={"owner_name_clean": "gin_trgm_ops"},
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    owner_name_clean: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))  # Corp, LLC, Individual, Trust
    sos_entity_name: Mapped[str | None] = mapped_column(String(500))
    sos_entity_number: Mapped[str | None] = mapped_column(String(50))
    officer_name: Mapped[str | None] = mapped_column(String(500))
    contact_title: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    mailing_address: Mapped[str | None] = mapped_column(Text)
    contacts: Mapped[list | None] = mapped_column(JSONB)  # All officers/contacts from SOS

    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_factors: Mapped[dict | None] = mapped_column(JSONB)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    property: Mapped["Property"] = relationship(back_populates="owners")
    scores: Mapped[list["ProspectScore"]] = relationship(back_populates="owner", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Owner {self.owner_name_clean}>"


from solarpros.models.property import Property  # noqa: E402
from solarpros.models.score import ProspectScore  # noqa: E402
