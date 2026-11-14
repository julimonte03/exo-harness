# SDD phase contract

Rules every SDD phase follows, whether the orchestrator delegated it or the agent runs it inline. A phase skill cites the sections it uses; when a phase skill and this contract disagree, this contract wins.

## A. Load the skills

1. Read `.exo/skill-registry.md` to see which skills this project has and where.
2. Find the phase in `.exo/shared/phase-skill-map.md` and pick the skills for the tier: Required, plus the Conditionals whose trigger applies, at most 5.
3. **Read each `SKILL.md` in full** before working. Do not summarize it from its description.
4. A missing skill degrades as `.exo/shared/skill-resolver.md` says: say so, apply the inline criteria, record it.
5. Without an orchestrator (the person called a phase skill directly), resolve the Required and Conditional skills yourself with the same steps.

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
| new | `sdd-new` | `proposal.md`; `spec.md` when the change alters behavior |
| explore | `sdd-explore` | `exploration.md` |
| propose | `sdd-propose` | `proposal.md` (refines the one from `sdd-new`) |
| spec | `sdd-spec` | `spec.md` (delta); in Tier 2 also `test-spec.md` |
| design | `sdd-design` | `design.md` |
| tasks | `sdd-tasks` | `tasks.md` and `test-spec.md` |
| apply | `sdd-apply` | code and tests; ticks the boxes in `tasks.md` |
| verify | `sdd-verify` | `verify-record.md` |
| archive | `sdd-archive` | merges the delta into the living specs and moves the change to `<specs_dir>/archive/[<epic>/]YYYY-MM-DD-<change-name>/` |

- **Templates:** start each document from `.exo/shared/templates/` (`proposal.md`, `spec.md`, `design.md`, `test-spec.md`, `verify-record.md`, `pr.md`). `exo speclint <file or change root>` checks them.
- **Mandatory artifacts per tier** (what `exo check` requires):

| Tier | Requires |
|---|---|
| 1 | `proposal.md`; `spec.md` only if the change alters behavior |
| 2 | `proposal.md`, `spec.md`, `test-spec.md` |
| 3 and 4 | `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `test-spec.md` |

  Every tier also needs `ai-usage-record.json` and `fitness-assessment.json`. Without a readable assessment the tier is unknown and Tier 4 rules apply.
- **Living specs:** `spec.md` is a delta over `<specs_dir>/capabilities/<capability>/spec.md`, with `## ADDED Requirements`, `## MODIFIED Requirements` and `## REMOVED Requirements`. Requirement IDs are `CAP-<capability>-FR-n` or `CAP-<capability>-NFR-n`; scenarios in the delta are `#### Scenario S-n: <title>` with Given, When and Then. A new requirement takes the next free number of its capability (`exo specs list`); a removed ID is never reused. `exo specs merge <change>` applies the delta.
- **Memory mirror** (`hybrid` and `memory`): save each artifact as `.exo/shared/memory-convention.md` says.

## D. Return envelope

Every phase ends with this block, as the last thing in its answer:

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
- **Read 1 to 3 files inline; 4 or more, delegate** to `sdd-explorer`. Running tests or a build: delegate. Git state commands (`git status`, `git diff --stat`) run inline.
- **Permissions are denied by default.** The explorer and every reviewer are read-only; the implementer writes only what the frozen plan (`tasks.md`, or the proposal in Tier 1) says. Nobody re-delegates: a subagent never launches another one.
- **Mandatory delegation triggers:**
  1. the 4-file rule above;
  2. writing to more than one file;
  3. before the PR: a fresh-context review and the wiki checkpoint (`.exo/shared/project-wiki-guard.md`);
  4. an incident or a production error;
  5. a long session (about 20 tool calls in the same phase): hand off before the context degrades;
  6. any verify in Tier 3 or 4: it runs in fresh context.
- **Pass skills as paths.** A delegation prompt starts with a `## Skills to load before work` block listing the exact `SKILL.md` paths, and the subagent reports how it resolved them (`.exo/shared/skill-resolver.md`).
- **Without subagents:** see `.exo/shared/agent-capabilities.md`.

## H. Execution mode

- **Interactive (default, `sdd.mode: interactive`):** after each phase, show the summary and ask "Adjust anything or continue?". Do not start the next phase without an answer.
- **Automatic (`sdd.mode: auto`, or when the person asks for it in the conversation):** continue phase by phase, and still stop on `needs-input`, `blocked`, a downgrade, `judgment-day` and before the PR.
- Artifacts are written in English. Talk to the person in their language.
