"""Import transactions from bank-exported CSV statements.

Real bank exports are inconsistent: date format varies by institution,
amounts might be one signed column or separate debit/credit columns, and
files are sometimes UTF-8, sometimes Windows-1252 (Excel exports of
account names with special characters are the usual culprit). This module
normalizes all of that into a stream of Transaction objects.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from datetime import date, datetime

from ledger.models.money import Money
from ledger.models.transaction import Transaction

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%b %d, %Y",
]


class ImportError_(ValueError):
    """Raised when a statement row can't be parsed."""


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportError_("could not decode file with any supported encoding")


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ImportError_(f"unrecognized date format: {value!r}")


def _parse_amount(row: dict, currency: str) -> Money:
    """Handle both single signed-amount columns and split debit/credit columns."""
    if "amount" in row and row["amount"].strip():
        raw = row["amount"].strip().replace(",", "")
        return Money.from_major(raw, currency)

    debit = row.get("debit", "").strip().replace(",", "")
    credit = row.get("credit", "").strip().replace(",", "")
    if debit:
        magnitude = Money.from_major(debit, currency)
        return -magnitude
    if credit:
        return Money.from_major(credit, currency)
    raise ImportError_("row has neither amount nor debit/credit column populated")


def parse_statement(
    raw: bytes, account_id: str, currency: str
) -> Iterator[Transaction]:
    """Parse a CSV bank statement into Transaction objects.

    Expects a header row containing at least `date` and `description`,
    plus either `amount` or `debit`/`credit` columns. Column names are
    matched case-insensitively.
    """
    text = _decode(raw)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return
    normalized_fields = {name: name.strip().lower() for name in reader.fieldnames}

    for line_no, raw_row in enumerate(reader, start=2):
        row = {normalized_fields[k]: (v or "") for k, v in raw_row.items() if k in normalized_fields}
        if not any(v.strip() for v in row.values()):
            continue  # skip blank trailing lines
        try:
            posted_on = _parse_date(row["date"])
            amount = _parse_amount(row, currency)
        except (KeyError, ImportError_) as exc:
            raise ImportError_(f"line {line_no}: {exc}") from exc

        description = row.get("description", "").strip()
        external_id = row.get("id") or row.get("reference") or None

        yield Transaction(
            account_id=account_id,
            posted_on=posted_on,
            amount=amount,
            description=description,
            external_id=external_id.strip() if external_id else None,
        )
