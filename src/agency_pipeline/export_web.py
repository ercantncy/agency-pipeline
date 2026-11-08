"""Export the marts, alerts and commentary as static JSON for the web app (see docs/WEB_SPEC.md)."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

from agency_pipeline import commentary, config, monitoring

DBT_PROJECT = config.PROJECT_ROOT / "dbt" / "dbt_project.yml"


def load_thresholds(path: Path = DBT_PROJECT) -> dict[str, dict[str, float]]:
    """Reconciliation thresholds from the dbt vars (single source of truth)."""
    v = yaml.safe_load(path.read_text())["vars"]
    return {
        ch: {"warn": v[f"recon_{ch}_warn"], "critical": v[f"recon_{ch}_critical"]}
        for ch in ("google_ads", "meta_ads")
    }


def _clean(v):
    """JSON-safe value: dates -> ISO, Decimal/float -> rounded float, NaN/inf/None -> None."""
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        v = float(v)
    if isinstance(v, float):
        return None if math.isnan(v) or math.isinf(v) else round(v, 4)
    return v


def _rows(con, sql: str, params: list, cols: list[str], month_cols=("month",)) -> list[dict]:
    out = []
    for r in con.execute(sql, params).fetchall():
        d = {}
        for c, v in zip(cols, r, strict=True):
            d[c] = v.strftime("%Y-%m") if c in month_cols and v is not None else _clean(v)
        out.append(d)
    return out


def default_months(con: duckdb.DuckDBPyConnection) -> list[date]:
    """Months present in rpt_client_monthly that are complete at the end of the data.

    The first month is kept even though data starts mid-month (2026-07 starts on 07-04) because
    the marts report it; only a trailing partial month is dropped.
    """
    last = con.execute("select max(date) from marts.fct_paid_daily").fetchone()[0]
    months = [
        r[0]
        for r in con.execute(
            "select distinct month from marts.rpt_client_monthly order by 1"
        ).fetchall()
    ]
    return [
        m for m in months if (m + timedelta(days=32)).replace(day=1) - timedelta(days=1) <= last
    ]


def _month_end(m: date) -> date:
    return (m + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def _client_payload(con, client: dict, months: list[date], thresholds, use_llm) -> dict:
    cid = client["client_id"]
    p = [cid]
    payload: dict = {"client": client}
    payload["monthly"] = _rows(
        con,
        """select month, channel, spend, clicks, conversions, conversion_value, cpa, roas, ctr,
                  spend_mom_pct, conversions_mom_pct, cpa_mom_pct, roas_mom_pct
           from marts.rpt_client_monthly where client_id = ? order by month, channel""",
        p,
        [
            "month",
            "channel",
            "spend",
            "clicks",
            "conversions",
            "conversion_value",
            "cpa",
            "roas",
            "ctr",
            "spend_mom_pct",
            "conversions_mom_pct",
            "cpa_mom_pct",
            "roas_mom_pct",
        ],
    )
    payload["paid_daily"] = _rows(
        con,
        """select date, channel, sum(spend), sum(impressions), sum(clicks),
                  sum(platform_conversions), sum(platform_conversion_value)
           from marts.fct_paid_daily where client_id = ? group by 1, 2 order by 1, 2""",
        p,
        ["date", "channel", "spend", "impressions", "clicks", "conversions", "conversion_value"],
    )
    payload["campaigns_monthly"] = _rows(
        con,
        """select cast(date_trunc('month', date) as date), channel, campaign_id,
                  any_value(campaign_name), sum(spend), sum(impressions), sum(clicks),
                  sum(platform_conversions), sum(platform_conversion_value)
           from marts.fct_paid_daily where client_id = ? group by 1, 2, 3 order by 1, 2, 3""",
        p,
        [
            "month",
            "channel",
            "campaign_id",
            "campaign_name",
            "spend",
            "impressions",
            "clicks",
            "conversions",
            "conversion_value",
        ],
    )
    payload["web_daily"] = _rows(
        con,
        """select date, channel_group, sum(sessions), sum(engaged_sessions), sum(users),
                  sum(key_events), sum(revenue)
           from marts.fct_web_daily where client_id = ? group by 1, 2 order by 1, 2""",
        p,
        ["date", "channel_group", "sessions", "engaged_sessions", "users", "key_events", "revenue"],
    )
    payload["seo_daily"] = _rows(
        con,
        """select date, clicks, impressions, ctr, avg_position
           from marts.fct_seo_daily where client_id = ? order by date""",
        p,
        ["date", "clicks", "impressions", "ctr", "avg_position"],
    )
    payload["seo_queries_monthly"] = _rows(
        con,
        """select month, query, clicks, impressions, ctr, avg_position
           from marts.fct_seo_query_monthly where client_id = ? order by month, query""",
        p,
        ["month", "query", "clicks", "impressions", "ctr", "avg_position"],
    )
    payload["reconciliation_daily"] = _rows(
        con,
        """select date, channel, platform_clicks, ga4_sessions, session_click_ratio,
                  platform_conversions, ga4_key_events, status
           from marts.fct_paid_vs_ga4_reconciliation where client_id = ? order by date, channel""",
        p,
        [
            "date",
            "channel",
            "platform_clicks",
            "ga4_sessions",
            "session_click_ratio",
            "platform_conversions",
            "ga4_key_events",
            "status",
        ],
    )
    payload["thresholds"] = thresholds
    by_month = {}
    for m in months:
        alerts = monitoring.run_checks(con, _month_end(m), cid)
        text = commentary.generate_commentary(con, cid, m, alerts, use_llm=use_llm)
        by_month[m.strftime("%Y-%m")] = {
            "alerts": [{k: _clean(v) for k, v in a.to_dict().items()} for a in alerts],
            "commentary": {"text": text.text, "source": text.source},
        }
    payload["months"] = by_month
    return payload


def _write(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


def export_web(
    con: duckdb.DuckDBPyConnection,
    out_dir: Path,
    months: list[date] | None = None,
    use_llm: bool | None = False,
) -> list[Path]:
    """Write manifest.json and clients/<id>.json under out_dir; returns the written paths."""
    out_dir = Path(out_dir)
    months = sorted(m.replace(day=1) for m in (months or default_months(con)))
    if not months:
        raise ValueError("no months to export")
    thresholds = load_thresholds()
    cols = [
        "client_id",
        "client_name",
        "currency",
        "scenario",
        "agency_name",
        "agency_logo_text",
        "agency_primary_color",
        "google_ads_customer_id",
        "meta_account_id",
        "ga4_property_id",
        "gsc_site_url",
    ]
    rows = con.execute(
        f"select {', '.join(cols)} from marts.dim_client order by client_id"
    ).fetchall()

    written: list[Path] = []
    manifest_clients = []
    for r in rows:
        client = dict(zip(cols, r, strict=True))
        payload = _client_payload(con, client, months, thresholds, use_llm)
        written.append(_write(out_dir / "clients" / f"{client['client_id']}.json", payload))
        counts = {}
        for m, info in payload["months"].items():
            sev = [a["severity"] for a in info["alerts"]]
            counts[m] = {"critical": sev.count("critical"), "warn": sev.count("warn")}
        manifest_clients.append(
            {
                "client_id": client["client_id"],
                "client_name": client["client_name"],
                "currency": client["currency"],
                "scenario": client["scenario"],
                "alert_counts_by_month": counts,
            }
        )
    first = rows[0]
    manifest = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agency": {
            "name": first[cols.index("agency_name")],
            "logo_text": first[cols.index("agency_logo_text")],
            "primary_color": first[cols.index("agency_primary_color")],
        },
        "months": [m.strftime("%Y-%m") for m in months],
        "default_month": months[-1].strftime("%Y-%m"),
        "clients": manifest_clients,
    }
    written.insert(0, _write(out_dir / "manifest.json", manifest))
    return written
