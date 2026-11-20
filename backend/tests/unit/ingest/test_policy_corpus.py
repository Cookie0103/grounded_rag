import hashlib
import json
from datetime import date
from pathlib import Path

from app.ingest.policy_corpus import build_policy_corpus
from app.ingest.policy_pipeline import prepare_policy_document, read_policy_manifest


def test_build_marks_synthetic_documents_and_preserves_public_scope(tmp_path: Path) -> None:
    public = tmp_path / "raw" / "public"
    public.mkdir(parents=True)
    html = "<main><h1>住宅ローン</h1><p>返済の手続を確認します。</p></main>"
    (public / "hl-59.html").write_text(html, encoding="utf-8")
    url = "https://sonybank.jp/products/hl/59.html"
    catalog = {"url": url, "filename": "hl-59.html", "title": "返済手続", "in_scope": True}
    manifest = {
        **catalog,
        "saved_at": "2026-11-18T17:58:28+09:00",
        "sha256": hashlib.sha256(html.encode()).hexdigest(),
    }
    (public / "allowlist.json").write_text(json.dumps([catalog]), encoding="utf-8")
    (public / "manifest.jsonl").write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    first = build_policy_corpus(tmp_path, as_of=date(2026, 11, 18), target_documents=150)
    second = build_policy_corpus(tmp_path, as_of=date(2026, 11, 18), target_documents=150)

    assert first == second
    assert len(first) == 150
    assert first[0].policy.synthetic is False
    assert first[0].policy.source_url == url
    internal = [item for item in first if item.policy.source == "internal"]
    assert len(internal) >= 100
    assert all(
        item.policy.synthetic and item.policy.based_on == ("public/hl-59",) for item in internal
    )
    assert all("synthetic: true" in (tmp_path / item.path).read_text() for item in first[1:])


def test_synthetic_only_builds_ingestible_manifest_without_public_snapshots(tmp_path: Path) -> None:
    root = tmp_path / "data"

    items = build_policy_corpus(
        root, as_of=date(2026, 11, 18), target_documents=12, synthetic_only=True
    )

    assert read_policy_manifest(root) == items
    assert not (root / "raw").exists()
    assert [item.policy.corpus_tier for item in items] == ["S"] * 3 + ["L"] * 9
    assert {item.policy.source for item in items} == {"internal", "distractor"}
    for item in items:
        assert item.policy.synthetic is True
        assert item.policy.source_url is None
        assert "synthetic: true" in (root / item.path).read_text(encoding="utf-8")
        assert prepare_policy_document(root, item).chunked.children


def test_synthetic_only_keeps_current_and_historical_versions(tmp_path: Path) -> None:
    items = build_policy_corpus(
        tmp_path, as_of=date(2026, 11, 18), target_documents=3, synthetic_only=True
    )

    old, current = [item for item in items if item.policy.policy_id == "HL-DEMO-DOCS"]
    assert old.id == "internal/HL-DEMO-DOCS-v1"
    assert old.policy.status == "offline"
    assert old.policy.effective_to == current.policy.effective_from == date(2026, 11, 1)
    assert current.id == "internal/HL-DEMO-DOCS-v2"
    assert current.policy.status == "online"
    assert current.policy.effective_to is None
    assert "連絡方法の希望" in (tmp_path / current.path).read_text(encoding="utf-8")
