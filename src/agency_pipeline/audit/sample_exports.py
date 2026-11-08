"""Write UI-style CSV exports from the synthetic sources, to exercise the importers.

The files mimic what the Google Ads, GA4, Meta Ads Manager and Search Console UIs download
(title lines, '#' comments, thousands separators, "--" for empty, total rows). The formats
are based on typical exports and must be verified against real files.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from agency_pipeline import config
from agency_pipeline.sources import get_sources
from agency_pipeline.sources.synthetic.scenario import profile_for

DEFAULT_END = date(2026, 10, 31)
DEFAULT_DAYS = 30
FILES = {
    "google_ads": "google-ads-campaigns-by-day.csv",
    "ga4": "ga4-traffic-acquisition.csv",
    "meta": "meta-ads-campaigns-by-day.csv",
    "gsc": "search-console-Dates.csv",
}


def _n(value: float, decimals: int = 0) -> str:
    """Number with thousands separators; 0 as '--' is handled by callers."""
    return f"{value:,.{decimals}f}"


def _write(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)


def _long(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def write_google_ads(df: pd.DataFrame, path: Path, currency: str, start: date, end: date) -> None:
    rows: list[list[str]] = [
        ["Campaign report"],
        [f"{_long(start)} - {_long(end)}"],
        ["Day", "Campaign", "Campaign type", "Currency code", "Impr.", "Clicks", "Cost",
         "Conversions", "Conv. value"],
    ]  # fmt: skip
    kinds = {"SEARCH": "Search", "PERFORMANCE_MAX": "Performance Max", "DISPLAY": "Display"}
    for r in df.sort_values(["segments_date", "campaign_name"]).itertuples():
        rows.append([
            r.segments_date.isoformat(), r.campaign_name,
            kinds.get(r.campaign_advertising_channel_type, r.campaign_advertising_channel_type),
            currency, _n(r.metrics_impressions), _n(r.metrics_clicks),
            _n(r.metrics_cost_micros / 1e6, 2), _n(r.metrics_conversions, 2),
            _n(r.metrics_conversions_value, 2) if r.metrics_conversions_value else "--",
        ])  # fmt: skip
    tot = df[["metrics_impressions", "metrics_clicks", "metrics_cost_micros",
              "metrics_conversions", "metrics_conversions_value"]].sum()  # fmt: skip
    for label in ("Total: Account", "Total: Campaigns"):
        rows.append([
            label, "--", "--", "--", _n(tot.iloc[0]), _n(tot.iloc[1]),
            _n(tot.iloc[2] / 1e6, 2), _n(tot.iloc[3], 2), _n(tot.iloc[4], 2),
        ])  # fmt: skip
    _write(path, rows)


def write_ga4(df: pd.DataFrame, path: Path, client_name: str, start: date, end: date) -> None:
    rows: list[list[str]] = [
        ["# ----------------------------------------"],
        ["# Traffic acquisition: Session source / medium"],
        [f"# Property: {client_name} - GA4"],
        ["# ----------------------------------------"],
        [f"# Start date: {start:%Y%m%d}"],
        [f"# End date: {end:%Y%m%d}"],
        [],
        ["Date", "Session source / medium", "Session campaign", "Sessions", "Engaged sessions",
         "Total users", "Key events", "Purchase revenue"],
    ]  # fmt: skip
    for r in df.sort_values(["date", "session_source", "session_medium"]).itertuples():
        rows.append([
            r.date, f"{r.session_source} / {r.session_medium}", r.session_campaign_name,
            _n(r.sessions), _n(r.engaged_sessions), _n(r.total_users), _n(r.key_events),
            _n(r.purchase_revenue, 2),
        ])  # fmt: skip
    _write(path, rows)


def write_meta(df: pd.DataFrame, path: Path, currency: str, goal_is_lead: bool, variant: str):
    """`variant` 'day' -> Day + Campaign ID; 'reporting' -> Reporting starts/ends, no id."""
    date_cols = ["Day"] if variant == "day" else ["Reporting starts", "Reporting ends"]
    id_cols = ["Campaign ID"] if variant == "day" else []
    result_cols = ["Leads"] if goal_is_lead else ["Purchases", "Purchases conversion value"]
    rows: list[list[str]] = [
        [*date_cols, "Campaign name", *id_cols, f"Amount spent ({currency})", "Impressions",
         "Link clicks", *result_cols]
    ]  # fmt: skip
    for r in df.sort_values(["date_start", "campaign_name"]).itertuples():
        actions = {a["action_type"]: float(a["value"]) for a in json.loads(r.actions)}
        values = {a["action_type"]: float(a["value"]) for a in json.loads(r.action_values)}
        if goal_is_lead:
            results = [_n(actions["offsite_conversion.fb_pixel_lead"])]
        else:
            purchases = actions["offsite_conversion.fb_pixel_purchase"]
            value = values.get("offsite_conversion.fb_pixel_purchase", 0.0)
            results = [_n(purchases) if purchases else "--", _n(value, 2) if value else "--"]
        dates = [r.date_start] if variant == "day" else [r.date_start, r.date_start]
        ids = [r.campaign_id] if variant == "day" else []
        rows.append([
            *dates, r.campaign_name, *ids, _n(float(r.spend), 2), _n(float(r.impressions)),
            _n(float(r.inline_link_clicks)), *results,
        ])  # fmt: skip
    _write(path, rows)


def write_gsc(df: pd.DataFrame, path: Path) -> None:
    daily = (
        df.assign(pos_w=df["position"] * df["impressions"])
        .groupby("date", as_index=False)
        .agg(clicks=("clicks", "sum"), impressions=("impressions", "sum"), pos_w=("pos_w", "sum"))
    )
    rows = [["Date", "Clicks", "Impressions", "CTR", "Position"]]
    for r in daily.itertuples():
        ctr = 100 * r.clicks / r.impressions if r.impressions else 0
        pos = r.pos_w / r.impressions if r.impressions else 0
        rows.append(
            [r.date.isoformat(), _n(r.clicks), _n(r.impressions), f"{ctr:.1f}%", f"{pos:.1f}"]
        )
    _write(path, rows)


def generate(
    client_id: str, out_dir: Path, end: date = DEFAULT_END, days: int = DEFAULT_DAYS
) -> dict[str, Path]:
    """Write the four exports for one synthetic client; returns {kind: path}."""
    clients = {c.client_id: c for c in config.load_clients()}
    if client_id not in clients:
        raise ValueError(f"unknown client '{client_id}' (known: {', '.join(sorted(clients))})")
    client = clients[client_id]
    start = end - timedelta(days=days - 1)
    frames = {s.name: s.extract(client, start, end) for s in get_sources()}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {k: out_dir / v for k, v in FILES.items()}
    is_lead = profile_for(client).goal == "lead"
    write_google_ads(frames["google_ads"], paths["google_ads"], client.currency, start, end)
    write_ga4(frames["ga4"], paths["ga4"], client.client_name, start, end)
    variant = "reporting" if client_id == "harbor-coffee" else "day"
    write_meta(frames["meta_ads"], paths["meta"], client.currency, is_lead, variant)
    write_gsc(frames["gsc"], paths["gsc"])
    return paths
