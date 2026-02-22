"""CA Secretary of State business entity lookup client.

Provides both a real Playwright-based client that navigates the CA SOS
bizfile search (https://bizfileonline.sos.ca.gov/search/business) and a
mock client that returns realistic data for development/testing.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class BaseSOSLookupClient(ABC):
    """Abstract interface for CA Secretary of State entity search."""

    @abstractmethod
    async def search_entity(self, entity_name: str) -> dict | None:
        """Search the CA SOS for a business entity by name.

        Returns
        -------
        dict | None
            A dict with keys:
                - entity_name (str)
                - entity_number (str)
                - entity_type (str): Corp, LLC, LP, etc.
                - status (str): Active, Inactive, Dissolved, etc.
                - agent_name (str | None)
                - agent_address (str | None)
            Returns ``None`` if no matching entity was found.
        """


class SOSLookupClient(BaseSOSLookupClient):
    """Real CA SOS business search via Playwright browser automation.

    Navigates the bizfile online search at
    https://bizfileonline.sos.ca.gov/search/business and scrapes the
    top result for the given entity name.
    """

    SEARCH_URL = "https://bizfileonline.sos.ca.gov/search/business"

    async def search_entity(self, entity_name: str) -> dict | None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("playwright_not_installed", hint="pip install playwright")
            raise

        logger.info("sos_lookup_start", entity_name=entity_name)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()
                page.set_default_timeout(30_000)

                await page.goto(self.SEARCH_URL, wait_until="networkidle")

                # Type the entity name into the search field
                search_input = page.locator("#SearchCriteria")
                await search_input.fill(entity_name)

                # Select "Entity Name" search type
                search_type = page.locator("#SearchType")
                await search_type.select_option("ENTITY")

                # Submit the search
                submit_btn = page.locator('button[type="submit"], input[type="submit"]')
                await submit_btn.first.click()

                # Wait for results
                await page.wait_for_selector(
                    "table.table tbody tr, .no-results, .search-results",
                    timeout=15_000,
                )

                # Check for no results
                no_results = await page.locator(".no-results").count()
                if no_results > 0:
                    logger.info("sos_lookup_no_results", entity_name=entity_name)
                    return None

                # Click the first result row to get details
                first_row = page.locator("table.table tbody tr").first
                first_row_exists = await first_row.count()
                if first_row_exists == 0:
                    logger.info("sos_lookup_no_results", entity_name=entity_name)
                    return None

                # Extract data from the first result row
                cells = first_row.locator("td")
                cell_count = await cells.count()

                if cell_count < 3:
                    logger.warning("sos_lookup_unexpected_format", cell_count=cell_count)
                    return None

                result_entity_name = (await cells.nth(0).inner_text()).strip()
                entity_number = (await cells.nth(1).inner_text()).strip()
                status = (await cells.nth(2).inner_text()).strip()

                # Click into the detail page for more information
                link = first_row.locator("a").first
                link_exists = await link.count()

                entity_type = ""
                agent_name = None
                agent_address = None

                if link_exists > 0:
                    await link.click()
                    await page.wait_for_load_state("networkidle")

                    # Extract entity type from detail page
                    entity_type_el = page.locator(
                        "text=Entity Type >> .. >> dd, "
                        "[data-label='Entity Type']"
                    )
                    if await entity_type_el.count() > 0:
                        entity_type = (await entity_type_el.first.inner_text()).strip()

                    # Extract agent information
                    agent_name_el = page.locator(
                        "text=Agent for Service of Process >> .. >> dd"
                    )
                    if await agent_name_el.count() > 0:
                        agent_name = (await agent_name_el.first.inner_text()).strip()

                    agent_addr_el = page.locator(
                        "text=Agent Address >> .. >> dd"
                    )
                    if await agent_addr_el.count() > 0:
                        agent_address = (await agent_addr_el.first.inner_text()).strip()

                result = {
                    "entity_name": result_entity_name,
                    "entity_number": entity_number,
                    "entity_type": entity_type,
                    "status": status,
                    "agent_name": agent_name,
                    "agent_address": agent_address,
                }

                logger.info(
                    "sos_lookup_result",
                    entity_name=result_entity_name,
                    entity_number=entity_number,
                    status=status,
                )
                return result

            finally:
                await browser.close()


class MockSOSLookupClient(BaseSOSLookupClient):
    """Mock SOS lookup client that returns realistic data for testing.

    Recognizes common business name patterns (LLC, Corp, Inc, LP, Trust)
    and returns plausible data. Names that don't look like business
    entities return ``None`` to simulate a "not found" scenario.
    """

    # Common mock entities keyed by normalized name fragments
    _MOCK_ENTITIES: dict[str, dict] = {
        "pacific": {
            "entity_name": "PACIFIC COMMERCIAL HOLDINGS LLC",
            "entity_number": "202112345678",
            "entity_type": "LLC",
            "status": "Active",
            "agent_name": "James R. Wilson",
            "agent_address": "1200 Wilshire Blvd, Suite 400, Los Angeles, CA 90017",
        },
        "golden": {
            "entity_name": "GOLDEN STATE PROPERTIES INC",
            "entity_number": "C4567890",
            "entity_type": "Corp",
            "status": "Active",
            "agent_name": "Maria L. Chen",
            "agent_address": "555 Montgomery St, Suite 1500, San Francisco, CA 94111",
        },
        "sunrise": {
            "entity_name": "SUNRISE REALTY GROUP LP",
            "entity_number": "LP202198765",
            "entity_type": "LP",
            "status": "Active",
            "agent_name": "Robert K. Patel",
            "agent_address": "9800 La Cienega Blvd, Suite 200, Inglewood, CA 90301",
        },
        "valley": {
            "entity_name": "VALLEY INVESTMENT TRUST",
            "entity_number": "C3456789",
            "entity_type": "Corp",
            "status": "Active",
            "agent_name": "Susan M. Nguyen",
            "agent_address": "2300 Clayton Rd, Suite 100, Concord, CA 94520",
        },
        "coastal": {
            "entity_name": "COASTAL DEVELOPMENT PARTNERS LLC",
            "entity_number": "202209876543",
            "entity_type": "LLC",
            "status": "Active",
            "agent_name": "David A. Thompson",
            "agent_address": "300 Spectrum Center Dr, Suite 400, Irvine, CA 92618",
        },
        "west": {
            "entity_name": "WESTERN COMMERCIAL CORP",
            "entity_number": "C2345678",
            "entity_type": "Corp",
            "status": "Inactive",
            "agent_name": "Linda S. Martinez",
            "agent_address": "1999 Harrison St, Suite 1600, Oakland, CA 94612",
        },
    }

    # Entity type indicators in names
    _ENTITY_TYPE_PATTERNS: list[tuple[str, str]] = [
        (r"\bllc\b", "LLC"),
        (r"\bl\.l\.c\b", "LLC"),
        (r"\binc\b", "Corp"),
        (r"\bcorp\b", "Corp"),
        (r"\bcorporation\b", "Corp"),
        (r"\blp\b", "LP"),
        (r"\bl\.p\b", "LP"),
        (r"\blimited\s+partnership\b", "LP"),
        (r"\btrust\b", "Trust"),
        (r"\bpartners\b", "LP"),
        (r"\bholdings\b", "LLC"),
        (r"\bproperties\b", "Corp"),
        (r"\brealty\b", "Corp"),
        (r"\bgroup\b", "LLC"),
    ]

    async def search_entity(self, entity_name: str) -> dict | None:
        logger.info("mock_sos_lookup", entity_name=entity_name)

        # Simulate network latency
        await asyncio.sleep(0.1)

        name_lower = entity_name.lower().strip()

        # Check for direct matches against known mock entities
        for key, entity_data in self._MOCK_ENTITIES.items():
            if key in name_lower:
                result = entity_data.copy()
                logger.info(
                    "mock_sos_lookup_found",
                    entity_name=result["entity_name"],
                    entity_number=result["entity_number"],
                )
                return result

        # For names that look like business entities, generate plausible data
        detected_type = self._detect_entity_type(name_lower)
        if detected_type:
            entity_name_upper = entity_name.upper().strip()
            result = {
                "entity_name": entity_name_upper,
                "entity_number": self._generate_entity_number(detected_type),
                "entity_type": detected_type,
                "status": "Active",
                "agent_name": "John Q. Smith",
                "agent_address": "100 Main St, Suite 200, Sacramento, CA 95814",
            }
            logger.info(
                "mock_sos_lookup_generated",
                entity_name=entity_name_upper,
                entity_type=detected_type,
            )
            return result

        # Individual names or unrecognised patterns return None
        logger.info("mock_sos_lookup_not_found", entity_name=entity_name)
        return None

    def _detect_entity_type(self, name_lower: str) -> str | None:
        """Detect the entity type from common naming patterns."""
        for pattern, entity_type in self._ENTITY_TYPE_PATTERNS:
            if re.search(pattern, name_lower):
                return entity_type
        return None

    @staticmethod
    def _generate_entity_number(entity_type: str) -> str:
        """Generate a plausible CA SOS entity number based on type."""
        if entity_type == "LLC":
            return "202300112233"
        if entity_type == "LP":
            return "LP202300445566"
        # Corp / Trust / default
        return "C9988776"
