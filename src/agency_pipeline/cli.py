"""Command line interface. Each pipeline stage is one command; `run` chains them."""

from __future__ import annotations

from datetime import date, timedelta

import typer
from rich.console import Console
from rich.table import Table

from agency_pipeline import config, load
from agency_pipeline.sources import get_sources

app = typer.Typer(help="Agency reporting pipeline.", no_args_is_help=True)
console = Console()

DEFAULT_END = date(2026, 10, 31)
DEFAULT_DAYS = 120
DEFAULT_START = DEFAULT_END - timedelta(days=DEFAULT_DAYS - 1)  # 2026-07-04


@app.command("extract-load")
def extract_load(
    client: str | None = typer.Option(None, help="Client id (default: all clients)."),
    start: str = typer.Option(DEFAULT_START.isoformat(), help="First day, YYYY-MM-DD."),
    end: str = typer.Option(DEFAULT_END.isoformat(), help="Last day, YYYY-MM-DD."),
) -> None:
    """Extract from the sources and load the raw schema of the warehouse."""
    clients = config.load_clients()
    if client:
        clients = [c for c in clients if c.client_id == client]
        if not clients:
            raise typer.BadParameter(f"unknown client: {client}", param_hint="--client")
    start_d, end_d = date.fromisoformat(start), date.fromisoformat(end)
    if start_d > end_d:
        raise typer.BadParameter("--start must not be after --end")

    counts = load.extract_load(clients, get_sources(), start_d, end_d)
    table = Table(title=f"Loaded {start_d} to {end_d}")
    table.add_column("raw table")
    table.add_column("rows", justify="right")
    for name, n in counts.items():
        table.add_row(name, f"{n:,}")
    console.print(table)


@app.command()
def transform() -> None:
    """Run the dbt project (staging + marts)."""
    import os
    import subprocess
    import sys

    dbt_dir = str(config.PROJECT_ROOT / "dbt")
    # dbt-duckdb resolves relative paths against the cwd, so always hand it an absolute path.
    env = {**os.environ, config.WAREHOUSE_ENV_VAR: str(config.warehouse_path().resolve())}
    # Subprocess (not in-process dbtRunner) so dbt releases its DuckDB file lock on exit.
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    proc = subprocess.run(
        [*cmd, "build", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir], env=env
    )
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


@app.command()
def check(
    end: str = typer.Option(DEFAULT_END.isoformat(), help="Check as of this day, YYYY-MM-DD."),
    client: str | None = typer.Option(None, help="Client id (default: all clients)."),
    as_json: bool = typer.Option(False, "--json", help="Emit alerts as JSON."),
) -> None:
    """Run monitoring checks over the marts (exit code 1 if any alert is critical)."""
    import json

    import duckdb

    from agency_pipeline import monitoring

    end_d = date.fromisoformat(end)
    con = duckdb.connect(str(config.warehouse_path()), read_only=True)
    try:
        alerts = monitoring.run_checks(con, end_d, client)
    finally:
        con.close()
    if as_json:
        typer.echo(json.dumps([a.to_dict() for a in alerts], indent=2))
    elif not alerts:
        console.print(f"[green]All checks passed as of {end_d}.[/green]")
    else:
        table = Table(title=f"Monitoring alerts as of {end_d}")
        for col in ("client", "severity", "check", "period", "message"):
            table.add_column(col)
        for a in alerts:
            style = "red" if a.severity == "critical" else "yellow"
            period = ""
            if a.start_date:
                period = str(a.start_date)
                if a.end_date and a.end_date != a.start_date:
                    period += f" to {a.end_date}"
            sev = f"[{style}]{a.severity}[/{style}]"
            table.add_row(a.client_id, sev, a.check, period, a.message)
        console.print(table)
    if any(a.severity == "critical" for a in alerts):
        raise typer.Exit(code=1)


DEFAULT_MONTH = "2026-10"


def _parse_month(value: str) -> date:
    try:
        year, mon = value.split("-")
        return date(int(year), int(mon), 1)
    except ValueError:
        raise typer.BadParameter("expected YYYY-MM", param_hint="--month") from None


def _build_reports(client: str, month: date, use_llm: bool | None) -> None:
    import duckdb

    from agency_pipeline.reporting import build_report

    con = duckdb.connect(str(config.warehouse_path()), read_only=True)
    try:
        rows = con.execute("select client_id from marts.dim_client order by 1").fetchall()
        ids = [r[0] for r in rows]
        if client != "all":
            if client not in ids:
                raise typer.BadParameter(f"unknown client: {client}", param_hint="--client")
            ids = [client]
        for cid in ids:
            path = build_report(con, cid, month, config.OUTPUT_DIR, use_llm=use_llm)
            size_kb = path.stat().st_size / 1024
            shown = path.relative_to(config.PROJECT_ROOT)
            console.print(f"[green]wrote[/green] {shown} ({size_kb:,.0f} KB)")
    finally:
        con.close()


@app.command()
def report(
    client: str = typer.Option("all", help="Client id, or 'all'."),
    month: str = typer.Option(DEFAULT_MONTH, help="Report month, YYYY-MM."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Force template commentary (no API call)."),
) -> None:
    """Build white-labeled client reports (output/reports/<client>/<month>.html)."""
    _build_reports(client, _parse_month(month), False if no_llm else None)


@app.command()
def run(
    month: str = typer.Option(DEFAULT_MONTH, help="Report month, YYYY-MM."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Force template commentary (no API call)."),
) -> None:
    """Run the whole pipeline: extract-load, transform, check, report (exit 1 on criticals)."""
    month_d = _parse_month(month)
    month_end = (month_d + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    console.rule("1/5 extract-load")
    extract_load(
        client=None, start=DEFAULT_START.isoformat(), end=DEFAULT_END.isoformat()
    )
    console.rule("2/5 transform")
    transform()
    console.rule("3/5 check")
    exit_code = 0
    try:
        check(end=month_end.isoformat(), client=None, as_json=False)
    except typer.Exit as e:
        exit_code = e.exit_code
    console.rule("4/5 report")
    _build_reports("all", month_d, False if no_llm else None)
    console.rule("5/5 export-web")
    _export_web("web/public/data", None, False if no_llm else None)
    if exit_code:
        console.print("[red]Critical alerts are open (reports were still built).[/red]")
        raise typer.Exit(code=exit_code)


@app.command("export-web")
def export_web_cmd(
    out: str = typer.Option("web/public/data", help="Output directory for the JSON files."),
    months: str | None = typer.Option(
        None, help="Comma list of YYYY-MM (default: all full months)."
    ),
    llm: bool = typer.Option(False, "--llm", help="Use the LLM for commentary (needs an API key)."),
) -> None:
    """Export marts, alerts and commentary as JSON for the web app."""
    _export_web(out, months, llm)


def _export_web(out: str, months: str | None, use_llm: bool | None) -> None:
    from pathlib import Path

    import duckdb

    from agency_pipeline.export_web import export_web

    month_list = [_parse_month(m.strip()) for m in months.split(",")] if months else None
    out_dir = Path(out)
    if not out_dir.is_absolute():
        out_dir = config.PROJECT_ROOT / out_dir
    con = duckdb.connect(str(config.warehouse_path()), read_only=True)
    try:
        paths = export_web(con, out_dir, month_list, use_llm)
    finally:
        con.close()
    console.print(f"[green]exported[/green] {len(paths)} files to {out_dir}")


@app.command()
def audit(
    google_ads: str = typer.Option(..., "--google-ads", help="Google Ads campaign-by-day CSV."),
    ga4: str = typer.Option(..., "--ga4", help="GA4 traffic CSV (by day, source / medium)."),
    client_name: str = typer.Option(..., "--client-name", help="Client name on the scorecard."),
    meta: str | None = typer.Option(None, "--meta", help="Meta Ads Manager campaign-by-day CSV."),
    gsc: str | None = typer.Option(None, "--gsc", help="Search Console 'Dates.csv' export."),
    currency: str | None = typer.Option(None, help="Currency code (default: from the export)."),
    consultant: str = typer.Option("Ercan Tuncay", help="Name shown as preparer."),
    out: str | None = typer.Option(None, help="Output HTML (default output/audits/<slug>-<date>)."),
) -> None:
    """Tracking & Reporting Audit: CSV exports in, one-page HTML scorecard out."""
    from pathlib import Path

    from agency_pipeline.audit.runner import AuditError, run_audit
    from agency_pipeline.audit.scorecard import slugify, write_scorecard
    from agency_pipeline.sources.csv_exports import ExportError

    try:
        result = run_audit(
            google_ads_path=Path(google_ads), ga4_path=Path(ga4), client_name=client_name,
            meta_path=Path(meta) if meta else None, gsc_path=Path(gsc) if gsc else None,
            currency=currency, consultant=consultant,
        )  # fmt: skip
    except (ExportError, AuditError, FileNotFoundError) as e:
        console.print(f"[red]error:[/red] {e}")
        raise typer.Exit(code=2) from None
    default = config.OUTPUT_DIR / "audits" / f"{slugify(client_name)}-{date.today():%Y-%m-%d}.html"
    path = write_scorecard(result, Path(out) if out else default, consultant)
    table = Table(title=f"Audit: {client_name}, score {result.score}/100")
    for col in ("#", "check", "status", "headline"):
        table.add_column(col)
    for c in result.checks:
        table.add_row(str(c.number), c.title, c.status, c.headline)
    console.print(table)
    for n in result.notes:
        console.print(f"[yellow]note:[/yellow] {n}")
    console.print(f"[green]wrote[/green] {path}")


@app.command("sample-exports")
def sample_exports_cmd(
    client: str = typer.Option(..., help="Synthetic client id, e.g. bluepeak-dental."),
    out: str = typer.Option(..., help="Directory for the generated CSV files."),
    end: str = typer.Option(DEFAULT_END.isoformat(), help="Last day, YYYY-MM-DD."),
    days: int = typer.Option(30, help="Number of days ending at --end."),
) -> None:
    """Write UI-style CSV exports (Google Ads, GA4, Meta, Search Console) for a synthetic client."""
    from pathlib import Path

    from agency_pipeline.audit.sample_exports import generate

    try:
        paths = generate(client, Path(out), date.fromisoformat(end), days)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from None
    for p in paths.values():
        console.print(f"[green]wrote[/green] {p}")


if __name__ == "__main__":
    app()
