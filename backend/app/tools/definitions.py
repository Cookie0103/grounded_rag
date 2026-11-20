"""只读工具注册表，输出模型同时定义字段白名单。"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

type ToolName = Literal[
    "query_loan_contracts",
    "query_repayment_schedule",
    "query_delinquency",
    "query_rate_terms",
    "query_benefits",
]

MAX_DETAIL_ROWS = 5


class ToolArguments(BaseModel):
    """客户级查询只使用可信的工具上下文。"""

    model_config = ConfigDict(extra="forbid", strict=True)


class ContractArguments(ToolArguments):
    contract_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
        Field(description="対象の契約番号"),
    ]


class RepaymentScheduleArguments(ContractArguments):
    start_period: Annotated[int | None, Field(ge=1, description="照会を開始する返済回（含む）")] = (
        None
    )
    end_period: Annotated[int | None, Field(ge=1, description="照会を終了する返済回（含む）")] = (
        None
    )

    @model_validator(mode="after")
    def validate_period_order(self) -> Self:
        """期数区间须按升序提交。"""
        if (
            self.start_period is not None
            and self.end_period is not None
            and self.start_period > self.end_period
        ):
            raise ValueError("起始期数不能大于结束期数")
        return self


class _AllowlistedModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LoanContract(_AllowlistedModel):
    contract_id: str
    product: str
    principal_yen: int
    disbursed_on: date
    status: str


class LoanContractsData(_AllowlistedModel):
    contracts: list[LoanContract]


class RepaymentInstallment(_AllowlistedModel):
    period: int
    due_date: date
    amount_yen: int
    principal_yen: int
    interest_yen: int


class RepaymentScheduleData(_AllowlistedModel):
    next_payment_date: date | None
    next_payment_yen: int | None
    outstanding_principal_yen: int
    remaining_installments: int
    schedule: list[RepaymentInstallment]


class DelinquencyData(_AllowlistedModel):
    days_overdue: int
    amount_yen: int
    late_fee_yen: int


class RateTermsData(_AllowlistedModel):
    annual_rate_percent: float
    rate_type: str
    fixed_until: date | None
    insurance_type: str
    insurance_increment_percent: float


class Benefit(_AllowlistedModel):
    name: str
    status: str


class BenefitsData(_AllowlistedModel):
    benefits: list[Benefit]


type ToolData = (
    LoanContractsData | RepaymentScheduleData | DelinquencyData | RateTermsData | BenefitsData
)


@dataclass(frozen=True)
class ToolDefinition:
    name: ToolName
    description: str
    path: str
    arguments_model: type[ToolArguments]
    data_model: type[ToolData]
    list_field: str | None = None
    list_limit: int = MAX_DETAIL_ROWS

    @property
    def parameters(self) -> dict[str, object]:
        """生成意图规划可用的 JSON Schema。"""
        return self.arguments_model.model_json_schema()


TOOL_DEFINITIONS: dict[ToolName, ToolDefinition] = {
    definition.name: definition
    for definition in (
        ToolDefinition(
            "query_loan_contracts",
            "現在のお客さまの住宅ローン契約を照会します。",
            "/loan-contracts",
            ToolArguments,
            LoanContractsData,
            "contracts",
        ),
        ToolDefinition(
            "query_repayment_schedule",
            "契約の次回返済額・返済日、残元金、残り回数と返済予定を照会します。返済回の範囲を指定できます。",
            "/repayment-schedule",
            RepaymentScheduleArguments,
            RepaymentScheduleData,
            "schedule",
        ),
        ToolDefinition(
            "query_delinquency",
            "現在のお客さまの延滞日数、延滞額、遅延損害金を照会します。",
            "/delinquency",
            ToolArguments,
            DelinquencyData,
        ),
        ToolDefinition(
            "query_rate_terms",
            "契約の適用金利、金利タイプ、固定金利期間の終了日、団信の条件を照会します。",
            "/rate-terms",
            ContractArguments,
            RateTermsData,
        ),
        ToolDefinition(
            "query_benefits",
            "現在のお客さまに適用される優遇やキャンペーンの状況を照会します。",
            "/benefits",
            ToolArguments,
            BenefitsData,
            "benefits",
        ),
    )
}
