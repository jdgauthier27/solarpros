import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class SolarAnalysis(Base):
    __tablename__ = "solar_analyses"
    __table_args__ = (
        UniqueConstraint("property_id", "data_source", name="uq_solar_property_source"),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )

    data_source: Mapped[str] = mapped_column(String(50), nullable=False)  # google_solar, pvwatts
    usable_roof_sqft: Mapped[float | None] = mapped_column(Float)
    pitch: Mapped[float | None] = mapped_column(Float)
    azimuth: Mapped[float | None] = mapped_column(Float)
    sunshine_hours: Mapped[float | None] = mapped_column(Float)
    system_size_kw: Mapped[float | None] = mapped_column(Float)
    annual_kwh: Mapped[float | None] = mapped_column(Float)

    utility_rate: Mapped[float | None] = mapped_column(Float)  # $/kWh
    annual_savings: Mapped[float | None] = mapped_column(Float)
    system_cost: Mapped[float | None] = mapped_column(Float)
    net_cost: Mapped[float | None] = mapped_column(Float)  # after ITC
    payback_years: Mapped[float | None] = mapped_column(Float)

    raw_response: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    property: Mapped["Property"] = relationship(back_populates="solar_analyses")

    def __repr__(self) -> str:
        return f"<SolarAnalysis {self.data_source} for {self.property_id}>"


from solarpros.models.property import Property  # noqa: E402
