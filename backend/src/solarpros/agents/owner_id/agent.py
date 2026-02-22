"""Owner Identification Agent.

Takes a property record, resolves the raw assessor owner name to a
clean entity, looks up the entity on the CA Secretary of State,
attempts to find and verify an email via Hunter.io, and computes an
overall confidence score.  The resolved owner is persisted to the
database.
"""

from __future__ import annotations

import re
import uuid

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.agents.owner_id.confidence import ContactConfidenceScorer
from solarpros.agents.owner_id.hunter_io import (
    BaseHunterIOClient,
    HunterIOClient,
    MockHunterIOClient,
)
from solarpros.agents.owner_id.sos_lookup import (
    BaseSOSLookupClient,
    MockSOSLookupClient,
    SOSLookupClient,
)
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.owner import Owner
from solarpros.models.property import Property

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Structured output schema for LangChain entity resolution
# ---------------------------------------------------------------------------


class ResolvedEntity(BaseModel):
    """Structured output from the LLM entity resolution step."""

    clean_name: str = Field(
        description="The cleaned, normalized entity or person name."
    )
    entity_type: str = Field(
        description=(
            "The guessed entity type: one of 'Corp', 'LLC', 'LP', "
            "'Trust', 'Individual', or 'Unknown'."
        )
    )
    is_business: bool = Field(
        description="True if this appears to be a business entity, False if individual."
    )
    domain_guess: str | None = Field(
        default=None,
        description=(
            "A plausible website domain for the entity (e.g. 'acmecorp.com'), "
            "or null if not guessable."
        ),
    )


# ---------------------------------------------------------------------------
# LangChain prompt
# ---------------------------------------------------------------------------

_ENTITY_RESOLUTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a data-cleaning assistant specialising in California "
                "commercial real-estate records. Your job is to take a raw owner "
                "name as recorded by a county assessor and produce:\n"
                "1. A clean, properly capitalised version of the name.\n"
                "2. The most likely entity type (Corp, LLC, LP, Trust, Individual, Unknown).\n"
                "3. Whether this is a business entity (true) or an individual person (false).\n"
                "4. If it is a business, guess a plausible website domain (lowercase, no www). "
                "If you cannot guess, return null.\n\n"
                "Common patterns:\n"
                "- 'SMITH JOHN & MARY' -> Individual, 'John & Mary Smith'\n"
                "- 'ACME PROPERTIES LLC' -> LLC, 'Acme Properties LLC', 'acmeproperties.com'\n"
                "- 'CHEN FAMILY TRUST DTD 01/15/2010' -> Trust, 'Chen Family Trust'\n"
                "- 'J & R INVESTMENTS INC C/O JONES' -> Corp, 'J & R Investments Inc'\n"
                "Do not include suffixes like 'C/O ...', 'ET AL', 'TR', or dates."
            ),
        ),
        ("human", "Raw owner name from assessor records: {raw_name}"),
    ]
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class OwnerIDAgent(BaseAgent):
    """Agent that identifies and resolves property owners."""

    agent_type: str = "owner_id"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.scorer = ContactConfidenceScorer()

        # Select real or mock clients based on config
        if settings.use_mock_apis:
            self.sos_client: BaseSOSLookupClient = MockSOSLookupClient()
            self.hunter_client: BaseHunterIOClient = MockHunterIOClient()
        else:
            self.sos_client = SOSLookupClient()
            self.hunter_client = HunterIOClient()

    # ----- LLM entity resolution -----

    async def _resolve_entity(self, raw_name: str) -> ResolvedEntity:
        """Clean and classify the raw owner name.

        Uses LangChain + Claude when real APIs are enabled, otherwise
        falls back to a simple heuristic-based mock resolver.
        """
        if settings.use_mock_apis:
            return self._mock_resolve_entity(raw_name)

        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=512,
        )

        structured_llm = llm.with_structured_output(ResolvedEntity)
        chain = _ENTITY_RESOLUTION_PROMPT | structured_llm

        result = await chain.ainvoke({"raw_name": raw_name})
        logger.info(
            "entity_resolved",
            raw_name=raw_name,
            clean_name=result.clean_name,
            entity_type=result.entity_type,
            is_business=result.is_business,
        )
        return result

    @staticmethod
    def _mock_resolve_entity(raw_name: str) -> ResolvedEntity:
        """Heuristic-based entity resolution for mock/dev mode."""
        name_upper = raw_name.upper()

        # Detect entity type from common suffixes
        is_business = False
        entity_type = "Individual"
        domain_guess = None

        if "LLC" in name_upper:
            entity_type = "LLC"
            is_business = True
        elif "INC" in name_upper or "CORP" in name_upper:
            entity_type = "Corp"
            is_business = True
        elif "LP" in name_upper or "PARTNERS" in name_upper:
            entity_type = "LP"
            is_business = True
        elif "TRUST" in name_upper:
            entity_type = "Trust"
            is_business = False
        elif any(kw in name_upper for kw in ("PROPERTIES", "HOLDINGS", "INVESTMENTS", "REALTY", "GROUP", "CAPITAL", "ENTERPRISES", "VENTURES")):
            entity_type = "LLC"
            is_business = True

        # Clean name: title case, strip common noise
        clean_name = raw_name.strip()
        for noise in (" C/O ", " ET AL", " TR ", " DTD "):
            idx = clean_name.upper().find(noise)
            if idx != -1:
                clean_name = clean_name[:idx]
        clean_name = clean_name.strip().title()

        # Domain guess for businesses
        if is_business:
            slug = re.sub(r"[^a-z0-9]", "", clean_name.lower().replace("llc", "").replace("inc", "").replace("corp", "").replace("lp", ""))
            if slug:
                domain_guess = f"{slug}.com"

        logger.info(
            "entity_resolved_mock",
            raw_name=raw_name,
            clean_name=clean_name,
            entity_type=entity_type,
            is_business=is_business,
        )

        return ResolvedEntity(
            clean_name=clean_name,
            entity_type=entity_type,
            is_business=is_business,
            domain_guess=domain_guess,
        )

    # ----- Name matching helper -----

    @staticmethod
    def _compute_name_match(raw_name: str, sos_entity_name: str | None) -> float:
        """Compare the raw assessor name against the SOS entity name.

        Returns a score between 0.0 and 1.0.
        """
        if not sos_entity_name:
            return ContactConfidenceScorer.NAME_MATCH_NONE

        raw_tokens = set(re.sub(r"[^a-z0-9\s]", "", raw_name.lower()).split())
        sos_tokens = set(
            re.sub(r"[^a-z0-9\s]", "", sos_entity_name.lower()).split()
        )

        # Remove common noise words for comparison
        noise = {"llc", "inc", "corp", "lp", "the", "of", "and", "co", "ltd"}
        raw_clean = raw_tokens - noise
        sos_clean = sos_tokens - noise

        if not raw_clean or not sos_clean:
            return ContactConfidenceScorer.NAME_MATCH_PARTIAL

        # Exact match (ignoring noise words)
        if raw_clean == sos_clean:
            return ContactConfidenceScorer.NAME_MATCH_EXACT

        # Close match: one is a subset of the other or high overlap
        intersection = raw_clean & sos_clean
        union = raw_clean | sos_clean
        jaccard = len(intersection) / len(union) if union else 0.0

        if jaccard >= 0.7:
            return ContactConfidenceScorer.NAME_MATCH_CLOSE
        if jaccard >= 0.3:
            return ContactConfidenceScorer.NAME_MATCH_PARTIAL

        return ContactConfidenceScorer.NAME_MATCH_NONE

    # ----- Main execute -----

    async def execute(self, **kwargs) -> dict:
        """Execute the owner identification pipeline for a single property.

        Parameters
        ----------
        property_id : str
            UUID of the property to identify the owner for.

        Returns
        -------
        dict
            Result summary with keys: property_id, owner_id, clean_name,
            entity_type, confidence_score, items_processed, items_failed.
        """
        property_id = kwargs.get("property_id")
        if not property_id:
            raise ValueError("property_id is required")

        property_uuid = uuid.UUID(str(property_id))

        self.log.info("owner_id_start", property_id=str(property_uuid))

        # 1. Load property from DB
        async with async_session_factory() as session:
            result = await session.execute(
                select(Property).where(Property.id == property_uuid)
            )
            prop = result.scalar_one_or_none()

        if not prop:
            raise ValueError(f"Property {property_uuid} not found")

        raw_name = prop.owner_name_raw
        if not raw_name:
            raise ValueError(
                f"Property {property_uuid} has no owner_name_raw"
            )

        # 2. Entity resolution via LangChain + Claude
        resolved = await self._resolve_entity(raw_name)

        # 3. SOS lookup (only for business entities)
        sos_result = None
        if resolved.is_business:
            sos_result = await self.sos_client.search_entity(resolved.clean_name)

        # 4. Email finder / verification via Hunter.io
        email_result = None
        email_verified = False
        verification_result = None

        if resolved.domain_guess:
            # Try to extract first/last name for the finder
            first_name, last_name = self._extract_contact_name(
                sos_result, resolved
            )
            if first_name and last_name:
                email_result = await self.hunter_client.find_email(
                    domain=resolved.domain_guess,
                    first_name=first_name,
                    last_name=last_name,
                )

            if email_result and email_result.get("email"):
                verification_result = await self.hunter_client.verify_email(
                    email_result["email"]
                )
                email_verified = (
                    verification_result.get("status") == "valid"
                    and verification_result.get("score", 0) >= 80
                )

        # 5. Compute confidence score
        sos_entity_name = sos_result["entity_name"] if sos_result else None
        name_match_score = self._compute_name_match(raw_name, sos_entity_name)

        sos_status_score = ContactConfidenceScorer.SOS_NOT_FOUND
        if sos_result:
            status = sos_result.get("status", "").lower()
            if status == "active":
                sos_status_score = ContactConfidenceScorer.SOS_ACTIVE
            else:
                sos_status_score = ContactConfidenceScorer.SOS_INACTIVE

        email_quality_score = ContactConfidenceScorer.EMAIL_NOT_FOUND
        if email_verified:
            email_quality_score = ContactConfidenceScorer.EMAIL_VERIFIED
        elif email_result and email_result.get("email"):
            email_quality_score = ContactConfidenceScorer.EMAIL_FOUND_UNVERIFIED

        # Phone from SOS result
        phone = sos_result.get("agent_phone") if sos_result else None
        phone_quality_score = (
            ContactConfidenceScorer.PHONE_DIRECT
            if phone
            else ContactConfidenceScorer.PHONE_NOT_FOUND
        )

        confidence_score, confidence_factors = self.scorer.compute(
            {
                "name_match": name_match_score,
                "sos_status": sos_status_score,
                "email_quality": email_quality_score,
                "phone_quality": phone_quality_score,
            }
        )

        # 6. Save Owner to DB
        owner_email = (
            email_result["email"]
            if email_result and email_result.get("email")
            else None
        )

        # Build contacts list from SOS officers + Hunter position info
        contacts_list = None
        if sos_result and sos_result.get("officers"):
            contacts_list = []
            for officer in sos_result["officers"]:
                contact = {
                    "name": officer.get("name"),
                    "title": officer.get("title"),
                    "phone": officer.get("phone"),
                    "address": officer.get("address"),
                }
                # Attach email to matching contact
                if (
                    owner_email
                    and officer.get("name")
                    and sos_result.get("agent_name")
                    and officer["name"] == sos_result["agent_name"]
                ):
                    contact["email"] = owner_email
                    if email_result and email_result.get("position"):
                        contact["title"] = email_result["position"]
                contacts_list.append(contact)

        # Primary contact title from SOS or Hunter
        contact_title = None
        if sos_result and sos_result.get("agent_title"):
            contact_title = sos_result["agent_title"]
        elif email_result and email_result.get("position"):
            contact_title = email_result["position"]

        async with async_session_factory() as session:
            owner = Owner(
                property_id=property_uuid,
                owner_name_clean=resolved.clean_name,
                entity_type=resolved.entity_type,
                sos_entity_name=sos_result["entity_name"] if sos_result else None,
                sos_entity_number=sos_result["entity_number"] if sos_result else None,
                officer_name=sos_result.get("agent_name") if sos_result else None,
                contact_title=contact_title,
                email=owner_email,
                email_verified=email_verified,
                phone=phone,
                mailing_address=(
                    sos_result.get("agent_address") if sos_result else None
                ),
                contacts=contacts_list,
                confidence_score=confidence_score,
                confidence_factors=confidence_factors,
            )
            session.add(owner)
            await session.commit()
            await session.refresh(owner)

        self.log.info(
            "owner_id_complete",
            property_id=str(property_uuid),
            owner_id=str(owner.id),
            clean_name=resolved.clean_name,
            confidence_score=confidence_score,
        )

        return {
            "property_id": str(property_uuid),
            "owner_id": str(owner.id),
            "clean_name": resolved.clean_name,
            "entity_type": resolved.entity_type,
            "sos_entity_name": sos_result["entity_name"] if sos_result else None,
            "email": owner_email,
            "email_verified": email_verified,
            "confidence_score": confidence_score,
            "confidence_factors": confidence_factors,
            "items_processed": 1,
            "items_failed": 0,
        }

    @staticmethod
    def _extract_contact_name(
        sos_result: dict | None, resolved: ResolvedEntity
    ) -> tuple[str | None, str | None]:
        """Extract a first and last name for email lookup.

        Prefers the SOS agent name; falls back to parsing the resolved
        clean name for individuals.
        """
        # Try the SOS agent name first (usually a person)
        if sos_result and sos_result.get("agent_name"):
            parts = sos_result["agent_name"].strip().split()
            if len(parts) >= 2:
                return parts[0], parts[-1]

        # For individuals, try parsing the clean name
        if not resolved.is_business:
            parts = resolved.clean_name.strip().split()
            if len(parts) >= 2:
                return parts[0], parts[-1]

        return None, None
