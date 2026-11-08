"""GA4 report export -> `raw.ga4_traffic_daily`.

Expected file: an Explore / Reports "Download file -> CSV" with Date as a dimension. GA4 starts
the file with '#' comment lines (report name, property, date range) and a blank line:

    # Start date: 20261002
    # End date: 20261031
    Date,Session source / medium,Session campaign,Sessions,Engaged sessions,Total users,
    Key events,Purchase revenue   (one header line in the real file)
    20261002,google / cpc,Search - Brand,"1,011",620,905,34,1520.00

Source and medium may be one combined column ("google / cpc") or two columns. "Conversions"
is accepted as an alias of "Key events" (older properties). NOTE: based on typical exports and
must be verified against a real file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from agency_pipeline.sources.csv_exports import _common as c

LABEL = "GA4 export"
COLUMNS = [
    "date", "property_id", "session_source", "session_medium", "session_campaign_name",
    "sessions", "engaged_sessions", "total_users", "key_events", "purchase_revenue", "client_id",
]  # fmt: skip

SPEC = [
    c.Col("date", ("Date", "Day"), True),
    c.Col("source_medium", ("Session source / medium", "Source / medium", "Session source medium")),
    c.Col("source", ("Session source", "Source")),
    c.Col("medium", ("Session medium", "Medium")),
    c.Col("campaign", ("Session campaign", "Session campaign name", "Campaign")),
    c.Col("sessions", ("Sessions",), True),
    c.Col("engaged", ("Engaged sessions",)),
    c.Col("users", ("Total users", "Users")),
    c.Col("key_events", ("Key events", "Conversions", "Event count")),
    c.Col("revenue", ("Purchase revenue", "Total revenue", "Revenue")),
]  # fmt: skip


def _need_source_medium(found: set[str]) -> list[str]:
    if "source_medium" in found or {"source", "medium"} <= found:
        return []
    return ["'Session source / medium' (or both 'Session source' and 'Session medium')"]


def parse(path: Path, client_id: str = "audit") -> pd.DataFrame:
    t = c.read_table(path, LABEL, SPEC, comment_prefix="#", extra_check=_need_source_medium)
    f = t.frame
    f = f.assign(date=c.date_column(f["date"], LABEL, "Date")).dropna(subset=["date"])
    if f.empty:
        raise c.ExportError(f"{LABEL}: no data rows found under the header.")
    warnings: list[str] = []
    if "source_medium" in f:
        parts = f["source_medium"].str.split(r"\s+/\s+", n=1, regex=True, expand=True)
        f["source"] = parts[0].fillna("(not set)")
        f["medium"] = (parts[1] if 1 in parts else pd.Series("", index=f.index)).fillna("(not set)")
    for col, default in (("campaign", "(not set)"),):
        if col not in f:
            f[col] = default
            warnings.append("GA4 export has no campaign column; UTM campaign checks are limited.")
    f["campaign"] = f["campaign"].where(f["campaign"] != "", "(not set)")
    f["source"] = f["source"].where(f["source"] != "", "(not set)")
    f["medium"] = f["medium"].where(f["medium"] != "", "(not set)")
    for col, label in (("engaged", "Engaged sessions"), ("users", "Total users"),
                       ("key_events", "Key events"), ("revenue", "Purchase revenue")):  # fmt: skip
        if col not in f:
            f[col] = ""
            warnings.append(f"GA4 export has no '{label}' column; treated as 0.")
    for col in ("sessions", "engaged", "users", "key_events", "revenue"):
        f[col] = c.number_column(f[col])
    g = f.groupby(["date", "source", "medium", "campaign"], as_index=False)[
        ["sessions", "engaged", "users", "key_events", "revenue"]
    ].sum()
    out = pd.DataFrame({
        "date": g["date"].dt.strftime("%Y%m%d"),
        "property_id": "audit",
        "session_source": g["source"],
        "session_medium": g["medium"],
        "session_campaign_name": g["campaign"],
        "sessions": g["sessions"].round().astype("int64"),
        "engaged_sessions": g["engaged"].round().astype("int64"),
        "total_users": g["users"].round().astype("int64"),
        "key_events": g["key_events"].astype(float),
        "purchase_revenue": g["revenue"].astype(float),
        "client_id": client_id,
    })  # fmt: skip
    out.attrs["warnings"] = warnings
    return out[COLUMNS]


def header_period(path: Path) -> tuple[str, str] | None:
    """Start/end dates from the '# Start date:' comment lines, if present (informational)."""
    text = c.read_text(path)
    s = re.search(r"#\s*Start date:\s*(\S+)", text)
    e = re.search(r"#\s*End date:\s*(\S+)", text)
    return (s.group(1), e.group(1)) if s and e else None
