"""阶段 37 并排报告及开发集保护。"""

from argparse import Namespace
from pathlib import Path

import pytest

from eval.copilot_cases import CopilotCase
from eval.copilot_observations import TurnObservation
from eval.copilot_report import EvalRow
from eval.dify_replay import DifyMeasurement
from scripts.compare_dify import (
    CompareConditions,
    _measure,
    comparison_table,
    read_development_cases,
)


def _row(case: str, system: str, **fields: object) -> EvalRow:
    return EvalRow.model_validate(
        {"case_id": case, "category": "intent", "system": system, **fields}
    )


def test_comparison_table_limits_measures_to_shared_cases() -> None:
    rows = [
        _row("shared", "Dify V3", latency_ms=1100, cost_cny=0.2, passed=True),
        _row("shared", "LangGraph", latency_ms=800, cost_cny=0.1, passed=False),
        _row("unpaired", "LangGraph", latency_ms=10000, cost_cny=100.0, passed=True),
    ]
    report = comparison_table(
        rows,
        CompareConditions(same_machine=True, same_gateway=True, dify_warmup=2, langgraph_warmup=2),
    )
    assert "1,100.00 毫秒" in report
    assert "800.00 毫秒" in report
    assert "10,000.00 毫秒" not in report
    assert "0.50 倍" in report
    assert "[+300.00 毫秒, +300.00 毫秒]" in report
    assert "同机、同网关、串行，双方均预热" in report


def test_sealed_paths_are_rejected_before_reading(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="封存"):
        read_development_cases(tmp_path / "sealed-test.jsonl", None)


@pytest.mark.asyncio
async def test_resume_uses_completed_cache_without_opening_api(tmp_path: Path) -> None:
    finished = DifyMeasurement(
        case_id="cached", fault_mode="none", observation=TurnObservation(answer="承知しました。")
    )
    (tmp_path / "observations.jsonl").write_text(
        finished.model_dump_json() + "\n", encoding="utf-8"
    )
    case = CopilotCase(id="cached", category="intent", question="こんにちは。", synthetic=True)
    rows = await _measure(Namespace(run_dir=tmp_path, fault_mode="none", report_only=False), [case])
    assert rows == [finished]
