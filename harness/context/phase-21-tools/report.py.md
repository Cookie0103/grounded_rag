"""只读复算消融结果：保留逐题配对，复用既有评分和bootstrap。"""
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from eval.dataset import load_questions
from eval.evaluate import EvalResult, load_verdicts, retrieval_stats, latency_p95_ms, cost_per_question
from eval.metrics import mean
from eval.report import render_report
from eval.runner import load_cache
from eval.scoring import ScoredQuestion, score_question, summarize, bootstrap_interval, nugget_recall

OUT = Path(__file__).resolve().parent
NAMES = ("no-retrieval", "naive-rag", "hybrid-no-rerank", "hybrid-rag", "routed", "full")
LABELS = ("无检索", "向量RAG", "混合、不精排", "混合+精排", "改写与路由", "完整系统")
RETRIEVALS = ("vector", "bm25", "hybrid", "hybrid-rerank")
RETRIEVAL_LABELS = ("仅向量", "仅BM25", "混合、不精排", "混合+精排")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def paired(before, after):
    ids = sorted(set(before) & set(after))
    differences = [after[i] - before[i] for i in ids]
    low, high = bootstrap_interval(differences)
    return {"n": len(ids), "mean_difference": mean(differences), "ci_low": low, "ci_high": high,
            "increases": [i for i in ids if after[i] > before[i]],
            "decreases": [i for i in ids if after[i] < before[i]]}


def pct(value):
    return f"{100 * value:.2f}%"


def diff_text(result, multiplier=100):
    return f"{result['mean_difference'] * multiplier:+.2f} [{result['ci_low'] * multiplier:+.2f}, {result['ci_high'] * multiplier:+.2f}]"


def main():
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in manifest["sha256"].items())
    qs = load_questions(ROOT / "docs/eval/dev70/questions.jsonl")
    eligible = {q.id for q in qs if q.answerable and q.gold_docs}
    records = [json.loads(line) for line in (OUT / "retrieval.jsonl").read_text(encoding="utf-8").splitlines()]
    groups = {n: {r["question_id"]: r for r in records if r["system"] == n} for n in RETRIEVALS}
    assert len(records) == 224 and all(set(g) == eligible for g in groups.values())
    retrieval = {n: {"n": len(g), "hits": sum(r["hit"] for r in g.values()),
        "recall_at_5": mean([float(r["hit"]) for r in g.values()]),
        "mrr": mean([r["mrr"] for r in g.values()]),
        "p95_ms": float(np.percentile([r["latency_ms"] for r in g.values()], 95)),
        "mean_ms": mean([r["latency_ms"] for r in g.values()])} for n, g in groups.items()}
    retrieval_diffs = {}
    mrr_diffs = {}
    for first, second in (("vector", "hybrid"), ("bm25", "hybrid"), ("hybrid", "hybrid-rerank")):
        retrieval_diffs[f"{first}->{second}"] = paired(
            {i: float(r["hit"]) for i, r in groups[first].items()},
            {i: float(r["hit"]) for i, r in groups[second].items()})
        mrr_diffs[f"{first}->{second}"] = paired(
            {i: r["mrr"] for i, r in groups[first].items()},
            {i: r["mrr"] for i, r in groups[second].items()})
    summary = {"manifest": "manifest.json", "protected_hashes_unchanged": True,
        "analysis_scripts_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (OUT / "report.py", OUT / "audit.py", OUT / "public_audit.py")},
        "retrieval": retrieval, "retrieval_differences": retrieval_diffs,
        "retrieval_mrr_differences": mrr_diffs, "systems": {}, "answer_differences": {}}
    lines = ["# 开发集消融实测（2026-10-22）", "",
        "同一份70道开发题；可回答且有金标题56道。仅开发集，不读取或运行封存测试集。",
        f"代码：`{manifest['code_commit']}`；语料：`{manifest['corpus_commit']}`。",
        "配置：Qwen3-Embedding-0.6B、Qwen3-Reranker-0.6B、CUDA、DeepSeek deepseek-flash、temperature=0。",
        "输入/源码/提示词哈希、模型包版本和逐题原始数据见同轮manifest及JSONL。", "",
        "## 检索消融（全部完成）", "",
        "原问题直接检索；各版本候选top5个子块映射并去重为文档；每个必要金标组至少命中一篇才算整题命中。",
        "同一分母56，排除14道不可回答题；OR来源沿用原hit_groups_at_k。MRR使用等价金标并集。",
        "GPU预热后每题四档循环轮换顺序、串行运行；未复用检索结果缓存。", "",
        "| 方案 | 命中/分母 | Recall@5 | MRR | 平均ms | P95 ms |",
        "|---|---:|---:|---:|---:|---:|"]
    for n, label in zip(RETRIEVALS, RETRIEVAL_LABELS):
        r = retrieval[n]
        lines.append(f"| {label} | {r['hits']}/{r['n']} | {pct(r['recall_at_5'])} | {r['mrr']:.4f} | {r['mean_ms']:.1f} | {r['p95_ms']:.1f} |")
    lines += ["", "| 配对比较 | Recall差值，百分点 [95%区间] | MRR差值 [95%区间] | Recall改善/退步题数 |", "|---|---:|---:|---:|"]
    for name, r in retrieval_diffs.items():
        m = mrr_diffs[name]
        mrr_text = f"{m['mean_difference']:+.4f} [{m['ci_low']:+.4f}, {m['ci_high']:+.4f}]"
        lines.append(f"| {name} | {diff_text(r)} | {mrr_text} | {len(r['increases'])}/{len(r['decreases'])} |")
    lines += ["", "精排相对混合检索：Recall净增2题（4改善、2退步），差值区间含0；MRR提高0.1071，配对区间约[0.0163, 0.1979]。",
        "本轮支持精排让第一篇相关文档更靠前；对整题必要文档全部进入top5的收益仍不确定，同时平均检索耗时增加约187.5ms。",
        "以上是该固定开发题集的一次观测，探索性区间未做多重比较校正，不能外推为普遍收益。", "",
        "逐题例子：dev021（Workflow受理/结束帧）精排后streaming文档升至首位，原混合结果未命中；",
        "dev080（Arize与Phoenix的空间字段）精排后前5块只来自Phoenix的两版文档，Arize必要来源被挤出，MRR仍为1但整题Recall从命中变为未命中。",
        "另一退步题dev046也失去goto-anything必要来源。这些观察说明按子块精排可能集中在少数文档，名次改善与跨篇覆盖是不同指标；本轮保留失败，不调参补分。"]
    lines += ["", "## 回答质量与运行成本", "",
        "所有档位重新作答，独立缓存；六档按题交错且循环轮换，四题并发。预热不计入延迟，P95包含同机资源竞争。",
        "同题生成一次，temperature=0仍不能排除模型随机变化。前三种RAG使用同一baseline_naive_rag_v1提示词与父块扩展。",
        "评审统一为Claude CLI默认模型、原judge_v2；复用score_question、summarize与原报告函数，未改规则或提示词。",
        "原v2评审仅在此前20条完整系统样本经作者复核预标校准；本轮新系统答案尚无新的人类校准，分数为自动评审实验结果。", "",
        "可信得分范围[-1,1]，由原+1/+0.5/0/-1规则汇总；V_strict为已评可回答题的vital要点完整支持比例的宏平均，partial不计；未评题不补0。",
        "各指标分母不同：可信得分只含已评审题，V_strict只含已评审的可回答题（列中括号为题数），Recall只含已生成的可回答金标题，延迟/费用来自全部已生成回答。", "",
        "| 方案 | 作答/70 | 评审/作答 | 可信得分 [95%区间] | V_strict（题数） | Recall@5 | P95秒 | 生成元/题 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    scored_maps = {}
    all_scored = {}
    details = []
    for name, label in zip(NAMES, LABELS):
        answers = load_cache(OUT / name / "answers.jsonl")
        verdicts = load_verdicts(OUT / name / "verdicts.jsonl")
        selected = [q for q in qs if q.id in answers]
        scored = [ScoredQuestion(q, verdicts[q.id], score_question(q, verdicts[q.id]))
                  for q in selected if q.id in verdicts]
        s = summarize(scored)
        answer_list = [answers[q.id] for q in selected]
        ret = retrieval_stats(list(zip(selected, answer_list)))
        vital_n = sum(item.question.answerable for item in scored)
        r = {"answers": len(answers), "judged": len(scored), "v_strict_question_count": vital_n, "trust": asdict(s),
             "retrieval": asdict(ret), "p95_ms": latency_p95_ms(answer_list),
             "generation_cny_per_question": cost_per_question(answer_list),
             "generation_cny_total": sum(a.cost_cny for a in answer_list)}
        summary["systems"][name] = r
        scored_maps[name] = {s.question.id: s.score.points for s in scored}
        all_scored[name] = {s.question.id: s for s in scored}
        if answer_list:
            result = EvalResult(name, selected, answer_list, scored=scored)
            (OUT / name / "report.md").write_text(render_report(result), encoding="utf-8")
        trust_text = f"{s.trust:+.3f} [{s.ci_low:+.3f}, {s.ci_high:+.3f}]" if scored else "待评"
        lines.append(f"| {label} | {len(answers)}/70 | {len(scored)}/{len(answers)} | {trust_text} | {pct(s.v_strict) if scored else '待评'} ({vital_n}) | {ret.recall_at_5 * 100:.2f}% ({ret.questions}) | {r['p95_ms']/1000:.2f} | {r['generation_cny_per_question']:.5f} |")
        for item in scored:
            details.append({"system": name, "question_id": item.question.id,
                "answerable": item.question.answerable, "points": item.score.points,
                "label": item.score.label, "v_strict": nugget_recall(item, vital_only=True) if item.question.answerable else None,
                "verdict": asdict(item.verdict)})
    lines += ["", "| 相邻档比较 | 同题数 | 可信得分差 [95%区间] | V_strict差，百分点 [95%区间] |", "|---|---:|---:|---:|"]
    for first, second in zip(NAMES[:-1], NAMES[1:]):
        trust = paired(scored_maps[first], scored_maps[second])
        vital = paired({i: nugget_recall(s, vital_only=True) for i, s in all_scored[first].items() if s.question.answerable},
                       {i: nugget_recall(s, vital_only=True) for i, s in all_scored[second].items() if s.question.answerable})
        summary["answer_differences"][f"{first}->{second}"] = {"trust": trust, "v_strict": vital}
        lines.append(f"| {first} → {second} | {trust['n']} | {diff_text(trust, 1) if trust['n'] else '待评'} | {diff_text(vital) if vital['n'] else '待评'} |")
    complete = all(r["answers"] == 70 and r["judged"] == 70 for r in summary["systems"].values())
    summary["complete"] = complete
    summary["generation_total_cny"] = sum(r["generation_cny_total"] for r in summary["systems"].values())
    common_ids = set.intersection(*(set(m) for m in scored_maps.values()))
    common_summary = {n: asdict(summarize([all_scored[n][i] for i in sorted(common_ids)])) for n in NAMES}
    summary["common_judged_ids"] = sorted(common_ids)
    summary["common_judged_summary"] = common_summary
    if not complete:
        types = dict(Counter(q.type for q in qs if q.id in common_ids))
        lines += ["", "### 共同已评审子集（仅断点诊断）", "",
            f"六档共同已评{len(common_ids)}题，题号为`{', '.join(sorted(common_ids))}`。这是执行顺序形成的子集，不是随机抽样，不能替代70题全量消融。",
            f"共同子集题型：`{json.dumps(types, ensure_ascii=False)}`；V_strict分母为其中{sum(q.answerable for q in qs if q.id in common_ids)}道可回答题。",
            "Claude周额度耗尽（CLI明确返回2026-10-25 12:00 Asia/Tokyo恢复），后续标签待恢复后续评；未换评审器或修改Prompt。", "",
            "| 方案 | 共同题数 | 可信得分 | V_strict |", "|---|---:|---:|---:|"]
        for n, label in zip(NAMES, LABELS):
            r = common_summary[n]
            lines.append(f"| {label} | {r['count']} | {r['trust']:+.4f} | {pct(r['v_strict'])} |")
    lines += ["", "## 解释边界与复现", "",
        f"本轮状态：{'六档全量完成' if complete else '回答质量评审未完成，表中按实际分母；不得当作70题全量质量结论'}。",
        f"本轮六档已生成回答的合计记账估算费用：¥{summary['generation_total_cny']:.6f}。",
        "区间来自同题配对差值的bootstrap（沿用原函数1000次、种子0）；包含0时不能宣称稳定提升。探索性多组比较，未做多重校正；区间仅反映题目抽样，不涵盖judge误差或生成随机波动。",
        "routed同时加入护栏、路由、改写/分解与不同的引用生成提示词；full同时增加证据评分、补检索、校验/再生成/拒答，不能把组间差值再分给其中某一个模块。",
        "所有RAG都使用父块扩展，本轮无法估计父子块策略的独立贡献。检索命中率也不能等同答案准确率。",
        "全链路Recall@5沿用原评测器对累计retrieved_docs前5文档的计算，单次检索四档表则来自最终top5子块；复杂系统额外检索的全部证据不由此完整刻画。",
        "生成费用为原provider按项目固定token单价估算并入账，非账单实扣；不含Claude订阅用量。", "",
        "在backend目录执行（需要已有数据库、本地CUDA模型、DeepSeek密钥与Claude CLI）：", "",
        "```powershell", "$env:HF_HUB_OFFLINE='1'", "$env:PYTHONUTF8='1'",
        ".\\.venv\\Scripts\\python.exe ..\\.cache\\ablation-20261022\\run.py retrieval",
        ".\\.venv\\Scripts\\python.exe ..\\.cache\\ablation-20261022\\run.py generate",
        ".\\.venv\\Scripts\\python.exe ..\\.cache\\ablation-20261022\\run.py judge",
        ".\\.venv\\Scripts\\python.exe ..\\.cache\\ablation-20261022\\report.py", "```", "",
        "同目录命令只续本轮断点；新实验须使用新目录并冻结新manifest。执行脚本与只读复算脚本随阶段context归档，原始JSONL留.cache/ablation-20261022。"]
    write_json(OUT / "summary.json", summary)
    lines.insert(2, f"> 状态：检索四档已全量完成；六档共生成{sum(r['answers'] for r in summary['systems'].values())}/420份回答、评审{sum(r['judged'] for r in summary['systems'].values())}/420份。{'全量完成。' if complete else '回答质量评审不完整，所有质量分数仅作断点诊断，不是70题最终成绩。'}\n")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "scores.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in details), encoding="utf-8")
    print(json.dumps({"retrieval": retrieval, "retrieval_differences": retrieval_diffs,
        "systems": {n: {k: r[k] for k in ("answers", "judged")} for n, r in summary["systems"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
