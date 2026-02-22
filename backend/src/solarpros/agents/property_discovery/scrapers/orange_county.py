"""Orange County Assessor scraper using Playwright browser automation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from playwright.async_api import async_playwright

from solarpros.agents.property_discovery.scrapers.base import BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Orange County public records portal configuration
# ---------------------------------------------------------------------------
# NOTE: These URLs may need adjustment as the county website changes.
OC_ASSESSOR_BASE_URL = "https://ocpublicaccess.com"
OC_ASSESSOR_SEARCH_URL = f"{OC_ASSESSOR_BASE_URL}/property-search"

# Timeout for navigation and element waits (ms)
DEFAULT_TIMEOUT_MS = 30_000


class OrangeCountyScraper(BaseScraper):
    """Scrapes commercial property data from the Orange County public records portal.

    Uses Playwright to automate a headless Chromium browser that navigates
    the assessor search interface, filters for commercial properties, and
    parses result tables.
    """

    def __init__(self, county_name: str = "Orange") -> None:
        super().__init__(county_name)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def setup(self) -> None:
        """Launch a headless Chromium browser via Playwright."""
        self.log.info("launching_browser")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        self.log.info("browser_ready")

    async def teardown(self) -> None:
        """Close browser and Playwright resources."""
        self.log.info("closing_browser")
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _navigate_to_search(self) -> None:
        """Navigate to the OC assessor property search page."""
        assert self._page is not None
        await self._page.goto(OC_ASSESSOR_SEARCH_URL, wait_until="networkidle")
        # Wait for the search form to be ready
        await self._page.wait_for_selector("input, form", timeout=DEFAULT_TIMEOUT_MS)

    async def _perform_search(self, page_num: int) -> None:
        """Execute a property search for the given page.

        Searches for commercial zoned properties on the OC public records
        portal.  The actual selectors will need to be tuned to match the
        live site's DOM structure.
        """
        assert self._page is not None

        if page_num == 1:
            # Initial search
            await self._navigate_to_search()

            # Try to interact with the property-type / use-code filter
            try:
                use_type_selector = self._page.locator(
                    "select[name='PropertyType'], select[name='useCode'], "
                    "#PropertyType, #useCode"
                )
                if await use_type_selector.count() > 0:
                    await use_type_selector.first.select_option(label="Commercial")
            except Exception:
                self.log.warning("use_type_selector_not_found")

            # Submit the search form
            try:
                submit_btn = self._page.locator(
                    "button[type='submit'], input[type='submit'], "
                    "button:has-text('Search'), a:has-text('Search')"
                )
                if await submit_btn.count() > 0:
                    await submit_btn.first.click()
                    await self._page.wait_for_load_state("networkidle")
            except Exception:
                self.log.warning("submit_button_not_found")
        else:
            # Paginate to the requested page
            await self._go_to_page(page_num)

    async def _go_to_page(self, page_num: int) -> None:
        """Navigate to a specific results page via pagination controls."""
        assert self._page is not None

        try:
            next_btn = self._page.locator(
                f"a:has-text('{page_num}'), "
                f"button:has-text('{page_num}'), "
                "a:has-text('Next'), button:has-text('Next'), "
                "a.next, .pagination .next"
            )
            if await next_btn.count() > 0:
                await next_btn.first.click()
                await self._page.wait_for_load_state("networkidle")
                # Brief pause to let dynamic content load
                await asyncio.sleep(1)
        except Exception:
            self.log.warning("pagination_failed", target_page=page_num)

    async def _parse_results_table(self) -> list[dict]:
        """Parse the property listing table from the current page.

        Returns:
            List of property dicts extracted from the results table.
        """
        assert self._page is not None
        properties: list[dict] = []

        # Try to locate the results table
        table = self._page.locator(
            "table.results, table.search-results, table.property-list, table"
        )
        if await table.count() == 0:
            self.log.warning("no_results_table_found")
            return properties

        # Get all data rows (skip header)
        rows = table.first.locator("tbody tr, tr:not(:first-child)")
        row_count = await rows.count()

        for i in range(row_count):
            try:
                row = rows.nth(i)
                cells = row.locator("td")
                cell_count = await cells.count()

                if cell_count < 3:
                    continue

                # Extract text from all cells
                cell_texts = []
                for c in range(cell_count):
                    text = await cells.nth(c).inner_text()
                    cell_texts.append(text.strip())

                # Map columns to property fields
                prop = self._map_row_to_property(cell_texts)
                if prop:
                    properties.append(prop)
            except Exception:
                self.log.warning("row_parse_failed", row_index=i)
                continue

        return properties

    def _map_row_to_property(self, cells: list[str]) -> dict | None:
        """Map a table row's cell values to a property dict.

        The column order assumed here is based on the OC public records
        portal layout.  Adjust indices as needed.

        Expected column layout (approximate):
            0: APN
            1: Site Address
            2: City
            3: Zip Code
            4: Use Code / Zoning
            5: Living Area (sqft)
            6: Year Built
            7: Owner Name
        """
        if len(cells) < 4:
            return None

        apn = cells[0] if len(cells) > 0 else ""
        address = cells[1] if len(cells) > 1 else ""
        city = cells[2] if len(cells) > 2 else ""
        zip_code = cells[3] if len(cells) > 3 else ""
        zoning = cells[4] if len(cells) > 4 else ""
        building_sqft_raw = cells[5] if len(cells) > 5 else "0"
        year_built_raw = cells[6] if len(cells) > 6 else "0"
        owner_name = cells[7] if len(cells) > 7 else ""

        # Parse numeric fields
        try:
            building_sqft = float(building_sqft_raw.replace(",", "").strip())
        except (ValueError, AttributeError):
            building_sqft = 0.0

        try:
            year_built = int(year_built_raw.strip())
        except (ValueError, AttributeError):
            year_built = 0

        # Estimate roof sqft as ~40% of building sqft for commercial
        roof_sqft = building_sqft * 0.4

        if not apn or not address:
            return None

        return {
            "apn": apn,
            "county": self.county_name,
            "address": address,
            "city": city,
            "state": "CA",
            "zip_code": zip_code,
            "zoning": zoning,
            "building_type": "",
            "building_sqft": building_sqft,
            "roof_sqft": roof_sqft,
            "year_built": year_built,
            "owner_name_raw": owner_name,
        }

    async def scrape(self, page_num: int) -> list[dict]:
        """Scrape a single page of property results from Orange County.

        Args:
            page_num: 1-based page number.

        Returns:
            List of property dicts parsed from the results table.
        """
        self.log.info("scraping_orange_county_page", page=page_num)

        await self._perform_search(page_num)

        # Polite delay between page loads
        await asyncio.sleep(2)

        properties = await self._parse_results_table()
        self.log.info(
            "orange_county_page_scraped",
            page=page_num,
            properties_found=len(properties),
        )
        return properties
