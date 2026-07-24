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
    ) -> None:
        self._creds = credentials
        self._endpoint = endpoint or ENDPOINTS[environment]
        self._token_endpoint = token_endpoint or re.sub(
            r"pmt_service\.cfm$", "token_service.cfm", self._endpoint
        )
        self._api_version = api_version
        self._timeout_ms = timeout_ms
        self._http = http_client or UrllibHttpClient()

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

    def capture_line_item(self, item: LineItemRef,
                          amount: Optional[Money] = None) -> TransactionResult:
        p = {"REQUEST_REF_PO_LI_ID": item.po_li_id}
        if amount:
            p.update({"LI_VALUE_1": amount.to_wire(), "LI_COUNT_1": "1",
                      "REQUEST_CURRENCY": amount.currency})
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

    def tokenize(self, card: Card) -> Token:
        """Ephemeral tokenization (spec §4.8).

        NOTE: this server-side call still touches the PAN and therefore keeps
        the caller in PCI scope. The lower-scope path is the browser Hosted
        Fields client (W-client), which tokenizes without the PAN reaching your
        server.
        """
        p = {
            **self._auth_params("TOKENIZE"),
            "PMT_NUMB": card.number,
            "PMT_EXPIRY": card.expiry,
        }
        if card.cvv:
            p["PMT_KEY"] = card.cvv
        raw = send(self._token_endpoint, self._http, self._timeout_ms, p)
        self._raise_if_api_error(raw)
        guid = raw.get("TOKEN_GUID") or raw.get("TOKEN") or raw.get("TOKEN_ID")
        if not guid:
            raise ConfigurationError("token service did not return a TOKEN_GUID", None, raw)
        return PaymentMethods.token(guid)

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
    """CCSTATUS returns multiple transactions flattened with indexed keys."""
    indexed: Dict[int, Dict[str, str]] = {}
    for k, v in raw.items():
        m = re.fullmatch(r"(.*?)_(\d+)", k)
        if not m:
            continue
        base, idx = m.group(1), int(m.group(2))
        if not re.match(r"^(TRANS_|REQUEST_ACTION|SERVICE_|PROCESSOR_|API_|AVS_|CVV_|PO_ID)", base):
            continue
        indexed.setdefault(idx, {})[base] = v
    # Order-level fields apply to every leg — notably CURR_CODE_ALPHA, without
    # which a leg has no currency and its amount cannot be constructed.
    inherited = {
        k: raw[k]
        for k in ("PO_ID", "XTL_ORDER_ID", "CURR_CODE_ALPHA", "MERCH_ACCT_ID")
        if k in raw
    }
    return [{**inherited, **fields} for _, fields in sorted(indexed.items())]
