"""SendGrid email client wrapper with mock support."""

import uuid

import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import CustomArg, From, Mail, To

from solarpros.config import settings

logger = structlog.get_logger()


class SendGridClient:
    """Wraps the SendGrid SDK to send transactional emails."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.sendgrid_api_key
        self.from_email = from_email or settings.sendgrid_from_email
        self.from_name = from_name or settings.sendgrid_from_name
        self._client = SendGridAPIClient(api_key=self.api_key)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        custom_args: dict | None = None,
    ) -> str:
        """Send an email via SendGrid.

        Returns the SendGrid message ID.
        """
        message = Mail(
            from_email=From(self.from_email, self.from_name),
            to_emails=To(to_email),
            subject=subject,
            html_content=html_body,
        )

        if custom_args:
            for key, value in custom_args.items():
                message.custom_arg = CustomArg(key, str(value))

        try:
            response = self._client.send(message)
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(
                "email_sent",
                to_email=to_email,
                subject=subject,
                status_code=response.status_code,
                message_id=message_id,
            )
            return message_id
        except Exception as e:
            logger.error(
                "email_send_failed",
                to_email=to_email,
                subject=subject,
                error=str(e),
            )
            raise


class MockSendGridClient:
    """Mock SendGrid client that logs sends and returns fake message IDs."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> None:
        self.from_email = from_email or settings.sendgrid_from_email
        self.from_name = from_name or settings.sendgrid_from_name
        self.sent_emails: list[dict] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        custom_args: dict | None = None,
    ) -> str:
        """Log the email send and return a fake message ID."""
        message_id = f"mock-{uuid.uuid4().hex[:16]}"
        record = {
            "message_id": message_id,
            "to_email": to_email,
            "from_email": self.from_email,
            "subject": subject,
            "html_body": html_body,
            "custom_args": custom_args,
        }
        self.sent_emails.append(record)
        logger.info(
            "mock_email_sent",
            to_email=to_email,
            subject=subject,
            message_id=message_id,
        )
        return message_id


def get_sendgrid_client() -> SendGridClient | MockSendGridClient:
    """Return the appropriate SendGrid client based on settings."""
    if settings.use_mock_apis:
        return MockSendGridClient()
    return SendGridClient()
