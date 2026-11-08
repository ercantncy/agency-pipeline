"""Google Ads UI export -> `raw.google_ads_campaign_daily`.

Expected file: Campaigns report, segmented by Day, downloaded as CSV. Typical layout:

    Campaign report                      <- title line 1 (report name)
    October 2, 2026 - October 31, 2026   <- title line 2 (date range)
    Day,Campaign,Campaign type,Currency code,Impr.,Clicks,Cost,Conversions,Conv. value
    2026-10-02,Search - Brand,Search,USD,"1,204",96,412.50,7.00,--
    Total: Account,...                   <- trailing total rows are dropped

Numbers may carry thousands separators; "--" means empty. NOTE: this is based on typical
exports and must be verified against a real file (column names change with UI language/version).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from agency_pipeline.sources.csv_exports import _common as c

LABEL = "Google Ads export"
COLUMNS = [
    "segments_date", "customer_id", "campaign_id", "campaign_name",
    "campaign_advertising_channel_type", "metrics_impressions", "metrics_clicks",
    "metrics_cost_micros", "metrics_conversions", "metrics_conversions_value", "client_id",
]  # fmt: skip

SPEC = [
    c.Col("day", ("Day", "Date"), True),
    c.Col("campaign", ("Campaign", "Campaign name"), True),
    c.Col("campaign_type", ("Campaign type", "Type", "Advertising channel type")),
    c.Col("campaign_id", ("Campaign ID", "Campaign id")),
    c.Col("currency", ("Currency code", "Currency")),
    c.Col("impressions", ("Impr.", "Impressions", "Impr"), True),
    c.Col("clicks", ("Clicks",), True),
    c.Col("cost", ("Cost", "Spend"), True),
    c.Col("conversions", ("Conversions", "Conv.")),
    c.Col("conv_value", ("Conv. value", "Conversion value", "Total conv. value")),
]  # fmt: skip


def parse(path: Path, client_id: str = "audit") -> pd.DataFrame:
    """Read the export and return the raw-table frame (one row per day and campaign)."""
    t = c.read_table(path, LABEL, SPEC)
    f = t.frame
    f = f.assign(day=c.date_column(f["day"], LABEL, "Day")).dropna(subset=["day"])
    if f.empty:
        raise c.ExportError(f"{LABEL}: no data rows found under the header.")
    warnings: list[str] = []
    for name in ("conversions", "conv_value"):
        if name not in f:
            f[name] = ""
            warnings.append(f"Google Ads export has no '{name}' column; treated as 0.")
    if "campaign_id" not in f:
        f["campaign_id"] = f["campaign"].map(lambda n: c.stable_id("google", n))
    else:
        f["campaign_id"] = f["campaign_id"].where(
            f["campaign_id"] != "", f["campaign"].map(lambda n: c.stable_id("google", n))
        )
    ctype = f["campaign_type"] if "campaign_type" in f else pd.Series("", index=f.index)
    f["campaign_type"] = (
        ctype.str.upper().str.replace(r"[^A-Z0-9]+", "_", regex=True).str.strip("_")
        .replace("", "UNSPECIFIED")
    )  # fmt: skip
    for col in ("impressions", "clicks", "cost", "conversions", "conv_value"):
        f[col] = c.number_column(f[col])
    keys = ["day", "campaign_id", "campaign", "campaign_type"]
    g = f.groupby(keys, as_index=False)[
        ["impressions", "clicks", "cost", "conversions", "conv_value"]
    ].sum()
    out = pd.DataFrame({
        "segments_date": g["day"].dt.date,
        "customer_id": "audit",
        "campaign_id": g["campaign_id"],
        "campaign_name": g["campaign"],
        "campaign_advertising_channel_type": g["campaign_type"],
        "metrics_impressions": g["impressions"].round().astype("int64"),
        "metrics_clicks": g["clicks"].round().astype("int64"),
        "metrics_cost_micros": np.round(g["cost"] * 1_000_000).astype("int64"),
        "metrics_conversions": g["conversions"].round(2),
        "metrics_conversions_value": g["conv_value"].round(2),
        "client_id": client_id,
    })  # fmt: skip
    out.attrs["currency"] = (
        f["currency"].replace("", np.nan).dropna().iloc[0].upper()
        if "currency" in f and f["currency"].replace("", np.nan).notna().any()
        else None
    )
    out.attrs["warnings"] = warnings
    return out[COLUMNS]
