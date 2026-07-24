"""sale() — CCAUTHCAP

Authorize and capture in one step. The common case for immediate fulfilment.
Use authorize() + capture() instead when you ship later.

A DECLINE IS NOT AN ERROR — it returns normally with status DECLINED.
"""
from inovio_gateway import TransactionStatus
from _harness import client, request, show

result = client().sale(request(tag="SALE"))

show("status", result.status.value)
show("order", result.order_ref.po_id if result.order_ref else "-")
show("amount", f"{result.amount.to_wire()} {result.amount.currency}" if result.amount else "-")
show("card", f'{result.card.brand if result.card else "?"} ****{result.card.last4 if result.card else "?"}')

if result.status is TransactionStatus.APPROVED:
    show("next", "fulfil the order")
elif result.status is TransactionStatus.DECLINED:
    # The service tier carries the decline taxonomy your dunning logic needs.
    retryable = result.service_classification and result.service_classification.retryable
    show("next", "retry later" if retryable else "do not retry")
elif result.status is TransactionStatus.PENDING:
    show("next", f"complete {result.next_action.kind if result.next_action else '?'}")
else:
    show("next", "inspect result.outcome")
