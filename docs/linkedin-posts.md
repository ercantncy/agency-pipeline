# LinkedIn posts

## Headline

Reporting infrastructure for marketing agencies — BigQuery + Looker Studio, no meetings

## Posting notes

- Two posts per week: odd numbers are technical, even numbers are economics. Post 1 first.
- Replace [bracketed] items. Every example in the repository is synthetic; say so when you show it.
- Each post is under 1,300 characters (checked).

---

## Post 1 (technical)

Google Ads says 1,691 clicks. GA4 says 298 sessions.

That is an 18% ratio. Not "a bit off." Broken.

Some gap is normal: bounces before the tag fires, consent mode, ad blockers, session dedupe. For paid search I'd expect something like 70-95% as a rough heuristic, not a rule.

An 18% ratio usually means one of these:
- auto-tagging is off
- a redirect strips the gclid
- landing pages are missing the GA4 tag
- the paid traffic is landing in "organic" or "(direct)" instead

The tell: organic and direct look suspiciously good while paid looks like it underperforms.

I wrote up the full diagnosis checklist and built a check that flags it daily (warn below 50%, critical below 30%).

Article and a synthetic demo: https://github.com/ercantncy/agency-pipeline/blob/master/docs/explainer-clicks-vs-sessions.md · https://ercantncy.github.io/agency-pipeline/

---

## Post 2 (economics)

If you run an agency, here is a number worth writing down.

Reporting hours per client per month. Industry estimates run 20 to 30 hours; use your own timesheets.

10 clients x 20 hours = 200 hours a month.
At an internal cost of $40/hour, that is $8,000 a month on reporting.

Now the other side. Many agencies charge clients $150-500/month for reporting. If you are not charging for it, it is a cost. If you are, the margin is eaten by the hours.

A pipeline will not remove every hour. But if it removes a quarter of them, that is 50 hours a month back.

I build this for 5-25 person PPC and SEO agencies, fixed price. If you want to run the math on your own numbers, send me your client count and I will do it with you.

https://calendly.com/example/20min

---

## Post 3 (technical)

Three tests I put on every reporting warehouse before a client sees a number:

1. Keys are unique and not null at the grain I claim. If a table says one row per client, day, channel and campaign, a test proves it.
2. Accepted values. Channel can only be google_ads or meta_ads. Status can only be ok, warn or critical.
3. Spend is never negative.

Boring. Also the reason a duplicated load or a source schema change fails in a pipeline run instead of in a client meeting.

A dashboard is only as trustworthy as the model under it. Most "the numbers are wrong" conversations are really "nobody tested the join."

The repo is public, with synthetic clients and the tests included: https://github.com/ercantncy/agency-pipeline

---

## Post 4 (economics)

The most expensive part of a reporting tool is not the licence.

It is the monthly 30 minutes per client that someone spends fixing it.

If a connector subscription costs a few hundred dollars a month and your team still spends 20 minutes per client reconciling Ads against GA4, the real cost is the subscription plus the hours.

I am not saying drop your tool. Many are fine. I am saying: count the hours attached to it, not just the invoice.

A cleaner setup is a warehouse you own, tests that catch the break, and a template that copies per client. It costs more to set up and less to run.

Fixed price setup, from $1,500. Audit first, from $149, if you want to know where you stand.

https://calendly.com/example/20min

---

## Post 5 (technical)

Not every gap between Ads and GA4 is a bug. Here is how I tell them apart.

Normal:
- Different definitions: click vs session
- Consent mode and ad blockers
- Time zones that do not match
- Session timeout merging two clicks into one visit

Defect:
- A ratio that falls off a cliff on a specific date (something changed)
- A ratio that is low from day one (never set up properly)
- Sessions missing from google/cpc but showing up in google/organic or direct

So the useful metric is not the ratio. It is the ratio over time, per channel, with a threshold.

I check it daily across clients and alert on consecutive bad days. One bad day is noise. Three in a row is a ticket.

Demo on synthetic data: https://ercantncy.github.io/agency-pipeline/

---

## Post 6 (economics)

Why I price the first step at $149 or $349.

An agency owner does not buy a $2,000 pipeline from a stranger. They buy a small, concrete answer first: "is my tracking broken?"

Fixed price. Three days. One page. At the end they know what is wrong, what it likely costs, and what to fix first. Some of them do not need me after that. That is fine.

The ones whose accounts do have a problem usually want it fixed, and then want it not to happen again. That is where a setup and a monthly retainer make sense.

I would rather earn trust at a small price than ask for a big one before I have shown anything.

Details: https://github.com/ercantncy/agency-pipeline/blob/master/docs/offer-one-pager.md

---

## Post 7 (technical)

How I structure client data so one report template serves every client.

One warehouse. Every table has a client_id column. Staging models clean the source data. Reporting tables roll it up: paid performance by day, web traffic by channel group, SEO by month, and a reconciliation table.

The template filters on client_id. Copy the report, set the filter, change nothing else.

Why not one dataset per client? Because then every model and every permission is multiplied by the number of clients.

The one thing to be careful about: a drop-down filter alone does not secure client data. Lock the filter, or use separate copies or views for client-facing links.

Setup guide: https://github.com/ercantncy/agency-pipeline/blob/master/docs/looker-studio-setup.md

---

## Post 8 (economics)

What a retainer should and should not be.

Should be: monitoring that catches broken data before the client does, a monthly commentary draft a human reviews, a set number of changes, a fast asynchronous turnaround, and the option to pause.

Should not be: meetings you do not need, a lock-in contract, or a vague promise of "support."

My version: $1,500 to $3,000 a month depending on how many client dashboards. 48-hour async turnaround. A defined number of change requests. Pause at the end of any month.

If the pipeline does its job, most months nothing happens. That is the point. You are paying for the month it would have.

https://calendly.com/example/20min
