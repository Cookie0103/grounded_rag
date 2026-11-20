"""区分需要专门转介的还款商谈与一般手续、查数。"""

import re
import unicodedata

_PAYMENT = r"(?:返済|支払(?:い)?|引き?落とし)"
_TOPIC = rf"(?:{_PAYMENT}|ローン)"
_PAYMENT_TOPIC = re.compile(_TOPIC)
_PREPAYMENT = re.compile(r"繰(?:り)?上(?:げ)?返済")
_SENTENCE_BOUNDARY = re.compile(r"[。！？!?\n]")
_EXPLICIT_COMPLAINT = re.compile(
    r"(?:苦情|クレーム)(?:があり|を|です|として|の申し立て)"
    r"|責任者(?:を呼|と話|に(?:取り次|取次|つな))"
)
_PAYMENT_DIFFICULTY = re.compile(
    rf"{_PAYMENT}(?:額|負担)?"
    r"(?:(?:が|は|も|を続けるのが|を続けることが)(?:とても|かなり|少し|もう)?"
    r"(?:困難|難し|厳し|きつ|苦し|滞っ|間に合わな|できな|できません)"
    r"|を?(?:続けられな|できな|できません))"
)
_UNABLE_TO_PAY = re.compile(
    r"(?:払え(?:な|ず|ません|ていな|ていません|そうに(?:な|ありませ))|払う余裕がな"
    r"|(?:お金|資金|残高)が足りな|(?:家計|資金繰り)(?:が|は)(?:苦し|厳し|きつ))"
)
_DELAY = r"(?:延滞|滞納)"
_NEAR = r"[^。！？!?\n]{0,12}"
_DELINQUENCY = re.compile(
    rf"{_TOPIC}{_NEAR}{_DELAY}|{_DELAY}{_NEAR}{_TOPIC}|{_PAYMENT}が遅れ"
    rf"|(?:^|[。！？!?\n])\s*(?:もう|すでに)?{_DELAY}(?:し|が|で|について)"
)
_ASK_FOR_HELP = re.compile(r"相談|商談|取[り]?次|つな[ぎぐ]|どう(?:すれば|したら|しよう)")
_TERMS = r"返済(?:の)?(?:条件|計画|期間)(?:の|を)?(?:変更|見直し?)"
_TERMS_CHANGE = re.compile(
    rf"{_TERMS}(?:し)?(?:たい|たく|てもら)"
    rf"|(?:{_TERMS}|返済(?:の)?猶予)[^。！？!?\n]{{0,24}}(?:相談|商談|お願い|できないか)"
    rf"|{_PAYMENT}(?:を|は)?(?:少し|もう少し|しばらく)?待ってもら"
)


def needs_repayment_support(question: str) -> bool:
    """专门处理个人还款商谈，保留只问手续或只查状态的原路径。"""
    normalized = unicodedata.normalize("NFKC", question)
    if _EXPLICIT_COMPLAINT.search(normalized):
        return False
    # 去掉提前还款操作用语，避免把其中的「返済できない」当成偿还困难。
    repayment = _PREPAYMENT.sub("繰上手続", normalized)
    return bool(
        _PAYMENT_DIFFICULTY.search(repayment)
        or _TERMS_CHANGE.search(repayment)
        or (_DELINQUENCY.search(repayment) and _ASK_FOR_HELP.search(repayment))
        or any(
            _PAYMENT_TOPIC.search(sentence) and _UNABLE_TO_PAY.search(sentence)
            for sentence in _SENTENCE_BOUNDARY.split(repayment)
        )
    )
