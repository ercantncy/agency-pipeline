# How to export the CSVs for your Tracking & Reporting Audit

Four short exports, about 15 minutes in total. Use the **same date range for every file**: the last 30 full days (or the last full calendar month). Send the files to your consultant by email or a shared folder. Nothing here changes any setting in your accounts.

Menu names below follow the current interfaces; platforms rename things often, so items marked *(verify)* may be labelled differently in your account.

> Prefer not to export files? Read-only access to the accounts (Viewer on Google Ads and GA4, Analyst on the Meta ad account, Restricted user on Search Console) works as an alternative.

## 1. Google Ads (required)

1. In Google Ads, open **Campaigns** (left menu) and set the date range (top right).
2. Click **Segment** (above the table) and choose **Time > Day**.
3. Click **Columns > Modify columns** *(verify)* and make sure these are shown: **Campaign type**, **Impr.**, **Clicks**, **Cost**, **Conversions**, **Conv. value**. Add **Currency code** if it is available.
4. Click **Download** (arrow icon in the toolbar) and choose **.csv**.

Leave the two title lines at the top of the file as they are; the audit expects them. Include paused campaigns if they had spend in the period.

## 2. Google Analytics 4 (required)

1. In GA4, open **Reports > Acquisition > Traffic acquisition** *(verify)*.
2. Set the date range (top right).
3. Change the first column dimension to **Session source / medium** (dropdown above the first column).
4. Click the **+** next to the dimension column (**Add secondary dimension**) and add **Date** and **Session campaign**. *(verify: if secondary dimensions are limited in your view, use Explore > Free form instead, with Date, Session source / medium and Session campaign as rows, and Sessions, Engaged sessions, Total users, Key events, Purchase revenue as values.)*
5. Click **Share this report > Download file > Download CSV** (icon top right) *(verify)*.

Required columns: **Date, Session source / medium, Sessions**. Helpful: **Session campaign, Engaged sessions, Total users, Key events** (older properties call this **Conversions**), **Purchase revenue**. If the table shows only 10 rows per page, set **Rows per page** to the maximum (5000+) before downloading, so the file is complete.

## 3. Meta Ads Manager (optional, needed for checks 2 and 4 on Meta)

1. In Ads Manager, open the **Campaigns** tab and set the date range.
2. Click **Breakdowns > By time > Day**.
3. Click **Columns > Customize columns** *(verify)* and include: **Campaign name**, **Amount spent**, **Impressions**, **Link clicks**, and your conversion column (**Purchases** and **Purchases conversion value** for shops, **Leads** for lead generation). **Campaign ID** is a good extra.
4. Click **Reports > Export table data** *(verify)*, choose **Export as .csv**.

## 4. Google Search Console (optional, improves check 6)

1. In Search Console, open **Performance > Search results**.
2. Set the date range to match the other files (**Date > Custom** *(verify)*).
3. Click **Export** (top right) and choose **Download .csv**. Inside the downloaded zip, send the file called **Dates.csv**.

## What happens next

Your consultant loads the files, checks them against each other, and returns a one-page scorecard with a 0 to 100 score, a green/amber/red status for six checks, and the three fixes that matter most. If a file is missing, the related check is shown as "not assessed" and does not affect the score.
