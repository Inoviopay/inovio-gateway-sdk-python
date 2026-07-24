"""Unit tests for behavior not covered by the shared conformance corpus."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal

from inovio_gateway import (
    AVS_CODES, SERVICE_RESPONSE_CODES, SPEC_API_VERSION, Credentials,
    InovioClient, Money, PaymentMethods, Refs, TransactionStatus, ValidationError,
)
from inovio_gateway.model import Idempotency, LineItem, Recurring, RiskOptions, TimeoutVoid
from inovio_gateway.request import TransactionRequest
from inovio_gateway.transport import HttpResponse

CREDS = Credentials("u", "p", "7")

APPROVED = {
    "REQUEST_ACTION": "CCAUTHCAP", "TRANS_STATUS_NAME": "APPROVED",
    "TRANS_VALUE": "1.00", "CURR_CODE_ALPHA": "USD", "PO_ID": "PO-1",
    "API_RESPONSE": "0", "SERVICE_RESPONSE": "100",
}


class Capture:
    def __init__(self, response=None):
        self.response = response or APPROVED
        self.params = {}

    def post(self, url, body, headers, timeout_ms):
        from urllib.parse import parse_qsl
        self.params = dict(parse_qsl(body, keep_blank_values=True))
        return HttpResponse(200, json.dumps(self.response))


def client(http):
    return InovioClient(
        CREDS, endpoint="https://x.invalid/pmt_service.cfm", http_client=http
    )


_DEFAULT_ITEMS = object()


def req(pm=None, items=_DEFAULT_ITEMS, **kw):
    # `items` must distinguish "not supplied" from an explicitly empty list —
    # `items or [...]` would silently substitute the default for [] and hide
    # the empty-line-items validation this suite exists to check.
    if items is _DEFAULT_ITEMS:
        items = [LineItem("A", 1, Money.of("1.00", "USD"))]
    return TransactionRequest(
        payment_method=pm or PaymentMethods.card("4111111111111111", "122030"),
        line_items=items,
        **kw,
    )


class MoneyTest(unittest.TestCase):
    def test_rejects_float_accepts_decimal_string(self):
        with self.assertRaises(TypeError):
            Money.of(1.25, "USD")
        with self.assertRaises(TypeError):
            Money.of("1.2.3", "USD")
        with self.assertRaises(TypeError):
            Money.of("1.25", "DOLLARS")
        m = Money.of("1.25", "usd")
        self.assertEqual(m.amount, Decimal("1.25"))
        self.assertEqual(m.currency, "USD")
        self.assertEqual(m.to_wire(), "1.25")

    def test_accepts_decimal(self):
        self.assertEqual(Money.of(Decimal("2.50"), "EUR").to_wire(), "2.50")

    def test_equality_is_numeric(self):
        self.assertEqual(Money.of("1.50", "USD"), Money.of("1.50", "USD"))
        self.assertNotEqual(Money.of("1.50", "USD"), Money.of("1.50", "EUR"))


class PaymentMethodTest(unittest.TestCase):
    def test_card_validation(self):
        with self.assertRaises(TypeError):
            PaymentMethods.card("41111", "122030")
        with self.assertRaises(TypeError):
            PaymentMethods.card("4111111111111111", "12/30")
        with self.assertRaises(TypeError):
            PaymentMethods.card("4111111111111111", "132030")
        c = PaymentMethods.card("4111 1111 1111 1111", "122030", "123")
        self.assertEqual(c.number, "4111111111111111")

    def test_saved_card_requires_identifier(self):
        with self.assertRaises(TypeError):
            PaymentMethods.saved_card()
        self.assertEqual(PaymentMethods.saved_card(pmt_id="X").pmt_id, "X")


class GeneratedEnumTest(unittest.TestCase):
    def test_spec_values_and_classifiers(self):
        self.assertEqual(SPEC_API_VERSION, "4.14")
        self.assertEqual(len(list(TransactionStatus)), 5)
        self.assertTrue(SERVICE_RESPONSE_CODES[640].retryable)
        self.assertTrue(SERVICE_RESPONSE_CODES[219].stop_recurring)
        self.assertTrue(SERVICE_RESPONSE_CODES[100].approval)
        # AVS 'A' is partial (street matches, postal does not) — not positive
        self.assertEqual(AVS_CODES["A"].classification, "partial")
        self.assertEqual(AVS_CODES["N"].classification, "negative")
        self.assertEqual(AVS_CODES["X"].classification, "positive")


class RequestBuildTest(unittest.TestCase):
    def test_line_items_are_one_indexed_with_auth_params(self):
        http = Capture()
        client(http).sale(req(items=[
            LineItem("A", 1, Money.of("1.00", "USD")),
            LineItem("B", 2, Money.of("2.50", "USD")),
        ]))
        self.assertEqual(http.params["LI_PROD_ID_1"], "A")
        self.assertEqual(http.params["LI_VALUE_1"], "1.00")
        self.assertEqual(http.params["LI_COUNT_2"], "2")
        self.assertEqual(http.params["REQUEST_CURRENCY"], "USD")
        self.assertEqual(http.params["REQUEST_ACTION"], "CCAUTHCAP")
        self.assertEqual(http.params["SITE_ID"], "7")
        self.assertEqual(http.params["REQUEST_API_VERSION"], "4.14")

    def test_wire_misspelling_hidden(self):
        http = Capture()
        client(http).sale(req(recurring=Recurring(initiator="MIT", rebill="REBILL")))
        self.assertEqual(http.params["REQUEST_INITATOR"], "MIT")  # sic
        self.assertEqual(http.params["REQUEST_REBILL"], "1")

    def test_mixed_currency_rejected(self):
        with self.assertRaises(ValidationError):
            client(Capture()).sale(req(items=[
                LineItem("A", 1, Money.of("1.00", "USD")),
                LineItem("B", 1, Money.of("1.00", "EUR")),
            ]))

    def test_empty_items_and_count_cap(self):
        with self.assertRaises(ValidationError):
            client(Capture()).sale(req(items=[]))
        with self.assertRaises(ValidationError):
            client(Capture()).sale(req(items=[LineItem("A", 11, Money.of("1.00", "USD"))]))

    def test_timeout_void_range(self):
        with self.assertRaises(ValidationError):
            client(Capture()).sale(req(risk=RiskOptions(timeout_void=TimeoutVoid(5))))

    def test_token_sends_guid_not_pan(self):
        http = Capture()
        client(http).sale(req(pm=PaymentMethods.token("TG-123")))
        self.assertEqual(http.params["TOKEN_GUID"], "TG-123")
        self.assertNotIn("PMT_NUMB", http.params)

    def test_idempotency_defaults_retry_safe(self):
        http = Capture()
        client(http).sale(req(idempotency=Idempotency(xtl_order_id="ORD-1")))
        self.assertEqual(http.params["UNIQUE_XTL_ORDER_ID"], "2")


class FollowUpTest(unittest.TestCase):
    def test_follow_ups_send_order_reference(self):
        order = Refs.order("PO-42")
        for method, action in [
            ("capture", "CCCAPTURE"), ("refund", "CCCREDIT"),
            ("reverse", "CCREVERSE"), ("reverse_capture", "CCREVERSECAP"),
        ]:
            http = Capture()
            getattr(client(http), method)(order)
            self.assertEqual(http.params["REQUEST_REF_PO_ID"], "PO-42", method)
            self.assertEqual(http.params["REQUEST_ACTION"], action, method)

    def test_partial_capture_carries_amount(self):
        http = Capture()
        client(http).capture(Refs.order("PO-42"), Money.of("5.00", "USD"))
        self.assertEqual(http.params["LI_VALUE_1"], "5.00")


class TransportTest(unittest.TestCase):
    def test_case_insensitive_response(self):
        http = Capture({
            "request_action": "CCAUTHCAP", "trans_status_name": "APPROVED",
            "po_id": "PO-LOWER", "api_response": "0", "service_response": "100",
        })
        r = client(http).sale(req())
        self.assertIs(r.status, TransactionStatus.APPROVED)
        self.assertEqual(r.order_ref.po_id, "PO-LOWER")

    def test_xtl_po_id_aliases(self):
        http = Capture({
            "REQUEST_ACTION": "CCAUTHCAP", "TRANS_STATUS_NAME": "APPROVED",
            "XTL_PO_ID": "ORD-9", "API_RESPONSE": "0",
        })
        self.assertEqual(client(http).sale(req()).xtl_order_ref.value, "ORD-9")

    def test_credentials_validated(self):
        with self.assertRaises(ValidationError):
            Credentials("u", "", "1")


if __name__ == "__main__":
    unittest.main()
