"""PaymentMethod — the central polymorphic type (object model §3.2).

Absorbs the ``PMT_NUMB`` wire overload: that one field means PAN (card), bank
account number (ACH) or IBAN (SEPA/iDEAL/EPS) depending on the rail. The SDK
keys the wire semantics off the concrete variant so a partner never sees it.

v1 fills Card / Token / SavedCard. The rest are declared so a later rail fills a
seam rather than reshaping ``sale()``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union


class PaymentMethod:
    """Base type. Do not subclass outside this module."""

    kind: str = ""


@dataclass(frozen=True)
class Card(PaymentMethod):
    """Raw card-number entry — the number passes through your server. Prefer Token."""

    number: str
    expiry: str
    cvv: Optional[str] = None
    kind: str = "card"


@dataclass(frozen=True)
class Token(PaymentMethod):
    """Single-use ephemeral token -> TOKEN_GUID.

    The token replaces ONLY the PAN. Per spec §4.8.2 a token-based transaction
    still carries PMT_EXPIRY and PMT_KEY, so those travel with the token —
    omitting the expiry yields API 110 "Required field" on REF_FIELD=pmt_expiry.
    Verified against the live T1 gateway.
    """

    guid: str
    expiry: Optional[str] = None
    cvv: Optional[str] = None
    kind: str = "token"


@dataclass(frozen=True)
class SavedCard(PaymentMethod):
    """Previously vaulted card -> PMT_ID / PMT_ID_XTL (+ CUST_ID)."""

    pmt_id: Optional[str] = None
    pmt_id_xtl: Optional[str] = None
    cust_id: Optional[str] = None
    kind: str = "savedCard"


# --- declared for later phases; not constructible paths in v1 --------------


@dataclass(frozen=True)
class NetworkToken(PaymentMethod):
    value: str
    kind: str = "networkToken"


@dataclass(frozen=True)
class WalletToken(PaymentMethod):
    wallet_type: str
    cryptogram: str
    kind: str = "walletToken"


@dataclass(frozen=True)
class DecryptedWalletToken(PaymentMethod):
    provider: str
    tavv: str
    eci: Optional[str] = None
    tid: Optional[str] = None
    kind: str = "decryptedWalletToken"


@dataclass(frozen=True)
class BankAccount(PaymentMethod):
    account_number: str
    routing_number: str
    kind: str = "bankAccount"


@dataclass(frozen=True)
class BankMandate(PaymentMethod):
    iban: str
    debit_type: str
    kind: str = "bankMandate"


PaymentMethodV1 = Union[Card, Token, SavedCard]

_PAN_RE = re.compile(r"^\d{12,19}$")
_EXPIRY_RE = re.compile(r"^\d{6}$")
_CVV_RE = re.compile(r"^\d{3,4}$")


class PaymentMethods:
    """Validating constructors — a bad format fails locally, not as a gateway 111/112."""

    @staticmethod
    def card(number: str, expiry: str, cvv: Optional[str] = None) -> Card:
        digits = re.sub(r"[\s-]", "", number or "")
        if not _PAN_RE.match(digits):
            raise TypeError("PaymentMethods.card: number must be 12-19 digits")
        if not _EXPIRY_RE.match(expiry or ""):
            raise TypeError(
                f"PaymentMethods.card: expiry must be MMYYYY (6 digits), got {expiry!r}"
            )
        month = int(expiry[:2])
        if month < 1 or month > 12:
            raise TypeError(f"PaymentMethods.card: expiry month out of range in {expiry}")
        if cvv is not None and not _CVV_RE.match(cvv):
            raise TypeError("PaymentMethods.card: cvv must be 3-4 digits")
        return Card(number=digits, expiry=expiry, cvv=cvv)

    @staticmethod
    def token(guid: str, expiry: Optional[str] = None, cvv: Optional[str] = None) -> Token:
        """``expiry`` (MMYYYY) is required when the token is used to transact."""
        if not guid:
            raise TypeError("PaymentMethods.token: guid is required")
        if expiry is not None and not _EXPIRY_RE.match(expiry):
            raise TypeError(
                f"PaymentMethods.token: expiry must be MMYYYY (6 digits), got {expiry!r}"
            )
        return Token(guid=guid, expiry=expiry, cvv=cvv)

    @staticmethod
    def saved_card(
        pmt_id: Optional[str] = None,
        pmt_id_xtl: Optional[str] = None,
        cust_id: Optional[str] = None,
    ) -> SavedCard:
        if not pmt_id and not pmt_id_xtl:
            raise TypeError(
                "PaymentMethods.saved_card: one of pmt_id or pmt_id_xtl is required"
            )
        return SavedCard(pmt_id=pmt_id, pmt_id_xtl=pmt_id_xtl, cust_id=cust_id)


def assert_v1_payment_method(pm: PaymentMethod) -> None:
    if not isinstance(pm, (Card, Token, SavedCard)):
        raise TypeError(
            f'payment method "{pm.kind}" is declared in the model but not implemented '
            "in v1 (v1 supports card, token, savedCard)"
        )
