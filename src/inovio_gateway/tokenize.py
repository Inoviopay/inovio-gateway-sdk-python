"""Ephemeral tokenization (spec §4.8).

This is NOT the transaction service: a different endpoint (``token_service.cfm``),
a different request shape, and HMAC header auth instead of username/password.
Exchanging a PAN here yields a single-use ``TOKEN_GUID`` that replaces
``PMT_NUMB`` on a later sale/authorize.

Signature construction::

    X-SIGNATURE = hex(HMAC_SHA256(site_key, timestamp + unique_id + site_id))
    X-TIMESTAMP = YYYYMMDDHHMMSS, UTC, valid for 300 seconds

.. warning::
   The v4.14 PDF is self-contradictory here. Its §4.8.1.2 note claims the
   message also includes ``card_pan``, and the document's worked example agrees.
   The gateway does NOT do this — ``CRPT.TOKEN_PKG`` validates
   ``hmac_sha256(utc || unique_id || site_id, site_key)``. Signing with the PAN
   included yields error 121 "Get CCtoken GUID signature match fail". Verified
   against the live T1 token service; this follows the gateway, not the document.

The site key is provisioned per merchant site and is NOT the gateway password —
obtain it from Inovio support.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from .errors import ConfigurationError, ValidationError
from .model.payment_method import Card, PaymentMethods, Token
from .transport import HttpClient, send


@dataclass(frozen=True)
class TokenizedCardInfo:
    """BIN metadata the token service returns alongside the token."""

    brand: Optional[str] = None
    type: Optional[str] = None
    bank: Optional[str] = None
    country: Optional[str] = None
    account_fund_source: Optional[str] = None
    card_class: Optional[str] = None


@dataclass(frozen=True)
class TokenizeResult:
    token: Token
    card: TokenizedCardInfo
    raw: Dict[str, str] = field(default_factory=dict)
    #: Gateway-side IP recorded for the token request.
    token_ip: Optional[str] = None
    #: Token service request id — quote this to support.
    token_req_id: Optional[str] = None


def token_timestamp(now: Optional[datetime] = None) -> str:
    """UTC timestamp in the token service's YYYYMMDDHHMMSS format."""
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")


def sign_token_request(site_key: str, timestamp: str, unique_id: str, site_id: str) -> str:
    """Build the request signature.

    Exposed so a caller can verify their site key without a live call.
    """
    msg = f"{timestamp}{unique_id}{site_id}".encode()
    return hmac.new(site_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_token_response(
    site_key: str, timestamp: str, token_req_id: str, raw_body: str, signature: str
) -> bool:
    """Verify the response signature the token service returns.

    Per ``CRPT.TOKEN_PKG`` the gateway signs
    ``timestamp + token_req_id + raw_response_body`` with the same site key.
    """
    msg = f"{timestamp}{token_req_id}{raw_body.strip()}".encode()
    expected = hmac.new(site_key.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), (signature or "").lower())


def _blank_to_none(v: Optional[str]) -> Optional[str]:
    return None if v is None or v.strip() == "" else v


def tokenize_card(
    card: Card,
    *,
    endpoint: str,
    http_client: HttpClient,
    timeout_ms: int,
    site_id: str,
    site_key: str,
    api_version: str,
    unique_id: Optional[str] = None,
) -> TokenizeResult:
    if not site_key:
        raise ValidationError(
            "tokenize requires a site_key — the per-site HMAC secret from Inovio "
            "support. It is NOT your gateway password."
        )
    uid = unique_id or secrets.token_hex(16)
    if len(uid) > 32:
        raise ValidationError("tokenize: unique_id must be at most 32 characters")
    ts = token_timestamp()

    raw = send(
        endpoint,
        http_client,
        timeout_ms,
        {
            # The token service takes CARD_PAN — not PMT_NUMB, no expiry/CVV.
            "CARD_PAN": card.number,
            "SITE_ID": site_id,
            "UNIQUE_ID": uid,
            "REQUEST_API_VERSION": api_version,
            "REQUEST_RESPONSE_FORMAT": "JSON",
        },
        extra_headers={
            "X-SIGNATURE": sign_token_request(site_key, ts, uid, site_id),
            "X-TIMESTAMP": ts,
        },
    )

    guid = raw.get("TOKEN_GUID")
    if not guid:
        message = raw.get("ERROR_MESSAGE") or "token service did not return a TOKEN_GUID"
        if raw.get("ERROR_CODE") == "121":
            message += (
                " (signature mismatch — check the site key, and that the signed "
                "message is timestamp+unique_id+site_id with NO card_pan)"
            )
        raise ConfigurationError(message, None, raw)

    return TokenizeResult(
        # Carry expiry/cvv forward: the token replaces the PAN, but the
        # transaction service still needs them (§4.8.2).
        token=PaymentMethods.token(guid, card.expiry, card.cvv),
        # BIN metadata is best-effort: the token service returns these keys
        # with EMPTY values when the BIN is not in its lookup table (observed
        # on live T1 for some test PANs). Normalize blanks to None so callers
        # can check presence rather than compare against "".
        card=TokenizedCardInfo(
            brand=_blank_to_none(raw.get("CARD_BRAND_NAME")),
            type=_blank_to_none(raw.get("CARD_TYPE")),
            bank=_blank_to_none(raw.get("CARD_BANK")),
            country=_blank_to_none(raw.get("CARD_COUNTRY")),
            account_fund_source=_blank_to_none(raw.get("CARD_ACCOUNT_FUND_SOURCE")),
            card_class=_blank_to_none(raw.get("CARD_CLASS")),
        ),
        raw=raw,
        token_ip=raw.get("TOKEN_IP"),
        token_req_id=raw.get("TOKEN_REQID"),
    )
