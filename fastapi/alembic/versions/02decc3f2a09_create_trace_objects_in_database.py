"""create trace objects in database

Revision ID: 02decc3f2a09
Revises: be4217b9b58f
Create Date: 2023-06-03 17:58:15.670697

"""
import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02decc3f2a09'
down_revision = 'be4217b9b58f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'run_metric',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('token', sa.String(40), nullable=False),
        sa.Column('run_name', sa.String, nullable=True),
        sa.Column('timestamp', sa.DateTime, default=datetime.datetime.utcnow()),
        sa.Column('task_id', sa.Integer, nullable=True),
        sa.Column('status', sa.String, nullable=True),
        sa.Column('process', sa.String, nullable=True),
        sa.Column('tag', sa.String, nullable=True),
        sa.Column('name', sa.String, nullable=True),
        sa.Column('cpus', sa.Integer, nullable=True),
        sa.Column('memory', sa.Integer, nullable=True),
        sa.Column('disk', sa.Integer, nullable=True),
        sa.Column('duration', sa.Integer, nullable=True),
    )
    op.create_table(
        'run_metadata',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('token', sa.String(40), nullable=False),
        sa.Column('run_name', sa.String, nullable=True),
        sa.Column('timestamp', sa.DateTime, default=datetime.datetime.utcnow()),
        sa.Column('reference', sa.String, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('run_metadata')
    op.drop_table('run_trace')
