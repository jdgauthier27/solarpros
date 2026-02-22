from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """Configurable weights for the 7 scoring components. Must sum to 1.0."""

    solar_potential: float = 0.25
    roof_size: float = 0.20
    savings: float = 0.20
    utility_zone: float = 0.10
    owner_type: float = 0.10
    contact_quality: float = 0.10
    building_age: float = 0.05

    def __post_init__(self) -> None:
        total = (
            self.solar_potential
            + self.roof_size
            + self.savings
            + self.utility_zone
            + self.owner_type
            + self.contact_quality
            + self.building_age
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Scoring weights must sum to 1.0 (got {total:.4f})"
            )

    def to_dict(self) -> dict[str, float]:
        return {
            "solar_potential": self.solar_potential,
            "roof_size": self.roof_size,
            "savings": self.savings,
            "utility_zone": self.utility_zone,
            "owner_type": self.owner_type,
            "contact_quality": self.contact_quality,
            "building_age": self.building_age,
        }


DEFAULT_WEIGHTS = ScoringWeights()
