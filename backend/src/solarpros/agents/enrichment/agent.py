"""Enrichment Agent — replaces OwnerIDAgent with multi-source waterfall.

For each property:
  1. Entity resolution (Claude Haiku) — reuses existing OwnerIDAgent logic
  2. Multi-source waterfall (SOS → Places → Apollo → Hunter → Google Search)
  3. Buying role classification (Claude Haiku or heuristic)
  4. Persist: Owner (company-level) + Contact rows (1-5 per property)
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.agents.enrichment.role_classifier import classify_role_heuristic, classify_role_llm
from solarpros.agents.enrichment.waterfall import EnrichmentWaterfall
from solarpros.agents.owner_id.agent import OwnerIDAgent
from solarpros.agents.owner_id.confidence import ContactConfidenceScorer
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.contact import Contact
from solarpros.models.owner import Owner
from solarpros.models.property import Property

logger = structlog.get_logger()


class EnrichmentAgent(BaseAgent):
    """Agent that enriches property owners with multi-source contact data."""

    agent_type: str = "enrichment"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._owner_id_agent = OwnerIDAgent()  # Reuse entity resolution logic
        self.waterfall = self._build_waterfall()

    def _build_waterfall(self) -> EnrichmentWaterfall:
        """Build the enrichment waterfall with real or mock clients."""
        if settings.enrichment_use_mock:
            from solarpros.agents.enrichment.clients.mock import (
                MockApolloClient,
                MockCASOSClient,
                MockGooglePlacesClient,
                MockGoogleSearchClient,
                MockHunterIOClient,
            )
            return EnrichmentWaterfall(
                sos_client=MockCASOSClient(),
                places_client=MockGooglePlacesClient(),
                apollo_client=MockApolloClient(),
                hunter_client=MockHunterIOClient(),
                search_client=MockGoogleSearchClient(),
            )
        else:
            from solarpros.agents.enrichment.clients.apollo import ApolloClient
            from solarpros.agents.enrichment.clients.ca_sos_api import CASOSAPIClient
            from solarpros.agents.enrichment.clients.google_places import GooglePlacesClient
            from solarpros.agents.enrichment.clients.google_search import GoogleSearchClient
            from solarpros.agents.enrichment.clients.hunter_io import HunterIODomainClient
            return EnrichmentWaterfall(
                sos_client=CASOSAPIClient(),
                places_client=GooglePlacesClient(),
                apollo_client=ApolloClient(),
                hunter_client=HunterIODomainClient(),
                search_client=GoogleSearchClient(),
            )

    async def execute(self, **kwargs) -> dict:
        """Execute enrichment for a single property.

        Parameters
        ----------
        property_id : str
            UUID of the property to enrich.

        Returns
        -------
        dict
            Result summary with owner_id, contact_count, enrichment_log.
        """
        property_id = kwargs.get("property_id")
        if not property_id:
            raise ValueError("property_id is required")

        property_uuid = uuid.UUID(str(property_id))
        self.log.info("enrichment_start", property_id=str(property_uuid))

        # 1. Load property
        async with async_session_factory() as session:
            result = await session.execute(
                select(Property).where(Property.id == property_uuid)
            )
            prop = result.scalar_one_or_none()

        if not prop:
            raise ValueError(f"Property {property_uuid} not found")

        raw_name = prop.owner_name_raw
        if not raw_name:
            raise ValueError(f"Property {property_uuid} has no owner_name_raw")

        # 2. Entity resolution (reuse existing logic)
        resolved = await self._owner_id_agent._resolve_entity(raw_name)

        # 3. Run enrichment waterfall
        waterfall_result = await self.waterfall.enrich(
            clean_name=resolved.clean_name,
            entity_type=resolved.entity_type,
            is_business=resolved.is_business,
            domain_guess=resolved.domain_guess,
            city=prop.city,
        )

        company_data = waterfall_result["company"]
        raw_contacts = waterfall_result["contacts"]
        sos_result = waterfall_result["sos_result"]
        enrichment_log = waterfall_result["enrichment_log"]

        # 4. Classify buying roles for each contact
        for contact in raw_contacts:
            contact["buying_role"] = await classify_role_llm(
                contact_name=contact.get("full_name", ""),
                title=contact.get("job_title"),
                company_name=resolved.clean_name,
            )

        # 5. Compute confidence scores
        scorer = ContactConfidenceScorer()

        # Overall confidence based on best contact data
        best_email_quality = ContactConfidenceScorer.EMAIL_NOT_FOUND
        best_phone_quality = ContactConfidenceScorer.PHONE_NOT_FOUND
        for c in raw_contacts:
            if c.get("email"):
                best_email_quality = max(
                    best_email_quality,
                    ContactConfidenceScorer.EMAIL_VERIFIED if c.get("email_source") in ("apollo",) else ContactConfidenceScorer.EMAIL_FOUND_UNVERIFIED,
                )
            if c.get("phone"):
                best_phone_quality = max(best_phone_quality, ContactConfidenceScorer.PHONE_DIRECT)

        sos_entity_name = sos_result["entity_name"] if sos_result else None
        name_match = self._owner_id_agent._compute_name_match(raw_name, sos_entity_name)

        sos_status = ContactConfidenceScorer.SOS_NOT_FOUND
        if sos_result:
            status = sos_result.get("status", "").lower()
            sos_status = ContactConfidenceScorer.SOS_ACTIVE if status == "active" else ContactConfidenceScorer.SOS_INACTIVE

        owner_confidence, confidence_factors = scorer.compute({
            "name_match": name_match,
            "sos_status": sos_status,
            "email_quality": best_email_quality,
            "phone_quality": best_phone_quality,
        })

        # 6. Persist Owner + Contact records
        primary_officer = sos_result.get("agent_name") if sos_result else None
        primary_email = None
        for c in raw_contacts:
            if c.get("email"):
                primary_email = c["email"]
                break

        async with async_session_factory() as session:
            owner = Owner(
                property_id=property_uuid,
                owner_name_clean=resolved.clean_name,
                entity_type=resolved.entity_type,
                sos_entity_name=sos_entity_name,
                sos_entity_number=sos_result["entity_number"] if sos_result else None,
                officer_name=primary_officer,
                email=primary_email,
                email_verified=any(
                    c.get("email_source") == "apollo" for c in raw_contacts if c.get("email")
                ),
                phone=company_data.get("phone"),
                mailing_address=sos_result.get("agent_address") if sos_result else None,
                contacts=[
                    {"name": c.get("full_name"), "title": c.get("job_title"), "role": c.get("buying_role")}
                    for c in raw_contacts
                ],
                confidence_score=owner_confidence,
                confidence_factors=confidence_factors,
                # V2 company enrichment
                company_domain=company_data.get("domain"),
                company_website=company_data.get("website"),
                company_phone=company_data.get("phone"),
                google_place_id=company_data.get("place_id"),
                enrichment_log=enrichment_log,
            )
            session.add(owner)
            await session.flush()

            # Create Contact records (1-5 per owner)
            contact_ids = []
            for i, c in enumerate(raw_contacts[:5]):
                is_primary = i == 0 or c.get("buying_role") == "economic_buyer"
                # Compute per-contact confidence
                c_confidence = 0.5  # base
                if c.get("email"):
                    c_confidence += 0.2
                if c.get("phone"):
                    c_confidence += 0.15
                if c.get("linkedin_url"):
                    c_confidence += 0.1
                if c.get("buying_role") in ("economic_buyer", "champion"):
                    c_confidence += 0.05

                contact = Contact(
                    owner_id=owner.id,
                    full_name=c.get("full_name", "Unknown"),
                    first_name=c.get("first_name"),
                    last_name=c.get("last_name"),
                    job_title=c.get("job_title"),
                    buying_role=c.get("buying_role"),
                    email=c.get("email"),
                    email_verified=c.get("email_source") == "apollo",
                    email_source=c.get("email_source"),
                    phone=c.get("phone"),
                    phone_type="direct" if c.get("phone") else None,
                    phone_source=c.get("phone_source"),
                    linkedin_url=c.get("linkedin_url"),
                    confidence_score=min(c_confidence, 1.0),
                    is_primary=is_primary,
                    enrichment_sources=c.get("enrichment_sources", {}),
                )
                session.add(contact)
                await session.flush()
                contact_ids.append(str(contact.id))

            await session.commit()

        self.log.info(
            "enrichment_complete",
            property_id=str(property_uuid),
            owner_id=str(owner.id),
            contact_count=len(contact_ids),
            enrichment_sources=list(enrichment_log.keys()),
        )

        return {
            "property_id": str(property_uuid),
            "owner_id": str(owner.id),
            "clean_name": resolved.clean_name,
            "entity_type": resolved.entity_type,
            "contact_count": len(contact_ids),
            "contact_ids": contact_ids,
            "confidence_score": owner_confidence,
            "enrichment_log": enrichment_log,
            "items_processed": 1,
            "items_failed": 0,
        }
