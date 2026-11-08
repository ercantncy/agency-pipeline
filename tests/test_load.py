import duckdb
import pytest

from agency_pipeline import load
from agency_pipeline.config import load_clients
from agency_pipeline.sources import get_sources
from tests.conftest import START

END = START.replace(day=20)  # short window keeps the test fast


def counts(path):
    con = duckdb.connect(str(path))
    try:
        tables = [*load.RAW_TABLES, "clients"]
        return {t: con.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0] for t in tables}
    finally:
        con.close()


def test_load_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "wh.duckdb"
    monkeypatch.setenv("AGENCY_PIPELINE_WAREHOUSE", str(path))
    clients = load_clients()
    first = load.extract_load(clients, get_sources(), START, END)
    after_first = counts(path)
    load.extract_load(clients, get_sources(), START, END)
    assert counts(path) == after_first
    assert after_first["clients"] == 3
    assert all(n > 0 for n in after_first.values())
    assert first["clients"] == 3


def test_column_types(tmp_path):
    path = tmp_path / "wh.duckdb"
    load.extract_load(load_clients()[:1], get_sources(), START, END, warehouse=path)
    con = duckdb.connect(str(path))
    types = dict(
        con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='raw' AND table_name='ga4_traffic_daily'"
        ).fetchall()
    )
    assert types["sessions"] == "BIGINT" and types["date"] == "VARCHAR"
    assert types["_loaded_at"] == "TIMESTAMP" and types["key_events"] == "DOUBLE"


@pytest.mark.parametrize("table", list(load.RAW_TABLES))
def test_tables_have_client_and_loaded_at(table, tmp_path):
    path = tmp_path / "wh.duckdb"
    load.extract_load(load_clients()[:1], get_sources(), START, END, warehouse=path)
    con = duckdb.connect(str(path))
    cols = {r[0] for r in con.execute(f"DESCRIBE raw.{table}").fetchall()}
    assert {"client_id", "_loaded_at"} <= cols
