"""把本机公开快照与可重现的日文合成规程整理成两档语料。"""

import hashlib
from datetime import date, datetime, timedelta
from itertools import product
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, TypeAdapter

from app.core.errors import CorpusError
from app.core.policy import PolicyMetadata

TARGET_DOCUMENTS = 3000
RATE_MONTHS = 24
SYNTHETIC_SEED = 430218
_CONTEXTS = ("電話応対", "書面案内", "折返し連絡")
_SUBJECTS = (
    ("返済条件の確認", "hl-59"),
    ("繰上返済の案内", "hl-59"),
    ("金利見直しの説明", "hl-57"),
    ("手数料の案内", "hl-fees"),
    ("証明書の照会", "hl-60"),
    ("完済後の連絡", "hl-62"),
    ("団信の請求受付", "hl-63"),
    ("団信の保障確認", "hl-08"),
    ("契約資料の照会", "hl-04"),
    ("共有契約の受付", "hl-42"),
    ("提出書類の確認", "hl-07"),
    ("住所等の変更案内", "hl-61"),
)
_DISTRACTORS = (
    ("fx_deposit", "外貨預金"),
    ("card_loan", "カードローン"),
    ("investment_trust", "投資信託"),
    ("yen_deposit", "円預金"),
    ("debit_card", "デビットカード"),
    ("home_loan", "住宅改修ローン"),
)
_DISTRACTOR_TOPICS = ("残高照会", "証明書手続", "返済方法", "金利の確認", "条件変更")
_DISTRACTOR_CHECKS = {
    "外貨預金": "対象の通貨と期間を確認し、条件が異なる資料は案内候補から外す。",
    "カードローン": "住宅ローンの資料と混在しないよう、対象の契約と商品名を記録する。",
    "投資信託": "商品の説明と個別の判断を混同しないよう、資料の対象範囲だけを確認する。",
    "円預金": "普通預金と期間のある商品で案内資料を取り違えないよう、公開資料の表題を照合する。",
    "デビットカード": "カードの利用に関する手続か、預金口座に関する手続かを聞き分けて記録する。",
    "住宅改修ローン": (
        "住宅購入に関する契約と改修に関する契約を分け、対象工事の確認は担当に引き継ぐ。"
    ),
}
_POLICY_TYPES = {
    "hl-57": "rate",
    "hl-rates": "rate",
    "hl-fees": "fee",
    "hl-08": "insurance",
    "hl-05": "insurance",
    "hl-63": "insurance",
    "hl-59": "repayment",
}


class PolicyMaterial(BaseModel):
    """语料源标识、相对路径及可写入两种索引的元数据。"""

    model_config = ConfigDict(frozen=True)

    id: str
    path: str
    policy: PolicyMetadata


class _PublicItem(BaseModel):
    url: str
    filename: str
    in_scope: bool = True


class _SavedPage(_PublicItem):
    saved_at: datetime
    sha256: str


def build_policy_corpus(
    root: Path, *, as_of: date, target_documents: int = TARGET_DOCUMENTS
) -> list[PolicyMaterial]:
    """读取保存清单并生成有标记的内部层、干扰层和入库索引清单。"""
    public = _load_public(root)
    if not public:
        raise CorpusError("公开层清单里没有可用的住宅贷款页面")
    evidence_by_id = {item.id: item for item in public}
    core = public + _make_internal(root, as_of, public[0], evidence_by_id)
    if len(core) > target_documents:
        raise CorpusError(f"目标篇数 {target_documents} 小于 S 档的 {len(core)} 篇")
    result = core + _make_distractors(root, as_of, target_documents - len(core))
    (root / "policy_index.jsonl").write_text(
        "".join(f"{item.model_dump_json()}\n" for item in result), encoding="utf-8"
    )
    return result


def _load_public(root: Path) -> list[PolicyMaterial]:
    public_dir = root / "raw" / "public"
    catalog = TypeAdapter(list[_PublicItem]).validate_json(
        (public_dir / "allowlist.json").read_bytes()
    )
    saved = {
        page.url: page
        for line in (public_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for page in [_SavedPage.model_validate_json(line)]
    }
    return [
        _public_material(root, item, saved[item.url])
        for item in sorted(catalog, key=lambda row: row.filename)
        if item.in_scope and item.url in saved
    ]


def _public_material(root: Path, item: _PublicItem, saved: _SavedPage) -> PolicyMaterial:
    filename = Path(item.filename)
    address = urlsplit(item.url)
    if (
        filename.name != item.filename
        or filename != Path(saved.filename)
        or address.scheme != "https"
        or address.hostname != "sonybank.jp"
    ):
        raise CorpusError(f"公开层清单不一致：{item.filename}")
    relative = Path("raw") / "public" / filename
    if hashlib.sha256((root / relative).read_bytes()).hexdigest() != saved.sha256:
        raise CorpusError(f"公开文件哈希不一致：{filename.name}")
    key = filename.stem
    return PolicyMaterial(
        id=f"public/{key}",
        path=relative.as_posix(),
        policy=PolicyMetadata(
            source="public",
            synthetic=False,
            product_line="home_loan",
            policy_type="faq" if key.startswith("faq-") else _POLICY_TYPES.get(key, "procedure"),
            policy_id=f"PUBLIC-{key.upper()}",
            effective_from=saved.saved_at.date(),
            status="online",
            corpus_tier="S",
            source_url=item.url,
        ),
    )


def _make_internal(
    root: Path, as_of: date, fallback: PolicyMaterial, evidence_by_id: dict[str, PolicyMaterial]
) -> list[PolicyMaterial]:
    transition = as_of.replace(day=1)
    materials: list[PolicyMaterial] = []
    for number, ((subject, source), channel) in enumerate(product(_SUBJECTS, _CONTEXTS), 1):
        evidence = evidence_by_id.get(f"public/{source}", fallback)
        materials.extend(_procedure_group(root, subject, channel, number, transition, evidence))
    rates_source = evidence_by_id.get("public/hl-rates", fallback)
    materials.extend(_rate_notices(root, transition, rates_source))
    return materials


def _procedure_group(
    root: Path, subject: str, channel: str, number: int, transition: date, evidence: PolicyMaterial
) -> list[PolicyMaterial]:
    policy_id = f"HL-OPS-{number:03d}"
    guidance = (
        "受付メモにはお問い合わせの種類だけを残し、確認後に案内する。",
        "受付メモには確認済み、追加確認、専門窓口への取次ぎの区分を残す。",
    )
    old = _internal_policy(
        policy_id, evidence, transition - timedelta(days=365), effective_to=transition
    )
    current = _internal_policy(policy_id, evidence, transition)
    versions = [
        _write(
            root,
            f"{policy_id}-v{version}",
            f"{subject}・{channel}（版 {version}）",
            policy,
            _procedure_body(subject, channel, line, evidence),
        )
        for version, (policy, line) in enumerate(zip((old, current), guidance, strict=True), 1)
    ]
    faq_policy = _internal_policy(f"{policy_id}-FAQ", evidence, transition)
    versions.append(
        _write(
            root,
            f"{policy_id}-faq",
            f"{subject}・{channel}の応対例",
            faq_policy,
            _procedure_body(subject, channel, "確認した公開資料を応対記録に記載する。", evidence),
        )
    )
    return versions


def _procedure_body(subject: str, channel: str, guidance: str, evidence: PolicyMaterial) -> str:
    return (
        f"## {subject}の流れ\n\n"
        f"{channel}の訓練では、まずお客さまが一般の手続と個別契約のどちらを尋ねているかを確認する。"
        "一般の手続は公開資料に示された範囲を案内する。個別の契約情報が必要な場合は、"
        "お客さまと担当者の関係を確認する手順へ引き継ぐ。未確認の金額、期日、条件をその場で確約しない。"
        f"{guidance}\n\n"
        "応対例「お問い合わせの内容を確認いたします。一般のご案内とお客さまごとの"
        "確認事項を分けて、確認できる範囲からお伝えいたします。」資料の対象が異なる場合は無理に推測せず、"
        "関係する窓口へつなぐ。案内を続ける前に、資料の日付と適用範囲を確認し、"
        "判断が必要な事項は担当窓口への引継ぎ事項として短く記録する。\n\n"
        f"参照先 ID {evidence.id}。この手順は訓練用の仮想業務であり、過去の行内運用を示さない。"
    )


def _internal_policy(
    policy_id: str,
    evidence: PolicyMaterial,
    effective_from: date,
    *,
    effective_to: date | None = None,
) -> PolicyMetadata:
    return PolicyMetadata(
        source="internal",
        synthetic=True,
        product_line="home_loan",
        policy_type="rate" if policy_id.startswith("HL-RATE-") else "procedure",
        policy_id=policy_id,
        effective_from=effective_from,
        effective_to=effective_to,
        status="offline" if effective_to is not None else "online",
        corpus_tier="S",
        based_on=(evidence.id,),
    )


def _shift_month(month: date, offset: int) -> date:
    year, month_index = divmod(month.year * 12 + month.month - 1 + offset, 12)
    return date(year, month_index + 1, 1)


def _rate_notices(root: Path, month: date, evidence: PolicyMaterial) -> list[PolicyMaterial]:
    result = []
    for offset in range(1 - RATE_MONTHS, 1):
        starts = _shift_month(month, offset)
        end = _shift_month(month, offset + 1) if offset < 0 else None
        policy_id = f"HL-RATE-{starts:%Y-%m}"
        fictional_rate = 1 + _seeded_number(policy_id) % 2001 / 1000
        body = (
            "## 訓練用の月次通知\n\n"
            f"{starts:%Y年%m月}の訓練に使う架空の商品Aの年率は{fictional_rate:.3f}％とする。"
            "この値は検索と版管理の検証専用であり、銀行が公開している適用金利、"
            "過去の金利、優遇、見積りのいずれも表さない。既存契約の適用金利を説明するときは"
            "契約情報の確認手順に引き継ぐ。次回の訓練資料に移る際は、案内資料の年月と版番号を照合して、"
            "対象外の月の値を使わない。\n\n"
            "比較例に旧版の値を載せるときは、当月の欄と分けて対象年月を併記する。"
            "応対記録には基準日、照合した資料の ID と版を残す。確認先が複数あるときは、"
            "どの版を表示したかと、説明に使った版が一致しているかを別々にチェックする。\n\n"
            f"参照先 ID {evidence.id}。参照は公開ページの通知形式に限り、数値はすべて架空。"
        )
        result.append(
            _write(
                root,
                policy_id,
                f"{starts:%Y年%m月}・架空の金利通知",
                _internal_policy(policy_id, evidence, starts, effective_to=end),
                body,
            )
        )
    return result


def _make_distractors(root: Path, as_of: date, count: int) -> list[PolicyMaterial]:
    result = []
    for number in range(1, count + 1):
        product_line, product_label = _DISTRACTORS[
            _seeded_number(f"product:{number}") % len(_DISTRACTORS)
        ]
        topic = _DISTRACTOR_TOPICS[_seeded_number(f"topic:{number}") % len(_DISTRACTOR_TOPICS)]
        channel = _CONTEXTS[_seeded_number(f"channel:{number}") % len(_CONTEXTS)]
        policy_id = f"DIST-{number:04d}"
        start = as_of - timedelta(days=60 + _seeded_number(policy_id) % 660)
        expired = product_line == "home_loan" and number % 2 == 0
        metadata = PolicyMetadata(
            source="distractor",
            synthetic=True,
            product_line=product_line,
            policy_type="procedure",
            policy_id=policy_id,
            effective_from=start,
            effective_to=as_of - timedelta(days=30) if expired else None,
            status="offline" if expired else "online",
            corpus_tier="L",
        )
        body = _distractor_body(product_label, topic, channel, policy_id)
        result.append(
            _write(root, policy_id, f"架空の{product_label}・{topic}・{channel}", metadata, body)
        )
    return result


def _seeded_number(key: str) -> int:
    return int(hashlib.sha256(f"{SYNTHETIC_SEED}:{key}".encode()).hexdigest()[:8], 16)


def _distractor_body(product: str, topic: str, channel: str, policy_id: str) -> str:
    return (
        f"## {product}の{topic}\n\n"
        f"この文書は{channel}を想定した架空商品の応対例。整理番号 {policy_id} を控え、"
        f"お客さまが一般の{topic}を求めているか、個別の契約の確認を求めているかを把握する。"
        "案内できる範囲を確認してから関連資料を参照する。個別情報が必要な場合は照会の権限を確認し、"
        "確認できていない条件や金額は回答しない。既に照会した内容と次に確認する内容を分けて記録する。"
        "折返しが必要な場合は、確認先と伝える内容を受付記録に残して担当窓口へ引き継ぐ。"
        "適用条件、書類の発行、受付の可否に関する例示はシナリオごとに見直す。"
        f"資料を取り違えないよう、案内対象と版の有効期間を再度照合する。{_DISTRACTOR_CHECKS[product]}"
    )


def _write(
    root: Path, key: str, title: str, policy: PolicyMetadata, markdown: str
) -> PolicyMaterial:
    relative = Path("synthetic") / policy.source / f"{key}.md"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"---\nsynthetic: true\n---\n# {title}\n\n{markdown}\n\n合成資料（検証専用）\n",
        encoding="utf-8",
    )
    return PolicyMaterial(id=f"{policy.source}/{key}", path=relative.as_posix(), policy=policy)
