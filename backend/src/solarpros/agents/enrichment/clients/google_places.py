"""Google Places API client for business enrichment.

Searches for a business by name + city to get phone, website, and place ID.
"""

from __future__ import annotations

import httpx
import structlog

from solarpros.agents.enrichment.clients.base import BaseEnrichmentClient
from solarpros.config import settings

logger = structlog.get_logger()


class GooglePlacesClient(BaseEnrichmentClient):
    """Real Google Places API client."""

    source_name = "google_places"

    BASE_URL = "https://places.googleapis.com/v1/places:searchText"
    TIMEOUT = 15.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_places_api_key

    async def search(self, **kwargs) -> dict | None:
        """Search Google Places for a business.

        Parameters
        ----------
        business_name : str
            Name of the business to search for.
        city : str
            City to narrow the search.

        Returns
        -------
        dict | None
            Business info including phone, website, place_id.
        """
        business_name = kwargs.get("business_name", "")
        city = kwargs.get("city", "")
        if not business_name or not self.api_key:
            return None

        query = f"{business_name} {city} California" if city else f"{business_name} California"

        logger.info("google_places_search_start", query=query)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.BASE_URL,
                    headers={
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": (
                            "places.id,places.displayName,places.formattedAddress,"
                            "places.nationalPhoneNumber,places.websiteUri,"
                            "places.rating,places.types"
                        ),
                    },
                    json={"textQuery": query, "maxResultCount": 1},
                )

                if response.status_code != 200:
                    logger.warning(
                        "google_places_error_status",
                        status=response.status_code,
                    )
                    return None

                data = response.json()
                places = data.get("places", [])
                if not places:
                    return None

                place = places[0]
                website = place.get("websiteUri", "")
                domain = ""
                if website:
                    # Extract domain from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(website)
                    domain = parsed.netloc.replace("www.", "")

                return {
                    "place_id": place.get("id", ""),
                    "name": place.get("displayName", {}).get("text", ""),
                    "phone": place.get("nationalPhoneNumber"),
                    "website": website,
                    "domain": domain,
                    "address": place.get("formattedAddress"),
                    "rating": place.get("rating"),
                    "types": place.get("types", []),
                }

        except httpx.TimeoutException:
            logger.warning("google_places_timeout", business_name=business_name)
            return None
        except Exception as exc:
            logger.warning(
                "google_places_error",
                business_name=business_name,
                error=str(exc),
            )
            return None
