"""Budget alert thresholds.

Given a budget's utilization ratio, determine which alert tier applies.
Thresholds are evaluated from lowest to highest so that the highest tier
whose ratio the spend has reached wins.
"""

from __future__ import annotations

from dataclasses import dataclass

from ledger.models.budget import BudgetStatus


@dataclass(frozen=True)
class AlertThreshold:
    ratio: float  # e.g. 0.8 means "80% of budget used"
    label: str


DEFAULT_THRESHOLDS = (
    AlertThreshold(0.5, "on_track"),
    AlertThreshold(0.8, "warning"),
    AlertThreshold(1.0, "over_budget"),
)


def evaluate_alert(
    status: BudgetStatus, thresholds: tuple[AlertThreshold, ...] = DEFAULT_THRESHOLDS
) -> str | None:
    """Return the label of the highest threshold reached, or None."""
    ratio = status.utilization_ratio()
    triggered: str | None = None
    for threshold in sorted(thresholds, key=lambda t: t.ratio):
        if ratio > threshold.ratio:
            triggered = threshold.label
    return triggered
