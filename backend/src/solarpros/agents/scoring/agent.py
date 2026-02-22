from datetime import UTC, datetime

from sqlalchemy import func, select

from solarpros.agents.base import BaseAgent
from solarpros.agents.scoring.segmentation import assign_tier
from solarpros.agents.scoring.weights import DEFAULT_WEIGHTS, DEFAULT_WEIGHTS_V2, ScoringWeights, ScoringWeightsV2
from solarpros.agents.trigger_events.agent import EVENT_BASE_SCORES, compute_recency_decay
from solarpros.db.session import async_session_factory
from solarpros.models.contact import Contact
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.score import ProspectScore
from solarpros.models.solar_analysis import SolarAnalysis
from solarpros.models.trigger_event import TriggerEvent

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

BUYING_ROLE_SCORES: dict[str, float] = {
    "economic_buyer": 40.0,
    "champion": 30.0,
    "technical_evaluator": 20.0,
    "financial_evaluator": 10.0,
    "influencer": 5.0,
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


# --- V2 scoring functions ---


def score_trigger_event(trigger_events: list) -> float:
    """Score based on the best trigger event (base score * recency decay).

    Takes the highest-scoring trigger event after applying recency decay.
    Returns 0-100.
    """
    if not trigger_events:
        return 0.0

    best_score = 0.0
    for event in trigger_events:
        base = EVENT_BASE_SCORES.get(event.event_type, 50.0)
        decay = compute_recency_decay(event.event_date)
        score = base * decay
        best_score = max(best_score, score)

    return min(best_score, 100.0)


def score_contact_depth(contact_count: int) -> float:
    """Score based on number of contacts discovered.

    0 contacts = 0, 1 = 30, 2 = 60, 3 = 80, 4+ = 100.
    """
    if contact_count == 0:
        return 0.0
    if contact_count == 1:
        return 30.0
    if contact_count == 2:
        return 60.0
    if contact_count == 3:
        return 80.0
    return 100.0


def score_decision_maker_quality(contacts: list) -> float:
    """Score based on the buying roles of discovered contacts.

    Sums role scores: economic_buyer=40, champion=30, tech=20, finance=10.
    Capped at 100.
    """
    if not contacts:
        return 0.0

    total = 0.0
    for contact in contacts:
        role = contact.buying_role if hasattr(contact, "buying_role") else contact.get("buying_role")
        total += BUYING_ROLE_SCORES.get(role, 0.0)

    return min(total, 100.0)


def compute_composite(components: dict[str, float], weights: ScoringWeights | ScoringWeightsV2) -> float:
    """Compute the weighted composite score from individual component scores."""
    weight_map = weights.to_dict()
    return sum(components.get(key, 0.0) * weight_map[key] for key in weight_map)


class ScoringAgent(BaseAgent):
    agent_type: str = "scoring"

    async def execute(self, **kwargs) -> dict:
        property_id = kwargs["property_id"]
        use_v2 = kwargs.get("use_v2", True)
        weights = DEFAULT_WEIGHTS_V2 if use_v2 else DEFAULT_WEIGHTS

        self.log.info("scoring_property", property_id=str(property_id), version=2 if use_v2 else 1)

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

            # Compute the 7 base scores
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

            # V2: compute 3 additional scores
            trigger_score = 0.0
            contact_depth = 0.0
            dm_quality = 0.0

            if use_v2:
                # Load trigger events
                result = await session.execute(
                    select(TriggerEvent).where(TriggerEvent.property_id == property_id)
                )
                triggers = list(result.scalars().all())
                trigger_score = score_trigger_event(triggers)

                # Load contacts (from all owners of this property)
                contacts = []
                if owner:
                    result = await session.execute(
                        select(Contact).where(Contact.owner_id == owner.id)
                    )
                    contacts = list(result.scalars().all())

                contact_depth = score_contact_depth(len(contacts))
                dm_quality = score_decision_maker_quality(contacts)

                components["trigger_event"] = trigger_score
                components["contact_depth"] = contact_depth
                components["decision_maker_quality"] = dm_quality

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
                trigger_event_score=trigger_score,
                contact_depth_score=contact_depth,
                decision_maker_quality_score=dm_quality,
                composite_score=composite,
                tier=tier,
                scoring_version=2 if use_v2 else 1,
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
            version=2 if use_v2 else 1,
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
