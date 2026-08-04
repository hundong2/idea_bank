from __future__ import annotations

from .errors import UnsupportedCase
from .models import CalculationResult, ExpenseMethod, FreelanceIncome, TaxCase
from .rules import Ruleset, load_ruleset


def _assert_supported(case: TaxCase) -> None:
    reasons: list[str] = []
    if not case.resident:
        reasons.append("non-resident")
    if case.has_other_income:
        reasons.append("income type outside wage/freelance scope")
    if case.has_foreign_tax_or_income:
        reasons.append("foreign income or foreign tax credit")
    if case.has_prior_loss_carryforward:
        reasons.append("loss carryforward")
    if reasons:
        raise UnsupportedCase("manual review required: " + ", ".join(reasons))


def _wage_deduction(gross_pay: int, rules: Ruleset) -> int:
    for bracket in rules.wage_deduction_brackets:
        if bracket.upper is None or gross_pay <= bracket.upper:
            deduction = bracket.base + ((gross_pay - bracket.excess_over) * bracket.excess_rate_bps // 10_000)
            return min(gross_pay, rules.wage_deduction_cap, deduction)
    raise AssertionError("ruleset must end with an open wage bracket")


def _business_income(item: FreelanceIncome | None) -> int:
    if item is None:
        return 0
    if item.expense_method == ExpenseMethod.ACTUAL:
        income = item.gross_receipts - int(item.actual_expenses or 0)
        if income < 0:
            raise UnsupportedCase("manual review required: business loss")
        return income
    if item.expense_method == ExpenseMethod.SIMPLE_RATE:
        expense = item.gross_receipts * int(item.simple_expense_rate_bps or 0) // 10_000
        return max(0, item.gross_receipts - expense)
    return int(item.finalized_business_income or 0)


def _progressive_tax(tax_base: int, rules: Ruleset) -> int:
    for bracket in rules.income_tax_brackets:
        if bracket.upper is None or tax_base <= bracket.upper:
            return max(0, tax_base * bracket.rate_bps // 10_000 - bracket.quick_deduction)
    raise AssertionError("ruleset must end with an open tax bracket")


def calculate(case: TaxCase) -> CalculationResult:
    """Calculate the bounded national income-tax result in integer KRW.

    The caller remains responsible for tax eligibility facts and deductions/credits.
    Unsupported complexity fails closed instead of silently estimating.
    """
    _assert_supported(case)
    rules = load_ruleset(case.tax_year)
    gross_pay = case.wage.gross_pay if case.wage else 0
    wage_deduction = _wage_deduction(gross_pay, rules) if case.wage else 0
    wage_income = gross_pay - wage_deduction
    business_income = _business_income(case.freelance)
    aggregate = wage_income + business_income
    deductions_applied = min(aggregate, case.income_deductions)
    tax_base = aggregate - deductions_applied
    calculated = _progressive_tax(tax_base, rules)
    credits_applied = min(calculated, case.tax_credits)
    determined = calculated - credits_applied + case.additional_income_tax
    source_withheld = (case.wage.withheld_income_tax if case.wage else 0) + (
        case.freelance.withheld_income_tax if case.freelance else 0
    )
    prepaid = source_withheld + case.prepayments_income_tax
    local_withheld = (case.wage.withheld_local_income_tax if case.wage else 0) + (
        case.freelance.withheld_local_income_tax if case.freelance else 0
    )
    warnings = (
        "Individual local income tax is not calculated; local withholding is reported separately.",
        "Deductions, credits, expense-method eligibility, and filing-form selection require upstream validation.",
    )
    return CalculationResult(
        tax_year=case.tax_year,
        ruleset_version=rules.version,
        profile=case.profile,
        wage_income_deduction=wage_deduction,
        wage_income_amount=wage_income,
        business_income_amount=business_income,
        aggregate_income_amount=aggregate,
        income_deductions_applied=deductions_applied,
        tax_base=tax_base,
        calculated_income_tax=calculated,
        tax_credits_applied=credits_applied,
        additional_income_tax=case.additional_income_tax,
        determined_income_tax=determined,
        prepaid_income_tax=prepaid,
        balance_due=determined - prepaid,
        withheld_local_income_tax=local_withheld,
        warnings=warnings,
    )
