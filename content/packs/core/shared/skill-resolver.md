# Skill resolver

How an agent finds the skill it has to load, and what it does when the skill is not there.

## Steps

1. **Paths given.** If the delegation prompt has a `## Skills to load before work` block, read exactly those `SKILL.md` paths, in full. Resolution: `paths-injected`.
2. **Registry.** Otherwise, look the name up in `.exo/skill-registry.md` and read the `SKILL.md` at its path. Resolution: `fallback-registry`.
3. **Known folders.** If the registry is missing or does not list it, look for `<name>/SKILL.md` in the skills folders of this agent: `.claude/skills/` (Claude Code, Copilot) or `.agents/skills/` (other agents). Resolution: `fallback-path`.
4. **Not found.** The skill is not installed. Resolution: `none`. Go to Degradation.

An unqualified name resolves first in the pack of the skill that asked for it, then in `core`. Skill names are unique, so this only matters when reading the registry by pack.

## Degradation

When a skill is not installed:

1. Say it, with this exact sentence: `<pack>/<skill> not installed — applying inline criteria`. The pack is the one in the last table of `.exo/shared/phase-skill-map.md`.
2. Apply the inline criteria from that table.
3. Record it in the AI Usage Record (`.exo/shared/capability-attribution.md`), with `"resolution": "none"` and the sentence as `note`.

Never skip a skill silently, and never pretend to have loaded one you did not read.

## Report

A subagent reports how it resolved each skill in the `notes` of its envelope (`.exo/shared/sdd-phase-common.md`, section D), for example:

```text
Skills: sdd-design (paths-injected), threat-modeling (none: security/threat-modeling not installed — applying inline criteria).
```

The orchestrator copies those lines into `capabilities_used`.
