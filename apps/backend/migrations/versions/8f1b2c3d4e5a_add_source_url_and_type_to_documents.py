"""add_source_url_and_type_to_documents

Revision ID: 8f1b2c3d4e5a
Revises: 7e9a1b2c3d4f
Create Date: 2026-11-18 10:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f1b2c3d4e5a'
down_revision: Union[str, Sequence[str], None] = '7e9a1b2c3d4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add source_url column to documents table
    op.add_column('documents', sa.Column('source_url', sa.String(1000), nullable=True))
    op.create_index('ix_documents_source_url', 'documents', ['source_url'], unique=False)

    # 2. Add source_type column to documents table
    op.add_column('documents', sa.Column('source_type', sa.String(50), server_default='upload', nullable=False))
    op.create_index('ix_documents_source_type', 'documents', ['source_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_source_type', table_name='documents')
    op.drop_column('documents', 'source_type')

    op.drop_index('ix_documents_source_url', table_name='documents')
    op.drop_column('documents', 'source_url')
