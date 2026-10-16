import json
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import CorpusError
from app.ingest.corpus import EXPECTED_DOCUMENT_COUNT
from app.ingest.fetch import (
    TreeEntry,
    fetch_entries,
    git_blob_sha,
    raw_url,
    select_entries,
    sync_corpus,
    tree_url,
)

HELLO_BLOB_SHA = "ce013625030ba8dba906f756967f9e9ca394464a"  # git hash-object 对 "hello\n"


def _tree(count: int = EXPECTED_DOCUMENT_COUNT, *, truncated: bool = False) -> dict[str, Any]:
    items: list[dict[str, str]] = [
        {"path": f"zh/learn/doc{i:03}.mdx", "type": "blob", "sha": f"{i:040}"} for i in range(count)
    ]
    items += [
        {"path": "zh/learn", "type": "tree", "sha": "0" * 40},
        {"path": "zh/learn/pic.png", "type": "blob", "sha": "1" * 40},
        {"path": "zh/cli/overview.mdx", "type": "blob", "sha": "2" * 40},
        {"path": "en/learn/doc000.mdx", "type": "blob", "sha": "3" * 40},
    ]
    return {"truncated": truncated, "tree": items}


def test_git_blob_sha_matches_git() -> None:
    assert git_blob_sha(b"hello\n") == HELLO_BLOB_SHA


def test_urls_pin_the_commit() -> None:
    assert "c80a31868611b673bd77725a6310c685068a585e" in raw_url("zh/home.mdx")
    assert tree_url().endswith("?recursive=1")


def test_select_entries_keeps_only_corpus_files_in_sorted_order() -> None:
    entries = select_entries(_tree())

    assert len(entries) == EXPECTED_DOCUMENT_COUNT
    assert [entry.path for entry in entries] == sorted(entry.path for entry in entries)
    assert all(entry.path.startswith("zh/learn/") for entry in entries)


def test_select_entries_rejects_a_wrong_document_count() -> None:
    with pytest.raises(CorpusError, match="应有 182 篇，实际 181 篇"):
        select_entries(_tree(EXPECTED_DOCUMENT_COUNT - 1))


def test_select_entries_rejects_a_truncated_listing() -> None:
    with pytest.raises(CorpusError, match="截断"):
        select_entries(_tree(truncated=True))


def test_fetch_entries_parses_the_json_listing() -> None:
    def fake_fetch(url: str) -> bytes:
        assert url == tree_url()
        return json.dumps(_tree()).encode()

    assert len(fetch_entries(fake_fetch)) == EXPECTED_DOCUMENT_COUNT


def test_sync_downloads_once_then_skips(tmp_path: Path) -> None:
    content = {"zh/learn/a.mdx": b"hello\n", "zh/learn/b.mdx": b"second\n"}
    entries = [TreeEntry(path, git_blob_sha(data)) for path, data in content.items()]
    requested: list[str] = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return content[url.split("/c80a318", 1)[1].split("/", 1)[1]]

    first = sync_corpus(entries, tmp_path, fake_fetch)
    second = sync_corpus(entries, tmp_path, fake_fetch)

    assert (first.downloaded, first.skipped) == (2, 0)
    assert (second.downloaded, second.skipped) == (0, 2)
    assert len(requested) == 2
    assert (tmp_path / "zh/learn/a.mdx").read_bytes() == b"hello\n"


def test_sync_redownloads_a_corrupted_local_file(tmp_path: Path) -> None:
    entry = TreeEntry("zh/learn/a.mdx", git_blob_sha(b"hello\n"))
    target = tmp_path / entry.path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"truncated")

    stats = sync_corpus([entry], tmp_path, lambda _url: b"hello\n")

    assert stats.downloaded == 1
    assert target.read_bytes() == b"hello\n"


def test_sync_rejects_a_download_that_does_not_match_the_listed_hash(tmp_path: Path) -> None:
    entry = TreeEntry("zh/learn/a.mdx", git_blob_sha(b"hello\n"))

    with pytest.raises(CorpusError, match="哈希不一致"):
        sync_corpus([entry], tmp_path, lambda _url: b"something else")

    assert not (tmp_path / entry.path).exists()
