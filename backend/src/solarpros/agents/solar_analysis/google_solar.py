"""Google Solar API client for retrieving building solar potential data.

Uses the Building Insights endpoint to get roof geometry, sunshine hours,
and recommended system sizing for a given coordinate pair.

See: https://developers.google.com/maps/documentation/solar/
"""

from __future__ import annotations

import random

import aiohttp
import structlog

from solarpros.config import settings
from solarpros.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()

GOOGLE_SOLAR_BASE_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"

# Circuit breaker shared across all GoogleSolarClient instances in the process.
_google_solar_breaker = CircuitBreaker(
    name="google_solar",
    failure_threshold=5,
    recovery_timeout=60.0,
)


class GoogleSolarClient:
    """Async client for the Google Solar Building Insights API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.google_solar_api_key
        self.log = logger.bind(client="google_solar")

    async def get_solar_data(self, latitude: float, longitude: float) -> dict:
        """Fetch solar potential data for the given coordinates.

        Parameters
        ----------
        latitude:
            Property latitude in decimal degrees.
        longitude:
            Property longitude in decimal degrees.

        Returns
        -------
        dict
            Parsed solar data with keys: usable_roof_sqft, pitch, azimuth,
            sunshine_hours, system_size_kw, annual_kwh, raw_response.

        Raises
        ------
        aiohttp.ClientError
            On network or HTTP errors (after circuit breaker evaluation).
        """
        return await _google_solar_breaker.call(
            self._fetch, latitude, longitude
        )

    async def _fetch(self, latitude: float, longitude: float) -> dict:
        """Internal fetch method executed through the circuit breaker."""
        params = {
            "location.latitude": latitude,
            "location.longitude": longitude,
            "requiredQuality": "HIGH",
            "key": self.api_key,
        }

        self.log.info(
            "google_solar_request",
            latitude=latitude,
            longitude=longitude,
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                GOOGLE_SOLAR_BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                raw = await resp.json()

        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: dict) -> dict:
        """Extract the fields we care about from the API response.

        The Google Solar API returns a deeply nested structure.  We pull
        out the most useful values for downstream financial analysis.
        """
        solar_potential = raw.get("solarPotential", {})

        # Roof segment data -- aggregate across all segments.
        roof_segments = solar_potential.get("roofSegmentStats", [])
        total_roof_sqft = sum(
            seg.get("stats", {}).get("areaMeters2", 0) * 10.7639
            for seg in roof_segments
        )

        # Use the primary (largest) segment for pitch and azimuth.
        primary_segment = max(
            roof_segments,
            key=lambda s: s.get("stats", {}).get("areaMeters2", 0),
            default={},
        )
        pitch = primary_segment.get("pitchDegrees", 0.0)
        azimuth = primary_segment.get("azimuthDegrees", 180.0)

        # Sunshine hours (annual, from the whole-roof stats).
        whole_roof_stats = solar_potential.get("wholeRoofStats", {})
        sunshine_hours = whole_roof_stats.get("sunshineQuantiles", [0] * 12)
        avg_sunshine_hours = (
            sunshine_hours[-1] if sunshine_hours else 0.0
        )

        # Best panel configuration.
        solar_panel_configs = solar_potential.get("solarPanelConfigs", [])
        best_config = solar_panel_configs[-1] if solar_panel_configs else {}
        panels_count = best_config.get("panelsCount", 0)
        # Each panel is roughly 400W.
        system_size_kw = round(panels_count * 0.4, 2)
        annual_kwh = best_config.get(
            "yearlyEnergyDcKwh", system_size_kw * avg_sunshine_hours * 0.78
        )

        return {
            "usable_roof_sqft": round(total_roof_sqft, 1),
            "pitch": round(pitch, 1),
            "azimuth": round(azimuth, 1),
            "sunshine_hours": round(avg_sunshine_hours, 1),
            "system_size_kw": system_size_kw,
            "annual_kwh": round(annual_kwh, 1),
            "raw_response": raw,
        }


class MockGoogleSolarClient:
    """Returns realistic mock data for development and testing.

    The mock values are slightly randomized so that different coordinates
    produce plausible but varied results.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.log = logger.bind(client="mock_google_solar")

    async def get_solar_data(self, latitude: float, longitude: float) -> dict:
        """Return synthetic solar data based on the latitude seed."""
        self.log.info(
            "mock_google_solar_request",
            latitude=latitude,
            longitude=longitude,
        )

        # Use latitude as a seed so the same property always gets the same
        # results, while different properties get slightly different ones.
        rng = random.Random(int(latitude * 10000))

        usable_roof_sqft = round(rng.uniform(3000, 15000), 1)
        pitch = round(rng.uniform(5, 25), 1)
        azimuth = round(rng.uniform(150, 210), 1)
        sunshine_hours = round(rng.uniform(1600, 2100), 1)
        system_size_kw = round(rng.uniform(50, 200), 2)
        annual_kwh = round(system_size_kw * sunshine_hours * 0.78, 1)

        return {
            "usable_roof_sqft": usable_roof_sqft,
            "pitch": pitch,
            "azimuth": azimuth,
            "sunshine_hours": sunshine_hours,
            "system_size_kw": system_size_kw,
            "annual_kwh": annual_kwh,
            "raw_response": {
                "_mock": True,
                "latitude": latitude,
                "longitude": longitude,
            },
        }
