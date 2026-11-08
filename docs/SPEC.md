# Agency Reporting Pipeline — Build Spec (contract for all contributors)

Portfolio-grade reference implementation of the "Agency Reporting Pipeline" productized service:
multi-source ad/web data -> warehouse -> modeled marts -> white-label per-client reports + monitoring.
Runs fully locally on synthetic data (DuckDB); the same dbt project targets BigQuery in production.

## Stack
- Python 3.12 managed by `uv` (`uv sync`, `uv run ...`). `requires-python = ">=3.12,<3.13"`.
- DuckDB (local warehouse file `data/warehouse.duckdb`, gitignored).
- dbt-core + dbt-duckdb (target `dev`), dbt-bigquery (target `prod`, not exercised in CI).
- typer CLI, pytest, ruff. Jinja2 + Plotly (offline, inlined JS) for HTML reports.
- `anthropic` SDK for optional LLM commentary (model `claude-sonnet-5-5`), deterministic template fallback when `ANTHROPIC_API_KEY` is unset.
- All code, comments, docs in English.

## Layout
```
pyproject.toml
config/clients.yml              # client registry (3 synthetic clients)
src/agency_pipeline/
  __init__.py
  config.py                     # load clients.yml -> list[ClientConfig]; paths (DATA_DIR, WAREHOUSE_PATH)
  sources/base.py               # abstract Source: name, table, extract(client, start, end) -> pandas.DataFrame
  sources/synthetic/            # one module per source + shared scenario engine (seeded)
  load.py                       # write extracted frames into DuckDB schema `raw` (idempotent per client+date range: delete-then-insert)
  monitoring.py                 # checks over marts -> list[Alert]
  commentary.py                 # monthly commentary (LLM or template)
  reporting/                    # HTML report builder + templates/
  cli.py                        # typer app, entry point `agency-pipeline`
dbt/                            # dbt project `agency_reporting`, profiles.yml in this dir
tests/
docs/
.github/workflows/ci.yml
```

## Clients (config/clients.yml)
Fields: `client_id` (slug), `client_name`, `agency_brand` (white-label: name, primary_color hex, logo_text),
`currency` (USD/GBP), `google_ads_customer_id`, `meta_account_id`, `ga4_property_id`, `gsc_site_url`, `scenario`.
Three clients, one per scenario:
- `northwind-outdoor` — scenario `healthy`: GA4 paid-search sessions ≈ 85–92% of Google Ads clicks; Meta ≈ 65–75%.
- `bluepeak-dental` — scenario `broken_autotagging`: GA4 google/cpc sessions ≈ 15–20% of Ads clicks (the "1,691 clicks vs 298 sessions" story); the rest lands in `google / organic` or `(direct) / (none)`.
- `harbor-coffee` — scenario `tracking_outage`: healthy, except GA4 returns ~0 sessions for 3 consecutive days ~10 days before the end date.
All share one agency brand ("Brightline Digital", #2F6FEB) to show white-labeling; schema allows per-client brand.

## Synthetic data rules
- Fully deterministic: `numpy.random.default_rng(seed)` with seed derived from (global seed 42, client_id, source).
- Default window: 120 days ending 2026-10-31 (CLI flags `--start/--end` override).
- Weekly seasonality (weekends lower for dental/B2B-ish, higher for coffee/outdoor), mild trend, noise.
- 3–5 campaigns per platform per client with stable IDs/names.
- Values must be internally consistent (clicks <= impressions, conversions <= clicks, sessions >= engaged_sessions, etc).

## Raw tables (DuckDB schema `raw`) — mimic the real API shapes
Every raw table also has `client_id VARCHAR` and `_loaded_at TIMESTAMP`.

`raw.google_ads_campaign_daily` (Google Ads API `campaign` report)
- `segments_date DATE`, `customer_id VARCHAR`, `campaign_id VARCHAR`, `campaign_name VARCHAR`,
  `campaign_advertising_channel_type VARCHAR` (SEARCH|PERFORMANCE_MAX|DISPLAY),
  `metrics_impressions BIGINT`, `metrics_clicks BIGINT`, `metrics_cost_micros BIGINT`,
  `metrics_conversions DOUBLE`, `metrics_conversions_value DOUBLE`

`raw.meta_ads_insights_daily` (Marketing API insights, level=campaign, time_increment=1)
- `date_start VARCHAR` ('YYYY-MM-DD'), `account_id VARCHAR`, `campaign_id VARCHAR`, `campaign_name VARCHAR`,
  `objective VARCHAR`, `impressions VARCHAR`, `inline_link_clicks VARCHAR`, `spend VARCHAR` (decimal strings, as the API returns),
  `actions VARCHAR` (JSON array of {"action_type","value"}; include `link_click`, `offsite_conversion.fb_pixel_purchase`, `offsite_conversion.fb_pixel_lead`),
  `action_values VARCHAR` (JSON array, purchase value)

`raw.ga4_traffic_daily` (GA4 Data API runReport)
- `date VARCHAR` ('YYYYMMDD'), `property_id VARCHAR`, `session_source VARCHAR`, `session_medium VARCHAR`,
  `session_campaign_name VARCHAR` ('(not set)' when unknown), `sessions BIGINT`, `engaged_sessions BIGINT`,
  `total_users BIGINT`, `key_events DOUBLE`, `purchase_revenue DOUBLE`
- Source/medium rows to include: google/cpc, facebook/paid (also some `fb / paid`, `ig / paid` variants), google/organic, bing/organic,
  (direct)/(none), newsletter/email, referral sites/referral.

`raw.gsc_search_daily` (Search Console searchAnalytics, dimensions date,query,page)
- `date DATE`, `site_url VARCHAR`, `query VARCHAR`, `page VARCHAR`, `clicks BIGINT`, `impressions BIGINT`, `ctr DOUBLE`, `position DOUBLE`
- ~20–40 queries per client, long-tail distribution.

`raw.clients` — flattened clients.yml (client_id, client_name, agency_name, agency_primary_color, agency_logo_text, currency, scenario, + account ids).

## dbt models (project `agency_reporting`, reads source `raw`)
Staging (`stg_*`, views): typed, renamed, money in currency units (cost_micros/1e6, spend::double), dates as DATE,
Meta actions JSON parsed (DuckDB `json` functions) into `link_clicks`, `purchases`, `leads`, `purchase_value`.
GA4 `channel_group` derivation (macro), case-insensitive:
- paid_search: medium in (cpc, ppc, paidsearch)
- paid_social: medium in (paid, paid_social, cpm) and source in (facebook, fb, instagram, ig, meta, linkedin)
- organic_search: medium = organic
- email: medium = email
- referral: medium = referral
- direct: source = (direct) and medium in ((none), (not set))
- other: everything else

Marts (tables, schema `marts`):
- `dim_client` — from raw.clients.
- `fct_paid_daily` — grain client_id, date, channel ('google_ads'|'meta_ads'), campaign_id: campaign_name, spend, impressions, clicks, platform_conversions, platform_conversion_value.
- `fct_web_daily` — grain client_id, date, channel_group: sessions, engaged_sessions, users, key_events, revenue.
- `fct_paid_vs_ga4_reconciliation` — grain client_id, date, channel ('google_ads'↔paid_search, 'meta_ads'↔paid_social):
  platform_clicks, ga4_sessions, session_click_ratio (null if clicks=0), platform_conversions, ga4_key_events,
  status: 'critical' if ratio < 0.30, 'warn' if ratio < 0.50 (Meta: < 0.20 critical, < 0.40 warn), else 'ok'. Thresholds as dbt vars.
- `fct_seo_daily` — grain client_id, date: clicks, impressions, ctr, avg_position (impression-weighted).
- `fct_seo_query_monthly` — grain client_id, month (DATE, first of month), query: clicks, impressions, ctr, avg_position.
- `rpt_client_monthly` — grain client_id, month, channel ('google_ads'|'meta_ads'|'total_paid'): spend, clicks, conversions, conversion_value, cpa, roas, ctr, plus `*_mom_pct` for spend, conversions, cpa, roas.
dbt tests: unique/not_null on grains (use `dbt_utils.unique_combination_of_columns` OR a singular test if avoiding packages — prefer NO external packages, write a generic test macro), accepted_values for channel/status, non-negative spend.

## Monitoring (`agency-pipeline check`)
Alert(client_id, severity 'warn'|'critical', check, message). Checks:
- freshness: latest date per client per source in marts older than `end_date - 2 days` -> critical.
- reconciliation: any day in the last 14 days with status warn/critical -> alert (aggregate consecutive days in message).
- volume drop: GA4 sessions on a day < 30% of trailing 14-day median -> critical (catches outage).
Exit code 1 if any critical. Output: rich table + optional `--json`.

## Reports (`agency-pipeline report --client <id|all> --month YYYY-MM`)
Output `output/reports/<client_id>/<YYYY-MM>.html`, single self-contained file, white-labeled with agency brand (no mention of the pipeline vendor).
Sections ("pages"): 1 Executive summary (KPI tiles + commentary), 2 Paid overview (spend/conv/CPA/ROAS trend), 3 Google Ads campaigns table,
4 Meta Ads campaigns table, 5 Website (GA4 channel groups), 6 SEO (top queries, position trend), 7 Data quality (reconciliation chart + open alerts, explained in plain English).
Commentary: `commentary.py` builds a compact JSON of the month's KPIs + MoM deltas + alerts; with API key, asks Claude for a ~120-word client-friendly paragraph (no invented numbers, only from JSON); otherwise deterministic template. Mark LLM output as "draft — review before sending" in a CLI log line, not in the report.

## CLI (`agency-pipeline`)
- `extract-load [--client] [--start] [--end]` — synthetic sources -> raw.
- `transform` — runs `dbt build` (project dir `dbt/`, profiles dir `dbt/`).
- `check [--json]`
- `report --client --month`
- `run --month YYYY-MM` — all of the above end-to-end (default month 2026-10).
