"""Buying role classification using Claude Haiku.

Classifies each contact into one of:
  - economic_buyer: Signs the check / approves budget
  - champion: Internal advocate who pushes the deal
  - technical_evaluator: Evaluates technical feasibility
  - financial_evaluator: Analyzes ROI / financial justification
  - influencer: Has influence but not decision authority
"""

from __future__ import annotations

import re

import structlog
from pydantic import BaseModel, Field

from solarpros.config import settings

logger = structlog.get_logger()

BUYING_ROLES = [
    "economic_buyer",
    "champion",
    "technical_evaluator",
    "financial_evaluator",
    "influencer",
]

# Title patterns for heuristic classification
_ROLE_PATTERNS: list[tuple[str, str]] = [
    # Economic buyers
    (r"\bceo\b", "economic_buyer"),
    (r"\bpresident\b", "economic_buyer"),
    (r"\bowner\b", "economic_buyer"),
    (r"\bmanaging\s+partner\b", "economic_buyer"),
    (r"\bmanaging\s+director\b", "economic_buyer"),
    (r"\bprincipal\b", "economic_buyer"),
    (r"\bgeneral\s+manager\b", "economic_buyer"),
    # Champions
    (r"\bfacilities\s+manager\b", "champion"),
    (r"\bfacilities\s+director\b", "champion"),
    (r"\bdirector\s+of\s+facilities\b", "champion"),
    (r"\bproperty\s+manager\b", "champion"),
    (r"\bdirector\s+of\s+operations\b", "champion"),
    (r"\bvp\s+of?\s*operations\b", "champion"),
    (r"\boperations\s+manager\b", "champion"),
    (r"\bsustainability\b", "champion"),
    # Technical evaluators
    (r"\bcoo\b", "technical_evaluator"),
    (r"\bdirector\s+of\s+development\b", "technical_evaluator"),
    (r"\bengineering\b", "technical_evaluator"),
    (r"\btechnical\b", "technical_evaluator"),
    (r"\bconstruction\b", "technical_evaluator"),
    (r"\barchitect\b", "technical_evaluator"),
    # Financial evaluators
    (r"\bcfo\b", "financial_evaluator"),
    (r"\bfinance\b", "financial_evaluator"),
    (r"\bcontroller\b", "financial_evaluator"),
    (r"\btreasurer\b", "financial_evaluator"),
    (r"\baccounting\b", "financial_evaluator"),
    # Influencers
    (r"\bsenior\s+partner\b", "influencer"),
    (r"\bassistant\b", "influencer"),
    (r"\bsecretary\b", "influencer"),
    (r"\bagent\b", "influencer"),
]


class ClassifiedRole(BaseModel):
    """Structured output from the LLM role classifier."""

    buying_role: str = Field(description="One of: economic_buyer, champion, technical_evaluator, financial_evaluator, influencer")
    confidence: float = Field(description="Confidence 0.0-1.0 in the classification")
    reasoning: str = Field(description="Brief explanation of why this role was assigned")


def classify_role_heuristic(title: str | None, department: str | None = None) -> str:
    """Classify buying role using title pattern matching.

    Falls back to 'influencer' if no patterns match.
    """
    if not title:
        return "influencer"

    combined = f"{title} {department or ''}".lower().strip()

    for pattern, role in _ROLE_PATTERNS:
        if re.search(pattern, combined):
            return role

    return "influencer"


async def classify_role_llm(
    contact_name: str,
    title: str | None,
    company_name: str | None,
    department: str | None = None,
) -> str:
    """Classify buying role using Claude Haiku.

    Falls back to heuristic classification if LLM is unavailable.
    """
    if settings.enrichment_use_mock or not settings.anthropic_api_key:
        return classify_role_heuristic(title, department)

    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a B2B sales intelligence expert. Classify this contact into exactly one buying role "
                "based on their title and company context.\n\n"
                "Roles:\n"
                "- economic_buyer: Has budget authority. CEO, President, Owner, Managing Partner, Managing Director, General Manager.\n"
                "- champion: Internal advocate for solar adoption. Facilities Manager, Property Manager, Director of Operations, VP Operations, Sustainability roles.\n"
                "- technical_evaluator: Evaluates technical feasibility. COO, Director of Development, Engineering, Construction, Architect.\n"
                "- financial_evaluator: Analyzes ROI. CFO, Controller, Treasurer, Finance Director.\n"
                "- influencer: Has influence but not direct authority. Other roles.\n\n"
                "Return ONLY the role name, nothing else.",
            ),
            (
                "human",
                "Contact: {name}\nTitle: {title}\nCompany: {company}\nDepartment: {department}",
            ),
        ])

        llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=50,
        )

        chain = prompt | llm
        result = await chain.ainvoke({
            "name": contact_name,
            "title": title or "Unknown",
            "company": company_name or "Unknown",
            "department": department or "Unknown",
        })

        role = result.content.strip().lower()
        if role in BUYING_ROLES:
            return role

        # If LLM returned something unexpected, fall back to heuristic
        return classify_role_heuristic(title, department)

    except Exception as exc:
        logger.warning("role_classification_llm_error", error=str(exc))
        return classify_role_heuristic(title, department)
