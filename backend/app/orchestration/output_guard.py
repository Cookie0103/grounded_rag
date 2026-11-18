"""回答的确定性出口校验。"""

import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Literal

from app.orchestration.context import CITATION
from app.orchestration.models import Citation

type OutputReason = Literal[
    "prohibited_expression", "unsupported_number", "invalid_citation", "missing_citation"
]
type _Number = tuple[str, Decimal | str]

_GAP = r"[^。！？!?\n]{0,24}"
_CERTAINTY = r"(?:必ず|絶対に|確実に)"
_PROMISE = r"(?:保証|お約束|確約)(?:します|いたします|できます)"
_PROHIBITED = re.compile(
    r"間違いありません|間違いないです|絶対に大丈夫|確実に大丈夫"
    rf"|(?:審査|与信){_GAP}(?:通ります|通過します|合格します|可決されます"
    rf"|承認(?:されます|いたします|です|になります|となります)|通ることを{_PROMISE})"
    rf"|{_CERTAINTY}{_GAP}(?:融資を受けられます|融資できます|借りられます|対象です)"
    rf"|(?:金利|利率){_GAP}(?:{_PROMISE}|(?:で|は|が)確定(?:です|します|いたします)"
    rf"|{_CERTAINTY}{_GAP}(?:適用されます|になります|に固定されます))"
)
_QUALIFIED = re.compile(
    r"[」』]?(?:と(?:は)?(?:限りません|断定できません|は言えません|保証できません|"
    r"お約束できません)|かどうか)"
)

_UNSIGNED = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_SIGNED = rf"[+-]?{_UNSIGNED}"
_MONEY_FACTORS = {
    "億": 100_000_000,
    "千万": 10_000_000,
    "百万": 1_000_000,
    "十万": 100_000,
    "万": 10_000,
    "千": 1_000,
    "百": 100,
    "十": 10,
    "": 1,
}
_MONEY_SUFFIXES = "|".join(unit for unit in _MONEY_FACTORS if unit)
_MONEY_ITEM = re.compile(rf"({_UNSIGNED})(?:[ \t]*({_MONEY_SUFFIXES}))?")
_KANJI_DIGITS = {character: number for number, character in enumerate("〇一二三四五六七八九")}
_KANJI_DIGITS["零"] = 0
_KANJI_SMALL_PLACES = {place: _MONEY_FACTORS[place] for place in ("十", "百", "千")}
_KANJI_LARGE_PLACES = {place: _MONEY_FACTORS[place] for place in ("万", "億")}
_KANJI = "".join((*_KANJI_DIGITS, *_KANJI_SMALL_PLACES, *_KANJI_LARGE_PLACES))
_KANJI_MONEY = re.compile(rf"([{_KANJI}]+)[ \t]*円")
_MONEY = (
    rf"(?:[+-]?(?:{_UNSIGNED}[ \t]*億(?:[ \t]*{_UNSIGNED}[ \t]*万)?"
    rf"(?:[ \t]*{_UNSIGNED})?|{_UNSIGNED}[ \t]*(?:{_MONEY_SUFFIXES})(?:[ \t]*{_UNSIGNED})?"
    rf"|{_UNSIGNED})|[{_KANJI}]+)[ \t]*円"
)
_YEN_IN_MAN = Decimal(_MONEY_FACTORS["万"]).normalize()
_YEN_FACTOR_DIGITS = len(str(max(_MONEY_FACTORS.values())))
_FULL_DATE = (
    r"(?:[0-9]{4}[ \t]*年[ \t]*[0-9]{1,2}[ \t]*月[ \t]*[0-9]{1,2}[ \t]*日"
    r"|[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})"
)
_YEAR_MONTH = r"[0-9]{4}[ \t]*年[ \t]*[0-9]{1,2}[ \t]*月"
_MONTH_DAY = r"[0-9]{1,2}[ \t]*月[ \t]*[0-9]{1,2}[ \t]*日"
_DATE_PART = re.compile(r"[0-9]+")
_FULL_DATE_PARTS = 3
_UNITS = {
    "パーセント": "percent",
    "%": "percent",
    "営業日": "business_days",
    "日間": "days",
    "日": "days",
    "か月間": "months",
    "カ月間": "months",
    "箇月間": "months",
    "ヶ月間": "months",
    "か月": "months",
    "カ月": "months",
    "箇月": "months",
    "ヶ月": "months",
    "月間": "months",
    "月": "calendar_month",
    "年間": "years",
    "年": "years",
    "回": "installments",
    "契約": "records",
    "件": "records",
    "期": "installments",
    "名": "people",
    "人": "people",
    "": "bare",
}
_UNIT_SUFFIXES = "|".join(unit for unit in _UNITS if unit)
_TOKEN = re.compile(
    rf"(?<![0-9A-Za-z_+.-])(?<![0-9],)(?P<approx>約[ \t]*)?(?:"
    rf"(?P<yen>{_MONEY})|(?P<date>{_FULL_DATE}|{_YEAR_MONTH}|{_MONTH_DAY})"
    r"|(?:毎月|当月|翌月|前月|同月|今月|来月)[ \t]*(?P<day_of_month>[0-9]{1,2})[ \t]*日"
    rf"|(?:第[ \t]*(?P<period>{_UNSIGNED})[ \t]*(?:回|期)"
    rf"|(?P<period_end>{_UNSIGNED})[ \t]*(?:回目|期目))"
    rf"|(?P<amount>{_SIGNED})(?:[ \t]*(?P<unit>{_UNIT_SUFFIXES}))?)"
    r"(?![0-9A-Za-z_]|[.,][0-9])"
)
_CALENDAR_YEAR = re.compile(r"^[12][0-9]{3}$")
_APPROX_MAN = re.compile(rf"{_SIGNED}[ \t]*万円")
_ORDERED_LIST = re.compile(r"^[ \t]*[0-9]+[.)][ \t]+", re.MULTILINE)
_POLICY_HEADER = re.compile(r"^\[[0-9]+\] 資料：[^\n]*(?:\n|$)", re.MULTILINE)
_NONCANONICAL_CITATION = re.compile(r"［\s*\d+\s*］|【\s*\d+\s*】|\[\s*\d+(?:[,、-]\s*\d+)+\s*\]")
_NARROW_SPACES = str.maketrans({"−": "-", " ": " ", " ": " "})
_TOOL_NUMBER_FIELDS = {
    "amount_yen": "yen",
    "interest_yen": "yen",
    "late_fee_yen": "yen",
    "next_payment_yen": "yen",
    "outstanding_principal_yen": "yen",
    "principal_yen": "yen",
    "annual_rate_percent": "percent",
    "insurance_increment_percent": "percent",
    "days_overdue": "days",
    "remaining_installments": "installments",
    "period": "period",
}
_TOOL_DATE_FIELDS = frozenset({"disbursed_on", "due_date", "fixed_until", "next_payment_date"})
_TOOL_DATE = re.compile(_FULL_DATE)


@dataclass(frozen=True)
class OutputDecision:
    """稳定的校验结果与撤回原因。"""

    reasons: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """回答是否通过校验。"""
        return not self.reasons


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text.translate(_NARROW_SPACES))


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


def _kanji_yen_value(text: str) -> Decimal:
    total = group = digits = 0
    for character in text:
        if character in _KANJI_DIGITS:
            digits = digits * 10 + _KANJI_DIGITS[character]
        elif character in _KANJI_SMALL_PLACES:
            group += (digits or 1) * _KANJI_SMALL_PLACES[character]
            digits = 0
        else:
            total += (group + digits or 1) * _KANJI_LARGE_PLACES[character]
            group = digits = 0
    return Decimal(total + group + digits)


def _yen_value(text: str) -> Decimal:
    if kanji := _KANJI_MONEY.fullmatch(text):
        return _kanji_yen_value(kanji[1])
    items = _MONEY_ITEM.findall(text)
    with localcontext() as context:
        context.prec = max(context.prec, len(text) + _YEN_FACTOR_DIGITS)
        value = sum((_decimal(number) * _MONEY_FACTORS[unit] for number, unit in items), Decimal(0))
        return -value if text.startswith("-") else value


def _date_number(value: str) -> _Number:
    parts = [int(part) for part in _DATE_PART.findall(value)]
    if len(parts) == _FULL_DATE_PARTS:
        year, month, day = parts
        return "date", f"{year:04}-{month:02}-{day:02}"
    if "年" in value:
        year, month = parts
        return "year_month", f"{year:04}-{month:02}"
    month, day = parts
    return "month_day", f"{month:02}-{day:02}"


def _value(match: re.Match[str]) -> _Number:
    if yen := match["yen"]:
        return "yen", _yen_value(yen)
    if date := match["date"]:
        return _date_number(date)
    if day := match["day_of_month"]:
        return "calendar_day", _decimal(day)
    if period := match["period"] or match["period_end"]:
        return "period", _decimal(period)
    unit = match["unit"] or ""
    amount = match["amount"]
    kind = "calendar_year" if unit == "年" and _CALENDAR_YEAR.fullmatch(amount) else _UNITS[unit]
    return kind, _decimal(amount)


def _tokens(text: str) -> list[re.Match[str]]:
    without_citations = _NONCANONICAL_CITATION.sub(" ", CITATION.sub(" ", text))
    return list(_TOKEN.finditer(_ORDERED_LIST.sub("", _normalize(without_citations))))


def numeric_claims(text: str) -> set[_Number]:
    """抽取带单位的数值用于和评测金标精确比对。"""
    return {_value(token) for token in _tokens(text)}


def _tool_value(key: object, value: object) -> _Number | None:
    if not isinstance(key, str):
        return None
    if key in _TOOL_DATE_FIELDS and isinstance(value, str) and _TOOL_DATE.fullmatch(value):
        return _date_number(value)
    kind = _TOOL_NUMBER_FIELDS.get(key)
    if kind is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if kind != "percent" and not isinstance(value, int):
        return None
    number = Decimal(str(value))
    return (kind, number) if number.is_finite() else None


def _numeric_tool_fields(fields: Mapping[object, object]) -> set[_Number]:
    numbers: set[_Number] = set()
    for key, value in fields.items():
        if isinstance(value, Mapping):
            numbers.update(_numeric_tool_fields(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    numbers.update(_numeric_tool_fields(item))
        elif number := _tool_value(key, value):
            numbers.add(number)
    return numbers


def _tool_numbers(outputs: Sequence[Mapping[str, object]]) -> set[_Number]:
    numbers: set[_Number] = set()
    for output in outputs:
        data = output.get("data")
        if not isinstance(data, Mapping):
            continue
        numbers.update(_numeric_tool_fields(data))
        total = output.get("total")
        if isinstance(total, int) and not isinstance(total, bool):
            numbers.add(("records", Decimal(total)))
            if "schedule" in data:
                numbers.add(("installments", Decimal(total)))
    return numbers


def _date_projections(numbers: set[_Number]) -> set[_Number]:
    projected: set[_Number] = set()
    for kind, value in numbers:
        if not isinstance(value, str):
            continue
        if kind == "date":
            year, month, day = value.split("-")
            projected.update({("year_month", f"{year}-{month}"), ("month_day", f"{month}-{day}")})
        elif kind == "year_month":
            year, month = value.split("-")
        else:
            continue
        projected.update({("calendar_year", Decimal(year)), ("calendar_month", Decimal(month))})
    return projected


def _rounded_tool_yen(numbers: set[_Number]) -> set[_Number]:
    # 白名单仅允许把工具中的日元金额四舍五入到整万日元，并明确标注「約」。
    rounded: set[_Number] = set()
    for kind, value in numbers:
        if kind == "yen" and isinstance(value, Decimal):
            with localcontext() as context:
                context.prec = max(context.prec, value.adjusted() + 1)
                rounded.add(("yen", value.quantize(_YEN_IN_MAN, rounding=ROUND_HALF_UP)))
    return rounded


def _has_unsupported_number(
    answer: str, tools: Sequence[Mapping[str, object]], policy_texts: Sequence[str]
) -> bool:
    claims = _tokens(answer)
    if not claims:
        return False
    tool_numbers = _tool_numbers(tools)
    exact = set(tool_numbers)
    approximate: set[_Number] = set()
    for text in policy_texts:
        for token in _tokens(_POLICY_HEADER.sub("", text)):
            (approximate if token["approx"] else exact).add(_value(token))
    exact.update(_date_projections(exact))
    rounded_yen = _rounded_tool_yen(tool_numbers)
    for claim in claims:
        value = _value(claim)
        if value in exact:
            continue
        if claim["approx"] and (
            value in approximate
            or (_APPROX_MAN.fullmatch(claim["yen"] or "") and value in rounded_yen)
        ):
            continue
        return True
    return False


def _citation_reason(
    answer: str, allowed: Sequence[Citation], active: Collection[str], required: bool
) -> OutputReason | None:
    indices = {_normalize(index) for index in CITATION.findall(answer)}
    valid = {str(citation.index) for citation in allowed if citation.document_id in active}
    if not indices.issubset(valid) or _NONCANONICAL_CITATION.search(answer):
        return "invalid_citation"
    if required and not indices:
        return "missing_citation"
    return None


def validate_output(
    answer: str,
    *,
    tool_evidence: Sequence[Mapping[str, object]] = (),
    policy_texts: Sequence[str] = (),
    allowed_citations: Sequence[Citation] = (),
    active_document_ids: Collection[str] = (),
    require_citations: bool = False,
) -> OutputDecision:
    """检查禁用表达、数字证据与规程引用。"""
    reasons: list[OutputReason] = []
    normalized = _normalize(answer)
    if any(
        not _QUALIFIED.match(normalized, found.end()) for found in _PROHIBITED.finditer(normalized)
    ):
        reasons.append("prohibited_expression")
    if _has_unsupported_number(answer, tool_evidence, policy_texts):
        reasons.append("unsupported_number")
    reason = _citation_reason(answer, allowed_citations, active_document_ids, require_citations)
    if reason:
        reasons.append(reason)
    return OutputDecision(tuple(reasons))
