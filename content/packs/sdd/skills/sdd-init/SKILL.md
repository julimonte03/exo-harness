---
name: sdd-init
description: >-
  Sets up the SDD cycle in a project that already ran exo init: runs exo
  doctor, reviews the SDD settings in .exo/config.json (ticket pattern, specs
  folder, persistence, interactive or automatic mode) and offers to change
  them, makes sure the project wiki .exo/context.md exists, explains the cycle
  and the risk tiers, and lists the living specs. It writes no SDD artifacts.
  Use it when someone says "sdd init", "set up sdd", "configure the sdd cycle",
  "enable spec-driven development", "how do I start with sdd", or before the
  first change of a project.
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: init
  exo-permissions: read-only+exo-init
---

# sdd-init

## Result

- `exo doctor` without errors, or each error explained with its fix.
- The SDD settings reviewed with the person; ticket changes applied only through `exo init`.
- `.exo/context.md` present, written by `project-onboarding`, or the person's explicit choice to skip it.
- The person knows the cycle, the tiers and how to start a change (`skill:sdd-new`).
- The envelope of `.exo/shared/sdd-phase-common.md`, section D, with `change_name: none`.

This skill creates no change and writes no SDD artifact (no proposal, spec or record), never touches `<specs_dir>/capabilities/`, never edits `tickets` in `.exo/config.json` by hand, and never writes `.exo/context.md` itself.

## Steps

### 1. Diagnose

Run `exo doctor` (`--json` to process it).

- `install` says the engine is not installed: ask the person to run `exo init` first, and stop with `status: blocked`.
- Each error: explain it in one line and say how to fix it. Warnings, such as a `config` field that went back to its default: mention them.
- `exo` itself missing: say so and stop.

### 2. Review the settings

Read `.exo/config.json` and show the person the current values, one line each:

| Setting | Meaning | Values |
|---|---|---|
| `tickets.pattern`, `tickets.example` | the project's ticket IDs; null means no tickets, and commits use Conventional Commits without an ID | a regular expression and an example ID |
| `specs_dir` | where changes and living specs live | default `specs` |
| `sdd.persistence` | where artifacts are kept (`.exo/shared/sdd-phase-common.md`, section B) | `filesystem` (default), `memory`, `hybrid`, `none` |
| `sdd.mode` | whether the cycle stops after every phase | `interactive` (default), `auto` |
| `governance.protected_branches` | branches nobody commits to directly | default `main`, `master`, `prod`, `production` |

Then offer changes; apply only what the person approves.

- **Tickets:** always through `exo init`, never by editing the file. Preview first, then apply:

  ```bash
  exo init --ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example 'PROJ-123' --dry-run
  exo init --ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example 'PROJ-123' --yes
  ```

  Other common patterns: `#\d+` (`#123`) and `AB#\d+` (`AB#123`). `--no-tickets` removes the tickets. `exo init` keeps the installed agents and packs.
- **`specs_dir`, `sdd.persistence`, `sdd.mode`:** `exo init` has no flag for them. If the person wants another value, they edit `.exo/config.json` (or you do it with their approval), and `exo doctor` confirms the value is valid. Changing `specs_dir` moves no existing change: warn before.
- Ask, never decide: these settings are the person's.

### 3. Project wiki

- No `.exo/context.md`: run `project-onboarding` now if the person agrees. Tier 1 changes can start without it; Tier 3 and 4 should not (`.exo/shared/project-wiki-guard.md`).
- It exists: read it, and note what looks outdated (commands, areas, owners) for the person.

### 4. Explain the cycle

Say it briefly, in the person's language:

- Every change starts with `skill:sdd-new`: it names the change, classifies its risk from 7 dimensions (`skill:risk-tiering`) and drafts the proposal.
- The tier sets the ceremony (`.exo/shared/phase-skill-map.md`, Phases per tier):

  | Tier | Phases |
  |---|---|
  | 1 | proposal (and a spec delta if behavior changes), apply, light verify, archive |
  | 2 | adds a spec and a test spec |
  | 3 | adds explore when needed, a refined proposal, design and tasks; verify in fresh context |
  | 4 | Tier 3 plus a mandatory `judgment-day` before archive |

- Missing or unreadable risk evidence means Tier 4. Raising a tier is automatic; lowering it needs the person's own words.
- In interactive mode every phase ends with "Adjust anything or continue?". `skill:sdd-status` tells where a change is at any time.
- At archive, the change's spec delta is merged into the living specs, one file per capability.

### 5. Living specs

Run `exo specs list` and show the capabilities and their requirement counts. If there are none, say that they appear as changes are archived (`exo specs merge`, run by `sdd-archive`), and that each one follows `.exo/shared/templates/capability-spec.md`. A capability with `problems` above 0: suggest `exo speclint <specs_dir>/capabilities/<capability>/spec.md`.

### 6. Close

Offer to start the first change with `skill:sdd-new`.

## Record

There is no change yet, so there is no AI Usage Record to write: record nothing. The first change gets its record from `exo change new`. Settings the person chose live in `.exo/config.json`; do not copy them to memory (`skill:memory-protocol`).

## Envelope

```yaml
status: ok
phase: init
change_name: none
artifacts:
  - path: .exo/config.json
    summary: ticket pattern set through exo init (PROJ-123 style)
notes: >-
  Isolation: no isolation (inline). Skills: sdd-init (fallback-registry),
  project-onboarding (fallback-registry). Degraded: none.
  doctor: 0 errors. context.md: written by project-onboarding. Living specs: none yet.
next: new
```

- `artifacts: []` when nothing changed.
- `needs-input`: a setting waits for the person's decision.
- `blocked`: the engine is not installed in the project, or `exo` is missing.
