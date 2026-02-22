"""Contact confidence scoring for owner identification results.

Computes a weighted confidence score (0.0 -- 1.0) based on four
factors that reflect how reliably we have identified the property
owner and their contact information.

Scoring Factors & Weights
-------------------------
- **name_match** (30%): How well the assessor name matches the SOS entity.
    - 1.0  exact match (case-insensitive)
    - 0.8  close match (e.g. abbreviation differences)
    - 0.5  partial match (one name token appears in the other)
    - 0.0  no match / SOS entity not found

- **sos_status** (20%): Status of the entity on the CA SOS records.
    - 1.0  Active
    - 0.5  Inactive / Suspended / Dissolved
    - 0.0  Not Found

- **email_quality** (30%): Quality of the discovered email contact.
    - 1.0  Verified (Hunter.io status = "valid")
    - 0.6  Found but unverified
    - 0.0  Not found

- **phone_quality** (20%): Quality of the discovered phone contact.
    - 1.0  Direct phone number available
    - 0.7  Company/general phone number
    - 0.0  Not found
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Factor weights -- must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "name_match": 0.30,
    "sos_status": 0.20,
    "email_quality": 0.30,
    "phone_quality": 0.20,
}


class ContactConfidenceScorer:
    """Computes a weighted confidence score for owner contact records."""

    # Exposed as class attributes so tests can inspect / override if needed.
    WEIGHTS = _WEIGHTS

    # ---- name_match mappings ----
    NAME_MATCH_EXACT: float = 1.0
    NAME_MATCH_CLOSE: float = 0.8
    NAME_MATCH_PARTIAL: float = 0.5
    NAME_MATCH_NONE: float = 0.0

    # ---- sos_status mappings ----
    SOS_ACTIVE: float = 1.0
    SOS_INACTIVE: float = 0.5
    SOS_NOT_FOUND: float = 0.0

    # ---- email_quality mappings ----
    EMAIL_VERIFIED: float = 1.0
    EMAIL_FOUND_UNVERIFIED: float = 0.6
    EMAIL_NOT_FOUND: float = 0.0

    # ---- phone_quality mappings ----
    PHONE_DIRECT: float = 1.0
    PHONE_COMPANY: float = 0.7
    PHONE_NOT_FOUND: float = 0.0

    def compute(self, factors: dict) -> tuple[float, dict]:
        """Compute the overall confidence score.

        Parameters
        ----------
        factors : dict
            A dictionary with keys corresponding to the scoring factors:
                - name_match (float): 0.0 -- 1.0
                - sos_status (float): 0.0 -- 1.0
                - email_quality (float): 0.0 -- 1.0
                - phone_quality (float): 0.0 -- 1.0

            Missing keys default to 0.0.

        Returns
        -------
        tuple[float, dict]
            A tuple of ``(score, factor_details)`` where *score* is the
            overall weighted confidence (0.0 -- 1.0, rounded to 3 decimal
            places) and *factor_details* is a dictionary with each
            factor's raw value, weight, and weighted contribution.
        """
        factor_details: dict[str, dict] = {}
        total_score = 0.0

        for factor_name, weight in self.WEIGHTS.items():
            raw_value = float(factors.get(factor_name, 0.0))
            # Clamp to [0, 1]
            raw_value = max(0.0, min(1.0, raw_value))
            weighted = raw_value * weight

            factor_details[factor_name] = {
                "raw": round(raw_value, 3),
                "weight": weight,
                "weighted": round(weighted, 3),
            }
            total_score += weighted

        score = round(total_score, 3)

        logger.info(
            "confidence_score_computed",
            score=score,
            factors={k: v["raw"] for k, v in factor_details.items()},
        )

        return score, factor_details
