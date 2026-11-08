"""Search Console Performance export ("Dates.csv") -> `raw.gsc_search_daily`.

Expected file: Performance -> Export -> Download CSV; the zip contains Dates.csv:

    Date,Clicks,Impressions,CTR,Position
    2026-10-02,118,"2,310",5.1%,14.2

Only daily totals are available, so rows are loaded with query='(all)' and page='(all)'.
NOTE: based on typical exports and must be verified against a real file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from agency_pipeline.sources.csv_exports import _common as c

LABEL = "Search Console export"
COLUMNS = [
    "date", "site_url", "query", "page", "clicks", "impressions", "ctr", "position", "client_id",
]  # fmt: skip

SPEC = [
    c.Col("date", ("Date", "Day"), True),
    c.Col("clicks", ("Clicks", "Total clicks"), True),
    c.Col("impressions", ("Impressions", "Total impressions"), True),
    c.Col("ctr", ("CTR", "Average CTR")),
    c.Col("position", ("Position", "Average position")),
]  # fmt: skip


def parse(path: Path, client_id: str = "audit") -> pd.DataFrame:
    f = c.read_table(path, LABEL, SPEC).frame
    f = f.assign(date=c.date_column(f["date"], LABEL, "Date")).dropna(subset=["date"])
    if f.empty:
        raise c.ExportError(f"{LABEL}: no data rows found under the header.")
    clicks = c.number_column(f["clicks"])
    impressions = c.number_column(f["impressions"])
    ctr = c.percent_column(f["ctr"]) if "ctr" in f else pd.Series(float("nan"), index=f.index)
    computed = (clicks / impressions.where(impressions > 0)).astype(float)
    position = c.number_column(f["position"], float("nan")) if "position" in f else float("nan")
    out = pd.DataFrame({
        "date": f["date"].dt.date,
        "site_url": "(audit)",
        "query": "(all)",
        "page": "(all)",
        "clicks": clicks.round().astype("int64"),
        "impressions": impressions.round().astype("int64"),
        "ctr": ctr.fillna(computed).fillna(0.0),
        "position": position,
        "client_id": client_id,
    })  # fmt: skip
    out.attrs["warnings"] = []
    return out[COLUMNS].drop_duplicates("date", keep="last").reset_index(drop=True)
