# Flow document

The shape of a functional flow outside an SDD change: in the answer, or in the file the person names (for example `docs/flows/<slug>.md`). Keep the headings; write `Open question:` where the evidence is missing, and `None` with the reason when a section does not apply. The example is synthetic: returning a delivered order in an online shop.

## Template

````markdown
# Flow: <goal in a few words>

## Frame

- **Trigger:** <what starts the flow>
- **Goal:** <what the main actor gets>
- **End states:** <success>; <each way it ends without success>
- **Boundary:** starts at <first step>, ends at <last step>. Out of this flow: <related flows>.

## Actors

| Actor | Kind | Responsible for |
|---|---|---|
| <role> | person | ... |
| <system> | system | ... |
| <provider> | external system | ... |

## Main path

1. <Actor> <verb> <object>.
2. <Actor> checks <condition> (BR-1).
   - <answer> → 3. <answer> → E1.
3. ...

## Exceptions

| ID | Starts at | What the actor sees | How it ends |
|---|---|---|---|
| E1 | 2 | ... | <back to a step, a compensation, or a final state> |

## Data that travels

| Data | Produced by | Received by | Step | Level |
|---|---|---|---|---|
| <business name> | <actor> | <actor> | 3 | Internal |

## States

| State | Entered by | Leaves to |
|---|---|---|
| <state> | step 4 | <state> (step 6), <state> (E2) |

## Business rules

- **BR-1:** <rule>. Source: <path:line, a document, or the person>.

## Diagram

```mermaid
<the diagram of references/mermaid-patterns.md>
```

## Open questions

1. <question>: <why it matters>. Default if unanswered: <assumption>.
````

## Example

````markdown
# Flow: return a delivered order

## Frame

- **Trigger:** a customer wants to send back items from an order that was delivered.
- **Goal:** the customer gets a return label, and later a refund for the items received.
- **End states:** refunded; not returned (outside the window, or cancelled by the customer); refund rejected after inspection.
- **Boundary:** starts when the customer opens a delivered order, ends when the refund is issued or rejected. Out of this flow: exchanges, and returns of orders not yet delivered (those are cancellations).

## Actors

| Actor | Kind | Responsible for |
|---|---|---|
| Customer | person | Asks for the return, picks the items, ships the parcel |
| Web shop | system | Shows the orders, checks the return window, collects the request |
| Returns service | system | Creates the return, the label and the refund request |
| Carrier | external system | Issues the label and reports the parcel's scans |
| Warehouse operator | person | Inspects the items received |
| Payments provider | external system | Refunds the original payment |

## Main path

1. Customer opens a delivered order and asks to return it.
2. Web shop checks the return window (BR-1).
   - Within the window → 3. Outside the window → E2.
3. Customer picks the items and a reason for each.
4. Returns service creates the return and asks the Carrier for a label.
5. Customer receives the label and the drop-off instructions.
6. Carrier scans the parcel at drop-off and at the warehouse.
7. Warehouse operator inspects the items (BR-2).
   - All accepted → 8. Some rejected → 8 for the accepted items, and E5 for the rest.
8. Returns service asks the Payments provider to refund the accepted items (BR-3).
9. Customer receives the refund confirmation.

## Exceptions

| ID | Starts at | What the actor sees | How it ends |
|---|---|---|---|
| E1 | 3 | Customer leaves without confirming: the request is kept as a draft for 24 hours | Final state: not returned, when the draft expires |
| E2 | 2 | "This order can no longer be returned", with the date the window closed | Final state: not returned |
| E3 | 4 | The Carrier does not answer: "We could not create your label; we will email it within a few minutes" | Retried in the background; after three failures a support case opens and the customer is told |
| E4 | 6 | No scan within 14 days of the label | Reminder to the customer; after 30 days the return is closed as not returned |
| E5 | 7 | Customer is told which items were rejected and why | Rejected items are shipped back; final state for them: refund rejected |
| E6 | 8 | The Payments provider declines the refund | Support agent issues store credit (BR-4); Open question: is store credit acceptable for every payment method |

## Data that travels

| Data | Produced by | Received by | Step | Level |
|---|---|---|---|---|
| Order number and items | Web shop | Returns service | 4 | Internal |
| Delivery address | Web shop | Carrier | 4 | Restricted (personal data to an external actor: check the carrier agreement) |
| Return reason | Customer | Returns service, Warehouse operator | 3, 7 | Internal |
| Inspection result | Warehouse operator | Returns service | 7 | Internal |
| Refund amount and payment reference | Returns service | Payments provider | 8 | Restricted |

## States

| State | Entered by | Leaves to |
|---|---|---|
| Draft | step 3 | Requested (step 4), Expired (E1) |
| Requested | step 4 | In transit (step 6), Closed (E4) |
| In transit | step 6 | Received (step 7) |
| Received | step 7 | Refunded (step 8), Partially refunded (E5), Rejected (E5) |
| Refunded, Partially refunded, Rejected, Expired, Closed | | final |

## Business rules

- **BR-1:** an order can be returned within 30 days of its delivery date. Source: src/returns/policy.py:12.
- **BR-2:** an item is accepted when it is unused and in its original packaging. Source: the returns policy page the person gave.
- **BR-3:** the refund goes to the original payment method. Source: src/returns/refunds.py:40.
- **BR-4:** a declined refund becomes store credit. Open question: confirmed only for card payments.

## Open questions

1. Does the 30-day window count from delivery or from the order date for marketplace sellers? It changes BR-1 for a third of the orders. Default if unanswered: from delivery, as in the code.
2. Who decides on store credit when the refund is declined: the support agent or the system? Default if unanswered: the support agent.
````

## Checks before delivering

- The step numbers, decision questions and exception IDs in the diagram match the text.
- Each `BR-n` has a source or is an open question; none was invented.
- The Restricted rows name what has to be checked (an agreement, a waiver, the design).
- The example values are synthetic; real order numbers, addresses or names never appear.
