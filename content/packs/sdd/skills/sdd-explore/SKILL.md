---
name: sdd-explore
description: >-
  Investigates the area of an SDD change in read-only mode before an approach
  is chosen: the relevant files and current behavior with path:line, the
  living specs of the affected capabilities, risks, unknowns, and options with
  their trade-offs. Returns the full text of exploration.md. Use it in Tier 3
  and 4 when the area is unknown, when understanding a flow means reading 4 or
  more files, or when someone asks "sdd explore", "explore this change", "how
  does X work before we change it", "what are the options".
metadata:
  exo-pack: sdd
  exo-execution: subagent
  exo-subagent: sdd-explorer
  exo-phase: explore
  exo-permissions: read-only
---

# sdd-explore

## Result

The full text of `exploration.md`, with the structure below, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D.

Who writes the file:

- **Delegated to `sdd-explorer`** (the usual case): you return the text in your answer and never write files. The orchestrator writes `<change-root>/exploration.md` from it.
- **Inline** (an agent without subagents, or the person called this skill directly): you write `<change-root>/exploration.md` yourself, after the answer is complete.

This skill never touches code, tests, configuration, other artifacts (`proposal.md`, `spec.md`, ...) or the living specs, and never runs commands that change state.

## Inputs

The delegation prompt brings (`.exo/shared/agent-capabilities.md`, With subagents): the change name and root, the phase (`explore`), a `## Skills to load before work` block with exact paths, the question to answer, the output of `exo specs list --json`, and what memory returned for the change.

- Read `proposal.md` (intent and scope from `skill:sdd-new`) and `.exo/context.md` first.
- The explorer has read tools only. If the prompt has no `exo specs list` output, find the living specs with a glob over `<specs_dir>/capabilities/*/spec.md`.
- Inline, gather the inputs yourself: `exo specs list --json`, and memory as `skill:memory-protocol` says (`exo mem search "<change-name>"`, then `exo mem get <id>`).
- No change yet: return the exploration in the answer only, and suggest `skill:sdd-new`.

## Load the skills

Follow `.exo/shared/sdd-phase-common.md`, section A, and report how each one resolved (`.exo/shared/skill-resolver.md`).

- **Required:** `context-retrieval`: retrieve context before claiming anything, and cite the source next to each claim.
- **Conditional:** `product-discovery`, when the product problem is new or fuzzy. While the product pack is not installed, say `product/product-discovery not installed — applying inline criteria` and apply them within your phase: find, or mark as unknown, who the user is, the problem, the value and how success is measured. Put what you found in Goal and what is unclear in Open Questions; `skill:sdd-propose` writes them into the Intent of `proposal.md`.

## Steps

1. **Goal.** Restate what the change must achieve, from `proposal.md`, in two to four lines.
2. **Current behavior.** Follow the flow from its entry point (route, command, UI event, job) to the data and back. Every claim has its `path:line`. Read the actual code; tests show the intended behavior. Mark `[Unverified]` anything you could not read.
3. **Affected capabilities.** For each capability the change touches: its living spec, the requirement IDs involved (`CAP-<capability>-FR-n`), and whether the code and the spec agree. A behavior without a capability spec: propose a kebab-case name for a new capability.
4. **Options.** Two or three when there is a real choice; one when there is not, saying why. Each option: what it does, the files and modules it touches, pros, cons, how reversible it is, effort and risk. Recommend one and say why; the person decides in propose.
5. **Risks.** What can break, who is affected, sensitive data, missing tests, migrations. Each risk with its evidence.
6. **Open questions.** Only what a person can answer: the question, why it matters, and the default you would assume.

Read in small batches and summarize as you go. Stop when the options are clear. After about 20 tool calls, wrap up with what you have and list the rest in Open Questions (`.exo/shared/sdd-phase-common.md`, section G).

If the evidence contradicts the tier (sensitive data, a wider blast radius, an irreversible step), add a `fitness_signal` to the envelope. Only the orchestrator re-classifies.

## `exploration.md`

There is no template: use exactly these sections, in English, and write `None.` in a section with nothing to say.

```markdown
# Exploration: <change-name>

## Goal

<What the change must achieve, in two to four lines.>

## Current Behavior

- <claim> (src/auth/session.py:42)
- <claim> [Unverified]

## Affected Capabilities

| Capability | Living spec | Requirements involved | Code and spec agree |
|---|---|---|---|
| auth | specs/capabilities/auth/spec.md | CAP-auth-FR-1, CAP-auth-FR-2 | yes |

## Options

### Option A: <name>

- What: ...
- Touches: ...
- Pros: ...
- Cons: ...
- Reversibility: ...
- Effort and risk: ...

Recommendation: Option A, because ...

## Risks

| Risk | Evidence | Impact | Mitigation idea |
|---|---|---|---|

## Open Questions

1. <question>. Why it matters: ... Default if nobody answers: ...
```

## Record

A delegated explorer cannot run commands: it lists in its envelope notes the skills it loaded, with their resolution, and the files it read. The orchestrator records them. Inline, run these yourself, without the subagent entry:

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-explore", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add capabilities_used '{"name": "sdd-explorer", "type": "subagent", "activation": "auto"}'
exo change record <change> --add skills_used '"sdd-explore"'
exo change record <change> --add knowledge_used '{"source": "code", "ref": "src/auth/session.py:42"}'
```

A degraded skill gets `"resolution": "none"` and the degradation sentence as `note` (`.exo/shared/capability-attribution.md`). Whoever writes `exploration.md` also saves it with topic key `sdd/<change-name>/exploration` in `hybrid` and `memory` persistence (`.exo/shared/memory-convention.md`).

## Without subagents

Run this skill inline in the same session, with the same sections (`.exo/shared/agent-capabilities.md`): read in small batches, write `exploration.md` yourself, and put `Isolation: no isolation (inline)` in the notes.

## Envelope

```yaml
status: ok
phase: explore
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/exploration.md
    summary: text returned in the answer, not written; 2 options, recommends B
notes: >-
  Isolation: subagent. Skills: sdd-explore (paths-injected), context-retrieval
  (paths-injected), product-discovery (none: product/product-discovery not
  installed — applying inline criteria). Read 9 files.
next: propose
```

- `needs-input`: an open question blocks every option; say exactly what to ask.
- `blocked`: the code or the specs cannot be read.
