# Web App Spec (contract between the Python export and the frontend)

The agency-facing product is a static single-page web app in `web/`. No backend: the pipeline exports
JSON into `web/public/data/`, the app reads it with `fetch`. Same build runs locally (`npm run dev`)
and on GitHub Pages (HashRouter, Vite `base: './'`).

## Export: `agency-pipeline export-web [--months 2026-07,...]`
Python module `src/agency_pipeline/export_web.py`. Reads marts from the warehouse, runs
`monitoring.run_checks` and `commentary.generate_commentary` (template unless `--llm`) for every
client x month, writes the files below. Numbers are plain JSON numbers (no formatting), dates ISO
`YYYY-MM-DD`, months `YYYY-MM`. Ratios/MoM are fractions (0.1 = +10%). Nulls allowed where noted.
Floats rounded to 4 decimals. Default months: every full month present in the data (2026-07..2026-10).

### `data/manifest.json`
```json
{
  "generated_at": "2026-11-08T12:00:00Z",
  "agency": { "name": "Brightline Digital", "logo_text": "Brightline", "primary_color": "#2F6FEB" },
  "months": ["2026-07", "2026-08", "2026-09", "2026-10"],
  "default_month": "2026-10",
  "clients": [
    {
      "client_id": "bluepeak-dental", "client_name": "BluePeak Dental Group", "currency": "GBP",
      "scenario": "broken_autotagging",
      "alert_counts_by_month": { "2026-10": { "critical": 1, "warn": 0 } }
    }
  ]
}
```

### `data/clients/<client_id>.json`
```json
{
  "client": { "client_id": "...", "client_name": "...", "currency": "GBP", "scenario": "...",
              "agency_name": "...", "agency_logo_text": "...", "agency_primary_color": "#...",
              "google_ads_customer_id": "...", "meta_account_id": "...", "ga4_property_id": "...", "gsc_site_url": "..." },
  "monthly": [  // rpt_client_monthly, all months, channel in google_ads|meta_ads|total_paid
    { "month": "2026-10", "channel": "total_paid", "spend": 0, "clicks": 0, "conversions": 0,
      "conversion_value": 0, "cpa": null, "roas": null, "ctr": null,
      "spend_mom_pct": null, "conversions_mom_pct": null, "cpa_mom_pct": null, "roas_mom_pct": null }
  ],
  "paid_daily": [  // fct_paid_daily summed over campaigns
    { "date": "2026-10-01", "channel": "google_ads", "spend": 0, "impressions": 0, "clicks": 0,
      "conversions": 0, "conversion_value": 0 }
  ],
  "campaigns_monthly": [
    { "month": "2026-10", "channel": "meta_ads", "campaign_id": "...", "campaign_name": "...",
      "spend": 0, "impressions": 0, "clicks": 0, "conversions": 0, "conversion_value": 0 }
  ],
  "web_daily": [
    { "date": "2026-10-01", "channel_group": "paid_search", "sessions": 0, "engaged_sessions": 0,
      "users": 0, "key_events": 0, "revenue": 0 }
  ],
  "seo_daily": [ { "date": "2026-10-01", "clicks": 0, "impressions": 0, "ctr": 0, "avg_position": 0 } ],
  "seo_queries_monthly": [
    { "month": "2026-10", "query": "...", "clicks": 0, "impressions": 0, "ctr": 0, "avg_position": 0 }
  ],
  "reconciliation_daily": [
    { "date": "2026-10-01", "channel": "google_ads", "platform_clicks": 0, "ga4_sessions": 0,
      "session_click_ratio": null, "platform_conversions": 0, "ga4_key_events": 0, "status": "ok" }
  ],
  "thresholds": { "google_ads": { "warn": 0.5, "critical": 0.3 }, "meta_ads": { "warn": 0.4, "critical": 0.2 } },
  "months": {
    "2026-10": {
      "alerts": [ { "client_id": "...", "severity": "critical", "check": "reconciliation",
                    "message": "...", "start_date": "2026-10-18", "end_date": "2026-10-31" } ],
      "commentary": { "text": "...", "source": "template" }
    }
  }
}
```
Alerts for month M are `run_checks(end_date = last day of M, client_id)`.
Thresholds read from `dbt/dbt_project.yml` vars (single source of truth).

## Frontend (`web/`)
Vite + React 18 + TypeScript + Tailwind CSS 3 + react-router-dom 6 (HashRouter) + Recharts 2 + lucide-react.
Exact pinned versions in package.json, `package-lock.json` committed. `npm run build` -> `web/dist`.

Routes:
- `/` Portfolio overview — agency-wide KPIs for the selected month (spend, conversions, blended CPA,
  open critical alerts), client table (health badge, spend, conv, CPA, ROAS, MoM, 30-day spend sparkline),
  latest alerts feed.
- `/clients/:clientId` with tabs (query param `tab`): overview | paid | campaigns | website | seo | data-quality.
- `/alerts` alert center across clients, filter by severity/check/client.
- `/report/:clientId/:month` client-facing white-label report: no app chrome, agency brand only,
  print stylesheet, "Print / Save PDF" and "Copy link" actions hidden on print.
Global: month selector (persists in URL `?month=`), light/dark theme (system default + toggle),
currency formatting per client (Intl.NumberFormat), loading/empty/error states, responsive down to 375px
(sidebar collapses to a top bar / drawer).
