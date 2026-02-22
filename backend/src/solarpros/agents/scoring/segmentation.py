TIER_THRESHOLDS: dict[str, int] = {"A": 75, "B": 50}


def assign_tier(composite_score: float) -> str:
    """Assign a tier letter based on composite score thresholds."""
    if composite_score >= TIER_THRESHOLDS["A"]:
        return "A"
    if composite_score >= TIER_THRESHOLDS["B"]:
        return "B"
    return "C"


def segment_prospects(scores: list[dict]) -> dict[str, list]:
    """Group a list of scored prospect dicts by their tier."""
    segments: dict[str, list] = {"A": [], "B": [], "C": []}
    for score in scores:
        tier = score.get("tier", assign_tier(score.get("composite_score", 0)))
        segments.setdefault(tier, []).append(score)
    return segments
