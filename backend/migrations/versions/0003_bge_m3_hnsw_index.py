"""bge-m3 hnsw index

给 bge-m3 的向量建 HNSW 部分索引（和 qwen3 的一样，每个模型一个）。

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_bge_m3_hnsw ON chunk_embeddings "
        "USING hnsw (embedding vector_cosine_ops) WHERE model = 'bge-m3'"
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_embeddings_bge_m3_hnsw", table_name="chunk_embeddings")
