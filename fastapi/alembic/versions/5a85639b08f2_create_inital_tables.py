"""create inital tables

Revision ID: 5a85639b08f2
Revises: 
Create Date: 2023-05-24 10:42:47.671516

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a85639b08f2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'runtoken',
        sa.Column('id', sa.String, primary_key=True)
    )
    op.create_table(
        'user',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('run_tokens', sa.String, sa.ForeignKey('runtoken.id')),
    )



def downgrade() -> None:
    pass
