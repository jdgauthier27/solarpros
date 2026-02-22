from datetime import UTC, datetime

from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.agents.scoring.segmentation import assign_tier
from solarpros.agents.scoring.weights import DEFAULT_WEIGHTS, ScoringWeights
from solarpros.db.session import async_session_factory
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.score import ProspectScore
from solarpros.models.solar_analysis import SolarAnalysis

# County -> utility mapping for Southern California
COUNTY_UTILITY_MAP: dict[str, str] = {
    "San Diego": "SDGE",
    "Orange": "SCE",
    "Riverside": "SCE",
    "San Bernardino": "SCE",
    "Los Angeles": "LADWP",
    "Ventura": "SCE",
    "Imperial": "SDGE",
    "Santa Barbara": "SCE",
    "Kern": "SCE",
}

UTILITY_SCORES: dict[str, float] = {
    "SDGE": 100.0,
    "SCE": 75.0,
    "LADWP": 50.0,
}

OWNER_TYPE_SCORES: dict[str, float] = {
    "Corp": 90.0,
    "LLC": 85.0,
    "Partnership": 70.0,
    "Individual": 60.0,
    "Trust": 40.0,
}


def score_solar_potential(annual_kwh: float | None) -> float:
    """Normalize annual kWh production to a 0-100 score."""
    if annual_kwh is None:
        return 0.0
    return min(annual_kwh / 500_000 * 100, 100.0)


def score_roof_size(roof_sqft: float | None) -> float:
    """Normalize roof square footage (5K-50K range) to a 0-100 score."""
    if roof_sqft is None:
        return 0.0
    raw = (roof_sqft - 5000) / 450 * 100
    return max(0.0, min(raw, 100.0))


def score_savings(annual_savings: float | None) -> float:
    """Normalize annual savings to a 0-100 score."""
    if annual_savings is None:
        return 0.0
    return min(annual_savings / 100_000 * 100, 100.0)


def score_utility_zone(county: str) -> float:
    """Look up utility score by county."""
    utility = COUNTY_UTILITY_MAP.get(county)
    if utility is None:
        return 50.0
    return UTILITY_SCORES.get(utility, 50.0)


def score_owner_type(entity_type: str | None) -> float:
    """Score based on business entity type."""
    if entity_type is None:
        return 50.0
    return OWNER_TYPE_SCORES.get(entity_type, 50.0)


def score_contact_quality(confidence_score: float, email_verified: bool) -> float:
    """Score contact quality: confidence contributes 80 pts, verified email 20 pts."""
    return confidence_score * 80 + (20.0 if email_verified else 0.0)


def score_building_age(year_built: int | None) -> float:
    """Score based on building age. Older buildings score higher (more likely to need solar)."""
    if year_built is None:
        return 0.0
    current_year = datetime.now(UTC).year
    age = current_year - year_built
    if age >= 30:
        return 100.0
    if age >= 20:
        return 80.0
    if age >= 10:
        return 60.0
    return 40.0


def compute_composite(components: dict[str, float], weights: ScoringWeights) -> float:
    """Compute the weighted composite score from individual component scores."""
    weight_map = weights.to_dict()
    return sum(components[key] * weight_map[key] for key in weight_map)


class ScoringAgent(BaseAgent):
    agent_type: str = "scoring"

    async def execute(self, **kwargs) -> dict:
        property_id = kwargs["property_id"]
        weights = DEFAULT_WEIGHTS

        self.log.info("scoring_property", property_id=str(property_id))

        async with async_session_factory() as session:
            # Load property
            result = await session.execute(
                select(Property).where(Property.id == property_id)
            )
            prop = result.scalar_one_or_none()
            if not prop:
                raise ValueError(f"Property {property_id} not found")

            # Load primary owner (first non-opted-out owner)
            result = await session.execute(
                select(Owner)
                .where(Owner.property_id == property_id, Owner.opted_out.is_(False))
                .limit(1)
            )
            owner = result.scalar_one_or_none()

            # Load latest solar analysis
            result = await session.execute(
                select(SolarAnalysis)
                .where(SolarAnalysis.property_id == property_id)
                .order_by(SolarAnalysis.created_at.desc())
                .limit(1)
            )
            solar = result.scalar_one_or_none()

            # Compute individual scores
            components = {
                "solar_potential": score_solar_potential(
                    solar.annual_kwh if solar else None
                ),
                "roof_size": score_roof_size(prop.roof_sqft),
                "savings": score_savings(
                    solar.annual_savings if solar else None
                ),
                "utility_zone": score_utility_zone(prop.county),
                "owner_type": score_owner_type(
                    owner.entity_type if owner else None
                ),
                "contact_quality": score_contact_quality(
                    owner.confidence_score if owner else 0.0,
                    owner.email_verified if owner else False,
                ),
                "building_age": score_building_age(prop.year_built),
            }

            composite = compute_composite(components, weights)
            tier = assign_tier(composite)

            # Save ProspectScore
            prospect_score = ProspectScore(
                property_id=property_id,
                owner_id=owner.id if owner else None,
                solar_analysis_id=solar.id if solar else None,
                solar_potential_score=components["solar_potential"],
                roof_size_score=components["roof_size"],
                savings_score=components["savings"],
                utility_zone_score=components["utility_zone"],
                owner_type_score=components["owner_type"],
                contact_quality_score=components["contact_quality"],
                building_age_score=components["building_age"],
                composite_score=composite,
                tier=tier,
                scoring_version=1,
                weight_config=weights.to_dict(),
            )
            session.add(prospect_score)
            await session.commit()
            await session.refresh(prospect_score)

        self.log.info(
            "scoring_complete",
            property_id=str(property_id),
            composite_score=composite,
            tier=tier,
        )

        return {
            "items_processed": 1,
            "items_failed": 0,
            "property_id": str(property_id),
            "score_id": str(prospect_score.id),
            "components": components,
            "composite_score": composite,
            "tier": tier,
        }
