"""Synthetic GA4 Data API report, coherent with the Google Ads, Meta and Search Console sources."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from agency_pipeline.config import ClientConfig
from agency_pipeline.sources.base import Source
from agency_pipeline.sources.synthetic.google_ads import GoogleAdsSource
from agency_pipeline.sources.synthetic.gsc import GscSource
from agency_pipeline.sources.synthetic.meta_ads import MetaAdsSource
from agency_pipeline.sources.synthetic.scenario import (
    GOOGLE_SESSION_RATIO,
    LOST_TO_ORGANIC,
    META_SESSION_RATIO,
    date_range,
    day_multiplier,
    outage_dates,
    profile_for,
    rng_for,
)

COLUMNS = [
    "date", "property_id", "session_source", "session_medium", "session_campaign_name",
    "sessions", "engaged_sessions", "total_users", "key_events", "purchase_revenue", "client_id",
]  # fmt: skip

NOT_SET = "(not set)"
#: Meta clicks are reported under these source labels (mix of tagging conventions).
META_VARIANTS = (("facebook", 0.70), ("fb", 0.15), ("ig", 0.15))
REFERRALS = (("blog.trailnotes.example", 0.6), ("news.localdirectory.example", 0.4))

#: (engagement rate, key events per session) per traffic type.
ENGAGEMENT = {
    "cpc": (0.62, None),  # key-event rate comes from the client's Google Ads conversion rate
    "paid": (0.55, 0.020),
    "organic": (0.68, 0.022),
    "direct": (0.58, 0.030),
    "email": (0.72, 0.050),
    "referral": (0.60, 0.015),
}


class Ga4Source(Source):
    name = "ga4"
    table = "ga4_traffic_daily"

    def extract(self, client: ClientConfig, start: date, end: date) -> pd.DataFrame:
        profile = profile_for(client)
        rng = rng_for(client.client_id, self.name)
        dates = date_range(start, end)
        mult = day_multiplier(dates, profile, rng)
        outages = outage_dates(client, end)

        google = GoogleAdsSource().extract(client, start, end)
        meta = MetaAdsSource().extract(client, start, end)
        gsc = GscSource().extract(client, start, end)
        google_clicks = google.groupby(["segments_date", "campaign_name"])["metrics_clicks"].sum()
        meta["clicks"] = meta["inline_link_clicks"].astype(int)
        meta_clicks = meta.groupby(["date_start", "campaign_name"])["clicks"].sum()
        organic_clicks = gsc.groupby("date")["clicks"].sum()

        g_mean, g_sd = GOOGLE_SESSION_RATIO[client.scenario]
        m_mean, m_sd = META_SESSION_RATIO
        rows: list[tuple] = []  # (date, source, medium, campaign, sessions, kind)

        for i, day in enumerate(dates):
            g_ratio = float(np.clip(rng.normal(g_mean, g_sd), 0.05, 0.97))
            m_ratio = float(np.clip(rng.normal(m_mean, m_sd), 0.05, 0.97))
            lost = 0
            for campaign in profile.google_campaigns:
                clicks = int(google_clicks.get((day, campaign.name), 0))
                sessions = int(round(clicks * g_ratio))
                lost += clicks - sessions
                rows.append((day, "google", "cpc", campaign.name, sessions, "cpc"))
            for campaign in profile.meta_campaigns:
                clicks = int(meta_clicks.get((day.isoformat(), campaign.name), 0))
                total = int(round(clicks * m_ratio))
                for source, share in META_VARIANTS:
                    medium = "paid"
                    rows.append(
                        (day, source, medium, campaign.name, int(round(total * share)), "paid")
                    )

            # Broken auto-tagging: untagged paid clicks land in organic / direct instead.
            lost_organic = lost_direct = 0
            if client.scenario == "broken_autotagging":
                lost_organic = int(round(lost * LOST_TO_ORGANIC))
                lost_direct = lost - lost_organic

            organic = float(organic_clicks.get(day, 0)) * rng.normal(0.92, 0.03) + lost_organic
            rows.append((day, "google", "organic", NOT_SET, int(round(organic)), "organic"))
            rows.append(
                (day, "bing", "organic", NOT_SET, int(round(organic * 0.08 / 0.92)), "organic")
            )
            direct = profile.direct_daily_sessions * mult[i] * rng.lognormal(0, 0.06) + lost_direct
            rows.append((day, "(direct)", "(none)", NOT_SET, int(round(direct)), "direct"))
            if day.weekday() == 1:  # weekly newsletter on Tuesdays
                send = profile.direct_daily_sessions * 0.5 * rng.lognormal(0, 0.15)
                rows.append(
                    (day, "newsletter", "email", "weekly-newsletter", int(round(send)), "email")
                )
            for site, share in REFERRALS:
                ref = profile.direct_daily_sessions * 0.08 * share * mult[i] * rng.lognormal(0, 0.2)
                rows.append((day, site, "referral", NOT_SET, int(round(ref)), "referral"))

        df = pd.DataFrame(rows, columns=["d", "session_source", "session_medium",
                                         "session_campaign_name", "sessions", "kind"])  # fmt: skip
        n = len(df)

        # GA4 collects (almost) nothing during a tracking outage.
        outage_mask = df["d"].isin(outages).to_numpy()
        df.loc[outage_mask, "sessions"] = rng.integers(0, 3, int(outage_mask.sum()))

        eng_rate = df["kind"].map(lambda k: ENGAGEMENT[k][0]).to_numpy() * rng.normal(1, 0.03, n)
        ke_rate = df["kind"].map(lambda k: ENGAGEMENT[k][1] or profile.google_cvr * 0.9).to_numpy()
        sessions = df["sessions"].to_numpy()
        engaged = np.minimum(sessions, rng.binomial(sessions, np.clip(eng_rate, 0, 1)))
        users = np.minimum(sessions, np.round(sessions * rng.uniform(0.75, 0.92, n))).astype(int)
        key_events = np.round(rng.poisson(sessions * ke_rate * rng.lognormal(0, 0.1, n)), 0)
        revenue = (
            np.round(key_events * profile.aov * rng.lognormal(0, 0.08, n), 2)
            if profile.goal == "purchase"
            else np.zeros(n)
        )

        out = pd.DataFrame({
            "date": df["d"].map(lambda d: d.strftime("%Y%m%d")),
            "property_id": client.ga4_property_id,
            "session_source": df["session_source"],
            "session_medium": df["session_medium"],
            "session_campaign_name": df["session_campaign_name"],
            "sessions": sessions.astype("int64"),
            "engaged_sessions": engaged.astype("int64"),
            "total_users": users.astype("int64"),
            "key_events": key_events.astype(float),
            "purchase_revenue": revenue,
            "client_id": client.client_id,
        })  # fmt: skip
        return out[COLUMNS]
