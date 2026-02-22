"""Request/response schemas for dashboard endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_properties: int = 0
    total_analyzed: int = 0
    total_scored: int = 0
    total_campaigns: int = 0
    tier_a_count: int = 0
    tier_b_count: int = 0
    tier_c_count: int = 0
    avg_score: float = 0.0
    total_emails_sent: int = 0
    total_opens: int = 0
    total_replies: int = 0


class FunnelStage(BaseModel):
    stage: str
    count: int
    conversion_rate: float = 0.0
