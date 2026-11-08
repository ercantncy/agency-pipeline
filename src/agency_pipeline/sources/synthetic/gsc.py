"""Synthetic Search Console searchAnalytics (dimensions: date, query, page)."""

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
    "date",
    "site_url",
    "query",
    "page",
    "clicks",
    "impressions",
    "ctr",
    "position",
    "client_id",
]


class GscSource(Source):
    name = "gsc"
    table = "gsc_search_daily"

    def extract(self, client: ClientConfig, start: date, end: date) -> pd.DataFrame:
        profile = profile_for(client)
        rng = rng_for(client.client_id, self.name)
        dates = date_range(start, end)
        mult = day_multiplier(dates, profile, rng)
        queries = profile.queries
        n_q = len(queries)

        # Long-tail demand: Zipf-like weights; brand queries (first 3) rank near the top.
        weights = 1.0 / np.arange(1, n_q + 1) ** 1.1
        weights /= weights.sum()
        base_position = np.clip(rng.normal(9, 4, n_q), 1.2, 30)
        base_position[:3] = [1.1, 1.3, 1.8]
        pages = [self._page_for(client, q, i) for i, q in enumerate(queries)]
        # Impressions per click-through: roughly 1 click per 14 impressions at the top, fewer lower.
        daily_clicks = profile.organic_daily_clicks * mult

        frames = []
        for q_idx, query in enumerate(queries):
            position = np.clip(base_position[q_idx] + rng.normal(0, 0.6, len(dates)), 1.0, 50.0)
            ctr = np.clip(0.32 * np.exp(-0.21 * (position - 1)), 0.004, 0.5)
            impressions = rng.poisson(daily_clicks * weights[q_idx] / ctr)
            clicks = rng.binomial(impressions, ctr)
            frames.append(pd.DataFrame({
                "date": dates,
                "site_url": client.gsc_site_url,
                "query": query,
                "page": pages[q_idx],
                "clicks": clicks.astype("int64"),
                "impressions": impressions.astype("int64"),
                "position": np.round(position, 2),
            }))  # fmt: skip
        df = pd.concat(frames, ignore_index=True)
        df = df[df["impressions"] > 0].copy()  # the API omits rows with no impressions
        df["ctr"] = df["clicks"] / df["impressions"]
        df["client_id"] = client.client_id
        return df.sort_values(["date", "query"], ignore_index=True)[COLUMNS]

    @staticmethod
    def _page_for(client: ClientConfig, query: str, idx: int) -> str:
        base = client.gsc_site_url.rstrip("/")
        if idx < 3:
            return base + "/"
        slug = "-".join(query.split()[-2:])
        return f"{base}/{slug}/"
