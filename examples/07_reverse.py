"""reverse() — CCREVERSE

VOIDS an authorization, releasing the hold. This is not a refund: nothing was
captured, so nothing is returned. Use it when an order is cancelled before
shipping.

To void a CAPTURE instead, use reverse_capture().
"""
from _harness import client, request, show

c = client()

auth = c.authorize(request(tag="REV"))
show("authorized", f"{auth.status.value} order={auth.order_ref.po_id if auth.order_ref else '-'}")

voided = c.reverse(auth.order_ref)
show("reversed", voided.status.value)
# Void legs come back with a negative amount.
show("amount", voided.amount.to_wire() if voided.amount else "-")
show("effect", "authorization released — order nets to zero")
