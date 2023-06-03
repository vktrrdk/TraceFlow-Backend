"""create initial database

Revision ID: be4217b9b58f
Revises: 
Create Date: 2023-06-03 12:24:56.668703

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be4217b9b58f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('run_tokens', sa.ARRAY(sa.String), nullable=True)

    )
    op.create_table(
        'runtoken',
        sa.Column('id', sa.String(40), primary_key=True)
    )

def downgrade() -> None:
    op.drop_table('user')
    op.drop_table('runtoken')
