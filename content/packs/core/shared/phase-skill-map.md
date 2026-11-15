# Phase → skill map

Which skills each SDD phase loads, by tier. The orchestrator reads this map before every delegation, and so does a phase skill that runs without an orchestrator (`.exo/shared/sdd-phase-common.md`, section A).

## How to read it

- **Tier 1** loads the Required skills of the phases it runs.
- **Tier 2** adds the Conditional skills whose trigger applies.
- **Tier 3** adds the advisory judges.
- **Tier 4** adds `judgment-day` after verify.
- **At most 5 skills per delegation,** counting only the skills of this map (the phase skill itself, `memory-protocol` and `ai-usage-record` do not count). If more apply, keep the Required ones and the Conditionals whose trigger is strongest, and say which ones you left out.
- **Judges run as separate read-only delegations**, never inside the executor's context. Without subagents, run them inline after the executor's work and say "no isolation".
- **The stack router** is the router skill of the project's stack pack (for example the `java` pack), when one is installed. Without it, follow the commands and conventions in `.exo/context.md`.
- **A skill that is not installed degrades.** Say `<pack>/<skill> not installed — applying inline criteria`, apply its inline criteria from the last table, and record it (`.exo/shared/capability-attribution.md`). Never skip a skill silently.

## Phases per tier

| Tier | Phases | Ceremony |
|---|---|---|
| 1 | risk → new (proposal; spec delta only if behavior changes) → apply → verify (light) → archive | minimal |
| 2 | risk → new → spec (+ test-spec) → apply → verify → archive | light |
| 3 | risk → new → explore (if needed) → propose → spec → design → tasks (+ test-spec) → apply → verify (fresh context) → archive | full |
| 4 | Tier 3, with verify always in fresh context and a mandatory `judgment-day` before archive | full |

The mandatory artifacts of each tier are in `.exo/shared/sdd-phase-common.md`, section C.

## Map

| Phase | Required | Conditional (trigger → skill) | Judges (Tier ≥ 3) |
|---|---|---|---|
| risk | `risk-tiering` | — | — |
| new | `context-retrieval` | — | — |
| explore | `context-retrieval` | new or fuzzy product problem → `product-discovery` | — |
| propose | `context-retrieval` | new feature, MVP or unclear value → `product-discovery` | `judge-product`, `judge-business` |
| spec | — | Tier 2 → `test-strategy` · UI → `accessibility-audit` · new user flow → `product-discovery` | `judge-product` |
| design | stack router | hard to reverse → `architecture-decision-record` · new surface, trust boundary, sensitive data or money → `threat-modeling` · large architecture → `software-solution` · several sessions or developers → `context-anchoring` | `judge-security`, `judge-code-reviewer`, `judge-frontend` (UI) |
| tasks | `test-strategy` | two or more independent units → `parallel-dispatch` | `judge-team` (Tier 4) |
| apply | `code-generation`, `secure-coding-baseline`, `work-unit-commits`, stack router | logs, tickets or production data going to the model → `prompt-hygiene` · UI → `frontend-design` | — |
| verify | `harness-review` | UI in the diff → `accessibility-audit` · dependency or lockfile change → `security-scan-node` or `security-scan-jkp` | `judge-code-reviewer`, `judge-security`, `judge-frontend` (UI) |
| judgment | `judgment-day` (Tier 4) | — | — |
| archive | `branch-pr` | decisions worth keeping → `architecture-decision-record` | — |

Every phase also follows `memory-protocol` and records its work with `ai-usage-record`.

Threats found in design go to `design.md`, section Risks & Mitigations. Advisory judges, and the findings the person decides not to fix, go to the AI Usage Record (`judges_invoked`, `dismissed_followups`).

## Skills from packs not installed yet

These skills are named by the map but ship in later packs. When one is missing, say the degradation sentence with its pack and apply these criteria.

| Skill | Pack | Inline criteria when missing |
|---|---|---|
| `product-discovery` | product | Write who the user is, the problem, the value and how success is measured: in proposal.md, section Intent, when the phase owns proposal.md (new, propose); otherwise as open questions for the person. Ask the person when any of them is unclear. |
| `accessibility-audit` | frontend | Check keyboard access, visible focus, labels and accessible names, contrast and text alternatives in the UI that changed (WCAG 2.2 AA). List each failure with its criterion. |
| `architecture-decision-record` | design | When a decision is hard to reverse, propose a short record (context, decision, alternatives, consequences) for the project's docs and write it there once the person approves its text. Cite it from design.md in the design phase, or from the AI Usage Record decisions later. |
| `threat-modeling` | security | List the assets, entry points and trust boundaries the change touches; for each, the threats that apply (STRIDE) and their mitigation. Write them in design.md, Risks & Mitigations. |
| `software-solution` | core | Describe the components, their responsibilities and the integration points in design.md, Architecture Overview, before the details. |
| `context-anchoring` | sdd | Keep the decisions so far in the change's state memory (`.exo/shared/memory-convention.md`) so another session or person can continue. |
| `parallel-dispatch` | core | Group the tasks into units that do not touch the same files. Run them one after the other, unless the agent can delegate each unit to its own subagent. |
| `secure-coding-baseline` | security | Validate and encode untrusted input at the boundary, use parameterized queries, keep secrets out of code and logs, check authorization on every entry point and fail closed. |
| `prompt-hygiene` | core | Before pasting logs, tickets or production data into the conversation, remove secrets, personal data and customer identifiers; prefer short synthetic excerpts. |
| `frontend-design` | frontend | Reuse the project's existing UI components and design tokens. Do not add new visual styles without the person's approval. |
| `security-scan-node` | frontend | Run the dependency audit of the Node project (for example `npm audit --omit=dev`) and report the high and critical findings. |
| `security-scan-jkp` | java | Run the dependency check of the Java project (for example the OWASP dependency-check plugin) and report the high and critical findings. |
| `judge-product` | quality | In a separate read-only pass, check that the change solves the problem in the proposal for its user, and nothing else. Report gaps as findings. |
| `judge-business` | quality | In a separate read-only pass, check the value, cost and risk stated in the proposal. Report what is missing or contradictory. |
| `judge-frontend` | quality | In a separate read-only pass, review the UI changes for consistency with the existing components, states (loading, empty, error) and accessibility. |
| `judge-team` | quality | In a separate read-only pass, check that tasks.md can be split among people without overlapping files, and that each unit has its own tests. |
