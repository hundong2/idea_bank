from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .errors import ValidationError


class IncomeProfile(StrEnum):
    EMPLOYEE = "employee"
    FREELANCER = "freelancer"
    MIXED = "mixed"


class ExpenseMethod(StrEnum):
    ACTUAL = "actual"
    SIMPLE_RATE = "simple_rate"
    FINALIZED_INCOME = "finalized_income"


def _require_non_negative(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{name} must be a non-negative integer amount in KRW")


@dataclass(frozen=True, slots=True)
class WageIncome:
    gross_pay: int
    withheld_income_tax: int = 0
    withheld_local_income_tax: int = 0

    def __post_init__(self) -> None:
        for name in ("gross_pay", "withheld_income_tax", "withheld_local_income_tax"):
            _require_non_negative(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class FreelanceIncome:
    gross_receipts: int
    withheld_income_tax: int = 0
    withheld_local_income_tax: int = 0
    expense_method: ExpenseMethod = ExpenseMethod.FINALIZED_INCOME
    actual_expenses: int | None = None
    simple_expense_rate_bps: int | None = None
    simple_rate_eligibility_confirmed: bool = False
    finalized_business_income: int | None = None
    industry_code: str | None = None

    def __post_init__(self) -> None:
        for name in ("gross_receipts", "withheld_income_tax", "withheld_local_income_tax"):
            _require_non_negative(name, getattr(self, name))
        if self.expense_method == ExpenseMethod.ACTUAL:
            if self.actual_expenses is None:
                raise ValidationError("actual_expenses is required for actual expense method")
            _require_non_negative("actual_expenses", self.actual_expenses)
        elif self.expense_method == ExpenseMethod.SIMPLE_RATE:
            if not self.simple_rate_eligibility_confirmed:
                raise ValidationError("simple expense rate eligibility must be explicitly confirmed")
            if self.simple_expense_rate_bps is None or not 0 <= self.simple_expense_rate_bps <= 10_000:
                raise ValidationError("simple_expense_rate_bps must be between 0 and 10000")
            if not self.industry_code:
                raise ValidationError("industry_code is required for simple expense rate method")
        elif self.expense_method == ExpenseMethod.FINALIZED_INCOME:
            if self.finalized_business_income is None:
                raise ValidationError("finalized_business_income is required")
            _require_non_negative("finalized_business_income", self.finalized_business_income)


@dataclass(frozen=True, slots=True)
class TaxCase:
    tax_year: int
    wage: WageIncome | None = None
    freelance: FreelanceIncome | None = None
    income_deductions: int = 0
    tax_credits: int = 0
    additional_income_tax: int = 0
    prepayments_income_tax: int = 0
    resident: bool = True
    has_other_income: bool = False
    has_foreign_tax_or_income: bool = False
    has_prior_loss_carryforward: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.wage is None and self.freelance is None:
            raise ValidationError("at least one supported income source is required")
        for name in ("income_deductions", "tax_credits", "additional_income_tax", "prepayments_income_tax"):
            _require_non_negative(name, getattr(self, name))

    @property
    def profile(self) -> IncomeProfile:
        if self.wage and self.freelance:
            return IncomeProfile.MIXED
        return IncomeProfile.EMPLOYEE if self.wage else IncomeProfile.FREELANCER


@dataclass(frozen=True, slots=True)
class CalculationResult:
    tax_year: int
    ruleset_version: str
    profile: IncomeProfile
    wage_income_deduction: int
    wage_income_amount: int
    business_income_amount: int
    aggregate_income_amount: int
    income_deductions_applied: int
    tax_base: int
    calculated_income_tax: int
    tax_credits_applied: int
    additional_income_tax: int
    determined_income_tax: int
    prepaid_income_tax: int
    balance_due: int
    withheld_local_income_tax: int
    warnings: tuple[str, ...]
