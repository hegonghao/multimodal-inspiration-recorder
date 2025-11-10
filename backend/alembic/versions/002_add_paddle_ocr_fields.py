"""Add PaddleOCR fields: content_markdown, pdf_file_path, page_count, processing_options

Revision ID: 002
Revises: 001
Create Date: 2025-11-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new fields for PaddleOCR features"""

    # Add new columns
    op.add_column('inspiration_records', sa.Column('content_markdown', sa.Text(), nullable=True))
    op.add_column('inspiration_records', sa.Column('pdf_file_path', sa.String(500), nullable=True))
    op.add_column('inspiration_records', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('inspiration_records', sa.Column('processing_options', sa.Text(), nullable=True))

    # Drop old input_type constraint
    op.drop_constraint('chk_input_type', 'inspiration_records', type_='check')

    # Add new input_type constraint with 'pdf'
    op.create_check_constraint(
        'chk_input_type',
        'inspiration_records',
        "input_type IN ('voice', 'text', 'image', 'pdf')"
    )

    # Add page_count constraint
    op.create_check_constraint(
        'chk_page_count_positive',
        'inspiration_records',
        'page_count IS NULL OR page_count > 0'
    )


def downgrade() -> None:
    """Remove PaddleOCR fields"""

    # Remove constraints
    op.drop_constraint('chk_page_count_positive', 'inspiration_records', type_='check')
    op.drop_constraint('chk_input_type', 'inspiration_records', type_='check')

    # Recreate old input_type constraint without 'pdf'
    op.create_check_constraint(
        'chk_input_type',
        'inspiration_records',
        "input_type IN ('voice', 'text', 'image')"
    )

    # Drop new columns
    op.drop_column('inspiration_records', 'processing_options')
    op.drop_column('inspiration_records', 'page_count')
    op.drop_column('inspiration_records', 'pdf_file_path')
    op.drop_column('inspiration_records', 'content_markdown')
