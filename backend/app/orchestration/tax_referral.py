"""识别房贷减税个案判断，保留一般制度与证明书办理。"""

import re
import unicodedata

from app.orchestration import prompts

TAX_REFERRAL_PROMPT = "tax_referral_v1"
_LOAN_TAX = re.compile(r"住宅借入金等特別控除|ローン(?:の)?(?:減税|控除)")
_TAX = re.compile(r"減税|控除|税金(?:が|は)?戻")
_PERSON = re.compile(
    r"私|自分|本人|お客[さ様]ま|お客様|うち(?:は|も|だと|の場合|の条件)"
    r"|この(?:ケース|条件|状況|場合)|我が家"
)
_ELIGIBILITY = re.compile(
    r"適用(?:の可否|可否|にな|され|でき)|対象(?:に|とな|ですか|かどうか)"
    r"|(?:受けられ|使え)(?:る|ます|そう)|(?:受ける|使う)ことが(?:でき|可能)"
    r"|受け(?:られる|られます)か|資格"
)
_AMOUNT = re.compile(r"いくら|ど(?:の|れ)くらい|控除額|減税額|戻(?:る|り|って)|金額|試算")
_JUDGMENT = re.compile(r"(?:判定|判断|試算|計算)(?:して|でき|をお願い|を頼)")
_GENERAL = re.compile(r"一般(?:的|に)|ど(?:んな|のような)(?:人|条件)|仕組み|計算方法|上限")
_PAPERWORK = re.compile(r"証明書|書類|再発行|発送|郵送|ダウンロード|申告書")
_BARE_ELIGIBILITY = re.compile(r"(?:控除|減税)(?:は|を)?(?:受けられ|使え)ますか")
_BARE_AMOUNT = re.compile(r"(?:いくら|ど(?:の|れ)くらい)[^。！？!?\n]{0,12}戻")
_DIRECT_ELIGIBILITY = re.compile(
    r"対象(?:に|とな)(?:る(?:の|か)|りますか)|対象ですか|適用(?:の可否|可否|されますか)"
    r"|(?:受けられ|使え)(?:ますか|る(?:のか|か|のかな))"
)


def _tax_topic(question: str) -> bool:
    return bool(_LOAN_TAX.search(question) or ("ローン" in question and _TAX.search(question)))


def needs_tax_referral(question: str) -> bool:
    """在生成前处理明确的个人资格判断或金额请求。"""
    question = unicodedata.normalize("NFKC", question)
    if not _tax_topic(question):
        return False
    if _PERSON.search(question) and (
        _DIRECT_ELIGIBILITY.search(question) or _JUDGMENT.search(question)
    ):
        return True
    if _GENERAL.search(question) or _PAPERWORK.search(question):
        return False
    if _PERSON.search(question) and (_ELIGIBILITY.search(question) or _AMOUNT.search(question)):
        return True
    return bool(
        _JUDGMENT.search(question)
        or _BARE_ELIGIBILITY.search(question)
        or _BARE_AMOUNT.search(question)
    )


def tax_referral_on_rejection(question: str, standalone_question: str | None) -> bool:
    """资格、金额咨询的末端撤回使用同一话术；证明书和明显一般题保持原兜底。"""
    for text in (question, standalone_question or ""):
        normalized = unicodedata.normalize("NFKC", text)
        if needs_tax_referral(normalized):
            return True
        if (
            _tax_topic(normalized)
            and not _GENERAL.search(normalized)
            and not _PAPERWORK.search(normalized)
            and (_ELIGIBILITY.search(normalized) or _AMOUNT.search(normalized))
        ):
            return True
    return False


def tax_referral_answer() -> str:
    return prompts.render(TAX_REFERRAL_PROMPT).strip()
