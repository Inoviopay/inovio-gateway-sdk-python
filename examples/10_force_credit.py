"""force_credit() — CCCREDIT + FORCE_CREDIT

Pushes money to a card with NO original transaction to reference. Use it for
goodwill payments, or to refund an order taken outside the gateway.

Because nothing constrains the amount, merchant accounts must have this enabled
explicitly. If it is NOT enabled the gateway rejects the request at the API tier
with 104 "Invalid service action" — an AuthenticationError, not a decline.
Observed on live T1 with a standard test account.
"""
from inovio_gateway import AuthenticationError, TransactionStatus
from _harness import client, request, show

try:
    result = client().force_credit(request(tag="FORCE"))
    show("status", result.status.value)
    show("amount", result.amount.to_wire() if result.amount else "-")
    if result.status is TransactionStatus.DECLINED:
        show("service code", f'{result.outcome.service.code} "{result.outcome.service.advice or ""}"')
except AuthenticationError as e:
    show("rejected", e.message)
    show("cause", "FORCE_CREDIT is not enabled on this merchant account")
    show("fix", "ask Inovio support to enable it for the MID")
