import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("apn", "county", name="uq_properties_apn_county"),
        Index("ix_properties_location", "location", postgresql_using="gist"),
        Index("ix_properties_county", "county"),
        Index("ix_properties_is_commercial", "is_commercial"),
    )

    apn: Mapped[str] = mapped_column(String(50), nullable=False)
    county: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2), default="CA")
    zip_code: Mapped[str | None] = mapped_column(String(10))
    location = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    zoning: Mapped[str | None] = mapped_column(String(50))
    building_type: Mapped[str | None] = mapped_column(String(100))
    building_sqft: Mapped[float | None] = mapped_column(Float)
    roof_sqft: Mapped[float | None] = mapped_column(Float)
    year_built: Mapped[int | None] = mapped_column(Integer)
    owner_name_raw: Mapped[str | None] = mapped_column(String(500))

    is_commercial: Mapped[bool] = mapped_column(Boolean, default=False)
    meets_roof_min: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    owners: Mapped[list["Owner"]] = relationship(back_populates="property", lazy="selectin")
    solar_analyses: Mapped[list["SolarAnalysis"]] = relationship(
        back_populates="property", lazy="selectin"
    )
    scores: Mapped[list["ProspectScore"]] = relationship(
        back_populates="property", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Property {self.apn} @ {self.county}>"


# Avoid circular imports
from solarpros.models.owner import Owner  # noqa: E402
from solarpros.models.score import ProspectScore  # noqa: E402
from solarpros.models.solar_analysis import SolarAnalysis  # noqa: E402
