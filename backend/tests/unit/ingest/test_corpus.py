from pathlib import Path

import pytest

from app.ingest.corpus import (
    category_of,
    document_id,
    edition_of,
    is_corpus_path,
    list_raw_files,
)


@pytest.mark.parametrize(
    "path",
    [
        "zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx",
        "zh/self-host/deploy/configuration/environments.mdx",
        "zh/learn/key-concepts.mdx",
        "zh/api-reference/guides/x.mdx",
        "zh/cloud/use-dify/monitor/x.mdx",
        "zh/cloud/use-dify/workspace/x.mdx",
        "zh/home.mdx",
        "zh/quick-start.mdx",
    ],
)
def test_corpus_paths_are_included(path: str) -> None:
    assert is_corpus_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "zh/cloud/use-dify/build/x.mdx",  # 云版只收 knowledge / workspace / monitor
        "zh/develop-plugin/getting-started/x.mdx",
        "zh/cli/overview.mdx",
        "en/learn/key-concepts.mdx",
        "zh/learn/image.png",
        "zh/api-reference/openapi_service.json",
        "README.md",
    ],
)
def test_other_paths_are_excluded(path: str) -> None:
    assert not is_corpus_path(path)


@pytest.mark.parametrize(
    ("path", "doc_id", "edition", "category"),
    [
        (
            "zh/self-host/use-dify/knowledge/create-knowledge/import-text-data/readme.mdx",
            "self-host/use-dify/knowledge/create-knowledge/import-text-data/readme",
            "self_host",
            "knowledge",
        ),
        ("zh/cloud/use-dify/monitor/x.mdx", "cloud/use-dify/monitor/x", "cloud", "monitor"),
        (
            "zh/self-host/deploy/configuration/environments.mdx",
            "self-host/deploy/configuration/environments",
            "self_host",
            "deploy",
        ),
        ("zh/learn/key-concepts.mdx", "learn/key-concepts", "common", "learn"),
        (
            "zh/api-reference/guides/x.mdx",
            "api-reference/guides/x",
            "common",
            "api-reference",
        ),
        ("zh/home.mdx", "home", "common", "home"),
        (
            "zh/self-host/use-dify/getting-started/quick.mdx",
            "self-host/use-dify/getting-started/quick",
            "self_host",
            "getting-started",
        ),
    ],
)
def test_document_id_edition_and_category_come_from_the_path(
    path: str, doc_id: str, edition: str, category: str
) -> None:
    assert document_id(path) == doc_id
    assert edition_of(doc_id) == edition
    assert category_of(doc_id) == category


def test_file_directly_under_use_dify_has_use_dify_category() -> None:
    assert category_of("self-host/use-dify/readme") == "use-dify"


def test_list_raw_files_is_sorted_and_only_mdx(tmp_path: Path) -> None:
    for name in ["zh/b.mdx", "zh/a/z.mdx", "zh/a/a.mdx", "zh/skip.png"]:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("x", encoding="utf-8")

    listed = [path.relative_to(tmp_path).as_posix() for path in list_raw_files(tmp_path)]

    assert listed == ["zh/a/a.mdx", "zh/a/z.mdx", "zh/b.mdx"]
