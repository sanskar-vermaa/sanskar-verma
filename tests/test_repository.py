import sqlite3
from datetime import date

import pytest

from ledger.models.money import Money
from ledger.models.transaction import Account, Transaction
from ledger.storage.db import connect
from ledger.storage.repository import TransactionRepository


@pytest.fixture
def repo():
    conn = connect(":memory:")
    return TransactionRepository(conn)


def _account(account_id="acc1", currency="USD"):
    return Account(account_id, "Checking", currency, Money.zero(currency))


def test_upsert_account_then_get(repo):
    repo.upsert_account(_account())
    account = repo.get_account("acc1")
    assert account is not None
    assert account.name == "Checking"
    assert account.currency == "USD"


def test_get_unknown_account_returns_none(repo):
    assert repo.get_account("nope") is None


def test_add_transaction_roundtrip(repo):
    repo.upsert_account(_account())
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 1, 15),
        amount=Money.from_major("-25.00", "USD"),
        description="GROCERY STORE",
        external_id="tx-1",
    )
    txn_id = repo.add_transaction(txn)
    assert txn_id is not None

    fetched = repo.list_transactions(account_id="acc1")
    assert len(fetched) == 1
    assert fetched[0].amount.amount_minor == -2500
    assert fetched[0].description == "GROCERY STORE"


def test_reimporting_same_external_id_is_idempotent(repo):
    repo.upsert_account(_account())
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 1, 15),
        amount=Money.from_major("-25.00", "USD"),
        description="GROCERY STORE",
        external_id="tx-1",
    )
    first_id = repo.add_transaction(txn)
    second_id = repo.add_transaction(txn)
    assert first_id == second_id
    assert len(repo.list_transactions(account_id="acc1")) == 1


def test_date_range_filtering(repo):
    repo.upsert_account(_account())
    for day, desc in [(5, "A"), (15, "B"), (25, "C")]:
        repo.add_transaction(
            Transaction(
                account_id="acc1",
                posted_on=date(2024, 1, day),
                amount=Money.from_major("-1.00", "USD"),
                description=desc,
                external_id=desc,
            )
        )
    filtered = repo.list_transactions(
        account_id="acc1", start=date(2024, 1, 10), end=date(2024, 1, 20)
    )
    assert [t.description for t in filtered] == ["B"]


def test_set_category(repo):
    repo.upsert_account(_account())
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 1, 15),
        amount=Money.from_major("-25.00", "USD"),
        description="GROCERY STORE",
        external_id="tx-1",
    )
    txn_id = repo.add_transaction(txn)
    repo.set_category(txn_id, "Groceries")
    fetched = repo.list_transactions(account_id="acc1")
    assert fetched[0].category == "Groceries"


def test_transaction_without_external_id_is_not_deduplicated(repo):
    repo.upsert_account(_account())
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 1, 15),
        amount=Money.from_major("-25.00", "USD"),
        description="CASH WITHDRAWAL",
    )
    repo.add_transaction(txn)
    repo.add_transaction(txn)
    # Two separate cash withdrawals with no external id are both real
    # transactions and must both be stored, not collapsed into one.
    assert len(repo.list_transactions(account_id="acc1")) == 2
