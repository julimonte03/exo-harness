---
name: software-solution
description: >-
  Designs the macro-architecture of a software solution, in regulated and
  non-regulated environments: the context and its boundaries, the quality
  drivers and constraints, two or three real options with their trade-offs
  and a recommendation, then, for the option chosen, the components,
  integration, data, security, operation, cost and risks. Inside an SDD
  change it is the design conditional for large architectures: it returns
  the Architecture Overview for sdd-design to write into design.md; outside
  a change it writes its own solution document. Use it when a change creates
  a system or a service, spans several components or teams, adds an
  external integration or a data store, handles regulated data, or when
  someone asks for a solution architecture or to compare architectural
  options. Triggers: "design the architecture", "solution
  architecture for", "compare architecture options", "how should we build
  this system", "high-level design", "macro architecture", "architecture
  for a regulated environment".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-specs
---

# software-solution

## Result

- **The frame:** the problem, the scope, the regime (regulated or not), three to five quality drivers with a measure, the constraints and the assumptions.
- **A context view:** actors, external systems, the system boundary, the trust boundaries and the data flows with their protection level, as a Mermaid diagram.
- **Two or three options** compared against the drivers, with a recommendation, what it gives up, and the person's decision.
- **The chosen option in detail:** components and responsibilities, integration points, data, security, operation, cost and a risk register.
- **Where it lands:** inside a change, text for `sdd-design` (Where the output goes); outside one, a solution document (`references/solution-document.md`).

## When

- **SDD conditional in design,** for a large architecture (`.exo/shared/phase-skill-map.md`, row design): a new system or service; several components, services or teams; a new integration with an external system; a new data store or a data migration; regulated or Restricted data crossing a boundary; demanding availability, volume or latency targets.
- **On request:** "design the architecture for ...", "compare these options", "review this architecture before we grow it".
- **Not for:** a change inside one module, where `sdd-design` alone is enough; a single decision, which is a decision record (`architecture-decision-record`, pack `design`); a code review (`harness-review`, pack `quality`); UI design; the detailed module design, which `sdd-design` owns.

## Where the output goes

| Context | What you produce | Who writes it |
|---|---|---|
| A change, design phase | The Architecture Overview text, and input for Data Shapes, Error Handling, Migration / Backwards Compatibility and Risks & Mitigations | `sdd-design`, in design.md |
| Outside a change | The solution document | You, in the file the person names (default `docs/architecture/<slug>.md`) |
| A decision that is hard to reverse | A draft decision record | `architecture-decision-record` (pack `design`), after the person approves its text |

- Never write design.md or any other artifact of a phase (`.exo/shared/sdd-phase-common.md`, section C). If the person also wants the full solution document during a change, write it outside the change folder; `sdd-design` links it from the Architecture Overview.
- Without `architecture-decision-record`, say `design/architecture-decision-record not installed — applying inline criteria` and apply its row of the map: propose a short record (status, context, decision, alternatives, consequences) for the project's ADR folder, written once the person approves its text.

## Inputs

1. **The problem and the scope:** the request; in a change, proposal.md and spec.md (`exo change status <change> --json`).
2. **What exists:** `.exo/context.md`, the code the solution touches (`path:line`, skill:context-retrieval), the project's decision records and the living specs (`exo specs list --json`). For four or more files, delegate the reading to `sdd-explorer` (`.exo/shared/sdd-phase-common.md`, section G); without subagents, read in small batches and summarize as you go.
3. **The constraints the person knows:** regulation and audits, mandated platforms or vendors, budget, dates, the team's skills, existing contracts.
4. **Data protection:** `.exo/shared/data-protection.md` and `data_protection` in `.exo/config.json`.
5. **Memory:** `exo mem search "architecture"` and the system's name, for earlier decisions (skill:memory-protocol).

## Steps

The detail of each step is in the references:

| Steps | Reference |
|---|---|
| 1 to 4 | `references/context-and-drivers.md` |
| 5 and 6 | `references/options-and-tradeoffs.md` |
| 7 and 8 | `references/integration-and-data.md` |
| 2 and 9 | `references/security-and-compliance.md` |
| 10 to 12 | `references/operations-and-cost.md` |
| 13 | `references/solution-document.md` |

### 1. Frame the problem

The problem in two lines, the scope and what is out of it, the decision the architecture must make possible, how long it must last, and the stakeholders as roles.

### 2. Decide the regime

- Ask whether the system or its data is subject to regulation or audit obligations (financial services, health, personal data protection law, public sector, card payments, contractual audits).
- **Regulated:** add the controls of `references/security-and-compliance.md` (traceability, segregation of duties, audit trail, residency, retention, change control, evidence).
- **Not regulated:** the security baseline only.
- Nobody answers and Restricted data is involved: treat it as regulated and label it `Assumed:`. Never state that a specific regulation applies without the person confirming it.

### 3. Set the drivers and constraints

- Three to five **quality drivers** as scenarios with a measure: "with 2,000 orders a minute at peak, 99% of checkouts answer within 800 ms". The measure comes from the person or the spec; otherwise propose one and label it a proposal.
- **Constraints:** what is already fixed (platform, language, vendor, hosting, regulation, budget, dates, team).
- **Assumptions,** each with how and when it gets checked.

### 4. Draw the context

Actors (roles), external systems, the boundary of the solution, the trust boundaries, and the data flows with their level (Public, Internal, Restricted, Critical). A Mermaid flowchart; no real hostnames, IP addresses or URLs in it.

### 5. Build the options

- Two or three real options. Always include the simplest one that could meet the drivers (often: extend what exists) and, when it fits, a managed or bought one.
- Each option: its components and responsibilities, how it meets each driver, what it costs to build and to run, and what it makes hard later.
- No straw men: an option you would never recommend is not an option.

### 6. Compare and recommend

- A matrix: the drivers, weighted with the person, against the options; plus reversibility, cost and risk.
- The recommendation, the two or three reasons that decide it, and what it gives up.
- **Checkpoint:** show the context, the options and the recommendation, and ask the person to choose before you detail anything. In an unattended run, detail the recommendation and label the choice `Assumed:`.
- A choice that is hard to reverse becomes a decision record (Where the output goes).

### 7. Detail the components and integration

- Each component: its responsibility in one sentence, its owner (team or role), the data it owns, and its interfaces.
- Each integration point: the style (request and response, messages or events, batch, stream), the contract and its versioning, failure handling (timeouts, retries with backoff, idempotency, dead letters) and the consistency it offers.

### 8. Place the data

- One writer per data set; where each one lives; its level; residency; retention and deletion; personal data kept to the minimum; migrations; copies for reporting.
- Apply `data-classification` (pack `security`). Without it, say `security/data-classification not installed — applying inline criteria` and apply its row of the map.

### 9. Secure it

- Identity and access (people and services), the authorization model, secrets management, encryption in transit and at rest, audit logging, network boundaries, and the supply chain of dependencies.
- **Threats:** `threat-modeling` (pack `security`) is Required in design from Tier 3; hand it the context view and the trust boundaries. Outside a change, apply it, or say `security/threat-modeling not installed — applying inline criteria` and apply its row of the map.

### 10. Plan the operation

Deployment and environments, the release strategy, observability (logs, metrics, traces and a few service level objectives with targets from the person), resilience (failure modes, recovery time and recovery point objectives, backups that are restored in tests), capacity, and the runbooks that must exist.

### 11. Estimate the cost

The cost drivers (compute, storage, data transfer, licenses, operations work), an order of magnitude per option, a unit cost (per transaction, per customer), and guardrails (budgets and alerts). Never invent prices: use the figures the person gives; otherwise compare options as low, medium or high and say so.

### 12. Register the risks

Each risk with its likelihood, impact, mitigation and owner role. The top ones go to Risks & Mitigations through `sdd-design`.

### 13. Deliver

- **Inside a change:** return the text blocks of `references/solution-document.md` (Inside a change) for `sdd-design`, and the draft decision records.
- **Outside a change:** write the solution document where the person says.
- **To the person:** the recommendation, the main trade-off, the top three risks, and the decisions still open.

## Return

Inside a change, the Architecture Overview text for `sdd-design` starts like this:

```markdown
## Architecture Overview

**Option chosen:** B, a returns service with its own store, fed by order events (see the comparison below; decided by the person).

| Component | Responsibility | Owner | Owns data |
|---|---|---|---|
| Web shop | Shows orders and collects return requests | web team | none new |
| Returns service | Creates returns, labels and refund requests | delivery team | returns (Internal), refund requests (Restricted) |
| Carrier (external) | Issues labels and scans parcels | vendor | none of ours |

Integration: the web shop calls the returns service synchronously (REST, versioned path); the returns service consumes `OrderDelivered` events and publishes `ReturnReceived`; refunds go to the payments provider with an idempotency key per return.

Why B over A (extend the order service): it keeps the order service's release cycle untouched and isolates the Restricted refund data; it costs one more deployable and an event consumer.
```

## Rules

- **Evidence or a question.** Volumes, targets, prices and obligations come from the person, the spec or the code; the rest is a labeled proposal or an open question.
- **The simplest option that meets the drivers.** No technology for its own sake, and no distribution the drivers do not need.
- **The person chooses** the option; you recommend and record.
- **Stay in your lane.** No code, no edits to design.md or other phase artifacts, no module-level design.
- **Clean diagrams and documents:** no secrets, personal data, real hostnames, IP addresses or internal URLs when they leave the team; every Restricted flow flagged.
- **Never claim compliance.** Say the design supports a control and what evidence it produces; the organization's compliance function confirms it.

## Record

Inside a change, before the design envelope (`.exo/shared/capability-attribution.md`); `activation` is `auto` when the phase map loaded it:

```bash
exo change record <change> --add capabilities_used '{"name": "software-solution", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"software-solution"'
exo change record <change> --add decisions '{"summary": "Architecture: option B, returns service fed by order events", "rationale": "isolates refund data, no change to the order release cycle", "by": "human"}'
```

A degradation is recorded with `"resolution": "none"` and its sentence as `note`. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change, save the decision to memory as skill:memory-protocol says.

## Before you finish

- [ ] The regime is decided (or assumed and labeled), and the drivers have measures or labeled proposals.
- [ ] The context view shows the boundaries, the trust boundaries and the data levels.
- [ ] Two or three real options were compared, and the person chose one (or the choice is labeled `Assumed:`).
- [ ] Every component has one responsibility and an owner; every integration point says how it fails.
- [ ] Data, security, operation, cost and risks are covered for the chosen option.
- [ ] Inside a change, nothing was written into design.md; the text went to `sdd-design`.
- [ ] Hard-to-reverse decisions have draft records; nothing claims compliance.
