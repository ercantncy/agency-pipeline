"""Report rendering on a temporary warehouse."""

from __future__ import annotations

import re
from datetime import date

import duckdb
import pytest
from typer.testing import CliRunner

from agency_pipeline.cli import app
from agency_pipeline.reporting import build_report

CLIENTS = ["northwind-outdoor", "bluepeak-dental", "harbor-coffee"]


@pytest.fixture(scope="module")
def reports(tmp_path_factory):
    root = tmp_path_factory.mktemp("rpt")
    mp = pytest.MonkeyPatch()
    mp.setenv("AGENCY_PIPELINE_WAREHOUSE", str(root / "warehouse.duckdb"))
    runner = CliRunner()
    assert runner.invoke(app, ["extract-load"]).exit_code == 0
    assert runner.invoke(app, ["transform"]).exit_code == 0
    con = duckdb.connect(str(root / "warehouse.duckdb"), read_only=True)
    out = {
        c: build_report(con, c, date(2026, 10, 1), root / "output", use_llm=False) for c in CLIENTS
    }
    con.close()
    yield out
    mp.undo()


def _visible_text(html: str) -> str:
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.mark.parametrize("client", CLIENTS)
def test_report_is_self_contained_and_white_labeled(reports, client):
    path = reports[client]
    assert path.name == "2026-10.html" and path.parent.name == client
    html = path.read_text(encoding="utf-8")
    assert not re.search(r'<script[^>]+src=["\']?(https?:)?//', html)
    assert not re.search(r'<link[^>]+href=["\']?https?:', html)
    text = _visible_text(html)
    assert "Brightline Digital" in text
    assert "pipeline" not in text.lower()
    assert "#2F6FEB" in html
    for n in range(1, 8):
        assert f'<span class="sec-num">0{n}</span>' in html


def test_bluepeak_shows_data_quality_alert(reports):
    html = reports["bluepeak-dental"].read_text(encoding="utf-8")
    assert 'class="alert critical"' in html
    assert "All checks passed" not in html
    assert "£" in html


def test_northwind_has_no_critical_alert(reports):
    html = reports["northwind-outdoor"].read_text(encoding="utf-8")
    assert 'class="alert critical"' not in html
    assert "All checks passed" in html
    assert "$" in html
