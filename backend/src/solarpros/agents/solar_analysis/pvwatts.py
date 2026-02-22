"""NREL PVWatts V8 API client -- fallback solar data source.

Used when the Google Solar API is unavailable (circuit breaker open, missing
API key, or unsupported location).  PVWatts provides energy production
estimates based on coordinates and system capacity.

See: https://developer.nrel.gov/docs/solar/pvwatts/v8/
"""

from __future__ import annotations

import random

import aiohttp
import structlog

from solarpros.config import settings
from solarpros.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()

PVWATTS_BASE_URL = "https://developer.nrel.gov/api/pvwatts/v8.json"

_pvwatts_breaker = CircuitBreaker(
    name="pvwatts",
    failure_threshold=5,
    recovery_timeout=60.0,
)


class PVWattsClient:
    """Async client for the NREL PVWatts V8 API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.nrel_api_key
        self.log = logger.bind(client="pvwatts")

    async def get_solar_data(
        self,
        latitude: float,
        longitude: float,
        system_capacity_kw: float,
    ) -> dict:
        """Fetch PVWatts energy production estimate.

        Parameters
        ----------
        latitude:
            Property latitude in decimal degrees.
        longitude:
            Property longitude in decimal degrees.
        system_capacity_kw:
            Nameplate DC system capacity in kW (e.g. 100.0).

        Returns
        -------
        dict
            Parsed data with keys: annual_kwh, sunshine_hours, raw_response.
        """
        return await _pvwatts_breaker.call(
            self._fetch, latitude, longitude, system_capacity_kw
        )

    async def _fetch(
        self,
        latitude: float,
        longitude: float,
        system_capacity_kw: float,
    ) -> dict:
        """Internal fetch executed through the circuit breaker."""
        params = {
            "api_key": self.api_key,
            "lat": latitude,
            "lon": longitude,
            "system_capacity": system_capacity_kw,
            "module_type": 1,  # Premium
            "losses": 14.08,
            "array_type": 1,  # Fixed (roof mount)
            "tilt": 20,
            "azimuth": 180,
        }

        self.log.info(
            "pvwatts_request",
            latitude=latitude,
            longitude=longitude,
            system_capacity_kw=system_capacity_kw,
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                PVWATTS_BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                raw = await resp.json()

        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: dict) -> dict:
        """Extract relevant fields from the PVWatts response."""
        outputs = raw.get("outputs", {})
        station_info = raw.get("station_info", {})

        annual_kwh = outputs.get("ac_annual", 0.0)
        # solrad_annual is average daily kWh/m^2/day -- convert to annual hours.
        solrad_annual = outputs.get("solrad_annual", 0.0)
        sunshine_hours = round(solrad_annual * 365, 1)

        return {
            "annual_kwh": round(annual_kwh, 1),
            "sunshine_hours": sunshine_hours,
            "raw_response": raw,
        }


class MockPVWattsClient:
    """Returns realistic mock PVWatts data for development and testing."""

    def __init__(self, api_key: str | None = None) -> None:
        self.log = logger.bind(client="mock_pvwatts")

    async def get_solar_data(
        self,
        latitude: float,
        longitude: float,
        system_capacity_kw: float,
    ) -> dict:
        """Return synthetic PVWatts production data."""
        self.log.info(
            "mock_pvwatts_request",
            latitude=latitude,
            longitude=longitude,
            system_capacity_kw=system_capacity_kw,
        )

        rng = random.Random(int(latitude * 10000))
        sunshine_hours = round(rng.uniform(1600, 2100), 1)
        # Realistic ratio: ~1.4-1.6 kWh per watt for SoCal.
        kwh_per_kw = rng.uniform(1400, 1700)
        annual_kwh = round(system_capacity_kw * kwh_per_kw / 1000 * 1000, 1)

        return {
            "annual_kwh": annual_kwh,
            "sunshine_hours": sunshine_hours,
            "raw_response": {
                "_mock": True,
                "latitude": latitude,
                "longitude": longitude,
                "system_capacity_kw": system_capacity_kw,
            },
        }
