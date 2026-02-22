"""pipeline v2 models

Revision ID: d5f9a2b1c3e7
Revises: c4e8f1a2b3d5
Create Date: 2026-02-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5f9a2b1c3e7"
down_revision: Union[str, None] = "c4e8f1a2b3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New table: contacts ---
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(500), nullable=False),
        sa.Column("first_name", sa.String(200)),
        sa.Column("last_name", sa.String(200)),
        sa.Column("job_title", sa.String(300)),
        sa.Column("buying_role", sa.String(50)),
        sa.Column("email", sa.String(320)),
        sa.Column("email_verified", sa.Boolean, default=False),
        sa.Column("email_source", sa.String(50)),
        sa.Column("phone", sa.String(20)),
        sa.Column("phone_type", sa.String(20)),
        sa.Column("phone_source", sa.String(50)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("confidence_score", sa.Float, default=0.0),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("opted_out", sa.Boolean, default=False),
        sa.Column("enrichment_sources", postgresql.JSONB),
    )
    op.create_index("ix_contacts_owner_id", "contacts", ["owner_id"])
    op.create_index("ix_contacts_email", "contacts", ["email"])

    # --- New table: trigger_events ---
    op.create_table(
        "trigger_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True)),
        sa.Column("relevance_score", sa.Float, default=0.0),
        sa.Column("raw_data", postgresql.JSONB),
    )
    op.create_index("ix_trigger_events_property_id", "trigger_events", ["property_id"])
    op.create_index("ix_trigger_events_owner_id", "trigger_events", ["owner_id"])
    op.create_index("ix_trigger_events_event_type", "trigger_events", ["event_type"])

    # --- New table: outreach_sequences ---
    op.create_table(
        "outreach_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("delay_days", sa.Integer, default=0),
        sa.Column("subject_template", sa.String(500)),
        sa.Column("body_template", sa.Text),
        sa.Column("instructions", sa.Text),
    )
    op.create_index("ix_outreach_sequences_campaign_id", "outreach_sequences", ["campaign_id"])

    # --- New table: outreach_touches ---
    op.create_table(
        "outreach_touches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), default="pending"),
        sa.Column("sendgrid_message_id", sa.String(200)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("call_duration_seconds", sa.Integer),
        sa.Column("call_outcome", sa.String(50)),
        sa.Column("linkedin_connection_status", sa.String(30)),
        sa.Column("response_type", sa.String(50)),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_outreach_touches_campaign_id", "outreach_touches", ["campaign_id"])
    op.create_index("ix_outreach_touches_contact_id", "outreach_touches", ["contact_id"])
    op.create_index("ix_outreach_touches_channel", "outreach_touches", ["channel"])

    # --- Modify owners table: add company-level enrichment fields ---
    op.add_column("owners", sa.Column("company_domain", sa.String(200)))
    op.add_column("owners", sa.Column("company_website", sa.String(500)))
    op.add_column("owners", sa.Column("company_phone", sa.String(20)))
    op.add_column("owners", sa.Column("company_description", sa.Text))
    op.add_column("owners", sa.Column("employee_count", sa.Integer))
    op.add_column("owners", sa.Column("google_place_id", sa.String(200)))
    op.add_column("owners", sa.Column("enrichment_log", postgresql.JSONB))

    # --- Modify prospect_scores table: add 3 new scoring dimensions ---
    op.add_column("prospect_scores", sa.Column("trigger_event_score", sa.Float, server_default="0.0"))
    op.add_column("prospect_scores", sa.Column("contact_depth_score", sa.Float, server_default="0.0"))
    op.add_column("prospect_scores", sa.Column("decision_maker_quality_score", sa.Float, server_default="0.0"))


def downgrade() -> None:
    # Drop new score columns
    op.drop_column("prospect_scores", "decision_maker_quality_score")
    op.drop_column("prospect_scores", "contact_depth_score")
    op.drop_column("prospect_scores", "trigger_event_score")

    # Drop new owner columns
    op.drop_column("owners", "enrichment_log")
    op.drop_column("owners", "google_place_id")
    op.drop_column("owners", "employee_count")
    op.drop_column("owners", "company_description")
    op.drop_column("owners", "company_phone")
    op.drop_column("owners", "company_website")
    op.drop_column("owners", "company_domain")

    # Drop new tables
    op.drop_table("outreach_touches")
    op.drop_table("outreach_sequences")
    op.drop_table("trigger_events")
    op.drop_table("contacts")
