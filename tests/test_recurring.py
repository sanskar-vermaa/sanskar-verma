from datetime import date, timedelta

from ledger.models.money import Money
from ledger.models.transaction import Transaction
from ledger.rules.recurring import detect_recurring


def _txn(day: date, amount: str, description: str, account="acc1") -> Transaction:
    return Transaction(
        account_id=account,
        posted_on=day,
        amount=Money.from_major(amount, "USD"),
        description=description,
    )


def test_detects_monthly_subscription_with_amount_drift():
    txns = [
        _txn(date(2024, 1, 3), "-9.99", "NETFLIX.COM"),
        _txn(date(2024, 2, 3), "-9.99", "NETFLIX.COM"),
        _txn(date(2024, 3, 4), "-10.99", "NETFLIX.COM"),  # price increase, still within 5% is false here
    ]
    # 10.99 is ~10% above 9.99 median -> should NOT match with default 5% tolerance
    series = detect_recurring(txns, amount_tolerance_ratio=0.05)
    assert series == []

    series = detect_recurring(txns, amount_tolerance_ratio=0.15)
    assert len(series) == 1
    assert series[0].occurrences == 3


def test_ignores_one_off_transactions():
    txns = [_txn(date(2024, 1, 1), "-50.00", "RANDOM STORE")]
    assert detect_recurring(txns) == []


def test_normalizes_volatile_store_numbers_in_description():
    txns = [
        _txn(date(2024, 1, 5), "-45.00", "AMAZON.COM*A1B2C3D4"),
        _txn(date(2024, 2, 4), "-45.00", "AMAZON.COM*X9Y8Z7W6"),
        _txn(date(2024, 3, 6), "-45.00", "AMAZON.COM*Q1R2S3T4"),
    ]
    series = detect_recurring(txns)
    assert len(series) == 1
    assert series[0].occurrences == 3


def test_irregular_intervals_are_not_recurring():
    txns = [
        _txn(date(2024, 1, 1), "-20.00", "RANDOM SHOP"),
        _txn(date(2024, 1, 15), "-20.00", "RANDOM SHOP"),
        _txn(date(2024, 3, 20), "-20.00", "RANDOM SHOP"),
    ]
    assert detect_recurring(txns) == []


def test_separate_accounts_not_merged():
    txns = [
        _txn(date(2024, 1, 3), "-9.99", "NETFLIX.COM", account="acc1"),
        _txn(date(2024, 2, 3), "-9.99", "NETFLIX.COM", account="acc2"),
        _txn(date(2024, 3, 3), "-9.99", "NETFLIX.COM", account="acc1"),
    ]
    assert detect_recurring(txns) == []


def test_weekly_payroll_deposit():
    start = date(2024, 1, 5)
    txns = [
        _txn(start + timedelta(weeks=i), "1500.00", "ACME CORP PAYROLL")
        for i in range(4)
    ]
    series = detect_recurring(txns)
    assert len(series) == 1
    assert series[0].approx_interval_days == 7
    assert series[0].approx_amount.amount_minor == 150000
