"""Typed identity wrappers (object model §3.4).

There is no single transaction handle in the gateway — different follow-ups
consume different keys (§1.4). Distinct types make it impossible to hand
``capture()`` a customer id by mistake.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderRef:
    """Gateway order id (PO_ID) -> REQUEST_REF_PO_ID"""
    po_id: str


@dataclass(frozen=True)
class XtlOrderId:
    """Merchant order id (XTL_ORDER_ID) -> REQUEST_REF_PO_ID_XTL; idempotency key"""
    value: str


@dataclass(frozen=True)
class LineItemRef:
    """Gateway line-item id (PO_LI_ID_n) -> REQUEST_REF_PO_LI_ID"""
    po_li_id: str


@dataclass(frozen=True)
class TransactionId:
    value: str


@dataclass(frozen=True)
class ReqId:
    value: str


@dataclass(frozen=True)
class BatchId:
    value: str


@dataclass(frozen=True)
class CustomerRef:
    cust_id: Optional[str] = None
    xtl_cust_id: Optional[str] = None


@dataclass(frozen=True)
class SavedCardRef:
    pmt_id: Optional[str] = None
    pmt_id_xtl: Optional[str] = None


@dataclass(frozen=True)
class MembershipRef:
    mbshp_id: Optional[str] = None
    mbshp_id_xtl: Optional[str] = None


class Refs:
    @staticmethod
    def order(po_id: str) -> OrderRef:
        if not po_id:
            raise TypeError("Refs.order: po_id is required")
        return OrderRef(po_id)

    @staticmethod
    def xtl_order(value: str) -> XtlOrderId:
        if not value:
            raise TypeError("Refs.xtl_order: value is required")
        return XtlOrderId(value)

    @staticmethod
    def line_item(po_li_id: str) -> LineItemRef:
        if not po_li_id:
            raise TypeError("Refs.line_item: po_li_id is required")
        return LineItemRef(po_li_id)

    transaction = staticmethod(lambda v: TransactionId(v))
    req = staticmethod(lambda v: ReqId(v))
    batch = staticmethod(lambda v: BatchId(v))
    customer = staticmethod(lambda **kw: CustomerRef(**kw))
    saved_card = staticmethod(lambda **kw: SavedCardRef(**kw))
    membership = staticmethod(lambda **kw: MembershipRef(**kw))
