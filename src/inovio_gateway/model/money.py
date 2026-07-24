"""Money — decimal amount + ISO-4217 currency (object model §3.3 / Q7)."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"^-?\d+(\.\d+)?$")
_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")


class Money:
    """An amount is a ``Decimal``, never a ``float``.

    Binary floats cannot represent decimal amounts exactly (0.1 + 0.2 != 0.3)
    and the wire format is a decimal string like "1.25". Passing a float would
    silently corrupt amounts, so the constructor rejects it outright.
    """

    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Decimal, currency: str) -> None:
        self._amount = amount
        self._currency = currency

    @classmethod
    def of(cls, amount, currency: str) -> "Money":
        if isinstance(amount, float):
            raise TypeError(
                "Money.of: amount must be a Decimal or decimal string, not a float — "
                "binary floats cannot represent decimal amounts exactly. "
                'Pass Decimal("1.25") or "1.25", not 1.25.'
            )
        if isinstance(amount, Decimal):
            text = format(amount, "f")
        elif isinstance(amount, str):
            text = amount.strip()
        elif isinstance(amount, int):
            text = str(amount)
        else:
            raise TypeError(
                f"Money.of: amount must be a Decimal, str or int, got {type(amount).__name__}"
            )
        if not _AMOUNT_RE.match(text):
            raise TypeError(
                f'Money.of: amount must be a decimal string like "1.25", got {text!r}'
            )
        if not isinstance(currency, str) or not _CURRENCY_RE.match(currency.strip()):
            raise TypeError(
                f'Money.of: currency must be an ISO-4217 alpha-3 code like "USD", got {currency!r}'
            )
        try:
            value = Decimal(text)
        except InvalidOperation as exc:  # pragma: no cover - guarded by regex
            raise TypeError(f"Money.of: invalid amount {text!r}") from exc
        return cls(value, currency.strip().upper())

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    def to_wire(self) -> str:
        """Wire representation (what goes into LI_VALUE_n)."""
        return format(self._amount, "f")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._currency == other._currency and self._amount == other._amount

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __repr__(self) -> str:
        return f"Money({self.to_wire()!r}, {self._currency!r})"

    def __str__(self) -> str:
        return f"{self.to_wire()} {self._currency}"
