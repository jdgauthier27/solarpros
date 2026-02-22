"""Filters for identifying qualifying commercial properties."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Zoning code prefixes that indicate commercial use, keyed by county.
COMMERCIAL_ZONING_PREFIXES: dict[str, list[str]] = {
    "Los Angeles": ["C-1", "C-2", "C-3", "C-M", "M-1", "M-2", "C1", "C2", "C3", "CM", "M1", "M2"],
    "Orange": ["C1", "C2", "C3", "CM", "M1", "M2", "C-1", "C-2", "C-3", "C-M", "M-1", "M-2"],
    "San Bernardino": ["C-1", "C-2", "C-3", "C-M", "M-1", "M-2", "CG", "CR", "CS"],
    "Riverside": ["C-1", "C-2", "C-P", "C-M", "M-1", "M-2", "I-P"],
    "San Diego": ["C-1", "C-2", "C-3", "C-M", "M-1", "M-2", "CC", "CN", "CR", "CV"],
    "Ventura": ["C-1", "C-2", "C-3", "M-1", "M-2", "CPD"],
}

# Fallback prefixes used when the county is not in the mapping above.
_DEFAULT_COMMERCIAL_PREFIXES = ["C-", "C1", "C2", "C3", "M-", "M1", "M2", "CM"]

# Minimum roof square footage for a property to qualify.
MIN_ROOF_SQFT: float = 5000.0


# ---------------------------------------------------------------------------
# Filter functions
# ---------------------------------------------------------------------------


def is_commercial(zoning: str, county: str) -> bool:
    """Check whether a zoning code indicates commercial use.

    The check is case-insensitive and matches against known prefixes
    for the specified county.  Falls back to default prefixes if the
    county is not explicitly configured.

    Args:
        zoning: The zoning code string (e.g. "C-2", "M-1").
        county: The county name (e.g. "Los Angeles").

    Returns:
        ``True`` if the zoning code starts with a known commercial prefix.
    """
    if not zoning:
        return False

    zoning_upper = zoning.upper().strip()
    prefixes = COMMERCIAL_ZONING_PREFIXES.get(county, _DEFAULT_COMMERCIAL_PREFIXES)

    return any(zoning_upper.startswith(p.upper()) for p in prefixes)


def meets_roof_minimum(roof_sqft: float | None) -> bool:
    """Check whether a property's roof meets the minimum square footage.

    Args:
        roof_sqft: Roof area in square feet, or ``None`` if unknown.

    Returns:
        ``True`` if *roof_sqft* is at least :data:`MIN_ROOF_SQFT`.
    """
    if roof_sqft is None:
        return False
    return roof_sqft >= MIN_ROOF_SQFT


def filter_properties(properties: list[dict], county: str | None = None) -> list[dict]:
    """Apply commercial zoning and roof minimum filters.

    Each property dict is expected to have ``zoning``, ``roof_sqft``,
    and ``county`` keys.  The *county* argument can override the
    per-property county for filtering when all properties belong to the
    same county.

    Args:
        properties: List of raw property dicts from a scraper.
        county: Optional county override applied to all properties.

    Returns:
        Filtered list containing only qualifying properties.  Each
        qualifying dict is augmented with ``is_commercial`` and
        ``meets_roof_min`` boolean flags set to ``True``.
    """
    qualifying: list[dict] = []

    for prop in properties:
        prop_county = county or prop.get("county", "")
        prop_zoning = prop.get("zoning", "")
        prop_roof = prop.get("roof_sqft")

        commercial = is_commercial(prop_zoning, prop_county)
        roof_ok = meets_roof_minimum(prop_roof)

        if commercial and roof_ok:
            prop["is_commercial"] = True
            prop["meets_roof_min"] = True
            qualifying.append(prop)

    logger.info(
        "properties_filtered",
        total=len(properties),
        qualifying=len(qualifying),
        county=county,
    )
    return qualifying
