# Canvas example

A complete canvas for a synthetic Tier 3 change, `add-volume-discount`: invoices of a billing service get a discount by quantity. Its spec delta adds `CAP-billing-FR-7` (scenarios S-1 to S-3) and modifies `CAP-billing-FR-2` (scenario S-4); its threat model has `TM-1` and `TM-2`. The names, paths and numbers are invented.

```markdown
# Canvas: add-volume-discount

## Requirements

- CAP-billing-FR-7: an invoice whose total quantity reaches a tier gets that tier's discount: 5 % from 100 units, 10 % from 500 units. Scenarios S-1 (99 units, no discount), S-2 (100 units, 5 %), S-3 (500 units, 10 %).
- CAP-billing-FR-2 (modified): the invoice total is the sum of the lines minus the discount, rounded half-even to cents. Scenario S-4 (a discount of 12.345 rounds to 12.34).

## Entities

- **Invoice** (`src/billing/invoice.py:14`, existing): `lines` (list of Line), `discount` (Decimal, new, 0 or more), `total` (Decimal).
  - Invariant: `total == sum(line amounts) - discount`, rounded half-even to 2 decimals.
  - Invariant: `discount` is never negative and never larger than the sum of the lines.
- **Line** (`src/billing/invoice.py:8`, existing): `sku` (str), `quantity` (int, 1 or more), `unit_price` (Decimal, 0 or more).
- **DiscountTier** (new, `src/billing/discounts.py`): `min_quantity` (int), `rate` (Decimal between 0 and 1). The tiers are constants in code, not configuration.

## Approach

Compute the discount in a pure function, `discount_for(lines)`, that picks the highest tier the total quantity reaches, and call it from `Invoice.close()` before the total is fixed. Rejected: a discount per line (the business rule is per invoice) and tiers in the database (no one edits them today, and it adds a migration).

## Structure

- `src/billing/discounts.py` (new): `DiscountTier`, the tier constants and `discount_for(lines) -> Decimal`. Depends on nothing in the service.
- `src/billing/invoice.py`: `Invoice.discount` and the call to `discount_for` in `close()`. Depends on `discounts.py`.
- `tests/billing/test_discounts.py` (new) and `tests/billing/test_invoice.py`: the tests of the Test Plan.
- No other file changes.

## Operations

1. `Invoice.close()` adds up the quantities of all lines (S-1, S-2, S-3).
2. `discount_for` picks the tier with the highest `min_quantity` that the total quantity reaches; below 100 units it returns 0 (S-1).
3. The discount is `rate * sum(line amounts)`, rounded half-even to cents (S-2, S-3, S-4).
4. If the discount would exceed the sum of the lines (a line with a negative price slipped through), `close()` raises `InvalidInvoice("discount exceeds subtotal")` and the invoice stays open (TM-2).
5. `close()` stores `discount` and `total = subtotal - discount` (S-4).
6. A closed invoice is never recalculated: calling `close()` again raises `InvalidInvoice("already closed")` (TM-1).

## Norms

1. Money is `Decimal`, never `float`; rounding is `ROUND_HALF_EVEN` at the point of storage, as in `src/billing/invoice.py:40`.
2. Domain errors raise `InvalidInvoice` with a short message; no bare `Exception`.
3. Every scenario has the test the Test Plan names, with pytest; amounts in tests are literals, not computed.
4. Logging at INFO records the invoice ID and the tier applied, never the customer's name or address.

## Safeguards

1. Never apply a discount twice to the same invoice (TM-1).
2. Never produce a negative total or a discount larger than the subtotal (TM-2).
3. Never log customer data (Restricted): the invoice ID is the only identifier in logs.
4. Never read tiers from the request: they are constants in `discounts.py`.
```

Why it holds up in review:

- Every scenario appears in an Operation, and every Operation lands in one of the two source files.
- The closing line of Structure lets the verify flag any other file as scope creep.
- The Norms cite the existing code they follow, and each Safeguard names its threat or its data level.
