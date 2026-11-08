# ruff: noqa: E501  (inline HTML/CSS template)
"""Static demo site: an index page plus the generated client reports, ready for GitHub Pages."""

from __future__ import annotations

import html
import shutil
from datetime import date
from pathlib import Path

from agency_pipeline.config import load_clients

REPO_URL = "https://github.com/ercantncy/agency-pipeline"

SCENARIO_BLURBS = {
    "healthy": (
        "Clean month",
        "Ad clicks and analytics sessions reconcile. Every check passes and the report shows the green state.",
    ),
    "broken_autotagging": (
        "Broken auto-tagging",
        "Google Ads reports 1,759 clicks, GA4 records 309 paid-search sessions. "
        "The pipeline flags it as critical and explains it in plain English.",
    ),
    "tracking_outage": (
        "Tracking outage",
        "GA4 records almost nothing for three days. The volume-drop check catches it, "
        "so the dip is reported as missing data, not a traffic collapse.",
    ),
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agency Reporting Pipeline: live demo</title>
<style>
  :root {{ --fg:#0f172a; --muted:#475569; --line:#e2e8f0; --bg:#f8fafc; --card:#fff; --accent:#2f6feb; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --fg:#e2e8f0; --muted:#94a3b8; --line:#334155; --bg:#0b1120; --card:#111827; --accent:#6ea0ff; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  main {{ max-width:960px; margin:0 auto; padding:48px 16px 64px; }}
  h1 {{ font-size:2rem; line-height:1.2; margin:0 0 12px; }}
  .lead {{ color:var(--muted); font-size:1.1rem; max-width:720px; margin:0 0 32px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }}
  a.card {{ display:block; background:var(--card); border:1px solid var(--line); border-radius:12px;
            padding:20px; color:inherit; text-decoration:none; transition:border-color .15s; }}
  a.card:hover {{ border-color:var(--accent); }}
  .tag {{ font-size:.75rem; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); font-weight:600; }}
  .card h2 {{ font-size:1.15rem; margin:6px 0 8px; }}
  .card p {{ margin:0; color:var(--muted); font-size:.95rem; }}
  .links {{ margin-top:40px; display:flex; flex-wrap:wrap; gap:12px 24px; }}
  .links a {{ color:var(--accent); }}
  footer {{ margin-top:48px; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<main>
  <h1>Agency Reporting Pipeline</h1>
  <p class="lead">Google Ads, Meta Ads, GA4 and Search Console in one warehouse, tested models,
  monitoring that catches broken tracking, and a white-label report per client.
  Below are the {month_label} reports for three synthetic clients, each built to show one scenario.</p>
  <div class="grid">
{cards}
  </div>
  <div class="links">
    <a href="{repo}">Source code on GitHub</a>
    <a href="{repo}/blob/master/docs/explainer-clicks-vs-sessions.md">Why clicks and sessions don't match</a>
    <a href="{repo}/blob/master/docs/offer-one-pager.md">Services and pricing</a>
  </div>
  <footer>All data is synthetic and generated deterministically. Built {built}.</footer>
</main>
</body>
</html>
"""

CARD = """    <a class="card" href="{href}">
      <div class="tag">{tag}</div>
      <h2>{name}</h2>
      <p>{blurb}</p>
    </a>"""


def build_site(reports_dir: Path, site_dir: Path, month: date) -> Path:
    """Copy the month's reports into site_dir/reports and write site_dir/index.html."""
    if site_dir.exists():
        shutil.rmtree(site_dir)
    (site_dir / "reports").mkdir(parents=True)

    cards = []
    for client in load_clients():
        src = reports_dir / client.client_id / f"{month:%Y-%m}.html"
        if not src.exists():
            raise FileNotFoundError(f"Missing report {src}; run `agency-pipeline report` first.")
        dest = site_dir / "reports" / f"{client.client_id}-{month:%Y-%m}.html"
        shutil.copyfile(src, dest)
        tag, blurb = SCENARIO_BLURBS.get(client.scenario, (client.scenario, ""))
        cards.append(
            CARD.format(
                href=f"reports/{dest.name}",
                tag=html.escape(tag),
                name=html.escape(client.client_name),
                blurb=html.escape(blurb),
            )
        )

    index = site_dir / "index.html"
    index.write_text(
        PAGE.format(
            cards="\n".join(cards),
            month_label=f"{month:%B %Y}",
            repo=REPO_URL,
            built=date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    (site_dir / ".nojekyll").touch()
    return index
