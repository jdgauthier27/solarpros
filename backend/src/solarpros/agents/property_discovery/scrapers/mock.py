"""Mock scraper that generates realistic fake commercial property data."""

import random

from solarpros.agents.property_discovery.scrapers.base import BaseScraper

# ---------------------------------------------------------------------------
# Realistic SoCal reference data
# ---------------------------------------------------------------------------

_STREET_NAMES = [
    "Sepulveda Blvd",
    "Wilshire Blvd",
    "Century Blvd",
    "Pacific Coast Hwy",
    "Figueroa St",
    "Broadway",
    "Vermont Ave",
    "Western Ave",
    "La Cienega Blvd",
    "Crenshaw Blvd",
    "Olympic Blvd",
    "Sunset Blvd",
    "Hollywood Blvd",
    "Santa Monica Blvd",
    "Ventura Blvd",
    "Sherman Way",
    "Victory Blvd",
    "Van Nuys Blvd",
    "Reseda Blvd",
    "Topanga Canyon Blvd",
    "Harbor Blvd",
    "Beach Blvd",
    "Katella Ave",
    "Imperial Hwy",
    "Rosecrans Ave",
    "Artesia Blvd",
    "Valley Blvd",
    "Garvey Ave",
    "Whittier Blvd",
    "Atlantic Blvd",
]

_CITIES = [
    ("Los Angeles", "90001"),
    ("Los Angeles", "90012"),
    ("Los Angeles", "90015"),
    ("Torrance", "90501"),
    ("Long Beach", "90802"),
    ("Pasadena", "91101"),
    ("Glendale", "91201"),
    ("Burbank", "91502"),
    ("Downey", "90241"),
    ("Inglewood", "90301"),
    ("Hawthorne", "90250"),
    ("Culver City", "90232"),
    ("Pomona", "91766"),
    ("West Covina", "91790"),
    ("Whittier", "90601"),
    ("Alhambra", "91801"),
    ("El Monte", "91731"),
    ("Compton", "90220"),
    ("Carson", "90745"),
    ("Santa Clarita", "91350"),
]

_COMMERCIAL_ZONING_CODES = ["C-1", "C-2", "C-3", "C-M", "M-1", "M-2"]

_BUILDING_TYPES = [
    "Retail Store",
    "Office Building",
    "Warehouse",
    "Shopping Center",
    "Industrial",
    "Medical Office",
    "Restaurant",
    "Auto Repair",
    "Mixed Use Commercial",
    "Light Manufacturing",
    "Flex Space",
    "Distribution Center",
    "Self-Storage",
    "Bank Branch",
    "Strip Mall",
]

_BUSINESS_NAME_PREFIXES = [
    "Pacific",
    "Golden State",
    "West Coast",
    "SoCal",
    "Sunshine",
    "Metro",
    "Valley",
    "Harbor",
    "Eagle",
    "Summit",
    "Premier",
    "Allied",
    "National",
    "Liberty",
    "Atlas",
    "Apex",
    "Crown",
    "Gateway",
    "Pinnacle",
    "Sterling",
]

_BUSINESS_NAME_SUFFIXES = [
    "Properties LLC",
    "Investments Inc",
    "Holdings Corp",
    "Management Co",
    "Enterprises LLC",
    "Group Inc",
    "Partners LP",
    "Realty LLC",
    "Development Corp",
    "Capital Inc",
    "Trust",
    "Associates LLC",
    "Ventures Inc",
    "Commercial LLC",
    "Real Estate LP",
]


def _generate_apn() -> str:
    """Generate a realistic LA County-style APN (####-###-###)."""
    part1 = random.randint(1000, 9999)
    part2 = random.randint(100, 999)
    part3 = random.randint(100, 999)
    return f"{part1}-{part2}-{part3}"


def _generate_address() -> tuple[str, str, str]:
    """Return (street_address, city, zip_code)."""
    number = random.randint(100, 29999)
    street = random.choice(_STREET_NAMES)
    city, zip_code = random.choice(_CITIES)
    return f"{number} {street}", city, zip_code


def _generate_owner_name() -> str:
    """Generate a realistic business/owner name."""
    # ~80% business entity, ~20% personal name
    if random.random() < 0.8:
        prefix = random.choice(_BUSINESS_NAME_PREFIXES)
        suffix = random.choice(_BUSINESS_NAME_SUFFIXES)
        return f"{prefix} {suffix}"
    first = random.choice(
        ["James", "Robert", "Michael", "David", "Maria", "Jennifer", "Linda", "Susan"]
    )
    last = random.choice(
        [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Garcia",
            "Martinez",
            "Lee",
            "Kim",
            "Nguyen",
            "Patel",
        ]
    )
    return f"{last}, {first}"


class MockScraper(BaseScraper):
    """Scraper that generates realistic mock commercial property data.

    Used for development and testing when real county websites are
    unavailable or to avoid hammering live services.
    """

    def __init__(self, county_name: str, seed: int | None = None) -> None:
        super().__init__(county_name)
        self._seed = seed
        self._rng = random.Random(seed)
        self._generated_apns: set[str] = set()

    # setup/teardown are inherited no-ops, which is correct for mock

    def _unique_apn(self) -> str:
        """Generate a unique APN that hasn't been used in this session."""
        while True:
            apn = _generate_apn()
            if apn not in self._generated_apns:
                self._generated_apns.add(apn)
                return apn

    async def scrape(self, page_num: int) -> list[dict]:
        """Generate a page of mock commercial properties.

        Args:
            page_num: Page number (used for seeding reproducibility).

        Returns:
            List of 10-20 property dicts with realistic SoCal data.
        """
        # Seed per-page for reproducibility when a base seed is set
        if self._seed is not None:
            random.seed(self._seed + page_num)
        count = random.randint(10, 20)

        properties: list[dict] = []
        for _ in range(count):
            address, city, zip_code = _generate_address()
            building_sqft = random.randint(5000, 200000)
            # Roof sqft is typically 30-60% of building sqft for commercial
            roof_pct = random.uniform(0.30, 0.60)
            roof_sqft = max(3000, int(building_sqft * roof_pct))
            # Clamp roof sqft to specified range
            roof_sqft = min(roof_sqft, 80000)

            prop = {
                "apn": self._unique_apn(),
                "county": self.county_name,
                "address": address,
                "city": city,
                "state": "CA",
                "zip_code": zip_code,
                "zoning": random.choice(_COMMERCIAL_ZONING_CODES),
                "building_type": random.choice(_BUILDING_TYPES),
                "building_sqft": float(building_sqft),
                "roof_sqft": float(roof_sqft),
                "year_built": random.randint(1960, 2020),
                "owner_name_raw": _generate_owner_name(),
            }
            properties.append(prop)

        self.log.info("mock_page_generated", page=page_num, count=len(properties))
        return properties
