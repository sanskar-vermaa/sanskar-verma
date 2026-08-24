from ledger.models.budget import Budget
from ledger.models.money import Money
from ledger.rules.engine import CategoryRule
from ledger.storage.budget_repository import BudgetRepository, RuleRepository
from ledger.storage.db import connect


def test_upsert_and_get_budget():
    conn = connect(":memory:")
    repo = BudgetRepository(conn)
    budget = Budget("Dining", "2024-03", Money.from_major("200.00", "USD"), rollover=True)
    repo.upsert_budget(budget)

    fetched = repo.get_budget("Dining", "2024-03")
    assert fetched is not None
    assert fetched.limit.amount_minor == 20000
    assert fetched.rollover is True


def test_upsert_overwrites_existing_budget():
    conn = connect(":memory:")
    repo = BudgetRepository(conn)
    repo.upsert_budget(Budget("Dining", "2024-03", Money.from_major("200.00", "USD")))
    repo.upsert_budget(Budget("Dining", "2024-03", Money.from_major("250.00", "USD")))

    fetched = repo.get_budget("Dining", "2024-03")
    assert fetched.limit.amount_minor == 25000


def test_list_budget_periods_before_cutoff_ascending():
    conn = connect(":memory:")
    repo = BudgetRepository(conn)
    for period in ["2024-03", "2024-01", "2024-02", "2024-04"]:
        repo.upsert_budget(Budget("Dining", period, Money.from_major("100.00", "USD")))

    periods = repo.list_budget_periods("Dining", before_period="2024-04")
    assert periods == ["2024-01", "2024-02", "2024-03"]


def test_rule_repository_orders_by_priority():
    conn = connect(":memory:")
    repo = RuleRepository(conn)
    repo.add_rule(CategoryRule(10, "description", "AMAZON*", "Shopping"))
    repo.add_rule(CategoryRule(1, "description", "STARBUCKS*", "Coffee"))

    rules = repo.list_rules()
    assert [r.category for r in rules] == ["Coffee", "Shopping"]
