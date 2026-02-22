"""Solar Analysis Agent -- Phase 3 of the SolarPros pipeline.

Fetches solar potential data for a property (Google Solar first, PVWatts as
fallback), runs a financial analysis, and persists the results as a
``SolarAnalysis`` row in the database.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select

from solarpros.agents.base import BaseAgent
from solarpros.config import settings
from solarpros.db.session import async_session_factory
from solarpros.models.property import Property
from solarpros.models.solar_analysis import SolarAnalysis

from .calculator import SolarFinancialCalculator
from .google_solar import GoogleSolarClient, MockGoogleSolarClient
from .pvwatts import MockPVWattsClient, PVWattsClient

logger = structlog.get_logger()

# Default system size assumed when Google Solar is unavailable and we need
# to call PVWatts without a prior roof-derived estimate.
_DEFAULT_SYSTEM_SIZE_KW = 100.0


class SolarAnalysisAgent(BaseAgent):
    """Analyse a property's solar potential and financial viability."""

    agent_type: str = "solar_analysis"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Choose real vs. mock clients based on config.
        if settings.use_mock_apis:
            self.google_client = MockGoogleSolarClient()
            self.pvwatts_client = MockPVWattsClient()
        else:
            self.google_client = GoogleSolarClient()
            self.pvwatts_client = PVWattsClient()

        self.calculator = SolarFinancialCalculator()

    async def execute(self, **kwargs) -> dict:
        """Run solar analysis for a single property.

        Parameters
        ----------
        property_id : str | uuid.UUID
            The UUID of the property to analyse.

        Returns
        -------
        dict
            A summary including items_processed, data_source, and the
            financial metrics.
        """
        property_id = kwargs.get("property_id")
        if not property_id:
            raise ValueError("property_id is required")

        property_id = uuid.UUID(str(property_id))
        self.log = self.log.bind(property_id=str(property_id))

        # ------------------------------------------------------------------
        # 1. Load property from DB
        # ------------------------------------------------------------------
        async with async_session_factory() as session:
            result = await session.execute(
                select(Property).where(Property.id == property_id)
            )
            prop = result.scalar_one_or_none()

        if not prop:
            raise ValueError(f"Property {property_id} not found")

        if not prop.latitude or not prop.longitude:
            raise ValueError(
                f"Property {property_id} has no coordinates (latitude/longitude)"
            )

        self.log.info(
            "solar_analysis_start",
            address=prop.address,
            county=prop.county,
        )

        # ------------------------------------------------------------------
        # 2. Fetch solar data (Google Solar -> PVWatts fallback)
        # ------------------------------------------------------------------
        solar_data, data_source = await self._fetch_solar_data(
            prop.latitude, prop.longitude
        )

        system_size_kw = solar_data.get("system_size_kw", _DEFAULT_SYSTEM_SIZE_KW)
        annual_kwh = solar_data.get("annual_kwh", 0.0)

        # ------------------------------------------------------------------
        # 3. Financial analysis
        # ------------------------------------------------------------------
        financials = self.calculator.calculate(
            system_size_kw=system_size_kw,
            annual_kwh=annual_kwh,
            county=prop.county,
        )

        # ------------------------------------------------------------------
        # 4. Persist SolarAnalysis to DB
        # ------------------------------------------------------------------
        analysis = SolarAnalysis(
            property_id=property_id,
            data_source=data_source,
            usable_roof_sqft=solar_data.get("usable_roof_sqft"),
            pitch=solar_data.get("pitch"),
            azimuth=solar_data.get("azimuth"),
            sunshine_hours=solar_data.get("sunshine_hours"),
            system_size_kw=system_size_kw,
            annual_kwh=annual_kwh,
            utility_rate=financials["utility_rate"],
            annual_savings=financials["annual_savings"],
            system_cost=financials["system_cost"],
            net_cost=financials["net_cost"],
            payback_years=financials["payback_years"],
            raw_response=solar_data.get("raw_response"),
        )

        async with async_session_factory() as session:
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)

        self.log.info(
            "solar_analysis_complete",
            data_source=data_source,
            system_size_kw=system_size_kw,
            annual_kwh=annual_kwh,
            payback_years=financials["payback_years"],
        )

        return {
            "items_processed": 1,
            "items_failed": 0,
            "property_id": str(property_id),
            "data_source": data_source,
            "system_size_kw": system_size_kw,
            "annual_kwh": annual_kwh,
            **financials,
        }

    async def _fetch_solar_data(
        self, latitude: float, longitude: float
    ) -> tuple[dict, str]:
        """Try Google Solar first, fall back to PVWatts on any error.

        Returns
        -------
        tuple[dict, str]
            (solar_data_dict, data_source_name)
        """
        # Attempt Google Solar API first.
        try:
            data = await self.google_client.get_solar_data(latitude, longitude)
            return data, "google_solar"
        except Exception as exc:
            self.log.warning(
                "google_solar_failed_falling_back_to_pvwatts",
                error=str(exc),
                error_type=type(exc).__name__,
            )

        # Fallback: PVWatts with a default system size.
        try:
            data = await self.pvwatts_client.get_solar_data(
                latitude, longitude, _DEFAULT_SYSTEM_SIZE_KW
            )
            # PVWatts does not provide roof geometry; fill in defaults.
            data.setdefault("system_size_kw", _DEFAULT_SYSTEM_SIZE_KW)
            return data, "pvwatts"
        except Exception as exc:
            self.log.error(
                "pvwatts_also_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
