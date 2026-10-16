"""评测题的读取。字段含义见 docs/implementation-log/2026-10-16/notes-evaluation.md §7.1。"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    gold_docs: tuple[str, ...]
    edition: str | None = None  # self_host / cloud / None
    lexical: str = "similar"  # 用词是否贴近原文：similar / distant


def load_questions(path: Path) -> list[Question]:
    questions: list[Question] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            questions.append(
                Question(
                    id=item["id"],
                    question=item["question"],
                    gold_docs=tuple(item["gold_docs"]),
                    edition=item.get("edition"),
                    lexical=item.get("lexical", "similar"),
                )
            )
        except (json.JSONDecodeError, KeyError) as error:
            raise ValueError(f"{path}:{number} 不是合法的题目：{error}") from error
    return questions
