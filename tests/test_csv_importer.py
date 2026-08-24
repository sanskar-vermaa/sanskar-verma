import pytest

from ledger.importers.csv_importer import ImportError_, parse_statement


def test_parses_signed_amount_column():
    csv_bytes = (
        b"Date,Description,Amount,Id\n"
        b"2024-01-05,COFFEE SHOP,-4.50,tx1\n"
        b"2024-01-06,PAYCHECK,2000.00,tx2\n"
    )
    txns = list(parse_statement(csv_bytes, "acc1", "USD"))
    assert len(txns) == 2
    assert txns[0].amount.amount_minor == -450
    assert txns[0].external_id == "tx1"
    assert txns[1].amount.amount_minor == 200000


def test_parses_debit_credit_columns():
    csv_bytes = (
        b"Date,Description,Debit,Credit\n"
        b"01/05/2024,GROCERY STORE,25.10,\n"
        b"01/06/2024,REFUND,,10.00\n"
    )
    txns = list(parse_statement(csv_bytes, "acc1", "USD"))
    assert txns[0].amount.amount_minor == -2510
    assert txns[1].amount.amount_minor == 1000


def test_handles_multiple_date_formats_in_sequence():
    # Not realistic within one file, but each row is parsed independently
    # so mixed formats across different statements from different banks
    # all go through the same code path.
    csv_bytes = b'Date,Description,Amount\n"Jan 05, 2024",TEST,-1.00\n'
    txns = list(parse_statement(csv_bytes, "acc1", "USD"))
    assert txns[0].posted_on.isoformat() == "2024-01-05"


def test_skips_blank_trailing_rows():
    csv_bytes = b"Date,Description,Amount\n2024-01-05,TEST,-1.00\n,,\n"
    txns = list(parse_statement(csv_bytes, "acc1", "USD"))
    assert len(txns) == 1


def test_decodes_cp1252_fallback():
    # 0x92 is a right single quote in cp1252 but invalid utf-8 on its own.
    raw = b"Date,Description,Amount\n2024-01-05,JOE\x92S DINER,-12.00\n"
    txns = list(parse_statement(raw, "acc1", "USD"))
    assert "JOE" in txns[0].description

def test_raises_on_missing_amount_and_debit_credit():
    csv_bytes = b"Date,Description\n2024-01-05,MYSTERY CHARGE\n"
    with pytest.raises(ImportError_):
        list(parse_statement(csv_bytes, "acc1", "USD"))


def test_raises_on_unrecognized_date():
    csv_bytes = b"Date,Description,Amount\n2024.01.05,TEST,-1.00\n"
    with pytest.raises(ImportError_):
        list(parse_statement(csv_bytes, "acc1", "USD"))
