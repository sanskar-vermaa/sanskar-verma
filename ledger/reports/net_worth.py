"""Aggregate balances across accounts in different currencies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ledger.models.money import Money


@dataclass
class NetWorthReport:
    base_currency: str
    total: Money
    by_account: dict[str, Money]


def compute_net_worth(
    balances: dict[str, Money],
    base_currency: str,
    exchange_rates: dict[str, Decimal],
) -> NetWorthReport:
    """Sum account balances into a single base-currency total.

    `exchange_rates` maps a currency code to "units of base_currency per
    1 unit of that currency". Accounts already in `base_currency` don't
    need an entry. Raises KeyError if a balance's currency has no rate
    and isn't the base currency -- silently skipping an account would
    understate net worth without any indication something was omitted.
    """
    total = Money.zero(base_currency)
    for account_id, balance in balances.items():
        if balance.currency == base_currency:
            converted = balance
        else:
            rate = exchange_rates[balance.currency]
            converted = balance.convert(base_currency, rate)
        total = total + converted

    return NetWorthReport(base_currency=base_currency, total=total, by_account=dict(balances))
