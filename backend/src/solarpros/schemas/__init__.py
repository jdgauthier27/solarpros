"""Pydantic request/response schemas for the SolarPros API."""

from solarpros.schemas.agent import (
    AgentRunRead,
    PipelineStartRequest,
    PipelineStatusResponse,
)
from solarpros.schemas.campaign import (
    CampaignMetrics,
    EmailCampaignCreate,
    EmailCampaignRead,
    EmailCampaignUpdate,
    EmailSequenceRead,
)
from solarpros.schemas.dashboard import DashboardOverview, FunnelStage
from solarpros.schemas.owner import OptOutRequest, OwnerRead
from solarpros.schemas.property import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    PropertyCreate,
    PropertyDetail,
    PropertyFilter,
    PropertyRead,
    PropertyStats,
)
from solarpros.schemas.score import ProspectScoreRead, ScoreDistribution
from solarpros.schemas.solar import SolarAnalysisRead

__all__ = [
    # Property
    "PropertyCreate",
    "PropertyRead",
    "PropertyDetail",
    "PropertyFilter",
    "PropertyStats",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    # Solar
    "SolarAnalysisRead",
    # Owner
    "OwnerRead",
    "OptOutRequest",
    # Score
    "ProspectScoreRead",
    "ScoreDistribution",
    # Campaign
    "EmailCampaignCreate",
    "EmailCampaignRead",
    "EmailCampaignUpdate",
    "EmailSequenceRead",
    "CampaignMetrics",
    # Agent
    "AgentRunRead",
    "PipelineStartRequest",
    "PipelineStatusResponse",
    # Dashboard
    "DashboardOverview",
    "FunnelStage",
]
