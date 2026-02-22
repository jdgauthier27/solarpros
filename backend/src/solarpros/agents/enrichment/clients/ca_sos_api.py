"""CA Secretary of State REST API client.

Replaces the broken Playwright-based scraper with the official CALICO REST API.

Production endpoint:
    https://calico.sos.ca.gov/cbc/v1/api/BusinessEntityKeywordSearch?search-term=NAME

Auth:
    Header ``Ocp-Apim-Subscription-Key: KEY``

Returns up to 150 results per query.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient
from solarpros.config import settings

logger = structlog.get_logger()


class CASOSAPIClient(BaseEnrichmentClient):
    """Real CA SOS REST API client using httpx."""

    source_name = "ca_sos_api"

    BASE_URL = "https://calico.sos.ca.gov/cbc/v1/api"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.ca_sos_api_key

    async def search(self, **kwargs) -> dict | None:
        """Search the CA SOS for a business entity by name.

        Parameters
        ----------
        entity_name : str
            Business entity name to search for.

        Returns
        -------
        dict | None
            A dict with keys: entity_name, entity_number, entity_type,
            status, agent_name, agent_address, filing_date, officers.
            Returns None if no matching entity was found.
        """
        entity_name = kwargs.get("entity_name", "")
        if not entity_name:
            return None

        if not self.api_key:
            logger.warning("ca_sos_api_key_not_set")
            return None

        logger.info("ca_sos_api_search_start", entity_name=entity_name)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/BusinessEntityKeywordSearch",
                    params={"search-term": entity_name},
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                )

                if response.status_code == 404:
                    logger.info("ca_sos_api_not_found", entity_name=entity_name)
                    return None

                response.raise_for_status()
                results = response.json()

                if not results:
                    logger.info("ca_sos_api_empty_results", entity_name=entity_name)
                    return None

                # Take the first (best) match
                entity = results[0] if isinstance(results, list) else results

                # Normalize the API response to our internal format
                result = self._normalize_entity(entity)

                logger.info(
                    "ca_sos_api_result",
                    entity_name=result.get("entity_name"),
                    entity_number=result.get("entity_number"),
                    status=result.get("status"),
                )
                return result

        except httpx.TimeoutException:
            logger.warning("ca_sos_api_timeout", entity_name=entity_name)
            return None
        except Exception as exc:
            logger.warning(
                "ca_sos_api_error",
                entity_name=entity_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None

    @staticmethod
    def _normalize_entity(entity: dict) -> dict:
        """Normalize CA SOS API response to our internal format."""
        # Map known API response fields
        entity_type_raw = entity.get("EntityType", "")
        entity_type = "LLC"
        if "CORPORATION" in entity_type_raw.upper():
            entity_type = "Corp"
        elif "LIMITED LIABILITY" in entity_type_raw.upper():
            entity_type = "LLC"
        elif "LIMITED PARTNERSHIP" in entity_type_raw.upper():
            entity_type = "LP"
        elif entity_type_raw:
            entity_type = entity_type_raw

        agent_name = entity.get("AgentName")
        agent_address_parts = []
        for field in ("AgentAddress1", "AgentAddress2", "AgentCity", "AgentState", "AgentZip"):
            val = entity.get(field)
            if val:
                agent_address_parts.append(val)
        agent_address = ", ".join(agent_address_parts) if agent_address_parts else None

        # Build officers list from available data
        officers = []
        if agent_name:
            officers.append({
                "name": agent_name,
                "title": "Agent for Service of Process",
                "phone": None,
                "address": agent_address,
            })

        # Extract additional officers if available in the response
        for key_prefix in ("Officer1", "Officer2", "Officer3"):
            officer_name = entity.get(f"{key_prefix}Name")
            if officer_name:
                officers.append({
                    "name": officer_name,
                    "title": entity.get(f"{key_prefix}Title", "Officer"),
                    "phone": None,
                    "address": entity.get(f"{key_prefix}Address"),
                })

        return {
            "entity_name": entity.get("EntityName", ""),
            "entity_number": entity.get("EntityID", entity.get("EntityNumber", "")),
            "entity_type": entity_type,
            "status": entity.get("StatusDescription", entity.get("StandingSOS", "")),
            "agent_name": agent_name,
            "agent_address": agent_address,
            "filing_date": entity.get("FilingDate"),
            "officers": officers,
        }
