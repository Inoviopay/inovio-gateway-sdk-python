"""status() — CCSTATUS

Two distinct jobs:

 1. RECONCILIATION. Partial captures, refunds and voids are separate
    transactions sharing one order — so the net position is an order-level
    question. One TransactionResult cannot answer "what did this order actually
    settle for". This can.

 2. TIMEOUT RECOVERY. After a timeout the state is unknown; status() resolves
    it. See 14_timeout_recovery.py.
"""
from inovio_gateway import Money
from _harness import client, seed_order, show

c = client()

# Build a multi-leg order: authorize 100, capture 60, refund 10.
order = seed_order(c, "STATUS", amount="100.00")
c.capture(order.order_ref, Money.of("60.00", "USD"))
c.refund(order.order_ref, Money.of("10.00", "USD"))

s = c.status(order.order_ref)

show("legs", len(s.transactions))
show("authorized", s.authorized.to_wire())
show("captured", s.captured.to_wire())
show("refunded", s.refunded.to_wire())
show("net", f"{s.net.to_wire()}   (captured - refunded)")
show("outstanding", f"{s.outstanding.to_wire()}   (authorized - captured)")

print("\n  legs:")
for leg in s.transactions:
    amount = leg.amount.to_wire() if leg.amount else "-"
    print(f"    {leg.action:<14} {leg.status.value:<9} {amount}")

# You can also look an order up by YOUR id:
#   c.status(Refs.xtl_order("ORDER-555"))
