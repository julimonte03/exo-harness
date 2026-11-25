---
name: functional-flow-designer
description: >-
  Designs end-to-end functional flows that business and engineering read the
  same way: the trigger and the outcome, the actors (roles and systems), the
  numbered steps, every decision with its branches, the exceptions, the data
  that travels between actors with its protection level, the states and the
  business rules, plus a Mermaid diagram in the design pack's executive
  style or its neutral values. It never invents a rule: what the evidence
  does not show becomes an open question. Inside an SDD change it returns
  text for the phase that owns the artifact; outside one it writes a flow
  document. Use it to pin down how a process works end to end, with its
  exceptions and business rules. Not for drawing a flow already defined
  (diagram-design) or deciding what to build (product-discovery). Triggers:
  "design the functional flow", "functional flow with its exceptions and
  business rules", "map this process end to end with its exceptions",
  "what happens when the payment fails", "who does what in this process".
metadata:
  exo-pack: product
  exo-execution: inline
  exo-permissions: write-specs
---

# functional-flow-designer

## Result

One functional flow that a business owner and an engineer read the same way:

1. **Frame:** the trigger, the goal, the end states, and where the flow starts and stops.
2. **Actors:** each role and each system that takes part, with what it is responsible for.
3. **Main path:** numbered steps, each one an actor doing one thing.
4. **Decisions:** each one a question, with every answer and where it leads.
5. **Exceptions:** what can go wrong at each step, what the actor sees, and how the flow ends or recovers.
6. **Data that travels:** each piece of data, who produces it, who receives it, at which step, and its protection level.
7. **States and rules:** the lifecycle of the main entity when it has one, and the business rules `BR-n` behind the decisions.
8. **Diagram:** Mermaid, mirroring the text, in the executive style: the design pack's contract, or its neutral values.
9. **Open questions:** what the evidence does not answer, each with the default you would assume.

## When

- **On request:** "how does a return work end to end", "map the refund process", "who does what when an order is cancelled".
- **Around an SDD change,** when a flow crosses several actors or systems and the proposal, the spec or the design needs it pinned down (Where the output goes).
- **After discovery:** once skill:product-discovery chose the main user flow, this skill gives it its full detail.
- **Not for:** deciding whether the feature is worth building, or the main user flow of an MVP while discovery shapes it (skill:product-discovery); a diagram of a flow that is already defined, with no exceptions or rules to find (`diagram-design`, pack `design`); the components and their integration, which belong to `sdd-design` or `software-solution`; screen design; the calls inside one service, which go to design.md, Sequence Of Operations.

## Where the output goes

| Context | What you produce | Who writes it |
|---|---|---|
| The person, outside a change | The flow document of `references/flow-template.md` | You, in the answer or in the file the person names (for example `docs/flows/<slug>.md`) |
| A change, in propose | The main flow as one Scope bullet; the exceptions left out, for Out of Scope | `sdd-propose`, in proposal.md |
| A change, in spec | Given/When/Then scenarios for the main path, each decision branch and each exception; the rules as requirement candidates | `sdd-spec`, in spec.md, numbering IDs its way |
| A change, in design | The steps, the exceptions and the data, for Sequence Of Operations, Error Handling and Data Shapes | `sdd-design`, in design.md |

- Never edit an artifact of a phase (`.exo/shared/sdd-phase-common.md`, section C): return the text for the phase that owns it. If the person wants the flow document too, it is a project document, never a file of the change root: write it (for example in `docs/flows/`) with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C), and the phase links it.
- If an earlier artifact contradicts the flow you found in the code, stop and say what disagrees: that fix belongs to the phase that owns the artifact.

## Inputs

1. The request, in the person's words, and any process description, ticket or note they give. Clean pasted tickets, logs and exports first: no secrets, no personal data, no customer identifiers (`.exo/shared/data-protection.md`).
2. `.exo/context.md` and the code behind the flow: routes, handlers, state fields, validations, error messages, scheduled jobs. Cite `path:line` (skill:context-retrieval). For four or more files, delegate the reading (`.exo/shared/sdd-phase-common.md`, section G).
3. In a change: proposal.md, spec.md, and the living specs of the capability (`exo specs list --json`).
4. Memory: `exo mem search "<process>"` for earlier decisions about the same flow (skill:memory-protocol).

## Steps

The document template and a full example are in `references/flow-template.md`; the diagram patterns and styles in `references/mermaid-patterns.md`.

### 1. Frame the flow

Write one line each:

- **Trigger:** what starts it (an actor's intent, an event, a date).
- **Goal:** what the main actor gets when it works.
- **End states:** success, and each way it can end without success.
- **Boundary:** the first and the last step you describe, and what stays outside.

One flow per goal. If two goals appear ("return an item" and "exchange an item"), split them and ask which comes first.

### 2. Name the actors

- Roles, never people: "customer", "support agent", "warehouse operator".
- Systems are actors when they decide, store or send something: the web app, the billing service, a payments provider.
- One line of responsibility per actor.
- Mark external actors: their behavior is a constraint you describe, not something you design.

### 3. Write the main path

- Numbered steps, each `<actor> <verb> <object>`: "Customer submits the return request with the order number."
- One action per step, in the present tense and in the business's words.
- A step the business owner cannot follow needs plainer words; a step an engineer cannot map to behavior needs more detail.
- About 5 to 12 steps. Longer means sub-flows: name each one, keep it as a single step here, and describe it separately.

### 4. Add the decisions

- Each decision is a question with answers that cover every case: "Is the order within the return window?" Yes → step 5; No → E2.
- The rule that decides it becomes `BR-n`, with its source: `path:line`, or a policy the person gave.
- Never pick a threshold, a time limit or an amount yourself. Without a source, the rule is an open question with your default.

### 5. Add the exceptions

For each step, check: invalid input, nothing found, no permission, a repeated or duplicate action, a timeout or an external actor that does not answer, a cancellation, a partial completion. Write each one as `E<n>`:

- the step where it starts;
- what the actor sees;
- how it ends: back to a step, a compensation (undo what was done), or a final state.

Add the empty and first-use states when the flow shows lists or history.

### 6. Trace the data

A table with the data item, who produces it, who receives it, the step, and its level (Public, Internal, Restricted or Critical: `.exo/shared/data-protection.md`, section A).

- Name data by its business meaning ("refund amount", "delivery address"), never with real values.
- Flag every Restricted item that reaches an external actor, and every Critical item that goes beyond its owner: they are questions for the design and the security review, not details.

### 7. States and rules

- When the main entity has a lifecycle (an order, a request, a case), list its states and transitions, each with the step or exception that causes it.
- Every state is reachable, and every state that is not final has a way out.
- Collect the `BR-n` in one list, each with its source or marked as an open question.

### 8. Draw the diagram

Mermaid by default (`references/mermaid-patterns.md`):

- a flowchart with one lane per actor, for a process;
- a sequence diagram, when the flow is mostly messages between systems;
- a state diagram, for the lifecycle of step 7.

The diagram mirrors the text: the same step numbers, decision questions and exception IDs. Keep one diagram to about 20 nodes; split by sub-flow beyond that.

**Style:** one model (`references/mermaid-patterns.md`, Style):

- **With the `design` pack:** its contract `executive-style.md` (in `.exo/shared/`) in full, with the brand of `.exo/brand.json` when the project has one.
- **Without it:** the neutral values of that contract, copied in the reference, with the classes decision, exception, external and final, and the keys of `.exo/brand.json` the reference lists, key by key. Never invent brand colors or fonts.
- **A presentation diagram:** `diagram-design` (pack `design`) can turn the flow into a polished visual. Without it, say `design/diagram-design not installed — applying inline criteria` and deliver the Mermaid diagram.

**Before the diagram leaves the team** (a slide, an external tracker, a vendor), apply `secure-diagram-sanitizer` (pack `security`). Without it, say `security/secure-diagram-sanitizer not installed — applying inline criteria` and remove internal hostnames, IP addresses, URLs, repository and environment names, secrets and personal data from labels and notes.

### 9. Check it with both readers

Read the flow twice:

- **as the business owner:** every step in their words, every rule one they recognize, nothing technical needed to follow it;
- **as the engineer:** every step maps to observable behavior, every decision has its rule, every exception has an ending.

Then the completeness checks:

- every decision branch leads somewhere, and nothing is a dead end;
- every exception ends in a step, a compensation or a final state;
- every actor in the diagram appears in the steps, and every actor in the steps appears in the diagram;
- every data item has a producer and a receiver.

### 10. Questions for the person

In one message, at most five questions, each with why it matters and the default you would assume. Ask before writing when the trigger, the goal or the main actor is unclear. In an unattended run, write the defaults, label them `Assumed:` and list them in your answer (or the envelope notes, inside a change).

## Return

The flow document, in the answer or in the file the person named, then a short summary: the number of steps, decisions and exceptions, the Restricted or Critical data that crosses an actor boundary, and the open questions. An excerpt:

```markdown
## Main path

1. Customer opens a delivered order and asks to return it.
2. Web shop checks the return window (BR-1).
   - Within the window → 3. Outside the window → E2.
3. Customer picks the items and a reason for each.
4. Returns service creates the return and asks the Carrier for a label.
5. Customer receives the label and the drop-off instructions.

## Exceptions

| ID | Starts at | What the actor sees | How it ends |
|---|---|---|---|
| E2 | 2 | "This order can no longer be returned", with the date the window closed | Final state: not returned |
| E3 | 4 | The Carrier does not answer: "We could not create your label; we will email it within a few minutes" | Retried in the background; after three failures a support case opens and the customer is told |
```

## Rules

- **Evidence or a question.** Every rule, limit and step comes from the code, a document or the person. Never present an assumption as a fact.
- **Roles, not people.** No names, emails or customer data in the flow, the diagram or the examples.
- **The text is the source.** The diagram mirrors the text; when they disagree, fix the diagram.
- **Business words in the steps.** Technical detail (endpoints, tables, queues) belongs to the design, not to the flow.
- **Stay in your lane.** No UI design, no component design, no estimates.

## Record

Inside a change, an inline phase records it before its envelope (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes and the orchestrator records it. `activation` is `requested` when the person asked for the flow:

```bash
exo change record <change> --add capabilities_used '{"name": "functional-flow-designer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"functional-flow-designer"'
exo change record <change> --add decisions '{"summary": "Return window rule BR-1 confirmed: 30 days from delivery", "by": "human"}'
```

A degradation (`diagram-design`, `secure-diagram-sanitizer`) is recorded with `"resolution": "none"` and the sentence as `note`. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record; save the rules the person confirmed to memory as skill:memory-protocol says.

## Before you finish

- [ ] The trigger, the goal, the end states and the boundary are written.
- [ ] Every actor is a role or a system, with one line of responsibility.
- [ ] Every decision covers all its answers, and its rule has a source or is an open question.
- [ ] Every exception says what the actor sees and how it ends.
- [ ] Every data item has its level; Restricted and Critical crossings are flagged.
- [ ] The diagram uses the same numbers and IDs as the text, in the style of `references/mermaid-patterns.md`.
- [ ] Nothing was written into another phase's artifact; open questions carry a default.
