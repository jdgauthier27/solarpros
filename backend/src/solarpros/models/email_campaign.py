import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from solarpros.db.base import Base


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, paused, completed
    tier_filter: Mapped[str | None] = mapped_column(String(10))  # A, B, C, A,B
    min_score: Mapped[float | None] = mapped_column(Float)

    sequences: Mapped[list["EmailSequence"]] = relationship(
        back_populates="campaign", lazy="selectin", order_by="EmailSequence.step_number"
    )
    sends: Mapped[list["EmailSend"]] = relationship(back_populates="campaign", lazy="noload")

    def __repr__(self) -> str:
        return f"<EmailCampaign {self.name}>"


class EmailSequence(Base):
    __tablename__ = "email_sequences"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-4
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    campaign: Mapped["EmailCampaign"] = relationship(back_populates="sequences")

    def __repr__(self) -> str:
        return f"<EmailSequence step {self.step_number}>"


class EmailSend(Base):
    __tablename__ = "email_sends"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False
    )
    prospect_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prospect_scores.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="CASCADE"), nullable=False
    )

    sendgrid_message_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, sent, delivered, bounced, failed
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)

    response_type: Mapped[str | None] = mapped_column(String(50))  # interested, not_interested, question, out_of_office
    unsubscribe_token: Mapped[str] = mapped_column(String(100), nullable=False)
    physical_address: Mapped[str] = mapped_column(String(500), nullable=False)

    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)

    campaign: Mapped["EmailCampaign"] = relationship(back_populates="sends")

    def __repr__(self) -> str:
        return f"<EmailSend {self.status}>"
