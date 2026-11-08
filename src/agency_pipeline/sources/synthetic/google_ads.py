"""Synthetic Google Ads `campaign` report."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from agency_pipeline.config import ClientConfig
from agency_pipeline.sources.base import Source
from agency_pipeline.sources.synthetic.scenario import (
    date_range,
    day_multiplier,
    profile_for,
    rng_for,
)

COLUMNS = [
    "segments_date", "customer_id", "campaign_id", "campaign_name",
    "campaign_advertising_channel_type", "metrics_impressions", "metrics_clicks",
    "metrics_cost_micros", "metrics_conversions", "metrics_conversions_value", "client_id",
]  # fmt: skip

#: (click-through rate, cost-per-click multiplier, conversion-rate multiplier) by channel type.
CHANNEL_SHAPE = {
    "SEARCH": (0.060, 1.00, 1.00),
    "PERFORMANCE_MAX": (0.020, 0.80, 0.85),
    "DISPLAY": (0.006, 0.35, 0.40),
}


class GoogleAdsSource(Source):
    name = "google_ads"
    table = "google_ads_campaign_daily"

    def extract(self, client: ClientConfig, start: date, end: date) -> pd.DataFrame:
        profile = profile_for(client)
        rng = rng_for(client.client_id, self.name)
        dates = date_range(start, end)
        mult = day_multiplier(dates, profile, rng)
        rows = []
        for campaign in profile.google_campaigns:
            ctr, cpc_mod, cvr_mod = CHANNEL_SHAPE[campaign.kind]
            noise = rng.lognormal(0.0, 0.10, (len(dates), 4))
            for i, day in enumerate(dates):
                cpc = profile.google_cpc * cpc_mod * noise[i, 0]
                spend = profile.google_daily_spend * campaign.share * mult[i] * noise[i, 1]
                clicks = int(round(spend / cpc))
                impressions = max(clicks, int(round(clicks / (ctr * noise[i, 2]))))
                conversions = min(clicks, clicks * profile.google_cvr * cvr_mod * noise[i, 3])
                value = conversions * profile.aov * rng.lognormal(0.0, 0.05)
                rows.append({
                    "segments_date": day,
                    "customer_id": client.google_ads_customer_id.replace("-", ""),
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.name,
                    "campaign_advertising_channel_type": campaign.kind,
                    "metrics_impressions": impressions,
                    "metrics_clicks": clicks,
                    "metrics_cost_micros": int(round(clicks * cpc * 1_000_000)),
                    "metrics_conversions": round(float(conversions), 2),
                    "metrics_conversions_value": round(float(value), 2),
                    "client_id": client.client_id,
                })  # fmt: skip
        return pd.DataFrame(rows, columns=COLUMNS).astype({"metrics_cost_micros": np.int64})
