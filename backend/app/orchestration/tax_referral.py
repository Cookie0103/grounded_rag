"""识别房贷减税个案判断，保留一般制度与证明书办理。"""

import re
import unicodedata
from collections.abc import Iterator

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
    r"|(?:受けられ|使え|続けられ)(?:る|ます|そう)|(?:受ける|使う)ことが(?:でき|可能)"
    r"|(?:要件|条件)を満た|資格"
)
_AMOUNT = re.compile(r"いくら|ど(?:の|れ)くらい|控除額|減税額|戻(?:る|り|って)|金額|試算")
_JUDGMENT = re.compile(r"(?:判定|判断|試算|計算)(?:して|でき|をお願い|を頼)")
_GENERAL = re.compile(r"一般(?:的|に)|ど(?:んな|のような)(?:人|条件)|仕組み|計算方法|上限")
_PAPERWORK = re.compile(r"証明書|書類|再発行|発送|郵送|ダウンロード|申告書")
_BARE_ELIGIBILITY = re.compile(r"(?:控除|減税)(?:は|を)?(?:受けられ|使え)ますか")
_BARE_AMOUNT = re.compile(r"(?:いくら|ど(?:の|れ)くらい)[^。！？!?\n]{0,12}戻")
_QUESTION = re.compile(
    r"[?]|(?:か|かな|の)[!\s]*$|教え|知りたい|聞きたい|確認したい|相談したい|ほしい|欲しい"
    r"|いくら|ど(?:の|れ)くらい"
)
_CLAUSE = re.compile(r"[^。!?\n]+[!?]?")
_PERSONAL_REQUEST_WITH_DOCUMENT = re.compile(
    r"(?:控除額|減税額)[^。!?\n]{0,24}(?:いくら|ど(?:の|れ)くらい|試算|計算)"
    r"|(?:要件|条件)を満た|適用(?:の可否|可否|されますか)"
    r"|(?:控除|減税)を(?:受けられ|使え)"
)


def _tax_topic(question: str) -> bool:
    return bool(_LOAN_TAX.search(question) or ("ローン" in question and _TAX.search(question)))


def _case_questions(question: str) -> Iterator[str]:
    if not _tax_topic(question):
        return
    for clause in _CLAUSE.findall(question):
        if _GENERAL.search(clause) or not (_QUESTION.search(clause) or _JUDGMENT.search(clause)):
            continue
        if _PAPERWORK.search(clause) and not _PERSONAL_REQUEST_WITH_DOCUMENT.search(clause):
            continue
        if _ELIGIBILITY.search(clause) or _AMOUNT.search(clause):
            yield clause


def needs_tax_referral(question: str) -> bool:
    """在生成前处理明确的个人资格判断或金额请求。"""
    question = unicodedata.normalize("NFKC", question)
    personal = _PERSON.search(question) is not None
    return any(
        personal
        or _JUDGMENT.search(clause)
        or _BARE_ELIGIBILITY.search(clause)
        or _BARE_AMOUNT.search(clause)
        for clause in _case_questions(question)
    )


def tax_referral_on_rejection(question: str, standalone_question: str | None) -> bool:
    """资格、金额咨询的末端撤回使用同一话术；证明书和明显一般题保持原兜底。"""
    return any(
        next(_case_questions(unicodedata.normalize("NFKC", text)), None) is not None
        for text in (question, standalone_question or "")
    )


def tax_referral_answer() -> str:
    return prompts.render(TAX_REFERRAL_PROMPT).strip()
