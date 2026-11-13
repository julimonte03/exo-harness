---
name: sdd-status
description: >-
  Shows the status of the project's SDD changes (phase, artifacts, followups
  and ticket) without guessing. Use it when asked what state a change is in or
  what is missing.
metadata:
  exo-pack: sdd
  exo-execution: inline
---

# sdd-status

Answer only with what the engine returns. Do not infer the status by reading files by hand.

## Steps

1. To see all changes, run `exo change list --json`.
2. For a specific one, run `exo change status <change-name> --json`.
3. For open followups, run `exo change followups <change-name> --json`.
4. Summarize: phase, artifacts present, ticket, open followups and what comes next.

If the command is not available, say so and do not make up the status.
