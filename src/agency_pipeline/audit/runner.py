"""Audit pipeline: CSV exports -> isolated temp warehouse -> dbt -> checks -> scorecard data."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pandas as pd

from agency_pipeline import config, load
from agency_pipeline.audit import checks as checks_mod
from agency_pipeline.audit.checks import AuditInputs, CheckResult, score
from agency_pipeline.config import AgencyBrand, ClientConfig
from agency_pipeline.sources.csv_exports import ga4, google_ads, gsc, meta_ads

AUDIT_CLIENT_ID = "audit"


class AuditError(RuntimeError):
    """The audit could not be completed (message is safe to show to the consultant)."""


@dataclass
class AuditResult:
    client_name: str
    currency: str
    period_start: date
    period_end: date
    checks: list[CheckResult]
    score: int | None
    inputs: dict[str, bool]
    notes: list[str] = field(default_factory=list)

    @property
    def days(self) -> int:
        return (self.period_end - self.period_start).days + 1


def _dbt_build(warehouse: Path) -> None:
    dbt_dir = str(config.PROJECT_ROOT / "dbt")
    env = {**os.environ, config.WAREHOUSE_ENV_VAR: str(warehouse.resolve())}
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    proc = subprocess.run(
        [*cmd, "build", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir, "--quiet"],
        env=env, capture_output=True, text=True,
    )  # fmt: skip
    if proc.returncode != 0:
        # Test failures (e.g. an unusual currency code) must not block the audit as long as
        # the models themselves were built; the checks need only staging + marts tables.
        con = duckdb.connect(str(warehouse), read_only=True)
        try:
            built = {
                r[0]
                for r in con.execute(
                    "select table_name from information_schema.tables where table_schema = 'marts'"
                ).fetchall()
            }
        finally:
            con.close()
        needed = {"fct_paid_daily", "fct_web_daily", "fct_paid_vs_ga4_reconciliation"}
        if not needed <= built:
            tail = (proc.stdout + proc.stderr).strip()[-2000:]
            raise AuditError(f"dbt build failed:\n{tail}")


def run_audit(
    *,
    google_ads_path: Path,
    ga4_path: Path,
    client_name: str,
    meta_path: Path | None = None,
    gsc_path: Path | None = None,
    currency: str | None = None,
    consultant: str = "Ercan Tuncay",
) -> AuditResult:
    """Parse the exports, load them into a throwaway warehouse, run dbt and the six checks."""
    frames: dict[str, pd.DataFrame] = {
        "google_ads": google_ads.parse(google_ads_path, AUDIT_CLIENT_ID),
        "ga4": ga4.parse(ga4_path, AUDIT_CLIENT_ID),
    }
    if meta_path:
        frames["meta"] = meta_ads.parse(meta_path, AUDIT_CLIENT_ID)
    if gsc_path:
        frames["gsc"] = gsc.parse(gsc_path, AUDIT_CLIENT_ID)

    notes = [w for df in frames.values() for w in df.attrs.get("warnings", [])]
    start_end = {
        "google_ads": _bounds(frames["google_ads"]["segments_date"]),
        "ga4": _bounds(pd.to_datetime(frames["ga4"]["date"], format="%Y%m%d")),
    }
    if "meta" in frames:
        start_end["meta"] = _bounds(pd.to_datetime(frames["meta"]["date_start"]))
    if "gsc" in frames:
        start_end["gsc"] = _bounds(frames["gsc"]["date"])
    start = max(s for s, _ in start_end.values())
    end = min(e for _, e in start_end.values())
    if start > end:
        raise AuditError(
            "The exports do not overlap in time: "
            + ", ".join(f"{k} {s} to {e}" for k, (s, e) in start_end.items())
        )
    if len({v for v in start_end.values()}) > 1:
        notes.append(
            "Export date ranges differ ("
            + ", ".join(f"{k} {s:%b %d} to {e:%b %d}" for k, (s, e) in start_end.items())
            + f"); only the overlap {start:%b %d} to {end:%b %d} was audited."
        )
    currency = (
        currency
        or frames["google_ads"].attrs.get("currency")
        or (frames["meta"].attrs.get("currency") if "meta" in frames else None)
        or "USD"
    ).upper()
    for kind, df in (("Google Ads", frames["google_ads"]), ("Meta", frames.get("meta"))):
        found = df.attrs.get("currency") if df is not None else None
        if found and found != currency:
            notes.append(f"{kind} export is in {found} but the audit currency is {currency}.")

    client = ClientConfig(
        client_id=AUDIT_CLIENT_ID, client_name=client_name,
        agency_brand=AgencyBrand(consultant, "#1f3a5f", consultant), currency=currency,
        google_ads_customer_id="audit", meta_account_id="audit", ga4_property_id="audit",
        gsc_site_url="(audit)", scenario="audit",
    )  # fmt: skip

    with tempfile.TemporaryDirectory(prefix="agency-audit-") as tmp:
        warehouse = Path(tmp) / "audit.duckdb"
        previous = os.environ.get(config.WAREHOUSE_ENV_VAR)
        os.environ[config.WAREHOUSE_ENV_VAR] = str(warehouse)
        try:
            _load(warehouse, client, frames, start, end)
            _dbt_build(warehouse)
            con = duckdb.connect(str(warehouse), read_only=True)
            try:
                inputs = AuditInputs(
                    con=con, client_id=AUDIT_CLIENT_ID, start=start, end=end,
                    has_meta="meta" in frames, has_gsc="gsc" in frames,
                )  # fmt: skip
                results = checks_mod.run_all(inputs)
            finally:
                con.close()
        finally:
            if previous is None:
                os.environ.pop(config.WAREHOUSE_ENV_VAR, None)
            else:
                os.environ[config.WAREHOUSE_ENV_VAR] = previous

    return AuditResult(
        client_name=client_name, currency=currency, period_start=start, period_end=end,
        checks=results, score=score(results),
        inputs={"google_ads": True, "ga4": True, "meta": "meta" in frames, "gsc": "gsc" in frames},
        notes=notes,
    )  # fmt: skip


def _bounds(series: pd.Series) -> tuple[date, date]:
    s = pd.to_datetime(series)
    return s.min().date(), s.max().date()


def _load(
    warehouse: Path,
    client: ClientConfig,
    frames: dict[str, pd.DataFrame],
    start: date,
    end: date,
) -> None:
    tables = {
        "google_ads": ("google_ads_campaign_daily", "segments_date"),
        "ga4": ("ga4_traffic_daily", "date"),
        "meta": ("meta_ads_insights_daily", "date_start"),
        "gsc": ("gsc_search_daily", "date"),
    }
    con = load.connect(warehouse)
    try:
        load.ensure_schema(con)
        for kind, df in frames.items():
            table, date_col = tables[kind]
            fmt = "%Y%m%d" if kind == "ga4" else None
            days = pd.to_datetime(df[date_col], format=fmt)
            df = df[(days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end))]
            load.load_frame(con, SimpleNamespace(table=table), df, client, start, end)
        load.load_clients_table(con, [client])
    finally:
        con.close()
