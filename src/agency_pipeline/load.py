"""Load extracted frames into the DuckDB `raw` schema (explicit DDL, idempotent)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from agency_pipeline import config
from agency_pipeline.config import ClientConfig
from agency_pipeline.sources.base import Source

#: table -> (column DDL, SQL expression yielding the row's DATE, used for range deletes).
RAW_TABLES: dict[str, tuple[str, str]] = {
    "google_ads_campaign_daily": (
        """
        segments_date DATE, customer_id VARCHAR, campaign_id VARCHAR, campaign_name VARCHAR,
        campaign_advertising_channel_type VARCHAR, metrics_impressions BIGINT,
        metrics_clicks BIGINT, metrics_cost_micros BIGINT, metrics_conversions DOUBLE,
        metrics_conversions_value DOUBLE
        """,
        "segments_date",
    ),
    "meta_ads_insights_daily": (
        """
        date_start VARCHAR, account_id VARCHAR, campaign_id VARCHAR, campaign_name VARCHAR,
        objective VARCHAR, impressions VARCHAR, inline_link_clicks VARCHAR, spend VARCHAR,
        actions VARCHAR, action_values VARCHAR
        """,
        "CAST(date_start AS DATE)",
    ),
    "ga4_traffic_daily": (
        """
        date VARCHAR, property_id VARCHAR, session_source VARCHAR, session_medium VARCHAR,
        session_campaign_name VARCHAR, sessions BIGINT, engaged_sessions BIGINT,
        total_users BIGINT, key_events DOUBLE, purchase_revenue DOUBLE
        """,
        "strptime(date, '%Y%m%d')::DATE",
    ),
    "gsc_search_daily": (
        """
        date DATE, site_url VARCHAR, query VARCHAR, page VARCHAR, clicks BIGINT,
        impressions BIGINT, ctr DOUBLE, position DOUBLE
        """,
        "date",
    ),
}

CLIENTS_DDL = """
    client_id VARCHAR, client_name VARCHAR, agency_name VARCHAR, agency_primary_color VARCHAR,
    agency_logo_text VARCHAR, currency VARCHAR, scenario VARCHAR,
    google_ads_customer_id VARCHAR, meta_account_id VARCHAR, ga4_property_id VARCHAR,
    gsc_site_url VARCHAR
"""


def connect(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open the warehouse (default: current WAREHOUSE_PATH, honouring the env override)."""
    path = Path(path) if path else config.warehouse_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table, (ddl, _) in RAW_TABLES.items():
        con.execute(
            f"CREATE TABLE IF NOT EXISTS raw.{table} "
            f"({ddl}, client_id VARCHAR, _loaded_at TIMESTAMP)"
        )
    con.execute(f"CREATE TABLE IF NOT EXISTS raw.clients ({CLIENTS_DDL}, _loaded_at TIMESTAMP)")


def load_frame(
    con: duckdb.DuckDBPyConnection,
    source: Source,
    df: pd.DataFrame,
    client: ClientConfig,
    start: date,
    end: date,
) -> int:
    """Replace the client's rows for [start, end] in `raw.<source.table>`; return rows loaded."""
    ddl, date_expr = RAW_TABLES[source.table]
    columns = [c.split()[0] for c in ddl.replace("\n", " ").split(",") if c.strip()]
    columns.append("client_id")
    con.execute("BEGIN")
    try:
        con.execute(
            f"DELETE FROM raw.{source.table} WHERE client_id = ? AND {date_expr} BETWEEN ? AND ?",
            [client.client_id, start, end],
        )
        con.register("_stage", df[columns])
        cols = ", ".join(columns)
        con.execute(f"INSERT INTO raw.{source.table} SELECT {cols}, now()::TIMESTAMP FROM _stage")
        con.unregister("_stage")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(df)


def load_clients_table(con: duckdb.DuckDBPyConnection, clients: list[ClientConfig]) -> int:
    """Replace raw.clients with the flattened client registry."""
    rows = [
        (
            c.client_id, c.client_name, c.agency_brand.name, c.agency_brand.primary_color,
            c.agency_brand.logo_text, c.currency, c.scenario, c.google_ads_customer_id,
            c.meta_account_id, c.ga4_property_id, c.gsc_site_url,
        )
        for c in clients
    ]  # fmt: skip
    con.execute("DELETE FROM raw.clients")
    con.executemany(
        "INSERT INTO raw.clients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now()::TIMESTAMP)", rows
    )
    return len(rows)


def extract_load(
    clients: list[ClientConfig],
    sources: list[Source],
    start: date,
    end: date,
    warehouse: Path | None = None,
) -> dict[str, int]:
    """Run every source for every client into the warehouse; return rows loaded per raw table."""
    counts: dict[str, int] = {}
    con = connect(warehouse)
    try:
        ensure_schema(con)
        for client in clients:
            for source in sources:
                df = source.extract(client, start, end)
                n = load_frame(con, source, df, client, start, end)
                counts[source.table] = counts.get(source.table, 0) + n
        all_clients = config.load_clients()
        counts["clients"] = load_clients_table(con, all_clients)
    finally:
        con.close()
    return counts
