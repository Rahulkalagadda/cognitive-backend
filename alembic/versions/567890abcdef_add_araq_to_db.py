"""add araq to db

Revision ID: 567890abcdef
Revises: 1234567890ab
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '567890abcdef'
down_revision = '1234567890ab'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add 'araq' to questionnaire_slug enum type
    # Postgres ENUM types do not support adding values inside transaction blocks in older PG versions,
    # so we execute it in autocommit mode.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE questionnaire_slug ADD VALUE IF NOT EXISTS 'araq'")
    
    # 2. Add columns to reports table
    op.add_column('reports', sa.Column('araq_score', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('araq_sec_a_score', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('araq_sec_b_score', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('araq_sec_c_score', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('araq_sec_d_score', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('reports', 'araq_sec_d_score')
    op.drop_column('reports', 'araq_sec_c_score')
    op.drop_column('reports', 'araq_sec_b_score')
    op.drop_column('reports', 'araq_sec_a_score')
    op.drop_column('reports', 'araq_score')
