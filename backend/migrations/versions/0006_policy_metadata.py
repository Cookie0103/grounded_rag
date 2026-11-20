"""为文档和子块添加住宅贷款规程元数据。

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("documents", "chunks")


def _columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("source", sa.Text()),
        sa.Column("synthetic", sa.Boolean()),
        sa.Column("product_line", sa.Text()),
        sa.Column("policy_type", sa.Text()),
        sa.Column("policy_id", sa.Text()),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("status", sa.Text()),
        sa.Column("corpus_tier", sa.Text()),
        sa.Column("based_on", JSONB),
        sa.Column("source_url", sa.Text()),
    ]


def upgrade() -> None:
    # 旧迁移可能把已经带前缀的名字再次套进命名约定。
    for constraint in ("ck_documents_edition", "ck_documents_ck_documents_edition"):
        op.drop_constraint(op.f(constraint), "documents", type_="check", if_exists=True)
    for table in _TABLES:
        for column in _columns():
            op.add_column(table, column)


def downgrade() -> None:
    for table in reversed(_TABLES):
        for column in reversed(_columns()):
            op.drop_column(table, column.name)
    op.create_check_constraint(
        op.f("ck_documents_edition"), "documents", "edition IN ('self_host', 'cloud', 'common')"
    )
