"""内存里的 BM25 索引（bm25s）。索引不入库，启动时从 chunks 表建。"""

from collections.abc import Callable, Sequence

import bm25s
import numpy as np

from app.retrieval.tokenizer import tokenize

Tokenizer = Callable[[str], list[str]]


class Bm25Index:
    def __init__(
        self, chunk_ids: Sequence[str], texts: Sequence[str], tokenizer: Tokenizer = tokenize
    ) -> None:
        if len(chunk_ids) != len(texts):
            raise ValueError("chunk_ids 和 texts 的数量必须一致")
        self._ids = list(chunk_ids)
        self._tokenizer = tokenizer
        self._index = bm25s.BM25()
        if self._ids:  # bm25s 不能建空索引
            self._index.index([tokenizer(text) for text in texts], show_progress=False)

    def __len__(self) -> int:
        return len(self._ids)

    def search(
        self, query: str, limit: int, allowed_ids: frozenset[str] | None = None
    ) -> list[tuple[str, float]]:
        """返回 (块 ID, 分数)，分数从高到低；只有分数大于 0 的才算命中。"""
        tokens = self._tokenizer(query)
        if not tokens or not self._ids:
            return []
        scores = np.asarray(self._index.get_scores(tokens), dtype=float)
        if allowed_ids is not None:
            mask = np.fromiter((chunk_id in allowed_ids for chunk_id in self._ids), bool)
            scores = np.where(mask, scores, 0.0)
        order = np.argsort(-scores, kind="stable")[:limit]
        return [(self._ids[i], float(scores[i])) for i in order if scores[i] > 0]
