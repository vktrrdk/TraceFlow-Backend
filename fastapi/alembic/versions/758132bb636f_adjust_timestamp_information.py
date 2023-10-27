"""adjust timestamp information

Revision ID: 758132bb636f
Revises: db883b0b69b3
Create Date: 2023-10-27 14:10:26.258181

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '758132bb636f'
down_revision = 'db883b0b69b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'run_metric', sa.Column("start", sa.DateTime(), nullable=True),
    )
    op.add_column(
        'run_metric', sa.Column("submit", sa.DateTime(), nullable=True),
    )
    op.add_column(
        'run_metric', sa.Column("complete", sa.DateTime(), nullable=True),
    )
    op.drop_column(
        'run_metric', 'timestamp'
    )


def downgrade() -> None:
    op.add_column(
        'run_metric', sa.Column("timestamp", sa.DateTime(), nullable=True),
    )
    op.drop_column(
        'run_metric', 'start'
    )
    op.drop_column(
        'run_metric', 'submit'
    )
    op.drop_column(
        'run_metric', 'complete'
    )
