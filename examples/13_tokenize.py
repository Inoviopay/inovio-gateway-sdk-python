"""tokenize() — token_service.cfm

Exchanges a PAN for a single-use TOKEN_GUID that replaces PMT_NUMB on a later
transaction. A new token is required per transaction.

Needs a SITE KEY: a per-site HMAC secret from Inovio support, NOT your gateway
password. Without it the service answers error 121.

⚠️ This is a SERVER-SIDE call — the PAN passes through your infrastructure, so
you stay in PCI scope. The low-scope path is browser Hosted Fields.
"""
from inovio_gateway import PaymentMethods
from _harness import client, demo, request, show, token_client

# Tokenize on the site that holds the HMAC key...
t = token_client().tokenize(PaymentMethods.card(demo.pan, demo.expiry, demo.cvv))

show("token", t.token.guid)
show("token req id", t.token_req_id or "-")
# BIN metadata is best-effort — blank when the BIN is not in the lookup table.
bits = [b for b in (t.card.brand, t.card.type, t.card.bank) if b]
show("card", " / ".join(bits) or "(BIN not found)")

# The token replaces the PAN ONLY: expiry (and CVV) still travel with it, which
# tokenize() carries forward for you.
sale = client().sale(request(tag="TOK", payment_method=t.token))
show("sale with token", f"{sale.status.value} order={sale.order_ref.po_id if sale.order_ref else '-'}")
