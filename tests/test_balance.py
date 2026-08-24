from datetime import date

import pytest

from ledger.models.money import Money
from ledger.models.transaction import Account, Transaction
from ledger.reports.balance import current_balance


def _account(opening="1000.00"):
    return Account("acc1", "Checking", "USD", Money.from_major(opening, "USD"))


def _txn(amount):
    return Transaction("acc1", date(2024, 1, 1), Money.from_major(amount, "USD"), "txn")


def test_balance_with_no_transactions_is_opening_balance():
    assert current_balance(_account(), []).amount_minor == 100000


def test_balance_sums_debits_and_credits():
    txns = [_txn("-50.00"), _txn("200.00"), _txn("-25.00")]
    balance = current_balance(_account(), txns)
    assert balance.amount_minor == 112500  # 1000 - 50 + 200 - 25


def test_balance_rejects_currency_mismatch():
    account = _account()
    bad_txn = Transaction("acc1", date(2024, 1, 1), Money.from_major("10.00", "EUR"), "txn")
    with pytest.raises(ValueError):
        current_balance(account, [bad_txn])
