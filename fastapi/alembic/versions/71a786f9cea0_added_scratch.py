"""added scratch

Revision ID: 71a786f9cea0
Revises: f78bd1c5dff6
Create Date: 2023-07-28 14:18:38.345172

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '71a786f9cea0'
down_revision = 'f78bd1c5dff6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'run_metric', sa.Column('scratch', sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column(
        'run_metric', 'scratch'
    )
