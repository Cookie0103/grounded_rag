"""表定义。表结构只能通过 Alembic 迁移修改；这里的定义要和迁移一致。"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import BGE_M3_MODEL_NAME, EMBEDDING_DIMENSION, QWEN3_MODEL_NAME

# 统一约束命名，迁移里不会出现匿名约束
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _timestamp(name: str) -> Column[datetime]:
    return Column(name, TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


documents = Table(
    "documents",
    metadata,
    Column("id", Text, primary_key=True),  # 文档 ID：去掉 zh/ 和 .mdx 的相对路径
    Column("path", Text, nullable=False),
    Column("edition", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("content_hash", Text, nullable=False),  # sha256(原始文件字节 + INGEST_VERSION)
    Column("corpus_commit", Text, nullable=False),
    _timestamp("created_at"),
    _timestamp("updated_at"),
    CheckConstraint("edition IN ('self_host', 'cloud', 'common')", name="edition"),
)

parent_chunks = Table(
    "parent_chunks",
    metadata,
    Column("id", Text, primary_key=True),  # {document_id}#p{ordinal}
    Column("document_id", Text, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("heading_path", Text, nullable=False),
    Column("text", Text, nullable=False),
    _timestamp("created_at"),
)

chunks = Table(
    "chunks",
    metadata,
    Column("id", Text, primary_key=True),  # {document_id}#c{ordinal}
    Column("document_id", Text, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("parent_id", Text, ForeignKey("parent_chunks.id", ondelete="CASCADE"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("heading_path", Text, nullable=False),
    Column("text", Text, nullable=False),
    _timestamp("created_at"),
    Index("ix_chunks_document_id", "document_id"),
)

chunk_embeddings = Table(
    "chunk_embeddings",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("chunk_id", Text, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
    Column("model", Text, nullable=False),  # qwen3-embedding-0.6b / bge-m3
    Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
    _timestamp("created_at"),
    UniqueConstraint("chunk_id", "model"),
    # 每个嵌入模型一个部分索引
    Index(
        "ix_chunk_embeddings_qwen3_hnsw",
        "embedding",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=text(f"model = '{QWEN3_MODEL_NAME}'"),
    ),
    Index(
        "ix_chunk_embeddings_bge_m3_hnsw",
        "embedding",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=text(f"model = '{BGE_M3_MODEL_NAME}'"),
    ),
)


sessions = Table(
    "sessions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("edition", Text),
    Column("summary", Text, nullable=False, server_default=""),
    Column("turns", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    _timestamp("created_at"),
    _timestamp("updated_at"),
    CheckConstraint("edition IS NULL OR edition IN ('self_host', 'cloud')", name="edition"),
    Index("ix_sessions_updated_at", "updated_at"),
)


traces = Table(
    "traces",
    metadata,
    Column("trace_id", Text, primary_key=True),
    Column("question", Text, nullable=False),
    Column("route", Text, nullable=False),
    Column("edition", Text),
    Column("session_id", Text),
    Column("answer", Text, nullable=False),
    Column("abstained", Boolean, nullable=False),
    Column("degraded", Boolean, nullable=False),
    Column("cached", Boolean, nullable=False),
    Column("cost_cny", Float, nullable=False),
    Column("steps", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("retrieved_docs", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("citations", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    _timestamp("created_at"),
    Index("ix_traces_created_at", "created_at"),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("trace_id", Text, nullable=False),
    Column("rating", Text, nullable=False),
    Column("comment", Text, nullable=False, server_default=""),
    _timestamp("created_at"),
    CheckConstraint("rating IN ('good', 'bad')", name="rating"),
    Index("ix_feedback_trace_id", "trace_id"),
)

interventions = Table(
    "interventions",
    metadata,
    Column("question_key", Text, primary_key=True),  # 归一化后的问题（core.text.question_key）
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    _timestamp("created_at"),
)
