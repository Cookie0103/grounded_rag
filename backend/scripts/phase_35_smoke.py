"""经本机 HTTP 测量 20 条日文流式冒烟的首字、整段与撤回。"""

import argparse
import json
import sys
from collections import defaultdict

from app.core.config import CACHE_DIR, get_settings
from app.providers.budget import BudgetLedger
from scripts.phase_34_smoke import SAMPLES, _summary
from scripts.stream_client import ask_stream


def run(port: int) -> None:
    settings = get_settings()
    if settings.chat_model != "gateway":
        raise SystemExit("阶段 35 冒烟要求使用本机网关。")
    ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
    initial_spend = ledger.spent()
    client_first: list[float] = []
    client_total: list[float] = []
    trace_first: list[float] = []
    trace_total: list[float] = []
    generated_first: list[float] = []
    generated_total: list[float] = []
    node_times: dict[str, list[float]] = defaultdict(list)
    rows: list[dict[str, object]] = []
    for index, sample in enumerate(SAMPLES, 1):
        ledger.check()
        body: dict[str, object] = {
            "question": sample.question,
            "channel": sample.channel,
            "filter": {"corpus_tier": "S", "as_of": "2026-11-18"},
        }
        if sample.channel == "agent":
            body.update(agent_id=sample.agent_id, customer_id=sample.customer_id)
        result = ask_stream(port, body)
        answer = result.answer
        if answer is None or result.first_delta_ms is None:
            raise RuntimeError(f"样例 {index} 没有收到完整的流式内容")
        steps = answer["steps"]
        if any("模型不可用" in step["note"] for step in steps):
            raise SystemExit(f"样例 {index} 的网关模型不可用，已停止调用。")
        client_first.append(result.first_delta_ms)
        client_total.append(result.total_ms)
        trace_first.append(float(answer["first_token_ms"]))
        trace_total.append(float(answer["total_ms"]))
        for step in steps:
            node_times[step["name"]].append(float(step["ms"]))
        if any(step["name"] == "generate" for step in steps):
            generated_first.append(result.first_delta_ms)
            generated_total.append(result.total_ms)
        rows.append(
            {
                "sample": index,
                "intent": answer["intent"],
                "degraded": answer["degraded"],
                "abstained": answer["abstained"],
                "first_delta_client_ms": round(result.first_delta_ms, 2),
                "total_client_ms": round(result.total_ms, 2),
                "first_token_trace_ms": answer["first_token_ms"],
                "total_trace_ms": answer["total_ms"],
                "retractions": result.retractions,
                "prompt_tokens": answer["prompt_tokens"],
                "completion_tokens": answer["completion_tokens"],
                "cost_cny": answer["cost_cny"],
                "steps": [
                    {"name": step["name"], "ms": step["ms"], "note": step["note"]} for step in steps
                ],
            }
        )
    summary = {
        "synthetic": True,
        "samples": len(rows),
        "retracted_responses": sum(bool(row["retractions"]) for row in rows),
        "client_first": _summary(client_first),
        "client_total": _summary(client_total),
        "trace_first": _summary(trace_first),
        "trace_total": _summary(trace_total),
        "generated_client_first": _summary(generated_first) if generated_first else None,
        "generated_client_total": _summary(generated_total) if generated_total else None,
        "nodes": {name: _summary(values) for name, values in node_times.items()},
        "daily_spend_delta_cny": round(ledger.spent() - initial_spend, 8),
    }
    path = CACHE_DIR / "phase-35-stream-smoke.json"
    path.write_text(
        json.dumps({**summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sys.stdout.write(json.dumps(summary, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    run(parser.parse_args().port)


if __name__ == "__main__":
    main()
