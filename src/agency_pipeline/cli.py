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

    console.rule("1/4 extract-load")
    extract_load(
        client=None, start=DEFAULT_START.isoformat(), end=DEFAULT_END.isoformat()
    )
    console.rule("2/4 transform")
    transform()
    console.rule("3/4 check")
    exit_code = 0
    try:
        check(end=month_end.isoformat(), client=None, as_json=False)
    except typer.Exit as e:
        exit_code = e.exit_code
    console.rule("4/4 report")
    _build_reports("all", month_d, False if no_llm else None)
    if exit_code:
        console.print("[red]Critical alerts are open (reports were still built).[/red]")
        raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
