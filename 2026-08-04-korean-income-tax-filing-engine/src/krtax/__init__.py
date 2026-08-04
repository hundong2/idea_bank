"""Public interface for the tax calculation kernel."""

from .calculator import calculate
from .efile import FixedWidthField, FixedWidthSpec, build_canonical_payload, render_fixed_width
from .errors import EFileSpecUnavailable, TaxDomainError, UnsupportedCase, ValidationError
from .models import (
    CalculationResult,
    ExpenseMethod,
    FreelanceIncome,
    IncomeProfile,
    TaxCase,
    WageIncome,
)

__all__ = [
    "CalculationResult",
    "EFileSpecUnavailable",
    "ExpenseMethod",
    "FixedWidthField",
    "FixedWidthSpec",
    "FreelanceIncome",
    "IncomeProfile",
    "TaxCase",
    "TaxDomainError",
    "UnsupportedCase",
    "ValidationError",
    "WageIncome",
    "build_canonical_payload",
    "calculate",
    "render_fixed_width",
]
