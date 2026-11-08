from datetime import date

import pytest

from agency_pipeline.config import load_clients

START, END = date(2026, 7, 4), date(2026, 10, 31)


@pytest.fixture(scope="session")
def clients():
    return {c.client_id: c for c in load_clients()}


@pytest.fixture(scope="session")
def built_warehouse(tmp_path_factory):
    """Warehouse built once per session (extract-load + dbt) on a temp path."""
    from typer.testing import CliRunner

    from agency_pipeline.cli import app

    path = tmp_path_factory.mktemp("session_wh") / "warehouse.duckdb"
    mp = pytest.MonkeyPatch()
    mp.setenv("AGENCY_PIPELINE_WAREHOUSE", str(path))
    runner = CliRunner()
    assert runner.invoke(app, ["extract-load"]).exit_code == 0
    result = runner.invoke(app, ["transform"])
    assert result.exit_code == 0, result.output
    yield path
    mp.undo()


@pytest.fixture()
def con(built_warehouse):
    import duckdb

    c = duckdb.connect(str(built_warehouse), read_only=True)
    yield c
    c.close()
