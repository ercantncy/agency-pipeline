"""Render the one-page A4 audit scorecard (self-contained HTML, no external requests)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from agency_pipeline.audit.checks import top_fixes
from agency_pipeline.audit.runner import AuditResult

TEMPLATE_DIR = Path(__file__).parent / "templates"
PILLS = {
    "green": ("Healthy", "&#10003;"),
    "amber": ("Needs attention", "&#9650;"),
    "red": ("Critical", "&#10005;"),
    "not_assessed": ("Not assessed", "&ndash;"),
}
CONTACT = "hello@example.com"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "client"


def _verdict(score: int | None) -> tuple[str, str]:
    if score is None:
        return "No score", "flat"
    if score >= 85:
        return "Healthy", "green"
    if score >= 60:
        return "Needs attention", "amber"
    return "Critical issues", "red"


def _period(result: AuditResult) -> str:
    s, e = result.period_start, result.period_end
    if s.year == e.year:
        return f"{s.strftime('%b')} {s.day} to {e.strftime('%b')} {e.day}, {e.year}"
    return f"{s.strftime('%b')} {s.day}, {s.year} to {e.strftime('%b')} {e.day}, {e.year}"


def render_scorecard(
    result: AuditResult, consultant: str = "Ercan Tuncay", today: date | None = None
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    verdict, tone = _verdict(result.score)
    skipped = [
        n for n, k in (("Meta Ads", "meta"), ("Search Console", "gsc")) if not result.inputs[k]
    ]
    provided = ["Google Ads", "GA4"] + [
        n for n, k in (("Meta Ads", "meta"), ("Search Console", "gsc")) if result.inputs[k]
    ]
    return env.get_template("scorecard.html.j2").render(
        r=result,
        consultant=consultant,
        date_text=(today or date.today()).strftime("%B %d, %Y").replace(" 0", " "),
        period=_period(result),
        verdict=verdict,
        tone=tone,
        pills=PILLS,
        fixes=top_fixes(result.checks),
        provided=provided,
        skipped=skipped,
        contact=CONTACT,
    )


def write_scorecard(
    result: AuditResult, out: Path, consultant: str = "Ercan Tuncay", today: date | None = None
) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_scorecard(result, consultant, today), encoding="utf-8")
    return out
