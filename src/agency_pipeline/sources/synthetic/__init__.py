"""Synthetic sources: deterministic, scenario-driven stand-ins for the real platform APIs."""

from agency_pipeline.sources.base import Source
from agency_pipeline.sources.synthetic.ga4 import Ga4Source
from agency_pipeline.sources.synthetic.google_ads import GoogleAdsSource
from agency_pipeline.sources.synthetic.gsc import GscSource
from agency_pipeline.sources.synthetic.meta_ads import MetaAdsSource


def get_sources() -> list[Source]:
    """Registry of all sources; GA4 last because it is derived from the others."""
    return [GoogleAdsSource(), MetaAdsSource(), GscSource(), Ga4Source()]


__all__ = ["Ga4Source", "GoogleAdsSource", "GscSource", "MetaAdsSource", "get_sources"]
