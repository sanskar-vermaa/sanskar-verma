"""Transaction and Account domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ledger.models.money import Money


@dataclass
class Account:
    account_id: str
    name: str
    currency: str
    opening_balance: Money


@dataclass
class Transaction:
    """A single posted transaction on an account.

    `amount` is signed: negative for money leaving the account (a debit),
    positive for money arriving (a credit). `external_id` is whatever
    identifier the source statement used, if any, so repeated imports of
    the same statement can be deduplicated.
    """

    account_id: str
    posted_on: date
    amount: Money
    description: str
    external_id: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    transaction_id: int | None = None

    def is_debit(self) -> bool:
        return self.amount.is_negative()

    def dedupe_key(self) -> tuple:
        """Key used to detect duplicate imports of the same transaction.

        Falls back to (account, date, amount, description) when the source
        statement doesn't provide a stable external id -- many bank CSV
        exports don't.
        """
        if self.external_id:
            return (self.account_id, self.external_id)
        return (self.account_id, self.posted_on, self.amount, self.description)
