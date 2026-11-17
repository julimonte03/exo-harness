# Sync cases

How to classify a divergence between the canvas and the code, with examples, and how to write a canvas edit. The rule is `.exo/shared/spdd-common.md`, section D.

The examples use a synthetic change, `add-volume-discount`: invoices get a discount by total quantity (the canvas of `reasons-canvas-author/references/canvas-example.md`).

## The test question

Take the canvas as it is now and imagine a test written from it. After the change you are about to make:

- **the test would fail** → the behavior changes → logic correction (canvas first, approval, then code);
- **the test would still pass** → only the code changes → refactor (code first, then the canvas);
- **a scenario of the spec would fail, or the change adds an output the spec does not mention** → the requirement changes → spec change (stop; the spec phase first).

## Examples

| Situation | Kind | Why |
|---|---|---|
| The canvas rounds the discount up; the spec's scenario says half-even | logic correction | The canvas contradicts the spec; the spec wins, and the canvas changes first |
| No Operation says what happens to an invoice with no lines | logic correction | A missing case: the behavior of that path is being decided now |
| A Safeguard says "never log customer data", and the log needs the customer's account ID | logic correction | A Safeguard changes, even if only to allow one identifier |
| The error message the canvas fixed reads badly, and the person wants other words | logic correction | The output changes; a test on the message would fail |
| The tier lookup moves from `discount_for` to a helper in the same file | refactor | Same behavior; Structure gains the helper |
| Two Operations swap order and the stored result is the same | refactor | Update Operations so the order matches the code |
| A new module the plan does not name would make the code cleaner | not a sync | A file outside the plan: `needs-input` as skill:sdd-apply says, or a follow-up |
| The person wants the applied tier shown on the invoice, and the spec says nothing about showing it | spec or design change | A new output the user sees, which no requirement covers: stop with `needs-input`; the spec (and the design) gain it first, then the canvas |
| The person wants a third tier at 1000 units | spec change | A requirement's values change: the spec first, then the canvas |
| The canvas counts every line's quantity, and the model allows negative credit lines | conflict | The canvas cannot hold as written and either fix changes the behavior: ask |
| A rounding bug in the tax module | follow-up | Not part of the canvas or the plan |

## A canvas edit

Write each edit the same way, whether you apply it inline or return it from `sdd-implementer`:

```text
Canvas edit (logic correction)
Section: Operations, item 3
Old: "The discount is rate * subtotal, rounded up to cents"
New: "The discount is rate * subtotal, rounded half-even to cents"
Why: S-4 says half-even; the canvas said otherwise. The person confirmed: "half-even, as in the rest of billing".
Gate: back to approval (prompt-spec-review, approval mode).
```

```text
Canvas edit (refactor)
Section: Structure, item 1
Old: "src/billing/discounts.py (new): DiscountTier, the tier constants and discount_for(lines) -> Decimal."
New: "src/billing/discounts.py (new): DiscountTier, the tier constants, _tier_for(quantity) and discount_for(lines) -> Decimal."
Why: the tier lookup moved to a helper in the same file; behavior and tests unchanged.
Gate: no new approval.
```

## Keeping the numbering

- Never renumber an approved canvas: gates, decisions and notes cite items by number.
- A new item goes at the end of its section.
- A removed item stays, marked `(removed: <reason>)`.
- A changed item keeps its number.

## After an edit

1. `exo speclint <change-root>` passes.
2. A logic correction: the person sees the section before and after, and skill:prompt-spec-review asks for approval again.
3. The decision goes to the AI Usage Record: `Canvas: logic correction in Operations 3 (...)` or `Canvas: refactor, Structure updated (...)`.
