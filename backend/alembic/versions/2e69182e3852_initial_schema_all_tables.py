"""Initial schema: all tables

Revision ID: 2e69182e3852
Revises:
Create Date: 2026-02-22 04:35:09.482073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2e69182e3852'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('agent_runs',
    sa.Column('agent_type', sa.String(length=50), nullable=False),
    sa.Column('celery_task_id', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('items_processed', sa.Integer(), nullable=False),
    sa.Column('items_failed', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parent_run_id', sa.UUID(), nullable=True),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('result_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_run_id'], ['agent_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('email_campaigns',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('tier_filter', sa.String(length=10), nullable=True),
    sa.Column('min_score', sa.Float(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('properties',
    sa.Column('apn', sa.String(length=50), nullable=False),
    sa.Column('county', sa.String(length=50), nullable=False),
    sa.Column('address', sa.String(length=500), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('state', sa.String(length=2), nullable=False),
    sa.Column('zip_code', sa.String(length=10), nullable=True),
    sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('zoning', sa.String(length=50), nullable=True),
    sa.Column('building_type', sa.String(length=100), nullable=True),
    sa.Column('building_sqft', sa.Float(), nullable=True),
    sa.Column('roof_sqft', sa.Float(), nullable=True),
    sa.Column('year_built', sa.Integer(), nullable=True),
    sa.Column('owner_name_raw', sa.String(length=500), nullable=True),
    sa.Column('is_commercial', sa.Boolean(), nullable=False),
    sa.Column('meets_roof_min', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('apn', 'county', name='uq_properties_apn_county')
    )
    # Note: GeoAlchemy2 auto-creates spatial index 'idx_properties_location' for the geometry column
    op.create_index('ix_properties_county', 'properties', ['county'], unique=False)
    op.create_index('ix_properties_is_commercial', 'properties', ['is_commercial'], unique=False)
    op.create_table('email_sequences',
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('step_number', sa.Integer(), nullable=False),
    sa.Column('delay_days', sa.Integer(), nullable=False),
    sa.Column('subject_template', sa.String(length=500), nullable=False),
    sa.Column('body_template', sa.Text(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['email_campaigns.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('owners',
    sa.Column('property_id', sa.UUID(), nullable=False),
    sa.Column('owner_name_clean', sa.String(length=500), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=True),
    sa.Column('sos_entity_name', sa.String(length=500), nullable=True),
    sa.Column('sos_entity_number', sa.String(length=50), nullable=True),
    sa.Column('officer_name', sa.String(length=500), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('email_verified', sa.Boolean(), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('mailing_address', sa.Text(), nullable=True),
    sa.Column('confidence_score', sa.Float(), nullable=False),
    sa.Column('confidence_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('opted_out', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_owners_name_trgm', 'owners', ['owner_name_clean'], unique=False, postgresql_using='gin', postgresql_ops={'owner_name_clean': 'gin_trgm_ops'})
    op.create_table('solar_analyses',
    sa.Column('property_id', sa.UUID(), nullable=False),
    sa.Column('data_source', sa.String(length=50), nullable=False),
    sa.Column('usable_roof_sqft', sa.Float(), nullable=True),
    sa.Column('pitch', sa.Float(), nullable=True),
    sa.Column('azimuth', sa.Float(), nullable=True),
    sa.Column('sunshine_hours', sa.Float(), nullable=True),
    sa.Column('system_size_kw', sa.Float(), nullable=True),
    sa.Column('annual_kwh', sa.Float(), nullable=True),
    sa.Column('utility_rate', sa.Float(), nullable=True),
    sa.Column('annual_savings', sa.Float(), nullable=True),
    sa.Column('system_cost', sa.Float(), nullable=True),
    sa.Column('net_cost', sa.Float(), nullable=True),
    sa.Column('payback_years', sa.Float(), nullable=True),
    sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('property_id', 'data_source', name='uq_solar_property_source')
    )
    op.create_table('prospect_scores',
    sa.Column('property_id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=True),
    sa.Column('solar_analysis_id', sa.UUID(), nullable=True),
    sa.Column('solar_potential_score', sa.Float(), nullable=False),
    sa.Column('roof_size_score', sa.Float(), nullable=False),
    sa.Column('savings_score', sa.Float(), nullable=False),
    sa.Column('utility_zone_score', sa.Float(), nullable=False),
    sa.Column('owner_type_score', sa.Float(), nullable=False),
    sa.Column('contact_quality_score', sa.Float(), nullable=False),
    sa.Column('building_age_score', sa.Float(), nullable=False),
    sa.Column('composite_score', sa.Float(), nullable=False),
    sa.Column('tier', sa.String(length=1), nullable=False),
    sa.Column('scoring_version', sa.Integer(), nullable=False),
    sa.Column('weight_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['solar_analysis_id'], ['solar_analyses.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('property_id', 'scoring_version', name='uq_score_property_version')
    )
    op.create_table('email_sends',
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('sequence_id', sa.UUID(), nullable=False),
    sa.Column('prospect_score_id', sa.UUID(), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('sendgrid_message_id', sa.String(length=200), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('open_count', sa.Integer(), nullable=False),
    sa.Column('click_count', sa.Integer(), nullable=False),
    sa.Column('response_type', sa.String(length=50), nullable=True),
    sa.Column('unsubscribe_token', sa.String(length=100), nullable=False),
    sa.Column('physical_address', sa.String(length=500), nullable=False),
    sa.Column('is_unsubscribed', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['email_campaigns.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['prospect_score_id'], ['prospect_scores.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sequence_id'], ['email_sequences.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('email_sends')
    op.drop_table('prospect_scores')
    op.drop_table('solar_analyses')
    op.drop_index('ix_owners_name_trgm', table_name='owners', postgresql_using='gin', postgresql_ops={'owner_name_clean': 'gin_trgm_ops'})
    op.drop_table('owners')
    op.drop_table('email_sequences')
    op.drop_index('ix_properties_is_commercial', table_name='properties')
    op.drop_index('ix_properties_county', table_name='properties')
    op.drop_table('properties')
    op.drop_table('email_campaigns')
    op.drop_table('agent_runs')
