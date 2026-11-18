from eval.copilot_report import (
    Calibration,
    EvalRow,
    RunMetadata,
    build_metrics,
    paired_top5,
    render_report,
)


def test_top5_requires_every_group_and_distinguishes_unobserved_retrieval() -> None:
    hits = EvalRow(
        case_id="synthetic-1",
        category="policy",
        policy_answerable=True,
        gold_doc_groups=(("alt-a", "a"), ("b",)),
        retrieved_docs=("a", "a", "c", "d", "e", "b"),
    )
    miss = hits.model_copy(update={"case_id": "synthetic-2", "retrieved_docs": ()})
    unknown = hits.model_copy(update={"case_id": "synthetic-3", "retrieved_docs": None})

    metrics = build_metrics([hits, miss, unknown])

    assert metrics["top5"].value == 0.5
    assert metrics["top5"].n == 2


def test_paired_top5_uses_common_case_ids_and_seeded_interval() -> None:
    s1 = EvalRow(
        case_id="synthetic-1",
        category="policy",
        policy_answerable=True,
        gold_docs=("a",),
        retrieved_docs=("a",),
    )
    s2 = s1.model_copy(update={"case_id": "synthetic-2"})
    l1 = s1.model_copy(update={"tier": "L", "retrieved_docs": ()})
    l3 = s1.model_copy(update={"tier": "L", "case_id": "synthetic-3"})

    delta = paired_top5([s1, s2], [l3, l1])

    assert (delta.n, delta.value, delta.low, delta.high) == (1, -1.0, -1.0, -1.0)


def test_tool_failure_rate_weights_call_counts_including_denials() -> None:
    row = EvalRow(
        case_id="synthetic-1",
        category="lookup",
        tools_ok=1,
        tools_failed=1,
        tools_denied=1,
        degraded_correctly=True,
    )
    other = EvalRow(
        case_id="synthetic-2",
        category="lookup",
        tools_ok=2,
        tools_failed=0,
        tools_denied=0,
        degraded_correctly=False,
    )
    unobserved = EvalRow(case_id="synthetic-3", category="lookup")

    metrics = build_metrics([row, other, unobserved])

    assert metrics["tool_failure"].value == 0.2
    assert metrics["tool_failure"].n == 5
    assert metrics["degradation"].value == 1.0
    assert metrics["degradation"].n == 1


def test_expired_versions_include_response_citations_and_top_five_only() -> None:
    base = EvalRow(
        case_id="synthetic-1",
        category="policy",
        version_trap=True,
        retrieved_docs=("a", "b", "c", "d", "e", "old"),
        citation_docs=(),
        expired_docs=("old",),
    )
    citation = base.model_copy(update={"case_id": "synthetic-2", "citation_docs": ("old",)})
    unknown = base.model_copy(update={"case_id": "synthetic-3", "citation_docs": None})
    empty = base.model_copy(
        update={"case_id": "synthetic-4", "retrieved_docs": (), "expired_docs": None}
    )

    result = build_metrics([base, citation, unknown, empty])["expired"]

    assert (result.numerator, result.n) == (1, 3)


def test_report_uses_observed_latency_and_calibrated_offline_labels_only() -> None:
    slow = EvalRow(
        case_id="synthetic-1",
        category="intent",
        expected_intent="lookup",
        intent="policy",
        prior_turns=2,
        first_token_ms=4000,
        latency_ms=5000,
        generation_ms=3500,
        cost_cny=0.01,
        offline_acceptable=True,
        passed=False,
    )
    fast = EvalRow(
        case_id="synthetic-2",
        category="intent",
        expected_intent="lookup",
        intent="lookup",
        first_token_ms=2000,
        latency_ms=3000,
        cost_cny=0.03,
        offline_acceptable=False,
        passed=True,
    )
    metadata = RunMetadata(dataset="合成冒烟", hardware={"芯片": "Apple"}, warmup=1, concurrency=2)

    report = render_report([slow, fast], metadata, calibration=Calibration(matched=16, total=20))

    assert "3,900.00 毫秒" in report
    assert "4,900.00 毫秒" in report
    assert "¥0.020000" in report
    assert "未达到 100 条" in report
    assert "| 多轮意图准确率（第 3 轮起） | 0.00%" in report
    assert "| 离线可采纳率 | 未测" in report
    assert "80.00%" in report
    assert "生成节点耗时最高" in report
    assert "意图错" in report
    assert "| lookup | 0 | 0 | 1 | 1 |" in report
    assert "注入 5% 超时" in report
    assert "坐席采纳率 | 未测" in report

    calibrated = render_report(
        [slow, fast], metadata, calibration=Calibration(matched=17, total=20)
    )
    assert "| 离线可采纳率 | 50.00%" in calibrated


def test_cost_multiple_uses_paired_sessions_and_dify_baseline() -> None:
    matching = EvalRow(case_id="synthetic-1", category="policy", cost_cny=0.02)
    langgraph_only = matching.model_copy(update={"case_id": "synthetic-2", "cost_cny": 0.50})
    dify = matching.model_copy(update={"system": "Dify V3", "cost_cny": 0.01})
    dify_only = dify.model_copy(update={"case_id": "synthetic-3", "cost_cny": 0.75})

    report = render_report([matching, langgraph_only, dify, dify_only], RunMetadata())

    assert "| LangGraph | S | 无注入 | 2.00 倍 | 1 |" in report
    assert "| Dify V3 | S | 无注入 | 1.00 倍 | 2 |" in report
