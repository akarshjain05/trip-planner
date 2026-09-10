"""add celery_task_id

Revision ID: aaa08af776fa
Revises: cc62bf5a281f
Create Date: 2026-08-23 18:39:26.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aaa08af776fa'
down_revision: Union[str, None] = 'cc62bf5a281f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_runs', sa.Column('celery_task_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_runs', 'celery_task_id')
