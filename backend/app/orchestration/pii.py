"""入口问题中的个人识别信息脱敏。"""

import re
import string

_ASCII_PRINTABLE = string.digits + string.ascii_letters + string.punctuation
# 单字符映射使匹配区间对应原文，不改变无须脱敏的全角文本。
_WIDTH = str.maketrans(
    "".join(chr(ord(character) + 0xFEE0) for character in _ASCII_PRINTABLE) + "　‐‑–−",
    _ASCII_PRINTABLE + " ----",
)
_LABEL_JOIN = r"[ \t]*(?:は|が|[:=]|は[:=])?[ \t]*"
_SEPARATOR = r"[ \t-]"
_DIGIT_START = r"(?<![A-Za-z0-9_+-])(?<![0-9][.,])"
_DIGIT_END = r"(?![A-Za-z0-9_]|[.,][0-9])"
_CONTRACT_LABEL = re.compile(rf"契約(?:番号|No\.?|ID|識別子){_LABEL_JOIN}$", re.IGNORECASE)
_QUANTITY_SUFFIX = re.compile(
    r"[ \t]*(?:[十百千万億]*円|%|パーセント|営業日|日|か月|カ月|ヶ?月|年|回|件|期|名|人)"
)

_EMAIL = re.compile(
    r"(?P<value>[A-Z0-9.!#$%&'*+/=?^_\x60{|}~-]+@"
    r"(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?\.)+[A-Z]{2,})",
    re.IGNORECASE,
)
_LABELED_NUMBERS = (
    (
        re.compile(
            rf"(?:口座番号|口座No\.?|口座ナンバー|(?:普通|当座)口座)"
            rf"(?:[ \t]*\((?:普通|当座|普通預金|当座預金)\))?{_LABEL_JOIN}"
            rf"(?P<value>(?:[0-9]{{3}}{_SEPARATOR}+)?[0-9]{{7}}){_DIGIT_END}",
            re.IGNORECASE,
        ),
        "［口座番号］",
    ),
    (
        re.compile(
            rf"(?:カード番号|カードNo\.?|カードナンバー|カード){_LABEL_JOIN}"
            rf"(?P<value>[0-9](?:{_SEPARATOR}?[0-9]){{12,18}}){_DIGIT_END}",
            re.IGNORECASE,
        ),
        "［カード番号］",
    ),
    (
        re.compile(
            rf"(?:マイナンバー|個人番号){_LABEL_JOIN}"
            rf"(?P<value>[0-9](?:{_SEPARATOR}?[0-9]){{11}}){_DIGIT_END}"
        ),
        "［マイナンバー］",
    ),
)

_PHONE_PREFIX = rf"(?:\+81{_SEPARATOR}*(?:\(0\){_SEPARATOR}*)?|0)"
_PHONE = re.compile(
    rf"{_DIGIT_START}(?P<value>{_PHONE_PREFIX}(?:"
    rf"[5789]0{_SEPARATOR}?[0-9]{{4}}{_SEPARATOR}?[0-9]{{4}}|"
    rf"120{_SEPARATOR}?[0-9]{{3}}{_SEPARATOR}?[0-9]{{3}}|"
    rf"800{_SEPARATOR}?[0-9]{{3}}{_SEPARATOR}?[0-9]{{4}}|"
    rf"(?=(?:{_SEPARATOR}?[0-9]){{9}}{_DIGIT_END})"
    rf"[1-9][0-9]{{0,3}}{_SEPARATOR}?[0-9]{{1,4}}{_SEPARATOR}?[0-9]{{4}})"
    rf"){_DIGIT_END}"
)
_CARD = re.compile(
    rf"{_DIGIT_START}(?P<value>"
    rf"[0-9]{{4}}(?:{_SEPARATOR}[0-9]{{4}}){{3}}|"
    rf"[0-9]{{4}}{_SEPARATOR}[0-9]{{6}}{_SEPARATOR}[0-9]{{5}}|"
    rf"[0-9]{{16}}){_DIGIT_END}"
)
_MY_NUMBER = re.compile(
    rf"{_DIGIT_START}(?P<value>[0-9]{{4}}(?:{_SEPARATOR}?[0-9]{{4}}){{2}}){_DIGIT_END}"
)


def _mask(question: str, pattern: re.Pattern[str], placeholder: str, *, unlabelled: bool) -> str:
    normalized = question.translate(_WIDTH)
    spans = []
    for match in pattern.finditer(normalized):
        start, end = match.span("value")
        if unlabelled and (
            _CONTRACT_LABEL.search(normalized, 0, start) or _QUANTITY_SUFFIX.match(normalized, end)
        ):
            continue
        spans.append((start, end))
    for start, end in reversed(spans):
        question = question[:start] + placeholder + question[end:]
    return question


def redact_pii(question: str) -> str:
    """替换问题中的个人识别信息。"""
    question = _mask(question, _EMAIL, "［メールアドレス］", unlabelled=False)
    for pattern, placeholder in _LABELED_NUMBERS:
        question = _mask(question, pattern, placeholder, unlabelled=False)
    for pattern, placeholder in (
        (_PHONE, "［電話番号］"),
        (_CARD, "［カード番号］"),
        (_MY_NUMBER, "［マイナンバー］"),
    ):
        question = _mask(question, pattern, placeholder, unlabelled=True)
    return question
