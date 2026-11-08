"""Synthetic Meta Marketing API insights (level=campaign, time_increment=1)."""

from __future__ import annotations

import json
from datetime import date

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
    "date_start", "account_id", "campaign_id", "campaign_name", "objective", "impressions",
    "inline_link_clicks", "spend", "actions", "action_values", "client_id",
]  # fmt: skip


class MetaAdsSource(Source):
    name = "meta_ads"
    table = "meta_ads_insights_daily"

    def extract(self, client: ClientConfig, start: date, end: date) -> pd.DataFrame:
        profile = profile_for(client)
        rng = rng_for(client.client_id, self.name)
        dates = date_range(start, end)
        mult = day_multiplier(dates, profile, rng)
        is_lead = profile.goal == "lead"
        rows = []
        for campaign in profile.meta_campaigns:
            for i, day in enumerate(dates):
                spend = profile.meta_daily_spend * campaign.share * mult[i] * rng.lognormal(0, 0.10)
                impressions = int(spend / profile.meta_cpm * 1000)
                clicks = int(
                    rng.binomial(impressions, profile.meta_link_ctr * rng.lognormal(0, 0.05))
                )
                # Traffic campaigns do not optimise for conversions.
                cvr = 0.0 if campaign.kind == "OUTCOME_TRAFFIC" else profile.meta_cvr
                conversions = int(rng.binomial(clicks, min(cvr * rng.lognormal(0, 0.10), 1.0)))
                purchases, leads = (0, conversions) if is_lead else (conversions, 0)
                value = round(purchases * profile.aov * rng.lognormal(0, 0.05), 2)
                actions = [
                    {"action_type": "link_click", "value": str(clicks)},
                    {
                        "action_type": "offsite_conversion.fb_pixel_purchase",
                        "value": str(purchases),
                    },
                    {"action_type": "offsite_conversion.fb_pixel_lead", "value": str(leads)},
                ]
                action_values = (
                    [
                        {
                            "action_type": "offsite_conversion.fb_pixel_purchase",
                            "value": f"{value:.2f}",
                        }
                    ]
                    if purchases
                    else []
                )
                rows.append({
                    "date_start": day.isoformat(),
                    "account_id": client.meta_account_id,
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.name,
                    "objective": campaign.kind,
                    "impressions": str(impressions),
                    "inline_link_clicks": str(clicks),
                    "spend": f"{spend:.2f}",
                    "actions": json.dumps(actions),
                    "action_values": json.dumps(action_values),
                    "client_id": client.client_id,
                })  # fmt: skip
        return pd.DataFrame(rows, columns=COLUMNS)
