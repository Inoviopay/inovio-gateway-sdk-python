# Inovio Gateway SDK — Python

Port of the Node/TS reference (**W3** of the internal SDK plan). Structurally
identical to the other SDKs; only ergonomics differ.

> **Status: alpha, local only.** Not published to PyPI.

## Install / test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests    # 36 tests
python3 scripts/generate_enums.py                        # regenerate enums
```

Python **3.8+**, standard library only — no third-party dependencies.
Per decision **D2**, this is a **sync-only** client; async is deferred until a
partner asks for it.

## Quick start

```python
from inovio_gateway import Credentials, InovioClient, Money, PaymentMethods, Refs
from inovio_gateway.model import Idempotency, LineItem
from inovio_gateway.request import TransactionRequest

client = InovioClient(Credentials(user, password, site_id="123"), environment="SANDBOX")

result = client.sale(TransactionRequest(
    payment_method=PaymentMethods.card("4111111111111111", "122030", "123"),
    line_items=[LineItem("SKU-1", 1, Money.of("10.00", "USD"))],
    idempotency=Idempotency(xtl_order_id="ORDER-555"),   # retry-safe by default
))

if result.status is TransactionStatus.APPROVED:
    ...
elif result.status is TransactionStatus.PENDING:
    result.next_action     # 3DS challenge, redirect, voucher
```

## Five things that will surprise you

Identical semantics to the Node reference — see the Node reference SDK's README for the full rationale:

1. **A decline is not an exception.** `sale()` returns `status=DECLINED`.
   Exceptions mean you never got a payment answer.
2. **No `approved`/`declined` booleans.** Only `status` — so `PENDING` cannot be
   silently treated as failure.
3. **`settled` is almost always `False` at response time** (batch flips it later).
   `conversion` appears only on real FX.
4. **`status()` is the reconciliation primitive**, not just timeout recovery —
   captures and refunds are separate legs sharing a `PO_ID`.
5. **`Money` refuses floats.** `Money.of(1.25, "USD")` raises; pass `"1.25"` or
   `Decimal("1.25")`.

## Python-specific notes

- Amounts are `decimal.Decimal` internally; `Money.of` accepts `Decimal`, `str`
  or `int` and rejects `float`.
- The timeout exception is **`InovioTimeoutError`**, deliberately not named
  `TimeoutError` — partners routinely catch the builtin, and shadowing it would
  hide the unknown-state case that needs `status()` recovery.
- `py.typed` ships, so type checkers see the annotations.

## Enums are generated

`src/inovio_gateway/enums/generated.py` comes from `spec/spec-enums.json`
(decision **D1**). Do not edit it. The `retryable`/`terminal`/`stop_recurring`
and AVS/CVV classifications are **derived, not from the spec** — see
[`spec/README.md`](spec/README.md).

## Vendored spec artifacts

This repo **stands alone**: `spec/spec-enums.json` and
`spec/conformance-fixtures.json` are committed copies, so a fresh clone builds,
tests and regenerates with no sibling checkout, submodule or network fetch.

They are not the editable source — they are produced upstream in the internal
`inoviov2` workspace (`api-sdk/spec/`), where the extraction pipeline and its
validator live. To pull an upstream change in:

```bash
./scripts/sync-spec.sh /path/to/inoviov2/api-sdk/spec
```

Then regenerate the enums, run the suite, and commit the spec change together
with the generated code it produces.

**This is a coordinated change.** The other Inovio SDK repos vendor the same two
files; if they are not synced in step, the SDKs silently stop agreeing — which
is exactly what the shared conformance corpus exists to prevent.

## Conformance

`tests/test_conformance.py` runs the shared corpus in
`spec/conformance-fixtures.json` — the same 18 fixtures every language SDK
must pass identically.
