import re
from datetime import date
from pathlib import Path

import pytest

from agency_pipeline.audit.runner import run_audit
from agency_pipeline.audit.sample_exports import generate
from agency_pipeline.audit.scorecard import render_scorecard
from agency_pipeline.sources.csv_exports import ExportError, ga4, google_ads, gsc, meta_ads
from agency_pipeline.sources.csv_exports._common import parse_number
from agency_pipeline.sources.synthetic.google_ads import COLUMNS as GOOGLE_COLUMNS
from agency_pipeline.sources.synthetic.meta_ads import COLUMNS as META_COLUMNS


def write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_number():
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("1.234,56") == 1234.56
    assert parse_number("--") is None
    assert parse_number("$12.30") == 12.30
    assert parse_number("12,5") == 12.5
    assert parse_number("1,234") == 1234


def test_google_ads_title_lines_totals_and_aliases(tmp_path):
    p = write(
        tmp_path,
        "g.csv",
        "Campaign report\n"
        '"October 2, 2026 - October 3, 2026"\n'
        "  day , CAMPAIGN,Campaign Type,Impr.,Clicks,Cost,Conversions,Conv. value,Currency code\n"
        '"Oct 2, 2026",Search - Brand,Search,"1,204",96,"1,412.50",7,--,USD\n'
        '2026-10-03,Search - Brand,Performance Max,--,"1,010",12.25,0,"2,000.00",USD\n'
        'Total: Account,--,--,"1,204","1,106","1,424.75",7,"2,000.00",--\n'
        'Total: Campaigns,--,--,"1,204","1,106","1,424.75",7,"2,000.00",--\n',
    )
    df = google_ads.parse(p)
    assert list(df.columns) == GOOGLE_COLUMNS
    assert len(df) == 2
    first = df.iloc[0]
    assert first.metrics_clicks == 96 and first.metrics_cost_micros == 1_412_500_000
    assert first.metrics_impressions == 1204 and first.metrics_conversions_value == 0
    assert df.iloc[1].metrics_impressions == 0
    assert df.iloc[1].campaign_advertising_channel_type == "PERFORMANCE_MAX"
    assert df.attrs["currency"] == "USD"


def test_google_ads_missing_columns_error(tmp_path):
    p = write(tmp_path, "g.csv", "Day,Campaign,Impr.\n2026-10-02,A,5\n")
    with pytest.raises(ExportError) as e:
        google_ads.parse(p)
    msg = str(e.value)
    assert "Clicks" in msg and "Cost" in msg and "missing required" in msg


def test_ga4_comments_combined_and_separate_columns(tmp_path):
    combined = write(
        tmp_path,
        "a.csv",
        "# Start date: 20261002\n# End date: 20261003\n\n"
        "Date,Session source / medium,Session campaign,Sessions,Total users,Conversions\n"
        '20261002,google / cpc,brand,"1,000",900,12\n'
        "20261002,(direct) / (none),(not set),50,40,0\n",
    )
    df = ga4.parse(combined)
    assert set(df.session_source) == {"google", "(direct)"}
    assert df[df.session_source == "google"].iloc[0].key_events == 12
    assert df.iloc[0].date == "20261002"
    assert "Engaged sessions" in " ".join(df.attrs["warnings"])
    separate = write(
        tmp_path,
        "b.csv",
        "Date,Session source,Session medium,Sessions\n2026-10-02,fb,paid,5\n",
    )
    df2 = ga4.parse(separate)
    assert df2.iloc[0].session_medium == "paid" and df2.iloc[0].date == "20261002"
    with pytest.raises(ExportError, match="source"):
        ga4.parse(write(tmp_path, "c.csv", "Date,Sessions\n20261002,5\n"))


def test_meta_variants(tmp_path):
    p = write(
        tmp_path,
        "m.csv",
        "Reporting starts,Reporting ends,Campaign name,Amount spent (GBP),Impressions,"
        "Link clicks,Purchases,Purchases conversion value\n"
        '2026-10-02,2026-10-02,Promo,"1,234.50","41,200",455,9,864.00\n'
        "2026-10-02,2026-10-02,Traffic,10,1000,50,--,--\n",
    )
    df = meta_ads.parse(p)
    assert list(df.columns) == META_COLUMNS
    row = df[df.campaign_name == "Promo"].iloc[0]
    assert row.spend == "1234.50" and row.inline_link_clicks == "455"
    assert df.attrs["currency"] == "GBP"
    assert '"link_click", "value": "455"' in row.actions
    assert '"value": "864.00"' in row.action_values
    assert len(set(df.campaign_id)) == 2  # ids derived from names
    assert set(df.campaign_id) == set(meta_ads.parse(p).campaign_id)  # and stable
    with pytest.raises(ExportError, match="Link clicks"):
        meta_ads.parse(write(tmp_path, "x.csv", "Day,Campaign name,Amount spent,Impressions\n"))


def test_gsc_percent_ctr(tmp_path):
    p = write(
        tmp_path,
        "d.csv",
        'Date,Clicks,Impressions,CTR,Position\n2026-10-02,118,"2,310",5.1%,14.2\n',
    )
    df = gsc.parse(p)
    assert df.iloc[0].ctr == pytest.approx(0.051)
    assert df.iloc[0]["query"] == "(all)" and df.iloc[0].impressions == 2310


@pytest.fixture(scope="module")
def audits(tmp_path_factory):
    out = {}
    for cid in ("bluepeak-dental", "harbor-coffee", "northwind-outdoor"):
        d = tmp_path_factory.mktemp(cid)
        p = generate(cid, d)
        out[cid] = run_audit(
            google_ads_path=p["google_ads"],
            ga4_path=p["ga4"],
            meta_path=p["meta"],
            gsc_path=p["gsc"],
            client_name=cid,
        )
    return out


def statuses(result):
    return {c.number: c.status for c in result.checks}


def test_bluepeak_red_on_google_ratio(audits):
    r = audits["bluepeak-dental"]
    assert statuses(r)[1] == "red"
    assert statuses(r)[5] == "green"
    assert r.score < 50
    assert (r.period_start, r.period_end) == (date(2026, 10, 2), date(2026, 10, 31))


def test_harbor_outage_detected(audits):
    r = audits["harbor-coffee"]
    s = statuses(r)
    assert s[5] == "red" and s[1] == "green"
    assert "Oct 19" in r.checks[4].what


def test_northwind_scores_high(audits):
    r = audits["northwind-outdoor"]
    assert r.score >= 85
    assert statuses(r)[1] == statuses(r)[5] == statuses(r)[6] == "green"


def test_missing_inputs_not_assessed(tmp_path):
    p = generate("northwind-outdoor", tmp_path)
    r = run_audit(google_ads_path=p["google_ads"], ga4_path=p["ga4"], client_name="X")
    assert statuses(r)[2] == "not_assessed"
    assert r.score >= 85  # excluded from the score, not counted as a failure
    assert "Not assessed" in render_scorecard(r)


def test_scorecard_html_is_self_contained(audits):
    for r in audits.values():
        html = render_scorecard(r, today=date(2026, 11, 8))
        assert "Tracking &amp; Reporting Audit" in html
        assert "Ercan Tuncay" in html and "hello@example.com" in html
        assert not re.findall(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', html)
        assert "http://" not in html and "https://" not in html
        assert "<script" not in html
