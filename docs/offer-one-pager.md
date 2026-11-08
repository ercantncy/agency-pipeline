# Agency Reporting Pipeline

**Client reporting infrastructure for PPC, SEO and paid-social agencies. BigQuery + Looker Studio. No meetings.**

Prepared by Ercan Tuncay · hello@example.com · https://calendly.com/example/20min

---

## Who this is for

Marketing agencies with 5 to 25 people (and solo ad managers with 5 to 10 clients) in the US and UK who:

- build monthly client reports by hand, or patch them together from exports and spreadsheets;
- pay for a connector or reporting tool and still fix numbers manually every month;
- get asked "why does Google Ads say one thing and GA4 another?" and do not have a fast, defensible answer.

## The hours math

Industry estimates put manual reporting at roughly 20 to 30 hours per client per month once you count data pulls, reconciliation, formatting, commentary and client questions. Treat that as a starting point and replace it with your own timesheet numbers.

| | Example |
|---|---|
| Clients reported on monthly | 10 |
| Reporting hours per client per month | 20 |
| Total hours per month | 200 |
| Internal cost per hour (your number) | $40 |
| Monthly cost of reporting | $8,000 |

If a pipeline removes even a quarter of those hours, the retainer below pays for itself. If you resell reporting to clients at $150 to $500 per month, the work is already billable; the pipeline raises the margin on it.

The pitch is hours, not technology: if you spend 10 hours a week on reporting, this is designed to get most of them back.

---

## Three ways to work together

### 1. Tracking & Reporting Audit: $149 (single source pair) / $349 (full)

**Delivered in 3 business days. One-page scorecard.**

We compare what Google Ads, Meta Ads, GA4 and Search Console each say about the same period, find where the numbers disagree, and tell you why.

Included:
- Click-to-session reconciliation for paid search and paid social (the "Ads says 1,691 clicks, GA4 says 298 sessions" problem).
- Check for auto-tagging, UTM and redirect problems, GA4-to-Ads linking, and landing pages missing the tag.
- A one-page scorecard: what is healthy, what is broken, what it probably costs you, and what to fix first.

The $149 tier covers one client and one ad platform against GA4. The $349 tier covers one client across Google Ads, Meta Ads, GA4 and Search Console.

Not included: fixing the issues (see tier 2), access to accounts beyond read-only.

### 2. Agency Reporting Pipeline Setup: $1,500 to $3,000 fixed

**Typically 2 to 3 calendar weeks.** Price depends on source count and complexity.

What you get:
- 4 to 6 sources connected (Google Ads, Meta Ads, GA4 and Search Console as the core set; LinkedIn Ads, HubSpot or Shopify as optional additions, scoped before kickoff).
- A warehouse model in BigQuery: raw tables, cleaned staging models, and reporting tables for paid performance, web traffic by channel group, SEO, a paid-vs-GA4 reconciliation table, and a monthly client rollup with month-over-month change.
- Automated tests on the data (unique keys, non-null keys, valid channel and status values, non-negative spend).
- A 7-page white-label report template in your brand, copyable per client: executive summary, paid overview, Google Ads campaigns, Meta Ads campaigns, website, SEO, and data quality.
- Monitoring that checks data freshness, click-to-session reconciliation, and sudden drops in GA4 sessions.
- A recorded Loom handover and a written handover document.
- A 14-day fix guarantee: if something we built is wrong or breaks in the 14 days after handover, we fix it at no charge.

Payment: 50% upfront, 50% on handover.

### 3. Reporting Ops Retainer: $1,500 to $3,000 per month

For agencies that want the pipeline kept running without owning it.

- N client dashboards maintained (the price tier depends on N; agreed up front).
- Pipeline monitoring and alerts, with fixes when a source breaks or a tracking issue appears.
- Monthly commentary drafted for each client from the month's numbers and reviewed by a human before it reaches you.
- X change requests per month (new chart, new metric, new campaign grouping), agreed in the plan.
- 48-hour asynchronous turnaround on requests. Loom and shared dashboards, no standing meetings.
- Pause anytime: stop at the end of any billing month, restart when you are ready.

Billed monthly in advance.

---

## What is included and what is not

| Included | Not included |
|---|---|
| Read-only access to your ad and analytics accounts | Managing or changing campaigns, bids or budgets |
| Pipeline, warehouse model, report template, tests, monitoring | Fixing website or tag-manager issues on a client's site unless scoped (the audit will tell you what needs fixing) |
| Handover documentation | Ongoing support outside the setup guarantee or retainer |
| Commentary drafts, human-reviewed (retainer) | Strategy or media-buying advice |
| Connector pass-through costs, quoted before purchase | Paid connector licences (billed to you at cost, if any) |
| One agreed brand theme for the template | Custom design systems for each end client |

## FAQ

**What access do you need?**
Read-only access to each source: Viewer on the Google Ads account (or a manager-account link), Analyst or Viewer on the GA4 property, read access on the Meta ad account, and Restricted or Full user in Search Console. We do not need edit access to campaigns.

**Is it secure?**
Credentials are limited to read-only scopes. API tokens and service-account keys are stored in a secrets manager or environment variables, never in the code repository, and are revoked at your request. For production, the warehouse is a BigQuery project that you own (see next question). No client data is copied to personal devices beyond what is needed to build and test, and we are happy to sign an NDA or data-processing agreement.

**Who owns the data and the code?**
You do. The BigQuery project, datasets and dashboards live in your Google Cloud and Looker Studio accounts. You receive the dbt models and pipeline code with the handover. If you stop working with us, the pipeline keeps running as documented.

**What if the numbers do not match between Google Ads and GA4?**
They will not match exactly, and that is normal. Clicks and sessions are different things, and some loss is expected. The pipeline measures the ratio, shows it in the data quality page, and flags it when it drops into a warning range (below 50% for paid search by default) or a critical range (below 30%). Then we diagnose it. See the explainer: *Google Ads says 1,691 clicks, GA4 says 298 sessions*.

**Do you replace our reporting tool?**
Not necessarily. Some agencies keep it for client-facing graphs and use the warehouse for reconciliation and custom metrics. We will tell you honestly if a tool you already pay for is enough.

**What does it cost to run?**
BigQuery's free tier typically covers small-agency volumes, and Looker Studio is free (Pro is per user). Verify your expected usage during scoping; any paid connector costs are passed through at cost.

**Can I see a working example?**
Yes. A reference implementation with three synthetic clients, including a broken-tracking case, is on GitHub: https://github.com/ercantncy/agency-pipeline (live demo: https://ercantncy.github.io/agency-pipeline/). A 5-minute Loom walkthrough is here: https://www.loom.com/share/example-walkthrough.

## How to start

1. Book a 20-minute call: https://calendly.com/example/20min. Or reply with the number of clients you report on and which platforms you use.
2. Start with the audit ($149 or $349). It is fixed-price, takes 3 days, and the fee is credited toward a Setup if you proceed within 30 days. [Confirm this policy before publishing.]
3. If the audit shows a pipeline would pay off, we scope the Setup and agree a fixed price in writing.

Ercan Tuncay · hello@example.com · https://calendly.com/example/20min · https://www.linkedin.com/in/example
