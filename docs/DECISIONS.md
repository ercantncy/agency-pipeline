# Decisions (2026-11-08)

Agreed in a grilling session. Change by editing this file, with the date.

| # | Decision |
|---|---|
| 1 | This repo is portfolio proof **and** the delivery template: each agency engagement forks it and swaps synthetic sources for real ones. Not a SaaS. |
| 2 | Public repo under the owner's real name. Owner checks the employment contract's side-business clause first. |
| 3 | Sell under a personal name for the first 90 days; consider a studio brand after 2 references. |
| 4 | Beachhead: 5–25 person PPC agencies in the US/UK (Google Ads + GA4 heavy). Solo media buyers are a secondary channel. |
| 5 | 12–15 hours/week, starting 2026-11-09. |
| 6 | Production data: Google Ads via BigQuery Data Transfer Service, GA4 native BigQuery export, Search Console bulk export, Meta via our own Python script (read-only token). Staging models get rewritten for these schemas at the first real client. |
| 7 | End clients get Looker Studio; the agency gets this web app as its monitoring console, behind Cloudflare Pages + Access. |
| 8 | Up to 2 free reference setups: 4 sources, 1 month maintenance, in exchange for a written testimonial, a case study (named or anonymous) and a commitment to consider a paid retainer in month 2. Written agreement: `docs/reference-setup-agreement.md`. |
| 9 | Pricing: first 3 paying clients at setup $1,500 and retainer $1,500/mo; from client 4, setup $2,500 and retainer $2,000/mo. Audit $149/$349. |
| 10 | Next build: `agency-pipeline audit`, the Tracking & Reporting Audit scorecard. Real connectors are built when the first client signs. |
| 11 | Payments: first 1–2 via Upwork or Ruul. Open a sole proprietorship (şahıs şirketi) at $1,500/mo or the first retainer, after an accountant confirms e-SMM vs invoice and the GVK 89/13 conditions. |
| 12 | Audit input is CSV exports (Google Ads, GA4, Meta, optional Search Console) loaded into the same `raw` tables; tolerant column mapping; download guide in `docs/audit-csv-guide.md`. |
| 13 | Scorecard: 6 checks (Ads click↔session ratio, Meta click↔session ratio, UTM hygiene, conversion agreement, volume drops/outages, suspicious direct/organic spikes), each green/amber/red with what/why/fix, plus a 0–100 score. |
| 14 | Delivered as a one-page HTML (A4 print to PDF) under the consultant's name, from the CLI. Samples for bluepeak and harbor in `docs/samples/`. Not part of the web app. |
| 15 | Reference Setup Agreement template in plain-English letter form. |
