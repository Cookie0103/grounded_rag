"""阶段 36 用例契约与种子真值。"""

import json
from collections import Counter
from pathlib import Path

import pytest

from app.orchestration.guard import check_input
from app.orchestration.pii import redact_pii
from eval.copilot_cases import CopilotCase, load_cases, validate_cases
from scripts.generate_copilot_cases import generate_cases


@pytest.fixture(scope="module")
def generated() -> list[CopilotCase]:
    """保留一次默认种子的生成结果供各项断言使用。"""
    return generate_cases()


def test_generated_suites_cover_expected_scenarios(generated: list[CopilotCase]) -> None:
    assert Counter(case.category for case in generated) == {
        "intent": 160,
        "lookup": 40,
        "lane": 20,
        "guard": 20,
    }
    intents = [case for case in generated if case.category == "intent"]
    assert Counter(case.expected_intent for case in intents) == {
        "smalltalk": 40,
        "complaint": 40,
        "policy": 40,
        "lookup": 40,
    }
    assert sum(len(case.history) >= 2 for case in intents) == 40
    lookup = [case for case in generated if case.category == "lookup"]
    assert Counter(case.fault for case in lookup if case.fault) == {"timeout": 4, "5xx": 4}
    assert sum(case.expected_outcome == "denied" for case in lookup) == 6
    assert sum(case.large_response for case in lookup) == 4
    lane = [case for case in generated if case.category == "lane"]
    assert Counter(case.expected_outcome for case in lane) == {"answer": 12, "handoff": 8}
    assert all(case.channel == "customer" and not case.expected_tools for case in lane)
    assert Counter(case.guard_kind for case in generated if case.category == "guard") == {
        "pii": 5,
        "injection": 5,
        "unsupported_number": 5,
        "promise": 5,
    }
    assert all(case.synthetic for case in generated)
    assert Counter(case.split for case in generated) == {"dev": 192, "holdout": 48}
    assert not validate_cases(generated, scope="synthetic")


def test_lookup_gold_changes_with_seed(generated: list[CopilotCase]) -> None:
    assert any(case.expected_claims == ("34日", "408058円", "4335円") for case in generated)
    assert any("1.830％" in case.expected_claims for case in generated)
    assert any(
        {"420回", "2026年12月15日", "156334円"} <= set(case.expected_claims)
        for case in generated
        if case.large_response
    )
    other = {case.id: case for case in generate_cases(seed=34)}
    assert any(
        other[case.id].expected_claims != case.expected_claims
        for case in generated
        if "408058円" in case.expected_claims
    )
    assert generated == generate_cases()


def test_guard_inputs_exercise_redaction_and_injection_controls(
    generated: list[CopilotCase],
) -> None:
    assert all(
        redact_pii(case.question) != case.question for case in generated if case.guard_kind == "pii"
    )
    assert all(check_input(case.question) for case in generated if case.guard_kind == "injection")


def test_load_legacy_author_policy_fields(tmp_path: Path) -> None:
    path = tmp_path / "policy.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "policy-dev-demo",
                "type": "version",
                "split": "dev",
                "question": "案内を受ける時期によって書類は変わりますか。",
                "gold_docs": ["example@obsolete"],
                "gold_doc_groups": [["example@obsolete", "alternative@obsolete"]],
                "as_of": "2026-09-01",
                "nuggets": [
                    {"text": "有効日を確かめる。", "importance": "vital"},
                    {"text": "対象の手続きを区別する。", "importance": "okay"},
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (case,) = load_cases(path)
    assert case.category == "policy"
    assert case.version_trap
    assert case.as_of is not None
    assert case.required_groups == (("example@obsolete", "alternative@obsolete"),)
    assert not validate_cases([case], known_documents={"example@obsolete", "alternative@obsolete"})


def test_validate_flags_duplicate_and_missing_as_of(tmp_path: Path) -> None:
    path = tmp_path / "policy.jsonl"
    line = (
        '{"id":"invalid","question":"以前の規程を確認したいです。","type":"version",'
        '"gold_docs":["unknown@obsolete"],"nuggets":[{"text":"条件","importance":"vital"}]}\n'
    )
    path.write_text(line * 2, encoding="utf-8")
    issues = validate_cases(load_cases(path), known_documents=set())
    assert any("重复" in issue.message for issue in issues)
    assert any("as_of" in issue.message for issue in issues)
    assert any("unknown@obsolete" in issue.message for issue in issues)
