# Agent capabilities

The SDD cycle runs in agents with and without subagents. This contract says what changes between them, so every agent produces the same artifacts and passes the same checks.

## What each agent has

| Agent | Subagents | Hooks | Notes |
|---|---|---|---|
| Claude Code | yes: `sdd-explorer`, `sdd-implementer`, `sdd-verifier`, `sdd-judge` in `.claude/agents/`; with the discovery pack, also `re-extractor` and `re-auditor` | not used | delegate with the agent's subagent tool |
| GitHub Copilot (agent mode) | when the session lets you call a custom agent by name | not used | if you cannot call it, take the path without subagents |
| Other agents that read `AGENTS.md` | assume no | not used | path without subagents |

The engine uses no hooks: the rules in `AGENTS.md` and the skills say when to run each command. If you are not sure whether you can delegate, try once; if the tool is not there, take the path without subagents and say so.

## With subagents

- Follow the delegation rules (`.exo/shared/sdd-phase-common.md`, section G).
- **Explorer:** reading 4 or more files. Read-only.
- **Implementer:** writing code and tests for the frozen plan.
- **Verifier:** verify in fresh context. Read-only, plus running the tests.
- **Judge:** advisory reviews and `judgment-day`. Read-only.
- The subagent starts without the conversation: pass the change name, the change root, the phase, the exact skill paths and what to return. It answers with the envelope (section D).

## Without subagents

- Run every phase **inline**, in the same session, with the same skills and the same artifacts.
- **Declare it.** Put `Isolation: no isolation (inline)` in the envelope notes, and in `verify-record.md`, section Tests or Issues Found, say that the verify did not run in an isolated context.
- **Read in batches.** With no explorer, read files in small batches and summarize as you go, so the context does not fill up.
- **Judges** run after the executor's work, as a separate pass with the judge's criteria, and you say so.

## Fresh context without subagents

A fresh-context verify (Tier 3) needs a context that did not write the code. Without subagents:

1. Write `<change-root>/handoff.md`: the change name, the phase to run (`verify`), the files to read (spec, design, tasks, test-spec, the diff: `git diff <base>`), the test command, and what to return. Nothing else: no conclusions of your own.
2. Ask the person to open a **new session** of their agent and say: "Run sdd-verify for `<change-name>`; start from `<change-root>/handoff.md`."
3. The new session runs `sdd-verify` from the handoff file and writes `verify-record.md`. Delete `handoff.md` when the verify is done; it is not an artifact of the change.

If the person prefers not to open a new session, run the verify inline and declare `no isolation`. That needs their explicit approval, recorded as a decision in the AI Usage Record.
