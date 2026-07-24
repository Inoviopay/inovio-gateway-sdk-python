"""refund() — CCCREDIT

Returns captured funds to the cardholder. Pass an amount for a partial refund;
omit it to refund the full order.

Refund legs arrive with a NEGATIVE amount. status() reports `refunded` as a
positive magnitude, so you rarely have to think about the sign.
"""
from inovio_gateway import Money
from _harness import client, seed_order, show

c = client()

# You can only refund what was captured.
order = seed_order(c, "REFUND", capture=True)
show("captured order", order.order_ref.po_id if order.order_ref else "-")

refund = c.refund(order.order_ref, Money.of("10.00", "USD"))
show("status", refund.status.value)
show("amount", f'{refund.amount.to_wire() if refund.amount else "-"}   (negative on the wire)')

# Full refund instead:
#   c.refund(order.order_ref)
