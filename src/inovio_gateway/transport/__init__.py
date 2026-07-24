"""Transport — form-encoded POST to pmt_service.cfm, response normalization.

Wire quirks are normalized ONCE, here, and never leak to the partner
(object model §2 principle 8):
  - responses are case-insensitive        -> keys upper-cased
  - REQUEST_INITATOR is misspelled in the wire protocol
  - XTL_ORDER_ID / XTL_PO_ID name the same thing
  - PMT_L4 / PMT_LAST4 name the same thing
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Mapping, Optional, Protocol

from ..errors import InovioTimeoutError, TransportError

SANDBOX = "SANDBOX"
PRODUCTION = "PRODUCTION"

#: Spec §2.1. Sandbox host is configurable — confirm before non-local use.
ENDPOINTS: Dict[str, str] = {
    PRODUCTION: "https://api.inoviopay.com/payment/pmt_service.cfm",
    SANDBOX: "https://api-uap.inoviopay.com/payment/pmt_service.cfm",
}

#: Field aliases that mean the same thing on the wire.
_ALIASES = {"XTL_PO_ID": "XTL_ORDER_ID", "PMT_LAST4": "PMT_L4"}


class HttpResponse:
    __slots__ = ("status", "body")

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body


class HttpClient(Protocol):
    """Injectable so hosts can supply their own client (and tests can mock)."""

    def post(
        self, url: str, body: str, headers: Mapping[str, str], timeout_ms: int
    ) -> HttpResponse:  # pragma: no cover - protocol
        ...


class UrllibHttpClient:
    """Default client — stdlib only, no third-party dependency."""

    def post(self, url, body, headers, timeout_ms) -> HttpResponse:
        req = urllib.request.Request(
            url, data=body.encode("utf-8"), headers=dict(headers), method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000.0) as resp:
            return HttpResponse(resp.status, resp.read().decode("utf-8", "replace"))


def form_encode(params: Mapping[str, str]) -> str:
    """Spec §2.2: URL-encoded form body."""
    return urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None and v != ""}
    )


def normalize_response(body: str) -> Dict[str, str]:
    """Normalize a raw gateway response into an upper-cased field map.

    Accepts JSON (what we request) and falls back to form-encoded text.
    """
    out: Dict[str, str] = {}

    def put(key: str, value) -> None:
        if value is None:
            return
        k = str(key).upper().strip()
        v = value if isinstance(value, str) else str(value)
        out[k] = v
        alias = _ALIASES.get(k)
        if alias and alias not in out:
            out[alias] = v

    text = (body or "").strip()
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except ValueError as exc:
            raise TransportError("gateway returned malformed JSON", exc) from exc

        def flatten(obj, prefix: str = "") -> None:
            if obj is None:
                return
            if isinstance(obj, list):
                for i, v in enumerate(obj):
                    flatten(v, f"{prefix}{i + 1}")
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        flatten(v, f"{prefix}{k}_")
                    else:
                        put(f"{prefix}{k}", v)
                return
            put(prefix.rstrip("_"), obj)

        flatten(parsed)
        return out

    for key, value in urllib.parse.parse_qsl(text, keep_blank_values=True):
        put(key, value)
    return out


def send(
    endpoint: str,
    http_client: HttpClient,
    timeout_ms: int,
    params: Mapping[str, str],
    idempotency_key: Optional[str] = None,
) -> Dict[str, str]:
    body = form_encode(params)
    try:
        resp = http_client.post(
            endpoint,
            body,
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout_ms,
        )
    except TimeoutError as exc:      # builtin — raised by socket timeouts
        raise InovioTimeoutError(
            f"gateway did not respond within {timeout_ms}ms — transaction state is UNKNOWN",
            timeout_ms,
            idempotency_key,
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError) or "timed out" in str(exc).lower():
            raise InovioTimeoutError(
                f"gateway did not respond within {timeout_ms}ms — transaction state is UNKNOWN",
                timeout_ms,
                idempotency_key,
            ) from exc
        raise TransportError(f"gateway request failed: {exc}", exc) from exc

    if resp.status < 200 or resp.status >= 300:
        raise TransportError(f"gateway returned HTTP {resp.status}")
    return normalize_response(resp.body)
