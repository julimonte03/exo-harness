---
name: risk-tiering
description: >-
  Classifies the risk tier (1 to 3) of an SDD change before any planning:
  gathers path:line evidence for the 7 fitness dimensions, scores each from 0
  to 3 with the classification rules, and records tier, rule and ceremony with
  exo fitness classify --change. Missing evidence gives Tier 3; lowering a
  recorded tier needs the person's literal confirmation. Use it at the start of
  every change, when a phase returns a fitness_signal, or when someone asks
  "classify the risk", "what tier is this", "risk tier", "fitness", "re-tier
  this change".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: risk
  exo-permissions: read-only+classify
---

# risk-tiering

## Result

- `<change-root>/fitness-assessment.json`, written only by `exo fitness classify --change`: the first tier, an upgrade, or a downgrade the person confirmed in their own words.
- A report: tier, rule, ceremony and judgment-day; the 7 dimensions, each with its score and its evidence (`path:line`, a document line, or the person's words); and what you could not verify.
- The envelope of `.exo/shared/sdd-phase-common.md`, section D.

This skill never edits `fitness-assessment.json` by hand, never writes any other artifact (proposal, spec, code), and never picks the tier itself: the rules do.

## Rules

- **The rules live in `references/classification-rules.md`:** what each dimension measures, the FM rules in order (the first match wins) and the ceremony of each tier. The command applies exactly that table; your job is honest scores.
- **Evidence first.** Every score points to its evidence. No evidence, no score.
- **Missing evidence gives Tier 3** (rule FM-00). Never guess a low score to save ceremony.
- **Upgrade is automatic; downgrade needs the person.** A tier lower than the recorded one is a downgrade: only the orchestrator decides it, with the person's literal confirmation.
- **Runs inline**, in the orchestrator's session (`.exo/shared/sdd-phase-common.md`, section G). A subagent never classifies: it returns a `fitness_signal`.

## Steps

### 1. Know the change

- `exo change status <change> --json` gives `path` (the change root), `artifacts`, `tier` and `tier_source`.
- `tier_source: assessment` means a tier is recorded: this is a re-classification. Read `fitness-assessment.json` for the previous `evidence` (the scores) and `rule`.
- What the change does: the request, `proposal.md` if it exists, and `.exo/context.md` (areas, owners, critical components, known risks). `data_protection.pii` in `.exo/config.json` lists the personal-data detectors the project turned on, and `.exo/shared/data-protection.md` defines the data levels.

### 2. Gather the evidence

| Dimension | Where to look |
|---|---|
| `blast_radius` | who calls the code: callers of the symbol, routes, consumers, screens and their users |
| `component_criticality` | what the component is (sign-in, payments, persistence, a shared library) and what `.exo/context.md` says about it |
| `security_data_sensitivity` | the data read or written (models, schemas, logs), secrets, authorization checks, new inputs or endpoints |
| `reversibility` | migrations, deletions, calls to third parties (mail, payments, external APIs), published contracts |
| `files_modules_footprint` | the files and modules to touch; `git diff --stat` once there is a diff |
| `test_maturity_gap` | tests for the area, whether they run (CI configuration), paths without tests |
| `regulatory_compliance_impact` | personal or financial data, audit trails, retention, consent, regulatory reports |

- Read one to three files inline. **Four or more: delegate to `sdd-explorer`** (read-only). The prompt gives the change name and root, the request, this table, and asks for facts with `path:line` per dimension, marking `[Unverified]` what it could not check, and **no scores**. You score.
- Without subagents, read in small batches inline and say `no isolation` (`.exo/shared/agent-capabilities.md`).
- Ask the person, in one message, for what only they know: who uses it, which regulation applies, whether a rollback is possible.

### 3. Score

Use the anchors below. Between two values, take the higher one and say why.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `blast_radius` | nothing at runtime (docs, dev scripts) | one feature or screen, few users, a workaround exists | a main flow, many users, or another service depends on it | every user, or several services or flows |
| `component_criticality` | not shipped (tests, tooling) | peripheral feature | important business feature | core: sign-in, payments, persistence, or marked critical in `.exo/context.md` |
| `security_data_sensitivity` | no data, no security surface | internal, non-personal data | personal data, an authenticated endpoint, an authorization rule or a new user input | credentials, secrets, payment, identity or health data, cryptography, or a new internet-facing boundary |
| `reversibility` | revert the commit | revert and redeploy, or flip a flag | needs a data fix or a coordinated rollback (migration, API consumers) | cannot be undone: data deleted or rewritten, messages or money already sent, a published contract |
| `files_modules_footprint` | one file | 2 to 5 files in one module | 6 to 15 files, or 2 to 3 modules | more than 15 files, more than 3 modules, or cross-cutting |
| `test_maturity_gap` | the behavior is tested and the tests run | tests miss paths the change touches | few tests, or only manual checks | no tests, or they do not run |
| `regulatory_compliance_impact` | none | indirect (logs or reports that are not regulated) | regulated data or processes, controls unchanged | changes a regulated control: consent, retention, audit trail, customer identification, regulatory reporting |

**A dimension without evidence stays out of the JSON.** The command then answers FM-00 (Tier 3) and lists it in `errors` as `missing <dimension>`. Say which dimension is missing and what evidence would settle it.

### 4. Classify and record

```bash
exo fitness classify --evidence-json '{"blast_radius": 1, "component_criticality": 1, "security_data_sensitivity": 0, "reversibility": 0, "files_modules_footprint": 1, "test_maturity_gap": 2, "regulatory_compliance_impact": 0}' --change <change> --json
```

- The JSON has exactly the 7 dimensions, integers from 0 to 3, on one line in single quotes. A typo or an unknown key also gives FM-00: fix the JSON, it is not missing evidence.
- In Windows PowerShell 5.1 the inner quotes get lost: write the JSON to a file and pass `--evidence-file <file>` instead of `--evidence-json` (`.exo/shared/sdd-phase-common.md`, section I).
- The output has `tier`, `rule`, `matched_rules`, `ceremony`, `judgment_day`, `errors` and, with `--change`, `assessment` (`previous`, `comparison`: `initial`, `same`, `upgrade` or `downgrade`, and `written`).
- Without `--change` the command only computes: use it to preview a result before recording it.
- **`upgrade`:** recorded at once. Tell the person which ceremony and phases the new tier adds (`.exo/shared/phase-skill-map.md`, Phases per tier).
- **Downgrade:** the command refuses with exit code 1 and records nothing. Ask the person: "The evidence now gives Tier `<new>` (`<rule>`), lower than the recorded Tier `<old>`. That removes `<the ceremony that goes away>`. Do you confirm lowering the tier? Please answer in your own words." Then:
  - they confirm: run the same command with `--confirm-downgrade "<their exact words>"`, copied verbatim, never paraphrased or written by you;
  - they do not confirm, or the answer is unclear: keep the recorded tier and run nothing.
- In automatic mode (`sdd.mode: auto`) a downgrade still stops for the person.

### 5. Handle a `fitness_signal`

Any later phase may return a `fitness_signal` (dimension, evidence, suggested score) when what it found contradicts the tier. The orchestrator handles it with this skill:

1. Check the evidence yourself: open the `path:line` it cites.
2. Start from the recorded scores (`evidence` in `fitness-assessment.json`) and change only the dimensions the evidence supports.
3. Run step 4 again: an upgrade applies at once, a downgrade asks the person.
4. Tell the person what changed for the rest of the cycle, for example that `design.md` and `tasks.md` are now required.

### 6. Report

```text
Tier 2 (FM-20) · ceremony light · no judgment-day · initial
| Dimension | Score | Evidence |
| blast_radius | 1 | only the settings screen calls it (src/ui/settings.tsx:14) |
| test_maturity_gap | 2 | no test covers the export path (tests/test_settings.py has none) |
| ... | | |
Not verified: who uses the CSV export (asked the person).
```

## Record

```bash
exo change record <change> --add capabilities_used '{"name": "risk-tiering", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "exo fitness classify", "type": "command", "activation": "auto"}'
exo change record <change> --add skills_used '"risk-tiering"'
exo change record <change> --add knowledge_used '{"source": "code", "ref": "src/ui/settings.tsx:14"}'
exo change record <change> --add decisions '{"summary": "Tier 3 -> Tier 2 downgrade", "rationale": "4 files, not 20 (git diff --stat)", "by": "human"}'
```

- `activation` is `requested` when the person asked for the classification by name. Add `sdd-explorer` (`"type": "subagent"`) if you delegated.
- `fitness-assessment.json` keeps only the scores, so each `path:line` you relied on goes to `knowledge_used`.
- Every tier change is a decision (`.exo/shared/capability-attribution.md`): an upgrade `by: agent`, a confirmed downgrade `by: human`.

## Envelope

```yaml
status: ok
phase: risk
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/fitness-assessment.json
    summary: Tier 2 (FM-20), ceremony light, initial
notes: >-
  Isolation: no isolation (inline). Skills: risk-tiering (fallback-registry).
  Degraded: none. Evidence: 7 of 7 dimensions.
next: new
```

- `next`: `new` at the start of a change. After a re-classification, the next phase of the new tier (`.exo/shared/sdd-status-contract.md`, Next phase).
- `needs-input`: a downgrade waits for the person's words, or only the person can supply a missing dimension.
- `blocked`: `exo` is not available or the change does not exist.
