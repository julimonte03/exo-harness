# Options and trade-offs

Steps 5 and 6 of `software-solution`: build real options, compare them against the drivers, and recommend one for the person to choose.

## Where options come from

Start from these sources and keep two or three that are genuinely different:

| Source | Example for returns |
|---|---|
| Extend what exists | Add returns to the order platform as a new module |
| A new component with clear ownership | A returns service with its own store, fed by order events |
| Buy or use a managed service | A returns management product from a vendor, integrated by API |
| Change the process, not the system | Support keeps handling returns, with a better back-office screen |

- **The simplest option that could meet the drivers** is always on the list. Often it wins.
- **No straw men.** If you would never recommend an option, replace it with one you might.
- **Same level of detail** for every option, or the comparison is biased toward the one you described best.

## Describing an option

For each option, the same five parts:

1. **Shape:** the components and their responsibilities, in a few lines or a small diagram.
2. **Drivers:** how it meets each driver, and where it struggles.
3. **Cost:** to build (rough effort) and to run (rough monthly order of magnitude, or low, medium, high).
4. **Risks:** what could go wrong, and what we do not know yet.
5. **Lock-in and reversibility:** what it makes hard to change later.

## The comparison matrix

Weights come from the ranking of the drivers, agreed with the person. Scores from 1 (poor) to 5 (strong), each with a one-line reason; the reasons matter more than the totals.

| Driver (weight) | A: extend the order platform | B: returns service + events | C: vendor product |
|---|---|---|---|
| Availability when the carrier is down (3) | 3: shares the order platform's retries | 4: queues label requests on its own | 3: depends on the vendor's design |
| Security of refund data (3) | 2: refund data in the busiest codebase | 4: isolated store, narrow access | 3: data at the vendor; needs an agreement |
| Modifiability: second carrier (2) | 2: carrier code inside order modules | 4: one adapter | 3: vendor supports four carriers |
| Time to market (2) | 4: no new deployable | 3: one new service and a consumer | 2: procurement and integration |
| Running cost (1) | 5: no new infrastructure | 3: one service, one store | 2: license per return |
| **Weighted total** | 32 | 41 | 30 |

- A close total means the weights decide: show the person which weight would flip the result.
- A score of 1 on a top driver disqualifies an option, whatever the total.

## Reversibility

| Kind | Examples | Treatment |
|---|---|---|
| Two-way door: cheap to undo | A library, an internal API between two services you own, a feature flag | Decide fast; revisit when needed |
| One-way door: expensive to undo | A data store, a vendor contract, a public API, a data model shared by many teams, the hosting region | Slow down: decision record, the person's explicit approval, an exit plan |

Every one-way door in the recommended option becomes a draft decision record.

## The recommendation

Write it in this shape:

> **Recommendation: B, a returns service fed by order events.**
> It wins on the two top drivers: refund data stays isolated, and label requests queue on their own when the carrier is down. It gives up some time to market (one new deployable and an event consumer) and adds a running cost the person rated as low priority.
> It would lose to A if the release date became the top driver.
> One-way doors: the returns store, and the `ReturnReceived` event as a contract for other teams. Both get a decision record.

Then stop and ask the person to choose (the checkpoint of step 6).

## Anti-patterns to name when you see them

| Anti-pattern | Sign | Better |
|---|---|---|
| Technology first | The option is named after a product, and the drivers came later | Start from the drivers; the product is a detail of an option |
| Distributed monolith | Several services that must deploy together and share a database | Fewer services with clear data ownership, or one modular deployable |
| Premature scale | Sharding, multi-region or event sourcing without a driver that needs it | The simplest design that meets the measured drivers, with a path to grow |
| Shared database as integration | Two teams read and write the same tables | One owner per data set; others use its interface or its events |
| Resume-driven design | The new technology is the goal | Ask what driver it serves; if none, drop it |
| Vendor without exit | No way to get the data out | An exit plan: export format, contract clause, effort to migrate |

## Decision records

For each one-way door, a draft with: status (`Proposed`), context (the drivers and constraints that matter), the decision, the alternatives with why each lost, and the consequences (good and bad). `architecture-decision-record` (pack `design`) writes it in the project's ADR folder once the person approves; without that skill, propose the same text for the folder the project uses (`docs/adr/` when it has none).
