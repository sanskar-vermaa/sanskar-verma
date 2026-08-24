from decimal import Decimal

import pytest

from ledger.models.money import Money
from ledger.reports.net_worth import compute_net_worth


def test_single_currency_sums_directly():
    balances = {"checking": Money.from_major("1000.00", "USD"), "savings": Money.from_major("5000.00", "USD")}
    report = compute_net_worth(balances, "USD", {})
    assert report.total.amount_minor == 600000


def test_converts_foreign_balances():
    balances = {
        "checking_usd": Money.from_major("1000.00", "USD"),
        "checking_eur": Money.from_major("100.00", "EUR"),
    }
    report = compute_net_worth(balances, "USD", {"EUR": Decimal("1.10")})
    # 1000 + (100 * 1.10) = 1110
    assert report.total.amount_minor == 111000


def test_missing_rate_raises():
    balances = {"acc": Money.from_major("100.00", "EUR")}
    with pytest.raises(KeyError):
        compute_net_worth(balances, "USD", {})


def test_empty_balances_is_zero():
    report = compute_net_worth({}, "USD", {})
    assert report.total.amount_minor == 0
