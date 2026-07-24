# Inovio Gateway SDK — Python

The Inovio payment gateway for Python. Card transactions — authorize, capture,
refund, tokenize — with a typed, synchronous API and no third-party dependencies.

> **Status: alpha.** Not yet published to PyPI.

## Install / test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/generate_enums.py                        # regenerate enums
```

Python **3.8+**, standard library only. This is a **synchronous** client.

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

The behaviours below are worth internalizing before you integrate:

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
  `TimeoutError` — callers routinely catch the builtin, and shadowing it would
  hide the unknown-state case that needs `status()` recovery.
- `py.typed` ships, so type checkers see the annotations.

## Classifier fields are our interpretation, not the spec

Some fields the SDK gives you are **derived by us from the response codes, not
returned by the gateway** — and you will branch real logic on them, so it is
worth knowing which:

- **`service_classification.retryable` / `terminal` / `stop_recurring`** — your
  dunning logic decides whether to re-try a declined charge based on these. We
  set them from the service response code; the gateway does not send them.
- **`avs.classification`** — `positive` / `partial` / `negative` / `neutral`.
  `partial` means some elements matched and some did not (e.g. street matches
  but postal code does not). **Whether a partial AVS result is acceptable is
  your risk decision** — the SDK reports the classification and deliberately
  does not accept or reject for you.

If you need the raw gateway value instead of our label, every result carries a
`raw` dict with the verbatim response fields.

## Tokenization (spec §4.8)

`tokenize()` exchanges a PAN for a single-use `TOKEN_GUID` that replaces
`PMT_NUMB` on a later sale or authorize. It hits a **different endpoint**
(`token_service.cfm`) with **different auth** — HMAC headers, not
username/password.

You need a **site key**: a per-site HMAC secret issued by Inovio support. It is
*not* your gateway password. Without it the service answers error 121.

Two things the SDK handles that the spec will mislead you on:

**1. The signed message excludes the PAN.** The v4.14 PDF's §4.8.1.2 note says
the HMAC covers `card_pan`, and its worked example agrees — but the gateway
does not. The gateway actually validates:

```
hmac_sha256(timestamp || unique_id || site_id, site_key)
```

Signing with the card number included fails with error 121. This SDK signs
the way the gateway expects.

**2. A token replaces the PAN only.** The transaction still needs the expiry
(and CVV where the processor asks), so `tokenize()` carries them forward onto
the returned token. Sending a bare `TOKEN_GUID` yields API 110 `Required field`
on `REF_FIELD=pmt_expiry`.

BIN metadata (`brand`, `bank`, `country`, ...) is best-effort: the service
returns those keys **empty** when the BIN is not in its lookup table, and the
SDK normalizes blanks to null/undefined so you can test for presence.

⚠️ `tokenize()` runs on your server, so the card number passes through it. To
keep the number in the cardholder's browser instead, use the browser Hosted
Fields client (not yet available).
