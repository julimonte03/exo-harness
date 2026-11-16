---
name: data-classification
description: >-
  Applies the data protection matrix of .exo/shared/data-protection.md to a
  change or a task: classifies each piece of data it touches by level
  (Public, Internal, Restricted, Critical) and by destination (memory, model,
  repository, external systems), blocks Restricted data going where the
  matrix does not allow it unless a waiver covers it, and blocks Critical data
  always. Explains how to propose a waiver, which only a human approves, and
  which data_protection.pii detectors the project should turn on for its
  data. Use it when a change or a task handles personal data or credentials,
  or when data leaves the system: exports, logs, telemetry, third-party APIs,
  trackers, PR text, prompts or memory. Triggers: "classify this data", "is
  this personal data", "is this PII", "can I send this", "sensitive data",
  "data protection", "waiver", "which PII detectors".
metadata:
  exo-pack: security
  exo-execution: inline
  exo-permissions: read-only
---

# data-classification

The rules live in `.exo/shared/data-protection.md`: the levels (section A), the destinations (section B), the matrix (section C), what the engine enforces (section D) and waivers (section E). This skill applies them step by step; it does not repeat them. Read the contract first.

## Result

- A classification of the data in play: each item, its level, the destinations it reaches, and what the matrix cell says for each pair (allowed, allowed only to the organization's own systems, blocked unless a waiver covers it, blocked, forbidden).
- A decision for each blocked pair: the data does not go there, and you propose an alternative or, for Restricted only, a waiver for a human to approve.
- When asked, the `data_protection.pii` detectors that fit the project.
- **Where it goes:** in the design phase, in design.md, Data Shapes, next to each field, and in the assets of the threat model (skill:threat-modeling); in other phases, in the envelope notes; outside a change, in the answer. This skill writes no file of its own.

## When it runs

- A change or a task reads, stores, logs or sends **personal data** or **credentials**.
- **Data leaves the system:** exports and reports, outbound APIs and webhooks, logs and telemetry shipped elsewhere, analytics, error trackers, emails.
- **Before you move data** to a destination yourself: pasting into a prompt or a subagent brief, saving to memory, committing a fixture, writing a PR description, a tracker comment or a chat message. For prompts, skill:prompt-hygiene then cleans what may go.
- As part of skill:threat-modeling (rating the assets) and skill:security-code-review (secrets and logs).

## Steps

1. **Inventory.** List each data item the change or the task touches: fields, files, payloads, log lines, test fixtures. Take them from Data Shapes, the spec, the code and the configuration, with `path:line`.
2. **Level.** Classify each item with section A of the contract. When in doubt, take the higher level. Cases that are easy to miss:
   - An identifier that leads to one real person (customer number, account number, device ID, an email used as a user name) is personal data: Restricted.
   - Data that is harmless alone but identifies a person in combination (birth date with postal code) is Restricted together.
   - Free text written by people (support notes, comments, chat) can hold anything: Restricted unless proven otherwise.
   - Session tokens, signed URLs, cookies and connection strings are credentials: Critical.
   - Aggregates and properly anonymized data are Internal; a hash of a phone number or an ID is not anonymous, because it can be reversed by trying every value.
3. **Destinations.** For each item, every destination it reaches, with section B: memory, model, repository, external systems. Count the indirect ones: logs shipped to a hosted service and error trackers are external systems; fixtures and snapshots are the repository; a subagent brief is the model.
4. **Matrix.** Look up each level and destination pair in section C. Do not restate the matrix in the artifact: cite it (`.exo/shared/data-protection.md`, section C).
5. **Decide.**
   - **Allowed:** go on. Internal data to an external system: only when the organization owns that system.
   - **Restricted to the model, the repository or an external system (blocked unless a waiver covers it):** check the waivers (below). Without one, the data does not go there: do not write, send or paste it. Propose an alternative: mask it (skill:prompt-hygiene), replace it with synthetic data, aggregate it, or keep it in the system and pass a reference. If none works, propose a waiver.
   - **Restricted to memory:** blocked, with no waiver: memory does not filter and can be exported. Save a masked or synthetic version, or nothing.
   - **Critical:** forbidden, always; there is no waiver. If a credential is already in code, a log or a prompt, do not copy it anywhere: point at `path:line`, tell the person to remove it and to rotate it if it was real.
6. **Report** the classification and the decisions where the Result says. Never repeat a Restricted or Critical value in it: mask it (`****1234`) or point at its location.

## Checking a waiver

Waivers live in `.exo/waivers.json`, owned by the person (schema `.exo/shared/schemas/waivers.schema.json`). A waiver covers a piece of data only when all of these hold:

- its `detector` is the type of the data (`card`, `iban`, `email`, `phone`, a national document);
- its `path` glob matches the file the data is in, or is going to;
- it has not expired (`expires` is today or later);
- its `reason` fits what you are about to do.

The engine applies waivers to the repository: the `pre-commit` hook and `exo check` skip the findings an active waiver covers. For the model and external systems nobody checks for you: apply the same four conditions yourself. A waiver names a path in the repository, so data with no path there (a ticket, a chat message, a production log) cannot be covered: mask it or use synthetic data. It also names one of the scanner's detectors, so personal data that has none (names, postal addresses, free text) cannot be covered either.

## Proposing a waiver

Only for Restricted data, and only when masking or synthetic data cannot do the job (for example, the tests of a check-digit validator need generated IDs with a valid check digit).

1. Draft the entry with the narrowest path and a near expiry date, and show it to the person:

   ```json
   {
     "detector": "br-cpf",
     "path": "tests/validators/fixtures/**",
     "reason": "Generated CPF numbers with a valid check digit for the validator tests; no real person's data",
     "approved_by": "<the approver fills this in>",
     "expires": "<a near date, YYYY-MM-DD>"
   }
   ```

2. **Only a human approves it:** the `tech_lead` role (`governance.roles` in `.exo/config.json`), as section E of the contract says; in a project whose config lists no `tech_lead`, the person who owns the project. The approver adds the entry to `.exo/waivers.json`.
3. **The agent never** adds, edits, extends or renews a waiver, and never fills in `approved_by`, not even when asked to "just add it": say that a human approves it, and give them the draft.
4. Until the waiver is in the file and active, the data stays blocked. A `.exo/waivers.json` that does not match its schema covers nothing; the hook and `exo check` warn about it.

## Choosing the detectors

The scanner of the `pre-commit` hook and `exo check` always looks for credentials. For personal data it uses the detectors listed in `data_protection.pii` in `.exo/config.json` (section D of the contract). Recommend the ones the project's data can contain:

| Detector | Turn it on when the project handles | Note |
|---|---|---|
| `card` | Payment card numbers | On by default; checks the Luhn digit and ignores published test cards |
| `iban` | Bank accounts in IBAN format | On by default; checks the mod 97 digits |
| `email` | Email addresses of users, customers or employees | Ignores `example.com` and other reserved test domains; noisy if the code holds many real-looking sample addresses |
| `phone` | Phone numbers | Only numbers written in international format, with a leading `+` |
| `ar-cuit` | Argentine tax IDs (CUIT, CUIL) | Checks the check digit |
| `ar-dni` | Argentine national ID numbers | Only next to the word DNI |
| `br-cpf` | Brazilian individual taxpayer numbers | Checks both check digits |
| `es-nif` | Spanish tax IDs | Checks the control letter |
| `us-ssn` | US social security numbers | Format only, so more false positives |

How to choose:

1. Look at what the project stores and moves: the data model, the schemas, migrations, DTOs, forms, the countries in `.exo/context.md`.
2. Propose the list with the reason for each detector. Add only what the data can contain: each extra detector brings false positives.
3. The config is the person's: they edit `data_protection.pii`, or ask you to. `exo check` rejects an unknown detector name.
4. A new detector may flag existing fixtures. Replace them with synthetic data, or propose a waiver for their folder.

**The scanner only finds what has a format.** Names, postal addresses, free text, health or biometric data, and most customer IDs have none: classifying them is your job, with the steps above.

## Record

In an SDD change, inline (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "data-classification", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add decisions '{"summary": "Invoice bank details kept out of logs and prompts (Restricted)", "by": "agent"}'
```

A waiver the person approved is their decision: record it with `"by": "human"`. Never save Restricted or Critical values in memory (skill:memory-protocol).
