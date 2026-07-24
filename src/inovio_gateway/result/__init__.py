"""TransactionResult and OrderStatus (object model §3.5, §3.6).

Two deliberate shapes, both load-bearing:

1. NO derived ``approved``/``declined`` booleans. ``status`` is the only way to
   ask about outcome. Booleans invite ``if approved: ... else: ...`` which
   silently treats PENDING as failure — the exact card-shaped mental model the
   5-state lifecycle exists to prevent.
2. Reference keys are FLAT, not nested in a ``refs`` bag. They are the most
   touched fields on the result (``capture(result.order_ref, ...)``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..enums.generated import AvsCodeInfo, CvvCodeInfo, TransactionStatus
from ..model.money import Money
from ..refs import (
    BatchId, CustomerRef, LineItemRef, MembershipRef, OrderRef, ReqId,
    SavedCardRef, TransactionId, XtlOrderId,
)


@dataclass(frozen=True)
class OutcomeTier:
    code: Optional[int] = None
    advice: Optional[str] = None


@dataclass(frozen=True)
class ApiOutcomeTier(OutcomeTier):
    ref_field: Optional[str] = None


@dataclass(frozen=True)
class Outcome:
    """The four independent tiers, outermost -> innermost (§1.3)."""
    api: ApiOutcomeTier
    service: OutcomeTier
    processor: OutcomeTier
    industry: OutcomeTier


@dataclass(frozen=True)
class ServiceClassification:
    retryable: bool
    stop_recurring: bool
    terminal: bool
    approval: bool


@dataclass(frozen=True)
class AccountUpdater:
    description: Optional[str] = None
    date: Optional[str] = None
    new_expiry: Optional[str] = None
    new_last4: Optional[str] = None


@dataclass(frozen=True)
class CardInfo:
    brand: Optional[str] = None
    detail: Optional[str] = None
    type: Optional[str] = None
    card_class: Optional[str] = None
    country: Optional[str] = None
    bank: Optional[str] = None
    prepaid: Optional[bool] = None
    balance: Optional[str] = None
    last4: Optional[str] = None
    network_token_used: Optional[int] = None
    account_updater: Optional[AccountUpdater] = None


@dataclass(frozen=True)
class NextAction:
    """What must happen next when status is PENDING (§4.1)."""
    kind: str        # redirect|displayVoucher|displayQr|threeDSChallenge|awaitSettlement
    url: Optional[str] = None
    barcode: Optional[str] = None
    token: Optional[str] = None
    redirect_url: Optional[str] = None
    jwt: Optional[str] = None
    proc_trans_id: Optional[str] = None
    pareq: Optional[str] = None


@dataclass(frozen=True)
class Conversion:
    amount: Money
    exchange_rate: str


@dataclass(frozen=True)
class AvsResult:
    code: str
    description: str
    card_network: str
    classification: str
    raw: str


@dataclass(frozen=True)
class CvvResult:
    code: str
    description: str
    classification: str
    raw: str


@dataclass(frozen=True)
class TransactionResult:
    status: TransactionStatus
    #: PENDING or RUNNING — a genuine grouping, not an alias for status.
    settling: bool
    action: str
    outcome: Outcome
    #: The FACT of settlement. Written 0 at auth and flipped later by batch, so
    #: this is usually False at response time and is NOT a failure signal.
    settled: bool
    raw: Dict[str, str]
    line_item_refs: List[LineItemRef] = field(default_factory=list)
    order_ref: Optional[OrderRef] = None
    xtl_order_ref: Optional[XtlOrderId] = None
    transaction_id: Optional[TransactionId] = None
    request_id: Optional[ReqId] = None
    batch_id: Optional[BatchId] = None
    customer_ref: Optional[CustomerRef] = None
    saved_card_ref: Optional[SavedCardRef] = None
    membership_ref: Optional[MembershipRef] = None
    amount: Optional[Money] = None
    #: Present ONLY when real currency conversion occurred. On domestic
    #: transactions the wire's "settled" amount is the auth amount echoed back,
    #: so an always-present block would mean nothing.
    conversion: Optional[Conversion] = None
    service_classification: Optional[ServiceClassification] = None
    avs: Optional[AvsResult] = None
    cvv: Optional[CvvResult] = None
    card: Optional[CardInfo] = None
    next_action: Optional[NextAction] = None


@dataclass(frozen=True)
class OrderStatus:
    """The order is the aggregation root (§3.6).

    Partial capture, refund and void are SEPARATE transaction rows sharing a
    PO_ID, not modifications of the original — so net position is an order-level
    question. These figures mirror BATCH_PKG's own sibling-sum keyed on PO_ID.
    """
    ref: OrderRef
    transactions: List[TransactionResult]
    settled: bool
    raw: Dict[str, str]
    xtl_ref: Optional[XtlOrderId] = None
    authorized: Optional[Money] = None
    captured: Optional[Money] = None
    refunded: Optional[Money] = None
    net: Optional[Money] = None
    outstanding: Optional[Money] = None


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    action: str
    outcome: Outcome
    raw: Dict[str, str]
