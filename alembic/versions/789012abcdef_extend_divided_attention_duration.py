"""extend divided attention duration

Revision ID: 789012abcdef
Revises: 567890abcdef
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '789012abcdef'
down_revision = '567890abcdef'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Update default template tasks divided-attention duration to 420 seconds
    op.execute("UPDATE template_tasks SET duration_seconds = 420 WHERE task_id = 'divided-attention'")
    # Also update the Standard Cognitive Battery template description and duration_minutes
    op.execute("UPDATE assessment_templates SET duration_minutes = 13, description = '8 Tasks (Attention, Memory, Reasoning, Coordination, Perception, Working Memory, Divided Attention) · ~13 mins' WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'")

def downgrade() -> None:
    op.execute("UPDATE template_tasks SET duration_seconds = 120 WHERE task_id = 'divided-attention'")
    op.execute("UPDATE assessment_templates SET duration_minutes = 8, description = '8 Tasks (Attention, Memory, Reasoning, Coordination, Perception, Working Memory, Divided Attention) · ~8 mins' WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'")
