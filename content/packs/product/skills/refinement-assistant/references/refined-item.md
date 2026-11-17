# Refined item

The shape of a refined backlog item. Keep the headings, write `None` with the reason when one does not apply, and `Open question:` where the answer is missing. The example is synthetic: a delivery service for an online shop.

## Template

```markdown
# <Outcome in a few words>

<ID, when the item has one and it matches tickets.pattern; otherwise leave this line out>

## Story

As a <role>, I want <capability>, so that <outcome>.

## Context

<The problem today and what it costs, with evidence: path:line, a document, the person's words.>

## Scope

- <what is included>

## Out of scope

- <what a reader might expect here, and where it goes instead>

## Acceptance criteria

1. Given <state>, When <action>, Then <observable result>.
2. ...

## Dependencies

- <item, team, system or decision>: <what is needed from it>

## Risks

| Risk | Impact | Mitigation or spike |
|---|---|---|
| ... | ... | ... |

## Open questions

1. <question> (answers: <role>): <why it matters>. Default: <assumption>.

## INVEST

| Criterion | Result | Why |
|---|---|---|
| Independent | pass/fail | ... |
| Negotiable | pass/fail | ... |
| Valuable | pass/fail | ... |
| Estimable | pass/fail | ... |
| Small | pass/fail | ... |
| Testable | pass/fail | ... |

## Split

<Only when needed: the slices in order, each with its title, story and criteria.>

## Estimate

<In the team's unit, labeled (proposal), with its basis; or "The team estimates in planning".>

## Verdict

<Ready | Ready with open questions | Not ready>: <what is missing or what to confirm>.
```

## Before

What a person might bring, as written:

```text
Delivery change
Customers should be able to change their delivery. Also cancel. Needs to work with the carrier.
ASAP please, lots of calls.
```

## After

```markdown
# Customers can reschedule a delivery before dispatch

## Story

As a customer waiting for an order, I want to move the delivery to another day, so that I am home when it arrives without calling support.

## Context

Support receives about 40 calls a week asking to move a delivery (weekly support summary the person gave). Today only a support agent can change the date, from the back office (src/backoffice/deliveries.py:88). The order page shows the date but no way to change it (src/web/order_page.tsx:41).

## Scope

- A "Change delivery day" action on the order page, before dispatch.
- The next available slots from the existing slot calendar (src/delivery/slots.py:20).
- A confirmation on screen and by the order notification the shop already sends.

## Out of scope

- Cancelling a delivery: a separate item (it serves another goal).
- Changes after dispatch: depend on the carrier (spike below).
- Changing the delivery address: has its own fraud checks.

## Acceptance criteria

1. Given an order not yet dispatched, When the customer opens it, Then they see "Change delivery day".
2. Given the customer picks another available day, When they confirm, Then the order shows the new day and they get the confirmation.
3. Given an order already dispatched, When the customer opens it, Then the action is not shown and a note says why.
4. Given no other day is available in the next 14 days, When the customer opens the action, Then they see "No other days available" and a link to support.
5. Given the change fails to save, When the customer confirms, Then they see "We could not change the day; your delivery stays on <current day>" and nothing changes.
6. Given the order is dispatched after the customer opened the action, When they confirm, Then they see "Your order has already left; the day can no longer change" and nothing changes.

## Dependencies

- Slot calendar (src/delivery/slots.py): reused as is.
- Notifications: the existing order notification template needs a "day changed" variant (owner: notifications team).

## Risks

| Risk | Impact | Mitigation or spike |
|---|---|---|
| A change arrives while the order is being dispatched | The parcel leaves on the old day | Check the dispatch status when confirming, not only when opening (criterion 6) |
| Customers change the day many times | Slot calendar churn | Open question 2 |

## Open questions

1. What is the latest time to change before dispatch (answers: product owner)? Default: 18:00 the day before.
2. Should the number of changes per order be limited (answers: operations)? Default: no limit in the first version.

## INVEST

| Criterion | Result | Why |
|---|---|---|
| Independent | pass | Uses the existing slot calendar and notifications |
| Negotiable | pass | The criteria fix outcomes, not the screen layout |
| Valuable | pass | Removes the most common support call |
| Estimable | pass | After moving changes after dispatch out of scope |
| Small | pass | One action, one page, six criteria |
| Testable | pass | Every criterion is observable on the order page |

## Estimate

5 points (proposal): one new action on an existing page, an existing calendar, one notification variant; the main unknown is the dispatch race, covered by criterion 6 and the first risk.

## Verdict

Not ready: question 1 blocks, because the latest change time decides when the action stops being offered (criteria 1 and 3). Once the product owner confirms it, the item is Ready with open questions: question 2 does not block.
```

## What changed, and why

- The vague "delivery change" became one outcome for one role; cancelling went to its own item.
- "Needs to work with the carrier" became an explicit boundary (before dispatch) and a spike for after dispatch.
- "ASAP, lots of calls" became evidence in the Context, not urgency in the text.
- Every number came from the person or the code; the two unknowns are open questions with defaults.
