"""检索指标：文档级的命中和倒数名次。评测的指标代码只读，不要为了提分去改它。"""

from collections.abc import Collection, Sequence


def ranked_documents(chunk_document_ids: Sequence[str]) -> list[str]:
    """子块排名 → 文档排名：同一篇文档只算第一次出现。"""
    return list(dict.fromkeys(chunk_document_ids))


def hit_at_k(gold_documents: Collection[str], ranked_docs: Sequence[str], k: int) -> bool:
    """金标文档是否**全部**出现在前 k 篇里（多跳题要求全部进入）。金标为空返回 False。"""
    if not gold_documents:
        return False
    return set(gold_documents) <= set(ranked_docs[:k])


def reciprocal_rank(gold_documents: Collection[str], ranked_docs: Sequence[str]) -> float:
    """第一篇金标文档名次的倒数；没出现是 0。"""
    for rank, document in enumerate(ranked_docs, start=1):
        if document in gold_documents:
            return 1.0 / rank
    return 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
