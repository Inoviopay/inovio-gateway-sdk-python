"""authorize() — CCAUTHORIZE

Places a hold without taking funds. Pair with capture() when you ship, or
reverse() to release the hold.

Keep result.order_ref — every follow-up operation consumes it.
"""
from _harness import client, request, show

auth = client().authorize(request(tag="AUTH"))

show("status", auth.status.value)
show("order", auth.order_ref.po_id if auth.order_ref else "-")
show("line items", ", ".join(l.po_li_id for l in auth.line_item_refs) or "-")
show("avs", f"{auth.avs.code} ({auth.avs.classification})" if auth.avs else "-")
show("cvv", f"{auth.cvv.code} ({auth.cvv.classification})" if auth.cvv else "-")

# AVS 'partial' means some elements matched and some did not. Whether that is
# acceptable is YOUR risk policy — the SDK reports, it does not decide.
if auth.avs and auth.avs.classification == "partial":
    show("note", "partial AVS match — apply your risk policy")
