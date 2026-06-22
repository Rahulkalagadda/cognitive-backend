"""add clinical_metrics to reports

Revision ID: 1234567890ab
Revises: None
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use postgresql dialect to add JSONB column
    op.add_column('reports', sa.Column('clinical_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('reports', 'clinical_metrics')
