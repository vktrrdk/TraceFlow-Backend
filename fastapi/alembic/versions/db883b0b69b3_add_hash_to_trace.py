"""add hash to trace

Revision ID: db883b0b69b3
Revises: 3244ac46cb4e
Create Date: 2023-08-25 09:20:04.162066

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db883b0b69b3'
down_revision = '3244ac46cb4e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'run_metric', sa.Column('hash', sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column(
        'run_metric', 'hash'
    )
