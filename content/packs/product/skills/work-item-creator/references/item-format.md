# Work item format

The fields of one work item, how to fill each, and a worked example. The shape is tracker-neutral: `references/tracker-formats.md` maps it onto Jira, Azure Boards, GitHub Issues and a generic CSV.

## Fields

| Field | Required | How to fill it |
|---|---|---|
| Ref | yes | `WI-<n>`, in plan order. Replaced by the tracker's ID once the person brings it back |
| Kind | yes | One of the kinds the team uses. Default: `story` for a unit a user can see, `task` for the rest, `spike` for time-boxed research |
| Title | yes | Imperative, outcome first, up to about 80 characters, unique in the set, no ID |
| Parent | yes | The change's `ticket_key` exactly as confirmed, an epic the person names, or `none` |
| Goal | yes | One sentence: who benefits and why, from the Intent of proposal.md |
| Scope | yes | The tasks of the unit as a checklist, and the files they touch |
| Out of scope | when useful | What a reader might expect here that belongs to another item or to later |
| Covers | in a change | The `S-n` scenarios and requirement IDs (`CAP-<capability>-FR-n`) |
| Acceptance criteria | yes | Given/When/Then, observable, with at least one failure path |
| Estimate | if the team estimates | In the team's unit, labeled `(proposal)`, with its basis |
| Blocked by | yes | Local references, or `none` |
| Test cases | if wanted | Two by default: the main path and the most likely failure |
| Done when | yes | The exact test command passes, and only the listed files changed |
| Branch | when work is split among people | `<type>/<change-name>-unit-<letter>`, from the change's branch |
| Links | yes | Paths of the artifacts in the repository: `specs/<change-name>/tasks.md`, `spec.md` |
| Labels | optional | Only labels the team already uses |

## Titles

| Weak | Better | Why |
|---|---|---|
| Coupons backend | Reject expired coupon codes | Says the outcome, not the layer |
| PROJ-123 part 2 | Accept a coupon code at checkout | No IDs in titles; the tracker shows them |
| Fix stuff in store.py | Load a coupon by its code | Names behavior, not a file |
| Implement the coupon validation logic and add tests for expired and invalid codes | Reject expired and unknown coupon codes | Short enough to scan on a board |

## Acceptance criteria

- One behavior per scenario, from the spec scenarios the item covers. Keep their meaning, and cite their `S-n`.
- Observable from outside: what the user sees, what the API answers, what is stored. Never the class or the table that does it.
- At least one failure path: invalid input, not found, not allowed, a dependency down.
- Outside a change, when there is no spec, write them from the plan the person gave, and list the ones you inferred as `Assumed:` for the person to confirm.

## Estimates

- Only when the team estimates, in its unit: story points, t-shirt sizes, or none.
- Basis: the changed lines the Forecast of tasks.md expects for the unit's tasks, the number of files and scenarios, and the unknowns (a new dependency, an external service, a migration).
- Labeled `(proposal)`: the team decides in its own refinement or planning.
- Never days or hours unless the person asks for them, and then as a range.

## Suggested test cases

Each test case has a title, its type, the steps or Given/When/Then, and the expected result:

- **Type:** `automated` when a test in test-spec.md (`T-n`) or in the task's Tests line proves it, with that test's name; `manual` otherwise, with why it is not automated.
- **Two by default:** the main path and the most likely failure. More only when the person asks, or when the item covers more than two scenarios and each needs its own case.
- **No real data:** synthetic values and placeholders only.

## Example

Three units of a synthetic change, `PROJ-123-add-coupons`, whose tasks.md has Units A and B independent and Unit C depending on both.

```markdown
## WI-1 (story): Apply percentage coupons to the cart total

- Parent: PROJ-123
- Goal: shoppers see the discount of a valid coupon in their total before paying (proposal.md, Intent).
- Scope:
  - [ ] 1. Apply a percentage coupon to a cart total
  - Files: src/coupons/rules.py, tests/test_rules.py
- Out of scope: storing coupons (WI-2), the checkout form (WI-3).
- Covers: S-1 (CAP-coupons-FR-1)
- Acceptance criteria:
  - Given a cart of 80.00 and a valid 10% coupon, When the coupon is applied, Then the total is 72.00.
  - Given a cart of 80.00 and a 0% coupon, When the coupon is applied, Then the total stays 80.00 and no discount line appears.
- Estimate: 2 points (proposal; about 60 changed lines, one file and its tests)
- Blocked by: none
- Test cases:
  - TC-1 (automated, tests/test_rules.py::test_percentage_off_total): Given a cart of 80.00 and a 10% coupon, When applied, Then the total is 72.00.
  - TC-2 (automated, tests/test_rules.py::test_zero_percent_coupon): Given a 0% coupon, When applied, Then the total is unchanged.
- Done when: `python -m pytest -q tests/test_rules.py` passes and only the files above changed.
- Branch: feat/PROJ-123-add-coupons-unit-a, from feat/PROJ-123-add-coupons
- Links: specs/PROJ-123-add-coupons/tasks.md (Unit A), specs/PROJ-123-add-coupons/spec.md (S-1)

## WI-2 (story): Reject expired coupon codes

- Parent: PROJ-123
- Goal: shoppers get a clear refusal for an expired coupon instead of a silent failure.
- Scope:
  - [ ] 2. Load a coupon by code and reject expired ones
  - Files: src/coupons/store.py, tests/test_coupon_store.py
- Covers: S-3 (CAP-coupons-FR-2)
- Acceptance criteria:
  - Given a coupon whose end date was yesterday, When a shopper enters its code, Then they see "This coupon has expired" and the total does not change.
  - Given a code that does not exist, When a shopper enters it, Then they see "We do not recognize this code".
- Blocked by: none
- Test cases:
  - TC-3 (automated, tests/test_coupon_store.py::test_rejects_expired_code): Given an expired coupon, When loaded by code, Then it is refused as expired.
  - TC-4 (manual: the message wording is reviewed by the product owner): Given an unknown code on the checkout page, When entered, Then the message reads "We do not recognize this code".
- Done when: `python -m pytest -q tests/test_coupon_store.py` passes and only the files above changed.
- Links: specs/PROJ-123-add-coupons/tasks.md (Unit B), specs/PROJ-123-add-coupons/spec.md (S-3)

## WI-3 (story): Accept a coupon code at checkout

- Parent: PROJ-123
- Goal: shoppers can enter a coupon at checkout and pay the discounted total.
- Scope:
  - [ ] 3. Accept a coupon code at checkout
  - Files: src/api/checkout.py, tests/test_checkout.py
- Covers: S-2, S-4 (CAP-coupons-FR-1, CAP-coupons-FR-2)
- Acceptance criteria:
  - Given a valid coupon, When the shopper submits it at checkout, Then the order is charged the discounted total.
  - Given an expired coupon, When the shopper submits it at checkout, Then the order is not placed and the refusal is shown.
- Blocked by: WI-1, WI-2
- Test cases:
  - TC-5 (automated, tests/test_checkout.py::test_checkout_with_coupon)
  - TC-6 (automated, tests/test_checkout.py::test_checkout_with_expired_coupon)
- Done when: `python -m pytest -q` passes and only the files above changed.
- Links: specs/PROJ-123-add-coupons/tasks.md (Unit C), specs/PROJ-123-add-coupons/spec.md (S-2, S-4)
```

## After the person creates them

The person answers, for example: "WI-1 is PROJ-201, WI-2 is PROJ-202, WI-3 is PRJ-203". With `tickets.pattern` set to `[A-Z][A-Z0-9]*-\d+`:

```text
WI-1 -> PROJ-201   matches the pattern
WI-2 -> PROJ-202   matches the pattern
WI-3 -> PRJ-203    matches the pattern, but its prefix differs from the others: is it right?
```

A value that fails the pattern (`203`, `PROJ 203`) is reported with the example and asked once more. A prefix that differs but matches is not an error: ask, because only the person knows.
