"""Monthly client commentary: LLM draft if an API key is set, else a deterministic template."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Literal

import duckdb

from agency_pipeline.monitoring import Alert

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5-5"
CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€"}
CHANNEL_LABELS = {"google_ads": "Google Ads", "meta_ads": "Meta Ads", "total_paid": "Paid media"}

SYSTEM_PROMPT = (
    "You write the monthly performance commentary for a marketing agency's client. "
    "Write about 120 words of plain English in one or two short paragraphs, with no headings, "
    "bullet points or markdown. Use ONLY numbers that appear in the JSON provided and never invent "
    "or estimate figures. Mention month-over-month movement where available. If the JSON lists "
    "data-quality issues, mention them tactfully and briefly, without blaming anyone. "
    "Be factual and calm; do not over-promise."
)


@dataclass(frozen=True)
class Commentary:
    text: str
    source: Literal["llm", "template"]


def _num(v):
    return None if v is None else round(float(v), 4)


def _alert_dict(a: Alert) -> dict:
    return {
        "check": a.check,
        "severity": a.severity,
        "message": a.message,
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "end_date": a.end_date.isoformat() if a.end_date else None,
    }


def build_month_context(
    con: duckdb.DuckDBPyConnection,
    client_id: str,
    month: date,
    alerts: list[Alert] | None = None,
) -> dict:
    """Compact JSON-able view of one client-month: KPIs, MoM deltas, data-quality alerts."""
    month = month.replace(day=1)
    client = con.execute(
        "select client_name, currency from marts.dim_client where client_id = ?", [client_id]
    ).fetchone()
    if client is None:
        raise ValueError(f"unknown client: {client_id}")
    rows = con.execute(
        """select channel, spend, clicks, conversions, conversion_value, cpa, roas, ctr,
                  spend_mom_pct, conversions_mom_pct, cpa_mom_pct, roas_mom_pct
           from marts.rpt_client_monthly where client_id = ? and month = ? order by channel""",
        [client_id, month],
    ).fetchall()
    keys = ["spend", "clicks", "conversions", "conversion_value", "cpa", "roas", "ctr"]
    mom_keys = ["spend", "conversions", "cpa", "roas"]
    channels = {}
    for r in rows:
        entry = {k: _num(v) for k, v in zip(keys, r[1:8], strict=True)}
        entry["mom"] = {k: _num(v) for k, v in zip(mom_keys, r[8:12], strict=True)}
        channels[r[0]] = entry
    return {
        "client": client[0],
        "currency": client[1],
        "month": month.strftime("%B %Y"),
        "channels": channels,
        "data_quality_issues": [_alert_dict(a) for a in (alerts or [])],
    }


def _money(v: float, symbol: str) -> str:
    return f"{symbol}{v:,.0f}"


def _money2(v: float, symbol: str) -> str:
    return f"{symbol}{v:,.2f}"


def _move(mom: float | None, noun: str) -> str:
    if mom is None:
        return ""
    if abs(mom) < 0.005:
        return ", flat on last month"
    direction = "up" if mom > 0 else "down"
    return f", {direction} {abs(mom) * 100:.1f}% on last month"


def _template(ctx: dict) -> str:
    sym = CURRENCY_SYMBOLS.get(ctx["currency"], ctx["currency"] + " ")
    total = ctx["channels"].get("total_paid")
    if not total or not total.get("spend"):
        return f"No paid media activity was recorded for {ctx['client']} in {ctx['month']}."
    mom = total["mom"]
    parts = [
        f"In {ctx['month']}, paid media spend for {ctx['client']} was "
        f"{_money(total['spend'], sym)}{_move(mom['spend'], 'spend')}, "
        f"generating {total['conversions']:,.0f} conversions"
        f"{_move(mom['conversions'], 'conversions')}."
    ]
    cost = f"Cost per acquisition was {_money2(total['cpa'], sym)}" if total.get("cpa") else None
    if cost:
        cpa_mom = mom["cpa"]
        if cpa_mom is None or abs(cpa_mom) < 0.005:
            cost += "."
        else:
            word = "an improvement" if cpa_mom < 0 else "a rise"
            direction = "down" if cpa_mom < 0 else "up"
            cost += f", {direction} {abs(cpa_mom) * 100:.1f}% ({word} on last month)."
        if total.get("roas"):
            cost += f" Return on ad spend was {total['roas']:.2f}x"
            r = mom["roas"]
            if r is not None and abs(r) >= 0.005:
                cost += f", {'up' if r > 0 else 'down'} {abs(r) * 100:.1f}% on last month"
            cost += "."
        parts.append(cost)

    platforms = {
        k: v for k, v in ctx["channels"].items() if k != "total_paid" and v.get("conversions")
    }
    if len(platforms) > 1:
        best_key = min(platforms, key=lambda k: platforms[k]["cpa"] or float("inf"))
        best = platforms[best_key]
        if best.get("cpa"):
            parts.append(
                f"{CHANNEL_LABELS[best_key]} was the most efficient channel, delivering "
                f"{best['conversions']:,.0f} conversions at {_money2(best['cpa'], sym)} each."
            )

    issues = ctx.get("data_quality_issues") or []
    if issues:
        kinds = {i["check"] for i in issues}
        if "volume_drop" in kinds or "freshness" in kinds:
            parts.append(
                "Please note that some website tracking data was incomplete during part of the "
                "period, so web figures may be understated; we are looking into it."
            )
        else:
            parts.append(
                "Please note that website analytics recorded noticeably fewer visits than the ad "
                "platforms reported clicks, so conversion tracking is being reviewed to make sure "
                "results are fully captured."
            )
    return " ".join(parts)


def _llm(ctx: dict) -> str:
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "Write the commentary from this data:\n" + json.dumps(ctx, indent=2),
            }
        ],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "text") == "text").strip()
    if not text:
        raise ValueError("empty response from model")
    return text


def generate_commentary(
    con: duckdb.DuckDBPyConnection,
    client_id: str,
    month: date,
    alerts: list[Alert],
    use_llm: bool | None = None,
) -> Commentary:
    ctx = build_month_context(
        con, client_id, month, [a for a in alerts if a.client_id == client_id]
    )
    if use_llm is None:
        use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_llm:
        try:
            text = _llm(ctx)
        except Exception as exc:  # any API/network/config failure must not break reporting
            logger.warning("LLM commentary failed (%s); using template instead.", exc)
        else:
            logger.info("Commentary is an LLM draft — review before sending (%s)", client_id)
            return Commentary(text, "llm")
    return Commentary(_template(ctx), "template")
