"""Wire response -> typed TransactionResult / OrderStatus.

All the "is this approved" judgment lives here and in the generated spec enums,
so every language SDK classifies identically.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Optional

from ..enums.generated import (
    AVS_CODES, CVV_CODES, SERVICE_RESPONSE_CODES, TransactionStatus,
)
from ..errors import TransportError
from ..model.money import Money
from ..refs import Refs
from . import (
    AccountUpdater, ApiOutcomeTier, AvsResult, CardInfo, Conversion, CvvResult,
    HealthResult, NextAction, OrderStatus, Outcome, OutcomeTier,
    ServiceClassification, TransactionResult,
)


def _num(v: Optional[str]) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def _flag(v: Optional[str]) -> bool:
    return v == "1" or (v or "").upper() in ("Y", "TRUE")


def _outcome(r: Dict[str, str]) -> Outcome:
    return Outcome(
        api=ApiOutcomeTier(_num(r.get("API_RESPONSE")), r.get("API_ADVICE"), r.get("REF_FIELD")),
        service=OutcomeTier(_num(r.get("SERVICE_RESPONSE")), r.get("SERVICE_ADVICE")),
        processor=OutcomeTier(_num(r.get("PROCESSOR_RESPONSE")), r.get("PROCESSOR_ADVICE")),
        industry=OutcomeTier(_num(r.get("INDUSTRY_RESPONSE")), r.get("INDUSTRY_ADVICE")),
    )


def _card(r: Dict[str, str]) -> Optional[CardInfo]:
    if not any(r.get(k) for k in ("CARD_BRAND_NAME", "PMT_L4", "CARD_TYPE", "CARD_BANK", "CARD_COUNTRY")):
        return None
    au = None
    if r.get("PMT_AAU_UPDATE_DESC") or r.get("PMT_AAU_UPDATE_DATE"):
        au = AccountUpdater(
            description=r.get("PMT_AAU_UPDATE_DESC"),
            date=r.get("PMT_AAU_UPDATE_DATE"),
            new_expiry=r.get("PMT_AAU_UPDATE_EXPIRY"),
            new_last4=r.get("PMT_AAU_UPDATE_L4"),
        )
    return CardInfo(
        brand=r.get("CARD_BRAND_NAME"), detail=r.get("CARD_DETAIL"),
        type=r.get("CARD_TYPE"), card_class=r.get("CARD_CLASS"),
        country=r.get("CARD_COUNTRY"), bank=r.get("CARD_BANK"),
        prepaid=r.get("CARD_PREPAID") == "1", balance=r.get("CARD_BALANCE"),
        last4=r.get("PMT_L4"), network_token_used=_num(r.get("TRANS_NTOKEN_USED")),
        account_updater=au,
    )


def _next_action(r: Dict[str, str], status: TransactionStatus) -> Optional[NextAction]:
    if status is not TransactionStatus.PENDING:
        return None
    if r.get("P3DS_PROCTRANSID") or r.get("PAREQ") or r.get("P3DS_JWT"):
        return NextAction(
            kind="threeDSChallenge", redirect_url=r.get("PROC_REDIRECT_URL"),
            jwt=r.get("P3DS_JWT"), proc_trans_id=r.get("P3DS_PROCTRANSID"),
            pareq=r.get("PAREQ"),
        )
    if r.get("PROC_BARCODE"):
        return NextAction(kind="displayVoucher", url=r.get("PROC_REDIRECT_URL"), barcode=r.get("PROC_BARCODE"))
    if r.get("PIX_TOKEN"):
        return NextAction(kind="displayQr", url=r.get("PROC_REDIRECT_URL"), token=r.get("PIX_TOKEN"))
    if r.get("PROC_REDIRECT_URL"):
        return NextAction(kind="redirect", url=r.get("PROC_REDIRECT_URL"))
    return NextAction(kind="awaitSettlement")


def _parse_status(raw: Optional[str]) -> TransactionStatus:
    s = (raw or "").upper().strip()
    try:
        return TransactionStatus(s)
    except ValueError:
        # An unrecognized status must not silently read as approved.
        return TransactionStatus.FAILED


def to_transaction_result(r: Dict[str, str]) -> TransactionResult:
    status = _parse_status(r.get("TRANS_STATUS_NAME"))
    svc_code = _num(r.get("SERVICE_RESPONSE"))
    svc = SERVICE_RESPONSE_CODES.get(svc_code) if svc_code is not None else None

    li_refs = [
        Refs.line_item(r[k])
        for k in sorted(
            (k for k in r if re.fullmatch(r"PO_LI_ID_\d+", k)),
            key=lambda k: int(k.rsplit("_", 1)[1]),
        )
    ]

    amount = (
        Money.of(r["TRANS_VALUE"], r["CURR_CODE_ALPHA"])
        if r.get("TRANS_VALUE") and r.get("CURR_CODE_ALPHA")
        else None
    )

    # Conversion is reported ONLY on real FX — otherwise the "settled" fields
    # are just the auth amount echoed back and would mean nothing.
    rate = r.get("TRANS_EXCH_RATE")
    conversion = None
    if rate and Decimal(rate) != 0 and r.get("TRANS_VALUE_SETTLED") and r.get("CURR_CODE_ALPHA_SETTLED"):
        conversion = Conversion(
            amount=Money.of(r["TRANS_VALUE_SETTLED"], r["CURR_CODE_ALPHA_SETTLED"]),
            exchange_rate=rate,
        )

    avs_raw = r.get("AVS_RESPONSE")
    avs_info = AVS_CODES.get((avs_raw or "").upper())
    cvv_raw = r.get("CVV_RESPONSE")
    cvv_info = CVV_CODES.get((cvv_raw or "").upper())

    return TransactionResult(
        status=status,
        settling=status in (TransactionStatus.PENDING, TransactionStatus.RUNNING),
        action=r.get("REQUEST_ACTION", ""),
        order_ref=Refs.order(r["PO_ID"]) if r.get("PO_ID") else None,
        xtl_order_ref=Refs.xtl_order(r["XTL_ORDER_ID"]) if r.get("XTL_ORDER_ID") else None,
        transaction_id=Refs.transaction(r["TRANS_ID"]) if r.get("TRANS_ID") else None,
        request_id=Refs.req(r["REQ_ID"]) if r.get("REQ_ID") else None,
        batch_id=Refs.batch(r["BATCH_ID"]) if r.get("BATCH_ID") else None,
        customer_ref=(
            Refs.customer(cust_id=r.get("CUST_ID"), xtl_cust_id=r.get("XTL_CUST_ID"))
            if r.get("CUST_ID") or r.get("XTL_CUST_ID") else None
        ),
        saved_card_ref=(
            Refs.saved_card(pmt_id=r.get("PMT_ID"), pmt_id_xtl=r.get("PMT_ID_XTL"))
            if r.get("PMT_ID") or r.get("PMT_ID_XTL") else None
        ),
        membership_ref=(
            Refs.membership(mbshp_id=r.get("MBSHP_ID"), mbshp_id_xtl=r.get("MBSHP_ID_XTL"))
            if r.get("MBSHP_ID") or r.get("MBSHP_ID_XTL") else None
        ),
        line_item_refs=li_refs,
        amount=amount,
        settled=_flag(r.get("TRANS_SETTLED")),
        conversion=conversion,
        outcome=_outcome(r),
        service_classification=(
            ServiceClassification(svc.retryable, svc.stop_recurring, svc.terminal, svc.approval)
            if svc else None
        ),
        avs=AvsResult(avs_info.code, avs_info.description, avs_info.card_network,
                      avs_info.classification, avs_raw) if avs_info else None,
        cvv=CvvResult(cvv_info.code, cvv_info.description, cvv_info.classification,
                      cvv_raw) if cvv_info else None,
        card=_card(r),
        next_action=_next_action(r, status),
        raw=dict(r),
    )


def _sum(values: List[Decimal], currency: str) -> Money:
    """Sum decimal amounts.

    Amounts may be NEGATIVE: the gateway reports credit and void legs with a
    negative TRANS_VALUE, so a refund of 1.00 arrives as -1. Confirmed against
    the live T1 gateway.
    """
    total = sum(values, Decimal("0"))
    return Money.of(total, currency)


def to_order_status(r: Dict[str, str], legs: List[TransactionResult]) -> OrderStatus:
    """Net position mirrors BATCH_PKG's sibling-sum keyed on PO_ID (§3.6)."""
    currency = next((l.amount.currency for l in legs if l.amount), None) or r.get("CURR_CODE_ALPHA", "USD")

    def amounts(pred) -> List[Decimal]:
        return [l.amount.amount for l in legs if pred(l) and l.amount]

    # Four distinct leg kinds — conflating void with refund gets the maths wrong.
    #
    #   CCAUTHORIZE / CCAUTHCAP  : establishes the authorized amount
    #   CCCAPTURE                : draws down against the authorization
    #   CCCREDIT                 : refunds a capture (money returned)
    #   CCREVERSE / CCREVERSECAP : VOIDS — cancels an authorization or capture.
    #                              A void is not a refund: it releases the hold,
    #                              so it reduces `authorized` rather than
    #                              inflating `refunded`. Verified on live T1,
    #                              where a voided auth nets to 0 with nothing
    #                              outstanding.
    is_auth = lambda l: re.search(r"AUTHORIZE|AUTHCAP", l.action or "", re.I)
    # CCAUTHCAP authorizes AND captures in one leg, so it counts as both —
    # otherwise sale() reports captured=0 with the full amount outstanding,
    # the opposite of what happened. Verified on the live T1 gateway.
    is_capture = lambda l: re.search(r"CAPTURE|AUTHCAP", l.action or "", re.I) and not re.search(r"REVERSECAP", l.action or "", re.I)
    is_void = lambda l: re.search(r"REVERSE", l.action or "", re.I)
    is_refund = lambda l: re.search(r"CREDIT", l.action or "", re.I)
    approved = lambda l: l.status is TransactionStatus.APPROVED

    authorized_gross = _sum(amounts(lambda l: is_auth(l) and approved(l)), currency)
    captured = _sum(amounts(lambda l: is_capture(l) and approved(l)), currency)
    # Credit and void legs arrive negative; report magnitudes.
    voided = _sum([abs(a) for a in amounts(lambda l: is_void(l) and approved(l))], currency)
    refunded = _sum([abs(a) for a in amounts(lambda l: is_refund(l) and approved(l))], currency)

    authorized = Money.of(authorized_gross.amount - voided.amount, currency)
    net = Money.of(captured.amount - refunded.amount, currency)
    outstanding = Money.of(authorized.amount - captured.amount, currency)

    # CCSTATUS's tabular payload carries no top-level PO_ID — it lives on each
    # leg. Fall back to the legs so the aggregate is keyed correctly.
    po_id = r.get("PO_ID") or next((l.order_ref.po_id for l in legs if l.order_ref), None)
    if not po_id:
        raise TransportError("CCSTATUS response carried no PO_ID on any leg")
    xtl = r.get("XTL_ORDER_ID") or next((l.xtl_order_ref.value for l in legs if l.xtl_order_ref), None)

    return OrderStatus(
        ref=Refs.order(po_id),
        xtl_ref=Refs.xtl_order(xtl) if xtl else None,
        transactions=legs,
        authorized=authorized, captured=captured, refunded=refunded,
        net=net, outstanding=outstanding,
        settled=bool(legs) and all((not is_auth(l)) or l.settled for l in legs),
        raw=dict(r),
    )
