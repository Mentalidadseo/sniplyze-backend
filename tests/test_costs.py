import pytest

from app.core.costs import CostGuard, CostLedger
from app.core.db import Database
from app.core.errors import BudgetExceeded, ConfirmationRequired


@pytest.fixture
def ledger():
    return CostLedger(Database(":memory:"))


def guard(ledger, **kw):
    opts = dict(threshold=0.5, confirm_unknown=True, daily_budget=0)
    opts.update(kw)
    return CostGuard(ledger, **opts)


def test_unknown_cost_requires_confirmation(ledger):
    with pytest.raises(ConfirmationRequired) as exc:
        guard(ledger).check("serp", 1, confirm=False)
    assert exc.value.details["estimated_cost"] is None
    assert guard(ledger).check("serp", 1, confirm=True).estimated_cost is None


def test_unknown_cost_allowed_when_configured(ledger):
    assert guard(ledger, confirm_unknown=False).check("serp", 1, confirm=False).known is False


def test_estimate_scales_with_units_using_max_observed_per_unit(ledger):
    ledger.record("serp", 0.002, units=1)
    ledger.record("serp", 0.003, units=1)
    ledger.record("serp", 0.0, units=1, from_cache=True)  # la caché no cuenta
    est = ledger.estimate("serp", 10)
    assert est.estimated_cost == pytest.approx(0.03)


def test_threshold(ledger):
    ledger.record("crawl", 0.01, units=10)  # 0.001 por página
    g = guard(ledger)
    assert g.check("crawl", 100, confirm=False).estimated_cost == pytest.approx(0.1)
    with pytest.raises(ConfirmationRequired) as exc:
        g.check("crawl", 1000, confirm=False)
    assert exc.value.details["estimated_cost"] == pytest.approx(1.0)
    assert g.check("crawl", 1000, confirm=True).estimated_cost == pytest.approx(1.0)


def test_daily_budget_blocks_even_with_confirmation(ledger):
    ledger.record("x", 0.9, units=1)
    with pytest.raises(BudgetExceeded):
        guard(ledger, daily_budget=1.0).check("x", 1, confirm=True)


def test_summary(ledger):
    ledger.record("a", 0.1)
    ledger.record("a", 0.1, from_cache=True)
    ledger.record("b", 0.2, ok=False, message="boom")
    s = ledger.summary()
    assert s["total_calls"] == 2
    assert s["total_cost"] == pytest.approx(0.3)
    assert s["cache_hits"] == 1
    assert s["saved_by_cache"] == pytest.approx(0.1)
    assert {r["endpoint"]: r["errors"] for r in s["by_endpoint"]} == {"a": 0, "b": 1}
