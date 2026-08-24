"""Persistence for budgets and category rules."""

from __future__ import annotations

import sqlite3

from ledger.models.budget import Budget
from ledger.models.money import Money
from ledger.rules.engine import CategoryRule


class BudgetRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_budget(self, budget: Budget) -> None:
        self._conn.execute(
            """
            INSERT INTO budgets (category, period, limit_minor, currency, rollover)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category, period) DO UPDATE SET
                limit_minor = excluded.limit_minor,
                currency = excluded.currency,
                rollover = excluded.rollover
            """,
            (
                budget.category,
                budget.period,
                budget.limit.amount_minor,
                budget.limit.currency,
                int(budget.rollover),
            ),
        )
        self._conn.commit()

    def get_budget(self, category: str, period: str) -> Budget | None:
        row = self._conn.execute(
            "SELECT * FROM budgets WHERE category = ? AND period = ?",
            (category, period),
        ).fetchone()
        if row is None:
            return None
        return Budget(
            category=row["category"],
            period=row["period"],
            limit=Money(row["limit_minor"], row["currency"]),
            rollover=bool(row["rollover"]),
        )

    def list_budget_periods(self, category: str, before_period: str) -> list[str]:
        """All periods this category has a budget for, strictly before `before_period`, ascending."""
        rows = self._conn.execute(
            "SELECT period FROM budgets WHERE category = ? AND period < ? ORDER BY period ASC",
            (category, before_period),
        ).fetchall()
        return [r["period"] for r in rows]


class RuleRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add_rule(self, rule: CategoryRule) -> None:
        self._conn.execute(
            "INSERT INTO category_rules (priority, field, pattern, category) VALUES (?, ?, ?, ?)",
            (rule.priority, rule.field, rule.pattern, rule.category),
        )
        self._conn.commit()

    def list_rules(self) -> list[CategoryRule]:
        rows = self._conn.execute(
            "SELECT * FROM category_rules ORDER BY priority ASC"
        ).fetchall()
        return [
            CategoryRule(
                priority=row["priority"],
                field=row["field"],
                pattern=row["pattern"],
                category=row["category"],
            )
            for row in rows
        ]
