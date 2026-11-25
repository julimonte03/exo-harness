---
name: roadmap-generator
description: >-
  Builds outcome-based roadmaps: objectives with their metrics, the
  initiatives that serve each one placed in horizons (now, next, later) or in
  quarters, their dependencies, risks and assumptions, the milestones that
  are real commitments, and a one-page executive view with summary cards and
  a Mermaid timeline, in the executive style of the design pack, or its
  neutral values without that pack. It starts with a short guided intake
  (owner, audience, scope, time range, key dates, workstreams), never invents
  dates, targets, capacity or commitments, and keeps what is uncertain
  visibly uncertain. Use it when someone asks for a roadmap, a product or
  technical plan for the coming quarters, a now-next-later view, or a
  one-page plan for leadership. Triggers: "build a roadmap", "roadmap for
  next year", "now next later", "quarterly plan for the team", "executive
  roadmap", "turn these initiatives into a roadmap", "one-page plan for
  leadership".
metadata:
  exo-pack: product
  exo-execution: inline
  exo-permissions: write-specs
---

# roadmap-generator

## Result

- **The roadmap** (`references/roadmap-model.md`): a header (owner, audience, scope, time range, version and date), the objectives `O-n` with their metrics, the initiatives `I-n` placed in horizons or quarters, the milestones `M-n` marked committed or target, the dependencies, the risks `R-n`, the assumptions `A-n`, and what is not on the roadmap.
- **The executive view** (`references/executive-view.md`): one page with a headline, three to five summary cards, the timeline, the top risks, the decisions asked of the audience, and a footer.
- **A visual:** a Mermaid timeline (or a Gantt chart when every date is real), or a visual brief for the slide or design tool the team uses.
- In the answer, or in the file the person names (for example `docs/roadmap/<slug>.md`). Inside an SDD change, that file is a project document, written with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C).

## When

- **On request:** "build a roadmap", "plan for next year", "now, next, later for the platform team", "one page for the steering committee".
- **After discovery,** when several features compete for the same team and someone has to order them.
- **Not for:** deciding whether one feature is worth building (skill:product-discovery); refining one item (skill:refinement-assistant); the plan of one change (`sdd-tasks`, pack `sdd`); a task-level schedule with a date per task, which is a project plan, not a roadmap: offer milestones instead. Once the roadmap is approved, skill:work-item-creator turns the initiatives of Now into work items.

## Inputs

1. **The intake answers** (step 1, `references/intake.md`).
2. **What the person brings:** strategy notes, objectives or OKRs, a list of initiatives, an earlier roadmap. Remove personal data and customer identifiers before working with them (`.exo/shared/data-protection.md`).
3. **Evidence in the repository,** for a technical or product roadmap: `.exo/context.md`, the living specs (`exo specs list --json`), the open changes (`exo change list --no-archived --json`), and the project's ADRs. Cite `path:line` (skill:context-retrieval).
4. **Memory:** `exo mem search "roadmap"` and the topic, for earlier decisions and versions (skill:memory-protocol).

## Steps

### 1. Run the intake

At most two rounds of at most five questions, each with a default (`references/intake.md`):

- **Owner:** the area or team that owns the roadmap.
- **Audience:** the team, leadership, other teams, or customers. A customer-facing roadmap carries no internal detail and no dates that are not commitments.
- **Scope and focus:** the product, platform or program it covers, and what it leaves out.
- **Time range and format:** now, next and later (the default), or quarters.
- **Key dates:** only commitments that already exist (a regulatory deadline, a contract, an event), each with its source.
- **Layers or workstreams:** how to group the initiatives (product areas, platform, compliance).
- **Capacity:** what the team can take on, in the person's words. Never assume it.

If the person already gave material that answers a question, confirm instead of asking.

### 2. Set the objectives

- Two to five objectives, each an **outcome**: a change in user behavior or a business result, not a feature.
- Each with a metric: baseline, target, date and source. Without a metric, write `Metric to define` and add an open question. Never invent a baseline or a target: propose one and label it a proposal.
- Tie each objective to the strategy the person gave.

### 3. List the initiatives

Each initiative `I-n` has: an outcome-oriented name, the objectives it serves, the result expected (a hypothesis), its confidence (high, medium, low), its size in the team's unit (or S, M, L), the owning team or role, its status (idea, discovery, in progress, done) and its workstream.

- An initiative that serves no objective goes to a **parking lot** with the question "which objective does this serve?". The person decides whether it stays.
- Keep the list honest: a "must have" from a stakeholder is still placed by its outcome and its dependencies.

### 4. Place them in time

- **Now:** in progress or starting, high confidence, with an owner and capacity behind it.
- **Next:** shaped and likely, medium confidence.
- **Later:** problems worth exploring, low confidence, **no dates**.
- **In quarters:** the same logic. The further the quarter, the coarser the items: problems and goals instead of features.
- **Dependencies first:** nothing is placed before what it depends on.
- **Capacity:** do not load Now beyond what the person said the team can take. When it does not fit, show the overflow and ask what moves.
- **Milestones:** fixed dates only for commitments, each labeled `committed` (with its source) or `target`.

### 5. Name the dependencies, risks and assumptions

- **Dependencies:** between initiatives, and on other teams, vendors or decisions. Mark the chain that decides the earliest committed milestone.
- **Risks** `R-n`: likelihood, impact, mitigation and owner role.
- **Assumptions** `A-n`: what must be true, and how and when it will be checked. Mark the riskiest one.

### 6. Check the roadmap

- Every initiative serves an objective; every objective has at least one initiative in Now or Next (otherwise it is a wish: say so).
- Every dependency points backward in time.
- Now fits the capacity the person gave.
- Later has no dates, and confidence falls with distance.
- Every committed milestone is reachable through its dependencies; flag the ones that are not.
- No output disguised as an outcome ("launch the new app" is an output; "half of the reschedules happen without a call" is an outcome).

### 7. Build the executive view

Follow `references/executive-view.md`: a one-sentence headline, three to five summary cards, the timeline, the top three risks, the decisions asked of the audience, and a footer with the owner role, the date, the version and the confidence legend ("Later is not a commitment").

**Style:** one model (`references/executive-view.md`, Style):

- **With the `design` pack:** its contract `executive-style.md` (in `.exo/shared/`) in full, with the brand of `.exo/brand.json` when the project has one.
- **Without it:** the neutral values of that contract, copied in the reference, and the keys of `.exo/brand.json` the reference lists, key by key. Never invent brand colors, fonts or logos.
- **Quality gate:** before it reaches leadership, apply `executive-visual-quality-gate` (pack `design`). Without it, say `design/executive-visual-quality-gate not installed — applying inline criteria` and run the checks at the end of the reference.

### 8. Draw the visual

- A Mermaid `timeline` for horizons or quarters; a `gantt` only when every date on it is real.
- A **visual brief** when the team builds slides in another tool: the layout, the sections, the cards and the style tokens, in the shape of the reference. `diagram-design` (pack `design`) can turn it into a finished visual; without it, say `design/diagram-design not installed — applying inline criteria` and deliver the Mermaid diagram with the brief.
- Before it leaves the organization, apply `secure-diagram-sanitizer` (pack `security`). Without it, say `security/secure-diagram-sanitizer not installed — applying inline criteria` and remove internal system names, hostnames, URLs, customer names and personal data.

### 9. Review it with the person

Show the executive view first, then the detail. Ask what is wrong, what is missing and what looks too optimistic. Adjust until the person approves, then set the version and the date in the header.

## Return

```markdown
**Headline:** by the end of Q3, most delivery changes happen without a call to support.

| Card | Objective | Target | Now | Confidence |
|---|---|---|---|---|
| Self-service | O-1: customers solve delivery changes alone | 50% of reschedules self-served by Q3 (baseline 0%) | I-1 Reschedule before dispatch | high |
| Fewer calls | O-2: support time goes to complex cases | Delivery calls from 40 to 15 a week | I-1 Reschedule before dispatch (I-4 Proactive delay notices is Next) | medium |
| Compliance | O-3: the order pages meet WCAG 2.2 AA | Audit passed | I-3 Accessibility fixes, for M-1 Audit, 2027-06-30 (committed: contract) | medium |

Top risk: R-1, the carrier may not accept changes after dispatch (spike in Now).
Decision needed: approve moving I-5 (reschedule after dispatch) from Now to Next: it depends on the carrier spike I-2, and Now stays within capacity.
```

## Rules

- **Outcomes over outputs.** Every initiative says what it changes and for whom.
- **No invented commitments.** Dates, targets, capacity and owners come from the person or a source; the rest is a proposal or an open question.
- **Uncertainty stays visible.** Confidence labels on every initiative; Later carries no dates and is not a promise.
- **Teams and roles, not people.**
- **Internal by default.** A roadmap is Internal data: it goes to the organization's own systems only. A public version is the person's explicit decision, without internal names, risks or unconfirmed dates (`.exo/shared/data-protection.md`, section C).
- **A living document.** Every version has a date; an update says what moved and why.

## Record

A roadmap usually lives outside any SDD change: save the approved version's key decisions to memory, without personal data, as skill:memory-protocol says (for example `exo mem save --type decision --topic-key roadmap/<owner> --title "Roadmap v2 approved" --content "<what moved and why>"`). If the person asked for it inside a change, an inline phase records it there before its envelope (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "roadmap-generator", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"roadmap-generator"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The owner, audience, scope, time range and capacity come from the person.
- [ ] Every objective is an outcome with a metric, or `Metric to define` with an open question.
- [ ] Every initiative serves an objective and carries a confidence label; the rest is in the parking lot.
- [ ] Dependencies point backward; Now fits the capacity; Later has no dates.
- [ ] Every fixed date is a milestone labeled committed (with its source) or target.
- [ ] The executive view fits one page and passed the quality checks.
- [ ] The header has a version and a date; nothing internal goes to an audience outside the organization.
