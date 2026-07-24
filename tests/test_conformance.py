"""Cross-language conformance suite.

Runs the shared fixtures in this repo's spec/conformance-fixtures.json against a
mocked transport. Every SDK (Node, PHP, Python, Java) runs this same corpus and
must produce the same typed result — the mechanism keeping the implementations
honest (PLAN.md §5).
"""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from inovio_gateway import (
    Credentials, InovioClient, InovioTimeoutError, Money, PaymentMethods, Refs,
)
from inovio_gateway.model import Idempotency, LineItem, PartialAuth
from inovio_gateway.request import TransactionRequest
from inovio_gateway.transport import HttpResponse

FIXTURES = json.loads(
    (Path(__file__).resolve().parents[1] / "spec" / "conformance-fixtures.json").read_text()
)["fixtures"]


class MockHttp:
    """Captures outgoing params and replays a canned response."""

    def __init__(self, response, simulate=None):
        self.response = response
        self.simulate = simulate
        self.last_params = {}

    def post(self, url, body, headers, timeout_ms):
        from urllib.parse import parse_qsl

        self.last_params = dict(parse_qsl(body, keep_blank_values=True))
        if self.simulate == "timeout":
            raise TimeoutError("simulated timeout")
        return HttpResponse(200, json.dumps(self.response or {}))


CREDS = Credentials("u", "p", "1")


def _get(obj, path):
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


#: fixture dotted paths use camelCase JS names; map to python attribute names
_ALIAS = {
    "orderRef": "order_ref", "poId": "po_id", "transactionId": "transaction_id",
    "xtlOrderRef": "xtl_order_ref", "serviceClassification": "service_classification",
    "stopRecurring": "stop_recurring", "nextAction": "next_action",
    "procTransId": "proc_trans_id", "redirectUrl": "redirect_url",
    "exchangeRate": "exchange_rate", "last4": "last4",
}


def _norm_path(path: str) -> str:
    return ".".join(_ALIAS.get(p, p) for p in path.split("."))


def _build_request(spec) -> TransactionRequest:
    pm_spec = spec["paymentMethod"]
    kind = pm_spec["kind"]
    if kind == "card":
        pm = PaymentMethods.card(pm_spec["number"], pm_spec["expiry"], pm_spec.get("cvv"))
    elif kind == "token":
        pm = PaymentMethods.token(pm_spec["guid"])
    else:
        pm = PaymentMethods.saved_card(
            pmt_id=pm_spec.get("pmtId"), pmt_id_xtl=pm_spec.get("pmtIdXtl"),
            cust_id=pm_spec.get("custId"),
        )
    req = TransactionRequest(
        payment_method=pm,
        line_items=[
            LineItem(
                product_id=li["productId"], count=li["count"],
                value=Money.of(li["value"]["amount"], li["value"]["currency"]),
            )
            for li in spec["lineItems"]
        ],
    )
    if "idempotency" in spec:
        req.idempotency = Idempotency(
            xtl_order_id=spec["idempotency"]["xtlOrderId"],
            mode=spec["idempotency"].get("mode"),
        )
    if "partialAuth" in spec:
        pa = spec["partialAuth"]
        req.partial_auth = PartialAuth(
            enabled=pa["enabled"],
            minimum_amount=(
                Money.of(pa["minimumAmount"]["amount"], pa["minimumAmount"]["currency"])
                if pa.get("minimumAmount") else None
            ),
        )
    return req


class ConformanceTest(unittest.TestCase):
    pass


def _make_test(fx):
    def test(self):
        op = fx["request"]["operation"]
        exp = fx.get("expect", {})

        if op == "constructMoney":
            with self.assertRaises(TypeError):
                Money.of(fx["request"]["amount"], fx["request"]["currency"])
            return

        http = MockHttp(fx.get("response"), fx.get("simulate"))
        client = InovioClient(
            CREDS, endpoint="https://gateway.invalid/payment/pmt_service.cfm",
            http_client=http, timeout_ms=50,
        )

        result = thrown = None
        try:
            if op == "sale":
                result = client.sale(_build_request(fx["request"]))
            elif op == "authorize":
                result = client.authorize(_build_request(fx["request"]))
            elif op == "status":
                result = client.status(Refs.order(fx["request"]["orderRef"]))
            else:
                self.fail(f"unhandled fixture operation: {op}")
        except Exception as e:  # noqa: BLE001 - fixtures assert on type
            thrown = e

        # --- expected throws ---
        want_throw = exp.get("throws")
        if isinstance(want_throw, str):
            self.assertIsNotNone(thrown, f"expected {want_throw}, got none")
            mapped = {
                "TimeoutError": "InovioTimeoutError",
                "TypeError": "TypeError",
            }.get(want_throw, want_throw)
            self.assertEqual(type(thrown).__name__, mapped, f"wrong error type: {thrown!r}")
            if "error.refField" in exp:
                self.assertEqual(thrown.ref_field, exp["error.refField"])
            if "error.xtlOrderId" in exp:
                self.assertIsInstance(thrown, InovioTimeoutError)
                self.assertEqual(thrown.xtl_order_id, exp["error.xtlOrderId"])
            return
        if want_throw is False and thrown is not None:
            self.fail(f"a decline must NOT raise, but got {type(thrown).__name__}: {thrown}")
        if thrown is not None:
            raise thrown

        for k, v in (fx.get("expectRequestParams") or {}).items():
            self.assertEqual(http.last_params.get(k), v, f"request param {k}")

        for path, want in exp.items():
            if path == "throws":
                continue
            if path == "statusNot":
                self.assertNotEqual(result.status.value, want)
                continue
            if path == "transactions.length":
                self.assertEqual(len(result.transactions), want)
                continue
            got = _get(result, _norm_path(path))
            if want is None:
                self.assertIsNone(got, f"{path}: expected absent, got {got!r}")
                continue
            if hasattr(got, "value") and not isinstance(got, (str, int)):
                got = got.value          # enum
            if isinstance(got, Decimal):
                got = format(got, "f")
            self.assertEqual(got, want, path)

    return test


for _fx in FIXTURES:
    setattr(ConformanceTest, "test_" + _fx["name"].replace("/", "_").replace("-", "_"), _make_test(_fx))


if __name__ == "__main__":
    unittest.main()
