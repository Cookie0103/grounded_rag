import hashlib
import json
from datetime import date
from pathlib import Path

from app.ingest.policy_corpus import build_policy_corpus


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
