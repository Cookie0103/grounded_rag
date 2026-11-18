"""以本机出题包和作者校准结果接入既有规程评审。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from zipfile import ZipFile

from eval.dataset import Question
from eval.judge import MAX_DOCUMENT_CHARS, Judge
from eval.scoring import ACCEPTABLE, PERFECT, ScoredQuestion, score_question

if TYPE_CHECKING:
    from eval.copilot_cases import CopilotCase

MIN_CALIBRATION_COUNT = 20
MIN_AGREEMENT_RATE = 0.85


@dataclass(frozen=True)
class Calibration:
    count: int
    agreements: int

    @property
    def rate(self) -> float | None:
        return self.agreements / self.count if self.count else None

    @property
    def accepted(self) -> bool:
        rate = self.rate
        return (
            self.count >= MIN_CALIBRATION_COUNT and rate is not None and rate >= MIN_AGREEMENT_RATE
        )


def _json_objects(content: str, label: str) -> Iterator[tuple[str, dict[str, object]]]:
    for number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        location = f"{label} 第 {number} 行"
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{location} JSON 不合法") from error
        if not isinstance(row, dict):
            raise ValueError(f"{location} 必须是 JSON 对象")
        yield location, row


def load_calibration(path: Path | None) -> Calibration:
    """根据作者独立标注和评审标签计算一致率。"""
    if path is None:
        return Calibration(count=0, agreements=0)
    seen: set[str] = set()
    agreements = 0
    for location, row in _json_objects(path.read_text(encoding="utf-8"), "评审校准文件"):
        sample_id = row.get("id")
        human, judge = row.get("human_acceptable"), row.get("judge_acceptable")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError(f"{location} 必须有非空的 id")
        if not isinstance(human, bool) or not isinstance(judge, bool):
            raise ValueError(f"{location} 的 human_acceptable 和 judge_acceptable 必须是布尔值")
        sample_id = sample_id.strip()
        if sample_id in seen:
            raise ValueError(f"{location} 有重复的 id")
        seen.add(sample_id)
        agreements += human == judge
    return Calibration(count=len(seen), agreements=agreements)


class PolicyCorpus:
    def __init__(self, path: Path, members: dict[str, str]) -> None:
        self._path = path
        self._members = members

    @classmethod
    def from_question_pack(cls, path: Path) -> PolicyCorpus:
        """读取阶段 31 出题包的文档索引。"""
        members: dict[str, str] = {}
        with ZipFile(path) as archive:
            files = set(archive.namelist())
            if "index.jsonl" not in files:
                raise ValueError("规程出题包缺少 index.jsonl")
            content = archive.read("index.jsonl").decode("utf-8")
            for location, row in _json_objects(content, "规程出题包索引"):
                document_id, filename = row.get("document_id"), row.get("file")
                if not isinstance(document_id, str) or not document_id.strip():
                    raise ValueError(f"{location} 必须有非空的 document_id")
                if not isinstance(filename, str) or not _is_document_filename(filename):
                    raise ValueError(f"{location} 的 Markdown 文件名不合法")
                member = f"documents/{filename}"
                if document_id in members or member not in files:
                    raise ValueError(f"{location} 的文档 ID 重复或 Markdown 文件缺失")
                members[document_id] = member
        return cls(path, members)

    def gold_texts(self, document_ids: Sequence[str]) -> tuple[str, ...]:
        """按金标文档 ID 从本机出题包读取评审资料。"""
        if not document_ids:
            return ()
        for document_id in document_ids:
            if document_id not in self._members:
                raise ValueError(f"规程出题包没有金标文档 {document_id}")
        with ZipFile(self._path) as archive:
            return tuple(
                archive.read(self._members[document_id]).decode("utf-8")[:MAX_DOCUMENT_CHARS]
                for document_id in document_ids
            )


def _is_document_filename(filename: str) -> bool:
    path = PurePosixPath(filename)
    return path.name == filename and path.suffix == ".md"


async def review_policy_raw(
    case: CopilotCase,
    answer: str,
    contexts: Sequence[str],
    *,
    judge: Judge,
    corpus: PolicyCorpus,
) -> ScoredQuestion:
    """沿用严格评审模板和评分，供作者在校准时取得独立的模型标签。"""
    question_text = case.question
    if case.as_of is not None:
        question_text += f"\n照会基準日 {case.as_of.isoformat()}"
    question = Question(
        id=case.id,
        question=question_text,
        gold_docs=case.gold_docs,
        nuggets=case.nuggets,
        unanswerable_category=case.unanswerable_category,
        gold_doc_groups=case.gold_doc_groups,
    )
    document_ids = tuple(dict.fromkeys(doc for group in question.required_groups for doc in group))
    gold_texts = await asyncio.to_thread(corpus.gold_texts, document_ids)
    verdict = await judge.judge_with_documents(
        question, answer, gold_texts, contexts, template_name="judge_v2.md"
    )
    return ScoredQuestion(question, verdict, score_question(question, verdict))


def policy_acceptable(review: ScoredQuestion) -> bool:
    """用既有评分判定是否达到规程回答的离线发送标准。"""
    label = PERFECT if review.question.answerable else ACCEPTABLE
    return review.score.label == label


async def review_policy(
    case: CopilotCase,
    answer: str,
    contexts: Sequence[str],
    *,
    judge: Judge,
    corpus: PolicyCorpus,
    calibration: Calibration,
) -> bool | None:
    """通过校准才采用评审标签，缺少合格校准时返回未测。"""
    if not calibration.accepted:
        return None
    review = await review_policy_raw(case, answer, contexts, judge=judge, corpus=corpus)
    return policy_acceptable(review)
