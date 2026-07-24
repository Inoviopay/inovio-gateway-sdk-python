"""update_order() — CCTRANSUPDATE

Attaches data to an order after the fact. The main use is receipts, which
Appendix G/J compliance requires for negative-option and trial billing.
"""
from inovio_gateway.model import Metadata
from inovio_gateway.request import OrderUpdate
from _harness import client, seed_order, show

c = client()

order = seed_order(c, "UPDATE")
show("order", order.order_ref.po_id if order.order_ref else "-")

meta = Metadata()
meta.udf = {"01": "fulfilled-2026-07-23", "02": "warehouse-B"}
update = OrderUpdate(receipt=f"https://merchant.example.invalid/receipts/{order.order_ref.po_id}")
update.metadata = meta

result = c.update_order(order.order_ref, update)
show("status", result.status.value)
show("use", "receipts for MCC 5968 / Visa trial compliance")
