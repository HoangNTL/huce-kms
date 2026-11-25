"""upgrade_document_chunks_metadata

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-25 16:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "document_chunks" not in insp.get_table_names():
        return

    existing_cols = {col["name"] for col in insp.get_columns("document_chunks")}
    existing_indexes = {idx["name"] for idx in insp.get_indexes("document_chunks")}

    if "context" not in existing_cols:
        op.add_column("document_chunks", sa.Column("context", sa.Text(), nullable=True))

    if "metadata" not in existing_cols:
        op.add_column(
            "document_chunks",
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )

    if "page_start" not in existing_cols:
        op.add_column(
            "document_chunks",
            sa.Column("page_start", sa.Integer(), server_default="1", nullable=False),
        )
        op.execute("UPDATE document_chunks SET page_start = page_number")

    if "page_end" not in existing_cols:
        op.add_column(
            "document_chunks",
            sa.Column("page_end", sa.Integer(), server_default="1", nullable=False),
        )
        op.execute("UPDATE document_chunks SET page_end = page_number")

    if "content_hash" not in existing_cols:
        op.add_column(
            "document_chunks",
            sa.Column("content_hash", sa.String(length=64), nullable=True),
        )

    idx_name = op.f("ix_document_chunks_content_hash")
    if idx_name not in existing_indexes:
        op.create_index(idx_name, "document_chunks", ["content_hash"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "document_chunks" not in insp.get_table_names():
        return

    existing_cols = {col["name"] for col in insp.get_columns("document_chunks")}
    existing_indexes = {idx["name"] for idx in insp.get_indexes("document_chunks")}

    idx_name = op.f("ix_document_chunks_content_hash")
    if idx_name in existing_indexes:
        op.drop_index(idx_name, table_name="document_chunks")

    for col_name in ("content_hash", "page_end", "page_start", "metadata", "context"):
        if col_name in existing_cols:
            op.drop_column("document_chunks", col_name)
