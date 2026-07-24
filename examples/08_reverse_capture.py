"""reverse_capture() — CCREVERSECAP

VOIDS a capture rather than the original authorization. Reach for this when you
captured in error and the batch has not settled yet.

After settlement, refund() is the correct operation instead.
"""
from _harness import client, seed_order, show

c = client()

order = seed_order(c, "REVCAP", capture=True)
show("captured order", order.order_ref.po_id if order.order_ref else "-")

result = c.reverse_capture(order.order_ref)
show("status", result.status.value)
show("amount", result.amount.to_wire() if result.amount else "-")
show("when to use", "capture made in error, before batch settlement")
