"""convert_status_and_role_to_smallint

Revision ID: 9a2b3c4d5e6f
Revises: 8f1b2c3d4e5a
Create Date: 2026-11-23 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '8f1b2c3d4e5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update documents.status from VARCHAR(20) to SMALLINT
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE SMALLINT 
        USING (
            CASE LOWER(TRIM(status::text))
                WHEN 'uploaded' THEN 0
                WHEN '0' THEN 0
                WHEN 'pending' THEN 1
                WHEN '1' THEN 1
                WHEN 'processing' THEN 2
                WHEN '2' THEN 2
                WHEN 'indexed' THEN 3
                WHEN '3' THEN 3
                WHEN 'failed' THEN 4
                WHEN '4' THEN 4
                ELSE 0
            END
        ),
        ALTER COLUMN status SET DEFAULT 0;
    """)

    # 2. Update documents.source_type from VARCHAR(50) to SMALLINT
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN source_type DROP DEFAULT,
        ALTER COLUMN source_type TYPE SMALLINT 
        USING (
            CASE LOWER(TRIM(source_type::text))
                WHEN 'crawler' THEN 2
                WHEN '2' THEN 2
                WHEN 'upload' THEN 1
                WHEN '1' THEN 1
                ELSE 1
            END
        ),
        ALTER COLUMN source_type SET DEFAULT 1;
    """)

    # 3. Update users.role from VARCHAR(20) to SMALLINT
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role DROP DEFAULT,
        ALTER COLUMN role TYPE SMALLINT 
        USING (
            CASE LOWER(TRIM(role::text))
                WHEN 'admin' THEN 2
                WHEN '2' THEN 2
                WHEN 'user' THEN 1
                WHEN '1' THEN 1
                ELSE 1
            END
        ),
        ALTER COLUMN role SET DEFAULT 1;
    """)


def downgrade() -> None:
    # 1. Rollback documents.status from SMALLINT to VARCHAR(20)
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE VARCHAR(20) 
        USING (
            CASE status
                WHEN 0 THEN 'uploaded'
                WHEN 1 THEN 'pending'
                WHEN 2 THEN 'processing'
                WHEN 3 THEN 'indexed'
                WHEN 4 THEN 'failed'
                ELSE 'uploaded'
            END
        ),
        ALTER COLUMN status SET DEFAULT 'uploaded';
    """)

    # 2. Rollback documents.source_type from SMALLINT to VARCHAR(50)
    op.execute("""
        ALTER TABLE documents 
        ALTER COLUMN source_type DROP DEFAULT,
        ALTER COLUMN source_type TYPE VARCHAR(50) 
        USING (
            CASE source_type
                WHEN 2 THEN 'crawler'
                ELSE 'upload'
            END
        ),
        ALTER COLUMN source_type SET DEFAULT 'upload';
    """)

    # 3. Rollback users.role from SMALLINT to VARCHAR(20)
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role DROP DEFAULT,
        ALTER COLUMN role TYPE VARCHAR(20) 
        USING (
            CASE role
                WHEN 2 THEN 'admin'
                ELSE 'user'
            END
        ),
        ALTER COLUMN role SET DEFAULT 'user';
    """)
