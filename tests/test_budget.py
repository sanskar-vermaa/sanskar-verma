from ledger.models.budget import Budget, evaluate_budget
from ledger.models.money import Money


def test_no_rollover_uses_flat_limit():
    budget = Budget(category="Dining", period="2024-03", limit=Money.from_major("200.00", "USD"))
    spent = {"2024-03": Money.from_major("150.00", "USD")}
    status = evaluate_budget(budget, spent, ordered_prior_periods=[])
    assert status.effective_limit.amount_minor == 20000
    assert status.remaining.amount_minor == 5000
    assert not status.is_over


def test_rollover_carries_unspent_forward():
    budget = Budget(
        category="Dining", period="2024-03", limit=Money.from_major("200.00", "USD"), rollover=True
    )
    spent = {
        "2024-01": Money.from_major("150.00", "USD"),  # 50 leftover
        "2024-02": Money.from_major("180.00", "USD"),  # 20 leftover
        "2024-03": Money.from_major("100.00", "USD"),
    }
    status = evaluate_budget(budget, spent, ordered_prior_periods=["2024-01", "2024-02"])
    # 200 (this month) + 50 + 20 leftover = 270 effective limit
    assert status.effective_limit.amount_minor == 27000
    assert status.remaining.amount_minor == 17000


def test_rollover_carries_overspend_forward_as_penalty():
    budget = Budget(
        category="Dining", period="2024-02", limit=Money.from_major("200.00", "USD"), rollover=True
    )
    spent = {
        "2024-01": Money.from_major("250.00", "USD"),  # overspent by 50
        "2024-02": Money.from_major("180.00", "USD"),
    }
    status = evaluate_budget(budget, spent, ordered_prior_periods=["2024-01"])
    # 200 - 50 overspend = 150 effective limit
    assert status.effective_limit.amount_minor == 15000
    assert status.remaining.amount_minor == -3000
    assert status.is_over


def test_missing_period_treated_as_zero_spend():
    budget = Budget(category="Travel", period="2024-05", limit=Money.from_major("500.00", "USD"))
    status = evaluate_budget(budget, spent_by_period={}, ordered_prior_periods=[])
    assert status.spent.amount_minor == 0
    assert status.utilization_ratio() == 0.0


def test_utilization_ratio_over_limit():
    budget = Budget(category="Travel", period="2024-05", limit=Money.from_major("100.00", "USD"))
    spent = {"2024-05": Money.from_major("150.00", "USD")}
    status = evaluate_budget(budget, spent, ordered_prior_periods=[])
    assert status.utilization_ratio() == 1.5
