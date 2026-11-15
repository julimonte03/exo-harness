---
name: sdd-verify
description: >-
  Verifies an implemented SDD change in a fresh context: checks the code and
  the tests against the spec delta, the design and the tasks, runs the
  project's tests, and returns verify-record.md with a Verdict of ready,
  needs-rework or blocked and its Gate summary. Read-only apart from running
  the tests, lint and build. Runs in the sdd-verifier subagent; fresh context
  is mandatory in Tier 3 and 4. Use it after sdd-apply, when the person asks
  to verify, review or check a change before its PR, or runs /sdd-verify, and
  when a new session starts from a change's handoff.md to verify it.
metadata:
  exo-pack: sdd
  exo-execution: subagent
  exo-subagent: sdd-verifier
  exo-phase: verify
  exo-permissions: read-only+tests
---

# sdd-verify

## Result

- The full text of `verify-record.md`, started from `.exo/shared/templates/verify-record.md`, with exactly its 8 sections in their order: Verdict, Spec Coverage, Scenario Coverage, Issues Found, Tests, Out-of-Scope Drift, Judgment Day Handoff, Gate summary.
- A Verdict (`ready`, `needs-rework` or `blocked`) backed by evidence with `path:line` and by tests that actually ran.
- From Tier 2, the full text of each verify gate the tier requires (`governance.gates` in `.exo/config.json`), each started from `.exo/shared/templates/gate.md` by the skill that owns it: `code_review` (`harness-review`) and `security_review` (`security-code-review`). `contract_check` is the Gate summary of the record itself; `threat_model` comes from design and `secure_coding_check` from apply.
- The record passes `exo speclint`, and the phase ends with the envelope of `.exo/shared/sdd-phase-common.md`, section D.

## Who runs it and who writes the record

| Situation | Runs in | Writes verify-record.md |
|---|---|---|
| With subagents, in every tier | `sdd-verifier`, in fresh context | the orchestrator, verbatim from the verifier's answer |
| Without subagents, Tier 3 and 4 | a new session started from `<change-root>/handoff.md` | that new session |
| Without subagents, Tier 1 and 2, or the person declines a new session | inline, declaring "no isolation" | the same session |

- **Fresh context** means a context that did not write the code. The orchestrator passes only the change name, the change root, the phase, the tier, the `## Skills to load before work` block, the base to diff against, the test, lint and build commands, the implementer's test baseline, and what to return. No conclusions, and nothing from the implementer's reasoning.
- **Fresh context without subagents** (`.exo/shared/agent-capabilities.md`):
  1. The orchestrator writes `<change-root>/handoff.md`: the change name, the phase (`verify`), the files to read (spec, design, tasks, test-spec, and the diff with `git diff <base>`), the test command and what to return. Nothing else.
  2. It asks the person to open a new session of their agent and say: "Run sdd-verify for `<change-name>`; start from `<change-root>/handoff.md`."
  3. The new session runs this skill from the handoff file, writes verify-record.md, records its work, and deletes handoff.md: it is not an artifact of the change.
- **Inline in Tier 4** needs the person's explicit approval, recorded as a decision in the AI Usage Record. Inline, say in the Tests section that the verify did not run in an isolated context.

## Permissions

- Read-only. Run only the test, lint and build commands of `.exo/context.md` or of the delegation, and read-only git (`git diff`, `git log`, `git show`, `git status`).
- Never change a file: no edits, no `git stash`, `checkout`, `reset` or `commit`, no formatter or linter in fix mode, no dependency installs, no snapshot updates. The caches the tools write on their own are fine.
- If a check can only be done by changing something, do not do it: report the check as not done and set the Verdict accordingly.
- A verifier never launches another subagent.

## Load the skills

Section A, with the verify row of `.exo/shared/phase-skill-map.md`, each `SKILL.md` read in full:

- **Required:** `harness-review`. When it is not installed, say `quality/harness-review not installed — applying inline criteria` and apply them: re-read the diff against the spec and the tasks; every scenario has a passing test, nothing is outside the scope, there are no debug leftovers, and the tests and linters pass with the exact commands.
- **Conditional:** `accessibility-audit` when the diff touches UI; `security-scan-node` or `security-scan-jkp` when a dependency or a lockfile changes; `skill-reviewer` when the diff adds or changes a skill. Each degrades with its inline criteria from the same map.
- A gate skill that degrades still produces its gate: without `harness-review`, write `code_review` from its inline criteria.
- **Gate skills:** the ones whose verify gate the tier requires, from the Gates table of the map: `security-code-review` from Tier 3. They count toward the limit of 5.

## Check

1. **Read** the artifacts the tier has: proposal.md, spec.md, design.md, tasks.md, test-spec.md. Then the diff (`git diff <base>`), and the changed files themselves, not only their hunks. Read in batches and take notes as you go.
2. **Spec Coverage.** Every ADDED and MODIFIED requirement has a test that proves it. For a REMOVED requirement, the behavior is gone and no test still expects it.
3. **Scenario Coverage.** Every `S-n` has the test that design.md's Test Plan names (or test-spec.md in Tier 2); the test exists, asserts the scenario's Then, and passes. A test that would pass without the behavior does not cover anything.
4. **Tasks.** Every box of tasks.md is ticked, and the work of each ticked task is in the diff. In Tier 1 and 2, compare against the proposal's Scope.
5. **Design.** The files match Modules / Files, and Error Handling and the mitigations of Risks & Mitigations are implemented.
6. **Tests.** Run the exact test command, then the lint and the build when `.exo/context.md` has them. A failure is pre-existing only with evidence: the implementer's baseline in the delegation, or the same failure on the base branch in CI. Never switch branches to find out.
7. **Drift.** Every changed file or hunk that no task (or, in Tier 1 and 2, the proposal's Scope) explains is drift: unrelated refactors or formatting, debug leftovers, dependencies the plan does not name.
8. **Criteria.** Apply `harness-review` and the Conditionals that loaded.

Back every finding with `path:line`. What you could not check goes in Issues Found, with the reason.

**Tier 1 is the light verify:** the same record and the same checks against the proposal, without judges. Without spec.md, Spec Coverage and Scenario Coverage say so (`No spec.md: the change must not alter behavior`), and the check is that the diff alters no behavior.

## Verdict

| Verdict | When |
|---|---|
| `ready` | Every scenario has a passing test, the tests pass (apart from proven pre-existing failures), there is no Critical or High issue and no drift, and (Tier 3 and 4) every box is ticked. |
| `needs-rework` | Something above fails and `sdd-apply` can fix it inside the plan. |
| `blocked` | The verify cannot conclude or the fix is outside the plan: the tests cannot run, an artifact is missing or contradicts another, the spec or the design is wrong. |

The Verdict section starts with the verdict word, then one sentence of reason (`ready: every scenario passes`). speclint and `exo change status` take the first word as the verdict.

Severities: **Critical** (data loss, a security hole, the main scenario broken), **High** (a scenario not proven or wrong, a mitigation missing), **Medium** (an edge case or an error path not handled), **Low** (naming, readability, leftovers).

## Write the record

| Section | What goes there |
|---|---|
| Verdict | `ready`, `needs-rework` or `blocked`, and one sentence of reason |
| Spec Coverage | each requirement ID -> the test that proves it, and its result |
| Scenario Coverage | each `S-n` -> the test that exercises it, and its result |
| Issues Found | per issue: severity, `path:line`, impact and suggested fix; `None` if nothing |
| Tests | the exact commands, passed and failed counts, the pre-existing failures, and the isolation (subagent, new session, or no isolation) |
| Out-of-Scope Drift | each change outside the plan, with `path:line`; `None` if nothing |
| Judgment Day Handoff | Tier 4: what `judgment-day` must look at (the riskiest files, the risks of design.md to re-check, what you could not verify). Tiers 1 to 3: `N/A` |
| Gate summary | the marker and the table below |

The Gate summary keeps the template's marker and fills its table, one row per issue (a single row saying "No findings" when there are none):

```markdown
<!-- exo-gate:contract_check -->

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | tests/test_login.py:57 | S-3 not proven by its test | S-3 |

Requires tech_lead approval: yes
Source: skill
```

`Requires tech_lead approval` is `yes` when the record has a Critical or High issue or any drift, and `no` otherwise. Cite only requirement and scenario IDs that the delta or the living specs define: speclint checks them. A full example is in `references/verify-record-example.md`.

## Judges (Tier 3 and 4)

The verifier does not run the judges. After it answers, the orchestrator runs `judge-code-reviewer`, `judge-security` and, when the diff touches UI, `judge-frontend`, each one as its own read-only delegation to `sdd-judge`, with the diff (or the list of changed files), spec.md, design.md and tasks.md. A judge that is not installed degrades (`quality/judge-code-reviewer not installed — applying inline criteria`) and the prompt carries its criteria from the map. Without subagents, run each judge inline after the verify, as a separate pass, and say "no isolation".

Each judge gets the first free ID of its prefix (from `exo change followups <change> --status all`), and the orchestrator records each finding with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F). The person decides on each finding: one to fix sends the change back to apply and then to verify again, and is marked with `--fixed <id>` once fixed; a dismissed one goes to `dismissed_followups` with its `id`. The change does not go to archive while a finding is undecided.

**A risk the `tech_lead` accepts.** When the `tech_lead` role decides not to fix an open Critical or High issue or gate finding, the orchestrator records that decision (`dismissed_followups` with the finding's `id`, or a decision with `"by": "human"`) and passes it to the next verify as data, not as a conclusion. The verifier keeps the finding in Issues Found, marked `accepted by tech_lead` with the reference, and it does not block `ready`; the gate that reported it stays `ESCALATED` with `Requires tech_lead approval: yes`, so the PR shows it.

## After the verifier answers

The orchestrator, or the session that ran the verify inline:

1. Writes the text verbatim to `<change-root>/verify-record.md`, and each gate text verbatim to `<change-root>/gates/<gate>.md`.
2. Runs `exo speclint <change-root>`. If the record or a gate fails, it sends the errors back to the verifier and asks for a corrected text; it never edits the findings, the Verdict or a gate verdict itself.
3. Records the work (below), shows the Verdict and the issues to the person, and follows section H.

## Record

Before the envelope (`.exo/shared/capability-attribution.md`). A subagent reports its skill resolution in the notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-verify", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add capabilities_used '{"name": "sdd-verifier", "type": "subagent", "activation": "auto"}'
exo change record <change> --add capabilities_used '{"name": "harness-review", "type": "skill", "activation": "auto", "resolution": "none", "note": "quality/harness-review not installed — applying inline criteria"}'
exo change record <change> --add skills_used '"sdd-verify"'
exo change record <change> --add judges_invoked '{"name": "judge-code-reviewer", "result": "1 Medium finding, fixed"}'
```

In `hybrid` and `memory` persistence, save the record with the topic key `sdd/<change-name>/verify-record`; in every mode, update the state artifact (`.exo/shared/memory-convention.md`), as skill:memory-protocol says.

## End

| Verdict | `status` | `next` |
|---|---|---|
| `ready` | `ok` | `archive` in Tiers 1 to 3; `judgment` in Tier 4 |
| `needs-rework` | `ok` | `apply` (skill:sdd-apply fixes the accepted issues) |
| `blocked` | `blocked` | `verify` once the blocker is gone, or the phase that owns the wrong artifact |

```yaml
status: ok
phase: verify
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/verify-record.md
    summary: "Verdict: needs-rework. 1 High (S-3 not proven), 1 Medium; 48 tests passed"
notes: >-
  Isolation: subagent in fresh context. Skills: sdd-verify (paths-injected),
  harness-review (none: quality/harness-review not installed — applying inline criteria).
  The orchestrator writes the record from this answer.
next: apply
```

With a `ready` Verdict, skill:sdd-archive closes the change.
