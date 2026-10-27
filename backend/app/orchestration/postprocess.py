"""输出后处理：遮蔽密钥、黑名单、折叠重复的句子。只处理生成出来的回答。"""

import re
from dataclasses import dataclass, field

# 命中黑名单词的回答整个换成拒答；默认空表，作者按需填
BLOCKED_TERMS: tuple[str, ...] = ()
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
)
MASK_TEXT = "[已隐藏]"
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?\n])")
MIN_SENTENCE_CHARS = 4
MAX_REPEATS = 2


@dataclass
class PostResult:
    answer: str
    notes: list[str] = field(default_factory=list)
    blocked: bool = False


def collapse_repeats(text: str) -> str:
    """同一句话出现超过 MAX_REPEATS 次，后面的丢掉；长度太短的句子（如「是。」）不算。"""
    sentences = SENTENCE_SPLIT.split(text)
    counts: dict[str, int] = {}
    kept: list[str] = []
    for sentence in sentences:
        key = sentence.strip()
        if len(key) < MIN_SENTENCE_CHARS:
            kept.append(sentence)
            continue
        counts[key] = counts.get(key, 0) + 1
        if counts[key] <= MAX_REPEATS:
            kept.append(sentence)
    return "".join(kept)


def postprocess(answer: str, blocked_terms: tuple[str, ...] | None = None) -> PostResult:
    terms = BLOCKED_TERMS if blocked_terms is None else blocked_terms
    if any(term and term in answer for term in terms):
        return PostResult(answer, ["命中黑名单"], blocked=True)
    result = PostResult(answer)
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(MASK_TEXT, result.answer)
        if masked != result.answer:
            result.answer = masked
            result.notes.append("遮蔽了疑似密钥")
    collapsed = collapse_repeats(result.answer)
    if collapsed != result.answer:
        result.answer = collapsed
        result.notes.append("折叠了重复的句子")
    return result
