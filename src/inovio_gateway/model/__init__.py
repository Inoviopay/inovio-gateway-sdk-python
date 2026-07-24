"""Shared request building blocks (object model §3.3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .money import Money
from .payment_method import (
    BankAccount,
    BankMandate,
    Card,
    DecryptedWalletToken,
    NetworkToken,
    PaymentMethod,
    PaymentMethods,
    PaymentMethodV1,
    SavedCard,
    Token,
    WalletToken,
    assert_v1_payment_method,
)

__all__ = [
    "Money", "PaymentMethod", "PaymentMethods", "PaymentMethodV1",
    "Card", "Token", "SavedCard", "NetworkToken", "WalletToken",
    "DecryptedWalletToken", "BankAccount", "BankMandate",
    "assert_v1_payment_method",
    "Customer", "Address", "LineItem", "Descriptor", "RiskOptions",
    "TimeoutVoid", "PartialAuth", "Idempotency", "Recurring", "Fees",
    "Affiliate", "Metadata", "BrowserData",
]


@dataclass
class Customer:
    """CUST_* + XTL_IP"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    birthday: Optional[str] = None      # MM-DD-YYYY per spec §4.2
    dln: Optional[str] = None
    dln_state: Optional[str] = None
    ssn_last4: Optional[str] = None
    br_cpf_cnpj: Optional[str] = None   # presence activates Credilink
    ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class Address:
    """BILL_ADDR_* / SHIP_ADDR_*"""
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None       # ISO-2
    district: Optional[str] = None


@dataclass
class LineItem:
    """LI_*_n — the SDK owns the 1-based wire indexing."""
    product_id: str
    count: int
    value: Money
    xtl_product_id: Optional[str] = None
    type: Optional[str] = None


@dataclass
class Descriptor:
    """PMT_DESCRIPTOR*"""
    name: str
    phone: Optional[str] = None
    city: Optional[str] = None


@dataclass
class TimeoutVoid:
    """Spec §14.3 — opt-in, NOT defaulted on (Q6). Range 30..600 seconds."""
    seconds: int


@dataclass
class RiskOptions:
    """CHKAVS / CHKCVV / REQUEST_MAX_WAIT"""
    avs: Optional[str] = None            # on|off|ignore|conditional
    avs_match_set: Optional[str] = None
    cvv: Optional[str] = None
    cvv_match_set: Optional[str] = None
    timeout_void: Optional[TimeoutVoid] = None


@dataclass
class PartialAuth:
    enabled: bool = False
    minimum_amount: Optional[Money] = None


@dataclass
class Idempotency:
    """``mode`` maps to UNIQUE_XTL_ORDER_ID. Defaults to RETURN_ORIGINAL (retry-safe)."""
    xtl_order_id: str
    mode: Optional[str] = None           # OFF|DECLINE_DUP|RETURN_ORIGINAL


@dataclass
class Recurring:
    """Card-on-file / recurring compliance flags (Appendices G/J/K)."""
    initiator: Optional[str] = None      # CIT|MIT
    rebill: Optional[str] = None         # NONE|REBILL|START_SUBSCRIPTION
    rebill_type: Optional[str] = None    # NONE|TRIAL|INITIAL|REBILL
    installment: Optional[bool] = None
    card_on_file: Optional[bool] = None
    membership_xtl_id: Optional[str] = None
    trial_consent: Optional[bool] = None
    receipt: Optional[str] = None


@dataclass
class Tax:
    amount: Money
    exempt: Optional[bool] = None


@dataclass
class Fees:
    tax: Optional[Tax] = None
    convenience_fee: Optional[Money] = None


@dataclass
class Affiliate:
    aff_id: Optional[str] = None
    sub_aff_id: Optional[str] = None


@dataclass
class Metadata:
    udf: Dict[str, str] = field(default_factory=dict)
    tppe_id: Optional[str] = None
    proc_udf1: Optional[str] = None
    proc_udf2: Optional[str] = None


@dataclass
class BrowserData:
    """3DS — the gateway silently disables 3DS if any of these is missing."""
    language: str
    user_agent: str
    header: str
