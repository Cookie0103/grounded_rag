"""检查评测题：`uv run poe eval-validate [文件]`。格式、配额、金标文档是否真的在语料里。"""

import argparse
import sys
from pathlib import Path

from app.ingest.corpus import RAW_DIR, document_id, list_raw_files
from eval.dataset import load_questions, quota_report, validate_questions

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "data" / "dev.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="检查评测题")
    parser.add_argument("questions", nargs="?", type=Path, default=DEFAULT_QUESTIONS)
    arguments = parser.parse_args()
    questions = load_questions(arguments.questions)
    known = {document_id(path.relative_to(RAW_DIR).as_posix()) for path in list_raw_files(RAW_DIR)}
    issues = validate_questions(questions, known or None)
    for issue in issues:
        mark = "错误" if issue.is_error else "提醒"
        sys.stdout.write(f"[{mark}] {issue.question_id}：{issue.message}\n")
    sys.stdout.write("\n".join(quota_report(questions)) + "\n")
    errors = [issue for issue in issues if issue.is_error]
    sys.stdout.write(f"\n{len(errors)} 个错误，{len(issues) - len(errors)} 个提醒\n")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
