"""Hunter.io domain search client for enrichment waterfall.

Adapted from the existing owner_id hunter_io module, but focuses on
domain-level email discovery (find all emails at a domain).
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient
from solarpros.config import settings

logger = structlog.get_logger()


class HunterIODomainClient(BaseEnrichmentClient):
    """Hunter.io domain search — finds all emails at a domain."""

    source_name = "hunter"

    BASE_URL = "https://api.hunter.io/v2"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.hunter_io_api_key

    async def search(self, **kwargs) -> dict | None:
        """Search Hunter.io for all emails at a domain.

        Parameters
        ----------
        domain : str
            The domain to search for emails.

        Returns
        -------
        dict | None
            Dict with domain, emails list, and organization name.
        """
        domain = kwargs.get("domain", "")
        if not domain or not self.api_key:
            return None

        logger.info("hunter_domain_search_start", domain=domain)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/domain-search",
                    params={"domain": domain, "api_key": self.api_key, "limit": 10},
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json().get("data", {})
                emails_raw = data.get("emails", [])

                if not emails_raw:
                    return None

                emails = []
                for e in emails_raw:
                    emails.append({
                        "email": e.get("value"),
                        "first_name": e.get("first_name"),
                        "last_name": e.get("last_name"),
                        "position": e.get("position"),
                        "confidence": e.get("confidence", 0),
                        "type": e.get("type"),
                    })

                return {
                    "domain": domain,
                    "emails": emails,
                    "organization": data.get("organization"),
                }

        except httpx.TimeoutException:
            logger.warning("hunter_domain_timeout", domain=domain)
            return None
        except Exception as exc:
            logger.warning("hunter_domain_error", domain=domain, error=str(exc))
            return None
