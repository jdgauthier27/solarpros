"""add owner contact_title and contacts fields

Revision ID: a3f1c2d4e5b6
Revises: 2e69182e3852
Create Date: 2026-02-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a3f1c2d4e5b6"
down_revision = "2e69182e3852"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("owners", sa.Column("contact_title", sa.String(200), nullable=True))
    op.add_column("owners", sa.Column("contacts", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("owners", "contacts")
    op.drop_column("owners", "contact_title")
