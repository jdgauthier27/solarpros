"""Apollo.io people enrichment client.

Searches for person contact info by name + company via the Apollo API.
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient
from solarpros.config import settings

logger = structlog.get_logger()


class ApolloClient(BaseEnrichmentClient):
    """Real Apollo.io API client."""

    source_name = "apollo"

    BASE_URL = "https://api.apollo.io/v1"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.apollo_api_key

    async def search(self, **kwargs) -> dict | None:
        """Search Apollo for a person by name + company.

        Parameters
        ----------
        person_name : str
            Full name of the person to search for.
        company_name : str
            Company name to narrow the search.

        Returns
        -------
        dict | None
            Contact enrichment data or None.
        """
        person_name = kwargs.get("person_name", "")
        company_name = kwargs.get("company_name", "")
        if not person_name or not self.api_key:
            return None

        parts = person_name.strip().split()
        first_name = parts[0] if parts else ""
        last_name = parts[-1] if len(parts) > 1 else ""

        logger.info(
            "apollo_search_start",
            person_name=person_name,
            company_name=company_name,
        )

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    f"{self.BASE_URL}/people/match",
                    headers={"X-Api-Key": self.api_key},
                    json={
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization_name": company_name,
                    },
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()
                person = data.get("person")
                if not person:
                    return None

                return {
                    "email": person.get("email"),
                    "email_status": person.get("email_status"),
                    "first_name": person.get("first_name", first_name),
                    "last_name": person.get("last_name", last_name),
                    "title": person.get("title"),
                    "department": person.get("department"),
                    "phone": (
                        person.get("phone_numbers", [{}])[0].get("sanitized_number")
                        if person.get("phone_numbers")
                        else None
                    ),
                    "phone_type": (
                        person.get("phone_numbers", [{}])[0].get("type")
                        if person.get("phone_numbers")
                        else None
                    ),
                    "linkedin_url": person.get("linkedin_url"),
                    "company_name": (
                        person.get("organization", {}).get("name")
                        if person.get("organization")
                        else company_name
                    ),
                    "company_domain": (
                        person.get("organization", {}).get("primary_domain")
                        if person.get("organization")
                        else None
                    ),
                }

        except httpx.TimeoutException:
            logger.warning("apollo_timeout", person_name=person_name)
            return None
        except Exception as exc:
            logger.warning(
                "apollo_error",
                person_name=person_name,
                error=str(exc),
            )
            return None
