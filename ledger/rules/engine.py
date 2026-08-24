"""Rule-based transaction categorization.

Rules match against a transaction field (currently `description`) using a
glob-style pattern, and assign a category. When multiple rules match the
same transaction, the rule with the lowest `priority` number wins; ties
are broken by preferring the more specific (longer) pattern, so a rule
matching "AMAZON MKTPLACE*" beats a catch-all "AMAZON*" at the same
priority.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from ledger.models.transaction import Transaction


@dataclass(frozen=True)
class CategoryRule:
    priority: int
    field: str
    pattern: str
    category: str

    def matches(self, txn: Transaction) -> bool:
        value = getattr(txn, self.field, None)
        if value is None:
            return False
        return fnmatch.fnmatchcase(str(value).upper(), self.pattern.upper())


class RuleEngine:
    def __init__(self, rules: list[CategoryRule] | None = None):
        self._rules = list(rules or [])

    def add_rule(self, rule: CategoryRule) -> None:
        self._rules.append(rule)

    def categorize(self, txn: Transaction) -> str | None:
        matches = [r for r in self._rules if r.matches(txn)]
        if not matches:
            return None
        matches.sort(key=lambda r: (r.priority, -len(r.pattern)))
        return matches[0].category

    def apply(self, transactions: list[Transaction]) -> int:
        """Categorize every uncategorized transaction in place.

        Returns the number of transactions that were newly categorized.
        Transactions that already have a category are left untouched --
        rules never overwrite a manual categorization.
        """
        updated = 0
        for txn in transactions:
            if txn.category is not None:
                continue
            category = self.categorize(txn)
            if category is not None:
                txn.category = category
                updated += 1
        return updated
