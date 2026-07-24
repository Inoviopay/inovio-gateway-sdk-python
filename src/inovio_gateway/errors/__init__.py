"""Exception hierarchy (object model §3.7).

A DECLINE IS NEVER RAISED (Q1). A declined transaction returns normally as
``TransactionResult(status=DECLINED)`` with the full outcome/AVS/CVV detail.
Exceptions mean "your request never got a payment answer", not "the answer was no".
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class InovioError(Exception):
    def __init__(self, message: str, raw: Optional[Mapping[str, str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.raw: Dict[str, str] = dict(raw) if raw else {}


class AuthenticationError(InovioError):
    """API tier 100-106 — bad credentials, inactive user, bad site/service."""

    def __init__(self, message, code=None, raw=None):
        super().__init__(message, raw)
        self.code = code


class ValidationError(InovioError):
    """Client-side or API 110-120 — missing/invalid field; ``ref_field`` names it."""

    def __init__(self, message, code=None, ref_field=None, raw=None):
        super().__init__(message, raw)
        self.code = code
        self.ref_field = ref_field


class ConfigurationError(InovioError):
    """Currency/product/merchant-account not configured (155, 165, 210, 500...)."""

    def __init__(self, message, code=None, raw=None):
        super().__init__(message, raw)
        self.code = code


class TransportError(InovioError):
    def __init__(self, message, cause: Any = None):
        super().__init__(message)
        self.cause = cause


class InovioTimeoutError(TransportError):
    """The gateway did not answer in time — TRANSACTION STATE IS UNKNOWN.

    Carries the idempotency key so the caller can resolve the true state with
    ``client.status(...)`` instead of blindly retrying and double-charging.
    """

    def __init__(self, message, timeout_ms: int, xtl_order_id: Optional[str] = None):
        super().__init__(message)
        self.timeout_ms = timeout_ms
        self.xtl_order_id = xtl_order_id

    @property
    def recovery_hint(self) -> str:
        if self.xtl_order_id:
            return (
                "Transaction state is UNKNOWN. Resolve it with "
                f'client.status(Refs.xtl_order("{self.xtl_order_id}")) before retrying — '
                "a blind retry may double-charge."
            )
        return (
            "Transaction state is UNKNOWN. No idempotency key was set, so the state "
            "cannot be resolved by key; set idempotency.xtl_order_id on future requests."
        )


#: Named InovioTimeoutError rather than TimeoutError so it never shadows the
#: builtin — partners routinely catch that, and silently capturing socket
#: timeouts under the same name would hide the unknown-state case.


class RateLimitError(InovioError):
    """API 100 — throttled."""
