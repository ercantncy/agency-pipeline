"""The six audit checks, each returning a status, a headline metric and plain-English text.

Scoring: every check has a weight (below). A green check earns its full weight, amber half,
red nothing. Checks that could not be assessed (input file missing) are left out and the score
is renormalised over the remaining weights. Score = round(100 * earned / assessed weight).

| # | Check                                   | Weight | Needs                |
|---|-----------------------------------------|-------:|----------------------|
| 1 | Google Ads clicks vs GA4 sessions       |     25 | Google Ads + GA4     |
| 2 | Meta link clicks vs GA4 sessions        |     15 | Meta + GA4           |
| 3 | UTM hygiene                             |     15 | GA4                  |
| 4 | Conversion agreement                    |     20 | Google Ads + GA4     |
| 5 | Volume drops and outages                |     15 | GA4                  |
| 6 | Suspicious direct / organic share       |     10 | GA4 (+ GSC, + 1)     |

All thresholds are consulting rules of thumb, kept as constants here so they are easy to tune.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

import duckdb

from agency_pipeline import monitoring

Status = Literal["green", "amber", "red", "not_assessed"]

WEIGHTS = {1: 25, 2: 15, 3: 15, 4: 20, 5: 15, 6: 10}
POINTS = {"green": 1.0, "amber": 0.5, "red": 0.0}

# Session / click ratios (GA4 sessions divided by platform clicks).
GOOGLE_RATIO_RED, GOOGLE_RATIO_AMBER, RATIO_TOO_HIGH = 0.50, 0.75, 1.30
META_RATIO_RED, META_RATIO_AMBER = 0.30, 0.50
# GA4 key events divided by platform conversions.
CONV_GREEN = (0.60, 1.60)
CONV_AMBER = (0.35, 2.50)
# UTM hygiene.
NOTSET_RED, NOTSET_AMBER = 0.25, 0.05
LABELS_RED, LABELS_AMBER = 4, 2
# Direct / organic.
DIRECT_RED, DIRECT_AMBER = 0.45, 0.30
ORGANIC_RED, ORGANIC_AMBER, ORGANIC_LOW = 1.50, 1.25, 0.60
LEAK_ORGANIC, LEAK_DIRECT = 1.10, 0.25  # with a failing paid ratio, lower bars apply

PAID_MEDIUMS = (
    "cpc",
    "ppc",
    "paid",
    "paidsearch",
    "paid_social",
    "paidsocial",
    "paid-social",
    "cpm",
)
META_SOURCES = (
    "facebook", "fb", "ig", "instagram", "meta", "facebook.com", "m.facebook.com",
    "l.facebook.com", "lm.facebook.com", "instagram.com", "l.instagram.com",
)  # fmt: skip


@dataclass
class CheckResult:
    number: int
    title: str
    status: Status
    headline: str
    what: str
    why: str
    fix: str
    weight: int
    fix_short: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class AuditInputs:
    con: duckdb.DuckDBPyConnection
    client_id: str
    start: date
    end: date
    has_meta: bool
    has_gsc: bool


def _one(con, sql: str, params: list | None = None):
    row = con.execute(sql, params or []).fetchone()
    return row[0] if row and row[0] is not None else 0


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def _n(x: float) -> str:
    return f"{x:,.0f}"


def _not_assessed(number: int, title: str, missing: str) -> CheckResult:
    return CheckResult(
        number, title, "not_assessed", "Not assessed",
        f"This check needs the {missing} export, which was not provided.",
        "Without it the comparison cannot be made, so it is left out of the score.",
        f"Send the {missing} export and re-run the audit.", WEIGHTS[number],
        fix_short=f"Provide the {missing} export so this check can run.",
    )  # fmt: skip


# --- data access -------------------------------------------------------------------------------


def _clicks(i: AuditInputs, channel: str) -> float:
    return _one(
        i.con,
        "select sum(clicks) from marts.fct_paid_daily where client_id = ? and channel = ?",
        [i.client_id, channel],
    )


def _conversions(i: AuditInputs, channel: str) -> float:
    return _one(
        i.con,
        "select sum(platform_conversions) from marts.fct_paid_daily "
        "where client_id = ? and channel = ?",
        [i.client_id, channel],
    )


_GOOGLE_CPC = "lower(source) = 'google' and lower(medium) in ('cpc', 'ppc', 'paidsearch')"


def _ga4(i: AuditInputs, column: str, where: str) -> float:
    return _one(
        i.con,
        f"select sum({column}) from staging.stg_ga4__traffic_daily where client_id = ? and {where}",
        [i.client_id],
    )


# --- checks ------------------------------------------------------------------------------------


def check_google_ratio(i: AuditInputs) -> CheckResult:
    title = "Google Ads clicks vs GA4 sessions"
    clicks = _clicks(i, "google_ads")
    sessions = _ga4(i, "sessions", _GOOGLE_CPC)
    if clicks <= 0:
        return CheckResult(
            1, title, "red", "No clicks in export",
            "The Google Ads export contains no clicks for the period.",
            "Without ad clicks nothing can be compared to GA4.",
            "Re-export the Campaign report with the Day segment and the right date range.",
            WEIGHTS[1], fix_short="Re-export the Google Ads report for the right dates.",
        )  # fmt: skip
    ratio = sessions / clicks
    headline = f"{_pct(ratio)} of clicks arrive as GA4 sessions"
    details = {"clicks": clicks, "sessions": sessions, "ratio": ratio}
    detail = f"{_n(clicks)} Google Ads clicks versus {_n(sessions)} GA4 google / cpc sessions"
    fix = (
        "Turn on auto-tagging in Google Ads (Account settings), confirm the Google Ads and GA4 "
        "links are active, and make sure no redirect or consent script strips the gclid "
        "parameter before GA4 loads."
    )
    if ratio < GOOGLE_RATIO_RED:
        status: Status = "red"
        what = f"{detail} ({_pct(ratio)}). Healthy accounts typically record 75 to 95%."
        why = (
            "Paid-search sessions, conversions and cost per conversion in GA4 are understated, "
            "and the missing visits are probably being counted as organic or direct."
        )
    elif ratio < GOOGLE_RATIO_AMBER:
        status = "amber"
        what = f"{detail} ({_pct(ratio)}), lower than the 75 to 95% seen in healthy accounts."
        why = "Part of the paid traffic is not being attributed to Google Ads in GA4."
    elif ratio > RATIO_TOO_HIGH:
        status = "amber"
        what = f"{detail} ({_pct(ratio)}): GA4 shows more sessions than there were clicks."
        why = "Double tagging, bot traffic or reloads inflate sessions and distort cost per visit."
        fix = (
            "Look for manual UTM parameters on top of auto-tagging, duplicate GA4 tags and "
            "bot traffic in the google / cpc source."
        )
    else:
        status = "green"
        what = f"{detail} ({_pct(ratio)}), within the normal range."
        why = "Paid-search traffic is attributed correctly, so click and session reports agree."
        fix = "No action needed."
    return CheckResult(
        1, title, status, headline, what, why, fix, WEIGHTS[1], details=details,
        fix_short="Fix Google Ads auto-tagging and the GA4 link so paid clicks are attributed.",
    )  # fmt: skip


def check_meta_ratio(i: AuditInputs) -> CheckResult:
    title = "Meta link clicks vs GA4 sessions"
    if not i.has_meta:
        return _not_assessed(2, title, "Meta Ads")
    clicks = _clicks(i, "meta_ads")
    sessions = _one(
        i.con,
        "select sum(sessions) from marts.fct_web_daily "
        "where client_id = ? and channel_group = 'paid_social'",
        [i.client_id],
    )
    if clicks <= 0:
        return CheckResult(
            2, title, "red", "No link clicks in export",
            "The Meta export contains no link clicks for the period.",
            "Without link clicks nothing can be compared to GA4.",
            "Re-export at campaign level with the Day breakdown and the Link clicks column.",
            WEIGHTS[2], fix_short="Re-export the Meta report with the Link clicks column.",
        )  # fmt: skip
    ratio = sessions / clicks
    detail = f"{_n(clicks)} Meta link clicks versus {_n(sessions)} GA4 paid-social sessions"
    fix = (
        "Add UTM parameters to every Meta ad (utm_source=facebook, utm_medium=paid_social, plus "
        "the campaign), and check the site loads GA4 quickly enough to catch mobile in-app "
        "visits."
    )
    details = {"clicks": clicks, "sessions": sessions, "ratio": ratio}
    if ratio < META_RATIO_RED:
        status: Status = "red"
        what = f"{detail} ({_pct(ratio)}). Around 60 to 80% is typical."
        why = "Most Meta traffic is invisible in GA4, so Meta looks worse (or its sales vanish)."
    elif ratio < META_RATIO_AMBER:
        status = "amber"
        what = f"{detail} ({_pct(ratio)}), below the usual 60 to 80%."
        why = "Part of the Meta traffic is not being attributed to paid social in GA4."
    elif ratio > RATIO_TOO_HIGH:
        status = "amber"
        what = f"{detail} ({_pct(ratio)}): more sessions than link clicks."
        why = "Double tagging or reloads inflate Meta sessions in GA4."
        fix = "Check for duplicate GA4 tags and for manual UTMs that overlap."
    else:
        status = "green"
        what = f"{detail} ({_pct(ratio)}), within the normal range."
        why = "Paid-social traffic reaches GA4 with usable tags."
        fix = "No action needed."
    return CheckResult(
        2, title, status, f"{_pct(ratio)} of link clicks arrive as GA4 sessions",
        what, why, fix, WEIGHTS[2], details=details,
        fix_short="Tag every Meta ad with UTM parameters so GA4 can attribute the visits.",
    )  # fmt: skip


def check_utm_hygiene(i: AuditInputs) -> CheckResult:
    title = "UTM and campaign tagging"
    paid = ",".join(f"'{m}'" for m in PAID_MEDIUMS)
    meta = ",".join(f"'{s}'" for s in META_SOURCES)
    paid_where = f"lower(medium) in ({paid})"
    total = _ga4(i, "sessions", paid_where)
    notset = _ga4(i, "sessions", f"{paid_where} and lower(campaign_name) in ('(not set)', '')")
    share = notset / total if total else 0.0
    labels = i.con.execute(
        f"select source, sum(sessions) from staging.stg_ga4__traffic_daily "
        f"where client_id = ? and lower(source) in ({meta}) and {paid_where} "
        f"group by 1 having sum(sessions) > 0 order by 2 desc",
        [i.client_id],
    ).fetchall()
    meta_cpc = _ga4(i, "sessions", f"lower(source) in ({meta}) and lower(medium) in ('cpc', 'ppc')")
    details = {"paid_sessions": total, "notset_share": share, "meta_labels": [r[0] for r in labels]}
    problems = []
    if len(labels) >= LABELS_AMBER:
        names = ", ".join(r[0] for r in labels)
        problems.append(f"Meta traffic is split over {len(labels)} source labels ({names})")
    if meta_cpc:
        problems.append(f"{_n(meta_cpc)} Meta sessions are tagged medium 'cpc' and count as search")
    if share >= NOTSET_AMBER:
        problems.append(f"{_pct(share)} of paid sessions have no campaign name")
    if share >= NOTSET_RED or len(labels) >= LABELS_RED:
        status: Status = "red"
    elif problems:
        status = "amber"
    else:
        status = "green"
    parts = []
    if labels:
        parts.append(f"{len(labels)} Meta source label{'s' if len(labels) != 1 else ''}")
    parts.append(f"{_pct(share)} of paid sessions untagged")
    headline = "; ".join(parts)
    if problems:
        what = "; ".join(problems) + "."
        why = (
            "Split or missing tags break campaign-level reporting: the same channel appears as "
            "several rows, and untagged paid visits cannot be tied to the spend that caused them."
        )
        fix = (
            "Agree one naming convention (for example utm_source=facebook, utm_medium=paid_social) "
            "and apply it to every ad. Use a GA4 channel-grouping rule to merge the old variants."
        )
    else:
        what = f"Paid traffic is consistently tagged ({_pct(share)} of paid sessions untagged)."
        why = "Consistent tags let every report group paid channels and campaigns correctly."
        fix = "No action needed."
    return CheckResult(
        3, title, status, headline, what, why, fix, WEIGHTS[3], details=details,
        fix_short="Standardise UTM source/medium names and tag every paid ad with a campaign.",
    )  # fmt: skip


def _conv_status(ratio: float) -> Status:
    if CONV_GREEN[0] <= ratio <= CONV_GREEN[1]:
        return "green"
    if CONV_AMBER[0] <= ratio <= CONV_AMBER[1]:
        return "amber"
    return "red"


def check_conversions(i: AuditInputs) -> CheckResult:
    title = "Conversion agreement"
    rows = []  # (label, platform, ga4, ratio, status)
    pairs = [("Google Ads", "google_ads", _GOOGLE_CPC)]
    if i.has_meta:
        pairs.append(("Meta", "meta_ads", "lower(medium) in ('paid', 'paid_social', 'paidsocial')"))
    for label, channel, where in pairs:
        platform = _conversions(i, channel)
        clicks = _clicks(i, channel)
        ga4_events = _ga4(i, "key_events", where)
        if platform <= 0:
            status: Status = "red" if clicks >= 100 else "amber"
            ratio = 0.0
        else:
            ratio = ga4_events / platform
            status = _conv_status(ratio)
        rows.append((label, platform, ga4_events, ratio, status))
    order = {"red": 0, "amber": 1, "green": 2}
    worst = min((r[4] for r in rows), key=order.__getitem__)
    headline = " / ".join(
        f"{r[0]}: {_pct(r[3])}" if r[1] > 0 else f"{r[0]}: no conversions" for r in rows
    )
    lines = [
        f"{label} reported {platform:,.0f} conversions, GA4 recorded {ga4:,.0f} key events "
        f"({_pct(ratio)})"
        if platform > 0
        else f"{label} reported no conversions despite its clicks"
        for label, platform, ga4, ratio, _ in rows
    ]
    what = "; ".join(lines) + ". Agreement within roughly 60 to 160% is normal."
    if worst == "green":
        why = "Platform and GA4 conversion counts agree closely enough to trust cost per result."
        fix = "No action needed."
    else:
        why = (
            "When the platform and GA4 disagree, nobody can say what a lead or sale really costs, "
            "and bidding algorithms optimise on the wrong signal."
        )
        fix = (
            "Check that the same conversion event is imported into Google Ads as in GA4, remove "
            "duplicate or test events, and compare attribution windows before comparing totals."
        )
    return CheckResult(
        4, title, worst, headline, what, why, fix, WEIGHTS[4],
        details={"rows": [list(r) for r in rows]},
        fix_short="Align conversion events and attribution settings between ad platforms and GA4.",
    )  # fmt: skip


def check_volume(i: AuditInputs) -> CheckResult:
    title = "Volume drops and outages"
    flagged: set[date] = set()
    end_d = i.end
    while end_d >= i.start + timedelta(days=7):
        for a in monitoring.check_volume_drop(i.con, end_d, i.client_id):
            d = a.start_date
            while d and a.end_date and d <= a.end_date:
                if i.start <= d <= i.end:
                    flagged.add(d)
                d += timedelta(days=1)
        end_d -= timedelta(days=monitoring.WINDOW_DAYS)
    have = {
        r[0]
        for r in i.con.execute(
            "select distinct date from marts.fct_web_daily where client_id = ?", [i.client_id]
        ).fetchall()
    }
    expected = [i.start + timedelta(days=k) for k in range((i.end - i.start).days + 1)]
    missing = {d for d in expected if d not in have}
    days = sorted(flagged | missing)
    runs = monitoring._runs(days)
    longest = max((len(r) for r in runs), default=0)
    if not days:
        return CheckResult(
            5, title, "green", "No outages found",
            "Daily GA4 sessions stayed within a normal range for the whole period.",
            "A steady baseline means trend reports reflect real visitor behaviour.",
            "No action needed.", WEIGHTS[5], fix_short="",
            details={"days": []},
        )  # fmt: skip
    status: Status = "red" if (longest >= 2 or len(days) >= 3) else "amber"
    span = "; ".join(monitoring._fmt_range(r[0], r[-1]) for r in runs)
    ads_clicks = _one(
        i.con,
        "select sum(clicks) from marts.fct_paid_daily where client_id = ? and date in "
        f"({','.join(['?'] * len(days))})",
        [i.client_id, *days],
    )
    extra = (
        f" Ad platforms still recorded {_n(ads_clicks)} clicks on those days, so the visitors "
        f"were there; GA4 simply did not see them."
        if ads_clicks
        else ""
    )
    return CheckResult(
        5, title, status, f"{len(days)} day{'s' if len(days) != 1 else ''} of missing data",
        f"GA4 sessions collapsed or were missing on {span}.{extra}",
        "Gaps like this look like a traffic crash in reports and make those days unusable for "
        "conversion rates and cost per result.",
        "Find what changed on those dates (tag manager publish, consent banner, site release), "
        "fix it, and set up an alert so the next outage is caught within a day.",
        WEIGHTS[5], details={"days": [d.isoformat() for d in days]},
        fix_short="Fix the tracking gap and add an automatic alert for sudden session drops.",
    )  # fmt: skip


def check_direct_organic(i: AuditInputs, paid_ratio_ok: bool | None) -> CheckResult:
    """`paid_ratio_ok`: None unknown, False when check 1 failed (leakage plausible)."""
    title = "Suspicious direct and organic traffic"
    total = _one(
        i.con, "select sum(sessions) from marts.fct_web_daily where client_id = ?", [i.client_id]
    )
    group = {
        g: _one(
            i.con,
            "select sum(sessions) from marts.fct_web_daily "
            "where client_id = ? and channel_group = ?",
            [i.client_id, g],
        )
        for g in ("direct", "organic_search")
    }
    direct_share = group["direct"] / total if total else 0.0
    gsc_clicks = (
        _one(
            i.con,
            "select sum(clicks) from staging.stg_gsc__search_daily where client_id = ?",
            [i.client_id],
        )
        if i.has_gsc
        else 0
    )
    org_ratio = group["organic_search"] / gsc_clicks if gsc_clicks else None
    leak = paid_ratio_ok is False
    details = {"direct_share": direct_share, "organic_vs_gsc": org_ratio}

    reasons: list[str] = []
    status: Status = "green"

    def bump(level: Status, reason: str) -> None:
        nonlocal status
        reasons.append(reason)
        if {"green": 0, "amber": 1, "red": 2}[level] > {"green": 0, "amber": 1, "red": 2}[status]:
            status = level

    suffix = " while paid clicks are going missing" if leak else ""
    if org_ratio is not None:
        text = f"GA4 organic sessions are {org_ratio:.2f}x the clicks Search Console reports"
        if org_ratio > ORGANIC_RED:
            bump("red", text)
        elif org_ratio > ORGANIC_AMBER:
            bump("amber", text)
        elif leak and org_ratio >= LEAK_ORGANIC:
            bump("red", text + suffix)
        elif org_ratio < ORGANIC_LOW:
            bump("amber", f"GA4 organic sessions are only {org_ratio:.2f}x Search Console clicks")
    direct_text = f"direct is {_pct(direct_share)} of all sessions"
    if direct_share >= DIRECT_RED:
        bump("red", direct_text)
    elif leak and direct_share >= LEAK_DIRECT:
        bump("red", direct_text + ("" if reasons else suffix))
    elif direct_share >= DIRECT_AMBER:
        bump("amber", direct_text)
    if not i.has_gsc and status == "red":
        status = "amber"  # without Search Console the evidence is weaker
    headline = f"Direct {_pct(direct_share)} of sessions" + (
        f"; organic {org_ratio:.2f}x GSC clicks" if org_ratio is not None else ""
    )
    if reasons:
        joined = "; ".join(reasons)
        what = joined[0].upper() + joined[1:] + "."
        if not i.has_gsc:
            what += " Search Console data was not provided, so organic could not be cross-checked."
        why = (
            "Visits that lose their source fall into direct or organic. That inflates those "
            "channels and makes paid media look weaker than it is."
        )
        fix = (
            "Fix the paid-traffic tagging first (see the checks above), then re-check direct and "
            "organic. Also look for missing UTM tags on email and social links."
        )
    else:
        what = (
            f"Direct is {_pct(direct_share)} of sessions"
            + (
                f" and organic sessions match Search Console clicks ({org_ratio:.2f}x)"
                if org_ratio is not None
                else ""
            )
            + "."
        )
        if not i.has_gsc:
            what += " Search Console data was not provided, so organic was not cross-checked."
        why = "Direct and organic look proportionate, so paid traffic is not leaking into them."
        fix = "No action needed."
    return CheckResult(
        6, title, status, headline, what, why, fix, WEIGHTS[6], details=details,
        fix_short="Recover traffic hiding in direct and organic by fixing paid tagging.",
    )  # fmt: skip


def run_all(i: AuditInputs) -> list[CheckResult]:
    first = check_google_ratio(i)
    results = [
        first,
        check_meta_ratio(i),
        check_utm_hygiene(i),
        check_conversions(i),
        check_volume(i),
        check_direct_organic(i, None if first.status == "green" else first.status != "red"),
    ]
    return results


def score(results: list[CheckResult]) -> int | None:
    assessed = [r for r in results if r.status != "not_assessed"]
    total = sum(r.weight for r in assessed)
    if not total:
        return None
    return round(100 * sum(r.weight * POINTS[r.status] for r in assessed) / total)


def top_fixes(results: list[CheckResult], limit: int = 3) -> list[CheckResult]:
    """Non-green checks, red before amber, then by weight."""
    rank = {"red": 0, "amber": 1}
    open_items = [r for r in results if r.status in rank]
    return sorted(open_items, key=lambda r: (rank[r.status], -r.weight))[:limit]
