# Google Ads says 1,691 clicks, GA4 says 298 sessions: where the difference comes from

An agency owner sends you a screenshot. Google Ads reports 1,691 clicks for the month. GA4 reports 298 sessions from google / cpc. The client asks which one is right and where the other 1,393 visitors went.

Some gap between these two numbers is normal. A gap of 82% is not. This article explains which differences are legitimate, which indicate a broken setup, how to tell them apart, and how an automated reconciliation check can catch the problem before a client does.

## Clicks and sessions are different things

A **click** is counted by Google Ads when someone clicks your ad. A **session** is counted by GA4 only after its tag loads on your page and sends a hit. Between the click and the session, a lot can happen.

### Legitimate reasons for a gap

- **Bounces before the tag fires.** Visitors who leave before the page and tag load (slow pages, accidental clicks, mobile users on weak connections) are clicks but never sessions.
- **Consent mode and ad blockers.** Users who decline analytics cookies, or run blockers, may not be measured at all, or may be measured only partially through modelled data. This varies widely with audience and region; it is a larger factor for UK and EU traffic.
- **Session timeout and deduplication.** GA4 ends a session after 30 minutes of inactivity by default. Multiple ad clicks inside one session count as one session. Someone who clicks your ad twice in a minute is two clicks, one session.
- **Cross-device and in-app browsers.** A click on a phone that converts later on a laptop appears as separate sessions with different attribution. In-app browsers (for example from social apps) often interfere with measurement.
- **Time zones.** If the Google Ads account and the GA4 property use different time zones, daily totals shift. Over a month the effect is small; over a single day it can be visible.
- **Invalid click filtering.** Google Ads removes invalid clicks (bots, accidental duplicate clicks) from reported clicks, but the timing of the adjustments can lag, and GA4 has its own bot filtering. The two systems do not filter identically.

### Reasons that indicate a broken setup

- **Auto-tagging is off, or the gclid is stripped.** Google Ads appends a `gclid` parameter to the landing URL. GA4 uses it to attribute the session to google / cpc. If auto-tagging is disabled, or a redirect, URL shortener, form tool or CMS rule drops the parameter, GA4 never sees it. The session still happens, but it lands in `google / organic` or `(direct) / (none)`.
- **Tag missing on landing pages.** Landing pages built in a separate tool (landing page builders, subdomains, checkout pages) often lack the GA4 tag. The click is real; the session is never recorded.
- **UTM overrides.** Manual UTM parameters on ad URLs (for example `utm_medium=paid` instead of `cpc`) can override auto-tagging so GA4 classifies the traffic into a different channel than you expect.
- **GA4 and Google Ads not linked.** Without the link, some attribution and import features do not work. Check Admin > Product links in GA4.

## Rough healthy ranges (heuristics only)

These are rules of thumb from experience, not benchmarks. Your industry, device mix, consent setup and landing pages move them.

| Channel | Sessions as a share of platform clicks, typical healthy range |
|---|---|
| Google Ads search | roughly 70% to 95% |
| Meta Ads (link clicks) | roughly 50% to 80%, lower because of in-app browsers and fast bounces |

A ratio persistently far below these ranges, or one that suddenly changes, is the signal. The absolute level matters less than the trend and the break.

## Diagnosis checklist

Work top to bottom. Each step is cheap and rules out a common cause.

1. **Compare the same dates in the same time zone.** Align account and property time zones, then use a full month rather than a day.
2. **Check the ratio over time.** A sudden cliff points to a change (a redirect, a new landing page, a tag removal). A flat low ratio points to a setup that never worked.
3. **Confirm auto-tagging is enabled** in Google Ads (Account settings > Auto-tagging).
4. **Click an ad (or paste a test URL) and watch the landing URL.** Does `gclid` survive to the final page after all redirects?
5. **Open GA4 Realtime or DebugView** and load the landing page. Does a session appear, with the source/medium you expect?
6. **Check where the missing sessions went.** In GA4, look at google / organic and (direct) / (none) sessions landing on your ad landing pages. A spike there that mirrors the missing paid sessions is the signature of a stripped gclid.
7. **Check the tag on every landing page and subdomain,** including pages hosted on other tools.
8. **Review manual UTM parameters** on ad URLs for values that conflict with auto-tagging.
9. **Confirm the GA4-Ads link** and that the right Ads account is linked to the right property.
10. **Review consent and blocker setup,** if the shortfall is moderate and the audience is in the UK or EU.

## How the pipeline flags it

In the reference pipeline, a reconciliation table (`fct_paid_vs_ga4_reconciliation`) sits between the paid-platform data and GA4. For each client and day it maps Google Ads to GA4 paid search and Meta Ads to GA4 paid social, then computes `session_click_ratio = ga4_sessions / platform_clicks`.

Status is assigned from thresholds, which are configurable:

| Channel | warn | critical |
|---|---|---|
| Google Ads vs paid search | ratio < 50% | ratio < 30% |
| Meta Ads vs paid social | ratio < 40% | ratio < 20% |

The monitoring command (`agency-pipeline check`) looks at the last 14 days, groups consecutive flagged days into one alert, and exits non-zero on critical so a scheduler can notify someone. The data quality page of the client report shows the ratio chart and open alerts in plain English.

## Worked example: bluepeak-dental

The repository includes three synthetic clients. Bluepeak Dental is built to reproduce the problem in this article: auto-tagging is effectively broken. In October 2026 Google Ads reports 1,759 clicks; GA4 attributes only 309 sessions to google / cpc, a ratio of roughly 18%: almost exactly the screenshot above.

The pipeline result for this client:

- The reconciliation status is **critical** (ratio under 30%) for paid search, on most days.
- In GA4, the traffic that should be google / cpc shows up instead in `google / organic` and `(direct) / (none)`. Organic and direct look healthier than they are, and paid search looks like it underperforms.
- Because the dashboard channel mapping is built from GA4's source and medium, the client's cost per acquisition for paid search looks far worse in GA4 than in Google Ads.

Following the checklist: step 3 (auto-tagging) and step 4 (does the gclid survive redirects?) are where this scenario would be fixed in a real account. After the fix, the ratio should climb back into the healthy range within days, and the monitor clears.

The other two synthetic clients provide contrast: Northwind Outdoor is healthy (paid search roughly 85% to 92%), and Harbor Coffee is healthy except for a three-day outage where GA4 returns almost no sessions, which the volume-drop check catches separately.

All data in the repository is synthetic and deterministic. The figures illustrate the mechanism; they are not benchmarks.

## Takeaway

A moderate gap between clicks and sessions is expected and explainable. A large or sudden gap is a defect in measurement, not in advertising, and it distorts every downstream number: channel mix, cost per acquisition, and the story you tell the client. Measuring the ratio daily and alerting on it turns a quarterly surprise into a same-week fix.

If you suspect this is happening in your accounts, a fixed-price Tracking & Reporting Audit ($149 or $349, 3 days) will tell you. https://calendly.com/example/20min
