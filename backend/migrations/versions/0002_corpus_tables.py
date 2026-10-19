"""corpus tables

文档、父块、子块、向量。迁移写成固定内容，不引用 app 里的表定义（后者以后会变）。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def _timestamp(name: str) -> sa.Column[datetime]:
    return sa.Column(name, sa.TIMESTAMP(timezone=True), nullable=False, server_default=NOW)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("edition", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("corpus_commit", sa.Text(), nullable=False),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.CheckConstraint(
            "edition IN ('self_host', 'cloud', 'common')", name="ck_documents_edition"
        ),
    )
    op.create_table(
        "parent_chunks",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        _timestamp("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_parent_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_parent_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        _timestamp("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["parent_chunks.id"],
            name="fk_chunks_parent_id_parent_chunks",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        _timestamp("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_chunk_embeddings"),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_chunk_embeddings_chunk_id_chunks",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("chunk_id", "model", name="uq_chunk_embeddings_chunk_id"),
    )
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_qwen3_hnsw ON chunk_embeddings "
        "USING hnsw (embedding vector_cosine_ops) WHERE model = 'qwen3-embedding-0.6b'"
    )


def downgrade() -> None:
    op.drop_table("chunk_embeddings")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("parent_chunks")
    op.drop_table("documents")
