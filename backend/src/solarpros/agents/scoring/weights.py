from dataclasses import dataclass, fields


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
        total = sum(getattr(self, f.name) for f in fields(self))
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Scoring weights must sum to 1.0 (got {total:.4f})"
            )

    def to_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class ScoringWeightsV2:
    """V2 weights with 10 scoring dimensions. Must sum to 1.0."""

    solar_potential: float = 0.18
    roof_size: float = 0.12
    savings: float = 0.15
    utility_zone: float = 0.06
    owner_type: float = 0.06
    contact_quality: float = 0.08
    building_age: float = 0.05
    trigger_event: float = 0.15
    contact_depth: float = 0.08
    decision_maker_quality: float = 0.07

    def __post_init__(self) -> None:
        total = sum(getattr(self, f.name) for f in fields(self))
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"ScoringWeightsV2 must sum to 1.0 (got {total:.4f})"
            )

    def to_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


DEFAULT_WEIGHTS = ScoringWeights()
DEFAULT_WEIGHTS_V2 = ScoringWeightsV2()
