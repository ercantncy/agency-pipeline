import pandas as pd
import pytest

from agency_pipeline.sources import get_sources
from tests.conftest import END, START


def frame(source_name, client):
    source = next(s for s in get_sources() if s.name == source_name)
    return source.extract(client, START, END)


@pytest.mark.parametrize("source", [s.name for s in get_sources()])
def test_deterministic(source, clients):
    client = clients["bluepeak-dental"]
    pd.testing.assert_frame_equal(frame(source, client), frame(source, client))


def test_internal_consistency(clients):
    for client in clients.values():
        ads = frame("google_ads", client)
        assert (ads.metrics_clicks <= ads.metrics_impressions).all()
        assert (ads.metrics_conversions <= ads.metrics_clicks).all()
        assert (ads.metrics_cost_micros >= 0).all()
        ga4 = frame("ga4", client)
        assert (ga4.engaged_sessions <= ga4.sessions).all()
        assert (ga4.total_users <= ga4.sessions).all()
        gsc = frame("gsc", client)
        assert (gsc.clicks <= gsc.impressions).all()
        meta = frame("meta_ads", client)
        assert (meta.inline_link_clicks.astype(int) <= meta.impressions.astype(int)).all()
        assert 20 <= gsc["query"].nunique() <= 40


def ratio(client):
    ads = frame("google_ads", client)
    ga4 = frame("ga4", client)
    cpc = ga4[(ga4.session_source == "google") & (ga4.session_medium == "cpc")]
    return cpc.sessions.sum() / ads.metrics_clicks.sum()


def test_healthy_ratio(clients):
    assert 0.8 <= ratio(clients["northwind-outdoor"]) <= 0.95


def test_broken_autotagging_ratio(clients):
    assert 0.12 <= ratio(clients["bluepeak-dental"]) <= 0.25


def test_harbor_outage(clients):
    ga4 = frame("ga4", clients["harbor-coffee"])
    daily = ga4.groupby("date").sessions.sum().sort_index()
    median = daily.median()
    low = pd.to_datetime(daily[daily < 0.05 * median].index, format="%Y%m%d")
    assert len(low) == 3
    assert (low[1:] - low[:-1]).max() == pd.Timedelta(days=1)
    assert (pd.Timestamp(END) - low.max()).days >= 9
