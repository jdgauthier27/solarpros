"""Export scored prospects to CSV."""

import asyncio
import csv
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from solarpros.config import settings
from solarpros.models.owner import Owner
from solarpros.models.property import Property
from solarpros.models.score import ProspectScore
from solarpros.models.solar_analysis import SolarAnalysis


async def export(output_path: str = "prospects.csv", min_score: float = 0.0):
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        query = (
            select(ProspectScore)
            .options(
                selectinload(ProspectScore.property),
                selectinload(ProspectScore.owner),
                selectinload(ProspectScore.solar_analysis),
            )
            .where(ProspectScore.composite_score >= min_score)
            .order_by(ProspectScore.composite_score.desc())
        )
        result = await session.execute(query)
        scores = result.scalars().all()

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Tier",
                "Score",
                "County",
                "Address",
                "Building Type",
                "Roof SqFt",
                "Owner",
                "Entity Type",
                "Email",
                "Email Verified",
                "System Size kW",
                "Annual Savings",
                "Payback Years",
            ])
            for score in scores:
                prop = score.property
                owner = score.owner
                solar = score.solar_analysis
                writer.writerow([
                    score.tier,
                    f"{score.composite_score:.1f}",
                    prop.county if prop else "",
                    prop.address if prop else "",
                    prop.building_type if prop else "",
                    prop.roof_sqft if prop else "",
                    owner.owner_name_clean if owner else "",
                    owner.entity_type if owner else "",
                    owner.email if owner else "",
                    owner.email_verified if owner else "",
                    solar.system_size_kw if solar else "",
                    f"{solar.annual_savings:.0f}" if solar and solar.annual_savings else "",
                    f"{solar.payback_years:.1f}" if solar and solar.payback_years else "",
                ])

        print(f"Exported {len(scores)} prospects to {output_path}")

    await engine.dispose()


if __name__ == "__main__":
    min_score = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    output = sys.argv[2] if len(sys.argv) > 2 else "prospects.csv"
    asyncio.run(export(output, min_score))
