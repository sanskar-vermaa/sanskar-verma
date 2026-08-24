"""Currency-safe money type.

Money amounts are stored as integer minor units (e.g. cents) to avoid the
rounding drift that comes from doing arithmetic on floats or even on
Decimals with inconsistent quantization. All arithmetic between two Money
values requires matching currencies; converting currencies is a deliberate,
explicit operation (see `convert`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

# Number of minor units per major unit, per currency. Not every currency
# uses 2 decimal places (JPY uses 0, BHD uses 3).
_MINOR_UNIT_EXPONENT = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "INR": 2,
    "JPY": 0,
    "BHD": 3,
    "KWD": 3,
}

_DEFAULT_EXPONENT = 2


def _exponent(currency: str) -> int:
    return _MINOR_UNIT_EXPONENT.get(currency.upper(), _DEFAULT_EXPONENT)


@dataclass(frozen=True, order=True)
class Money:
    """An exact monetary amount in a single currency.

    `amount_minor` is the integer number of minor units (cents, paise,
    etc). Use `Money.from_major` to construct from a human decimal string
    like "12.50".
    """

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def from_major(cls, amount: str | Decimal, currency: str) -> "Money":
        currency = currency.upper()
        exp = _exponent(currency)
        quantum = Decimal(1).scaleb(-exp)
        dec = Decimal(amount).quantize(quantum, rounding=ROUND_HALF_EVEN)
        minor = int(dec.scaleb(exp))
        return cls(minor, currency)

    @classmethod
    def zero(cls, currency: str) -> "Money":
        return cls(0, currency.upper())

    def to_major(self) -> Decimal:
        exp = _exponent(self.currency)
        return Decimal(self.amount_minor).scaleb(-exp)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"cannot combine {self.currency} with {other.currency} directly; "
                "use convert() first"
            )

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount_minor, self.currency)

    def __mul__(self, factor: int | Decimal) -> "Money":
        if isinstance(factor, int):
            return Money(self.amount_minor * factor, self.currency)
        exp = _exponent(self.currency)
        quantum = Decimal(1).scaleb(-exp)
        scaled = (Decimal(self.amount_minor) * factor).quantize(
            quantum, rounding=ROUND_HALF_EVEN
        )
        return Money(int(scaled), self.currency)

    def is_negative(self) -> bool:
        return self.amount_minor < 0

    def convert(self, target_currency: str, rate: Decimal) -> "Money":
        """Convert to another currency using `rate` units of target per 1 unit of self.

        The conversion is done in major units at full Decimal precision and
        only quantized to the target currency's minor unit at the end, so
        rounding error doesn't compound across chained conversions.
        """
        target_currency = target_currency.upper()
        converted_major = self.to_major() * rate
        return Money.from_major(converted_major, target_currency)

    def __str__(self) -> str:
        exp = _exponent(self.currency)
        return f"{self.to_major():.{exp}f} {self.currency}"
