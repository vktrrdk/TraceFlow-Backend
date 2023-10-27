"""adjust_scratch_correct

Revision ID: 3244ac46cb4e
Revises: 88030b537eda
Create Date: 2023-08-21 22:31:57.748856

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3244ac46cb4e'
down_revision = '88030b537eda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('run_metric', 'scratch', type_=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('run_metric', 'scratch', type_=sa.Boolean(), nullable=True)
