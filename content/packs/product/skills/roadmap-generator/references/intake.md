# Roadmap intake

The questions of step 1 of `roadmap-generator`, in two rounds. Ask the first round in one message; ask the second only for what the first round and the person's material did not answer. Every question has a default, so an unattended run can go on and label what it assumed.

## Round 1: frame

| # | Question | Why it matters | Default |
|---|---|---|---|
| 1 | Who owns this roadmap: which area or team? | Sets the scope and who approves it | The team the person speaks for |
| 2 | Who will read it: the team, leadership, other teams, or customers? | Decides the detail, the vocabulary and what may appear | Leadership and the team |
| 3 | What does it cover, and what does it leave out? | Keeps the roadmap from becoming a list of everything | The product or system the person named; the rest out |
| 4 | Which time range, and which format: now, next and later, or quarters? | Quarters invite date promises; horizons keep confidence honest | Now, next and later, over about a year |
| 5 | Which dates are already committed, and where does each come from? | Only these may appear as fixed milestones | None |

## Round 2: content

| # | Question | Why it matters | Default |
|---|---|---|---|
| 6 | What are the objectives, or the strategy they come from? | Every initiative has to serve one | Derive two to four from the material and label them proposals |
| 7 | Which initiatives are candidates, and which are already in progress? | The raw material; in-progress work goes to Now | Those in the material and the open changes in the repository |
| 8 | How should the initiatives be grouped: product areas, platform, compliance? | The layers or workstreams of the views | One group per objective |
| 9 | What can the team take on in Now, roughly? | Without it, Now overflows | Ask again; until answered, mark Now as "capacity not confirmed" |
| 10 | Which risks or dependencies on other teams do you already know? | They change the order | Only those found in the material |

## By audience

| Audience | Show | Leave out |
|---|---|---|
| The team | Everything, including the parking lot and the assumptions | Nothing |
| Leadership | Objectives, horizons, committed milestones, top risks, decisions needed | Initiative-level detail beyond one line, internal debates |
| Other teams | The initiatives that touch them, the dependencies in both directions, the dates they rely on | Internal priorities that do not affect them |
| Customers | Problems being solved, in their words, by horizon | Internal names, risks, capacity, any date that is not a commitment |

A customer-facing roadmap is a separate, reviewed version: never the internal one with parts hidden.

## Working from what the person brings

- **A list of features:** turn each into an initiative by asking "what changes, and for whom?"; group them under objectives; anything that answers neither goes to the parking lot.
- **An earlier roadmap:** keep its IDs, mark what moved since the last version and why, and carry over the assumptions that were never checked.
- **Objectives or OKRs:** use them as the objectives, with their key results as metrics.
- **A strategy document:** extract two to four outcomes, label them proposals, and confirm them before placing anything.
- **Open changes in the repository** (`exo change list --json`): they are in progress, so they belong to Now, under the objective they serve.

## Questions that usually unblock a stuck roadmap

- "If only one objective could move this year, which one?"
- "What would make you stop this initiative?"
- "Which date would hurt us if we missed it, and who decided it?"
- "What does the team stop doing to make room for this?"
