"""capture() — CCCAPTURE

Takes funds against a prior authorize(). Pass an amount to capture less than
was authorized; omit it to capture the full amount.

Captures are separate transactions sharing the order, so an order may have
several. Use status() for the net position.
"""
from inovio_gateway import Money
from _harness import client, request, show

c = client()

auth = c.authorize(request(tag="CAP"))
show("authorized", f"{auth.status.value} order={auth.order_ref.po_id if auth.order_ref else '-'}")

capture = c.capture(auth.order_ref, Money.of("10.00", "USD"))
show("captured", capture.status.value)
show("settled", f"{capture.settled}  (batch flips this later — not a failure)")

# Or capture the full authorized amount:
#   c.capture(auth.order_ref)
