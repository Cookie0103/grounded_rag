import json
import sys
from pathlib import Path

import pytest

from app.providers.fakes import FakeChatModel
from eval.dataset import Nugget, Question
from eval.judge import (
    ChatPromptRunner,
    CommandPromptRunner,
    Judge,
    JudgeError,
    build_judge_prompt,
    extract_json,
    gold_document_text,
    parse_verdict,
)

QUESTION = Question(
    "q1",
    "知识库一次最多上传几个文件",
    ("d1",),
    nuggets=(Nugget("最多 5 个", "vital"), Nugget("由 UPLOAD_FILE_BATCH_LIMIT 控制", "okay")),
)
GOOD = {
    "nuggets": ["support", "partial_support"],
    "contradiction": False,
    "behavior": "answered",
    "corrects_premise": False,
    "covers_interpretations": False,
}


def test_prompt_contains_question_numbered_nuggets_documents_and_answer() -> None:
    prompt = build_judge_prompt(QUESTION, "最多 5 个。", ["# 上传本地文件\n\n正文"])

    assert "知识库一次最多上传几个文件" in prompt
    assert "1. [vital] 最多 5 个" in prompt
    assert "2. [okay] 由 UPLOAD_FILE_BATCH_LIMIT 控制" in prompt
    assert "# 上传本地文件" in prompt
    assert "最多 5 个。" in prompt
    assert "{{" not in prompt  # 占位符都填了


def test_prompt_describes_the_expected_behavior_of_an_unanswerable_question() -> None:
    question = Question(
        "u", "怎么改", (), type="unanswerable", unanswerable_category="false_premise"
    )

    prompt = build_judge_prompt(question, "", [])

    assert "指出前提不成立" in prompt
    assert "（没有关键点）" in prompt
    assert "（空）" in prompt
    assert "（这道题没有金标文档）" in prompt


def test_json_is_extracted_from_surrounding_text_and_code_fences() -> None:
    wrapped = "好的，结果如下：\n```json\n" + json.dumps(GOOD) + "\n```\n以上。"

    assert extract_json(wrapped)["behavior"] == "answered"


@pytest.mark.parametrize("text", ["没有 JSON", "{坏掉的 json}", "[1, 2]"])
def test_text_without_a_json_object_is_rejected(text: str) -> None:
    with pytest.raises(JudgeError):
        extract_json(text)


def test_verdict_is_parsed_and_labels_are_normalized() -> None:
    data = {**GOOD, "nuggets": ["Support", " NOT_SUPPORT "], "contradiction": "true"}

    verdict = parse_verdict(json.dumps(data), 2)

    assert verdict.nuggets == ("support", "not_support")
    assert verdict.contradiction is True
    assert verdict.behavior == "answered"


def test_missing_optional_fields_default_to_false() -> None:
    verdict = parse_verdict(json.dumps({"nuggets": [], "behavior": "refused"}), 0)

    assert (verdict.contradiction, verdict.corrects_premise, verdict.covers_interpretations) == (
        False,
        False,
        False,
    )


@pytest.mark.parametrize(
    "data",
    [
        {**GOOD, "nuggets": ["support"]},  # 数量不对
        {**GOOD, "nuggets": ["support", "maybe"]},  # 标签不合法
        {**GOOD, "behavior": "ignored"},  # 行为不合法
        {**GOOD, "nuggets": "support"},  # 不是数组
    ],
)
def test_invalid_verdicts_are_rejected(data: dict[str, object]) -> None:
    with pytest.raises(JudgeError):
        parse_verdict(json.dumps(data), 2)


async def test_judge_returns_the_verdict_from_the_model() -> None:
    chat = FakeChatModel(responses=[json.dumps(GOOD)])
    judge = Judge(ChatPromptRunner(chat))

    verdict = await judge.judge_with_documents(QUESTION, "最多 5 个", ["文档"])

    assert verdict.nuggets == ("support", "partial_support")
    assert "最多 5 个" in chat.calls[0][0].content


async def test_judge_retries_once_when_the_output_is_not_valid() -> None:
    chat = FakeChatModel(responses=["我觉得不错", json.dumps(GOOD)])
    judge = Judge(ChatPromptRunner(chat))

    verdict = await judge.judge_with_documents(QUESTION, "答", ["文档"])

    assert verdict.behavior == "answered"
    assert len(chat.calls) == 2
    assert "上一次的输出不合法" in chat.calls[1][0].content


async def test_judge_gives_up_after_two_invalid_outputs() -> None:
    judge = Judge(ChatPromptRunner(FakeChatModel(responses=["不是", "还不是"])))

    with pytest.raises(JudgeError, match="两次"):
        await judge.judge_with_documents(QUESTION, "答", ["文档"])


async def test_sufficiency_judgement() -> None:
    chat = FakeChatModel(
        responses=['{"sufficient": true, "reason": "有依据"}', '{"sufficient": "no"}']
    )
    judge = Judge(ChatPromptRunner(chat))

    assert await judge.sufficient(QUESTION, ["上下文"]) is True
    assert await judge.sufficient(QUESTION, []) is False
    assert "（空）" in chat.calls[1][0].content


async def test_command_runner_pipes_the_prompt_through_stdin(tmp_path: Path) -> None:
    script = tmp_path / "echo_json.py"
    script.write_text(
        "import json, sys\n"
        "prompt = sys.stdin.read()\n"
        "labels = ['support'] * 2\n"
        "print(json.dumps({'nuggets': labels, 'behavior': 'answered', 'n': len(prompt)}))\n",
        encoding="utf-8",
    )
    judge = Judge(CommandPromptRunner([sys.executable, str(script)]))

    verdict = await judge.judge_with_documents(QUESTION, "答案", ["文档"])

    assert verdict.nuggets == ("support", "support")


async def test_command_runner_reports_a_failing_command(tmp_path: Path) -> None:
    script = tmp_path / "fail.py"
    script.write_text("import sys\nsys.stderr.write('boom')\nsys.exit(3)\n", encoding="utf-8")

    with pytest.raises(JudgeError, match="退出码 3：boom"):
        await CommandPromptRunner([sys.executable, str(script)]).run("x")


async def test_command_runner_times_out(tmp_path: Path) -> None:
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")

    with pytest.raises(JudgeError, match="没有返回"):
        await CommandPromptRunner([sys.executable, str(script)], timeout=0.5).run("x")


def test_gold_document_text_is_cleaned_and_truncated(tmp_path: Path) -> None:
    source = tmp_path / "zh" / "learn" / "a.mdx"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\ntitle: 标题\n---\n\n<Note>\n注意\n</Note>\n" + "字" * 20000, encoding="utf-8"
    )

    text = gold_document_text("learn/a", raw_dir=tmp_path)

    assert text.startswith("# 标题\n\n**注意：**")
    assert "<Note>" not in text
    assert len(text) == 12000
