from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .rules import Ruleset, load_ruleset


ALLOWED_OFFICIAL_HOST_SUFFIXES = ("law.go.kr", "nts.go.kr", "hometax.go.kr")
USER_AGENT = "krtax-maintenance-monitor/0.1 (+offline-by-default)"


class MaintenanceError(Exception):
    """A maintenance check could not produce trustworthy evidence."""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    source_id: str
    authority: str
    category: str
    url: str
    required_markers: tuple[str, ...]
    review_cadence_days: int


@dataclass(frozen=True, slots=True)
class SourceFingerprint:
    source_id: str
    requested_url: str
    final_url: str
    fetched_at: str
    normalized_sha256: str
    etag: str | None
    last_modified: str | None
    normalized_length: int


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_allowed_official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_OFFICIAL_HOST_SUFFIXES
    )


def normalize_html(content: bytes, charset: str = "utf-8") -> str:
    text = content.decode(charset, errors="replace")
    parser = _VisibleTextParser()
    parser.feed(text)
    visible = unicodedata.normalize("NFKC", " ".join(parser.parts))
    return re.sub(r"\s+", " ", visible).strip()


def load_source_registry(path: Path) -> tuple[SourceDefinition, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise MaintenanceError("unsupported source registry schema_version")
    seen: set[str] = set()
    result: list[SourceDefinition] = []
    for raw in data.get("sources", []):
        source_id = raw["source_id"]
        if source_id in seen:
            raise MaintenanceError(f"duplicate source_id: {source_id}")
        if not _is_allowed_official_url(raw["url"]):
            raise MaintenanceError(f"source URL is not an allowed official HTTPS host: {source_id}")
        markers = tuple(raw.get("required_markers", []))
        if not markers:
            raise MaintenanceError(f"at least one required marker is needed: {source_id}")
        cadence = raw.get("review_cadence_days")
        if not isinstance(cadence, int) or not 1 <= cadence <= 366:
            raise MaintenanceError(f"invalid review cadence: {source_id}")
        result.append(
            SourceDefinition(
                source_id=source_id,
                authority=raw["authority"],
                category=raw["category"],
                url=raw["url"],
                required_markers=markers,
                review_cadence_days=cadence,
            )
        )
        seen.add(source_id)
    if not result:
        raise MaintenanceError("source registry must not be empty")
    return tuple(result)


def fetch_fingerprint(source: SourceDefinition, timeout_seconds: int = 20) -> SourceFingerprint:
    if not _is_allowed_official_url(source.url):
        raise MaintenanceError(f"blocked non-official URL: {source.url}")
    request = Request(source.url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - strict allowlist above
        final_url = response.geturl()
        if not _is_allowed_official_url(final_url):
            raise MaintenanceError(f"blocked redirect outside official hosts: {final_url}")
        content = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        normalized = normalize_html(content, charset)
        missing = [marker for marker in source.required_markers if marker not in normalized]
        if missing:
            raise MaintenanceError(f"required content markers missing for {source.source_id}: {missing}")
        return SourceFingerprint(
            source_id=source.source_id,
            requested_url=source.url,
            final_url=final_url,
            fetched_at=datetime.now(UTC).isoformat(),
            normalized_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            normalized_length=len(normalized),
        )


def compare_fingerprints(
    current: Iterable[SourceFingerprint], baseline: dict[str, Any]
) -> list[dict[str, str]]:
    old = baseline.get("sources", {})
    changes: list[dict[str, str]] = []
    for item in current:
        previous = old.get(item.source_id)
        if previous is None:
            changes.append({"source_id": item.source_id, "status": "baseline_missing"})
        elif previous.get("normalized_sha256") != item.normalized_sha256:
            changes.append({"source_id": item.source_id, "status": "content_changed"})
    current_ids = {item.source_id for item in current}
    for source_id in sorted(set(old) - current_ids):
        changes.append({"source_id": source_id, "status": "source_not_checked"})
    return changes


def _validate_increasing(values: list[int | None], label: str) -> None:
    finite = [value for value in values if value is not None]
    if finite != sorted(finite) or len(finite) != len(set(finite)):
        raise MaintenanceError(f"{label} upper bounds must be strictly increasing")
    if not values or values[-1] is not None or any(value is None for value in values[:-1]):
        raise MaintenanceError(f"{label} must end with exactly one open bracket")


def validate_ruleset(rules: Ruleset) -> None:
    tax = list(rules.income_tax_brackets)
    wage = list(rules.wage_deduction_brackets)
    _validate_increasing([item.upper for item in tax], "income tax brackets")
    _validate_increasing([item.upper for item in wage], "wage deduction brackets")
    if not all(0 < item.rate_bps <= 10_000 for item in tax):
        raise MaintenanceError("income tax rates must be in (0, 10000] bps")
    for previous, current in zip(tax, tax[1:]):
        threshold = previous.upper
        assert threshold is not None
        tax_before = threshold * previous.rate_bps // 10_000 - previous.quick_deduction
        tax_after = threshold * current.rate_bps // 10_000 - current.quick_deduction
        if tax_before != tax_after:
            raise MaintenanceError(f"income tax quick deductions are discontinuous at {threshold}")
    for previous, current in zip(wage, wage[1:]):
        threshold = previous.upper
        assert threshold is not None
        before = previous.base + (threshold - previous.excess_over) * previous.excess_rate_bps // 10_000
        if current.excess_over != threshold or current.base != before:
            raise MaintenanceError(f"wage deduction brackets are discontinuous at {threshold}")
    if rules.wage_deduction_cap <= 0:
        raise MaintenanceError("wage deduction cap must be positive")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_approved_artifacts(root: Path, manifest_path: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise MaintenanceError("unsupported approved artifact manifest schema_version")
    for item in data.get("artifacts", []):
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise MaintenanceError(f"unsafe artifact path: {relative}")
        actual = sha256_file(root / relative)
        if actual != item["sha256"]:
            raise MaintenanceError(f"approved artifact hash mismatch: {relative}")


def validate_project(root: Path) -> dict[str, Any]:
    registry = load_source_registry(root / "maintenance" / "source-registry.json")
    rule_files = sorted((root / "src" / "krtax" / "rules").glob("*.json"))
    if not rule_files:
        raise MaintenanceError("no rulesets found")
    years: list[int] = []
    for path in rule_files:
        try:
            year = int(path.stem)
        except ValueError as exc:
            raise MaintenanceError(f"ruleset filename must be a tax year: {path.name}") from exc
        validate_ruleset(load_ruleset(year))
        years.append(year)
    validate_approved_artifacts(root, root / "maintenance" / "approved-artifacts.json")
    return {"status": "ok", "rulesets": years, "registered_sources": len(registry)}


def _load_baseline(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "sources": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _online_fingerprints(registry: tuple[SourceDefinition, ...]) -> list[SourceFingerprint]:
    results: list[SourceFingerprint] = []
    for source in registry:
        results.append(fetch_fingerprint(source))
    return results


def _snapshot_document(fingerprints: Iterable[SourceFingerprint]) -> dict[str, Any]:
    items = list(fingerprints)
    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "sources": {item.source_id: asdict(item) for item in items},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline-first maintenance harness")
    parser.add_argument("command", choices=("validate", "check", "capture"))
    parser.add_argument("--online", action="store_true", help="allow requests to registered official URLs")
    parser.add_argument("--root", type=Path, default=project_root())
    parser.add_argument("--baseline", type=Path, default=Path("maintenance/source-baseline.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "validate":
            print(json.dumps(validate_project(root), ensure_ascii=False, indent=2))
            return 0
        if not args.online:
            raise MaintenanceError("online source access is disabled; pass --online explicitly")
        registry = load_source_registry(root / "maintenance" / "source-registry.json")
        fingerprints = _online_fingerprints(registry)
        if args.command == "check":
            baseline_path = args.baseline if args.baseline.is_absolute() else root / args.baseline
            changes = compare_fingerprints(fingerprints, _load_baseline(baseline_path))
            print(json.dumps({"status": "changed" if changes else "unchanged", "changes": changes}, ensure_ascii=False, indent=2))
            return 2 if changes else 0
        if args.output is None:
            raise MaintenanceError("capture requires --output")
        output = args.output if args.output.is_absolute() else root / args.output
        baseline = (root / "maintenance" / "source-baseline.json").resolve()
        if output.resolve() == baseline:
            raise MaintenanceError("capture cannot overwrite the approved baseline; write a candidate")
        if output.exists():
            raise MaintenanceError("capture output already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(_snapshot_document(fingerprints), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "captured", "output": str(output)}, ensure_ascii=False))
        return 0
    except (MaintenanceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
