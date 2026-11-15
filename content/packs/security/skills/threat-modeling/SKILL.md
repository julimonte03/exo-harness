---
name: threat-modeling
description: >-
  Models the threats of a change at design time with STRIDE: the assets, the
  entry points and the trust boundaries it touches, a data flow diagram in
  text or mermaid, abuse cases, and for each threat its mitigation and its
  residual risk. Writes the threats to design.md, section Risks &
  Mitigations, and from Tier 3 the threat_model gate; the tech_lead role
  accepts the residual risk, never the agent. Use it in the SDD design phase
  when a change adds a new surface, crosses a trust boundary, handles
  sensitive data or money, or whenever the tier has the threat_model gate,
  and when someone asks for a threat model or a security design review.
  Triggers: "threat model", "threat modeling", "STRIDE", "security design
  review", "abuse cases", "trust boundaries", "data flow diagram", "what could
  an attacker do".
metadata:
  exo-pack: security
  exo-execution: inline
  exo-phase: design
  exo-permissions: write-specs
---

# threat-modeling

## Result

- A threat model in `<change-root>/design.md`, section Risks & Mitigations: assets, entry points and trust boundaries, a data flow diagram, the threats with their mitigation and residual risk, and the abuse cases.
- When the tier has the gate: `<change-root>/gates/threat_model.md`, started from `.exo/shared/templates/gate.md`, and `exo speclint <change-root>` passes.
- Outside an SDD change (someone asks for a threat model), the same model goes in the answer, or in the document the person names. No gate.

## When it runs

- **Design phase, Conditional** (`.exo/shared/phase-skill-map.md`, row design): a new surface, a trust boundary, sensitive data or money.
- **Always when the tier has the gate:** `threat_model` in the tier's `governance.gates` (`.exo/config.json`; by default Tier 3 and 4). A gate always runs its skill. A change with nothing to model still gets a short model that says why, and an `APPROVED` gate.
- **Tier 1 and 2** have no design phase. If such a change has one of the triggers, tell the person, or the orchestrator through a `fitness_signal`: the tier may be too low.
- **Again** whenever the design changes after review, so the model and the gate describe the approved design.

## What it writes

- Inside the design phase, which owns design.md (`sdd-design`), this skill writes only the section Risks & Mitigations, under a `### Threat model` heading. Risks that are not threats (a migration, a deadline) stay in the same section, outside that heading.
- The gate file, written by the same session: the design phase runs inline.
- It never touches the other sections of design.md, the spec, the proposal or the code. A threat whose mitigation needs a new file or test is a question for the design (Modules / Files, Test Plan), which the design phase answers.

## Inputs

1. proposal.md, spec.md and exploration.md when present; the design draft (Architecture Overview, Modules / Files, Data Shapes, Sequence Of Operations).
2. `.exo/context.md`: the stack, the deployment, the identity provider, the existing security controls.
3. The code at the entry points the change touches. Read 1 to 3 files inline; for 4 or more, delegate the reading to `sdd-explorer` (`.exo/shared/sdd-phase-common.md`, section G).
4. The level of each piece of data, with skill:data-classification and the matrix of `.exo/shared/data-protection.md`.

## Steps

The questions per STRIDE category, the rating matrix and the patterns are in `references/stride.md`. A complete example is in `references/threat-model-example.md`.

1. **Scope.** One or two sentences: what the change adds or modifies, and what is out of the model.
2. **Assets.** What is worth protecting: data (with its level: Public, Internal, Restricted, Critical), money, accounts, capabilities (sending emails, approving payments), availability of a service.
3. **Entry points.** Every way in that the change adds or changes: routes, message consumers, file imports, webhooks, scheduled jobs, admin screens, CLI commands, callbacks from third parties. For each, who can reach it: anyone, an authenticated user, an admin, an internal service.
4. **Trust boundaries.** Where the level of trust changes: internet to service, service to database, service to a third party, user to admin, tenant to tenant, process to file system, content to a model.
5. **Data flow diagram.** The slice of the system the change touches: external entities, processes, data stores, flows with their data, and the boundaries. Mermaid when the project renders it; otherwise text.
6. **Threats.** STRIDE per element, for each element that a flow across a boundary reaches. Keep only threats with a concrete path ("a user of tenant A reads tenant B's invoices by changing the ID"), never the generic list.
7. **Abuse cases.** At least one per entry point that crosses a boundary: `As <attacker>, I <action> through <entry point> to <goal>`. Each one names the threats it exercises.
8. **Rate** each threat: likelihood and impact give the risk (`references/stride.md`).
9. **Mitigate.** A concrete control and where it lands: a file of Modules / Files and the test that proves it in the Test Plan. Prefer the controls of skill:secure-coding-baseline and cite their IDs (`SCB-3`). In Tier 4, each threat also gets a negative test (skill:test-strategy).
10. **Residual risk.** Rate the threat again with the mitigation in place (`references/stride.md`, Rating): a mitigation lowers the likelihood, a design change the impact, and only a mitigation that removes the attack path with a test that proves it brings a High impact down to Low. Say what remains and why it is acceptable, or that it is not.

## Write it into design.md

```markdown
## Risks & Mitigations

### Threat model

**Scope:** customers upload invoices as PDF; a worker parses them into orders.

**Assets:** invoice files (Restricted: personal data), order records (Internal), the parser worker's availability.

**Entry points and trust boundaries:** POST /invoices and GET /invoices/{id} (authenticated customers; internet → service); the parser reads from object storage (service → storage).

**Data flow:** (mermaid diagram, see references/threat-model-example.md)

| ID | STRIDE | Element | Threat | Likelihood | Impact | Mitigation | Residual |
|---|---|---|---|---|---|---|---|
| TM-1 | Information disclosure | GET /invoices/{id} | A customer reads another customer's invoice by changing the ID | High | High | Load by ID and owner from the session (SCB-3); test_rejects_other_customers_invoice | Low |
| TM-2 | Denial of service | Parser worker | A crafted PDF exhausts memory | Medium | Medium | Size limit, page limit and a parser timeout (SCB-1); test_rejects_oversized_pdf | Medium |

**Abuse cases:**
- As a customer, I change the invoice ID in the URL to read other customers' invoices (TM-1).
- As an attacker with an account, I upload a decompression-bomb PDF to stop invoice processing (TM-2).
```

- **Threat IDs are `TM-n`.** Never `S-n`, which is a scenario ID that speclint checks against the spec, nor `T-n`, which is a test case of test-spec.md.
- **Name tests as the Test Plan names them,** so the verify can follow each mitigation to its test.
- **No real data:** synthetic names, `example.com`, placeholders.

## Residual risk and who accepts it

- The `tech_lead` role (`governance.roles` in `.exo/config.json`) accepts the residual risk. The agent proposes the rating and never accepts a risk.
- A residual risk of Medium or higher needs that acceptance explicitly: the gate asks for it, and the tech_lead gives it in the PR, where they own the specs folder through CODEOWNERS (`.exo/shared/ci-and-review.md`, section E), or sends the design back.
- A Low residual risk is accepted with the design: it stays visible in design.md for the same review.
- When the person tells you the tech_lead accepted a risk, record it as a decision with `"by": "human"`, naming the threat IDs.

## The threat_model gate

One row per threat. Severity is the **residual** risk; File:line is the element's code (`path:line`), or the file of Modules / Files followed by `(planned)` when it does not exist yet; Finding is the threat and its mitigation; Rule/OWASP is the STRIDE category with the OWASP category or CWE that fits.

```markdown
# Gate: threat_model

<!-- exo-gate:threat_model -->

## Verdict

APPROVED: every threat has a mitigation in the plan; TM-2 keeps a Medium residual risk for the tech_lead to accept.

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| Low | src/invoices/api.py:34 | TM-1: cross-customer read by ID; mitigated by the owner filter and its test | Information disclosure, A01:2021, CWE-639 |
| Medium | src/invoices/parser.py (planned) | TM-2: memory exhaustion with a crafted PDF; mitigated by size, page and time limits, a slow parse can still delay the queue | Denial of service, CWE-400 |

## Approval

Requires tech_lead approval: yes
Source: skill threat-modeling
```

- **Verdict:** `APPROVED` when every threat has a mitigation that lands in the plan and no residual risk is High or Critical. `ESCALATED` when a threat has no mitigation, a residual risk is High or Critical, or part of the change could not be modeled (say what).
- **Requires tech_lead approval:** `yes` when the verdict is `ESCALATED` or any residual risk is Medium or higher; `no` when every residual risk is Low.
- **Nothing to model:** one row, `| None | — | No new entry point, trust boundary or sensitive data | — |`, and `APPROVED` with that reason.
- A gate that is not `APPROVED` needs the `tech_lead` role; in an unattended run, do not stop: leave it `ESCALATED` and say so. `exo gate publish` turns it into one PR comment (`.exo/shared/ci-and-review.md`, section D).

## After the model

- In Tier 3 and 4 the design phase runs `judge-security` afterwards, which reuses these criteria. An accepted finding updates the model and the gate.
- skill:security-code-review checks in verify that each mitigation that lands in the code is there.

## Record

Before the design envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "threat-modeling", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"threat-modeling"'
exo change record <change> --add gates '{"name": "threat_model", "status": "pass", "detail": "2 threats; TM-2 residual Medium"}'
exo change record <change> --add decisions '{"summary": "Residual risk of TM-2 (Medium) accepted", "rationale": "the queue retries and alerts after 5 minutes", "by": "human"}'
```

The gate status is `pass` for `APPROVED` and `fail` for `ESCALATED`, and `waived` once the `tech_lead` accepts an `ESCALATED` gate; record it once the gate file is final.
