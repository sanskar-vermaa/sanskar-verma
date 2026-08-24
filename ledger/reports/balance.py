"""Account balance calculation."""

from __future__ import annotations

from ledger.models.money import Money
from ledger.models.transaction import Account, Transaction


def current_balance(account: Account, transactions: list[Transaction]) -> Money:
    """Opening balance plus every transaction on the account.

    All transactions must be in the account's currency -- balances don't
    silently absorb a currency mismatch.
    """
    balance = account.opening_balance
    for txn in transactions:
        if txn.amount.currency != account.currency:
            raise ValueError(
                f"transaction in {txn.amount.currency} cannot be applied to "
                f"a {account.currency} account balance"
            )
        balance = balance + txn.amount
    return balance
