"""Meta Ads Manager export -> `raw.meta_ads_insights_daily`.

Expected file: Ads Manager, campaign level, Breakdown -> Time -> Day, Export -> CSV. Typical:

    Day,Campaign name,Campaign ID,Amount spent (USD),Impressions,Link clicks,Purchases,
    Purchases conversion value   (one header line in the real file)
    2026-10-02,Prospecting - Lookalike,6100001,412.50,"41,200",455,9,864.00

Variants handled: "Reporting starts" instead of "Day"; no "Campaign ID" (a stable id is derived
from the campaign name); "Leads" and/or "Purchases" and/or generic "Results". The raw table
expects Marketing API style `actions` / `action_values` JSON, which is rebuilt here.
NOTE: based on typical exports and must be verified against a real file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from agency_pipeline.sources.csv_exports import _common as c

LABEL = "Meta Ads export"
COLUMNS = [
    "date_start", "account_id", "campaign_id", "campaign_name", "objective", "impressions",
    "inline_link_clicks", "spend", "actions", "action_values", "client_id",
]  # fmt: skip

SPEC = [
    c.Col("day", ("Day", "Reporting starts", "Date"), True),
    c.Col("campaign", ("Campaign name", "Campaign"), True),
    c.Col("campaign_id", ("Campaign ID",)),
    c.Col("objective", ("Objective",)),
    c.Col("spend", ("Amount spent", "Spend", "Cost"), True),
    c.Col("impressions", ("Impressions",), True),
    c.Col("link_clicks", ("Link clicks", "Inline link clicks"), True),
    c.Col("purchases", ("Purchases", "Website purchases")),
    c.Col("leads", ("Leads", "Website leads")),
    c.Col("results", ("Results",)),
    c.Col("value", (
        "Purchases conversion value", "Purchase conversion value",
        "Website purchases conversion value", "Conversion value",
    )),
]  # fmt: skip


def parse(path: Path, client_id: str = "audit") -> pd.DataFrame:
    t = c.read_table(path, LABEL, SPEC)
    f = t.frame
    f = f.assign(day=c.date_column(f["day"], LABEL, "Day")).dropna(subset=["day"])
    if f.empty:
        raise c.ExportError(f"{LABEL}: no data rows found under the header.")
    warnings: list[str] = []
    for col in ("spend", "impressions", "link_clicks"):
        f[col] = c.number_column(f[col])
    for col in ("purchases", "leads", "results", "value"):
        f[col] = c.number_column(f[col]) if col in f else 0.0
    if "campaign_id" not in f:
        f["campaign_id"] = f["campaign"].map(lambda n: c.stable_id("meta", n))
    f["campaign_id"] = f["campaign_id"].where(
        f["campaign_id"] != "", f["campaign"].map(lambda n: c.stable_id("meta", n))
    )
    if "objective" not in f:
        f["objective"] = "UNSPECIFIED"
    has_specific = "purchases" in t.frame or "leads" in t.frame
    if "results" in t.frame and not has_specific:
        # Generic "Results": a conversion value means sales, otherwise leads.
        key = "purchases" if f["value"].sum() > 0 else "leads"
        f[key] = f["results"]
        warnings.append(f"Meta 'Results' column treated as {key}; verify the campaign objective.")
    if not has_specific and "results" not in t.frame:
        warnings.append("Meta export has no Purchases/Leads/Results column; conversions are 0.")
    g = f.groupby(["day", "campaign_id", "campaign", "objective"], as_index=False)[
        ["spend", "impressions", "link_clicks", "purchases", "leads", "value"]
    ].sum()

    def actions(r) -> str:
        return json.dumps([
            {"action_type": "link_click", "value": str(int(round(r.link_clicks)))},
            {
                "action_type": "offsite_conversion.fb_pixel_purchase",
                "value": str(int(round(r.purchases))),
            },
            {"action_type": "offsite_conversion.fb_pixel_lead", "value": str(int(round(r.leads)))},
        ])  # fmt: skip

    def action_values(r) -> str:
        if r.value <= 0:
            return "[]"
        return json.dumps(
            [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": f"{r.value:.2f}"}]
        )

    out = pd.DataFrame({
        "date_start": g["day"].dt.date.astype(str),
        "account_id": "audit",
        "campaign_id": g["campaign_id"],
        "campaign_name": g["campaign"],
        "objective": g["objective"].str.upper().str.replace(r"[^A-Z0-9]+", "_", regex=True),
        "impressions": g["impressions"].round().astype("int64").astype(str),
        "inline_link_clicks": g["link_clicks"].round().astype("int64").astype(str),
        "spend": g["spend"].map(lambda v: f"{v:.2f}"),
        "actions": g.apply(actions, axis=1),
        "action_values": g.apply(action_values, axis=1),
        "client_id": client_id,
    })  # fmt: skip
    out.attrs["currency"] = t.units.get("spend")
    out.attrs["warnings"] = warnings
    return out[COLUMNS]
