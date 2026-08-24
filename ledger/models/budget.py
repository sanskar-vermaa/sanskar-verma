"""Budget tracking with monthly rollover.

A Budget applies to one category for one period (a "YYYY-MM" string). If
`rollover` is set, unspent balance from the previous period carries
forward and adds to the current period's effective limit; overspend also
carries forward and reduces it. This mirrors how "envelope budgeting"
actually works: it's not that each month resets to a fixed cap, it's that
the cap is the running balance of the envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

from ledger.models.money import Money


@dataclass
class Budget:
    category: str
    period: str  # "YYYY-MM"
    limit: Money
    rollover: bool = False


@dataclass
class BudgetStatus:
    budget: Budget
    spent: Money
    effective_limit: Money

    @property
    def remaining(self) -> Money:
        return self.effective_limit - self.spent

    @property
    def is_over(self) -> bool:
        return self.remaining.is_negative()

    def utilization_ratio(self) -> float:
        if self.effective_limit.amount_minor == 0:
            return float("inf") if self.spent.amount_minor > 0 else 0.0
        return self.spent.amount_minor / self.effective_limit.amount_minor


def evaluate_budget(
    budget: Budget,
    spent_by_period: dict[str, Money],
    ordered_prior_periods: list[str],
) -> BudgetStatus:
    """Compute a budget's status for `budget.period`.

    `spent_by_period` maps period -> total spent in that category/period.
    `ordered_prior_periods` lists periods strictly before `budget.period`,
    in chronological order, that share this budget's rollover chain --
    the caller is responsible for stopping the chain at wherever the
    budget didn't exist yet or rollover was reset.
    """
    effective_limit = budget.limit
    if budget.rollover:
        for period in ordered_prior_periods:
            prior_spent = spent_by_period.get(period, Money.zero(budget.limit.currency))
            prior_leftover = budget.limit - prior_spent
            effective_limit = effective_limit + prior_leftover

    spent = spent_by_period.get(budget.period, Money.zero(budget.limit.currency))
    return BudgetStatus(budget=budget, spent=spent, effective_limit=effective_limit)
