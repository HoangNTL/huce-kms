"""add_crawl_sessions_tables

Revision ID: a1b2c3d4e5f6
Revises: 9a2b3c4d5e6f
Create Date: 2026-11-23 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Create crawl_sessions table if not exists
    if 'crawl_sessions' not in tables:
        op.create_table(
            'crawl_sessions',
            sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('session_id_str', sa.String(length=50), nullable=False),
            sa.Column('status', sa.SmallInteger(), nullable=False, server_default='0'),
            sa.Column('source_domain', sa.String(length=255), nullable=True),
            sa.Column('total_urls', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('completed_urls', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('successful', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_crawl_sessions')),
        )
        op.create_index(op.f('ix_crawl_sessions_session_id_str'), 'crawl_sessions', ['session_id_str'], unique=True)
        op.create_index(op.f('ix_crawl_sessions_status'), 'crawl_sessions', ['status'], unique=False)
        op.create_index('ix_crawl_sessions_status_started_at', 'crawl_sessions', ['status', 'started_at'], unique=False)

    # 2. Create crawl_session_items table if not exists
    if 'crawl_session_items' not in tables:
        op.create_table(
            'crawl_session_items',
            sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('session_id', sa.Uuid(), nullable=False),
            sa.Column('url', sa.String(length=1000), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=True),
            sa.Column('page_hash', sa.String(length=64), nullable=True),
            sa.Column('status', sa.SmallInteger(), nullable=False, server_default='0'),
            sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('pdf_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('image_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_ingested', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('errors', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['session_id'], ['crawl_sessions.id'], name=op.f('fk_crawl_session_items_session_id_crawl_sessions'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_crawl_session_items')),
        )
        op.create_index(op.f('ix_crawl_session_items_session_id'), 'crawl_session_items', ['session_id'], unique=False)
        op.create_index(op.f('ix_crawl_session_items_page_hash'), 'crawl_session_items', ['page_hash'], unique=False)
        op.create_index(op.f('ix_crawl_session_items_status'), 'crawl_session_items', ['status'], unique=False)
        op.create_index('ix_crawl_session_items_session_status', 'crawl_session_items', ['session_id', 'status'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if 'crawl_session_items' in tables:
        op.drop_table('crawl_session_items')
    if 'crawl_sessions' in tables:
        op.drop_table('crawl_sessions')
