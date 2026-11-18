"""退役第一版的会话表。双泳道的检查点表由官方 saver 管理。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("LOCK TABLE sessions IN ACCESS EXCLUSIVE MODE"))
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sessions)")):
        op.rename_table("sessions", "archived_v1_sessions")
    else:
        op.drop_table("sessions")


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("archived_v1_sessions"):
        op.rename_table("archived_v1_sessions", "sessions")
        return
    now = sa.text("now()")
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("edition", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("turns", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=now),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.CheckConstraint(
            "edition IS NULL OR edition IN ('self_host', 'cloud')", name="ck_sessions_edition"
        ),
    )
    op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])
