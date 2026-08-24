from decimal import Decimal

import pytest

from ledger.models.money import Money


def test_from_major_rounds_half_even():
    assert Money.from_major("10.005", "USD").amount_minor == 1000  # rounds to even
    assert Money.from_major("10.015", "USD").amount_minor == 1002


def test_zero_decimal_currency():
    m = Money.from_major("1500", "JPY")
    assert m.amount_minor == 1500
    assert str(m) == "1500 JPY"


def test_three_decimal_currency():
    m = Money.from_major("1.234", "BHD")
    assert m.amount_minor == 1234


def test_addition_same_currency():
    a = Money.from_major("10.50", "USD")
    b = Money.from_major("2.25", "USD")
    assert (a + b).amount_minor == 1275


def test_addition_different_currency_raises():
    a = Money.from_major("10.00", "USD")
    b = Money.from_major("10.00", "EUR")
    with pytest.raises(ValueError):
        a + b


def test_convert_preserves_precision():
    a = Money.from_major("100.00", "USD")
    converted = a.convert("INR", Decimal("83.127"))
    assert converted.currency == "INR"
    assert converted.amount_minor == 831270  # 8312.70 INR


def test_multiply_by_decimal_factor():
    a = Money.from_major("100.00", "USD")
    result = a * Decimal("0.5")
    assert result.amount_minor == 5000


def test_multiply_by_int_factor():
    a = Money.from_major("10.00", "USD")
    result = a * 3
    assert result.amount_minor == 3000


def test_is_negative():
    assert Money.from_major("-5.00", "USD").is_negative()
    assert not Money.from_major("5.00", "USD").is_negative()


def test_subtraction():
    a = Money.from_major("10.00", "USD")
    b = Money.from_major("4.50", "USD")
    assert (a - b).amount_minor == 550


def test_negation():
    a = Money.from_major("10.00", "USD")
    assert (-a).amount_minor == -1000


def test_currency_is_normalized_to_uppercase():
    a = Money.from_major("10.00", "usd")
    assert a.currency == "USD"


def test_ordering():
    small = Money.from_major("5.00", "USD")
    large = Money.from_major("10.00", "USD")
    assert small < large
    assert sorted([large, small]) == [small, large]
