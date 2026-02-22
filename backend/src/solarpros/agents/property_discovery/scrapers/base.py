"""Base scraper interface for property discovery."""

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Abstract base class for county property scrapers.

    Provides a common interface for scraping commercial property data
    from county assessor websites. Subclasses must implement the
    ``scrape`` method for a single page of results.

    Supports async context manager usage::

        async with MyScraper("Los Angeles") as scraper:
            properties = await scraper.scrape_all(max_pages=5)
    """

    county_name: str

    def __init__(self, county_name: str) -> None:
        self.county_name = county_name
        self.log = logger.bind(scraper=self.__class__.__name__, county=county_name)

    async def setup(self) -> None:
        """Initialize resources such as a Playwright browser.

        The default implementation is a no-op, suitable for scrapers
        that do not need browser automation (e.g. mock scrapers).
        """

    async def teardown(self) -> None:
        """Release resources such as a Playwright browser.

        The default implementation is a no-op.
        """

    @abstractmethod
    async def scrape(self, page_num: int) -> list[dict]:
        """Scrape a single page of property results.

        Args:
            page_num: The 1-based page number to scrape.

        Returns:
            A list of property dicts, each containing at minimum:
            apn, address, county, zoning, building_sqft, roof_sqft,
            year_built, building_type, owner_name_raw.
        """

    async def scrape_all(self, max_pages: int = 10) -> list[dict]:
        """Iterate through pages and collect all scraped properties.

        Args:
            max_pages: Maximum number of pages to scrape. Stops early
                       if a page returns no results.

        Returns:
            Aggregated list of property dicts from all pages.
        """
        all_properties: list[dict] = []

        for page_num in range(1, max_pages + 1):
            self.log.info("scraping_page", page=page_num, max_pages=max_pages)
            try:
                page_results = await self.scrape(page_num)
            except Exception:
                self.log.exception("scrape_page_failed", page=page_num)
                break

            if not page_results:
                self.log.info("no_more_results", last_page=page_num)
                break

            all_properties.extend(page_results)
            self.log.info(
                "page_scraped",
                page=page_num,
                page_count=len(page_results),
                total_count=len(all_properties),
            )

        return all_properties

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "BaseScraper":
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        await self.teardown()
