"""End-to-end: extract-load + dbt build on a temporary warehouse."""

from __future__ import annotations

import duckdb
import pytest
from typer.testing import CliRunner

from agency_pipeline.cli import app

MARTS = [
    "dim_client",
    "fct_paid_daily",
    "fct_web_daily",
    "fct_paid_vs_ga4_reconciliation",
    "fct_seo_daily",
    "fct_seo_query_monthly",
    "rpt_client_monthly",
]


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    path = tmp_path_factory.mktemp("wh") / "warehouse.duckdb"
    mp = pytest.MonkeyPatch()
    mp.setenv("AGENCY_PIPELINE_WAREHOUSE", str(path))
    runner = CliRunner()
    assert runner.invoke(app, ["extract-load"]).exit_code == 0
    result = runner.invoke(app, ["transform"])
    assert result.exit_code == 0, result.output
    yield path
    mp.undo()


def test_marts_populated_and_bluepeak_critical(warehouse):
    con = duckdb.connect(str(warehouse), read_only=True)
    for table in MARTS:
        assert con.execute(f"select count(*) from marts.{table}").fetchone()[0] > 0, table
    critical, total = con.execute(
        "select count(*) filter (status = 'critical'), count(*) from "
        "marts.fct_paid_vs_ga4_reconciliation "
        "where client_id = 'bluepeak-dental' and channel = 'google_ads'"
    ).fetchone()
    assert critical / total > 0.9
