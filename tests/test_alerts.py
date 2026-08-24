from ledger.models.budget import Budget, BudgetStatus
from ledger.models.money import Money
from ledger.rules.alerts import evaluate_alert


def _status(spent_major: str, limit_major: str = "100.00") -> BudgetStatus:
    budget = Budget(category="Dining", period="2024-03", limit=Money.from_major(limit_major, "USD"))
    return BudgetStatus(
        budget=budget,
        spent=Money.from_major(spent_major, "USD"),
        effective_limit=Money.from_major(limit_major, "USD"),
    )


def test_low_spend_is_on_track():
    assert evaluate_alert(_status("30.00")) is None


def test_moderate_spend_triggers_on_track():
    assert evaluate_alert(_status("60.00")) == "on_track"


def test_high_spend_triggers_warning():
    assert evaluate_alert(_status("90.00")) == "warning"


def test_overspend_triggers_over_budget():
    assert evaluate_alert(_status("110.00")) == "over_budget"


def test_zero_spend_is_none():
    assert evaluate_alert(_status("0.00")) is None
