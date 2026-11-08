from __future__ import annotations

import logging
import sys
import types
from datetime import date

from agency_pipeline import commentary
from agency_pipeline.commentary import build_month_context, generate_commentary
from agency_pipeline.monitoring import run_checks

OCT = date(2026, 10, 1)


def _fake_anthropic(monkeypatch, behaviour):
    calls = {}

    class Messages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return behaviour()

    class Client:
        messages = Messages()

    mod = types.SimpleNamespace(Anthropic=lambda: Client())
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    return calls


def test_context_is_json_able_and_has_mom(con):
    import json

    ctx = build_month_context(con, "bluepeak-dental", OCT)
    json.dumps(ctx)
    assert ctx["currency"] == "GBP"
    assert ctx["channels"]["total_paid"]["mom"]["spend"] is not None


def test_template_deterministic_and_formatted(con):
    alerts = run_checks(con, date(2026, 10, 31), "bluepeak-dental")
    a = generate_commentary(con, "bluepeak-dental", OCT, alerts, use_llm=False)
    b = generate_commentary(con, "bluepeak-dental", OCT, alerts, use_llm=False)
    assert a == b and a.source == "template"
    spend = build_month_context(con, "bluepeak-dental", OCT)["channels"]["total_paid"]["spend"]
    assert f"£{spend:,.0f}" in a.text
    assert "tracking" in a.text


def test_usd_symbol(con):
    c = generate_commentary(con, "northwind-outdoor", OCT, [], use_llm=False)
    assert "$" in c.text and "tracking" not in c.text


def test_auto_without_key_uses_template(con, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert generate_commentary(con, "northwind-outdoor", OCT, []).source == "template"


def test_llm_path_with_fake_client(con, monkeypatch, caplog):
    reply = types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text="Draft text.")])
    calls = _fake_anthropic(monkeypatch, lambda: reply)
    with caplog.at_level(logging.INFO, logger=commentary.logger.name):
        c = generate_commentary(con, "northwind-outdoor", OCT, [], use_llm=True)
    assert (c.text, c.source) == ("Draft text.", "llm")
    assert calls["model"] == "claude-sonnet-5-5" and calls["max_tokens"] == 400
    assert "ONLY numbers" in calls["system"]
    assert "review before sending" in caplog.text


def test_llm_failure_falls_back(con, monkeypatch, caplog):
    def boom():
        raise RuntimeError("api down")

    _fake_anthropic(monkeypatch, boom)
    with caplog.at_level(logging.WARNING):
        c = generate_commentary(con, "northwind-outdoor", OCT, [], use_llm=True)
    assert c.source == "template"
    assert "api down" in caplog.text
