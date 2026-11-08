"""Shared scenario engine for the synthetic sources.

Every source derives its numbers from the same per-client profile, seeded RNGs and the
same day-level helpers, so cross-source relationships hold (e.g. GA4 paid-search sessions
are Google Ads clicks of the same day multiplied by a scenario ratio).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from agency_pipeline.config import GLOBAL_SEED, ClientConfig


def rng_for(client_id: str, source: str) -> np.random.Generator:
    """Deterministic generator derived from (global seed, client_id, source)."""
    digest = hashlib.sha256(f"{GLOBAL_SEED}:{client_id}:{source}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    name: str
    kind: str  # Google: advertising channel type. Meta: objective.
    share: float  # share of the platform's daily budget


@dataclass(frozen=True)
class Profile:
    """Business characteristics of a synthetic client."""

    weekend_factor: float
    trend: float  # relative growth across the window
    goal: str  # "purchase" or "lead"
    aov: float  # value per purchase / lead
    google_daily_spend: float
    google_cpc: float
    google_cvr: float
    meta_daily_spend: float
    meta_cpm: float
    meta_link_ctr: float
    meta_cvr: float
    organic_daily_clicks: float
    direct_daily_sessions: float
    google_campaigns: tuple[Campaign, ...]
    meta_campaigns: tuple[Campaign, ...]
    queries: tuple[str, ...]


def _queries(brand: list[str], heads: list[str], mods: list[str]) -> tuple[str, ...]:
    long_tail = [f"{m} {h}" for h in heads for m in mods]
    return tuple(brand + long_tail)[:36]


PROFILES: dict[str, Profile] = {
    "northwind-outdoor": Profile(
        weekend_factor=1.18,
        trend=0.12,
        goal="purchase",
        aov=96.0,
        google_daily_spend=460.0,
        google_cpc=1.10,
        google_cvr=0.034,
        meta_daily_spend=310.0,
        meta_cpm=9.5,
        meta_link_ctr=0.011,
        meta_cvr=0.022,
        organic_daily_clicks=210.0,
        direct_daily_sessions=180.0,
        google_campaigns=(
            Campaign("2100001", "Search - Brand", "SEARCH", 0.15),
            Campaign("2100002", "Search - Hiking Gear", "SEARCH", 0.35),
            Campaign("2100003", "PMax - All Products", "PERFORMANCE_MAX", 0.35),
            Campaign("2100004", "Display - Remarketing", "DISPLAY", 0.15),
        ),
        meta_campaigns=(
            Campaign("6100001", "Prospecting - Lookalike", "OUTCOME_SALES", 0.45),
            Campaign("6100002", "Retargeting - Cart Abandoners", "OUTCOME_SALES", 0.35),
            Campaign("6100003", "Catalog - Best Sellers", "OUTCOME_SALES", 0.20),
        ),
        queries=_queries(
            ["northwind outdoor", "northwind outdoor co", "northwind hiking boots"],
            ["hiking boots", "camping tent", "sleeping bag", "trekking poles", "rain jacket"],
            ["best", "waterproof", "lightweight", "cheap", "buy", "women's", "reviews"],
        ),
    ),
    "bluepeak-dental": Profile(
        weekend_factor=0.65,
        trend=0.06,
        goal="lead",
        aov=140.0,
        google_daily_spend=250.0,
        google_cpc=4.50,
        google_cvr=0.07,
        meta_daily_spend=120.0,
        meta_cpm=11.0,
        meta_link_ctr=0.009,
        meta_cvr=0.045,
        organic_daily_clicks=95.0,
        direct_daily_sessions=70.0,
        google_campaigns=(
            Campaign("2200001", "Search - Brand", "SEARCH", 0.15),
            Campaign("2200002", "Search - Emergency Dentist", "SEARCH", 0.35),
            Campaign("2200003", "Search - Invisalign", "SEARCH", 0.30),
            Campaign("2200004", "PMax - New Patients", "PERFORMANCE_MAX", 0.20),
        ),
        meta_campaigns=(
            Campaign("6200001", "Leads - Teeth Whitening Offer", "OUTCOME_LEADS", 0.55),
            Campaign("6200002", "Leads - Free Consultation", "OUTCOME_LEADS", 0.45),
        ),
        queries=_queries(
            ["bluepeak dental", "bluepeak dental group", "bluepeak dentist reviews"],
            ["dentist", "emergency dentist", "invisalign", "teeth whitening", "dental implants"],
            ["near me", "cost", "best", "open saturday", "private", "nhs", "same day"],
        ),
    ),
    "harbor-coffee": Profile(
        weekend_factor=1.22,
        trend=0.09,
        goal="purchase",
        aov=34.0,
        google_daily_spend=180.0,
        google_cpc=0.70,
        google_cvr=0.042,
        meta_daily_spend=140.0,
        meta_cpm=7.5,
        meta_link_ctr=0.013,
        meta_cvr=0.028,
        organic_daily_clicks=150.0,
        direct_daily_sessions=120.0,
        google_campaigns=(
            Campaign("2300001", "Search - Brand", "SEARCH", 0.20),
            Campaign("2300002", "Search - Coffee Beans", "SEARCH", 0.40),
            Campaign("2300003", "PMax - Subscriptions", "PERFORMANCE_MAX", 0.40),
        ),
        meta_campaigns=(
            Campaign("6300001", "Subscription Promo", "OUTCOME_SALES", 0.50),
            Campaign("6300002", "Retargeting - Site Visitors", "OUTCOME_SALES", 0.30),
            Campaign("6300003", "Reels - Roastery Story", "OUTCOME_TRAFFIC", 0.20),
        ),
        queries=_queries(
            ["harbor coffee", "harbor coffee roasters", "harbor coffee subscription"],
            [
                "coffee beans",
                "whole bean coffee",
                "coffee subscription",
                "espresso beans",
                "cold brew",
            ],
            ["best", "organic", "fresh roasted", "buy", "online", "decaf", "single origin"],
        ),
    ),
}

#: Share of Google Ads clicks that GA4 attributes to google/cpc, per scenario.
GOOGLE_SESSION_RATIO = {
    "healthy": (0.885, 0.02),
    "tracking_outage": (0.885, 0.02),
    "broken_autotagging": (0.175, 0.02),
}
META_SESSION_RATIO = (0.70, 0.02)
#: Clicks lost to broken auto-tagging resurface as google/organic and (direct)/(none).
LOST_TO_ORGANIC = 0.4
OUTAGE_DAYS = 3
OUTAGE_OFFSET = 10  # first outage day is this many days before the end date


def profile_for(client: ClientConfig) -> Profile:
    return PROFILES[client.client_id]


def date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def day_multiplier(
    dates: list[date], profile: Profile, rng: np.random.Generator, noise: float = 0.08
) -> np.ndarray:
    """Weekly seasonality x linear trend x lognormal noise, one value per day."""
    n = len(dates)
    weekend = np.array([d.weekday() >= 5 for d in dates])
    season = np.where(weekend, profile.weekend_factor, 1.0)
    trend = 1.0 + profile.trend * np.arange(n) / max(n - 1, 1)
    return season * trend * rng.lognormal(0.0, noise, n)


def outage_dates(client: ClientConfig, end: date) -> set[date]:
    """Days on which GA4 collects (almost) nothing, for the tracking_outage scenario."""
    if client.scenario != "tracking_outage":
        return set()
    first = end - timedelta(days=OUTAGE_OFFSET + OUTAGE_DAYS - 1)
    return {first + timedelta(days=i) for i in range(OUTAGE_DAYS)}


def as_frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)
