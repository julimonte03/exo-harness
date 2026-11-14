# Memory convention for SDD

How the SDD phases use the engine memory (`exo mem`). The general rules (when to read context, what to save, never secrets) are in the `memory-protocol` skill; this contract adds what is specific to changes.

## Topic keys

Each change artifact saved in memory uses the topic key `sdd/<change-name>/<artifact>`, without the epic:

| Artifact | Topic key |
|---|---|
| proposal, spec, design, tasks, test-spec, verify-record, exploration | `sdd/<change-name>/proposal`, `sdd/<change-name>/spec`, … |
| state of the change | `sdd/<change-name>/state` |

Saving with the same topic key updates the observation instead of duplicating it, so save as often as needed.

```bash
exo mem save --type discovery --title "PROJ-123-add-login: spec" --topic-key sdd/PROJ-123-add-login/spec --content - < specs/PROJ-123-add-login/spec.md
```

## When to save

- **`hybrid` and `memory` persistence** (`sdd.persistence` in `.exo/config.json`): after writing each artifact, save it with its topic key. With `memory`, memory is the only copy.
- **Every mode:** keep the state artifact up to date when a phase ends. It is what survives a context compaction or a new session: the change name, the tier, the phase just finished, the next one, open questions and decisions the person made. Keep it short.

```text
change: PROJ-123-add-login · tier 2 · done: spec · next: apply
decisions: SSO only for employees (the person, 2026-11-14)
open: none
```

- Decisions, bug causes and conventions found during the change also go to memory as ordinary observations (`--type decision`, `bugfix`, `convention`), as `memory-protocol` says.

## Two-step retrieval

1. **Search, then read.** `exo mem search "<change-name> <artifact>" --json` returns previews (truncated). Pick the observation whose `topic_key` is the one you want.
2. `exo mem get <id> --json` returns the full content. Never work from a preview.

To resume a change after a compaction or in a new session: search `"<change-name> state"`, read it in full, then read the artifacts it points to.

## What never goes to memory

Secrets, credentials, personal data, customer data and raw production logs. Summarize instead, and say what you left out.
