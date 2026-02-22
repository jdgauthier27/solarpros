"""CAN-SPAM compliance utilities.

Provides tools to verify email compliance, generate unsubscribe tokens,
build unsubscribe links, and add compliance footers to email content.
"""

import uuid

import structlog

logger = structlog.get_logger()

REQUIRED_ELEMENTS: list[str] = [
    "unsubscribe_link",
    "physical_address",
    "company_name",
]


def check_compliance(
    email_body: str,
    unsubscribe_token: str,
    physical_address: str,
) -> tuple[bool, list[str]]:
    """Check an email body for CAN-SPAM compliance.

    Args:
        email_body: The rendered HTML email body.
        unsubscribe_token: The unsubscribe token that should appear in a link.
        physical_address: The physical address that must be present.

    Returns:
        Tuple of (is_compliant, list_of_issues). An empty issues list
        means the email is compliant.
    """
    issues: list[str] = []

    if unsubscribe_token not in email_body:
        issues.append(
            "Missing unsubscribe link: the email must contain a working "
            "unsubscribe mechanism with the assigned token."
        )

    if physical_address not in email_body:
        issues.append(
            "Missing physical address: the email must include a valid "
            "physical postal address."
        )

    # Check for the word "unsubscribe" (case-insensitive) as a basic heuristic
    if "unsubscribe" not in email_body.lower():
        issues.append(
            "Missing unsubscribe text: the email should contain the word "
            "'unsubscribe' near the opt-out link."
        )

    is_compliant = len(issues) == 0

    if not is_compliant:
        logger.warning("email_compliance_check_failed", issues=issues)
    else:
        logger.debug("email_compliance_check_passed")

    return is_compliant, issues


def generate_unsubscribe_token() -> str:
    """Generate a unique UUID-based unsubscribe token."""
    return str(uuid.uuid4())


def build_unsubscribe_link(base_url: str, token: str) -> str:
    """Build a full unsubscribe URL from a base URL and token.

    Args:
        base_url: The application base URL (e.g. "https://app.solarpros.com").
        token: The unique unsubscribe token for this recipient.

    Returns:
        Full unsubscribe URL, e.g.
        "https://app.solarpros.com/api/v1/email/unsubscribe?token=abc-123"
    """
    base = base_url.rstrip("/")
    return f"{base}/api/v1/email/unsubscribe?token={token}"


def add_compliance_footer(
    body: str,
    unsubscribe_link: str,
    physical_address: str,
    company_name: str,
) -> str:
    """Append a CAN-SPAM compliant footer to an email body.

    This is a fallback in case the template does not already include the
    footer. If the body already contains an unsubscribe link, it is
    returned unchanged.

    Args:
        body: The email HTML body.
        unsubscribe_link: Full unsubscribe URL.
        physical_address: Physical mailing address.
        company_name: Sending company name.

    Returns:
        The body with a compliance footer appended (if not already present).
    """
    if "unsubscribe" in body.lower() and physical_address in body:
        return body

    footer = f"""
<hr style="margin-top: 40px; border: none; border-top: 1px solid #ccc;">
<p style="font-size: 11px; color: #999; line-height: 1.5;">
  This email was sent by {company_name}. If you no longer wish to receive
  these emails, you can <a href="{unsubscribe_link}" style="color: #999;">unsubscribe here</a>.
  <br><br>
  {physical_address}
</p>
"""
    return body + footer
