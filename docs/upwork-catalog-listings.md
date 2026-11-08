# Upwork Project Catalog listings and proposal templates

Catalog listings cost no Connects. Verify current Project Catalog field limits, category names and fee rules in the Upwork UI before publishing; they change. Titles below are counted and are 70 characters or fewer.

---

## Listing 1: Tracking & Reporting Audit

**Title (61 chars):** Google Ads, GA4 and Meta tracking audit with 1-page scorecard

**Description**

Your Google Ads clicks and your GA4 sessions do not match, and you cannot explain why to your client. I will find out.

In 3 business days I compare what Google Ads, Meta Ads, GA4 and Search Console report for the same period and deliver a one-page scorecard: what is healthy, what is broken, what is the likely cause, and what to fix first.

What I check:
- Click-to-session ratio for paid search and paid social, against rough healthy ranges
- Auto-tagging, UTM conventions and redirects that strip click IDs
- GA4 and Google Ads linking, and landing pages missing the tag
- Where unattributed paid traffic ends up (organic, direct)

What you get: a one-page scorecard (PDF) and a short Loom explaining the findings. I do not change your accounts. Fixes are a separate scope.

**Tiers**

| | Basic | Standard |
|---|---|---|
| Price | $149 | $349 |
| Delivery | 3 days | 3 days |
| Scope | 1 client, 1 ad platform vs GA4 | 1 client, Google Ads + Meta Ads + GA4 + Search Console |
| Scorecard | 1 page | 1 page + prioritised fix list |
| Loom walkthrough | no | yes |

**Requirements from buyer**
- Read-only access to the Google Ads account, GA4 property and, for Standard, Meta Ads and Search Console
- The date range to review (default: last full month)
- Names of any redirect tools, landing page builders or tag managers in use

**FAQ**
- *Do you need edit access?* No. Viewer or Analyst access is enough.
- *Will the numbers ever match exactly?* No. Some gap is normal. The audit tells you whether your gap is normal or a defect.
- *Do you fix the problems?* Not in this listing. I tell you what to fix and offer a fixed-price setup if you want a pipeline.
- *Can I use this for a client's report?* Yes. The scorecard is yours.

---

## Listing 2: Agency Reporting Pipeline Setup

**Title (64 chars):** Client reporting pipeline for agencies: BigQuery + Looker Studio

**Description**

Stop spending 20 to 30 hours per client per month building reports by hand. I build a reporting system you own.

Delivered: 4 to 6 sources (Google Ads, Meta Ads, GA4, Search Console; LinkedIn Ads, HubSpot or Shopify optional) into BigQuery, modeled into clean reporting tables with automated tests. A 7-page white-label Looker Studio template in your brand, copyable per client. Monitoring for stale data, click-to-session mismatches and traffic drops. Loom handover and written documentation. 14-day fix guarantee.

I use a tested reference build (dbt models, reconciliation, monitoring). A working demo on synthetic data is linked in my profile.

Not included: campaign management, fixing client websites, paid connector licences.

**Tiers**

| | Starter | Standard | Advanced |
|---|---|---|---|
| Price | $1,500 | $2,250 | $3,000 |
| Delivery | 14 days | 18 days | 21 days |
| Sources | 4 | 5 | 6 |
| Client report copies set up | 3 | 6 | 10 |
| Monitoring and alerts | yes | yes | yes |
| Loom handover | yes | yes | yes |
| Fix guarantee | 14 days | 14 days | 14 days |

**Requirements from buyer**
- Read-only access to each source account
- A Google Cloud project owned by your agency with billing enabled (I can guide you through it)
- Your logo, brand colors and one example of a report you send today
- A list of clients and which platforms each uses

**FAQ**
- *Who owns it?* You. The BigQuery project, dashboards and code are yours.
- *Do I have to pay for BigQuery or Looker Studio?* Looker Studio is free. BigQuery's free tier typically covers small-agency volumes; verify against your usage.
- *Can you use our existing connector?* Often yes. I will tell you during scoping whether it is worth keeping.
- *What if the numbers do not match?* The reconciliation table measures the gap per channel and flags it. I will explain what is normal and what is a defect.

---

## Listing 3: Reporting Ops Retainer

**Title (64 chars):** Monthly client reporting ops: dashboards, monitoring, commentary

**Description**

I keep your client reporting running so your team does not have to. For a fixed monthly fee I maintain your client dashboards, monitor the pipeline, fix breakages, draft monthly commentary (reviewed by a human before it goes to you) and handle a set number of change requests. Asynchronous only: Loom and shared dashboards, no standing meetings, 48-hour turnaround. Pause anytime at the end of a billing month.

Best for agencies that already have a pipeline from me, or an existing BigQuery plus Looker Studio setup that I review first.

**Tiers**

| | 5 clients | 10 clients | 15 clients |
|---|---|---|---|
| Price per month | $1,500 | $2,250 | $3,000 |
| Dashboards maintained | 5 | 10 | 15 |
| Change requests per month | 3 | 5 | 8 |
| Monthly commentary drafts | yes | yes | yes |
| Turnaround | 48h | 48h | 48h |

**Requirements from buyer**
- A working pipeline, or an audit/setup with me first
- A single point of contact for requests
- Read-only access to sources, kept valid

**FAQ**
- *What counts as a change request?* A new chart, metric, filter or campaign grouping. Fixing something broken is not counted against your limit.
- *Can I pause?* Yes, at the end of any billing month.
- *Is anyone on call?* No. This is asynchronous with a 48-hour target on working days.
- *Who writes the commentary?* A draft is generated from the month's numbers, and I review and edit it before sending.

---

## 90-second personalised proposal Loom: template

Record one per job. Total length 75 to 90 seconds. Open their actual report or site.

1. (0:00 - 0:10) "Hi [First name], I saw your post about [specific problem from the job post]. I'm Ercan Tuncay. I build reporting pipelines for agencies."
2. (0:10 - 0:35) Show something specific from their world: their public site, a sample of their report style, or their stated tool stack. "From what you described, you pull [sources] into [tool], and I'd guess [specific pain, e.g. numbers differ between Ads and GA4]."
3. (0:35 - 1:05) Show the demo for 30 seconds: the reconciliation or data quality page. "This is a synthetic client where Google Ads shows 1,759 clicks and GA4 309 sessions. The pipeline flags it automatically and explains it in plain English."
4. (1:05 - 1:25) Propose the first step: "I'd start with a $149/$349 audit so you know what's broken. Or if you already know, we scope the setup."
5. (1:25 - 1:30) "Link to the demo is below. Happy to answer anything here."

Rules: use their name; never reuse a Loom; no screen of anything that is not synthetic or theirs.

## Written proposal template

> Hi [First name],
>
> You mentioned [specific problem in their words]. That is usually one of two things: [likely cause 1] or [likely cause 2].
>
> What I would do: [1 sentence on the first step, usually the audit]. Fixed price [$X], delivered in [N] days. You would get [deliverable].
>
> A 90-second walkthrough aimed at your situation: https://www.loom.com/share/example-walkthrough. A working demo with synthetic data: https://github.com/ercantncy/agency-pipeline (live demo: https://ercantncy.github.io/agency-pipeline/).
>
> One question: [specific scoping question, e.g. which platforms and how many clients?]
>
> Ercan Tuncay

Filters for choosing jobs to answer: keywords such as agency, client reporting, Looker Studio, GA4, BigQuery; fixed-price jobs, or hourly jobs at a rate you accept. Send a handful of targeted proposals per week rather than many generic ones. Treat any success-rate figure you read online as unreliable and track your own.
