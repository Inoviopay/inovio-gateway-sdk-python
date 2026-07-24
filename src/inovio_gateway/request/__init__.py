"""Request objects and the model -> wire projection.

This is where the SDK earns its keep: flat, uppercase, 1-indexed wire params
(LI_VALUE_1, BILL_ADDR_ZIP, REQUEST_INITATOR...) are produced from cohesive
objects so the partner never types a wire field name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..errors import ValidationError
from ..model import (
    Address, Affiliate, BrowserData, Customer, Descriptor, Fees, Idempotency,
    LineItem, Metadata, PartialAuth, Recurring, RiskOptions,
)
from ..model.money import Money
from ..model.payment_method import (
    Card, PaymentMethod, SavedCard, Token, assert_v1_payment_method,
)

_IDEMPOTENCY_WIRE = {"OFF": "0", "DECLINE_DUP": "1", "RETURN_ORIGINAL": "2"}
_AVS_WIRE = {"on": "1", "off": "0", "ignore": "2", "conditional": "3"}
_REBILL_WIRE = {"NONE": "0", "REBILL": "1", "START_SUBSCRIPTION": "2"}
_REBILL_TYPE_WIRE = {"NONE": "0", "TRIAL": "1", "INITIAL": "2", "REBILL": "3"}


@dataclass
class TransactionRequest:
    payment_method: PaymentMethod
    line_items: List[LineItem]
    amount: Optional[Money] = None
    customer: Optional[Customer] = None
    billing_address: Optional[Address] = None
    shipping_address: Optional[Address] = None
    descriptor: Optional[Descriptor] = None
    risk: Optional[RiskOptions] = None
    partial_auth: Optional[PartialAuth] = None
    idempotency: Optional[Idempotency] = None
    recurring: Optional[Recurring] = None
    fees: Optional[Fees] = None
    affiliate: Optional[Affiliate] = None
    metadata: Optional[Metadata] = None
    merch_acct_id: Optional[str] = None
    browser: Optional[BrowserData] = None


SaleRequest = TransactionRequest
AuthorizeRequest = TransactionRequest


@dataclass
class CreditRequest(TransactionRequest):
    """CCCREDIT + FORCE_CREDIT — a credit with no referenced original."""
    force: bool = False


@dataclass
class OrderUpdate:
    """CCTRANSUPDATE payload — receipts attached post-hoc (Appendix G compliance)."""
    receipt: Optional[str] = None
    metadata: Optional[Metadata] = None


def _put(params: Dict[str, str], key: str, value) -> None:
    if value is None or value == "":
        return
    if isinstance(value, bool):
        params[key] = "1" if value else "0"
    else:
        params[key] = str(value)


def _apply_address(params: Dict[str, str], prefix: str, addr: Optional[Address]) -> None:
    if addr is None:
        return
    _put(params, f"{prefix}_ADDR", addr.line1)
    _put(params, f"{prefix}_ADDR2", addr.line2)
    _put(params, f"{prefix}_ADDR_CITY", addr.city)
    _put(params, f"{prefix}_ADDR_STATE", addr.state)
    _put(params, f"{prefix}_ADDR_ZIP", addr.zip)
    _put(params, f"{prefix}_ADDR_COUNTRY", addr.country)
    _put(params, f"{prefix}_ADDR_DISTRICT", addr.district)


def build_transaction_params(req: TransactionRequest) -> Dict[str, str]:
    """Project a request onto the wire parameter map."""
    p: Dict[str, str] = {}
    assert_v1_payment_method(req.payment_method)

    if not req.line_items:
        raise ValidationError("at least one line item is required", ref_field="LI_VALUE_1")

    pm = req.payment_method
    if isinstance(pm, Card):
        _put(p, "PMT_NUMB", pm.number)
        _put(p, "PMT_EXPIRY", pm.expiry)
        _put(p, "PMT_KEY", pm.cvv)
    elif isinstance(pm, Token):
        # The token stands in for the PAN only — the transaction service still
        # requires the expiry (and CVV where the processor asks for it).
        _put(p, "TOKEN_GUID", pm.guid)
        _put(p, "PMT_EXPIRY", pm.expiry)
        _put(p, "PMT_KEY", pm.cvv)
    elif isinstance(pm, SavedCard):
        _put(p, "PMT_ID", pm.pmt_id)
        _put(p, "PMT_ID_XTL", pm.pmt_id_xtl)
        _put(p, "CUST_ID", pm.cust_id)

    currency = req.amount.currency if req.amount else None
    for i, li in enumerate(req.line_items, start=1):
        if li.count > 10:
            raise ValidationError(
                f"line item {i}: count must be <= 10 (spec §4.4)",
                ref_field=f"LI_COUNT_{i}",
            )
        _put(p, f"LI_PROD_ID_{i}", li.product_id)
        _put(p, f"LI_PROD_ID_XTL_{i}", li.xtl_product_id)
        _put(p, f"LI_COUNT_{i}", li.count)
        _put(p, f"LI_VALUE_{i}", li.value.to_wire())
        _put(p, f"LI_TYPE_{i}", li.type)
        if currency is None:
            currency = li.value.currency
        elif li.value.currency != currency:
            raise ValidationError(
                f"line item {i} currency {li.value.currency} does not match {currency} — "
                "a single transaction cannot mix currencies"
            )
    _put(p, "REQUEST_CURRENCY", currency)

    c = req.customer
    if c:
        _put(p, "CUST_FNAME", c.first_name)
        _put(p, "CUST_LNAME", c.last_name)
        _put(p, "CUST_EMAIL", c.email)
        _put(p, "CUST_PHONE", c.phone)
        _put(p, "CUST_LOGIN", c.login)
        _put(p, "CUST_PASSWORD", c.password)
        _put(p, "CUST_BIRTHDAY", c.birthday)
        _put(p, "CUST_DLN", c.dln)
        _put(p, "CUST_DLN_STATE", c.dln_state)
        _put(p, "CUST_SSN_L4", c.ssn_last4)
        _put(p, "CUST_BRCPFCNPJ", c.br_cpf_cnpj)
        _put(p, "XTL_IP", c.ip)
        _put(p, "USER_AGENT_XTL", c.user_agent)

    _apply_address(p, "BILL", req.billing_address)
    _apply_address(p, "SHIP", req.shipping_address)

    if req.descriptor:
        _put(p, "PMT_DESCRIPTOR", req.descriptor.name)
        _put(p, "PMT_DESCRIPTOR_PHONE", req.descriptor.phone)
        _put(p, "PMT_DESCRIPTOR_CITY", req.descriptor.city)

    if req.risk:
        if req.risk.avs:
            _put(p, "CHKAVS", _AVS_WIRE.get(req.risk.avs))
        _put(p, "AVS_MATCH_SET", req.risk.avs_match_set)
        if req.risk.cvv:
            _put(p, "CHKCVV", _AVS_WIRE.get(req.risk.cvv))
        _put(p, "CVV_MATCH_SET", req.risk.cvv_match_set)
        if req.risk.timeout_void:
            s = req.risk.timeout_void.seconds
            if s < 30 or s > 600:
                raise ValidationError(
                    f"risk.timeout_void.seconds must be between 30 and 600, got {s}",
                    ref_field="REQUEST_MAX_WAIT",
                )
            _put(p, "REQUEST_MAX_WAIT", s)

    if req.partial_auth and req.partial_auth.enabled:
        _put(p, "PARTIAL_AUTH", "1")
        if req.partial_auth.minimum_amount:
            _put(p, "PARTIAL_AUTH_MIN", req.partial_auth.minimum_amount.to_wire())

    if req.idempotency:
        _put(p, "XTL_ORDER_ID", req.idempotency.xtl_order_id)
        mode = req.idempotency.mode or "RETURN_ORIGINAL"
        _put(p, "UNIQUE_XTL_ORDER_ID", _IDEMPOTENCY_WIRE[mode])

    if req.recurring:
        r = req.recurring
        # NOTE: the wire field is misspelled "INITATOR". Normalized here so the
        # partner never sees it.
        if r.initiator:
            _put(p, "REQUEST_INITATOR", r.initiator)
        if r.rebill:
            _put(p, "REQUEST_REBILL", _REBILL_WIRE[r.rebill])
        if r.rebill_type:
            _put(p, "TRANS_REBILL_TYPE", _REBILL_TYPE_WIRE[r.rebill_type])
        _put(p, "INSTALLMENT", r.installment)
        _put(p, "CARD_ON_FILE", r.card_on_file)
        _put(p, "MBSHP_ID_XTL", r.membership_xtl_id)
        _put(p, "TRIAL_CONSENT", r.trial_consent)
        _put(p, "RECEIPT", r.receipt)

    if req.fees:
        if req.fees.tax:
            _put(p, "TAX_AMT", req.fees.tax.amount.to_wire())
            _put(p, "TAX_EXEMPT", req.fees.tax.exempt)
        if req.fees.convenience_fee:
            _put(p, "CONVENIENCE_FEE", req.fees.convenience_fee.to_wire())

    if req.affiliate:
        _put(p, "REQUEST_AFF_ID", req.affiliate.aff_id)
        _put(p, "REQUEST_AFF_ID_SUB", req.affiliate.sub_aff_id)

    if req.metadata:
        _put(p, "TPPE_ID", req.metadata.tppe_id)
        _put(p, "PROC_UDF01", req.metadata.proc_udf1)
        _put(p, "PROC_UDF02", req.metadata.proc_udf2)
        for k, v in (req.metadata.udf or {}).items():
            _put(p, f"XTL_UDF{str(k).zfill(2)}", v)

    if req.browser:
        _put(p, "P3DS_BROWSER_LANGUAGE", req.browser.language)
        _put(p, "USER_AGENT_XTL", req.browser.user_agent)
        _put(p, "P3DS_BROWSER_HEADER", req.browser.header)

    _put(p, "MERCH_ACCT_ID", req.merch_acct_id)
    return p
