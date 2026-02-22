import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class TriggerEvent(Base):
    """Timing signal indicating a property is ready for solar."""

    __tablename__ = "trigger_events"
    __table_args__ = (
        Index("ix_trigger_events_property_id", "property_id"),
        Index("ix_trigger_events_owner_id", "owner_id"),
        Index("ix_trigger_events_event_type", "event_type"),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="SET NULL")
    )

    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # roof_replacement / hvac_permit / sustainability_hire / leadership_change / etc
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # city_permits / indeed_jobs / google_news / manual
    source_url: Mapped[str | None] = mapped_column(String(1000))

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    property: Mapped["Property"] = relationship()
    owner: Mapped["Owner | None"] = relationship()

    def __repr__(self) -> str:
        return f"<TriggerEvent {self.event_type}: {self.title}>"


from solarpros.models.owner import Owner  # noqa: E402
from solarpros.models.property import Property  # noqa: E402
