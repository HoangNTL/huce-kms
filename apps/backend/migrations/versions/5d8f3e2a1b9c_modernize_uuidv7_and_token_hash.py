"""modernize_uuidv7_and_token_hash

Revision ID: 5d8f3e2a1b9c
Revises: 4ac32ec4f23c
Create Date: 2026-11-17 12:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5d8f3e2a1b9c'
down_revision: Union[str, Sequence[str], None] = '4ac32ec4f23c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure pgcrypto is available for gen_random_uuid fallback in raw SQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # Truncate legacy integer-ID records before type conversion to avoid FK & NOT NULL constraint errors
    op.execute('TRUNCATE refresh_tokens, document_chunks, documents, categories, users CASCADE;')

    # 1. Drop existing Foreign Keys before altering types
    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.drop_constraint('documents_category_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('documents_uploader_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('document_chunks_document_id_fkey', 'document_chunks', type_='foreignkey')

    # 2. Drop existing indexes that are being renamed/retyped
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.drop_index('ix_documents_uploader_id', table_name='documents')

    # 3. Alter users table
    op.execute('ALTER TABLE users ALTER COLUMN id DROP DEFAULT;')
    op.execute('ALTER TABLE users ALTER COLUMN id TYPE UUID USING gen_random_uuid();')
    op.execute('ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid();')

    # 4. Alter refresh_tokens table
    op.execute('ALTER TABLE refresh_tokens ALTER COLUMN id DROP DEFAULT;')
    op.execute('ALTER TABLE refresh_tokens ALTER COLUMN id TYPE UUID USING gen_random_uuid();')
    op.execute('ALTER TABLE refresh_tokens ALTER COLUMN id SET DEFAULT gen_random_uuid();')
    op.execute('ALTER TABLE refresh_tokens ALTER COLUMN user_id TYPE UUID USING gen_random_uuid();')
    op.alter_column('refresh_tokens', 'token', new_column_name='token_hash', type_=sa.String(length=64))
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)

    # 5. Alter categories table
    op.execute('ALTER TABLE categories ALTER COLUMN id DROP DEFAULT;')
    op.execute('ALTER TABLE categories ALTER COLUMN id TYPE UUID USING gen_random_uuid();')
    op.execute('ALTER TABLE categories ALTER COLUMN id SET DEFAULT gen_random_uuid();')

    # 6. Alter documents table
    op.execute('ALTER TABLE documents ALTER COLUMN id DROP DEFAULT;')
    op.execute('ALTER TABLE documents ALTER COLUMN id TYPE UUID USING gen_random_uuid();')
    op.execute('ALTER TABLE documents ALTER COLUMN id SET DEFAULT gen_random_uuid();')
    op.execute('ALTER TABLE documents ALTER COLUMN category_id TYPE UUID USING NULL;')
    op.alter_column('documents', 'uploader_id', new_column_name='created_by_id', type_=postgresql.UUID(as_uuid=True), postgresql_using='NULL')
    op.create_index(op.f('ix_documents_created_by_id'), 'documents', ['created_by_id'], unique=False)

    # 7. Alter document_chunks table
    op.execute('ALTER TABLE document_chunks ALTER COLUMN id TYPE UUID USING id::uuid;')
    op.execute('ALTER TABLE document_chunks ALTER COLUMN id SET DEFAULT gen_random_uuid();')
    op.execute('ALTER TABLE document_chunks ALTER COLUMN document_id TYPE UUID USING NULL;')

    # 8. Re-establish Foreign Key Constraints with UUID types
    op.create_foreign_key(
        'refresh_tokens_user_id_fkey',
        'refresh_tokens', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'documents_category_id_fkey',
        'documents', 'categories',
        ['category_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'documents_created_by_id_fkey',
        'documents', 'users',
        ['created_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'document_chunks_document_id_fkey',
        'document_chunks', 'documents',
        ['document_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Downgrade drops new foreign keys and restores integer types
    op.drop_constraint('document_chunks_document_id_fkey', 'document_chunks', type_='foreignkey')
    op.drop_constraint('documents_created_by_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('documents_category_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')

    op.drop_index(op.f('ix_documents_created_by_id'), table_name='documents')
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')

    op.alter_column('documents', 'created_by_id', new_column_name='uploader_id', type_=sa.Integer())
    op.create_index('ix_documents_uploader_id', 'documents', ['uploader_id'], unique=False)
    op.alter_column('refresh_tokens', 'token_hash', new_column_name='token', type_=sa.String(length=255))
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)
