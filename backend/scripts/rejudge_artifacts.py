"""缓存重评的文件校验与错误历史；不调用模型或检索。"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.core.config import REPO_ROOT

FROZEN_FILES = (
    "eval/judge.py",
    "eval/evaluate.py",
    "eval/prompts/judge_v2.md",
    "scripts/rejudge.py",
    "scripts/rejudge_artifacts.py",
    "scripts/audit_rejudge.py",
)


def write_json(path: Path, value: object) -> None:
    """先写同目录临时文件再替换，避免中断留下半份JSON。"""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def fingerprints(paths: Sequence[Path]) -> dict[str, str]:
    """所有指定文件都必须存在；不忽略缺失文件。"""
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def read_hashes(value: object) -> dict[str, str]:
    """只接受非空字符串键值哈希表。"""
    if not isinstance(value, dict) or not value:
        raise ValueError("哈希表缺失或为空")
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise ValueError("哈希表键值必须是字符串")
    return {str(key): str(digest) for key, digest in value.items()}


def _by_filename(hashes: Mapping[str, str]) -> dict[str, str]:
    result = {key.replace("\\", "/").rsplit("/", 1)[-1]: value for key, value in hashes.items()}
    if len(result) != len(hashes):
        raise ValueError("哈希表包含重名文件，拒绝不明确的路径映射")
    return result


def verify_portable_hashes(recorded: Mapping[str, str], expected: Mapping[str, str]) -> None:
    """对明确列出的文件逐项比对；跨平台路径只映射唯一文件名。"""
    before, after = _by_filename(recorded), _by_filename(expected)
    if not before or before.keys() != after.keys() or before != after:
        raise ValueError("冻结哈希缺键、多键或内容不一致")


def verify_unchanged(hashes: Mapping[str, str]) -> None:
    """复核保护文件，即使异常退出也不能跳过。"""
    if fingerprints([Path(path) for path in hashes]) != hashes:
        raise RuntimeError("旧运行、题集、标签缓存或评审模板在重评期间发生变化")


def verify_frozen(path: Path) -> None:
    """显式核对本版完整实现清单，拒绝缺失、额外或不匹配的冻结项。"""
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    expected = fingerprints([REPO_ROOT / "backend" / name for name in FROZEN_FILES])
    verify_portable_hashes(read_hashes(record.get("frozen_files")), expected)


def record_errors(out_run: Path, errors: Mapping[str, str]) -> dict[str, list[str]]:
    """保留每题历史错误；成功补评不会删除此前记录。"""
    path = out_run / "errors-history.json"
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(history, dict) or any(
        not isinstance(key, str)
        or not isinstance(messages, list)
        or any(not isinstance(message, str) for message in messages)
        for key, messages in history.items()
    ):
        raise ValueError("错误历史格式不合法")
    result: dict[str, list[str]] = {key: list(messages) for key, messages in history.items()}
    for question_id, message in errors.items():
        messages = result.setdefault(question_id, [])
        if message not in messages:
            messages.append(message)
    write_json(path, result)
    return result
