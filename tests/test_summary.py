from datetime import date

import pytest

from ledger.models.money import Money
from ledger.models.transaction import Transaction
from ledger.reports.summary import summarize_month


def _txn(day, amount, category=None, currency="USD"):
    return Transaction(
        account_id="acc1",
        posted_on=day,
        amount=Money.from_major(amount, currency),
        description="txn",
        category=category,
    )


def test_income_and_expenses_split_correctly():
    txns = [
        _txn(date(2024, 3, 1), "2000.00"),
        _txn(date(2024, 3, 5), "-500.00"),
        _txn(date(2024, 3, 10), "-300.00"),
    ]
    summary = summarize_month(txns, "2024-03", "USD")
    assert summary.income.amount_minor == 200000
    assert summary.expenses.amount_minor == 80000
    assert summary.net.amount_minor == 120000


def test_excludes_other_months():
    txns = [_txn(date(2024, 3, 1), "100.00"), _txn(date(2024, 4, 1), "999.00")]
    summary = summarize_month(txns, "2024-03", "USD")
    assert summary.income.amount_minor == 10000


def test_uncategorized_bucket():
    txns = [_txn(date(2024, 3, 1), "-10.00"), _txn(date(2024, 3, 2), "-5.00", category="Food")]
    summary = summarize_month(txns, "2024-03", "USD")
    categories = {c.category: c.total.amount_minor for c in summary.by_category}
    assert categories["Uncategorized"] == -1000
    assert categories["Food"] == -500


def test_rejects_mismatched_currency():
    txns = [_txn(date(2024, 3, 1), "100.00", currency="EUR")]
    with pytest.raises(ValueError):
        summarize_month(txns, "2024-03", "USD")


def test_empty_month_returns_zero_summary():
    summary = summarize_month([], "2024-03", "USD")
    assert summary.income.amount_minor == 0
    assert summary.expenses.amount_minor == 0
    assert summary.by_category == []
