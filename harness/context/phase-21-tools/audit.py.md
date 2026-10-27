"""只读审计完整消融产物，核对真实开关、分母、配对与原预算账本。"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import CACHE_DIR, get_settings
from app.providers.budget import BudgetLedger
from app.providers.deepseek import cost_cny
from eval.dataset import load_questions
from eval.evaluate import load_verdicts
from eval.judge import parse_verdict
from eval.runner import load_cache
from eval.scoring import score_question

OUT = Path(__file__).resolve().parent
NAMES = ("no-retrieval", "naive-rag", "hybrid-no-rerank", "hybrid-rag", "routed", "full")
manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
qs = {q.id: q for q in load_questions(ROOT / "docs/eval/dev70/questions.jsonl")}
assert len(qs) == 70 and all(q.split == "dev" for q in qs.values())
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in manifest["sha256"].items())
counts = {}
total_cost = 0.0
all_scores = {}
for name in NAMES:
    answers_path = OUT / name / "answers.jsonl"
    verdicts_path = OUT / name / "verdicts.jsonl"
    answers = load_cache(answers_path)
    verdicts = load_verdicts(verdicts_path)
    assert set(answers) == set(qs) and set(verdicts) <= set(qs)
    assert len(answers_path.read_text(encoding="utf-8").splitlines()) == 70
    verdict_lines = verdicts_path.read_text(encoding="utf-8").splitlines()
    assert len(verdict_lines) == len(verdicts)
    for line in verdict_lines:
        row = json.loads(line)
        parse_verdict(line, len(qs[row["question_id"]].nuggets))
    rows = []
    for question_id, answer in answers.items():
        assert answer.error is None and answer.answer is not None
        total_cost += answer.cost_cny
        if question_id in verdicts:
            rows.append(score_question(qs[question_id], verdicts[question_id]).points)
        for step in answer.steps:
            if name == "no-retrieval":
                assert step.name == "generate" and not answer.contexts
            if name == "routed" and step.name in ("grade", "verify"):
                assert step.note == "已关闭"
            if name == "full" and step.name in ("grade", "verify"):
                assert step.note != "已关闭"
            if step.details is None:
                continue
            for r in step.details.retrievals:
                assert not r.cached and not r.degraded
                if name in ("naive-rag", "hybrid-no-rerank"):
                    assert not r.reranked_candidates
                    assert all(c.rerank_score is None for c in r.candidates)
                if name == "naive-rag":
                    assert all(c.bm25_rank is None for c in r.recall_candidates)
                if name == "hybrid-rag":
                    assert r.reranked_candidates
                    assert all(c.rerank_score is not None for c in r.candidates)
    assert math.isclose(sum(rows) / len(rows), summary["systems"][name]["trust"]["trust"], abs_tol=1e-12)
    counts[name] = {"answers": len(answers), "verdicts": len(verdicts)}
    all_scores[name] = {i: score_question(qs[i], verdicts[i]).points for i in verdicts}
for first, second in zip(NAMES[:-1], NAMES[1:]):
    common = set(all_scores[first]) & set(all_scores[second])
    delta = sum(all_scores[second][i] - all_scores[first][i] for i in common) / len(common)
    expected = summary["answer_differences"][f"{first}->{second}"]["trust"]
    assert expected["n"] == len(common) and math.isclose(delta, expected["mean_difference"], abs_tol=1e-12)
completions = [json.loads(line) for line in (OUT / "completions.jsonl").read_text(encoding="utf-8").splitlines()]
token_cost = sum(cost_cny(c["prompt_tokens"], c["completion_tokens"]) for c in completions)
ledger = BudgetLedger(CACHE_DIR / "budget", get_settings().daily_budget_cny)
budget_delta = ledger.spent() - manifest["budget_before_cny"]
assert math.isclose(total_cost, token_cost, abs_tol=1e-9)
assert math.isclose(total_cost, budget_delta, abs_tol=1e-9)
assert ledger.spent() <= get_settings().daily_budget_cny
report = {"protected_hashes_unchanged": True, "counts": counts,
    "analysis_scripts_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (OUT / "report.py", OUT / "audit.py", OUT / "public_audit.py")},
    "all_answers_complete": all(c["answers"] == 70 for c in counts.values()),
    "all_verdicts_complete": all(c["verdicts"] == 70 for c in counts.values()),
    "switches_and_uncached_retrieval_verified": True, "paired_scores_recomputed": True,
    "generation_cost_cny": total_cost, "token_cost_cny": token_cost, "budget_delta_cny": budget_delta,
    "completion_calls": len(completions), "api_model_names": sorted(set(c["model"] for c in completions)),
    "model_fingerprints": json.loads((OUT / "model-fingerprints.json").read_text(encoding="utf-8-sig")),
    "claude_cli": "2.1.306 / default model, remote model version not pinned",
    "raw_sha256": {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.rglob("*.jsonl"))},
    "human_calibrated_on_new_answers": False, "test_set_read": False}
(OUT / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in ("model_fingerprints", "raw_sha256")}, ensure_ascii=False))
