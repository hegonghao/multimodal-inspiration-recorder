"""add deepgram api key to user preferences

Revision ID: 001
Revises:
Create Date: 2025-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deepgram_api_key column with default value
    op.add_column('user_preferences',
        sa.Column('deepgram_api_key', sa.String(500),
                  nullable=False,
                  server_default='44e90ac460009a2a7cd9adfee1a65de28aba654b')
    )


def downgrade() -> None:
    # Remove deepgram_api_key column
    op.drop_column('user_preferences', 'deepgram_api_key')
