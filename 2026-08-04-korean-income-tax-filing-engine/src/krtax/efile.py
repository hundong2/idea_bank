from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .errors import EFileSpecUnavailable, ValidationError
from .models import CalculationResult


@dataclass(frozen=True, slots=True)
class FixedWidthField:
    name: str
    width: int
    kind: str = "text"  # text | number
    required: bool = True
    pad: str | None = None


@dataclass(frozen=True, slots=True)
class FixedWidthSpec:
    tax_year: int
    spec_id: str
    encoding: str
    line_ending: str
    fields: tuple[FixedWidthField, ...]
    reviewed: bool = False


def build_canonical_payload(result: CalculationResult, *, taxpayer_ref: str) -> dict[str, Any]:
    """Create a non-PII-keyed payload between calculation and filing adapters."""
    if not taxpayer_ref or len(taxpayer_ref) > 64:
        raise ValidationError("taxpayer_ref must be 1..64 characters")
    payload = asdict(result)
    payload["profile"] = result.profile.value
    payload["taxpayer_ref"] = taxpayer_ref
    return payload


def _render_field(field: FixedWidthField, payload: Mapping[str, Any]) -> str:
    value = payload.get(field.name)
    if value is None:
        if field.required:
            raise ValidationError(f"missing e-file field: {field.name}")
        value = ""
    raw = str(value)
    if len(raw) > field.width:
        raise ValidationError(f"e-file field {field.name} exceeds width {field.width}")
    if field.kind == "number":
        if raw.startswith("-") or not raw.isdigit():
            raise ValidationError(f"e-file field {field.name} must be an unsigned number")
        return raw.rjust(field.width, field.pad or "0")
    if field.kind != "text":
        raise ValidationError(f"unknown e-file field kind: {field.kind}")
    return raw.ljust(field.width, field.pad or " ")


def render_fixed_width(
    records: Sequence[Mapping[str, Any]],
    spec: FixedWidthSpec | None,
) -> bytes:
    """Render only with an explicitly reviewed, year-specific external schema."""
    if spec is None or not spec.reviewed:
        raise EFileSpecUnavailable("a reviewed official e-file specification must be registered")
    for record in records:
        if record.get("tax_year") != spec.tax_year:
            raise ValidationError("record tax_year does not match e-file specification")
    lines = ["".join(_render_field(field, record) for field in spec.fields) for record in records]
    return (spec.line_ending.join(lines) + spec.line_ending).encode(spec.encoding)
