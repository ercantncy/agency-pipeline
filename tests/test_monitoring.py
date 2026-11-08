from __future__ import annotations

import json
from datetime import date

from typer.testing import CliRunner

from agency_pipeline.cli import app
from agency_pipeline.monitoring import run_checks

END = date(2026, 10, 31)


def test_bluepeak_reconciliation_critical(con):
    alerts = run_checks(con, END, "bluepeak-dental")
    recon = [a for a in alerts if a.check == "reconciliation"]
    assert len(recon) == 1
    assert recon[0].severity == "critical"
    assert "Google Ads" in recon[0].message and "GA4" in recon[0].message
    assert not [a for a in alerts if a.check == "volume_drop"]


def test_harbor_outage_volume_drop(con):
    alerts = run_checks(con, END, "harbor-coffee")
    drops = [a for a in alerts if a.check == "volume_drop"]
    assert len(drops) == 1
    assert drops[0].severity == "critical"
    assert drops[0].start_date == date(2026, 10, 19)
    assert drops[0].end_date == date(2026, 10, 21)
    channels = [a for a in alerts if a.check == "reconciliation"]
    assert len(channels) == 2


def test_northwind_clean(con):
    assert run_checks(con, END, "northwind-outdoor") == []


def test_freshness_flags_stale_data(con):
    alerts = run_checks(con, date(2026, 11, 15), "northwind-outdoor")
    assert alerts and all(a.check == "freshness" and a.severity == "critical" for a in alerts)


def test_cli_check_exit_code_and_json(built_warehouse):
    runner = CliRunner()
    result = runner.invoke(app, ["check", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert {a["client_id"] for a in data} == {"bluepeak-dental", "harbor-coffee"}
    assert runner.invoke(app, ["check", "--client", "northwind-outdoor"]).exit_code == 0
