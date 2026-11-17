"""add_soft_delete_to_documents_and_users

Revision ID: 7e9a1b2c3d4f
Revises: 5d8f3e2a1b9c
Create Date: 2026-11-17 13:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e9a1b2c3d4f'
down_revision: Union[str, Sequence[str], None] = '5d8f3e2a1b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add deleted_at column to documents table
    op.add_column('documents', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_documents_deleted_at', 'documents', ['deleted_at'], unique=False)

    # 2. Add deleted_at column to users table
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'], unique=False)


def downgrade() -> None:
    # 1. Drop from users table
    op.drop_index('ix_users_deleted_at', table_name='users')
    op.drop_column('users', 'deleted_at')

    # 2. Drop from documents table
    op.drop_index('ix_documents_deleted_at', table_name='documents')
    op.drop_column('documents', 'deleted_at')
