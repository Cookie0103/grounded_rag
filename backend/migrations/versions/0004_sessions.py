"""sessions

多轮会话的短期记忆：版本、摘要、最近几轮原文。

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("edition", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("turns", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.CheckConstraint(
            "edition IS NULL OR edition IN ('self_host', 'cloud')", name="ck_sessions_edition"
        ),
    )
    op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_sessions_updated_at", table_name="sessions")
    op.drop_table("sessions")
