"""adjust scratch-column

Revision ID: 88030b537eda
Revises: 54327ecba7e3
Create Date: 2023-08-21 21:51:55.806312

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88030b537eda'
down_revision = '54327ecba7e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('run_metric', 'scratch', type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('run_metric', 'scratch', type=sa.Boolean(), nullable=True)
