"""watch_history

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watch_history",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("progress_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "last_watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "video_id", name="uq_watch_history"),
    )
    op.create_index("ix_watch_history_user_watched", "watch_history", ["user_id", "last_watched_at"])


def downgrade() -> None:
    op.drop_table("watch_history")