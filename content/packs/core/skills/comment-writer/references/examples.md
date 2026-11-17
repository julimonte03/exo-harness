# Examples, before and after

Synthetic examples for each kind of text `comment-writer` drafts. Names, IDs and paths are placeholders.

## Code comments

**Repeats the code.** Before:

```python
# increment the counter
retries += 1
```

After: delete the comment. The line says it.

**Explains why.** Before:

```python
time.sleep(2)
```

After:

```python
# The carrier's API rejects a second label request within two seconds of the first
# (their rate limit, docs/integrations/carrier.md). Waiting is cheaper than handling the 429.
time.sleep(2)
```

**TODO with a condition.** Before:

```typescript
// TODO fix this later
```

After, in a project with a ticket pattern and an ID the person confirmed:

```typescript
// TODO(PROJ-482): remove the v1 fallback once every client sends the API-Version header.
```

After, in a project without tickets:

```typescript
// TODO: remove the v1 fallback once every client sends the API-Version header
// (the access log shows none without it for 30 days).
```

**Docstring with the contract.** Before:

```python
def refund(order, amount):
    """Refund function."""
```

After (in a project that uses the Google style):

```python
def refund(order, amount):
    """Refund part or all of a paid order to its original payment method.

    Args:
        order: A paid order.
        amount: The amount to refund, in the order's currency; at most the amount not yet refunded.

    Returns:
        The refund, in state "pending" until the payment provider confirms it.

    Raises:
        RefundLimitExceeded: If the amount is more than what is left to refund.
    """
```

## Review comments

**Blocking issue.** Before:

> This will break.

After:

> **issue (blocking):** `src/orders/cancel.py:57` releases the stock before the payment is voided. If the void
> fails (the provider times out, which the logs show about once a day), the order stays charged and the stock
> is sold again. Could we void first and release the stock only after the void succeeds?

**Suggestion with code.** After:

> **suggestion (non-blocking):** the three checks in `validate_coupon` could read as one guard clause each,
> which makes the expired case easier to spot:
>
> ```suggestion
> if coupon is None:
>     raise CouponNotFound(code)
> if coupon.expires_at < now:
>     raise CouponExpired(code)
> ```

**Question instead of an assumption.** Before:

> You forgot the null check.

After:

> **question:** can `customer.address` be empty here? Guest checkouts (`src/checkout/guest.py:30`) create
> customers without one. If it can, the label request at line 64 will fail.

**Nitpicks, grouped.** After, as one comment:

> **nitpick (non-blocking):** a few small things, none blocking: `tmp` at line 12 could be `pending_refunds`;
> the log message at line 40 says "invoice" but this is a refund; line 71 has a leftover print.

**Praise.** After:

> **praise:** the table-driven tests in `tests/test_rounding.py` cover every currency's minor units. That is
> exactly where the last two bugs came from.

**Summary for a long review.** After:

> Thanks, the structure is easy to follow. Two blocking points, the rest are suggestions:
> 1. Stock released before the void (`cancel.py:57`).
> 2. No test for the partial refund path (S-3 in the spec).
> Everything else is optional; happy to pair on the first one.

## Replies to review feedback

**Agree and done.** "Good catch, thanks. Fixed in `a1b2c3d`: the void runs first now, and `test_cancel_when_void_fails` covers it."

**Disagree with a reason.** "I would keep the broad retry here: the client library raises three unrelated exception types for timeouts (`src/clients/carrier.py:12`). Narrowing it is worth doing, but in its own change: shall I open an item for it?"

**Stuck thread.** "We have gone back and forth twice on the cache key. Could we take five minutes on a call, or let the code owner of `src/cache/` decide? Either is fine with me."

## Issue replies

Before:

> Can't reproduce.

After:

> Thanks for the report. I could not reproduce it on the current main branch with Firefox and Chrome. To dig
> further, could you add: the app version (Settings, About), the exact steps from the home page, and what you
> expected to see versus what you saw? Please leave out any personal or account details. I will look again
> on Thursday.

## Team messages

**A question.** Before:

> hey, anyone around? quick question

After:

> **Question on refunds rounding:** for JPY, should partial refunds round down or to the nearest yen? The spec
> says "nearest" but the provider rounds down (`docs/integrations/payments.md`). I need an answer by Wednesday
> to finish PROJ-512; a link to the policy is enough.

**Status update.** After:

> **Coupons, status:** done: coupon rules and storage, merged. Next: the checkout endpoint, PR expected
> Thursday. Blocked: the staging coupon data; the platform team has the request (PLAT-77).

**Hand-off.** After:

> **Hand-off: carrier label retries** (I am out from tomorrow until Monday)
> - State: branch `fix/PROJ-530-label-retries`, tests green, PR open, one review done.
> - Open: the reviewer asked for a metric on retries; half done in `src/carrier/metrics.py`.
> - Risk: the carrier sandbox is flaky in the afternoon; rerun the integration test before assuming a bug.
> - Ask: the delivery team's lead for decisions on the retry limit.

**Announcement.** After:

> **From Monday 10 March, the test command changes** to `make test` (it now runs the database container for
> you). What to do: pull main and run `make test` once to build the container. The old `pytest` call still
> works until the end of March. Questions in this thread.
