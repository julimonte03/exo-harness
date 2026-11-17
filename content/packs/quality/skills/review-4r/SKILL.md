---
name: review-4r
description: >-
  Runs a 4R review on request: five read-only lenses over the same diff,
  branch or files. R1 Risk (security, data and blast radius), R2
  Readability, R3 Reliability (behavior and tests) and R4 Resilience
  (failure modes, observability, SLOs and rollback) review in parallel; then
  R5 Refuter tries to disprove their findings; then a synthesis by severity
  with one verdict. Uses the existing read-only subagents (sdd-judge, or
  sdd-explorer) and never fixes anything. Inside an SDD change its findings
  are recorded as J4R followups. Not part of the phase map. Use it when
  someone wants a production-readiness review whose findings have been
  challenged. Triggers: "4R review", "four R review", "risk, readability,
  reliability and resilience", "five-lens review", "review with a refuter",
  "challenge the findings", "production readiness review".
metadata:
  exo-pack: quality
  exo-execution: inline
  exo-permissions: read-only+record
---

# review-4r

## Result

- One synthesis: the findings that survived the Refuter, by severity, each with the lens that raised it and what R5 said about it; the refuted findings with their evidence; what was not reviewed; and one verdict, `APPROVED` or `ESCALATED`.
- Inside an SDD change: each surviving finding recorded as a `J4R-n` followup, and the review in the AI Usage Record (`.exo/shared/judge-common.md`, section F). Outside a change: the synthesis only; nothing is written.
- Nothing is fixed. The review advises; the person decides.

## When

- **On request only,** for a diff, a branch, a PR or a set of files: before a release, a risky merge, or when someone wants findings that have been argued against before they reach the team.
- It is not in the phase map, owns no gate, and replaces neither the judges of each phase nor skill:judgment-day.
- **Not for:** a check before committing (skill:pre-commit-review), the review of verify (skill:harness-review), or every judge's angle on a change, product and business included (skill:excellence-committee).

## Contract

`.exo/shared/judge-common.md` rules the lenses and the synthesis: advisory first (A), independence (B), no cascade (C), findings (D, with the code `J4R` when they are recorded in a change), verdict (E) and recording (F).

## Permissions

Read-only: read files, `git status`, `git diff`, `git log`, `exo change status` and `exo change followups`. Inside a change, also `exo change record`. Never edit, stage, commit or fix anything.

## The five lenses

| Lens | The question | Criteria |
|---|---|---|
| R1 Risk | What can this change break, expose or make irreversible? | `references/r1-risk.md` |
| R2 Readability | Can the next person understand and safely change it? | `references/r2-readability.md` |
| R3 Reliability | Does it do what it should, every time, and do the tests prove it? | `references/r3-reliability.md` |
| R4 Resilience | When something around it fails, does it degrade safely, and will anyone know? | `references/r4-resilience.md` |
| R5 Refuter | Which of the findings of R1 to R4 would not survive a hostile reading? | `references/r5-refuter.md` |

Each lens reviews only by its own criteria. R1 to R4 never see each other's findings; R5 sees only theirs.

## 1. Scope

1. **The target:** inside an SDD change, `exo change status <change> --json`, and the diff of the change; a branch or a PR, `git diff <base>...HEAD` against the target branch; uncommitted work, `git diff` and `git status`, reading new files in full.
2. **The stage before** (no cascade): `spec.md`, `design.md` and `tasks.md` inside a change; outside, the ticket or what the person says the change does. Ask once when there is nothing.
3. **The diff text:** the subagents cannot run git. Get the diff and pass its text, or the list of changed files when it is too long.
4. **IDs:** each lens numbers its own findings (`R1-1`, `R4-2`). Inside a change, take the next free `J4R` number from `exo change followups <change> --status all` for the recording.

## 2. R1 to R4, in parallel

- **One read-only delegation per lens, all four launched at the same time,** to `sdd-judge`. When `sdd-judge` is not available, use `sdd-explorer`: both are read-only and ship in the `sdd` pack. Use no other subagent.
- Each prompt follows `references/lens-prompt.md`: this skill's `SKILL.md` path and the lens's criteria file under `## Skills to load before work`, the target, the stage before, and what to return.
- **Never in a prompt:** another lens's findings, the author's explanation or self-assessment, or your own opinion.
- **Without either subagent:** run each lens inline, one at a time, as a separate pass with only its criteria, reading the files again from disk. Write down each pass's findings before you start the next, and say "no isolation" in the synthesis.

## 3. R5, the Refuter

- After R1 to R4 answer, one more read-only delegation, with `references/r5-refuter.md` and the four findings tables exactly as returned: IDs, severities, locations, findings, criteria and fixes. Nothing else from the lenses, and never the author's explanation.
- R5 argues against each finding from evidence and gives it an outcome: `upheld`, `upgraded`, `downgraded`, `refuted`, `duplicate of <ID>` or `cannot tell`. It adds no findings of its own.
- Without subagents, run R5 inline after the other four passes are written down, and treat each finding as a claim to disprove, not as your own.

## 4. Synthesize

1. **Settle each challenge.** Where R5 agrees with the lens, apply its outcome. Where R5 downgrades or refutes, read the cited `path:line` yourself: apply the outcome when the evidence holds; otherwise keep the lens's finding and note why. `cannot tell` keeps the finding, with what would settle it.
2. **Merge duplicates** across lenses: one item listing every lens ID, at the highest of their severities.
3. **Never** lower a finding about secrets or personal data below High, whatever R5 says.
4. **Order** the surviving findings Critical, High, Medium, Low.
5. **Verdict:** `APPROVED` when no surviving finding is Critical or High and nothing needed was left unreviewed; `ESCALATED` otherwise, with the reason in one line.

## When you are a lens

If the delegation made you one of the lenses, you are not the coordinator: read your criteria file in full, review only by it, and return this, then the envelope of `.exo/shared/sdd-phase-common.md`, section D, with `artifacts: []`:

```markdown
# Lens Findings: R4 Resilience on <target>

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| R4-1 | High | src/sync/client.py:31 | The call to the remote service has no timeout, so a slow server hangs the command | R4: timeouts | Pass a timeout and report the failure with what to do next |

## Not reviewed

None.
```

R5 returns a `## Challenges` table instead of Findings: `| ID | Outcome | Evidence (path:line) | Reason |`, one row per finding it received.

## Synthesis

```markdown
# 4R Review: <target>

## Verdict

ESCALATED: R1-1 (High) and R4-1 (High) survived the Refuter.

## Findings by severity

| Severity | IDs | J4R | Lens | path:line | Finding | Suggested fix | Refuter |
|---|---|---|---|---|---|---|---|
| High | R1-1 | J4R-1 | Risk | src/sync/client.py:22 | The access token is printed to the console | Remove the print; never log the token | upheld |
| High | R4-1, R3-2 | J4R-2 | Resilience, Reliability | src/sync/client.py:31 | No timeout on the remote call, and any error becomes a silent 0 | Add a timeout; report the error and exit non-zero | upheld; duplicate merged |
| Low | R2-1 | J4R-3 | Readability | src/sync/client.py:12 | The payload is built from internal attributes | Build it from the documented fields | downgraded from Medium: one call site |

## Refuted

- R3-1 "the store is not saved after sync": refuted, the store is not changed by sync (src/sync/client.py:18 only reads it).

## Not reviewed

None. Isolation: lenses in sdd-judge subagents.
```

## Record

Inside an SDD change only, as `.exo/shared/judge-common.md`, section F, and `.exo/shared/capability-attribution.md` say. Outside a change, record nothing. In Windows PowerShell 5.1, pass each JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

```bash
exo change record <change> --followup '{"id": "J4R-1", "judge": "review-4r", "rule": "R1 Risk: secrets in logs", "severity": "high", "summary": "The access token is printed to the console; remove the print", "location": "src/sync/client.py:22"}'
exo change record <change> --add judges_invoked '{"name": "review-4r", "result": "escalated: J4R-1, J4R-2 open"}'
exo change record <change> --add capabilities_used '{"name": "review-4r", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "sdd-judge", "type": "subagent", "activation": "auto"}'
exo change record <change> --add skills_used '"review-4r"'
```

- Each surviving finding gets the next free `J4R-n`, in the synthesis order; the `rule` names the lens and the criterion. A merged item is one followup. Show the `J4R` numbers next to the lens IDs in the synthesis, in the J4R column; outside a change, write `-` there.
- Refuted findings are not recorded, unless the person keeps one.
- Never dismiss a finding yourself; fixed ones are marked later with `--fixed <id>`. The review is not a phase: no `--phase-done`.

## Before you finish

- R1 to R4 ran independently; R5 saw only their findings tables.
- Every finding is in the synthesis: surviving, merged or refuted with its evidence.
- Secrets and personal data findings stayed at High or above.
- Nothing was edited; inside a change, everything is recorded; outside, nothing is.
