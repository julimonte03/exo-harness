---
name: accessibility-audit
description: >-
  Audits web UI for accessibility against WCAG 2.2 levels A and AA, with EN
  301 549 and the ARIA Authoring Practices patterns: keyboard access, focus,
  names and roles, forms and errors, contrast, text alternatives, status
  messages, target size and reflow. Cites each failure by criterion number and
  name, with a severity, path:line and a fix. In the SDD spec phase it turns
  the criteria into requirements and scenarios; in verify, when the diff
  touches UI (html, tsx, jsx, vue, svelte, css, scss), it reviews what changed
  and produces the accessibility_review gate, where an open Critical or High
  finding keeps the verify from ready. Use it when a change has UI, or when
  someone asks whether a screen, form or component works with a keyboard, a
  screen reader or zoom. Triggers: "accessibility", "a11y", "WCAG", "screen
  reader", "keyboard navigation", "focus order", "color contrast", "ARIA",
  "is this accessible", "EN 301 549".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-specs
---

# accessibility-audit

## Result

- **Spec phase:** accessibility requirements for the UI the change touches: an NFR with a measurable threshold and Given/When/Then scenarios for the keyboard and screen reader paths, which `sdd-spec` writes into spec.md.
- **Verify phase:** findings with severity, `path:line`, the criterion (`WCAG 2.2 SC 2.1.1 Keyboard (A)`) and a fix as text, plus the full text of `<change-root>/gates/accessibility_review.md`, started from `.exo/shared/templates/gate.md`, which passes `exo speclint`.
- **Outside a change:** the same findings in the answer, with a verdict; the gate text only when the person asks for it.

## When

| Moment | Trigger | What you do |
|---|---|---|
| spec (`.exo/shared/phase-skill-map.md`) | The change has UI | Turn the criteria into requirements and scenarios |
| verify | The diff touches UI files | Audit what changed and produce the `accessibility_review` gate |
| On request | Someone asks whether a UI is accessible | Audit the files or screens they name |

- **UI files:** `*.html`, `*.htm`, `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.scss`, and templates that render HTML. Find them with `git diff --name-only <base>...HEAD`.
- **Not for:** a change with no UI (say `N/A: no UI in the diff`); visual taste or design-system fit, which belong to `frontend-design` and `judge-frontend`; the full review of a change, which is `harness-review`. Native mobile and desktop apps: apply the same criteria where they fit and say what you could not check.

## Where it runs and who writes

| Situation | Runs in | Writes |
|---|---|---|
| spec | inline, inside `sdd-spec` | `sdd-spec` writes spec.md with your requirements and scenarios |
| verify with subagents | `sdd-verifier`, read-only, in fresh context | you return the gate text; the orchestrator writes `gates/accessibility_review.md` verbatim |
| verify without subagents, or from `handoff.md` | the session that runs the verify | that session |
| outside a change | inline | nobody: the findings go in the answer |

In verify, the findings also feed `verify-record.md` (Issues Found), which `sdd-verify` writes. This skill owns only the `accessibility_review` gate; never write the other gates or the record.

## Permissions

- **In verify:** read-only. Run only the test, lint and accessibility commands of `.exo/context.md` or of the delegation, and read-only git (`git diff`, `git log`, `git show`).
- **Tools are optional.** Automated checkers (axe-core and its test integrations, pa11y, Lighthouse, lint plugins such as `eslint-plugin-jsx-a11y`) run only when the project already has them, through its own scripts. Never install or fetch one (`npx` of a package that is not installed downloads it): suggest it as a follow-up instead. Without tools, the manual review is the audit.
- **In spec:** the requirements go into spec.md, which the spec phase owns. Never edit proposal.md, design.md or another phase's artifact.

## Spec: criteria into requirements

1. List the screens and components the change adds or modifies, and the user task each one serves.
2. Pick the criteria that apply (`references/wcag-22-checklist.md`), and the ARIA pattern of every custom widget (`references/aria-patterns.md`).
3. Write one NFR with a measurable threshold, and scenarios for each main task done with the keyboard alone and with a screen reader, plus its errors and status messages:

```markdown
### CAP-booking-NFR-3: Accessible booking form
The booking form SHALL meet WCAG 2.2 level AA: no Critical or High finding in the accessibility_review gate, and every control reachable and operable with the keyboard alone.

#### Scenario S-5: Errors are announced with their field
- Given the booking form with no room selected and an end time before the start time
- When the person submits it with the keyboard
- Then focus moves to the first field with an error
- And each error is shown as text next to its field and exposed as the field's description
```

4. `sdd-spec` gives the NFR the next free number of its capability and numbers the scenarios. Write behavior, not markup: "exposed as the field's description" is testable (a role and description query in Testing Library, for example) without naming the attribute.

## Verify: audit the diff

1. **Scope.** The UI files in the diff, each with the component or screen and the scenario it serves. Read them in full, plus the styles and shared components they use (focus styles, the design tokens behind colors).
2. **Automated checks,** only if the project has them: look for axe-core integrations (`jest-axe`, `vitest-axe`, `@axe-core/playwright`), pa11y, Lighthouse CI or accessibility lint rules in the manifests and scripts. Run the project's command, report it with its result, and remember that these tools catch only part of the failures.
3. **Manual review,** criterion by criterion, with `references/wcag-22-checklist.md`. Go in this order: keyboard and focus; names, roles and values; forms and errors; contrast and color; text alternatives; structure (headings, landmarks, lists, tables); dynamic content and status messages; target size, reflow and motion. For a custom widget, check its pattern in `references/aria-patterns.md`.
4. **Contrast:** compute the ratio when the colors are known (CSS values, token files in the repo) with the formula in the checklist. When they are not (tokens from an external package, text over images), list the check as not done.
5. **Rate** each failure (Severity) and write its fix as text.
6. **Not checked:** what a static review cannot confirm (screen reader output, behavior at 400% zoom, colors resolved at runtime). List it; it does not block on its own.

Signals in a diff that usually mean a failure:

| Signal | Usually fails |
|---|---|
| A click handler on a `div` or `span` with no role, `tabindex` or key handler | 2.1.1 Keyboard, 4.1.2 Name, Role, Value |
| `outline: none` or `outline: 0` with no other focus style | 2.4.7 Focus Visible |
| An `img` without `alt`, or an icon-only button without an accessible name | 1.1.1 Non-text Content, 4.1.2 |
| An input whose only label is its placeholder | 3.3.2 Labels or Instructions, 1.3.1 Info and Relationships |
| A positive `tabindex` | 2.4.3 Focus Order |
| Color as the only signal (red text for an error, a colored badge) | 1.4.1 Use of Color |
| Content that updates after a request with no live region | 4.1.3 Status Messages |
| A dialog or drawer that does not take focus, trap it while modal, close with Escape and give it back | 2.4.3 Focus Order, 2.1.2 No Keyboard Trap |
| `aria-hidden="true"` on something focusable | 4.1.2 |
| `maximum-scale=1` or `user-scalable=no`; fixed heights on text boxes | 1.4.4 Resize Text, 1.4.10 Reflow |
| Pointer targets under 24 by 24 CSS pixels with no spacing | 2.5.8 Target Size (Minimum) |
| A new route that keeps the previous page title | 2.4.2 Page Titled |

## Severity

- **Critical:** a person cannot complete the task with a keyboard, a screen reader, zoom or voice control (a blocker): a control of the main flow they cannot reach or operate, a keyboard trap, a required field with no name, content that flashes above the threshold of 2.3.1.
- **High:** an A or AA criterion fails in the main flow and the task needs great effort, or information is lost: errors not announced, invisible focus on the main controls, body text far below 4.5:1.
- **Medium:** an A or AA failure on secondary content, or with a reasonable workaround.
- **Low:** beyond AA (AAA criteria, best practice), or redundant ARIA with no effect on users.

## The accessibility_review gate

A conditional gate: it does not come from the tier. Verify writes it whenever it audits UI in the diff, `exo check` checks every gate present, and a project can require it in a tier through `governance.gates`.

```markdown
# Gate: accessibility_review

<!-- exo-gate:accessibility_review -->

## Verdict

ESCALATED: A11Y-1 keeps keyboard users from rating a booking.

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| Critical | src/components/RatingInput.tsx:18 | A11Y-1: the stars are span elements with click handlers only; a keyboard user cannot reach or set them. Use a radio group (native inputs) with a visible label. | WCAG 2.2 SC 2.1.1 Keyboard (A); SC 4.1.2 Name, Role, Value (A) |
| High | src/components/RatingInput.css:7 | A11Y-2: `outline: none` removes the focus indicator with no replacement | WCAG 2.2 SC 2.4.7 Focus Visible (AA) |
| Low | src/components/RatingInput.tsx:31 | A11Y-3: `role="button"` repeated on a native button | ARIA: native semantics first |

Not checked: the screen reader announcement of the selected value (needs the running UI).

## Approval

Requires tech_lead approval: yes
Source: skill accessibility-audit
```

- Keep the marker exactly `<!-- exo-gate:accessibility_review -->`, in a file named `accessibility_review.md`.
- Each Finding starts with `A11Y-<n>`, unique in the change and never reused, so a dismissal can point at it.
- The Rule/OWASP column holds the criterion as `WCAG 2.2 SC <number> <name> (<level>)`. Add the EN 301 549 clause only when the project must meet that standard (`references/standards-and-tools.md`).
- `APPROVED` when no Critical or High finding is open; `ESCALATED` when one is, or when something that matters could not be reviewed (say what).
- `Requires tech_lead approval: yes` when the verdict is `ESCALATED` or a Critical or High finding stays open or was dismissed; `no` otherwise.
- No findings: one row `| - | - | No findings | - |`, `APPROVED`, and the Not checked line when there is one.
- Check it with `exo speclint <change-root>/gates/accessibility_review.md`. A verify that runs again rewrites the gate.

## Effect on the verify

- Every open Critical or High finding also goes to Issues Found of `verify-record.md`, so the Verdict cannot be `ready` (`sdd-verify`, Verdict).
- **Only the person dismisses a finding,** with their reason. The orchestrator records it and passes it to the next verify as data:

  ```bash
  exo change record <change> --add dismissed_followups '{"id": "A11Y-1", "judge": "accessibility-audit", "rule": "WCAG 2.2 SC 2.1.1", "reason": "<reason the person gave>"}'
  ```

- A dismissed finding stays in the gate, marked `dismissed: <reason>`, and in Issues Found as dismissed by the person; it no longer blocks `ready`. The gate stays `ESCALATED` with approval yes, so the PR shows it.
- Never dismiss a finding yourself, and never lower a severity to reach `ready`.

## Outside an SDD change

The scope is the files or screens the person names, or the diff against the target branch. Give the findings grouped by severity, each with `path:line`, the criterion, who is blocked and how, and the fix; then the Not checked list and a one-line verdict. Add the gate text only when they want to paste it in a PR.

## Record

A subagent lists the skill and its resolution in its envelope notes, and the orchestrator records it. Inline, record it before the phase envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "accessibility-audit", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"accessibility-audit"'
exo change record <change> --add gates '{"name": "accessibility_review", "status": "fail", "detail": "ESCALATED: A11Y-1 Critical open"}'
```

`status` is `pass` for `APPROVED`, `fail` for `ESCALATED`, and `waived` once the `tech_lead` accepts it. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every changed UI file was read in full; the scope lists each one with its task.
- [ ] Each finding has a severity, `path:line`, its criterion by number and name, who it blocks, and a fix.
- [ ] Tools ran only if the project had them; the manual review was done anyway.
- [ ] What could not be checked is listed.
- [ ] In verify: the gate text follows the rules above and passes speclint; open Critical and High findings are in Issues Found.
- [ ] In spec: an NFR with a threshold and scenarios for the keyboard and screen reader paths, handed to `sdd-spec`.
- [ ] No finding was dismissed or downgraded without the person.
