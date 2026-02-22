"""Scrapers for county assessor property data."""

from solarpros.agents.property_discovery.scrapers.base import BaseScraper
from solarpros.agents.property_discovery.scrapers.la_county import LACountyScraper
from solarpros.agents.property_discovery.scrapers.mock import MockScraper
from solarpros.agents.property_discovery.scrapers.orange_county import OrangeCountyScraper
from solarpros.agents.property_discovery.scrapers.riverside import RiversideCountyScraper
from solarpros.agents.property_discovery.scrapers.san_bernardino import (
    SanBernardinoCountyScraper,
)
from solarpros.agents.property_discovery.scrapers.san_diego import SanDiegoCountyScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "Los Angeles": LACountyScraper,
    "Orange": OrangeCountyScraper,
    "San Diego": SanDiegoCountyScraper,
    "Riverside": RiversideCountyScraper,
    "San Bernardino": SanBernardinoCountyScraper,
}

__all__ = [
    "BaseScraper",
    "LACountyScraper",
    "MockScraper",
    "OrangeCountyScraper",
    "RiversideCountyScraper",
    "SanBernardinoCountyScraper",
    "SanDiegoCountyScraper",
    "SCRAPER_REGISTRY",
]
