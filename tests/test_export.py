from datetime import date

from ledger.models.money import Money
from ledger.models.transaction import Transaction
from ledger.reports.export import to_csv


def test_export_includes_header_and_row():
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 3, 5),
        amount=Money.from_major("-12.50", "USD"),
        description="COFFEE SHOP",
        category="Dining",
        tags=["personal", "recurring"],
    )
    output = to_csv([txn])
    lines = output.strip().splitlines()
    assert lines[0] == "date,description,amount,currency,category,tags"
    assert lines[1] == "2024-03-05,COFFEE SHOP,-12.50,USD,Dining,personal;recurring"


def test_export_empty_list_is_header_only():
    output = to_csv([])
    lines = output.strip().splitlines()
    assert len(lines) == 1


def test_export_handles_missing_category_and_tags():
    txn = Transaction(
        account_id="acc1",
        posted_on=date(2024, 3, 5),
        amount=Money.from_major("100.00", "USD"),
        description="DEPOSIT",
    )
    output = to_csv([txn])
    assert "DEPOSIT,100.00,USD,," in output
