"""InovioClient — the v1 card-core surface (object model §3.1).

Partners call ``client.sale()``, never ``REQUEST_ACTION=CCAUTHCAP``.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Union

from .enums.generated import (
    API_RESPONSE_CODES, RequestAction, SPEC_API_VERSION, TransactionStatus,
)
from .errors import (
    AuthenticationError, ConfigurationError, RateLimitError, ValidationError,
)
from .model.money import Money
from .model.payment_method import Card, PaymentMethods, Token
from .refs import LineItemRef, OrderRef, XtlOrderId
from .request import OrderUpdate, TransactionRequest, build_transaction_params
from .result import HealthResult, OrderStatus, TransactionResult
from .result.mapper import to_order_status, to_transaction_result
from .tokenize import TokenizeResult, tokenize_card
from .transport import ENDPOINTS, HttpClient, SANDBOX, UrllibHttpClient, send

DEFAULT_TIMEOUT_MS = 120_000


class Credentials:
    __slots__ = ("req_username", "req_password", "site_id", "merch_acct_id")

    def __init__(self, req_username: str, req_password: str, site_id: str,
                 merch_acct_id: Optional[str] = None) -> None:
        if not req_username or not req_password or not site_id:
            raise ValidationError(
                "credentials require req_username, req_password and site_id"
            )
        self.req_username = req_username
        self.req_password = req_password
        self.site_id = site_id
        self.merch_acct_id = merch_acct_id


class InovioClient:
    def __init__(
        self,
        credentials: Credentials,
        environment: str = SANDBOX,
        endpoint: Optional[str] = None,
        token_endpoint: Optional[str] = None,
        api_version: str = SPEC_API_VERSION,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        http_client: Optional[HttpClient] = None,
        site_key: Optional[str] = None,
    ) -> None:
        self._creds = credentials
        self._endpoint = endpoint or ENDPOINTS[environment]
        self._token_endpoint = token_endpoint or re.sub(
            r"pmt_service\.cfm$", "token_service.cfm", self._endpoint
        )
        self._api_version = api_version
        self._timeout_ms = timeout_ms
        self._http = http_client or UrllibHttpClient()
        #: Per-site HMAC secret for the token service (§4.8); tokenize() only.
        self._site_key = site_key

    # ------------------------------------------------------------------

    def _auth_params(self, action: str) -> Dict[str, str]:
        p = {
            "REQ_USERNAME": self._creds.req_username,
            "REQ_PASSWORD": self._creds.req_password,
            "SITE_ID": self._creds.site_id,
            "REQUEST_ACTION": action,
            "REQUEST_API_VERSION": self._api_version,
            "REQUEST_RESPONSE_FORMAT": "JSON",
        }
        if self._creds.merch_acct_id:
            p["MERCH_ACCT_ID"] = self._creds.merch_acct_id
        return p

    def _raise_if_api_error(self, r: Dict[str, str]) -> None:
        """Raise for API-tier failures only.

        A DECLINE IS NOT AN ERROR — it returns normally as
        TransactionResult(status=DECLINED) (Q1).
        """
        code = r.get("API_RESPONSE")
        if code is None or code == "":
            return
        try:
            code_i = int(code)
        except ValueError:
            return
        if code_i == 0:
            return
        info = API_RESPONSE_CODES.get(code_i)
        if info is None:
            return
        msg = info.description + (f" — {info.recommendation}" if info.recommendation else "")
        exc = info.maps_to_exception
        if exc in ("RateLimitException", "RateLimitError"):
            raise RateLimitError(msg, r)
        if exc == "AuthenticationException":
            raise AuthenticationError(msg, code_i, r)
        if exc == "ValidationException":
            raise ValidationError(msg, code=code_i, ref_field=r.get("REF_FIELD"), raw=r)
        if exc == "ConfigurationException":
            raise ConfigurationError(msg, code_i, r)

    def _call(self, action: str, params: Dict[str, str],
              idempotency_key: Optional[str] = None) -> Dict[str, str]:
        merged = {**self._auth_params(action), **params}
        raw = send(self._endpoint, self._http, self._timeout_ms, merged, idempotency_key)
        self._raise_if_api_error(raw)
        return raw

    def _transact(self, action: str, req: TransactionRequest,
                  extra: Optional[Dict[str, str]] = None) -> TransactionResult:
        params = build_transaction_params(req)
        if extra:
            params.update(extra)
        key = req.idempotency.xtl_order_id if req.idempotency else None
        return to_transaction_result(self._call(action, params, key))

    # ---------------------------- operations --------------------------

    def sale(self, req: TransactionRequest) -> TransactionResult:
        """CCAUTHCAP — authorize and capture in one step."""
        return self._transact(RequestAction.CCAUTHCAP.value, req)

    def authorize(self, req: TransactionRequest) -> TransactionResult:
        """CCAUTHORIZE — authorization only; capture later."""
        return self._transact(RequestAction.CCAUTHORIZE.value, req)

    def capture(self, order: OrderRef, amount: Optional[Money] = None) -> TransactionResult:
        """CCCAPTURE — capture a previous authorization. Partial-capable."""
        p = {"REQUEST_REF_PO_ID": order.po_id}
        if amount:
            p.update({"LI_VALUE_1": amount.to_wire(), "LI_COUNT_1": "1",
                      "REQUEST_CURRENCY": amount.currency})
        return to_transaction_result(self._call(RequestAction.CCCAPTURE.value, p))

    def capture_line_item(self, order: OrderRef, item: LineItemRef,
                          amount: Money) -> TransactionResult:
        """CCCAPTURE against a single line item.

        Per spec §5.5.6 the gateway requires the PARENT ORDER and an amount
alongside the line-item id — sending REQUEST_REF_PO_LI_ID alone is rejected
with API 113 "Invalid Data". LineItemRef does not carry its order, so both
must be passed. Verified against the live T1 gateway.

        :param order: the order the line item belongs to (gateway-required)
        :param item: the line item, from ``result.line_item_refs``
        :param amount: required — the gateway rejects a line-item capture
            without ``LI_VALUE_1``
        """
        if amount is None:
            raise ValidationError(
                "capture_line_item requires an amount — the gateway rejects a "
                "line-item capture without LI_VALUE_1 (spec §5.5.6)",
                ref_field="LI_VALUE_1",
            )
        p = {
            "REQUEST_REF_PO_ID": order.po_id,
            "REQUEST_REF_PO_LI_ID": item.po_li_id,
            "LI_VALUE_1": amount.to_wire(),
            "LI_COUNT_1": "1",
            "REQUEST_CURRENCY": amount.currency,
        }
        return to_transaction_result(self._call(RequestAction.CCCAPTURE.value, p))

    def reverse(self, order: OrderRef) -> TransactionResult:
        """CCREVERSE — void the original authorization."""
        return to_transaction_result(
            self._call(RequestAction.CCREVERSE.value, {"REQUEST_REF_PO_ID": order.po_id})
        )

    def reverse_capture(self, order: OrderRef) -> TransactionResult:
        """CCREVERSECAP — void a CCCAPTURE (not the original auth)."""
        return to_transaction_result(
            self._call(RequestAction.CCREVERSECAP.value, {"REQUEST_REF_PO_ID": order.po_id})
        )

    def refund(self, order: OrderRef, amount: Optional[Money] = None) -> TransactionResult:
        """CCCREDIT — refund against an existing order. Partial-capable."""
        p = {"REQUEST_REF_PO_ID": order.po_id}
        if amount:
            p.update({"LI_VALUE_1": amount.to_wire(), "LI_COUNT_1": "1",
                      "REQUEST_CURRENCY": amount.currency})
        return to_transaction_result(self._call(RequestAction.CCCREDIT.value, p))

    def force_credit(self, req: TransactionRequest) -> TransactionResult:
        """CCCREDIT + FORCE_CREDIT — a credit with no referenced original."""
        return self._transact(RequestAction.CCCREDIT.value, req, {"FORCE_CREDIT": "1"})

    def status(self, ref: Union[OrderRef, XtlOrderId]) -> OrderStatus:
        """CCSTATUS — the reconciliation primitive AND unknown-state recovery.

        Returns order-level net position derived from every leg sharing the
        PO_ID. For any order with more than one leg this is the only correct
        source of net figures.
        """
        p = (
            {"REQUEST_REF_PO_ID": ref.po_id}
            if isinstance(ref, OrderRef)
            else {"REQUEST_REF_PO_ID_XTL": ref.value}
        )
        raw = self._call(RequestAction.CCSTATUS.value, p)
        legs = [to_transaction_result(l) for l in _extract_legs(raw)]
        return to_order_status(raw, legs or [to_transaction_result(raw)])

    def update_order(self, order: OrderRef, update: OrderUpdate) -> TransactionResult:
        """CCTRANSUPDATE — attach receipts to an existing order (Appendix G/J)."""
        p = {"REQUEST_REF_PO_ID": order.po_id}
        if update.receipt:
            p["RECEIPT"] = update.receipt
        if update.metadata:
            for k, v in (update.metadata.udf or {}).items():
                p[f"XTL_UDF{str(k).zfill(2)}"] = v
        return to_transaction_result(self._call(RequestAction.CCTRANSUPDATE.value, p))

    def tokenize(self, card: Card, unique_id: Optional[str] = None) -> TokenizeResult:
        """Ephemeral tokenization (spec §4.8) — exchange a PAN for a single-use
        ``TOKEN_GUID`` usable in place of ``PMT_NUMB``.

        Requires ``site_key``, the per-site HMAC secret issued by Inovio
        support. It is NOT the gateway password; without it the token service
        answers error 121.

        NOTE: this is a server-side call — the PAN passes through your
        infrastructure, so you remain in your server's data flow. The low-scope path is the
        browser Hosted Fields client.
        """
        if not self._site_key:
            raise ValidationError(
                "tokenize requires `site_key` on the client — the per-site HMAC "
                "secret from Inovio support (not your gateway password)."
            )
        return tokenize_card(
            card,
            endpoint=self._token_endpoint,
            http_client=self._http,
            timeout_ms=self._timeout_ms,
            site_id=self._creds.site_id,
            site_key=self._site_key,
            api_version=self._api_version,
            unique_id=unique_id,
        )

    def test_auth(self) -> HealthResult:
        return self._to_health(self._call(RequestAction.TESTAUTH.value, {}))

    def test_availability(self) -> HealthResult:
        return self._to_health(self._call(RequestAction.TESTGW.value, {}))

    def _to_health(self, raw: Dict[str, str]) -> HealthResult:
        res = to_transaction_result(raw)
        svc = raw.get("SERVICE_RESPONSE")
        return HealthResult(
            ok=res.status is TransactionStatus.APPROVED or svc in ("100", "101"),
            action=raw.get("REQUEST_ACTION", ""),
            outcome=res.outcome,
            raw=res.raw,
        )


def _extract_legs(raw: Dict[str, str]) -> List[Dict[str, str]]:
    """CCSTATUS does not answer with flat fields like every other action.

    It returns a tabular payload::

        {"COLUMNS": ["REQUEST_ACTION", "TRANS_STATUS_NAME", ...],
         "DATA":    [["CCAUTHORIZE", "APPROVED", ...], ["CCCAPTURE", ...]]}

    One DATA row per leg against the order. Verified against the live T1
    gateway; the shape is not described in the v4.14 response-fields section.
    """
    import json as _json

    tabular = raw.get("__TABULAR__")
    if not tabular:
        return []
    try:
        parsed = _json.loads(tabular)
    except ValueError:
        return []
    columns, rows = parsed.get("COLUMNS"), parsed.get("DATA")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []

    legs: List[Dict[str, str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        leg: Dict[str, str] = {}
        for i, col in enumerate(columns):
            if i >= len(row):
                break
            v = row[i]
            if v is None or v == "":
                continue
            name = str(col).upper()
            # Duplicate column names appear (TRANS_ID twice); first wins.
            leg.setdefault(name, str(v))
        legs.append(leg)
    return legs
