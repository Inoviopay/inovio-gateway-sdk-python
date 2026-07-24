"""testAuth() — TESTAUTH

Verifies your credentials without creating a transaction. Use it to confirm a
new merchant's credentials before going live.

Bad credentials raise AuthenticationError (API tier 101), not a decline.
"""
from inovio_gateway import AuthenticationError
from _harness import client, show

try:
    health = client().test_auth()
    show("ok", health.ok)
    show("service code", f'{health.outcome.service.code} "{health.outcome.service.advice or ""}"')
except AuthenticationError as e:
    show("rejected", e.message)
