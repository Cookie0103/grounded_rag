"""traces, feedback, interventions

问答记录、用户反馈、人工干预的标准答案。

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")
EMPTY_ARRAY = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("edition", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("abstained", sa.Boolean(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("cached", sa.Boolean(), nullable=False),
        sa.Column("cost_cny", sa.Float(), nullable=False),
        sa.Column("steps", JSONB(), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("retrieved_docs", JSONB(), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("citations", JSONB(), nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("trace_id", name="pk_traces"),
    )
    op.create_index("ix_traces_created_at", "traces", ["created_at"])
    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("rating", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id", name="pk_feedback"),
        sa.CheckConstraint("rating IN ('good', 'bad')", name="ck_feedback_rating"),
    )
    op.create_index("ix_feedback_trace_id", "feedback", ["trace_id"])
    op.create_table(
        "interventions",
        sa.Column("question_key", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("question_key", name="pk_interventions"),
    )


def downgrade() -> None:
    op.drop_table("interventions")
    op.drop_index("ix_feedback_trace_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_traces_created_at", table_name="traces")
    op.drop_table("traces")
