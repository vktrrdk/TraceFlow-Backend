"""add_meta_files

Revision ID: 54327ecba7e3
Revises: 71a786f9cea0
Create Date: 2023-08-11 12:03:13.360397

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54327ecba7e3'
down_revision = '71a786f9cea0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('run_metadata', sa.Column('scratch', sa.String(), nullable=True))
    op.add_column('run_metadata', sa.Column('project_name', sa.String(), nullable=True))
    op.add_column('run_metadata', sa.Column('revision', sa.String(), nullable=True))
    op.add_column('run_metadata', sa.Column('work_dir', sa.String(), nullable=True))
    op.add_column('run_metadata', sa.Column('user_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('run_metadata', 'scratch')
    op.drop_column('run_metadata', 'project_name')
    op.drop_column('run_metadata', 'revision')
    op.drop_column('run_metadata', 'work_dir')
    op.drop_column('run_metadata', 'user_name')
