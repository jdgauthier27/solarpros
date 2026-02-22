"""Multi-source enrichment waterfall.

Chains multiple data sources in sequence, building up contact data
progressively. Each step enriches what prior steps found. Failures
at any step are logged and skipped — the waterfall continues.

Waterfall order:
  1. CA SOS API (entity resolution + officers)
  2. Google Places (company phone, website, place_id)
  3. Apollo.io (per-officer: email, phone, title, linkedin)
  4. Hunter.io (domain-level email discovery)
  5. Google Search (last resort for missing contacts)
"""

from __future__ import annotations

import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient

logger = structlog.get_logger()


class EnrichmentWaterfall:
    """Orchestrates sequential enrichment across multiple data sources."""

    def __init__(
        self,
        sos_client: BaseEnrichmentClient,
        places_client: BaseEnrichmentClient,
        apollo_client: BaseEnrichmentClient,
        hunter_client: BaseEnrichmentClient,
        search_client: BaseEnrichmentClient,
    ) -> None:
        self.sos_client = sos_client
        self.places_client = places_client
        self.apollo_client = apollo_client
        self.hunter_client = hunter_client
        self.search_client = search_client

    async def enrich(
        self,
        *,
        clean_name: str,
        entity_type: str,
        is_business: bool,
        domain_guess: str | None,
        city: str | None = None,
    ) -> dict:
        """Run the full enrichment waterfall.

        Returns a dict with:
          - company: dict of company-level data
          - contacts: list of contact dicts
          - enrichment_log: dict tracking which sources provided what
        """
        enrichment_log: dict[str, dict] = {}
        company: dict = {
            "domain": domain_guess,
            "website": None,
            "phone": None,
            "place_id": None,
            "description": None,
        }
        contacts: list[dict] = []

        # Step 1: CA SOS API
        sos_result = None
        if is_business:
            try:
                sos_result = await self.sos_client.search(entity_name=clean_name)
                if sos_result:
                    enrichment_log["ca_sos"] = {"status": "found", "entity_number": sos_result.get("entity_number")}
                    # Extract officers as initial contacts
                    for officer in sos_result.get("officers", []):
                        contacts.append({
                            "full_name": officer.get("name", ""),
                            "first_name": self._first_name(officer.get("name", "")),
                            "last_name": self._last_name(officer.get("name", "")),
                            "job_title": officer.get("title"),
                            "phone": officer.get("phone"),
                            "phone_source": "sos",
                            "email": None,
                            "email_source": None,
                            "linkedin_url": None,
                            "enrichment_sources": {"sos": True},
                        })
                else:
                    enrichment_log["ca_sos"] = {"status": "not_found"}
            except Exception as exc:
                logger.warning("waterfall_sos_error", error=str(exc))
                enrichment_log["ca_sos"] = {"status": "error", "error": str(exc)}

        # Step 2: Google Places API
        try:
            places_result = await self.places_client.search(
                business_name=clean_name, city=city or ""
            )
            if places_result:
                enrichment_log["google_places"] = {"status": "found", "place_id": places_result.get("place_id")}
                company["phone"] = company["phone"] or places_result.get("phone")
                company["website"] = company["website"] or places_result.get("website")
                company["place_id"] = places_result.get("place_id")
                # Update domain from Places if we didn't have one
                if not company["domain"] and places_result.get("domain"):
                    company["domain"] = places_result["domain"]
            else:
                enrichment_log["google_places"] = {"status": "not_found"}
        except Exception as exc:
            logger.warning("waterfall_places_error", error=str(exc))
            enrichment_log["google_places"] = {"status": "error", "error": str(exc)}

        # Step 3: Apollo.io — enrich each contact we found from SOS
        apollo_found = 0
        for contact in contacts:
            if not contact["full_name"]:
                continue
            try:
                apollo_result = await self.apollo_client.search(
                    person_name=contact["full_name"],
                    company_name=clean_name,
                )
                if apollo_result:
                    apollo_found += 1
                    # Fill in missing data from Apollo
                    if not contact["email"] and apollo_result.get("email"):
                        contact["email"] = apollo_result["email"]
                        contact["email_source"] = "apollo"
                    if not contact["phone"] and apollo_result.get("phone"):
                        contact["phone"] = apollo_result["phone"]
                        contact["phone_source"] = "apollo"
                    if not contact["linkedin_url"] and apollo_result.get("linkedin_url"):
                        contact["linkedin_url"] = apollo_result["linkedin_url"]
                    if apollo_result.get("title"):
                        contact["job_title"] = apollo_result["title"]
                    if apollo_result.get("company_domain"):
                        company["domain"] = company["domain"] or apollo_result["company_domain"]
                    contact["enrichment_sources"]["apollo"] = True
            except Exception as exc:
                logger.warning("waterfall_apollo_error", contact=contact["full_name"], error=str(exc))

        enrichment_log["apollo"] = {"status": "enriched", "contacts_found": apollo_found}

        # Step 4: Hunter.io — domain-level email discovery if we have a domain
        domain = company.get("domain")
        if domain:
            try:
                hunter_result = await self.hunter_client.search(domain=domain)
                if hunter_result and hunter_result.get("emails"):
                    enrichment_log["hunter"] = {"status": "found", "emails_count": len(hunter_result["emails"])}
                    self._merge_hunter_emails(contacts, hunter_result["emails"], domain)
                else:
                    enrichment_log["hunter"] = {"status": "not_found"}
            except Exception as exc:
                logger.warning("waterfall_hunter_error", error=str(exc))
                enrichment_log["hunter"] = {"status": "error", "error": str(exc)}
        else:
            enrichment_log["hunter"] = {"status": "skipped", "reason": "no_domain"}

        # Step 5: Google Search — last resort for contacts still missing email/phone
        missing_contacts = [c for c in contacts if not c.get("email") and not c.get("phone")]
        if missing_contacts and is_business:
            try:
                search_result = await self.search_client.search(
                    query=f"{clean_name} contact phone email"
                )
                if search_result and search_result.get("results"):
                    enrichment_log["google_search"] = {"status": "found"}
                    for result in search_result["results"]:
                        if result.get("extracted_phone"):
                            for c in missing_contacts:
                                if not c.get("phone"):
                                    c["phone"] = result["extracted_phone"]
                                    c["phone_source"] = "google_search"
                                    c["enrichment_sources"]["google_search"] = True
                                    break
                        if result.get("extracted_email"):
                            for c in missing_contacts:
                                if not c.get("email"):
                                    c["email"] = result["extracted_email"]
                                    c["email_source"] = "google_search"
                                    c["enrichment_sources"]["google_search"] = True
                                    break
                else:
                    enrichment_log["google_search"] = {"status": "not_found"}
            except Exception as exc:
                logger.warning("waterfall_search_error", error=str(exc))
                enrichment_log["google_search"] = {"status": "error", "error": str(exc)}
        else:
            enrichment_log["google_search"] = {"status": "skipped"}

        return {
            "company": company,
            "contacts": contacts,
            "sos_result": sos_result,
            "enrichment_log": enrichment_log,
        }

    def _merge_hunter_emails(
        self,
        contacts: list[dict],
        hunter_emails: list[dict],
        domain: str,
    ) -> None:
        """Merge Hunter.io domain emails into existing contacts or add new ones.

        Matches by last name; unmatched emails become new contacts (up to 5 total).
        """
        existing_names = {c["last_name"].lower() for c in contacts if c.get("last_name")}

        for he in hunter_emails:
            last = (he.get("last_name") or "").lower()
            matched = False

            # Try to match to existing contact by last name
            if last:
                for contact in contacts:
                    if contact.get("last_name", "").lower() == last and not contact.get("email"):
                        contact["email"] = he["email"]
                        contact["email_source"] = "hunter"
                        contact["enrichment_sources"]["hunter"] = True
                        matched = True
                        break

            # Add as new contact if unmatched and we have room
            if not matched and len(contacts) < 5 and he.get("email"):
                contacts.append({
                    "full_name": f"{he.get('first_name', '')} {he.get('last_name', '')}".strip(),
                    "first_name": he.get("first_name"),
                    "last_name": he.get("last_name"),
                    "job_title": he.get("position"),
                    "phone": None,
                    "phone_source": None,
                    "email": he["email"],
                    "email_source": "hunter",
                    "linkedin_url": None,
                    "enrichment_sources": {"hunter": True},
                })

    @staticmethod
    def _first_name(full_name: str) -> str | None:
        parts = full_name.strip().split()
        return parts[0] if parts else None

    @staticmethod
    def _last_name(full_name: str) -> str | None:
        parts = full_name.strip().split()
        return parts[-1] if len(parts) > 1 else None
