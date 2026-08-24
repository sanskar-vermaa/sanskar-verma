"""Detect recurring transactions (subscriptions, rent, payroll, etc).

Real recurring charges are not exact: a subscription might renew 28-31
days apart, and the amount can drift slightly (currency conversion fees,
tax changes, promo periods ending). Detection groups transactions by
description similarity, then checks whether the intervals between
consecutive occurrences and the amounts are consistent within tolerance.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from ledger.models.money import Money
from ledger.models.transaction import Transaction

_NORMALIZE_RE = re.compile(r"[^A-Z0-9 ]+")
_TRAILING_DIGITS_RE = re.compile(r"\b\d{3,}\b")


def _normalize_description(description: str) -> str:
    """Strip punctuation and volatile tokens (store numbers, dates, ids)
    so "AMAZON.COM*A1B2C3" and "AMAZON.COM*X9Y8Z7" group together."""
    upper = description.upper()
    upper = _TRAILING_DIGITS_RE.sub("", upper)
    upper = _NORMALIZE_RE.sub(" ", upper)
    return " ".join(upper.split())


@dataclass(frozen=True)
class RecurringSeries:
    description_key: str
    account_id: str
    transactions: tuple[Transaction, ...]
    approx_interval_days: float
    approx_amount: Money

    @property
    def occurrences(self) -> int:
        return len(self.transactions)


def detect_recurring(
    transactions: list[Transaction],
    *,
    min_occurrences: int = 3,
    interval_tolerance_days: float = 4.0,
    amount_tolerance_ratio: float = 0.05,
) -> list[RecurringSeries]:
    """Group transactions into recurring series.

    A group of same-normalized-description transactions on one account is
    considered recurring if it has at least `min_occurrences` entries and
    the gaps between consecutive dates are all within
    `interval_tolerance_days` of the group's median interval, and every
    amount is within `amount_tolerance_ratio` of the group's median
    amount (by absolute value, so it works for both debits and credits).
    """
    groups: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
    for txn in transactions:
        key = (txn.account_id, _normalize_description(txn.description))
        groups[key].append(txn)

    series: list[RecurringSeries] = []
    for (account_id, desc_key), txns in groups.items():
        if len(txns) < min_occurrences:
            continue
        ordered = sorted(txns, key=lambda t: t.posted_on)
        if not _consistent_currency(ordered):
            continue

        intervals = _day_gaps(ordered)
        median_interval = _median(intervals)
        if median_interval <= 0:
            continue
        if any(abs(gap - median_interval) > interval_tolerance_days for gap in intervals):
            continue

        magnitudes = [abs(t.amount.amount_minor) for t in ordered]
        median_amount = _median(magnitudes)
        if median_amount <= 0:
            continue
        if any(
            abs(m - median_amount) / median_amount > amount_tolerance_ratio
            for m in magnitudes
        ):
            continue

        series.append(
            RecurringSeries(
                description_key=desc_key,
                account_id=account_id,
                transactions=tuple(ordered),
                approx_interval_days=median_interval,
                approx_amount=Money(int(median_amount), ordered[0].amount.currency),
            )
        )
    return series


def _consistent_currency(txns: list[Transaction]) -> bool:
    currencies = {t.amount.currency for t in txns}
    return len(currencies) == 1


def _day_gaps(ordered_txns: list[Transaction]) -> list[float]:
    gaps = []
    for prev, curr in zip(ordered_txns, ordered_txns[1:]):
        gaps.append((curr.posted_on - prev.posted_on).days)
    return gaps


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
