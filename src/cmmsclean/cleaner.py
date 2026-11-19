"""Clean a CMMS export file row by row."""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .rules import clean_text, normalize_date, normalize_location, normalize_priority, normalize_status

OUTPUT_COLUMNS = ["id", "location", "status", "priority", "created", "closed", "description"]
HEADER_ALIASES = {
    "id": {"id", "wo", "wo #", "wo id", "work order", "work order #", "work order id", "ticket"},
    "location": {"location", "loc", "site", "building room"},
    "status": {"status", "state", "wo status"},
    "priority": {"priority", "prio", "urgency"},
    "created": {"created", "date opened", "opened", "open date", "date created", "created date"},
    "closed": {"closed", "date closed", "close date", "completed date", "date completed"},
    "description": {"description", "desc", "problem", "details", "summary"},
}
HEADER_LOOKUP = {alias: name for name, aliases in HEADER_ALIASES.items() for alias in aliases}
FIELD_RULES = {
    "location": normalize_location,
    "status": normalize_status,
    "priority": normalize_priority,
    "created": normalize_date,
    "closed": normalize_date,
}


@dataclass
class CleanResult:
    """Rows and counters produced by one cleaning run."""

    rows: list[dict[str, str]] = field(default_factory=list)
    rejects: list[dict[str, str]] = field(default_factory=list)
    rows_in: int = 0
    duplicates: int = 0
    changed: Counter = field(default_factory=Counter)
    unresolved: Counter = field(default_factory=Counter)


def map_headers(headers: list[str]) -> dict[str, str]:
    """Return {original header: canonical name}. Raises ValueError if id or created is missing."""
    mapping = {}
    for header in headers:
        name = HEADER_LOOKUP.get(" ".join(header.strip().lower().split()))
        if name and name not in mapping.values():
            mapping[header] = name
    for needed in ("id", "created"):
        if needed not in mapping.values():
            raise ValueError(f"no column found for '{needed}'")
    return mapping


def clean_rows(records: list[dict[str, str]], mapping: dict[str, str]) -> CleanResult:
    """Normalize records. Rows with no id or no readable created date go to rejects."""
    result = CleanResult()
    seen: set[str] = set()
    for record in records:
        result.rows_in += 1
        row = {name: clean_text(record.get(orig) or "") for orig, name in mapping.items()}
        row = {col: row.get(col, "") for col in OUTPUT_COLUMNS}
        reason = _reject_reason(row)
        if reason:
            result.rejects.append({**row, "reason": reason})
            continue
        if row["id"].upper() in seen:
            result.duplicates += 1
            continue
        seen.add(row["id"].upper())
        for col, rule in FIELD_RULES.items():
            original = row[col]
            if not original:
                continue
            fixed = rule(original)
            if fixed is None:
                result.unresolved[col] += 1
            elif fixed != original:
                row[col] = fixed
                result.changed[col] += 1
        result.rows.append(row)
    return result


def _reject_reason(row: dict[str, str]) -> str:
    if not row["id"]:
        return "missing id"
    if not row["created"]:
        return "missing created date"
    if normalize_date(row["created"]) is None:
        return "unreadable created date"
    return ""


def read_records(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file. Returns (headers, records)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("file has no header row")
        return list(reader.fieldnames), list(reader)


def write_rows(path: str | Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    """Write rows to a CSV file with the given column order."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def format_report(result: CleanResult) -> str:
    """Return a short text summary of a run."""
    lines = [
        f"rows in {result.rows_in}  clean {len(result.rows)}  rejected {len(result.rejects)}  duplicates dropped {result.duplicates}",
    ]
    for col in FIELD_RULES:
        lines.append(f"{col:<9} fixed {result.changed[col]:>3}  unresolved {result.unresolved[col]:>3}")
    return "\n".join(lines)
