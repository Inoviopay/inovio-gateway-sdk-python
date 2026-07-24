"""capture_line_item() — CCCAPTURE against one line item

For multi-item orders shipped separately: capture each line item as it goes
out, rather than capturing an amount against the whole order.

The gateway requires the PARENT ORDER and an amount alongside the line-item id
(spec §5.5.6) — passing the line-item ref alone is rejected.
"""
from inovio_gateway import Money
from inovio_gateway.model import LineItem
from _harness import client, demo, request, show

c = client()

auth = c.authorize(request(tag="LI", line_items=[
    LineItem(demo.product_id, 1, Money.of("10.00", "USD")),
    LineItem(demo.product_id, 1, Money.of("5.00", "USD")),
]))
show("authorized", f"{auth.status.value} lineItems={len(auth.line_item_refs)}")

if auth.line_item_refs:
    first = auth.line_item_refs[0]
    # order + item + amount — all three are required.
    captured = c.capture_line_item(auth.order_ref, first, Money.of("10.00", "USD"))
    show("captured item", f"{first.po_li_id} -> {captured.status.value}")

    s = c.status(auth.order_ref)
    show("outstanding", f"{s.outstanding.to_wire()}   (the unshipped line item)")
else:
    show("note", "gateway returned no line-item refs for this order")
