"""Shared harness for the runnable examples.

Every example is real, executed code — not a markdown snippet — so it cannot
silently drift from the API. ``python examples/run_all.py`` runs them all.

By default they run against a MOCK transport: no credentials, no network, no
money moves, safe in CI. Set INOVIO_LIVE=1 (plus credentials) to run the same
code against the real gateway.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional
from urllib.parse import parse_qsl

from inovio_gateway import Credentials, InovioClient, Money, PaymentMethods
from inovio_gateway.model import Address, Customer, Idempotency, LineItem
from inovio_gateway.request import TransactionRequest
from inovio_gateway.transport import HttpResponse

LIVE = os.environ.get("INOVIO_LIVE") == "1"

#: Canned responses keyed by REQUEST_ACTION, shaped like the real gateway.
_MOCK = {
    "CCAUTHORIZE": {
        "REQUEST_ACTION": "CCAUTHORIZE", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800001",
        "TRANS_ID": "2000000001", "PO_LI_ID_1": "9000001",
        "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
        "CARD_BRAND_NAME": "Visa", "PMT_L4": "0647",
        "AVS_RESPONSE": "Y", "CVV_RESPONSE": "M",
    },
    "CCAUTHCAP": {
        "REQUEST_ACTION": "CCAUTHCAP", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800002",
        "TRANS_ID": "2000000002", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
        "CARD_BRAND_NAME": "Visa", "PMT_L4": "0647",
    },
    "CCCAPTURE": {
        "REQUEST_ACTION": "CCCAPTURE", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800001",
        "TRANS_ID": "2000000003", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
    },
    "CCREVERSE": {
        "REQUEST_ACTION": "CCREVERSE", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "-10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800001",
        "TRANS_ID": "2000000004", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
    },
    "CCREVERSECAP": {
        "REQUEST_ACTION": "CCREVERSECAP", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "-10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800001",
        "TRANS_ID": "2000000005", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
    },
    "CCCREDIT": {
        "REQUEST_ACTION": "CCCREDIT", "TRANS_STATUS_NAME": "APPROVED",
        "TRANS_VALUE": "-10.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "18800001",
        "TRANS_ID": "2000000006", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
    },
    "CCTRANSUPDATE": {
        "REQUEST_ACTION": "CCTRANSUPDATE", "TRANS_STATUS_NAME": "APPROVED",
        "PO_ID": "18800001", "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
    },
    "TESTAUTH": {
        "REQUEST_ACTION": "TESTAUTH", "API_RESPONSE": "0",
        "SERVICE_RESPONSE": "100", "SERVICE_ADVICE": "User Authorized",
    },
    "TESTGW": {
        "REQUEST_ACTION": "TESTGW", "API_RESPONSE": "0",
        "SERVICE_RESPONSE": "101", "SERVICE_ADVICE": "Service Available",
    },
}

#: CCSTATUS answers with a COLUMNS/DATA table, not flat fields.
_MOCK_STATUS = {
    "COLUMNS": ["REQUEST_ACTION", "TRANS_STATUS_NAME", "TRANS_VALUE", "TRANS_ID", "PO_ID", "CURR_CODE_ALPHA"],
    "DATA": [
        ["CCAUTHORIZE", "APPROVED", 100.0, "T-1", "18800001", "USD"],
        ["CCCAPTURE", "APPROVED", 60.0, "T-2", "18800001", "USD"],
        ["CCCREDIT", "APPROVED", -10.0, "T-3", "18800001", "USD"],
    ],
}

_MOCK_TOKEN = {
    "TOKEN_GUID": "F76E1864D6E018BA5D98080167CDF86AD432FEBD",
    "TOKEN_IP": "10.13.100.134", "TOKEN_REQID": "4283012",
    "CARD_BRAND_NAME": "Visa", "CARD_TYPE": "VISA TRADITIONAL",
    "CARD_BANK": "CHASE BANK USA, NATIONAL ASSOCIATION",
    "CARD_COUNTRY": "USA", "CARD_ACCOUNT_FUND_SOURCE": "Credit",
    "CARD_CLASS": "CONSUMER",
}


class MockHttp:
    def post(self, url, body, headers, timeout_ms):
        p = dict(parse_qsl(body, keep_blank_values=True))
        if "token_service" in url:
            return HttpResponse(200, json.dumps(_MOCK_TOKEN))
        if p.get("REQUEST_ACTION") == "CCSTATUS":
            return HttpResponse(200, json.dumps(_MOCK_STATUS))
        r = _MOCK.get(p.get("REQUEST_ACTION"))
        if r is None:
            raise RuntimeError(f"no mock response for {p.get('REQUEST_ACTION')}")
        return HttpResponse(200, json.dumps(r))


def client(site_id: Optional[str] = None, http_client=None, timeout_ms: int = 60000) -> InovioClient:
    if LIVE:
        creds = Credentials(
            os.environ["INOVIO_USER"], os.environ["INOVIO_PASS"],
            site_id or os.environ["INOVIO_SITE_ID"],
            os.environ.get("INOVIO_MERCH_ACCT_ID"),
        )
    else:
        creds = Credentials("demo@example.invalid", "demo", site_id or "100103")
    return InovioClient(
        creds,
        endpoint=os.environ.get("INOVIO_ENDPOINT", "https://t1api.inoviopay.com/payment/pmt_service.cfm"),
        http_client=http_client if http_client is not None else (None if LIVE else MockHttp()),
        site_key=os.environ.get("INOVIO_SITE_KEY", "demo-site-key"),
        timeout_ms=timeout_ms,
    )


def token_client() -> InovioClient:
    """The token service authenticates per SITE with an HMAC key, independent of
    the gateway's username/password. Normally the same site — but on a shared
    test rig they can differ."""
    return client(site_id=os.environ.get("INOVIO_TOKEN_SITE_ID"))


class demo:
    pan = os.environ.get("INOVIO_TEST_PAN", "4622943123100647")
    expiry = os.environ.get("INOVIO_TEST_EXPIRY", "122026")
    cvv = os.environ.get("INOVIO_TEST_CVV", "242")
    product_id = os.environ.get("INOVIO_TEST_PRODUCT_ID", "111205")

    @staticmethod
    def customer() -> Customer:
        # The processor rejects a missing IP with 'remote_ip is missing'.
        return Customer(first_name="Ada", last_name="Lovelace",
                        email="ada@example.invalid", ip="203.0.113.10")

    @staticmethod
    def billing() -> Address:
        # Country is processor-required despite not being marked so in the spec.
        return Address(line1="123 Main St", city="Austin", state="TX",
                       zip="78701", country="US")

    @staticmethod
    def order_id(tag: str) -> str:
        return f"EXAMPLE-{tag}-{int(time.time() * 1000)}"


def request(amount: str = "10.00", tag: str = "EX", payment_method=None,
            line_items=None) -> TransactionRequest:
    r = TransactionRequest(
        payment_method=payment_method
        or PaymentMethods.card(demo.pan, demo.expiry, demo.cvv),
        line_items=line_items
        or [LineItem(demo.product_id, 1, Money.of(amount, "USD"))],
    )
    r.customer = demo.customer()
    r.billing_address = demo.billing()
    r.idempotency = Idempotency(xtl_order_id=demo.order_id(tag))
    return r


def seed_order(c: InovioClient, tag: str, capture: bool = False, amount: str = "10.00"):
    """Create a real order to operate on.

    Follow-up operations need an order that actually exists, so examples build
    their own rather than hardcoding an id that resolves only against a mock.
    """
    auth = c.authorize(request(amount=amount, tag=tag))
    if capture and auth.order_ref:
        c.capture(auth.order_ref, Money.of(amount, "USD"))
    return auth


def show(label: str, value) -> None:
    print(f"  {label:<22} {value}")
