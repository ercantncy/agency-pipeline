import json

import pytest
import yaml

from agency_pipeline import config
from agency_pipeline.export_web import export_web

TOP_KEYS = {
    "client",
    "monthly",
    "paid_daily",
    "campaigns_monthly",
    "web_daily",
    "seo_daily",
    "seo_queries_monthly",
    "reconciliation_daily",
    "thresholds",
    "months",
}


@pytest.fixture(scope="module")
def exported(built_warehouse, tmp_path_factory):
    import duckdb

    out = tmp_path_factory.mktemp("web")
    con = duckdb.connect(str(built_warehouse), read_only=True)
    try:
        paths = export_web(con, out, None, False)
    finally:
        con.close()
    return out, paths


def test_manifest_shape(exported):
    out, _ = exported
    m = json.loads((out / "manifest.json").read_text())
    assert m["months"] == ["2026-07", "2026-08", "2026-09", "2026-10"]
    assert m["default_month"] == "2026-10"
    assert set(m["agency"]) == {"name", "logo_text", "primary_color"}
    ids = {c["client_id"] for c in m["clients"]}
    assert "bluepeak-dental" in ids
    for c in m["clients"]:
        assert set(c) == {
            "client_id",
            "client_name",
            "currency",
            "scenario",
            "alert_counts_by_month",
        }


def test_client_files_have_all_keys(exported):
    out, _ = exported
    m = json.loads((out / "manifest.json").read_text())
    for c in m["clients"]:
        d = json.loads((out / "clients" / f"{c['client_id']}.json").read_text())
        assert set(d) == TOP_KEYS
        assert set(d["months"]) == set(m["months"])
        assert {r["channel"] for r in d["monthly"]} == {"google_ads", "meta_ads", "total_paid"}


def test_bluepeak_critical_reconciliation(exported):
    out, _ = exported
    d = json.loads((out / "clients" / "bluepeak-dental.json").read_text())
    alerts = d["months"]["2026-10"]["alerts"]
    assert any(a["severity"] == "critical" and a["check"] == "reconciliation" for a in alerts)
    assert d["months"]["2026-10"]["commentary"]["source"] == "template"
    m = json.loads((out / "manifest.json").read_text())
    bp = next(c for c in m["clients"] if c["client_id"] == "bluepeak-dental")
    assert bp["alert_counts_by_month"]["2026-10"]["critical"] >= 1


def test_thresholds_match_dbt_vars(exported):
    out, _ = exported
    v = yaml.safe_load((config.PROJECT_ROOT / "dbt" / "dbt_project.yml").read_text())["vars"]
    d = json.loads((out / "clients" / "bluepeak-dental.json").read_text())
    assert d["thresholds"] == {
        "google_ads": {
            "warn": v["recon_google_ads_warn"],
            "critical": v["recon_google_ads_critical"],
        },
        "meta_ads": {"warn": v["recon_meta_ads_warn"], "critical": v["recon_meta_ads_critical"]},
    }


def test_no_nan_in_output(exported):
    _, paths = exported
    for p in paths:
        text = p.read_text()
        assert "NaN" not in text and "Infinity" not in text
        json.loads(text, parse_constant=lambda c: pytest.fail(f"bad constant {c}"))
