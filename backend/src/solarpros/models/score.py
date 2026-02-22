import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class ProspectScore(Base):
    __tablename__ = "prospect_scores"
    __table_args__ = (
        UniqueConstraint("property_id", "scoring_version", name="uq_score_property_version"),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="SET NULL")
    )
    solar_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("solar_analyses.id", ondelete="SET NULL")
    )

    # 7 component scores (0-100)
    solar_potential_score: Mapped[float] = mapped_column(Float, default=0.0)
    roof_size_score: Mapped[float] = mapped_column(Float, default=0.0)
    savings_score: Mapped[float] = mapped_column(Float, default=0.0)
    utility_zone_score: Mapped[float] = mapped_column(Float, default=0.0)
    owner_type_score: Mapped[float] = mapped_column(Float, default=0.0)
    contact_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    building_age_score: Mapped[float] = mapped_column(Float, default=0.0)

    # V2: 3 new scoring dimensions
    trigger_event_score: Mapped[float] = mapped_column(Float, default=0.0)
    contact_depth_score: Mapped[float] = mapped_column(Float, default=0.0)
    decision_maker_quality_score: Mapped[float] = mapped_column(Float, default=0.0)

    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    tier: Mapped[str] = mapped_column(String(1), default="C")  # A, B, C
    scoring_version: Mapped[int] = mapped_column(Integer, default=1)
    weight_config: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    property: Mapped["Property"] = relationship(back_populates="scores")
    owner: Mapped["Owner | None"] = relationship(back_populates="scores")
    solar_analysis: Mapped["SolarAnalysis | None"] = relationship()

    def __repr__(self) -> str:
        return f"<ProspectScore {self.composite_score:.1f} ({self.tier})>"


from solarpros.models.owner import Owner  # noqa: E402
from solarpros.models.property import Property  # noqa: E402
from solarpros.models.solar_analysis import SolarAnalysis  # noqa: E402
