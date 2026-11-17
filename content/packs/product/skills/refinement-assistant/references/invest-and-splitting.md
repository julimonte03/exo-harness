# INVEST, splitting and estimates

Checks and patterns for steps 5 to 8 of `refinement-assistant`. The team's own Definition of Ready and estimate unit always win over the defaults here.

## INVEST

| Criterion | The question | Signs it fails | Usual fix |
|---|---|---|---|
| Independent | Can it be built and released without waiting for another item in the same sprint? | "After X is done", shared files with another item in progress, a half that only works with another item | Reorder, merge the coupled parts, or split so each slice stands alone |
| Negotiable | Does it fix the outcome and leave room for how? | A screen design or a technical solution written as the requirement | Move the "how" to notes; keep the criteria on observable outcomes |
| Valuable | Does a user or the business get something they can notice? | Pure layers ("create the table"), work nobody can try | Fold the layer into a vertical slice; or make it an explicit enabler with its reason |
| Estimable | Can the team size it with what they know? | Big unknowns: an external system, a new technology, unclear rules | Answer the open questions, or add a time-boxed spike first |
| Small | Does it fit comfortably in one iteration of the team? | More than about seven criteria, several roles or goals, "and also" | Split (below) |
| Testable | Can someone check each criterion, pass or fail? | "Fast", "easy", "user-friendly", "works like before" | Rewrite as Given/When/Then; a non-functional need gets a number from the person |

## Acceptance criteria that work

| Weak | Better |
|---|---|
| The page should be fast | Given 100 orders in the history, When the customer opens it, Then the first 20 appear within 2 seconds (the target comes from the person) |
| Handle errors properly | Given the payment provider does not answer, When the customer pays, Then they see "Payment is taking longer than usual" and are not charged twice |
| Admins can manage users | Given an admin, When they deactivate an account, Then that account can no longer sign in and the admin sees it marked inactive |
| Works on mobile | Given a 360-pixel-wide screen, When the customer opens the order page, Then every action is visible without horizontal scrolling |

Each criterion: one behavior, a starting state, one action, and a result someone can see or check in stored data.

## Split patterns

Every slice delivers something a user can try. Pick the first pattern that gives slices of similar size.

| Pattern | When | Example: "Customers manage deliveries" |
|---|---|---|
| Workflow steps | The item is a sequence | See the delivery day; then change it; then get notified |
| Business rule variations | Several rules or policies | Change before dispatch first; changes after dispatch later |
| Data variations | Different kinds of input | Home deliveries first; pickup points later |
| Channels or interfaces | Several ways in | Web first; mobile app later |
| Happy, then unhappy paths | The failures are many | The change works; then the full handling of conflicts and limits |
| Operations | Create, read, update, delete | View deliveries; change; cancel |
| Simple, then complex | One case covers most uses | Fixed slots first; time windows chosen by the customer later |
| Spike first | A big unknown blocks estimating | Two days to learn whether the carrier accepts changes; then the item |

**Never split by layer** (frontend, backend, database) or by activity (design, build, test). Those pieces deliver nothing on their own and hide integration risk until the end.

Order the slices so the first one tests the riskiest assumption or delivers the most value, and say why.

## Estimates

- **The unit is the team's:** story points, t-shirt sizes (XS to XL), or no estimates at all. Never convert points to days.
- **Relative, not absolute:** compare with an item the team already finished ("about like the address change, plus a notification").
- **Three drivers:** complexity (how many parts and rules), uncertainty (what nobody knows yet), effort (how much there is to do). State which one drives your proposal.
- **High uncertainty:** propose a spike with a time box and a question it must answer, instead of a large number.
- **Too big to estimate:** that is a Small fail; split first.
- **Always a proposal.** The team estimates together, for example in planning poker; yours only opens the conversation.

## Default Definition of Ready

Use it when the team has none, and say that it is the default:

1. One role, one capability, one outcome.
2. Acceptance criteria in Given/When/Then, all testable, covering the main failure.
3. Dependencies named, and none blocking the start.
4. No open question that blocks the start; the others have an owner.
5. Small enough for one iteration, or split.
6. Estimated by the team, when the team estimates.
7. Data protection considered: personal data or credentials involved are named, so the design can classify them.

## Talking with non-technical people

- Ask about outcomes and situations ("what happens today when a customer wants another day?"), not about systems.
- Offer options with consequences instead of open technical questions.
- Translate a needed technical term the first time ("dispatch: the moment the parcel leaves the warehouse").
- Read the refined item back in two lines before the details, so they can confirm the goal first.
