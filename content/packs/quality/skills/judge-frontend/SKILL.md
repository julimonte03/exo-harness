---
name: judge-frontend
description: >-
  Advisory, read-only frontend judge for changes that touch UI: reviews a
  design or the UI files of a diff for consistency with the existing
  components and design tokens, the loading, empty and error states, client
  performance, client-side security and accessibility (WCAG 2.2 AA), with
  the criteria of harness-review and accessibility-audit. Returns JFE-n
  findings with severity, path:line and the WCAG or rule item, plus an
  APPROVED or ESCALATED verdict; it never fixes anything. Runs in the
  sdd-judge subagent in design and verify from Tier 3, only when the change
  touches UI. Use it also when someone wants an independent frontend opinion
  on a component, a screen or a UI diff. Triggers: "frontend judge", "judge
  the UI", "independent frontend review", "review this component", "does
  this screen handle loading and errors", "is this UI consistent with our
  design system".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-frontend

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JFE-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## When the change touches UI

Only then. The change touches UI when the diff or `design.md` (Modules / Files) creates or modifies `.html`, `.tsx`, `.jsx`, `.vue`, `.svelte`, `.css` or `.scss` files, or when `design.md` describes a screen, a component or a page. A change with no UI does not call this judge; if it reaches you anyway, return `APPROVED` with no findings and `N/A: no UI in what you received` in Not reviewed.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path and, when installed, the paths of `accessibility-audit` and `frontend-design`; the change name and root, the phase, the tier, what to review (the diff text or the list of changed files) and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the work is done, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- You cannot run the app, the tests or an accessibility scanner. Judge from the code and the design; what only a running browser can tell goes in Not reviewed.
- This judge owns no gate. In verify, the `accessibility_review` gate comes from `accessibility-audit` (pack `frontend`) itself.

| Phase | What you review | Against (the stage before) |
|---|---|---|
| design (Tier 3, UI) | the UI of `design.md` (and `canvas.md` when there is one): components, states, data flows | `spec.md` and `proposal.md`; for `canvas.md`, `design.md` too |
| verify (Tier 3, UI) | the UI files of the diff, in full | `spec.md`, `design.md` and `tasks.md` |
| outside SDD | the UI files or the design the person gives | the ticket or the description the person gives |

## Criteria

Only the frontend; other judges cover correctness, server-side security, product and the plan. Reuse what exists: the UX/UI and accessibility dimensions of skill:harness-review (its checklists are in `harness-review/references/dimensions.md` in the skills folder), and the skills below when installed. Do not add criteria beyond the five below.

Before judging, find what the project already has: the components folder, the design system or token package (a `tokens`, `theme` or `design-tokens` import), the data-fetching and state patterns, and the conventions in `.exo/context.md`. When the project's frontend stack router skill is installed, follow its conventions too.

### 1. Consistency

- The change reuses the existing components instead of adding a near-duplicate; a new component follows the folder, naming and props conventions of its neighbors.
- Colors, spacing, typography, radii, shadows and motion come from the design tokens; a hard-coded value where a token exists is a finding.
- Forms, dialogs, notifications, routing and data fetching follow the patterns already in use.
- A new visual style needs the person's approval, written in the design.
- When `frontend-design` (pack `frontend`) is installed, apply its criteria too. When it is not, say `frontend/frontend-design not installed — applying inline criteria`: the bullets above are those criteria.

### 2. States

- Every screen and component that loads, sends or shows data handles loading, empty, error (with a way to recover: retry, keep what the user typed), success and partial results.
- Pending actions are visible and cannot be sent twice; an optimistic update rolls back on failure.
- Long text, many items and a slow network do not break the layout.
- In design: each component lists its states and what moves it from one to the next, and they match the scenarios of the spec.

### 3. Client performance

- No request waterfalls or duplicate fetches of the same data; requests are cancelled when the component goes away or the input changes.
- Lists render with stable keys; long lists are paginated or virtualized.
- No expensive work on every render; memoization only where the cost is real.
- A new dependency is worth its weight in the bundle; heavy screens load lazily; images have dimensions and load lazily below the fold.

### 4. Client-side security

Only what runs in the browser and no other judge covers; the server side belongs to skill:judge-security.

- **Injection into the page (XSS)** is skill:judge-security's, not yours: untrusted data rendered as raw HTML (`dangerouslySetInnerHTML`, `innerHTML`, `v-html`) or put into `href` or `src` unchecked. When you see one, do not rate it: point at its `path:line` in Not reviewed, for `judge-security`.
- No secrets, privileged keys or admin tokens in client code, in build-time variables exposed to the bundle, or in browser storage.
- No tokens or personal data in URLs, client logs or analytics events.
- Hiding a button is not access control: the server checks it too (point at the gap; the server review is not yours).
- Links that open a new tab use `rel="noopener noreferrer"`; cross-window messages check their origin.

### 5. Accessibility (WCAG 2.2 AA)

1. **`accessibility-audit`** (pack `frontend`). Read its `SKILL.md` in full when the delegation gives it, or resolve it as `.exo/shared/skill-resolver.md` says, and apply its criteria to the changed UI.
2. **When it is not installed:** say `frontend/accessibility-audit not installed — applying inline criteria`, and check keyboard access, visible focus, labels and accessible names, contrast and text alternatives in the UI that changed, then the rest of the WCAG 2.2 AA table of skill:harness-review (target size, focus not obscured, error identification, status messages).
3. Each failure cites its success criterion: `WCAG 2.2 SC 2.1.1`.

## Findings

- **ID:** `JFE-1`, `JFE-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D):
  - Critical: the main flow of the screen cannot be completed (at all, or with the keyboard alone); a secret in the client bundle.
  - High: a WCAG 2.2 A or AA failure that blocks a task (a control with no accessible name, a keyboard trap, an error announced only by color); a state the spec names left unhandled, so the user gets stuck; access control only in the UI; a token or personal data in storage, URLs or analytics.
  - Medium: a hard-coded value where a token exists; a near-duplicate component; a missing loading or empty state; a request that is not cancelled; a WCAG failure that does not block the task; a heavy dependency without need.
  - Low: naming, small inconsistencies with the neighbors.
- **Criterion:** the WCAG success criterion, or the criterion by name (`consistency: tokens`, `states: error`, `client performance`, `client security: storage`), or the scenario ID. A defect that comes from the design while you judge the diff is a finding against `design.md` (`no cascade: design.md`).
- **Suggested fix:** as text, naming the existing component or token to use when there is one. Never apply it. Never copy secrets or personal data into a finding: point at the `path:line`.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the work contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-frontend on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JFE-1 | High | web/src/components/LoginForm.tsx:42 | The show-password control is a clickable icon with no accessible name and no keyboard access | WCAG 2.2 SC 2.1.1, SC 4.1.2 | Use the existing IconButton with an aria-label such as "Show password" |
| JFE-2 | Medium | web/src/components/LoginForm.tsx:18 | The error text uses a hard-coded red instead of the danger color token | consistency: tokens | Use the danger token of the design system, as the other forms do |

## Not reviewed

The rendered contrast of the error text: it needs a running browser.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: verify
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-frontend (paths-injected),
  accessibility-audit (none: frontend/accessibility-audit not installed — applying inline criteria).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 1 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup, the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JFE-1", "judge": "judge-frontend", "rule": "WCAG 2.2 SC 2.1.1", "severity": "high", "summary": "The show-password icon has no accessible name and no keyboard access; use the existing IconButton with an aria-label", "location": "web/src/components/LoginForm.tsx:42"}'
exo change record <change> --add judges_invoked '{"name": "judge-frontend", "result": "escalated: JFE-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-frontend", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```

When `accessibility-audit` or `frontend-design` was missing, it also records each with `"resolution": "none"` and its degradation sentence as `note` (`.exo/shared/skill-resolver.md`).
