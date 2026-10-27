"""只读核验重评缓存与冻结清单，不调用真实评审。"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from eval.dataset import load_questions
from eval.judge import PROMPTS_DIR, parse_verdict
from scripts.rejudge import check_output_location
from scripts.rejudge_artifacts import (
    fingerprints,
    read_hashes,
    verify_frozen,
    verify_portable_hashes,
    verify_unchanged,
)


def audit_run(
    out_run: Path, src_run: Path, questions_path: Path, frozen_path: Path, *, partial: bool = False
) -> dict[str, int]:
    """校验模板、完整实现、源文件和标签覆盖；部分检查不冒充完成。"""
    verify_frozen(frozen_path)
    questions = load_questions(questions_path)
    check_output_location(any(q.split == "test" for q in questions), out_run)
    manifest = json.loads((out_run / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("template") != "judge_v2.md" or manifest.get("judge") != "claude -p":
        raise ValueError("评审模板或评审器不符")
    if manifest.get("system_rerun") is not False or manifest.get("retrieval_rerun") is not False:
        raise ValueError("运行来源不能证明未重跑系统/检索")
    expected = fingerprints(
        [
            *(src_run / name for name in ("answers.jsonl", "verdicts.jsonl", "report.md")),
            questions_path,
            PROMPTS_DIR / "judge_v2.md",
        ]
    )
    verify_portable_hashes(read_hashes(manifest.get("sha256")), expected)
    if manifest.get("seed_sha256"):
        verify_unchanged(read_hashes(manifest["seed_sha256"]))
    ids = _validate_labels(out_run / "verdicts.jsonl", {q.id: len(q.nuggets) for q in questions})
    if not partial and ids != {q.id for q in questions}:
        raise ValueError("评审尚未覆盖全部题目")
    if (out_run / "answers.jsonl").exists():
        raise ValueError("重评目录不应含新回答文件")
    errors = json.loads((out_run / "errors.json").read_text(encoding="utf-8"))
    if not partial and errors:
        raise ValueError("仍有当前评审错误")
    return {"planned": len(questions), "judged": len(ids), "errors": len(errors)}


def _validate_labels(path: Path, expected: dict[str, int]) -> set[str]:
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        question_id = row["question_id"]
        if question_id not in expected or question_id in ids:
            raise ValueError("标签含未知或重复题号")
        parse_verdict(line, expected[question_id])
        ids.add(question_id)
    return ids


def main(argv: Sequence[str] | None = None) -> None:
    """命令行只输出核验计数；任何失败都以非零退出。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--src-run", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args(argv)
    result = audit_run(args.run, args.src_run, args.questions, args.frozen, partial=args.partial)
    print_text = json.dumps(result, ensure_ascii=False)
    parser.exit(message=print_text + "\n")


if __name__ == "__main__":
    main()
