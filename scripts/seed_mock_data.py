"""Seed the database with mock property data for Southern California counties."""

import asyncio
import random
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from solarpros.config import settings

# Mock data for 5 Southern California counties
COUNTIES = {
    "Los Angeles": {
        "cities": ["Los Angeles", "Long Beach", "Pasadena", "Glendale", "Burbank"],
        "lat_range": (33.7, 34.3),
        "lng_range": (-118.7, -117.9),
        "zip_prefixes": ["900", "901", "902", "906", "910", "911"],
    },
    "Orange": {
        "cities": ["Anaheim", "Santa Ana", "Irvine", "Huntington Beach", "Costa Mesa"],
        "lat_range": (33.4, 33.9),
        "lng_range": (-118.1, -117.6),
        "zip_prefixes": ["926", "927", "928"],
    },
    "San Diego": {
        "cities": ["San Diego", "Chula Vista", "Oceanside", "Escondido", "Carlsbad"],
        "lat_range": (32.6, 33.2),
        "lng_range": (-117.3, -116.9),
        "zip_prefixes": ["919", "920", "921"],
    },
    "Riverside": {
        "cities": ["Riverside", "Moreno Valley", "Corona", "Temecula", "Murrieta"],
        "lat_range": (33.5, 34.0),
        "lng_range": (-117.5, -116.8),
        "zip_prefixes": ["925", "951", "952"],
    },
    "San Bernardino": {
        "cities": ["San Bernardino", "Fontana", "Rancho Cucamonga", "Ontario", "Victorville"],
        "lat_range": (34.0, 34.5),
        "lng_range": (-117.6, -117.0),
        "zip_prefixes": ["917", "923", "924"],
    },
}

COMMERCIAL_ZONINGS = ["C-1", "C-2", "C-3", "C-M", "M-1", "M-2", "CR", "CG", "CC"]
BUILDING_TYPES = [
    "Office Building",
    "Retail Center",
    "Warehouse",
    "Industrial",
    "Medical Office",
    "Shopping Center",
    "Mixed Use Commercial",
    "Restaurant",
    "Auto Dealership",
    "Hotel",
]
OWNER_NAMES = [
    "Pacific Properties LLC",
    "SunCoast Realty Inc",
    "Golden State Holdings",
    "Western Commercial Partners",
    "Coastal Ventures LLC",
    "Summit Property Group",
    "Valley Commercial LLC",
    "Harbor Real Estate Corp",
    "Sierra Investment Trust",
    "Desert Sun Properties",
    "Metro Commercial LLC",
    "Bayshore Holdings Inc",
    "Canyon View Partners",
    "Oceanfront Realty Trust",
    "Mountain Peak LLC",
    "Sunrise Capital Group",
    "Blue Sky Properties Inc",
    "Palm Tree Investments",
    "Redwood Realty Corp",
    "Eagle Rock Holdings",
]

STREETS = [
    "Main St",
    "Broadway",
    "Commerce Dr",
    "Industrial Blvd",
    "Business Park Way",
    "Enterprise Ave",
    "Market St",
    "Pacific Coast Hwy",
    "Harbor Blvd",
    "Valley View St",
    "Corporate Center Dr",
    "Technology Dr",
    "Innovation Way",
    "Trade Center Blvd",
    "Gateway Rd",
]


def generate_apn(county: str) -> str:
    return f"{random.randint(1000, 9999)}-{random.randint(100, 999)}-{random.randint(10, 99)}"


def generate_property(county: str, county_data: dict) -> dict:
    city = random.choice(county_data["cities"])
    lat = round(random.uniform(*county_data["lat_range"]), 6)
    lng = round(random.uniform(*county_data["lng_range"]), 6)
    zip_prefix = random.choice(county_data["zip_prefixes"])
    zip_code = f"{zip_prefix}{random.randint(10, 99)}"
    roof_sqft = random.uniform(3000, 80000)
    is_commercial = random.random() > 0.15  # 85% commercial
    meets_roof_min = roof_sqft >= 5000

    return {
        "id": str(uuid.uuid4()),
        "apn": generate_apn(county),
        "county": county,
        "address": f"{random.randint(100, 9999)} {random.choice(STREETS)}",
        "city": city,
        "state": "CA",
        "zip_code": zip_code,
        "latitude": lat,
        "longitude": lng,
        "zoning": random.choice(COMMERCIAL_ZONINGS),
        "building_type": random.choice(BUILDING_TYPES),
        "building_sqft": round(random.uniform(5000, 200000), 0),
        "roof_sqft": round(roof_sqft, 0),
        "year_built": random.randint(1960, 2020),
        "owner_name_raw": random.choice(OWNER_NAMES),
        "is_commercial": is_commercial,
        "meets_roof_min": meets_roof_min,
    }


async def seed():
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if data already exists
        result = await session.execute(text("SELECT COUNT(*) FROM properties"))
        count = result.scalar()
        if count and count > 0:
            print(f"Database already has {count} properties. Skipping seed.")
            return

        # Generate properties
        properties = []
        for county, data in COUNTIES.items():
            num_properties = random.randint(30, 50)
            for _ in range(num_properties):
                properties.append(generate_property(county, data))

        # Insert properties
        for prop in properties:
            lat, lng = prop["latitude"], prop["longitude"]
            await session.execute(
                text("""
                    INSERT INTO properties (
                        id, apn, county, address, city, state, zip_code,
                        latitude, longitude, location,
                        zoning, building_type, building_sqft, roof_sqft,
                        year_built, owner_name_raw, is_commercial, meets_roof_min,
                        created_at, updated_at
                    ) VALUES (
                        :id, :apn, :county, :address, :city, :state, :zip_code,
                        :latitude, :longitude, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                        :zoning, :building_type, :building_sqft, :roof_sqft,
                        :year_built, :owner_name_raw, :is_commercial, :meets_roof_min,
                        NOW(), NOW()
                    )
                """),
                prop,
            )

        await session.commit()
        print(f"Seeded {len(properties)} properties across {len(COUNTIES)} counties.")

        # Print summary
        for county in COUNTIES:
            county_props = [p for p in properties if p["county"] == county]
            commercial = sum(1 for p in county_props if p["is_commercial"])
            meets_roof = sum(1 for p in county_props if p["meets_roof_min"])
            print(
                f"  {county}: {len(county_props)} properties "
                f"({commercial} commercial, {meets_roof} meet roof min)"
            )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
