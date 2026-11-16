---
name: re-adoption-plan
description: >-
  Closes the adoption of an existing project with the person (R6): walks
  every recovered capability with them and marks it as-is-validated only with
  their explicit approval, recording their corrections in the spec; finds the
  adoption gaps (test runner, linters, CI, git hooks, CODEOWNERS, minimum
  docs, commit conventions, secret ignores, ADRs, the agent configuration the
  repository already has, and the test baseline) and writes them to
  .exo/discovery/adoption-backlog.md, one item per gap with its evidence and a
  suggested tier, with characterization tests first for critical
  capabilities; and creates an SDD change through sdd-new only for the items
  the person confirms. Runs inline and interactive only, after the audit of
  exo-adopt. Triggers: "validate the capabilities", "adoption plan",
  "adoption backlog", "what is missing to adopt this repo",
  "re-adoption-plan".
metadata:
  exo-pack: discovery
  exo-execution: inline
  exo-permissions: write-specs+tests
---

# re-adoption-plan

## Result

- Every as-is capability walked with the person: validated (`Status: as-is-validated`, with its corrections recorded), corrected and still `as-is`, or left for later with the reason.
- `.exo/discovery/adoption-backlog.md`, one item per gap, each with its evidence, a suggested tier and a status.
- One SDD change per item the person confirmed, created through `sdd-new`, and nothing more: no code, configuration, tests or docs of the project are changed here. Those are the changes' work.

`.exo/shared/discovery-contract.md`, sections G and H, rules this skill. When they disagree, the contract wins. The checklist of gaps and the format of the backlog are in `references/gaps.md`.

## Before you start

1. **Interactive only.** Every step needs the person. In an unattended run, stop here and report what is ready for them.
2. `exo discover status --json`: no `outside_changes`, and every unit `done`. `.exo/discovery/coverage.md` exists. A capability it still flags (below 90 %, or too many unverifiable claims) already had its two rounds in exo-adopt: show the person its precision before they validate it.
3. **Pending approvals.** If `.exo/discovery/pending-approval.md` exists (wiki sections or ADRs that `re-synthesize` proposed in an unattended run), walk it first: show each entry, write the approved ones to their target as skill:re-synthesize says, and remove each entry once it is decided. Delete the file when it is empty.

## 1. Validate each capability

`exo specs list --json` lists the capabilities and their status. Take the `as-is` ones one at a time, critical ones first (see section 3).

1. **Show** its Purpose, each FR (ID, title, text, evidence), its precision in `coverage.md` with the verdicts of its sampled FRs in `.exo/discovery/audit.json`, and its open questions in `.exo/discovery/open-questions.md`.
2. **Ask,** in the person's language: "Is this what `<capability>` does today? Confirm it, or tell me what is wrong."
3. **Apply the corrections in the spec,** by kind:

   | The person says | You do |
   |---|---|
   | The spec misreads the code | Read the cited lines again, and rewrite the FR as the code behaves, with its evidence |
   | The code is wrong (a bug they recognize) | Keep the FR as the code behaves (it is as-is) and add the sentence `Known defect: <what>.`; the fix becomes a backlog item that cites the FR |
   | An FR is not real behavior (dead code, an unused path) | Move it to `## Removed Requirements` with its heading and a `Reason:` line, so its ID is not reused |
   | A behavior is missing | Look for it in the code. With evidence, add an FR with the next free number; without it, it is an open question, not an FR |
   | They do not know | It stays an open question; the FR stays as it is |

4. **Validate only on an explicit yes** for that capability, such as "yes, validate it" (or several capabilities they name one by one). Then:
   - change `Status: as-is` to `Status: as-is-validated`;
   - add the preamble line `Validated: <YYYY-MM-DD>; corrections: <FR IDs, or none>`, before `## Purpose`;
   - run `exo speclint` on the spec.

   Silence, "probably", "later" or a general "looks good" over several capabilities is not a yes: the capability stays `as-is`. Once validated, it changes only by delta, through SDD changes (`exo specs merge` refuses a delta on a capability that is still `as-is`).
5. **Close its questions:** mark the ones answered in `open-questions.md`, with the answer.

## 2. Find the adoption gaps

Go through the checklist of `references/gaps.md`: test runner, linters and formatters, CI, git hooks, CODEOWNERS, minimum docs, commit conventions, secret ignores, ADRs, the agent configuration, and the test baseline.

- **Evidence first:** `inventory.json` (tests, CI, configuration files, manifests, sensitive files, `adr_dir_exists`), the files at the root of the repository, `.gitignore`, `git log --oneline -30`, `.exo/config.json`, `.exo/discovery/debt.md`. Read-only git commands only.
- **The agent configuration the repository already has** (other agents' rule files, instructions, settings): load `context-config-audit` (pack `core`) and turn each of its findings into an item. A missing `core` skill is an incomplete install: say so, suggest `exo doctor` and `exo sync`, and go on with the rest.
- **The debt that blocks adoption** (a hard-coded credential, a critical path without tests) becomes items too; the rest stays in `debt.md`.
- **A credential in the code** is told to the person at once, not only as an item: removing it from the code and rotating it cannot wait.

### The test baseline

Discovery never ran the project's tests (contract, section A). Measuring them is an item, and running them needs the person's confirmation:

1. Find the test command in the manifests' scripts or the CI configuration, and say it with how long it may take and what it needs (a database, the network).
2. Ask: "May I run `<command>` once to measure the baseline?" Run it only on a yes.
3. Write the result in the item: passed, failed and skipped counts, and the time. Do not fix any failure here: failing tests are items of their own.
4. `exo discover status --json` afterwards: if the run left files outside discovery's paths, tell the person.

## 3. Characterization tests first for critical capabilities

- **Critical:** a capability whose units have criticality words in `plan.json` (authentication, payments, security, personal data), whose FRs the sample marked `critical`, or that the person calls critical. These are the Tier 3 and 4 components.
- **For each one, before any other item that touches it,** add an item: characterization tests that pin today's behavior, defects included, starting with the FRs without a scenario and the gaps of the units' Tests sections. They change no behavior, so they can catch whatever a later change breaks.

## 4. Write the backlog

`.exo/discovery/adoption-backlog.md`, in the format of `references/gaps.md`:

- one item per gap, `ADOPT-<n>`, with what is missing, its evidence, why it matters, the change it proposes, a suggested tier and its status;
- characterization tests of critical capabilities first, then the rest in the order the person prefers;
- the suggested tier is a hint: `sdd-new` classifies each change with `risk-tiering`.

Show the person the backlog and ask which items to start.

## 5. Create the confirmed changes

- **Only the items the person confirms,** one at a time, with `sdd-new`: it names the change, asks for a ticket when the project uses them, creates it with `exo change new`, classifies its risk and stops at its approval gate. Give it the item's text as the request.
- Write the change's name in the item's status. Never start implementing it here: each change follows its own cycle and gates.
- The changes' folders are outside discovery's paths, so `exo discover status` lists them from now on: that is expected after R6.

## Before you finish

- `exo speclint` passes on every spec you touched (warnings are fine).
- Tell the person:
  - which capabilities were validated, and with which corrections;
  - which stay `as-is`, and why;
  - the backlog items, and the changes created;
  - the open questions that still need them.
- Commit `.exo/discovery/` and the specs only when the person asks (skill:work-unit-commits), for example `docs(discovery): validate the room-booking capability`.
