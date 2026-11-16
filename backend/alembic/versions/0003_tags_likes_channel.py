"""tags_likes_channel

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cover_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("videos", sa.Column("tags", postgresql.JSONB(), nullable=True))
    op.add_column("videos", sa.Column("custom_poster_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("videos", "custom_poster_url")
    op.drop_column("videos", "tags")
    op.drop_column("users", "description")
    op.drop_column("users", "cover_url")