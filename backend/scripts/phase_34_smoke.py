"""在本机通过生产入口测量合成日文样例的双泳道节点耗时。"""

import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import median

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import CACHE_DIR, get_settings
from app.orchestration.models import Channel, Intent
from app.providers.budget import BudgetLedger


@dataclass(frozen=True)
class Sample:
    question: str
    expected: Intent
    channel: Channel = "customer"
    customer_id: str = "C0001"
    agent_id: str = "A001"


SAMPLES = (
    Sample("こんにちは。", "smalltalk"),
    Sample("ありがとうございます。", "smalltalk"),
    Sample("おはようございます！", "smalltalk", "agent"),
    Sample("お世話になっています。", "smalltalk", "agent"),
    Sample("対応に納得できません。責任者に代わってください。", "complaint"),
    Sample("先ほどの案内について苦情を申し立てたいです。", "complaint"),
    Sample("連絡がなく困っています。上席に確認してもらえますか。", "complaint", "agent"),
    Sample("担当者の説明に不満があります。正式に申し出たいです。", "complaint", "agent"),
    Sample("一部繰上返済をするには、どんな手続が必要ですか。", "policy"),
    Sample("住宅ローンの事前審査ではどんな書類を用意しますか。", "policy"),
    Sample("返済用口座へ入金する方法を教えてください。", "policy"),
    Sample("固定金利の適用期間が終わる前の手続を教えてください。", "policy", "agent"),
    Sample("団体信用生命保険の取扱いを確認したいです。", "policy", "agent"),
    Sample("住宅ローンの金利タイプ変更について教えてください。", "policy", "agent"),
    Sample("このお客さまの住宅ローン契約を一覧で確認してください。", "lookup", "agent"),
    Sample("契約L0001の次回の返済予定額を照会してください。", "lookup", "agent"),
    Sample(
        "このお客さまに返済の延滞があるか確認してください。", "lookup", "agent", "C0002", "A002"
    ),
    Sample("私の来月の返済額はいくらですか。", "lookup"),
    Sample("契約L0001の次回返済額と一部繰上返済の手続を教えてください。", "lookup", "agent"),
    Sample(
        "契約L0004の適用金利を照会し、固定金利の期間終了時の手続も説明してください。",
        "lookup",
        "agent",
        "C0004",
        "A004",
    ),
)


def _summary(milliseconds: list[float]) -> dict[str, int | float]:
    return {
        "count": len(milliseconds),
        "median_ms": round(median(milliseconds), 2),
        "p95_ms": round(sorted(milliseconds)[math.ceil(len(milliseconds) * 0.95) - 1], 2),
    }


def run() -> None:
    settings = get_settings()
    if settings.chat_model != "gateway":
        raise SystemExit("阶段 34 冒烟要求经本机网关运行，请设置 CHAT_MODEL=gateway。")
    ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
    initial_spend = ledger.spent()
    app = create_app()
    durations: dict[str, list[float]] = defaultdict(list)
    rows: list[dict[str, object]] = []
    with TestClient(app) as client:
        warm_up = client.post("/retrieve", json={"query": "住宅ローン", "top_k": 1})
        warm_up.raise_for_status()
        for index, sample in enumerate(SAMPLES, 1):
            ledger.check()
            request: dict[str, object] = {
                "question": sample.question,
                "channel": sample.channel,
                "filter": {"corpus_tier": "S", "as_of": date(2026, 11, 18).isoformat()},
            }
            if sample.channel == "agent":
                request.update(agent_id=sample.agent_id, customer_id=sample.customer_id)
            started = time.perf_counter()
            response = client.post("/chat", json=request)
            elapsed = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            result = response.json()
            durations["end_to_end"].append(elapsed)
            steps = [
                {"name": step["name"], "ms": step["ms"], "note": step["note"]}
                for step in result["steps"]
            ]
            if any("模型不可用" in step["note"] for step in steps):
                raise SystemExit(f"样例 {index} 的网关模型不可用，已停止调用。")
            for step in steps:
                durations[step["name"]].append(step["ms"])
            rows.append(
                {
                    "sample": index,
                    "expected_intent": sample.expected,
                    "intent": result["intent"],
                    "secondary_intent": result["secondary_intent"],
                    "channel": sample.channel,
                    "elapsed_ms": round(elapsed, 2),
                    "degraded": result["degraded"],
                    "abstained": result["abstained"],
                    "citations": len(result["citations"]),
                    "tools": [
                        {
                            "name": call["tool_name"],
                            "status": call["status"],
                            "reason": call["reason"],
                        }
                        for call in result["tool_calls"]
                    ],
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "cost_cny": result["cost_cny"],
                    "steps": steps,
                }
            )
    summary = {key: _summary(values) for key, values in durations.items()}
    report = {
        "synthetic": True,
        "samples": len(rows),
        "primary_intent_matches": sum(item["intent"] == item["expected_intent"] for item in rows),
        "daily_spend_delta_cny": round(ledger.spent() - initial_spend, 8),
        "latency": summary,
        "rows": rows,
    }
    path = CACHE_DIR / "phase-34-orchestration-smoke.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(
        json.dumps(
            {key: value for key, value in report.items() if key != "rows"}, ensure_ascii=False
        )
        + "\n"
    )


if __name__ == "__main__":
    run()
