# 5-minute Loom walkthrough script

Goal: show a prospective agency owner that the work is real, tested and explainable, in five minutes. Speak plainly. Talk about hours saved and numbers that reconcile, not technology.

Setup before recording: terminal open at the repository root, the bluepeak-dental report open in a browser tab, the Northwind report in another, the README or SPEC visible in an editor. Run `uv run agency-pipeline run --month 2026-10` beforehand so output exists, or be ready to run it live. Close notifications.

Spoken text is in quotes. Actions are in brackets.

---

**0:00 - 0:30 | Hook and who this is for**

[Show the Bluepeak Dental report, data quality page, on screen.]

"Hi, I'm [Your Name]. This is a sample report for a dental client. Google Ads says 1,759 clicks. GA4 says 309 sessions. If you run an agency, you've probably had that conversation with a client. The next five minutes show how I set up a reporting pipeline that catches this automatically, and how it saves you the hours you spend on reporting every month. The data here is synthetic, so no real client is shown."

**0:30 - 1:15 | The problem in hours**

[Switch to a plain slide or the offer page.]

"Agencies commonly spend something like 20 to 30 hours per client per month on reporting. Ten clients is 200 hours. The goal of this setup is to give most of that back, and to make the numbers defensible when a client asks why two tools disagree."

**1:15 - 2:00 | The repo in one pass**

[Editor: show the folder layout.]

"Here's the repository. Sources pull data from Google Ads, Meta, GA4 and Search Console. For this demo they're synthetic, generated deterministically, so you can rerun it and get the same result. A load step puts everything in a warehouse. Locally that's DuckDB, in production it's BigQuery. Then a dbt project cleans and models the data into reporting tables."

[Show config/clients.yml.] "Three clients, one brand, Brightline Digital, to show white-labeling. Each client has a scenario. One healthy, one with broken tracking, one with an outage."

**2:00 - 2:50 | The warehouse model and tests**

[Terminal: run `uv run agency-pipeline transform`, show dbt build passing.]

"dbt builds staging models that fix types and units, then the reporting tables: paid performance, web traffic by channel group, SEO, a monthly rollup, and a reconciliation table that compares platform clicks with GA4 sessions. There are tests on keys, valid values and non-negative spend, so bad data fails loudly rather than reaching a client."

**2:50 - 3:40 | Monitoring**

[Terminal: run `uv run agency-pipeline check`; show table.]

"This is the monitoring check. It looks at freshness, the click-to-session ratio, and sudden drops in GA4 sessions. Bluepeak shows critical on reconciliation. Harbor Coffee shows a volume drop, which is a three-day outage in GA4. Northwind is clean. The command exits with an error code when something is critical, so a scheduler can send an alert before the client notices."

**3:40 - 4:30 | The report**

[Browser: Northwind report, page by page, quickly.]

"This is the white-label report. Seven sections: executive summary, paid overview, Google Ads and Meta campaigns, website, SEO and data quality. It's in the agency's brand, with no mention of me. The commentary is a short paragraph built only from the month's numbers. When I use a language model for the draft, a human reviews it before it goes out. Without one, it falls back to a deterministic template."

[Switch to Bluepeak, data quality page.]

"Now Bluepeak. The ratio is around 18 percent. The report explains in plain English that most paid sessions are being recorded as organic or direct, which usually means auto-tagging or redirects. That's the fix to make."

**4:30 - 5:00 | Production path and next step**

[Show docs/looker-studio-setup.md or the offer page.]

"In production this runs in your own BigQuery project, with a Looker Studio report in your brand, one copy per client. You own the data and the code. If you want to know whether your accounts have this problem, I do a fixed-price audit: $149 or $349, three days, one-page scorecard. The link is below. Thanks for watching."

---

## Recording notes

- Keep it under 5:15. Cut the live transform run if it is slow and show the pre-run output.
- Do not show real client names, ad account IDs or API keys. Everything shown must be synthetic.
- Add the repo link, the explainer link and [Calendly link] in the Loom description.
- Title: "Reporting pipeline for agencies: 5-minute walkthrough".
