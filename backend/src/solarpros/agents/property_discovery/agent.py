"""Property Discovery Agent -- scrapes county assessor data and persists qualifying properties."""

from __future__ import annotations

import structlog
from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.agents.property_discovery.filters import filter_properties
from solarpros.agents.property_discovery.scrapers.base import BaseScraper
from solarpros.agents.property_discovery.scrapers.la_county import LACountyScraper
from solarpros.agents.property_discovery.scrapers.mock import MockScraper
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.property import Property

logger = structlog.get_logger()

# Mapping of county name -> real scraper class
_SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "Los Angeles": LACountyScraper,
}


def _get_scraper(county: str) -> BaseScraper:
    """Return the appropriate scraper instance for a county.

    When ``settings.use_mock_scrapers`` is ``True`` (the default in
    development), a :class:`MockScraper` is returned regardless of
    county.  Otherwise the real scraper registered for the county is
    used, falling back to :class:`MockScraper` if no real scraper
    exists for the county yet.
    """
    if settings.use_mock_scrapers:
        logger.info("using_mock_scraper", county=county)
        return MockScraper(county)

    scraper_cls = _SCRAPER_REGISTRY.get(county)
    if scraper_cls is None:
        logger.warning(
            "no_real_scraper_for_county_falling_back_to_mock",
            county=county,
        )
        return MockScraper(county)

    logger.info("using_real_scraper", county=county, scraper=scraper_cls.__name__)
    return scraper_cls(county)


class PropertyDiscoveryAgent(BaseAgent):
    """Agent that discovers commercial properties for a given county.

    Workflow:
        1. Select the appropriate scraper (mock or real) for the county.
        2. Scrape property data across multiple pages.
        3. Filter for commercial zoning and minimum roof size.
        4. Persist qualifying properties to the database (upsert by APN + county).
        5. Return a summary dict with counts.
    """

    agent_type: str = "property_discovery"

    async def execute(self, **kwargs) -> dict:
        """Run property discovery for a single county.

        Keyword Args:
            county: Name of the county to scrape (required).
            max_pages: Maximum pages to scrape (default 10).

        Returns:
            Dict with keys: ``county``, ``scraped``, ``qualified``,
            ``saved``, ``duplicates``, ``items_processed``,
            ``items_failed``.
        """
        county: str = kwargs["county"]
        max_pages: int = kwargs.get("max_pages", 10)

        self.log.info("property_discovery_starting", county=county, max_pages=max_pages)

        # ---- Step 1: Scrape ----
        scraper = _get_scraper(county)
        async with scraper:
            raw_properties = await scraper.scrape_all(max_pages=max_pages)

        self.log.info("scraping_complete", county=county, raw_count=len(raw_properties))

        # ---- Step 2: Filter ----
        qualified = filter_properties(raw_properties, county=county)
        self.log.info("filtering_complete", county=county, qualified_count=len(qualified))

        # ---- Step 3: Persist ----
        saved = 0
        duplicates = 0
        failed = 0

        async with async_session_factory() as session:
            for prop_data in qualified:
                try:
                    # Check for existing property by APN + county (upsert logic)
                    result = await session.execute(
                        select(Property).where(
                            Property.apn == prop_data["apn"],
                            Property.county == prop_data["county"],
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update existing property with fresh data
                        for field in (
                            "address",
                            "city",
                            "state",
                            "zip_code",
                            "zoning",
                            "building_type",
                            "building_sqft",
                            "roof_sqft",
                            "year_built",
                            "owner_name_raw",
                            "is_commercial",
                            "meets_roof_min",
                        ):
                            if field in prop_data:
                                setattr(existing, field, prop_data[field])
                        duplicates += 1
                    else:
                        # Create new property
                        new_property = Property(
                            apn=prop_data["apn"],
                            county=prop_data["county"],
                            address=prop_data["address"],
                            city=prop_data.get("city"),
                            state=prop_data.get("state", "CA"),
                            zip_code=prop_data.get("zip_code"),
                            zoning=prop_data.get("zoning"),
                            building_type=prop_data.get("building_type"),
                            building_sqft=prop_data.get("building_sqft"),
                            roof_sqft=prop_data.get("roof_sqft"),
                            year_built=prop_data.get("year_built"),
                            owner_name_raw=prop_data.get("owner_name_raw"),
                            is_commercial=prop_data.get("is_commercial", True),
                            meets_roof_min=prop_data.get("meets_roof_min", True),
                        )
                        session.add(new_property)
                        saved += 1
                except Exception:
                    self.log.exception("property_save_failed", apn=prop_data.get("apn"))
                    failed += 1

            await session.commit()

        summary = {
            "county": county,
            "scraped": len(raw_properties),
            "qualified": len(qualified),
            "saved": saved,
            "duplicates": duplicates,
            "items_processed": saved + duplicates,
            "items_failed": failed,
        }
        self.log.info("property_discovery_complete", **summary)
        return summary
