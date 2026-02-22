"""Financial calculator for commercial solar installations.

Takes solar production data (system size, annual kWh) and a county name,
then produces savings estimates, system cost, payback period, and 25-year ROI
based on local utility rates and the federal Investment Tax Credit (ITC).
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

UTILITY_RATES: dict[str, float] = {
    "SDGE": 0.38,   # $/kWh -- San Diego Gas & Electric
    "SCE": 0.28,    # $/kWh -- Southern California Edison
    "LADWP": 0.22,  # $/kWh -- LA Dept of Water & Power
}

COUNTY_UTILITY_MAP: dict[str, str] = {
    "Los Angeles": "LADWP",
    "Orange": "SCE",
    "San Diego": "SDGE",
    "Riverside": "SCE",
    "San Bernardino": "SCE",
}

ITC_RATE: float = 0.30          # 30% federal Investment Tax Credit
COST_PER_WATT: float = 2.50    # $/W installed (commercial)

# System lifetime for ROI calculations.
SYSTEM_LIFETIME_YEARS: int = 25

# Annual panel degradation rate.
ANNUAL_DEGRADATION: float = 0.005  # 0.5% per year


class SolarFinancialCalculator:
    """Compute financial metrics for a proposed solar installation."""

    def __init__(self) -> None:
        self.log = logger.bind(component="solar_financial_calculator")

    @staticmethod
    def get_utility_for_county(county: str) -> str:
        """Return the primary utility for *county*.

        Falls back to ``"SCE"`` for counties not in the mapping.
        """
        return COUNTY_UTILITY_MAP.get(county, "SCE")

    def calculate(
        self,
        system_size_kw: float,
        annual_kwh: float,
        county: str,
    ) -> dict:
        """Run the full financial analysis.

        Parameters
        ----------
        system_size_kw:
            Nameplate DC system capacity in kW.
        annual_kwh:
            Estimated first-year energy production in kWh.
        county:
            County name (used to look up the local utility rate).

        Returns
        -------
        dict
            Financial metrics:
            - utility: utility code (e.g. "SDGE")
            - utility_rate: $/kWh
            - annual_savings: first-year dollar savings
            - system_cost: gross installed cost before incentives
            - net_cost: cost after federal ITC
            - payback_years: simple payback in years
            - roi_25yr: cumulative 25-year ROI as a decimal (e.g. 2.5 = 250%)
        """
        utility = self.get_utility_for_county(county)
        utility_rate = UTILITY_RATES.get(utility, 0.28)

        annual_savings = round(annual_kwh * utility_rate, 2)
        system_cost = round(system_size_kw * 1000 * COST_PER_WATT, 2)
        net_cost = round(system_cost * (1 - ITC_RATE), 2)

        payback_years = (
            round(net_cost / annual_savings, 1) if annual_savings > 0 else 0.0
        )

        # 25-year cumulative savings accounting for panel degradation.
        cumulative_savings = 0.0
        for year in range(1, SYSTEM_LIFETIME_YEARS + 1):
            degradation_factor = (1 - ANNUAL_DEGRADATION) ** (year - 1)
            cumulative_savings += annual_kwh * degradation_factor * utility_rate

        roi_25yr = (
            round((cumulative_savings - net_cost) / net_cost, 2)
            if net_cost > 0
            else 0.0
        )

        self.log.info(
            "financial_calculation",
            county=county,
            utility=utility,
            system_size_kw=system_size_kw,
            annual_savings=annual_savings,
            payback_years=payback_years,
            roi_25yr=roi_25yr,
        )

        return {
            "utility": utility,
            "utility_rate": utility_rate,
            "annual_savings": annual_savings,
            "system_cost": system_cost,
            "net_cost": net_cost,
            "payback_years": payback_years,
            "roi_25yr": roi_25yr,
        }
