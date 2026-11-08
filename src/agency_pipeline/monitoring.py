"""Monitoring checks over the marts: freshness, paid-vs-GA4 reconciliation, traffic volume drops."""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Literal

import duckdb

WINDOW_DAYS = 14
FRESHNESS_LAG_DAYS = 2
VOLUME_DROP_RATIO = 0.30

CHANNEL_LABELS = {
    "google_ads": ("Google Ads", "paid-search"),
    "meta_ads": ("Meta Ads", "paid-social"),
}
_SEVERITY_RANK = {"warn": 1, "critical": 2}


@dataclass(frozen=True)
class Alert:
    client_id: str
    severity: Literal["warn", "critical"]
    check: str  # "freshness" | "reconciliation" | "volume_drop"
    message: str  # plain English, safe to show to an agency client
    start_date: date | None = None
    end_date: date | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat() if self.start_date else None
        d["end_date"] = self.end_date.isoformat() if self.end_date else None
        return d


def _fmt_day(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def _fmt_range(start: date, end: date) -> str:
    return _fmt_day(start) if start == end else f"{_fmt_day(start)} to {_fmt_day(end)}"


def _runs(days: list[date]) -> list[list[date]]:
    """Split sorted dates into runs of consecutive calendar days."""
    runs: list[list[date]] = []
    for d in sorted(days):
        if runs and d - runs[-1][-1] == timedelta(days=1):
            runs[-1].append(d)
        else:
            runs.append([d])
    return runs


def _client_filter(client_id: str | None) -> tuple[str, list]:
    return ("and client_id = ?", [client_id]) if client_id else ("", [])


def check_freshness(
    con: duckdb.DuckDBPyConnection, end_date: date, client_id: str | None = None
) -> list[Alert]:
    where, params = _client_filter(client_id)
    cutoff = end_date - timedelta(days=FRESHNESS_LAG_DAYS)
    sources = {
        "Google Ads": ("fct_paid_daily", "and channel = 'google_ads'"),
        "Meta Ads": ("fct_paid_daily", "and channel = 'meta_ads'"),
        "Google Analytics 4": ("fct_web_daily", ""),
        "Search Console": ("fct_seo_daily", ""),
    }
    alerts: list[Alert] = []
    for label, (table, extra) in sources.items():
        rows = con.execute(
            f"select client_id, max(date) from marts.{table} "
            f"where date <= ? {extra} {where} group by 1 order by 1",
            [end_date, *params],
        ).fetchall()
        for cid, latest in rows:
            if latest < cutoff:
                lag = (end_date - latest).days
                alerts.append(
                    Alert(
                        cid,
                        "critical",
                        "freshness",
                        f"{label} data has not updated since {_fmt_day(latest)} "
                        f"({lag} days behind), so recent figures may be incomplete.",
                        latest,
                        end_date,
                    )
                )
    return alerts


def check_reconciliation(
    con: duckdb.DuckDBPyConnection, end_date: date, client_id: str | None = None
) -> list[Alert]:
    where, params = _client_filter(client_id)
    start = end_date - timedelta(days=WINDOW_DAYS - 1)
    rows = con.execute(
        f"""select client_id, channel, date, status, platform_clicks, ga4_sessions
            from marts.fct_paid_vs_ga4_reconciliation
            where date between ? and ? and status in ('warn', 'critical') {where}
            order by client_id, channel, date""",
        [start, end_date, *params],
    ).fetchall()
    grouped: dict[tuple[str, str], list[tuple]] = {}
    for r in rows:
        grouped.setdefault((r[0], r[1]), []).append(r)

    alerts: list[Alert] = []
    for (cid, channel), recs in grouped.items():
        platform, medium = CHANNEL_LABELS.get(channel, (channel, channel))
        by_day = {r[2]: r for r in recs}
        for run in _runs(list(by_day)):
            run_recs = [by_day[d] for d in run]
            clicks = sum(r[4] or 0 for r in run_recs)
            sessions = sum(r[5] or 0 for r in run_recs)
            pct = round(100 * sessions / clicks) if clicks else 0
            severity = max((r[3] for r in run_recs), key=_SEVERITY_RANK.__getitem__)
            n = len(run)
            alerts.append(
                Alert(
                    cid,
                    severity,  # type: ignore[arg-type]
                    "reconciliation",
                    f"{platform} reported {clicks:,.0f} clicks but GA4 recorded "
                    f"{sessions:,.0f} {medium} sessions ({pct}%) on {n} of the last "
                    f"{WINDOW_DAYS} days ({_fmt_range(run[0], run[-1])}). Clicks and sessions "
                    f"normally track closely, so tracking or attribution should be reviewed.",
                    run[0],
                    run[-1],
                )
            )
    return alerts


def check_volume_drop(
    con: duckdb.DuckDBPyConnection, end_date: date, client_id: str | None = None
) -> list[Alert]:
    where, params = _client_filter(client_id)
    first = end_date - timedelta(days=2 * WINDOW_DAYS)
    rows = con.execute(
        f"""select client_id, date, sum(sessions) from marts.fct_web_daily
            where date between ? and ? {where} group by 1, 2 order by 1, 2""",
        [first, end_date, *params],
    ).fetchall()
    series: dict[str, dict[date, float]] = {}
    for cid, d, s in rows:
        series.setdefault(cid, {})[d] = float(s or 0)

    window_start = end_date - timedelta(days=WINDOW_DAYS - 1)
    alerts: list[Alert] = []
    for cid, days in series.items():
        flagged: list[date] = []
        for d, sessions in days.items():
            if d < window_start:
                continue
            prior = [v for pd, v in days.items() if d - timedelta(days=WINDOW_DAYS) <= pd < d]
            if len(prior) < 7:
                continue
            median = statistics.median(prior)
            if median > 0 and sessions < VOLUME_DROP_RATIO * median:
                flagged.append(d)
        for run in _runs(flagged):
            observed = sum(days[d] for d in run)
            typical = sum(
                statistics.median(
                    [v for pd, v in days.items() if d - timedelta(days=WINDOW_DAYS) <= pd < d]
                )
                for d in run
            )
            alerts.append(
                Alert(
                    cid,
                    "critical",
                    "volume_drop",
                    f"Website sessions fell sharply on {_fmt_range(run[0], run[-1])}: "
                    f"{observed:,.0f} recorded versus roughly {typical:,.0f} expected. "
                    f"This pattern usually points to a tracking outage rather than a real "
                    f"drop in visitors.",
                    run[0],
                    run[-1],
                )
            )
    return alerts


def run_checks(
    con: duckdb.DuckDBPyConnection, end_date: date, client_id: str | None = None
) -> list[Alert]:
    """Run all checks; results sorted by client, then severity (critical first), then date."""
    alerts = [
        *check_freshness(con, end_date, client_id),
        *check_reconciliation(con, end_date, client_id),
        *check_volume_drop(con, end_date, client_id),
    ]
    return sorted(
        alerts,
        key=lambda a: (
            a.client_id,
            -_SEVERITY_RANK[a.severity],
            a.check,
            a.start_date or date.min,
        ),
    )
