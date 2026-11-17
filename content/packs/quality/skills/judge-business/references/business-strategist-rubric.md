# judge-business: the business strategist's rubric

How a strategist who has sat on both sides of the table, building the business case and selling the result, reads a proposal. Eight dimensions; use what the change calls for (Proportionality, at the end). Every finding still needs the artifact line and a suggested fix.

## 1. Value

The question: what does the business get, and why now?

- **Who benefits:** the user, the buyer when they differ, and the business itself. A change can help users and still cost the business more than it returns.
- **The outcome in business terms:** more revenue, more conversion or retention, less cost to serve, less risk (legal, security, operational), or time saved multiplied by how often it happens. "Better" or "modern" is not an outcome.
- **Why now:** the trigger (a customer commitment, a deadline, a competitor, a growing cost) and the cost of waiting another quarter.
- **Evidence:** where the value claim comes from: a measure, tickets, customer requests, a contract. A claim with no source is a hypothesis; it should say so.

Red flags: value described only as a feature list; benefits for "everyone"; a value that depends on users changing their habits with nothing that makes them change.

## 2. Cost

The question: what does it take to build it, run it and live with it?

- **Build:** the size the approach implies; the tier is a hint of the ceremony it needs.
- **Run:** infrastructure, licenses, paid third-party services (messaging, maps, payments), storage growth, on-call and support load.
- **Change:** training, migration of existing users or data, communication, documentation.
- **Opportunity:** what the team will not do while it builds this.

An order of magnitude or a range is enough. A run cost that scales with usage (per message, per call, per seat) needs its driver named.

## 3. Risk

The question: what can go wrong for the business, and can we undo it?

| Risk | Look for |
|---|---|
| Adoption | Users or customers will not change what they do; nothing in the plan helps them |
| Market | A competitor already covers it better; the segment is too small to matter |
| Legal, regulatory, contractual | Consent, data residency, accessibility law, terms promised to customers, licenses of what is reused |
| Reputation | A visible failure, a claim the product cannot keep, a change customers will read as a price rise |
| Operational | Support volume, manual work hidden behind the feature, a new dependency on one vendor |
| Financial | Pricing or billing mistakes, revenue that leaks through a loophole, costs that grow faster than income |
| Reversibility | A one-way door (a public price, a data migration, a contract) needs more care than a two-way door behind a feature flag |

Each risk the proposal names should come with a mitigation or an explicit acceptance.

## 4. Alternatives

The question: is this the cheapest way to get the value?

- **Do nothing:** what the status quo costs. If it costs little, the proposal needs a strong value.
- **Buy, partner or reuse:** an existing product, an open-source library, a feature of a tool the organization already pays for.
- **A smaller version:** a manual or semi-manual first step, a pilot with a few customers, a configuration change instead of code.
- **A process change** instead of software.

The chosen option should beat the others on value, cost or risk, and the proposal should say on which.

## 5. Fit with goals

The question: does this move a goal the organization already has?

- Name the objective it serves, from `.exo/context.md`, the roadmap or strategy documents in the repo, or the ticket.
- It fits the product's positioning and does not contradict another initiative (two teams solving the same problem, a feature that cannibalizes a paid one).
- When no goal is written anywhere, the finding asks the proposal to say which objective it serves; it is not a reason to stop reviewing.

## 6. Business metrics

The question: how will we know it paid off, and when do we stop?

- **A primary metric** tied to the value: the business outcome, not only the user outcome. For an internal tool they can be the same.
- **Baseline, target and time frame,** and the data source where it is read.
- **A leading indicator** that moves early (activation, first use, trial starts), so the team does not wait months to learn.
- **Guardrails:** what must not get worse (support tickets, churn, margin, conversion of the existing flow, page speed).
- **A decision rule:** which result means keep going, iterate or roll back.

## 7. Reaching the users (marketing and sales)

The question: once it is built, who finds out, and how does it turn into value?

- **Audience:** users, buyers, sales, support, partners: who must know, and who must be ready.
- **Discovery:** in-product hints, release notes, a campaign, a sales conversation. A feature nobody finds delivers nothing.
- **Message:** consistent with the value and the scope; no promise the scope does not keep.
- **Pricing and packaging:** whether it changes plans, entitlements or prices, and for whom. A change in what customers pay or get is never a detail.
- **Enablement:** the demo, the FAQ, the support notes, the training for an internal tool.
- **Rollout and feedback:** a pilot, a staged release or a flag, and the channel where feedback comes back.

For an internal tool, read this as adoption: who must start using it, who champions it, what replaces the old way.

## 8. Commercial sense

The question: does the money side add up?

- When money moves (prices, fees, discounts, refunds, payouts), the unit economics: what one transaction earns against what it costs to serve.
- Commitments to customers (service levels, support hours, data handling) that the change creates or touches.
- Claims to customers and in marketing must be true for every customer who reads them.

## Proportionality

Scale the depth to the size and the stakes of the change. Ask for what the decision needs, not for a full business plan.

| The change | What the proposal should cover |
|---|---|
| A fix, a refactor, internal tooling with no new cost | One line of value and one of cost; a risk only if there is one. Missing extras are not findings. |
| A feature for existing users | Dimensions 1 to 6, briefly; 7 when users must discover it |
| A new product, a new market, a price, a paid third-party service, a contract | All eight |

## Rules of the judge

- **Never invent figures:** no market sizes, prices, conversion rates or costs from memory. When the proposal needs a figure it lacks, the finding asks for it and may suggest how to estimate it.
- **No outside research:** judge with what the repo, the change and the person give.
- **Judge the business case, not the people** who wrote it, and never the users or customers it mentions.
- **Never copy** personal data, customer names from tickets or confidential contract terms into a finding: point at the line.
