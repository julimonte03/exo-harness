# SDD phase contract

Rules every SDD phase follows, whether the orchestrator delegated it or the agent runs it inline. A phase skill cites the sections it uses; when a phase skill and this contract disagree, this contract wins.

## A. Load the skills

1. Read `.exo/skill-registry.md` to see which skills this project has and where.
2. Find the phase in `.exo/shared/phase-skill-map.md` and pick the skills for the tier: the Required ones, which include the skill of every gate the phase writes; from Tier 2 on, the Conditionals whose trigger applies; and, at any tier, the skills of the conditional gates and of the SPDD overlay when their trigger applies (the map, How to read it). At most 5 skills, counting the map's and the ones the stack router loads; the phase skill itself, `memory-protocol` and `ai-usage-record` do not count.
3. **The anchor.** If `<change-root>/context-anchor.md` exists, read it first and load `context-anchoring`, which then counts as Required: update the anchor with the phase's decisions, assumptions and questions before the phase ends. A subagent only reads it and lists them in its envelope notes; the orchestrator updates the anchor.
4. **Read each `SKILL.md` in full** before working. Do not summarize it from its description.
5. A missing skill degrades as `.exo/shared/skill-resolver.md` says: say so, apply the inline criteria, record it. A missing `core` skill is not a degradation but an incomplete install: say so, suggest `exo doctor` and `exo sync`, and return `blocked`.
6. Without an orchestrator (the person called a phase skill directly), resolve the Required and Conditional skills yourself with the same steps.

## B. Retrieval mode

The mode is `sdd.persistence` in `.exo/config.json`:

| Mode | Artifacts live in | Read previous phases from |
|---|---|---|
| `filesystem` (default) | the change root | the files |
| `memory` | memory only | `exo mem` (`.exo/shared/memory-convention.md`) |
| `hybrid` | the change root, mirrored in memory | the files; memory if a file is missing |
| `none` | nowhere: the conversation only | the conversation |

With `memory` or `none`, `exo check` has nothing on disk to check, and it says so.

## C. Persistence

- **Change root:** `<specs_dir>/[<epic>/]<change-name>/`. `specs_dir` comes from `.exo/config.json` (default `specs`). `exo change new` creates it.
- **Exact file names per phase.** Write only your phase's files, and never edit another phase's artifact. If an earlier artifact is wrong, stop and return `status: needs-input` with what is wrong.

| Phase | Skill | Writes |
|---|---|---|
| risk | `risk-tiering` | `fitness-assessment.json` (through `exo fitness classify --change`) |
| new | `sdd-new` | `proposal.md`; in Tier 1, `spec.md` when the change alters behavior |
| explore | `sdd-explore` | `exploration.md` |
| propose | `sdd-propose` | `proposal.md` (refines the one from `sdd-new`) |
| spec | `sdd-spec` | `spec.md` (delta); in Tier 2 also `test-spec.md` |
| design | `sdd-design` | `design.md`; from Tier 3, `gates/threat_model.md` through `threat-modeling`; with SPDD, `canvas.md` through `reasons-canvas-author` and `gates/prompt_spec_review.md` through `prompt-spec-review` |
| tasks | `sdd-tasks` | `tasks.md` and `test-spec.md` |
| apply | `sdd-apply` | code and tests; ticks the boxes in `tasks.md`; in Tier 4, `gates/secure_coding_check.md` through `secure-coding-baseline`; with SPDD, keeps `canvas.md` in sync through `prompt-code-sync` (the orchestrator's session applies the edits `sdd-implementer` returns) and, after a logic correction, rewrites `gates/prompt_spec_review.md` through `prompt-spec-review`; in Tier 1 and 2, before the first task, `canvas.md` and that gate through `reasons-canvas-author` and `prompt-spec-review`, in the orchestrator's session |
| verify | `sdd-verify` | `verify-record.md`, the verify gates of the tier in `gates/`, and the conditional gates that apply (`accessibility_review`, `prompt_spec_review`) |
| archive | `sdd-archive` | merges the delta into the living specs, moves the change to `<specs_dir>/archive/[<epic>/]YYYY-MM-DD-<change-name>/`, and `pr.md` through `branch-pr` |

  **When the tier rises,** ownership moves with it: from Tier 2 on `sdd-spec` owns `spec.md` and completes the one `sdd-new` wrote; in Tier 3 and 4 `sdd-tasks` completes the `test-spec.md` that `sdd-spec` wrote in Tier 2.

  **Files outside the phases:** `context-anchor.md`, the living record of decisions that `context-anchoring` starts in design or on request, is the only file every later phase updates (section A); and `pr-part-<n>.md`, the bodies of a chain of PRs that `chained-pr` writes. Neither is an artifact of a phase, and no tier requires them.

  **Project documents outside the change root** (diagrams, a solution document, runbooks, SLOs, postmortems, capacity or chaos plans, on-call handoffs, flow documents, decision records): during a change, a skill writes them in any phase, with the person's approval of their text, and only when the plan lists them: design.md, Modules / Files, in Tier 3 and 4; the proposal's Scope in Tier 1 and 2. Listed there, verify does not count them as drift. One the plan does not list goes first to the phase that owns the plan, or to a later change. A document written after verify (a decision record in archive) needs only the person's approval. Outside a change, this rule does not apply.

- **Templates:** start each document from `.exo/shared/templates/` (`proposal.md`, `spec.md`, `design.md`, `canvas.md`, `test-spec.md`, `verify-record.md`, `gate.md`, `pr.md`). `exo speclint <file or change root>` checks them.
- **Mandatory artifacts per tier** (what `exo check` requires):

| Tier | Requires |
|---|---|
| 1 | `proposal.md`; `spec.md` only if the change alters behavior |
| 2 | `proposal.md`, `spec.md`, `test-spec.md` |
| 3 and 4 | `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `test-spec.md` |

  Every tier also needs `ai-usage-record.json` and `fitness-assessment.json`. Without a readable assessment the tier is unknown and Tier 4 rules apply.
- **Gates per tier:** `governance.gates` in `.exo/config.json` lists them; `exo check` requires one `<change-root>/gates/<gate>.md` per gate, from `.exo/shared/templates/gate.md`, except `contract_check`, which is the Gate summary of `verify-record.md`. The skill that writes each gate is in `.exo/shared/phase-skill-map.md`, Gates. A gate written in a read-only subagent comes back as text, and the orchestrator writes it verbatim, like `verify-record.md`.
- **Conditional gates:** `accessibility_review` (UI in the diff) and `prompt_spec_review` (the change has `canvas.md`) do not depend on the tier. `exo check` reviews every gate in `gates/`, and requires `prompt_spec_review` whenever `canvas.md` exists. A project that lists one in `governance.gates` makes it a gate of that tier, and its skill runs in every change of the tier (`.exo/shared/phase-skill-map.md`, Gates).
- **Living specs:** `spec.md` is a delta over `<specs_dir>/capabilities/<capability>/spec.md`, with `## ADDED Requirements`, `## MODIFIED Requirements` and `## REMOVED Requirements`. Requirement IDs are `CAP-<capability>-FR-n` or `CAP-<capability>-NFR-n`; scenarios in the delta are `#### Scenario S-n: <title>` with Given, When and Then. A new requirement takes the next free number of its capability (`exo specs list`); a removed ID is never reused. `exo specs merge <change>` applies the delta.
- **Memory mirror** (`hybrid` and `memory`): save each artifact as `.exo/shared/memory-convention.md` says.

## D. Return envelope

Every phase ends with this block, as the last thing in its answer. Before returning `status: ok`, an inline phase logs itself with `exo change record <change> --phase-done <phase>` (`.exo/shared/sdd-status-contract.md`, The phase log); for a phase that ran in a subagent, the orchestrator does it.

```yaml
status: ok            # ok | needs-input | blocked
phase: spec
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/spec.md
    summary: 2 requirements added, 1 modified
notes: >-
  Isolation: subagent (or "no isolation" when it ran inline).
  Skills: sdd-spec, test-strategy. Degraded: none.
next: design          # the next phase, or "none"
fitness_signal:       # optional: only when the evidence contradicts the tier
  contradicts_tier: true
  dimension: security_data_sensitivity
  evidence: the form stores national ID numbers (src/forms/signup.py:40)
  suggested_score: 3
```

- `needs-input`: you need the person; say exactly what to ask.
- `blocked`: something outside the phase stops you (a failing build you must not touch, a missing permission).
- Any phase may send a `fitness_signal`. Only the orchestrator re-classifies the tier.

## E. Change name and ticket

- **Format:** `[<ticket>-]<slug>`, where the slug is lowercase kebab-case (`add-login`). `exo change new` builds the name, validates it and normalizes the ticket (`AB#123` becomes `AB-123`); never build the folder by hand.
- **Tickets are optional and agnostic.** If `tickets.pattern` in `.exo/config.json` is null, the project has no tickets: do not ask, and commits use Conventional Commits without an ID.
- **With a pattern, ask once:** "Is there a ticket for this change? It looks like `<tickets.example>`. Leave it empty if not." Never infer it from the branch name, the commits or the conversation.
- **An answer that does not match the pattern:** say that it does not match and show the example, then ask once more. If it still does not match, continue without a ticket and say so in the envelope notes. Never invent an ID, and never change the pattern: that is the person's decision in `.exo/config.json`.

## F. Epic

- Only if the project has a ticket pattern. Ask once: "Does this change belong to an epic? Its ID looks like `<tickets.example>`. Leave it empty if not."
- The epic is one folder level: `<specs_dir>/<epic>/<change-name>/`, normalized like the ticket, and never `archive` or `capabilities`. Pass it with `exo change new --epic`.
- Existing folders are never moved to an epic. Change names are unique across epics.

## G. Delegation

- **Who runs each phase:**

  | Phase | Runs in | Writes the artifact |
  |---|---|---|
  | new, propose, spec, design, tasks, archive, status, init | the orchestrator's session (inline), because they talk with the person | the phase itself |
  | risk | inline; `sdd-explorer` gathers the evidence | `exo fitness classify --change` |
  | explore | `sdd-explorer` (read-only) | the orchestrator, from the explorer's answer |
  | apply | `sdd-implementer` | the implementer (code, tests, `tasks.md` boxes) |
  | verify | `sdd-verifier`, in fresh context (read-only, runs the tests) | the orchestrator, from the verifier's answer |
  | judges, judgment-day | `sdd-judge` (read-only) | the orchestrator records the outcome |

  A read-only subagent returns the full text of its document in its answer; it never writes files.
- **Read 1 to 3 files inline; 4 or more, delegate** to `sdd-explorer`. Running tests or a build: delegate it, to `sdd-implementer` within apply and to `sdd-verifier` anywhere else (it runs the test, lint and build commands and changes nothing); use only the four subagents of the pack. Git state commands (`git status`, `git diff --stat`) run inline.
- **Permissions are denied by default.** The explorer and every reviewer are read-only; the implementer writes only what the frozen plan says: `tasks.md` in Tier 3 and 4; in Tier 1 and 2, the proposal's Scope with the spec delta and, in Tier 2, the test-spec. Nobody re-delegates: a subagent never launches another one.
- **Mandatory delegation triggers:**
  1. the 4-file rule above;
  2. writing to more than one file;
  3. before the PR: a fresh-context review and the wiki checkpoint (`.exo/shared/project-wiki-guard.md`);
  4. an incident or a production error;
  5. a long session (about 20 tool calls in the same phase): hand off before the context degrades;
  6. any verify in Tier 3 or 4: it runs in fresh context.
- **Pass skills as paths.** A delegation prompt starts with a `## Skills to load before work` block listing the exact `SKILL.md` paths, and the subagent reports how it resolved them (`.exo/shared/skill-resolver.md`).
- **Recording:** a phase that runs inline records what it used with `exo change record`; a phase that ran in a subagent lists it in its envelope notes and the orchestrator records it. Subagents never run `exo change record`. The phase log (`--phase-done`) is written only for `status: ok`.
- **Without subagents:** see `.exo/shared/agent-capabilities.md`.

## H. Execution mode

- **Interactive (default, `sdd.mode: interactive`):** after each phase, show the summary and ask "Adjust anything or continue?". Do not start the next phase without an answer.
- **Automatic (`sdd.mode: auto`, or when the person asks for it in the conversation):** continue phase by phase, and still stop on `needs-input`, `blocked`, a downgrade, `judgment-day` and before the PR. Rework has a cap: at most two rework rounds; on the next one, stop and ask. A rework round is every return from verify to apply, for the Verdict or for a Critical or High judge finding. Judge findings are decided by severity, and a re-verify reviews the fix (the Judges section of the verify phase skill).
- Artifacts are written in English. Talk to the person in their language.

## I. JSON in the terminal

Several commands take JSON (`exo fitness classify --evidence-json`, `exo change record --add FIELD JSON`). Windows PowerShell 5.1 drops the inner double quotes when it calls a program, and the JSON arrives broken: the evidence becomes unreadable (Tier 4) or the record entry is rejected. In PowerShell 5.1, write the JSON to a file and pass `--evidence-file <file>` or `'@<file>'`, with the quotes, which keep PowerShell from parsing the `@` (`exo change record <change> --add capabilities_used '@entry.json'`). Write that file as UTF-8 (your file-writing tool does; in PowerShell, `Set-Content -Encoding utf8`); UTF-16 with a byte order mark, what `Out-File` writes, works too. A POSIX shell (bash, zsh) and PowerShell 7 pass single-quoted JSON as is.

Quote ticket and epic IDs (`--ticket 'AB#123'`): an unquoted `#` starts a comment in the shell. To remove the tickets of a project, use `exo init --no-tickets`: PowerShell 5.1 drops an empty `''` argument.
