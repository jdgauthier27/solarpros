"""Email personalization using Anthropic Claude.

Uses the Anthropic SDK directly (not LangChain) to adjust tone and add
personalized sentences based on business type, location, and other context.
"""

import re

import anthropic
import structlog

from solarpros.config import settings

logger = structlog.get_logger()

PERSONALIZATION_SYSTEM_PROMPT = """\
You are an expert email copywriter for a commercial solar energy company.
Your job is to take an email template and personalize it for a specific
business prospect.

Rules:
1. Keep the core message and structure intact.
2. Add 1-2 personalized sentences that reference the prospect's specific
   business type, location, or situation.
3. Adjust the tone to be appropriate for the business type (e.g., more formal
   for law firms, more casual for retail).
4. Do NOT change the subject line dramatically - only make minor adjustments.
5. Do NOT remove or alter the compliance footer (everything after the <hr> tag).
6. Do NOT invent financial numbers - use only the values provided in the context.
7. Return ONLY the personalized content with no additional commentary.
"""

PERSONALIZATION_USER_PROMPT = """\
Personalize the following email for this prospect:

CONTEXT:
- Company Name: {company_name}
- Contact Name: {contact_name}
- Business Type: {building_type}
- Entity Type: {entity_type}
- Location: {county} County
- Roof Size: {roof_sqft} sq ft
- Estimated System Size: {system_size} kW
- Estimated Annual Savings: {annual_savings}
- Payback Period: {payback_years} years

SUBJECT LINE:
{subject}

EMAIL BODY:
{body}

Return the personalized version in this exact format:
SUBJECT: <personalized subject>
BODY: <personalized body>
"""


class EmailPersonalizer:
    """Uses Claude to personalize email templates for each prospect."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def personalize(
        self,
        template_subject: str,
        template_body: str,
        context: dict,
    ) -> tuple[str, str]:
        """Personalize an email template using Claude.

        Args:
            template_subject: The subject line template with {{placeholders}}.
            template_body: The body template with {{placeholders}}.
            context: Dict with keys: company_name, contact_name, annual_savings,
                     system_size, payback_years, county, building_type,
                     entity_type, roof_sqft.

        Returns:
            Tuple of (personalized_subject, personalized_body).
        """
        # First do basic placeholder replacement
        subject = _replace_placeholders(template_subject, context)
        body = _replace_placeholders(template_body, context)

        user_prompt = PERSONALIZATION_USER_PROMPT.format(
            company_name=context.get("company_name", ""),
            contact_name=context.get("contact_name", ""),
            building_type=context.get("building_type", "commercial"),
            entity_type=context.get("entity_type", ""),
            county=context.get("county", ""),
            roof_sqft=context.get("roof_sqft", ""),
            system_size=context.get("system_size", ""),
            annual_savings=context.get("annual_savings", ""),
            payback_years=context.get("payback_years", ""),
            subject=subject,
            body=body,
        )

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=PERSONALIZATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            result_text = response.content[0].text
            personalized_subject, personalized_body = _parse_personalization_response(
                result_text, subject, body
            )

            logger.info(
                "email_personalized",
                company_name=context.get("company_name"),
                subject=personalized_subject,
            )
            return personalized_subject, personalized_body

        except Exception as e:
            logger.warning(
                "personalization_failed_using_fallback",
                error=str(e),
                company_name=context.get("company_name"),
            )
            # Fall back to simple placeholder replacement
            return subject, body


class MockEmailPersonalizer:
    """Mock personalizer that does simple {{variable}} placeholder replacement."""

    async def personalize(
        self,
        template_subject: str,
        template_body: str,
        context: dict,
    ) -> tuple[str, str]:
        """Replace {{variable}} placeholders with context values."""
        subject = _replace_placeholders(template_subject, context)
        body = _replace_placeholders(template_body, context)
        logger.info(
            "mock_email_personalized",
            company_name=context.get("company_name"),
            subject=subject,
        )
        return subject, body


def _replace_placeholders(template: str, context: dict) -> str:
    """Replace all {{variable}} placeholders in a template string."""
    result = template
    for key, value in context.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    return result


def _parse_personalization_response(
    response_text: str,
    fallback_subject: str,
    fallback_body: str,
) -> tuple[str, str]:
    """Parse Claude's response into subject and body.

    Expected format:
        SUBJECT: <subject>
        BODY: <body>
    """
    subject_match = re.search(r"SUBJECT:\s*(.+?)(?:\nBODY:)", response_text, re.DOTALL)
    body_match = re.search(r"BODY:\s*(.+)", response_text, re.DOTALL)

    subject = subject_match.group(1).strip() if subject_match else fallback_subject
    body = body_match.group(1).strip() if body_match else fallback_body

    return subject, body


def get_personalizer() -> EmailPersonalizer | MockEmailPersonalizer:
    """Return the appropriate personalizer based on settings."""
    if settings.use_mock_apis:
        return MockEmailPersonalizer()
    return EmailPersonalizer()
