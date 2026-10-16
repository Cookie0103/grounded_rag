"""按固定 commit 下载语料：先取文件列表（含 git blob 哈希），再逐个下载并校验。"""

import hashlib
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.errors import CorpusError
from app.ingest.corpus import (
    CORPUS_COMMIT,
    CORPUS_REPO,
    EXPECTED_DOCUMENT_COUNT,
    is_corpus_path,
)

DOWNLOAD_WORKERS = 8

FetchBytes = Callable[[str], bytes]


@dataclass(frozen=True)
class TreeEntry:
    path: str
    sha: str


@dataclass(frozen=True)
class FetchStats:
    downloaded: int
    skipped: int


def tree_url(repo: str = CORPUS_REPO, commit: str = CORPUS_COMMIT) -> str:
    return f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"


def raw_url(path: str, repo: str = CORPUS_REPO, commit: str = CORPUS_COMMIT) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def git_blob_sha(data: bytes) -> str:
    """git 对文件内容的哈希，和 GitHub 文件列表里的 sha 一致，用来校验下载是否完整。"""
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def select_entries(tree: dict[str, Any]) -> list[TreeEntry]:
    """从 GitHub 的文件列表里挑出语料文件；数量不对就报错并列出差异。"""
    if tree.get("truncated"):
        raise CorpusError("GitHub 返回的文件列表被截断，无法确定语料范围")
    entries = sorted(
        (
            TreeEntry(path=item["path"], sha=item["sha"])
            for item in tree["tree"]
            if item["type"] == "blob" and is_corpus_path(item["path"])
        ),
        key=lambda entry: entry.path,
    )
    if len(entries) != EXPECTED_DOCUMENT_COUNT:
        raise CorpusError(
            f"语料应有 {EXPECTED_DOCUMENT_COUNT} 篇，实际 {len(entries)} 篇；"
            "检查 corpus.py 里的 INCLUDE_PREFIXES / INCLUDE_FILES"
        )
    return entries


def fetch_entries(fetch: FetchBytes) -> list[TreeEntry]:
    return select_entries(json.loads(fetch(tree_url())))


def _is_up_to_date(target: Path, entry: TreeEntry) -> bool:
    return target.is_file() and git_blob_sha(target.read_bytes()) == entry.sha


def _download_one(entry: TreeEntry, raw_dir: Path, fetch: FetchBytes) -> bool:
    """下载一个文件；已存在且哈希一致就跳过。返回是否真的下载了。"""
    target = raw_dir / entry.path
    if _is_up_to_date(target, entry):
        return False
    data = fetch(raw_url(entry.path))
    if git_blob_sha(data) != entry.sha:
        raise CorpusError(f"下载的文件与 GitHub 记录的哈希不一致：{entry.path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def sync_corpus(entries: list[TreeEntry], raw_dir: Path, fetch: FetchBytes) -> FetchStats:
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        results = list(pool.map(lambda entry: _download_one(entry, raw_dir, fetch), entries))
    downloaded = sum(results)
    return FetchStats(downloaded=downloaded, skipped=len(results) - downloaded)
