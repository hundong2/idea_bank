from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from .errors import UnsupportedCase, ValidationError


@dataclass(frozen=True, slots=True)
class Bracket:
    upper: int | None
    rate_bps: int
    quick_deduction: int


@dataclass(frozen=True, slots=True)
class WageDeductionBracket:
    upper: int | None
    base: int
    excess_over: int
    excess_rate_bps: int


@dataclass(frozen=True, slots=True)
class Ruleset:
    tax_year: int
    version: str
    income_tax_brackets: tuple[Bracket, ...]
    wage_deduction_brackets: tuple[WageDeductionBracket, ...]
    wage_deduction_cap: int


def load_ruleset(tax_year: int) -> Ruleset:
    resource = files("krtax").joinpath("rules", f"{tax_year}.json")
    if not resource.is_file():
        raise UnsupportedCase(f"no reviewed ruleset is available for tax year {tax_year}")
    data = json.loads(resource.read_text(encoding="utf-8"))
    if data["status"] != "reviewed_baseline":
        raise ValidationError("ruleset is not approved for calculation")
    return Ruleset(
        tax_year=data["tax_year"],
        version=data["version"],
        income_tax_brackets=tuple(Bracket(**item) for item in data["income_tax_brackets"]),
        wage_deduction_brackets=tuple(
            WageDeductionBracket(**item) for item in data["wage_deduction_brackets"]
        ),
        wage_deduction_cap=data["wage_deduction_cap"],
    )
