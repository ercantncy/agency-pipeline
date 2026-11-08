"""Shared helpers for the CSV export importers: encoding, header detection, numbers, dates.

The importers are based on what typical platform UI exports look like. Column names, title
lines and number formats change between UI versions, languages and account settings, so
every format MUST be verified against a real file from the agency before the first audit.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

_EMPTY = {"", "--", "-", "—", "–", "n/a", "na", "nan", "none", "null", "(not set)"}
_TOTAL_ROW = re.compile(r"(grand\s+)?total\b")
_DATE_FORMATS = (
    "%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y",
    "%a, %b %d, %Y",
)  # fmt: skip


class ExportError(ValueError):
    """The file is not a usable export (message is written for the consultant to read)."""


@dataclass(frozen=True)
class Col:
    """One logical column: canonical name, accepted header spellings, required or not."""

    name: str
    aliases: tuple[str, ...]
    required: bool = False


@dataclass
class Table:
    """Rows of an export under canonical column names (values still strings)."""

    frame: pd.DataFrame
    units: dict[str, str] = field(default_factory=dict)  # canonical -> "(USD)"-style suffix
    header_line: int = 0
    skipped_total_rows: int = 0


def norm(header: str) -> str:
    """Case/whitespace/punctuation-insensitive header key: 'Conv. value' -> 'conv value'."""
    return re.sub(r"[^a-z0-9]+", " ", header.lower()).strip()


def _unit_split(header: str) -> tuple[str, str | None]:
    m = re.match(r"^(.*?)\s*\(([A-Za-z]{3})\)\s*$", header.strip())
    return (m.group(1), m.group(2).upper()) if m else (header, None)


def read_text(path: Path) -> str:
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def _delimiter(lines: list[str]) -> str:
    sample = "\n".join(lines[:30])
    counts = {d: sample.count(d) for d in (",", "\t", ";")}
    return max(counts, key=counts.__getitem__) if any(counts.values()) else ","


def read_table(
    path: Path,
    label: str,
    cols: list[Col],
    *,
    comment_prefix: str | None = None,
    scan_lines: int = 20,
    extra_check=None,
) -> Table:
    """Find the header row, map headers to canonical names, drop title/comment/total rows.

    `extra_check(found: set[str]) -> list[str]` may return additional missing-column messages.
    """
    text = read_text(path)
    lines = [ln for ln in text.splitlines()]
    if comment_prefix:
        lines = [ln for ln in lines if not ln.lstrip().startswith(comment_prefix)]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        raise ExportError(f"{label}: file '{Path(path).name}' is empty.")
    delim = _delimiter(lines)
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))

    alias_map: dict[str, str] = {}
    for c in cols:
        for a in (c.name, *c.aliases):
            alias_map.setdefault(norm(a), c.name)

    def mapping(row: list[str]) -> dict[int, str]:
        out: dict[int, str] = {}
        for i, cell in enumerate(row):
            base, _ = _unit_split(cell)
            canon = alias_map.get(norm(base))
            if canon and canon not in out.values():
                out[i] = canon
        return out

    best_idx, best = 0, {}
    for i, row in enumerate(rows[:scan_lines]):
        m = mapping(row)
        if len(m) > len(best):
            best_idx, best = i, m
    found = set(best.values())
    missing = [c for c in cols if c.required and c.name not in found]
    problems = [f"'{c.aliases[0] if c.aliases else c.name}'" for c in missing]
    if extra_check:
        problems += extra_check(found)
    if problems:
        shown = ", ".join(h for h in rows[best_idx] if h.strip()) or "(none recognised)"
        raise ExportError(
            f"{label}: missing required column(s): {', '.join(problems)}. "
            f"Header row found: {shown}. Re-export with these columns included."
        )

    header = rows[best_idx]
    units = {}
    for i, canon in best.items():
        _, unit = _unit_split(header[i])
        if unit:
            units[canon] = unit
    records, skipped = [], 0
    for row in rows[best_idx + 1 :]:
        cells = {canon: (row[i].strip() if i < len(row) else "") for i, canon in best.items()}
        first_cell = next((c.strip().lower() for c in row if c.strip()), "")
        if _TOTAL_ROW.match(first_cell):
            skipped += 1
            continue
        if not any(cells.values()):
            continue
        records.append(cells)
    frame = pd.DataFrame(records, columns=[best[i] for i in sorted(best)])
    return Table(frame, units, best_idx, skipped)


def parse_number(value) -> float | None:
    """'1,234.56' -> 1234.56; '--' / '' -> None; '$12.30', '(5)', '1.234,56' handled."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    s = str(value).strip()
    if s.lower() in _EMPTY:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.,\-]", "", s.strip("()"))
    if not s or s in {"-", ".", ","}:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        out = float(s)
    except ValueError:
        return None
    return -out if neg else out


def number_column(series: pd.Series, default: float = 0.0) -> pd.Series:
    return series.map(parse_number).astype(float).fillna(default)


def percent_column(series: pd.Series) -> pd.Series:
    """'5.2%' -> 0.052; plain '0.052' stays 0.052."""

    def one(v):
        n = parse_number(v)
        if n is None:
            return None
        return n / 100 if "%" in str(v) else n

    return series.map(one).astype(float)


def date_column(series: pd.Series, label: str, column: str) -> pd.Series:
    """Parse a date column. Blank cells -> NaT; slash dates are month-first unless a day > 12."""
    values = series.astype(str).str.strip()
    slash = values[values.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}")]
    day_first = bool(len(slash)) and bool((slash.str.split("/").str[0].astype(int) > 12).any())
    formats = (*_DATE_FORMATS, "%d/%m/%Y" if day_first else "%m/%d/%Y")
    out = []
    for v in values:
        if v.lower() in _EMPTY:
            out.append(pd.NaT)
            continue
        for fmt in formats:
            try:
                out.append(pd.Timestamp(datetime.strptime(v, fmt).date()))
                break
            except ValueError:
                continue
        else:
            raise ExportError(
                f"{label}: cannot read '{v}' in column '{column}' as a date. "
                f"Expected e.g. 2026-10-31, 20261031 or Oct 31, 2026."
            )
    return pd.Series(out, index=series.index)


def stable_id(*parts: str) -> str:
    """Deterministic numeric-looking id derived from names (when an export has no id column)."""
    digest = hashlib.sha1("|".join(parts).encode()).hexdigest()
    return str(int(digest[:12], 16))[:10]


def trim_to_range(df: pd.DataFrame, column: str, start: date, end: date) -> pd.DataFrame:
    days = pd.to_datetime(df[column])
    return df[(days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end))].reset_index(drop=True)
