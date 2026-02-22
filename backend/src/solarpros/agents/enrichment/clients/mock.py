"""Mock enrichment clients for development and testing.

Reuses the existing mock logic from the owner_id module for SOS data,
and provides mock implementations for Apollo, Google Places, Hunter.io,
and Google Search clients.
"""

from __future__ import annotations

import asyncio
import hashlib

import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient

logger = structlog.get_logger()


class MockCASOSClient(BaseEnrichmentClient):
    """Mock CA SOS API client that returns realistic data."""

    source_name = "ca_sos_api_mock"

    _FIRST_NAMES = [
        "James", "Robert", "Michael", "David", "Richard", "Thomas", "Daniel",
        "Maria", "Jennifer", "Patricia", "Linda", "Susan", "Karen", "Lisa",
    ]
    _LAST_NAMES = [
        "Wilson", "Chen", "Patel", "Thompson", "Garcia", "Martinez", "Rodriguez",
        "Kim", "Nguyen", "Lee", "Brown", "Johnson", "Williams", "Jones",
    ]
    _TITLES = [
        "CEO", "President", "Managing Partner", "Principal", "CFO",
        "VP of Operations", "Director of Development", "Facilities Manager",
    ]

    async def search(self, **kwargs) -> dict | None:
        entity_name = kwargs.get("entity_name", "")
        if not entity_name:
            return None

        await asyncio.sleep(0.05)

        name_lower = entity_name.lower()
        is_business = any(
            kw in name_lower
            for kw in ("llc", "inc", "corp", "lp", "trust", "holdings", "properties", "realty", "group")
        )
        if not is_business:
            return None

        seed = int(hashlib.md5(name_lower.encode()).hexdigest()[:8], 16)

        def pick(pool, offset=0):
            return pool[(seed + offset) % len(pool)]

        num_officers = (seed % 3) + 1
        officers = []
        for i in range(num_officers):
            officers.append({
                "name": f"{pick(self._FIRST_NAMES, i * 7)} {pick(self._LAST_NAMES, i * 13)}",
                "title": pick(self._TITLES, i * 5),
                "phone": f"({(seed + i * 3) % 900 + 100}) {(seed + i * 111) % 900 + 100}-{(seed + i * 37) % 9000 + 1000}",
                "address": f"{(seed + i * 200) % 9000 + 100} Main St, Los Angeles, CA",
            })

        entity_type = "LLC"
        if "inc" in name_lower or "corp" in name_lower:
            entity_type = "Corp"
        elif "lp" in name_lower:
            entity_type = "LP"

        return {
            "entity_name": entity_name.upper(),
            "entity_number": f"{'LLC' if entity_type == 'LLC' else 'C'}{seed % 900000 + 100000}",
            "entity_type": entity_type,
            "status": "Active",
            "agent_name": officers[0]["name"],
            "agent_address": officers[0]["address"],
            "officers": officers,
        }


class MockApolloClient(BaseEnrichmentClient):
    """Mock Apollo.io client returning realistic person enrichment data."""

    source_name = "apollo_mock"

    async def search(self, **kwargs) -> dict | None:
        person_name = kwargs.get("person_name", "")
        company_name = kwargs.get("company_name", "")
        if not person_name:
            return None

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(f"{person_name}{company_name}".lower().encode()).hexdigest()[:8], 16)
        parts = person_name.strip().split()
        first = parts[0] if parts else "Unknown"
        last = parts[-1] if len(parts) > 1 else "Unknown"

        domain = company_name.lower().replace(" ", "").replace(",", "")[:20] + ".com" if company_name else "example.com"
        email = f"{first[0].lower()}.{last.lower()}@{domain}"

        titles = ["VP of Operations", "Director of Facilities", "CFO", "COO", "Facilities Manager", "Property Manager"]
        departments = ["Operations", "Facilities", "Finance", "Executive", "Property Management"]

        return {
            "email": email,
            "email_status": "verified",
            "first_name": first,
            "last_name": last,
            "title": titles[seed % len(titles)],
            "department": departments[seed % len(departments)],
            "phone": f"+1{(seed % 900) + 100}{(seed * 7) % 9000000 + 1000000}",
            "phone_type": "direct",
            "linkedin_url": f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{seed % 10000}",
            "company_name": company_name,
            "company_domain": domain,
        }


class MockGooglePlacesClient(BaseEnrichmentClient):
    """Mock Google Places client returning business info."""

    source_name = "google_places_mock"

    async def search(self, **kwargs) -> dict | None:
        business_name = kwargs.get("business_name", "")
        city = kwargs.get("city", "")
        if not business_name:
            return None

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(f"{business_name}{city}".lower().encode()).hexdigest()[:8], 16)
        domain = business_name.lower().replace(" ", "")[:20] + ".com"

        return {
            "place_id": f"ChIJ{seed % 10**16:016d}",
            "name": business_name,
            "phone": f"({(seed % 900) + 100}) {(seed * 3) % 900 + 100}-{(seed * 7) % 9000 + 1000}",
            "website": f"https://www.{domain}",
            "domain": domain,
            "address": f"{seed % 9000 + 100} Business Ave, {city or 'Los Angeles'}, CA",
            "rating": round(3.5 + (seed % 15) / 10, 1),
            "types": ["establishment", "point_of_interest"],
        }


class MockHunterIOClient(BaseEnrichmentClient):
    """Mock Hunter.io client for domain email search."""

    source_name = "hunter_mock"

    async def search(self, **kwargs) -> dict | None:
        domain = kwargs.get("domain", "")
        if not domain:
            return None

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(domain.lower().encode()).hexdigest()[:8], 16)
        names = [
            ("James", "Wilson", "CEO"),
            ("Sarah", "Chen", "CFO"),
            ("Michael", "Patel", "VP Operations"),
            ("Linda", "Martinez", "Facilities Manager"),
            ("David", "Kim", "Director of Operations"),
        ]

        num_emails = (seed % 3) + 2
        emails = []
        for i in range(num_emails):
            first, last, title = names[(seed + i) % len(names)]
            emails.append({
                "email": f"{first[0].lower()}.{last.lower()}@{domain}",
                "first_name": first,
                "last_name": last,
                "position": title,
                "confidence": 80 + (seed + i) % 20,
                "type": "personal",
            })

        return {
            "domain": domain,
            "emails": emails,
            "organization": domain.split(".")[0].title(),
        }


class MockGoogleSearchClient(BaseEnrichmentClient):
    """Mock Google Search (Serper.dev) client for last-resort contact finding."""

    source_name = "google_search_mock"

    async def search(self, **kwargs) -> dict | None:
        query = kwargs.get("query", "")
        if not query:
            return None

        await asyncio.sleep(0.05)

        seed = int(hashlib.md5(query.lower().encode()).hexdigest()[:8], 16)

        return {
            "query": query,
            "results": [
                {
                    "title": f"{query} - Company Profile",
                    "link": f"https://example.com/company/{seed}",
                    "snippet": f"Contact information for {query}. Phone: (310) {seed % 900 + 100}-{seed % 9000 + 1000}",
                    "extracted_phone": f"(310) {seed % 900 + 100}-{seed % 9000 + 1000}",
                    "extracted_email": None,
                },
            ],
        }
