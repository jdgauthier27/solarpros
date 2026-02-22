import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class OutreachSequence(Base):
    """Multi-channel sequence definition for a campaign."""

    __tablename__ = "outreach_sequences"
    __table_args__ = (
        Index("ix_outreach_sequences_campaign_id", "campaign_id"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # email / linkedin / phone / direct_mail
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    subject_template: Mapped[str | None] = mapped_column(String(500))
    body_template: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(
        Text
    )  # For phone: call script. For LinkedIn: connection note

    # Relationships
    campaign: Mapped["EmailCampaign"] = relationship()

    def __repr__(self) -> str:
        return f"<OutreachSequence step {self.step_number} ({self.channel})>"


class OutreachTouch(Base):
    """Multi-channel outreach tracking record."""

    __tablename__ = "outreach_touches"
    __table_args__ = (
        Index("ix_outreach_touches_campaign_id", "campaign_id"),
        Index("ix_outreach_touches_contact_id", "contact_id"),
        Index("ix_outreach_touches_channel", "channel"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # email / linkedin / phone / direct_mail
    status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )  # pending / sent / delivered / opened / replied / answered / connected

    sendgrid_message_id: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Phone-specific
    call_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    call_outcome: Mapped[str | None] = mapped_column(
        String(50)
    )  # answered / voicemail / no_answer

    # LinkedIn-specific
    linkedin_connection_status: Mapped[str | None] = mapped_column(
        String(30)
    )  # pending / accepted / declined

    response_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # interested / not_interested / question / meeting_scheduled
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    campaign: Mapped["EmailCampaign"] = relationship()
    contact: Mapped["Contact"] = relationship()

    def __repr__(self) -> str:
        return f"<OutreachTouch {self.channel} ({self.status})>"


from solarpros.models.contact import Contact  # noqa: E402
from solarpros.models.email_campaign import EmailCampaign  # noqa: E402
