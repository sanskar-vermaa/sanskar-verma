"""Repository layer: translate between domain models and SQLite rows."""

from __future__ import annotations

import sqlite3
from datetime import date

from ledger.models.money import Money
from ledger.models.transaction import Account, Transaction


class TransactionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_account(self, account: Account) -> None:
        self._conn.execute(
            """
            INSERT INTO accounts (account_id, name, currency, opening_balance_minor)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                name = excluded.name,
                currency = excluded.currency,
                opening_balance_minor = excluded.opening_balance_minor
            """,
            (
                account.account_id,
                account.name,
                account.currency,
                account.opening_balance.amount_minor,
            ),
        )
        self._conn.commit()

    def get_account(self, account_id: str) -> Account | None:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        if row is None:
            return None
        return Account(
            account_id=row["account_id"],
            name=row["name"],
            currency=row["currency"],
            opening_balance=Money(row["opening_balance_minor"], row["currency"]),
        )

    def add_transaction(self, txn: Transaction) -> int:
        """Insert a transaction, returning its id.

        Returns the id of the existing row (not a new insert) if this
        transaction's (account_id, external_id) pair already exists --
        this is how re-importing the same statement stays idempotent.
        """
        cur = self._conn.execute(
            """
            INSERT INTO transactions
                (account_id, posted_on, amount_minor, currency, description,
                 external_id, category, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, external_id) DO UPDATE SET
                description = excluded.description
            """,
            (
                txn.account_id,
                txn.posted_on.isoformat(),
                txn.amount.amount_minor,
                txn.amount.currency,
                txn.description,
                txn.external_id,
                txn.category,
                ",".join(txn.tags),
            ),
        )
        self._conn.commit()
        if cur.lastrowid and cur.rowcount == 1:
            return cur.lastrowid
        row = self._conn.execute(
            "SELECT transaction_id FROM transactions WHERE account_id = ? AND external_id = ?",
            (txn.account_id, txn.external_id),
        ).fetchone()
        return row["transaction_id"]

    def set_category(self, transaction_id: int, category: str) -> None:
        self._conn.execute(
            "UPDATE transactions SET category = ? WHERE transaction_id = ?",
            (category, transaction_id),
        )
        self._conn.commit()

    def add_tag(self, transaction_id: int, tag: str) -> None:
        row = self._conn.execute(
            "SELECT tags FROM transactions WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"no transaction with id {transaction_id}")
        tags = [t for t in row["tags"].split(",") if t]
        if tag not in tags:
            tags.append(tag)
        self._conn.execute(
            "UPDATE transactions SET tags = ? WHERE transaction_id = ?",
            (",".join(tags), transaction_id),
        )
        self._conn.commit()

    def list_transactions(
        self,
        account_id: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Transaction]:
        query = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        if start is not None:
            query += " AND posted_on >= ?"
            params.append(start.isoformat())
        if end is not None:
            query += " AND posted_on <= ?"
            params.append(end.isoformat())
        query += " ORDER BY posted_on ASC, transaction_id ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [_row_to_transaction(row) for row in rows]


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    tags = [t for t in row["tags"].split(",") if t]
    return Transaction(
        transaction_id=row["transaction_id"],
        account_id=row["account_id"],
        posted_on=date.fromisoformat(row["posted_on"]),
        amount=Money(row["amount_minor"], row["currency"]),
        description=row["description"],
        external_id=row["external_id"],
        category=row["category"],
        tags=tags,
    )
