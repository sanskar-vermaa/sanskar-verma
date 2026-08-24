"""Export transactions to CSV for spreadsheets or archival."""

from __future__ import annotations

import csv
import io

from ledger.models.transaction import Transaction


def to_csv(transactions: list[Transaction]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "description", "amount", "currency", "category", "tags"])
    for txn in transactions:
        writer.writerow(
            [
                txn.posted_on.isoformat(),
                txn.description,
                txn.amount.to_major(),
                txn.amount.currency,
                txn.category or "",
                ";".join(txn.tags),
            ]
        )
    return buf.getvalue()
