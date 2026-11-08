"""Build the self-contained, white-labelled monthly HTML report for one client."""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

from agency_pipeline.commentary import generate_commentary
from agency_pipeline.monitoring import run_checks

TEMPLATE_DIR = Path(__file__).parent / "templates"
SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€"}
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
MUTED = "#64748b"
GRID = "#e2e8f0"
# Secondary series colours; the agency colour is always the first/primary series.
PALETTE = ["#0d9488", "#f59e0b", "#7c3aed", "#64748b", "#db2777"]
CHANNEL_LABELS = {"google_ads": "Google Ads", "meta_ads": "Meta Ads", "total_paid": "All paid"}
GROUP_LABELS = {
    "paid_search": "Paid search",
    "paid_social": "Paid social",
    "organic_search": "Organic search",
    "direct": "Direct",
    "email": "Email",
    "referral": "Referral",
    "other": "Other",
}
# Reconciliation thresholds (session / click ratio) mirroring the dbt vars.
THRESHOLDS = {"google_ads": (0.50, 0.30), "meta_ads": (0.40, 0.20)}
CHECK_HELP = {
    "reconciliation": (
        "Ad clicks and website sessions disagree",
        "Some clicks recorded by the ad platform never show up as sessions in Google Analytics. "
        "Typical causes are broken auto-tagging or missing UTM parameters, so paid traffic is "
        "credited to organic or direct and the ad results look worse than they really are.",
    ),
    "volume_drop": (
        "Website tracking stopped recording traffic",
        "Analytics recorded far fewer sessions than normal. This usually means the tracking "
        "tag was removed or broken, so those days are missing from the website numbers.",
    ),
    "freshness": (
        "A data source is out of date",
        "The latest data from one of the connected platforms is older than expected, so the "
        "most recent days may be incomplete.",
    ),
}


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


class _Fmt:
    def __init__(self, currency: str):
        self.sym = SYMBOLS.get(currency, currency + " ")

    def money(self, v, dec: int | None = None) -> str:
        v = _num(v)
        if v is None:
            return "–"
        if dec is None:
            dec = 0 if abs(v) >= 1000 else 2
        return f"{self.sym}{v:,.{dec}f}"

    @staticmethod
    def int(v) -> str:
        v = _num(v)
        return "–" if v is None else f"{v:,.0f}"

    @staticmethod
    def pct(v, dec: int = 1) -> str:
        v = _num(v)
        return "–" if v is None else f"{v * 100:.{dec}f}%"

    @staticmethod
    def ratio(v) -> str:
        v = _num(v)
        return "–" if v is None else f"{v:.2f}x"


def _delta(pct, higher_is_better: bool | None) -> dict | None:
    """MoM chip. higher_is_better=None means neutral (e.g. spend)."""
    pct = _num(pct)
    if pct is None:
        return None
    if abs(pct) < 0.0005:
        return {"text": "0.0%", "arrow": "▬", "cls": "flat"}
    up = pct > 0
    if higher_is_better is None:
        cls = "flat"
    else:
        cls = "good" if up == higher_is_better else "bad"
    return {"text": f"{abs(pct) * 100:.1f}%", "arrow": "▲" if up else "▼", "cls": cls}


def _mom(cur, prev) -> float | None:
    cur, prev = _num(cur), _num(prev)
    if cur is None or not prev:
        return None
    return cur / prev - 1


def _style(fig: go.Figure, height: int = 280, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 48, "r": 16, "t": 16, "b": 36},
        font={"family": FONT, "size": 12, "color": "#334155"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend={"orientation": "h", "y": 1.12, "x": 0, "font": {"size": 11}},
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont={"color": MUTED})
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont={"color": MUTED})
    return fig


class _Charts:
    """Renders figures to HTML fragments; Plotly JS is inlined with the first one only."""

    def __init__(self) -> None:
        self._first = True

    def html(self, fig: go.Figure) -> str:
        out = fig.to_html(
            full_html=False,
            include_plotlyjs=True if self._first else False,
            config={"displayModeBar": False, "responsive": True},
        )
        self._first = False
        return out


def _q(con, sql: str, params: list) -> pd.DataFrame:
    return con.execute(sql, params).df()


def _month_metrics(con, client_id: str, month: date) -> pd.DataFrame:
    return _q(
        con,
        "select * from marts.rpt_client_monthly where client_id = ? and month = ?",
        [client_id, month],
    )


def _kpis(con, client_id: str, month: date, prev: date, fmt: _Fmt) -> list[dict]:
    paid = _month_metrics(con, client_id, month)
    tot = paid[paid.channel == "total_paid"]
    tiles: list[dict] = []
    if not tot.empty:
        r = tot.iloc[0]
        tiles += [
            {
                "label": "Ad spend",
                "value": fmt.money(r.spend),
                "delta": _delta(r.spend_mom_pct, None),
            },
            {
                "label": "Conversions",
                "value": fmt.int(r.conversions),
                "delta": _delta(r.conversions_mom_pct, True),
            },
            {
                "label": "Cost per conversion",
                "value": fmt.money(r.cpa, 2),
                "delta": _delta(r.cpa_mom_pct, False),
            },
        ]
        if _num(r.conversion_value) and r.conversion_value > 0:
            tiles.append(
                {
                    "label": "Return on ad spend",
                    "value": fmt.ratio(r.roas),
                    "delta": _delta(r.roas_mom_pct, True),
                }
            )
    nxt = (month + timedelta(days=32)).replace(day=1)
    web = _q(
        con,
        """select date_trunc('month', date) m, sum(sessions) s from marts.fct_web_daily
           where client_id = ? and date >= ? and date < ? group by 1""",
        [client_id, prev, nxt],
    )
    ws = {pd.Timestamp(r.m).date(): r.s for r in web.itertuples()}
    if month in ws:
        tiles.append(
            {
                "label": "Website sessions",
                "value": fmt.int(ws[month]),
                "delta": _delta(_mom(ws[month], ws.get(prev)), True),
            }
        )
    seo = _q(
        con,
        """select date_trunc('month', date) m, sum(clicks) c from marts.fct_seo_daily
           where client_id = ? and date >= ? and date < ? group by 1""",
        [client_id, prev, nxt],
    )
    sc = {pd.Timestamp(r.m).date(): r.c for r in seo.itertuples()}
    if month in sc:
        tiles.append(
            {
                "label": "Organic search clicks",
                "value": fmt.int(sc[month]),
                "delta": _delta(_mom(sc[month], sc.get(prev)), True),
            }
        )
    return tiles


def _paid_charts(con, client_id, month, nxt, accent, charts: _Charts) -> list[dict]:
    df = _q(
        con,
        """select date, channel, sum(spend) spend, sum(platform_conversions) conv
           from marts.fct_paid_daily where client_id = ? and date >= ? and date < ?
           group by 1, 2 order by 1""",
        [client_id, month, nxt],
    )
    if df.empty:
        return []
    colors = {"google_ads": accent, "meta_ads": PALETTE[0]}
    spend = go.Figure()
    conv = go.Figure()
    for ch, g in df.groupby("channel"):
        for fig, col in ((spend, "spend"), (conv, "conv")):
            fig.add_bar(
                x=g["date"],
                y=g[col],
                name=CHANNEL_LABELS[ch],
                marker_color=colors.get(ch, MUTED),
                hovertemplate="%{y:,.0f}",
            )
    spend.update_layout(barmode="stack")
    conv.update_layout(barmode="stack")
    day = df.groupby("date")[["spend", "conv"]].sum()
    cpa = (day.spend / day.conv.where(day.conv > 0)).rolling(7, min_periods=3).mean()
    cpa_fig = go.Figure(
        go.Scatter(
            x=cpa.index,
            y=cpa.values,
            mode="lines",
            line={"color": accent, "width": 2.5},
            name="Cost per conversion",
            hovertemplate="%{y:,.2f}",
        )
    )
    return [
        {
            "title": "Daily ad spend",
            "sub": "Stacked by platform",
            "html": charts.html(_style(spend)),
        },
        {
            "title": "Daily conversions",
            "sub": "As reported by the ad platforms",
            "html": charts.html(_style(conv)),
        },
        {
            "title": "Cost per conversion",
            "sub": "7-day rolling average; lower is better",
            "html": charts.html(_style(cpa_fig, legend=False)),
            "wide": True,
        },
    ]


def _campaign_table(con, client_id, channel, month, nxt, fmt: _Fmt) -> dict | None:
    df = _q(
        con,
        """select campaign_name, sum(spend) spend, sum(impressions) impr, sum(clicks) clicks,
                  sum(platform_conversions) conv, sum(platform_conversion_value) val
           from marts.fct_paid_daily
           where client_id = ? and channel = ? and date >= ? and date < ?
           group by 1 order by spend desc""",
        [client_id, channel, month, nxt],
    )
    if df.empty:
        return None
    has_value = df.val.sum() > 0

    def row(name, r) -> dict:
        cells = [
            name,
            fmt.money(r.spend),
            fmt.int(r.impr),
            fmt.int(r.clicks),
            fmt.pct(r.clicks / r.impr if r.impr else None, 2),
            fmt.int(r.conv),
            fmt.money(r.spend / r.conv if r.conv else None, 2),
        ]
        if has_value:
            cells.append(fmt.ratio(r.val / r.spend if r.spend else None))
        return {"cells": cells}

    rows = [row(r.campaign_name, r) for r in df.itertuples()]
    total = df[["spend", "impr", "clicks", "conv", "val"]].sum()
    rows.append({**row("Total", total), "total": True})
    head = ["Campaign", "Spend", "Impressions", "Clicks", "CTR", "Conversions", "Cost / conv."]
    if has_value:
        head.append("ROAS")
    return {"head": head, "rows": rows}


def _web(con, client_id, month, nxt, prev, accent, fmt: _Fmt, charts: _Charts) -> dict | None:
    df = _q(
        con,
        """select channel_group, date_trunc('month', date) m, sum(sessions) sessions,
                  sum(engaged_sessions) engaged, sum(key_events) ke, sum(revenue) rev
           from marts.fct_web_daily where client_id = ? and date >= ? and date < ?
           group by 1, 2""",
        [client_id, prev, nxt],
    )
    cur = df[df.m == pd.Timestamp(month)].sort_values("sessions", ascending=False)
    if cur.empty:
        return None
    old = df[df.m == pd.Timestamp(prev)].set_index("channel_group").sessions
    has_rev = cur.rev.sum() > 0
    rows = []
    for r in cur.itertuples():
        d = _delta(_mom(r.sessions, old.get(r.channel_group)), True)
        cells = [
            GROUP_LABELS.get(r.channel_group, r.channel_group),
            fmt.int(r.sessions),
            fmt.pct(r.engaged / r.sessions if r.sessions else None, 0),
            fmt.int(r.ke),
        ]
        if has_rev:
            cells.append(fmt.money(r.rev))
        cells.append(f"{d['arrow']} {d['text']}" if d else "–")
        rows.append({"cells": cells})
    head = ["Channel", "Sessions", "Engaged", "Key events"]
    if has_rev:
        head.append("Revenue")
    head.append("Sessions vs last month")
    top = cur.sort_values("sessions")
    fig = go.Figure(
        go.Bar(
            x=top.sessions,
            y=[GROUP_LABELS.get(g, g) for g in top.channel_group],
            orientation="h",
            marker_color=accent,
            hovertemplate="%{x:,.0f} sessions",
        )
    )
    _style(fig, height=300, legend=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(margin={"l": 100, "r": 16, "t": 8, "b": 32}, hovermode="closest")
    return {"head": head, "rows": rows, "chart": charts.html(fig)}


def _seo(con, client_id, month, nxt, prev, accent, fmt: _Fmt, charts: _Charts) -> dict | None:
    q = _q(
        con,
        """select month, query, clicks, impressions, ctr, avg_position
           from marts.fct_seo_query_monthly where client_id = ? and month in (?, ?)""",
        [client_id, month, prev],
    )
    cur = q[q.month == pd.Timestamp(month)].sort_values("clicks", ascending=False).head(10)
    if cur.empty:
        return None
    old = q[q.month == pd.Timestamp(prev)].set_index("query").avg_position
    rows = []
    for r in cur.itertuples():
        p = old.get(r.query)
        change = "–"
        if p is not None and not math.isnan(p):
            diff = p - r.avg_position  # positive = moved up the results
            if abs(diff) >= 0.1:
                change = f"{'▲' if diff > 0 else '▼'} {abs(diff):.1f}"
        rows.append(
            {
                "cells": [
                    r.query,
                    fmt.int(r.clicks),
                    fmt.int(r.impressions),
                    fmt.pct(r.ctr, 1),
                    f"{r.avg_position:.1f}",
                    change,
                ]
            }
        )
    daily = _q(
        con,
        """select date, avg_position, clicks from marts.fct_seo_daily
           where client_id = ? and date >= ? and date < ? order by date""",
        [client_id, month, nxt],
    )
    pos = daily.avg_position.rolling(7, min_periods=3).mean()
    fig = go.Figure(
        go.Scatter(
            x=daily.date,
            y=pos,
            mode="lines",
            line={"color": accent, "width": 2.5},
            name="Average position",
            hovertemplate="%{y:.1f}",
        )
    )
    _style(fig, legend=False)
    fig.update_yaxes(autorange="reversed", title={"text": "Position (1 = top)"})
    clicks = go.Figure(
        go.Bar(
            x=daily.date,
            y=daily.clicks,
            marker_color=PALETTE[0],
            name="Clicks",
            hovertemplate="%{y:,.0f}",
        )
    )
    _style(clicks, legend=False)
    return {
        "head": [
            "Search query",
            "Clicks",
            "Impressions",
            "CTR",
            "Avg. position",
            "Position vs last month",
        ],
        "rows": rows,
        "charts": [
            {
                "title": "Average search position",
                "sub": "7-day rolling; higher on the chart is better",
                "html": charts.html(fig),
            },
            {
                "title": "Daily organic clicks",
                "sub": "From Google Search Console",
                "html": charts.html(clicks),
            },
        ],
    }


def _recon_charts(con, client_id, month, nxt, accent, charts: _Charts) -> list[dict]:
    df = _q(
        con,
        """select date, channel, session_click_ratio r from marts.fct_paid_vs_ga4_reconciliation
           where client_id = ? and date >= ? and date < ? order by date""",
        [client_id, month, nxt],
    )
    out = []
    for ch, color in (("google_ads", accent), ("meta_ads", PALETTE[0])):
        g = df[df.channel == ch]
        if g.empty or g.r.isna().all():
            continue
        warn, crit = THRESHOLDS[ch]
        fig = go.Figure(
            go.Scatter(
                x=g.date,
                y=g.r,
                mode="lines",
                line={"color": color, "width": 2.5},
                name="Sessions per click",
                hovertemplate="%{y:.0%}",
            )
        )
        fig.add_hline(
            y=warn,
            line={"color": "#f59e0b", "dash": "dash", "width": 1.5},
            annotation_text=f"Warning below {warn:.0%}",
            annotation_position="top left",
            annotation_font={"size": 11, "color": "#b45309"},
        )
        fig.add_hline(
            y=crit,
            line={"color": "#dc2626", "dash": "dash", "width": 1.5},
            annotation_text=f"Critical below {crit:.0%}",
            annotation_position="bottom left",
            annotation_font={"size": 11, "color": "#b91c1c"},
        )
        _style(fig, legend=False)
        top = max(1.1, float(g.r.max()) * 1.1)
        fig.update_yaxes(tickformat=".0%", range=[0, min(top, 1.6)])
        out.append(
            {
                "title": f"{CHANNEL_LABELS[ch]}: website sessions per ad click",
                "sub": "A healthy setup lands above the dashed lines",
                "html": charts.html(fig),
            }
        )
    return out


def _alert_view(a) -> dict:
    title, why = CHECK_HELP.get(
        a.check, (a.check.replace("_", " ").capitalize(), "This check flagged unusual data.")
    )
    s, e = a.start_date, a.end_date or a.start_date
    if s is None:
        period = "Current"
    else:
        period = f"{s:%b} {s.day}" if s == e else f"{s:%b} {s.day} to {e:%b} {e.day}"
    return {
        "severity": a.severity,
        "title": title,
        "message": a.message,
        "why": why,
        "period": period,
    }


def build_report(
    con,
    client_id: str,
    month: date,
    out_dir: str | Path,
    *,
    use_llm: bool | None = None,
) -> Path:
    """Render output/reports/<client_id>/<YYYY-MM>.html and return its path."""
    month = month.replace(day=1)
    nxt = (month + timedelta(days=32)).replace(day=1)
    prev = (month - timedelta(days=1)).replace(day=1)
    month_end = nxt - timedelta(days=1)

    dim = _q(con, "select * from marts.dim_client where client_id = ?", [client_id])
    if dim.empty:
        raise ValueError(f"unknown client: {client_id}")
    client = dim.iloc[0]
    accent = client.agency_primary_color
    fmt = _Fmt(client.currency)
    charts = _Charts()

    alerts = run_checks(con, month_end, client_id)
    commentary = generate_commentary(con, client_id, month, alerts, use_llm=use_llm)

    kpis = _kpis(con, client_id, month, prev, fmt)
    paid_charts = _paid_charts(con, client_id, month, nxt, accent, charts)
    tables = {
        ch: _campaign_table(con, client_id, ch, month, nxt, fmt)
        for ch in ("google_ads", "meta_ads")
    }
    web = _web(con, client_id, month, nxt, prev, accent, fmt, charts)
    seo = _seo(con, client_id, month, nxt, prev, accent, fmt, charts)
    recon = _recon_charts(con, client_id, month, nxt, accent, charts)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape(["j2"]))
    html = env.get_template("report.html.j2").render(
        client=client,
        accent=accent,
        css=(TEMPLATE_DIR / "report.css").read_text(),
        month_label=f"{month:%B %Y}",
        prev_label=f"{prev:%B}",
        kpis=kpis,
        commentary=[p.strip() for p in commentary.text.split("\n\n") if p.strip()],
        paid_charts=paid_charts,
        tables=tables,
        web=web,
        seo=seo,
        recon=recon,
        alerts=[_alert_view(a) for a in alerts],
    )
    out = Path(out_dir) / "reports" / client_id / f"{month:%Y-%m}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
