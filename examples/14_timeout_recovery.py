"""Timeout recovery — the pattern that prevents double charges.

A timeout does NOT mean the transaction failed. It means the state is UNKNOWN:
the gateway may have approved it and lost the response. Retrying blindly can
charge the customer twice.

Two mechanisms work together:

 1. IDEMPOTENCY. Setting idempotency.xtl_order_id defaults to RETURN_ORIGINAL,
    so a repeat of the same request returns the original result instead of
    creating a second charge.
 2. status(). InovioTimeoutError carries your order id, so you can ask the
    gateway what actually happened.
"""
from inovio_gateway import InovioTimeoutError
from _harness import client, request, show


class AlwaysTimesOut:
    """A transport that always times out, so the example is deterministic."""

    def post(self, url, body, headers, timeout_ms):
        raise TimeoutError("simulated")


req = request(tag="TIMEOUT")
c = client(http_client=AlwaysTimesOut(), timeout_ms=50)

try:
    c.sale(req)
except InovioTimeoutError as e:
    show("caught", type(e).__name__)
    show("order id", e.xtl_order_id or "(none — cannot resolve)")
    show("guidance", e.recovery_hint)

    # Resolve the true state instead of guessing:
    #   actual = client().status(Refs.xtl_order(e.xtl_order_id))
    #   if not actual.transactions: pass  # safe to retry
    show("do NOT", "retry blindly — that risks a double charge")
