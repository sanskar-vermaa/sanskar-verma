"""Reporting: monthly summaries and category breakdowns."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ledger.models.money import Money
from ledger.models.transaction import Transaction


@dataclass
class CategoryTotal:
    category: str
    total: Money
    count: int


@dataclass
class MonthlySummary:
    period: str  # "YYYY-MM"
    currency: str
    income: Money
    expenses: Money
    net: Money
    by_category: list[CategoryTotal]


def summarize_month(
    transactions: list[Transaction], period: str, currency: str
) -> MonthlySummary:
    """Summarize all transactions whose posted_on falls in `period` ("YYYY-MM").

    Raises ValueError if any matching transaction is in a different
    currency than `currency` -- summaries don't silently mix currencies.
    """
    matching = [t for t in transactions if t.posted_on.strftime("%Y-%m") == period]

    income = Money.zero(currency)
    expenses = Money.zero(currency)
    totals_by_category: dict[str, list[Transaction]] = defaultdict(list)

    for txn in matching:
        if txn.amount.currency != currency:
            raise ValueError(
                f"transaction {txn.transaction_id} is in {txn.amount.currency}, "
                f"expected {currency}"
            )
        if txn.amount.is_negative():
            expenses = expenses - txn.amount
        else:
            income = income + txn.amount
        category = txn.category or "Uncategorized"
        totals_by_category[category].append(txn)

    by_category = [
        CategoryTotal(
            category=category,
            total=sum(
                (t.amount for t in txns), start=Money.zero(currency)
            ),
            count=len(txns),
        )
        for category, txns in totals_by_category.items()
    ]
    by_category.sort(key=lambda c: c.total.amount_minor)

    net = income - expenses
    return MonthlySummary(
        period=period,
        currency=currency,
        income=income,
        expenses=expenses,
        net=net,
        by_category=by_category,
    )
