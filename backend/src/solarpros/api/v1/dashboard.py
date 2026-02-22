"""Dashboard overview and funnel endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from solarpros.db.session import get_db
from solarpros.models import EmailCampaign, EmailSend, Property, ProspectScore, SolarAnalysis
from solarpros.schemas import DashboardOverview, FunnelStage

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    """Query counts from properties, solar_analyses, prospect_scores, email_campaigns, and email_sends."""
    # Total properties
    prop_count = (await db.execute(select(func.count(Property.id)))).scalar() or 0

    # Total analyzed (distinct properties with a solar analysis)
    analyzed_count = (
        await db.execute(
            select(func.count(func.distinct(SolarAnalysis.property_id)))
        )
    ).scalar() or 0

    # Total scored (distinct properties with a prospect score)
    scored_count = (
        await db.execute(
            select(func.count(func.distinct(ProspectScore.property_id)))
        )
    ).scalar() or 0

    # Total campaigns
    campaign_count = (await db.execute(select(func.count(EmailCampaign.id)))).scalar() or 0

    # Tier counts
    tier_stmt = select(ProspectScore.tier, func.count(ProspectScore.id)).group_by(ProspectScore.tier)
    tier_result = await db.execute(tier_stmt)
    tier_map = {row[0]: row[1] for row in tier_result.all()}

    # Avg composite score
    avg_score_result = (
        await db.execute(select(func.avg(ProspectScore.composite_score)))
    ).scalar()
    avg_score = round(avg_score_result, 2) if avg_score_result is not None else 0.0

    # Email metrics
    emails_sent = (
        await db.execute(
            select(func.count(EmailSend.id)).where(EmailSend.status != "pending")
        )
    ).scalar() or 0

    total_opens = (
        await db.execute(select(func.count(EmailSend.opened_at)))
    ).scalar() or 0

    total_replies = (
        await db.execute(select(func.count(EmailSend.replied_at)))
    ).scalar() or 0

    return DashboardOverview(
        total_properties=prop_count,
        total_analyzed=analyzed_count,
        total_scored=scored_count,
        total_campaigns=campaign_count,
        tier_a_count=tier_map.get("A", 0),
        tier_b_count=tier_map.get("B", 0),
        tier_c_count=tier_map.get("C", 0),
        avg_score=avg_score,
        total_emails_sent=emails_sent,
        total_opens=total_opens,
        total_replies=total_replies,
    )


@router.get("/funnel", response_model=list[FunnelStage])
async def get_funnel(
    db: AsyncSession = Depends(get_db),
) -> list[FunnelStage]:
    """Return pipeline funnel stages: discovered -> analyzed -> scored -> emailed -> replied."""
    # Stage 1: Discovered (total properties)
    discovered = (await db.execute(select(func.count(Property.id)))).scalar() or 0

    # Stage 2: Analyzed (properties with solar analysis)
    analyzed = (
        await db.execute(
            select(func.count(func.distinct(SolarAnalysis.property_id)))
        )
    ).scalar() or 0

    # Stage 3: Scored (properties with prospect score)
    scored = (
        await db.execute(
            select(func.count(func.distinct(ProspectScore.property_id)))
        )
    ).scalar() or 0

    # Stage 4: Emailed (distinct prospects that have been emailed, i.e. have an EmailSend)
    emailed = (
        await db.execute(
            select(func.count(func.distinct(EmailSend.prospect_score_id)))
        )
    ).scalar() or 0

    # Stage 5: Replied (distinct prospects that have a reply)
    replied = (
        await db.execute(
            select(func.count(func.distinct(EmailSend.prospect_score_id))).where(
                EmailSend.replied_at.isnot(None)
            )
        )
    ).scalar() or 0

    stages = [
        ("discovered", discovered),
        ("analyzed", analyzed),
        ("scored", scored),
        ("emailed", emailed),
        ("replied", replied),
    ]

    funnel: list[FunnelStage] = []
    for i, (stage_name, count) in enumerate(stages):
        if i == 0:
            conversion_rate = 1.0
        else:
            prev_count = stages[i - 1][1]
            conversion_rate = round(count / prev_count, 4) if prev_count > 0 else 0.0
        funnel.append(
            FunnelStage(stage=stage_name, count=count, conversion_rate=conversion_rate)
        )

    return funnel
