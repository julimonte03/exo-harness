---
name: product-discovery
description: >-
  Structures product discovery before anything is built: who has the problem
  and the job they are trying to get done, the hypotheses behind the idea and
  the riskiest one, success metrics with baseline, target and source, the main
  user flows, acceptance criteria in Given/When/Then, and the smallest MVP
  worth shipping. Inside an SDD change it feeds the phase that loads it (the
  Intent of proposal.md, scenarios for the spec, or open questions for the
  person) and never edits another phase's artifact. Use it when a product
  problem is new or fuzzy, when a new feature, an MVP or its value is unclear,
  when a change adds a new user flow, or when someone wants to know what to
  build first and how to tell whether it works. Triggers: "product
  discovery", "jobs to be done", "who is this for", "is this worth building",
  "define the MVP", "success metrics", "user flow", "what should we build
  first", "how will we know it works", "acceptance criteria for a new
  feature".
metadata:
  exo-pack: product
  exo-execution: inline
  exo-permissions: write-specs
---

# product-discovery

## Result

The six parts of a discovery, each backed by evidence or marked as an open question:

1. **Job to be done:** the user (a role), the situation, the job and the outcome they want.
2. **Hypotheses:** what must be true for the idea to work, with the riskiest one first.
3. **Success metrics:** a primary metric with baseline, target, timeframe and source, plus a guardrail.
4. **User flows:** the main path and its failure and edge paths, step by step.
5. **Acceptance criteria:** Given/When/Then, one observable behavior each.
6. **MVP scope:** the smallest slice that tests the riskiest hypothesis end to end, and what waits.

Where they land depends on who loaded the skill (next section). What nobody can answer yet becomes an open question for the person, never a guess.

## When

- **SDD conditional** (`.exo/shared/phase-skill-map.md`): explore, when the product problem is new or fuzzy; propose, for a new feature, an MVP or an unclear value; spec, when the change adds a new user flow.
- **On request,** outside a change: "is this worth building", "what is the MVP", "who would use this".
- **Not for:** a change whose user, problem and value are already clear and written (a bug fix, a refactor, a dependency bump); writing the spec delta itself, which is `sdd-spec`; a roadmap across many features; UI design.

## Where the output goes

Write only into the artifact the current phase owns (`.exo/shared/sdd-phase-common.md`, section C). If an earlier artifact is wrong or missing a part, stop with `status: needs-input` and say what is missing: never edit it.

| Loaded by | Runs in | What this skill produces | Who writes it |
|---|---|---|---|
| `sdd-explore` | `sdd-explorer` (read-only) | What the evidence says about the user, the problem, the value and the measure, for the Goal of exploration.md; every unknown as an Open Question | the explorer returns text; the orchestrator writes the file |
| `sdd-new`, `sdd-propose` | inline | The Intent of proposal.md (User, Problem, Value, Success measure), the MVP cut in Scope and Out of Scope, and the main flow as a Scope bullet | the phase, in proposal.md |
| `sdd-spec` | inline | Requirements and Given/When/Then scenarios for each new flow, ready for the delta | `sdd-spec`, in spec.md, numbering IDs and scenarios its way |
| The person, outside a change | inline | The full discovery brief (`references/discovery-brief.md`) | you, in the answer or in the file the person names |

- In spec, first check that the Intent of proposal.md states the user, the problem, the value and the success measure. If one is missing, return `needs-input` and name it: that gap belongs to `sdd-propose`.
- The explorer cannot ask the person. Mark each unknown `[Unverified]` or as an Open Question, with the default you would assume.
- Hypotheses and the experiment that would test them have no section in proposal.md: put the riskiest one in Value ("we expect ... because ...") and the rest as open questions in your answer, or in the brief outside a change.

## Inputs

1. The request, in the person's words.
2. `.exo/context.md`, the README and the code the idea touches: what exists today, who uses it, what is logged or measured. Cite `path:line` (skill:context-retrieval).
3. In a change: proposal.md, exploration.md when present, and `exo specs list --json` for the living specs of the capabilities involved.
4. Memory: `exo mem search "<topic>"` for earlier decisions about the same users or feature (skill:memory-protocol).

Tickets, support logs or analytics exports are evidence too, but clean them first: no personal data, no customer identifiers (`.exo/shared/data-protection.md`). Describe users as roles, never by name.

## Steps

Methods, formats and worked examples for each step are in `references/methods.md`.

### 1. Job to be done

Write the job as: "When `<situation>`, `<user role>` wants to `<job>`, so they can `<outcome>`." Then the current workaround and what it costs them (time, errors, money, risk), with evidence. If you cannot name a real user role and a situation, stop here and ask: the rest depends on it.

### 2. Hypotheses

List what must be true for the idea to succeed, one line each, in four kinds: **value** (they want it), **usability** (they can use it), **feasibility** (we can build it with this stack), **viability** (it is worth its cost and risk). Mark each as supported (with evidence) or assumed. Put the riskiest assumed one first, with the cheapest way to test it before or while building.

### 3. Success metrics

- **Primary metric:** one number that moves if the job gets done better, with its baseline, its target, when it is measured and where the data comes from (`references/methods.md`, Metrics).
- **Guardrail:** what must not get worse (error rate, support tickets, latency, another flow's conversion).
- No baseline today: say so, and make "start measuring X" part of the MVP. Never invent a baseline or a target: propose one and label it as a proposal for the person.

### 4. User flows

For each flow: the entry point, the numbered steps, the decisions, and how it ends. Include the failure paths (invalid input, nothing found, no permission, the service is down) and the empty and first-use states. Use a numbered list, or a mermaid flowchart when the project renders it.

### 5. Acceptance criteria

One scenario per behavior, in Given/When/Then, observable from outside: what the user sees or what the system stores, never the class or the table that does it. Cover the main path, each failure path of step 4 and the edge cases. In spec, hand them to `sdd-spec` in its format:

```markdown
#### Scenario S-1: A free room is booked
- Given the room "Atlas" is free tomorrow from 10:00 to 11:00
- When the person books it for that hour
- Then they see the booking confirmed with the room and the time
```

### 6. MVP scope

Cut to the smallest slice that tests the riskiest hypothesis end to end, for one user role and one main flow. Sort the rest as later, with why. Prefer a thin slice through every layer over a complete layer with nothing on top. In propose, the slice becomes Scope and the rest Out of Scope.

### 7. Questions for the person

In one message, at most five questions, each with why it matters and the default you would assume. Ask before writing when the user, the problem or the success measure is unclear. In an unattended run, write the defaults, label them `Assumed:` and list them in the envelope notes.

## Write it into proposal.md

In propose (and new), the Intent keeps the four parts `sdd-propose` uses:

```markdown
## Intent

- **User:** support agents who answer refund requests.
- **Problem:** finding the order behind a refund request takes four searches and about six minutes (src/support/search.py:41); agents skip it and refund blindly.
- **Value:** we expect a single lookup by request to cut handling time and blind refunds, because agents already copy the request ID first.
- **Success measure:** median handling time under two minutes, and blind refunds below 2% of refunds, from the support tool's event log, 30 days after release (baseline today: six minutes, 11%).
```

Scope gets the MVP slice and a bullet with the main flow; Out of Scope gets what waits. Run `exo speclint <change-root>/proposal.md` after editing.

## Rules

- **Evidence or a question.** Every claim about users, usage or numbers has a source (`path:line`, a document, the person's words) or is an open question. Never present an assumption as a fact.
- **Roles, not people.** No names, emails or customer data in any artifact, example or memory entry.
- **Outcome over output.** A feature list is not a goal: tie every scope item to the job, a hypothesis or the metric.
- **The person decides** the MVP cut and the targets. You propose; record what they decide.
- **Stay in your lane.** No UI design, no technical design, no estimates in days. Hand those to the phases that own them.

## Record

Inside a change, before the phase envelope (`.exo/shared/capability-attribution.md`). A subagent lists the skill in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "product-discovery", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"product-discovery"'
exo change record <change> --add decisions '{"summary": "MVP: lookup by request ID for agents; bulk lookup later", "by": "human"}'
```

`activation` is `requested` when the person asked for discovery by name. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record; save the decisions to memory as skill:memory-protocol says, without personal data.

## Before you finish

- [ ] The user is a role, and the job has a situation and an outcome.
- [ ] The riskiest hypothesis is named, with how to test it.
- [ ] The primary metric has a baseline (or "none yet"), a target, a timeframe and a source; there is a guardrail.
- [ ] Every flow has its failure paths, and every scenario is Given/When/Then and observable.
- [ ] The MVP is one slice for one user and one flow; the rest is listed as later.
- [ ] Nothing was written outside the artifact the current phase owns; gaps in earlier artifacts went back as `needs-input`.
- [ ] Unknowns are open questions with a default, never invented numbers.
