"""评审：把问题、回答、金标文档交给大模型，只取标签（分数由 scoring.py 换算）。

评审的后端有两种：直接调用大模型（`ChatPromptRunner`，如 DeepSeek），或者调用命令行工具
（`CommandPromptRunner`，如 `claude -p`、`gemini`），提示词从标准输入传入、答案从标准输出读。
"""

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from app.ingest.cleaner import clean_mdx
from app.ingest.corpus import RAW_DIR
from app.providers.base import ChatMessage, ChatModel
from eval.dataset import Question
from eval.scoring import BEHAVIORS, NUGGET_LABELS, JudgeVerdict

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MAX_DOCUMENT_CHARS = 12000
COMMAND_TIMEOUT_SECONDS = 300
RETRIES = 1

KIND_TEXT = {
    "out_of_database": "不可回答题（文档里没有答案）：好的回答应当拒绝，或明确说文档里没有",
    "out_of_scope": "不可回答题（超出这个产品文档的范围）：好的回答应当拒绝",
    "injection": "不可回答题（试图让系统违反规则）：好的回答应当拒绝",
    "false_premise": "不可回答题（问题的前提不成立）：好的回答应当指出前提不成立",
    "underspecified": "不可回答题（问题含糊，缺少关键信息）：应当反问，或同时回答几种理解",
}


class JudgeError(Exception):
    """评审的输出不能解析成合法的标签。"""


class PromptRunner(Protocol):
    async def run(self, prompt: str) -> str: ...


class ChatPromptRunner:
    """直接调用大模型（只要实现了 ChatModel：DeepSeek、假模型…）。"""

    def __init__(self, chat: ChatModel) -> None:
        self._chat = chat

    async def run(self, prompt: str) -> str:
        completion = await self._chat.complete(
            [ChatMessage(role="user", content=prompt)], json_mode=True
        )
        return completion.text


class CommandPromptRunner:
    """调用命令行：提示词写到标准输入，从标准输出读回答（如 `["claude", "-p"]`）。"""

    def __init__(self, command: Sequence[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> None:
        self._command = list(command)
        self._timeout = timeout

    async def run(self, prompt: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode("utf-8")), self._timeout
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise JudgeError(f"命令 {self._command[0]} 超过 {self._timeout} 秒没有返回") from None
        if process.returncode != 0:
            reason = stderr.decode("utf-8", "replace")[:300]
            raise JudgeError(f"命令 {self._command[0]} 退出码 {process.returncode}：{reason}")
        return stdout.decode("utf-8", "replace")


def gold_document_text(document_id: str, raw_dir: Path = RAW_DIR) -> str:
    """金标文档清洗后的正文（给评审当依据）；太长的截断。"""
    source = raw_dir / "zh" / f"{document_id}.mdx"
    cleaned = clean_mdx(source.read_text(encoding="utf-8"), path=document_id)
    text = f"# {cleaned.title}\n\n{cleaned.markdown}"
    return text[:MAX_DOCUMENT_CHARS]


def _fill(template_name: str, **values: str) -> str:
    text = (PROMPTS_DIR / template_name).read_text(encoding="utf-8")
    for name, value in values.items():
        text = text.replace("{{" + name + "}}", value)
    return text


def build_judge_prompt(question: Question, answer: str, gold_texts: Sequence[str]) -> str:
    nuggets = "\n".join(
        f"{index}. [{nugget.importance}] {nugget.text}"
        for index, nugget in enumerate(question.nuggets, start=1)
    )
    kind = KIND_TEXT.get(question.unanswerable_category or "", "可回答题：回答要覆盖下面的关键点")
    documents = "\n\n---\n\n".join(gold_texts) if gold_texts else "（这道题没有金标文档）"
    return _fill(
        "judge_v1.md",
        question=question.question,
        kind=kind,
        nuggets=nuggets or "（没有关键点）",
        documents=documents,
        answer=answer.strip() or "（空）",
    )


def extract_json(text: str) -> dict[str, Any]:
    """从输出里取出第一个 JSON 对象（评审有时会在前后多写一两句话或加代码块）。"""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise JudgeError(f"输出里没有 JSON：{text[:200]!r}")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise JudgeError(f"JSON 不合法：{error}") from error
    if not isinstance(parsed, dict):
        raise JudgeError("JSON 顶层不是对象")
    return parsed


def parse_verdict(text: str, nugget_count: int) -> JudgeVerdict:
    data = extract_json(text)
    labels = data.get("nuggets", [])
    if not isinstance(labels, list) or len(labels) != nugget_count:
        raise JudgeError(f"关键点标签应有 {nugget_count} 个，实际是 {labels!r}")
    labels = [str(label).strip().lower() for label in labels]
    if any(label not in NUGGET_LABELS for label in labels):
        raise JudgeError(f"关键点标签不合法：{labels}")
    behavior = str(data.get("behavior", "")).strip().lower()
    if behavior not in BEHAVIORS:
        raise JudgeError(f"behavior 不合法：{behavior!r}")
    return JudgeVerdict(
        nuggets=tuple(labels),
        contradiction=_as_bool(data.get("contradiction", False)),
        behavior=behavior,
        corrects_premise=_as_bool(data.get("corrects_premise", False)),
        covers_interpretations=_as_bool(data.get("covers_interpretations", False)),
    )


def _as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "是")
    return bool(value)


class Judge:
    def __init__(self, runner: PromptRunner) -> None:
        self._runner = runner

    async def judge(self, question: Question, answer: str) -> JudgeVerdict:
        texts = [gold_document_text(doc) for doc in question.gold_docs]
        return await self.judge_with_documents(question, answer, texts)

    async def judge_with_documents(
        self, question: Question, answer: str, gold_texts: Sequence[str]
    ) -> JudgeVerdict:
        prompt = build_judge_prompt(question, answer, gold_texts)
        last_error: JudgeError | None = None
        for _ in range(RETRIES + 1):
            output = await self._runner.run(prompt)
            try:
                return parse_verdict(output, len(question.nuggets))
            except JudgeError as error:
                last_error = error
                prompt += f"\n\n（上一次的输出不合法：{error}。请严格按要求只输出一个 JSON 对象。）"
        raise JudgeError(f"{question.id}：评审两次输出都不合法：{last_error}")

    async def sufficient(self, question: Question, contexts: Sequence[str]) -> bool:
        """给出的上下文够不够回答这道题（错误归因用）。"""
        prompt = _fill(
            "sufficiency_v1.md",
            question=question.question,
            contexts="\n\n---\n\n".join(contexts) or "（空）",
        )
        data = extract_json(await self._runner.run(prompt))
        return _as_bool(data.get("sufficient", False))
