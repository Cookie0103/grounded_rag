"""RRF（倒数排名融合）：只看名次，不看原始分数，所以不用把 BM25 分数和余弦距离换算到同一尺度。"""

from collections.abc import Sequence

from app.core.config import RRF_K


def rrf(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """每个文档的得分 = 它在各个榜单里的 1 / (k + 名次) 之和（名次从 1 开始）。

    同分时先出现在前面榜单、名次更靠前的排前面，结果是确定的。
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, tuple[int, int]] = {}
    for list_index, ranking in enumerate(rankings):
        for position, item in enumerate(ranking, start=1):
            if item in scores and first_seen[item][0] == list_index:
                continue  # 同一个榜单里重复出现，只算第一次
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + position)
            first_seen.setdefault(item, (list_index, position))
    return sorted(scores.items(), key=lambda pair: (-pair[1], first_seen[pair[0]]))
