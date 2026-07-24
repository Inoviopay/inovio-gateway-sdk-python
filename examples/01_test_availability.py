"""testAvailability() — TESTGW

Health check for the gateway itself. No credentials are validated and no
transaction is created, so it is safe to poll.
"""
from _harness import client, show

health = client().test_availability()
show("ok", health.ok)
show("service code", f'{health.outcome.service.code} "{health.outcome.service.advice or ""}"')
