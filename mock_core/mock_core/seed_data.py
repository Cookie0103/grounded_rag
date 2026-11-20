"""生成没有真实客户资料及金融条款的固定测试数据。"""

import calendar
import hashlib
import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from random import Random
from typing import NamedTuple

SEED = 33
AS_OF = date(2026, 11, 18)
PRODUCTS = ("変動セレクト住宅ローン", "固定セレクト住宅ローン", "住宅ローン")
INSURANCE = (
    ("団体信用生命保険", Decimal("0.000")),
    ("がん団信50", Decimal("0.075")),
    ("がん団信100", Decimal("0.125")),
    ("3大疾病団信", Decimal("0.225")),
    ("ワイド団信", Decimal("0.375")),
)

# 列与主键顺序同时规定灌库和指纹格式。
TABLES = {
    "agents": ("agent_id",),
    "customers": ("customer_id", "account_number", "address", "phone_number"),
    "agent_customer": ("agent_id", "customer_id"),
    "loan_contracts": (
        "contract_id",
        "customer_id",
        "product",
        "principal_yen",
        "disbursed_on",
        "status",
        "is_pair_loan",
    ),
    "repayment_schedule": (
        "contract_id",
        "period",
        "due_date",
        "amount_yen",
        "principal_yen",
        "interest_yen",
    ),
    "repayment_history": ("contract_id", "period", "paid_on"),
    "delinquencies": ("contract_id", "customer_id", "days_overdue", "amount_yen", "late_fee_yen"),
    "rate_terms": (
        "contract_id",
        "annual_rate_percent",
        "rate_type",
        "fixed_until",
        "insurance_type",
        "insurance_increment_percent",
    ),
    "benefits": ("customer_id", "name", "status"),
}
COMPOSITE_KEYS = {"agent_customer", "repayment_schedule", "repayment_history", "benefits"}

type SeedValue = str | int | date | Decimal | None
type SeedRow = tuple[SeedValue, ...]
type SeedRows = dict[str, list[SeedRow]]


class Scenario(NamedTuple):
    disbursed_on: date
    installments: int
    product: str
    rate_type: str
    fixed_until: date | None = None


class Installment(NamedTuple):
    contract_id: str
    period: int
    due_date: date
    amount_yen: int
    principal_yen: int
    interest_yen: int


def _add_months(day: date, months: int) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def _round_yen(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _installments(
    contract_id: str, principal_yen: int, annual_rate_percent: Decimal, scenario: Scenario
) -> list[Installment]:
    monthly_rate = annual_rate_percent / 1200
    discount = (1 + monthly_rate) ** -scenario.installments
    payment = _round_yen(principal_yen * monthly_rate / (1 - discount))
    outstanding = principal_yen
    schedule = []
    for period in range(1, scenario.installments + 1):
        interest = _round_yen(outstanding * monthly_rate)
        principal = outstanding if period == scenario.installments else payment - interest
        outstanding -= principal
        due_date = _add_months(scenario.disbursed_on, period)
        schedule.append(
            Installment(contract_id, period, due_date, principal + interest, principal, interest)
        )
    return schedule


def _scenario(number: int, rng: Random) -> Scenario:
    examples = {
        1: Scenario(date(2024, 1, 15), 420, PRODUCTS[0], "変動金利"),
        2: Scenario(date(2024, 3, 15), 360, PRODUCTS[0], "変動金利"),
        3: Scenario(date(2015, 8, 15), 120, PRODUCTS[2], "変動金利"),
        4: Scenario(date(2024, 5, 15), 360, PRODUCTS[1], "固定金利", date(2027, 5, 15)),
        5: Scenario(date(2023, 7, 15), 360, PRODUCTS[2], "部分固定金利特約", date(2033, 7, 15)),
        301: Scenario(date(2024, 1, 15), 360, PRODUCTS[1], "固定金利", date(2034, 1, 15)),
    }
    if number in examples:
        return examples[number]
    disbursed_on = _add_months(date(2018, 1, 15), rng.randrange(105))
    installments = rng.choice((120, 180, 240, 300, 360))
    product = rng.choice(PRODUCTS)
    if product == PRODUCTS[1]:
        return Scenario(
            disbursed_on, installments, product, "固定金利", _add_months(disbursed_on, 120)
        )
    return Scenario(disbursed_on, installments, product, "変動金利")


def _add_contract(rows: SeedRows, number: int, rng: Random) -> None:
    contract_id = f"L{number:04d}"
    is_pair_loan = number in {1, 301}
    customer_id = "C0001" if is_pair_loan else f"C{number:04d}"
    scenario = _scenario(number, rng)
    principal = rng.randrange(15_000_000, 55_000_001, 10_000)
    insurance_type, increment = rng.choice(INSURANCE)
    annual_rate = Decimal(rng.randint(725, 2475)).scaleb(-3) + increment
    schedule = _installments(contract_id, principal, annual_rate, scenario)
    paid = [installment for installment in schedule if installment.due_date < AS_OF]
    status = "完済" if len(paid) == len(schedule) else "返済中"
    if number == 2:
        overdue = paid[-2:]
        paid = paid[:-2]
        amount = sum(installment.amount_yen for installment in overdue)
        days = (AS_OF - overdue[0].due_date).days
        # 模拟迟延损害金只用于走通查询路径。
        rows["delinquencies"].append(
            (contract_id, customer_id, days, amount, amount * days // 3200)
        )
        status = "延滞中"
    rows["loan_contracts"].append(
        (
            contract_id,
            customer_id,
            scenario.product,
            principal,
            scenario.disbursed_on,
            status,
            int(is_pair_loan),
        )
    )
    rows["repayment_schedule"].extend(schedule)
    rows["repayment_history"].extend((contract_id, row.period, row.due_date) for row in paid)
    rows["rate_terms"].append(
        (
            contract_id,
            annual_rate,
            scenario.rate_type,
            scenario.fixed_until,
            insurance_type,
            increment,
        )
    )


def build_seed(seed: int = SEED) -> SeedRows:
    """生成按表和主键排序的合成记录。"""
    rng = Random(seed)
    rows: SeedRows = {table: [] for table in TABLES}
    rows["agents"].extend((f"A{number:03d}",) for number in range(1, 21))
    for number in range(1, 301):
        customer_id = f"C{number:04d}"
        rows["customers"].append(
            (
                customer_id,
                f"SYNTHETIC-{number:07d}",
                f"架空県合成市試験町{number}",
                f"000-0000-{number:04d}",
            )
        )
        rows["agent_customer"].append((f"A{(number - 1) % 20 + 1:03d}", customer_id))
        rows["benefits"].extend(
            [
                (customer_id, "Club S（合成）", rng.choice(("適用中", "対象外"))),
                (customer_id, "住宅ローン契約特典（合成）", rng.choice(("適用中", "対象外"))),
            ]
        )
        _add_contract(rows, number, rng)
    rows["agent_customer"].append(("A020", "C0001"))
    _add_contract(rows, 301, rng)
    for table in TABLES:
        key_width = 2 if table in COMPOSITE_KEYS else 1
        rows[table].sort(key=lambda row: row[:key_width])
    return rows


def fingerprint(rows: SeedRows) -> str:
    """计算所有有序合成表的 SHA-256 指纹。"""
    digest = hashlib.sha256()
    for table in TABLES:
        digest.update(f"{table}\n".encode())
        for row in rows[table]:
            digest.update(
                json.dumps(row, ensure_ascii=False, default=str, separators=(",", ":")).encode()
            )
            digest.update(b"\n")
    return digest.hexdigest()


def summarize(rows: SeedRows) -> dict[str, int]:
    """统计验收要求的合成场景。"""
    expiry_limit = AS_OF + timedelta(days=365)
    return {
        "customers": len(rows["customers"]),
        "agents": len(rows["agents"]),
        "max_installments": max(int(row[1]) for row in rows["repayment_schedule"]),
        "pair_loan_customers": len({row[1] for row in rows["loan_contracts"] if row[6]}),
        "delinquent_contracts": len(rows["delinquencies"]),
        "paid_contracts": sum(row[5] == "完済" for row in rows["loan_contracts"]),
        "fixed_expiring_within_year": sum(
            row[2] == "固定金利" and isinstance(row[3], date) and AS_OF < row[3] <= expiry_limit
            for row in rows["rate_terms"]
        ),
        "partial_fixed_contracts": sum(row[2] == "部分固定金利特約" for row in rows["rate_terms"]),
    }
