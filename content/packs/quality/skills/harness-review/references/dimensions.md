# harness-review: checklists by dimension

The detail behind the four dimensions of `SKILL.md`. Use what applies to the change; every finding still needs its `path:line`.

## Engineering

### Coverage

- For each requirement ID of the delta: the test that proves it, and the run where you saw it pass.
- For each scenario `S-n`: the test exists, its Arrange, Act and Assert follow the Given, When and Then, and it asserts what can be observed (output, state, calls at the boundary).
- The test fails without the behavior. Warning signs: it asserts only on mocks, asserts something always true, or catches the very error the scenario expects to see.
- Every scenario whose Then rejects or fails has its own test.

### Drift

- Files that no task or Scope item names.
- Reformatting or renaming in code the change did not need to touch.
- New dependencies, lockfile changes, CI or build changes that the plan does not mention.
- Generated files committed without the plan asking for them (build output, coverage reports).

### Leftovers

Examples by language family; follow the project's own tools and conventions.

| Family | Look for |
|---|---|
| Python | `print(` used for debugging, `breakpoint()`, `import pdb`, `pytest.mark.skip` without a reason |
| JavaScript and TypeScript | `console.log`, `debugger`, `.only(`, `fit(`, `xit(`, a new `@ts-ignore` without a reason |
| Java and Kotlin | `System.out.println`, `printStackTrace()`, `@Disabled` without a reason |
| Any | commented-out blocks, hard-coded local paths or ports, temporary files, sleeps added to make a test pass |

A `TODO` that the change adds without an owner or a ticket is a Low finding. Never delete existing `TODO`s, and never ask for that.

### Commands

- The exact test command from `.exo/context.md` (Commands), then the lint and the build.
- Per command: the command line as you ran it, the passed and failed counts, and each pre-existing failure with its evidence.

## Security, light pass

| Look for | Reference |
|---|---|
| Untrusted input in a query, a shell command or a template | OWASP A03:2021 Injection |
| Untrusted input in a file path | OWASP A01:2021 Broken Access Control (CWE-22) |
| A new entry point without an authorization check | OWASP A01:2021 Broken Access Control |
| A new entry point without authentication, or weak session handling | OWASP A07:2021 Identification and Authentication Failures |
| Credentials in code, config or tests | CWE-798; `.exo/shared/data-protection.md` |
| Deserialization of untrusted data | OWASP A08:2021 Software and Data Integrity Failures |
| Stack traces or internals shown to users | OWASP A05:2021 Security Misconfiguration |
| Secrets or personal data in logs | OWASP A09:2021 Security Logging and Monitoring Failures |
| A new or upgraded dependency | OWASP A06:2021 Vulnerable and Outdated Components |

Anything that needs more than reading the diff (data flows across modules, the threat model, the full OWASP review) goes to `security-code-review`.

## UX/UI

- **States:** loading, empty, error, success and partial results; long text, many items, a slow network.
- **Copy:** says what happened and what to do; no internal codes or stack traces shown to users; the same terms as the rest of the product.
- **Interaction:** destructive actions confirm or can be undone; forms keep what the user typed after an error; no dead ends.
- **Consistency:** the existing components and design tokens; spacing and typography follow the design system.
- **Layout:** it holds at the breakpoints the project supports; nothing overflows or overlaps.
- **Command line and APIs:** help text for new options, exit code 0 only on success, errors on stderr, error formats and status codes consistent with the rest of the project.

## Accessibility: WCAG 2.2 AA criteria to check first

Review the changed markup, styles and behavior. When the project's test command includes accessibility checks, report their results too; do not add or run other tools.

| SC | Name (level) | Check in the changed UI |
|---|---|---|
| 1.1.1 | Non-text Content (A) | Images and icons that carry meaning have a text alternative; decorative ones are hidden from assistive technologies |
| 1.3.1 | Info and Relationships (A) | Headings, lists, tables and form groups use the right semantics, not only styling |
| 1.4.3 | Contrast (Minimum) (AA) | Text has a contrast ratio of at least 4.5:1, or 3:1 for large text |
| 1.4.10 | Reflow (AA) | Content works at 320 CSS pixels wide without scrolling in two directions |
| 1.4.11 | Non-text Contrast (AA) | Controls, focus indicators and meaningful graphics have at least 3:1 against what is next to them |
| 2.1.1 | Keyboard (A) | Everything works with the keyboard alone, and focus never gets trapped (2.1.2) |
| 2.4.3 | Focus Order (A) | Focus moves in an order that keeps the meaning |
| 2.4.7 | Focus Visible (AA) | The focused element is visibly marked |
| 2.4.11 | Focus Not Obscured (Minimum) (AA, new in 2.2) | Sticky headers, banners and dialogs do not hide the focused element entirely |
| 2.5.7 | Dragging Movements (AA, new in 2.2) | Anything done by dragging also works with a single pointer, without dragging |
| 2.5.8 | Target Size (Minimum) (AA, new in 2.2) | Pointer targets are at least 24 by 24 CSS pixels, or have enough space around them |
| 3.2.6 | Consistent Help (A, new in 2.2) | Help links and contact options keep the same relative place across pages |
| 3.3.1 | Error Identification (A) | Input errors are described in text, next to the field |
| 3.3.2 | Labels or Instructions (A) | Every input has a visible label or instructions |
| 3.3.7 | Redundant Entry (A, new in 2.2) | Information the user already gave in the same process is filled in or offered, not asked again |
| 3.3.8 | Accessible Authentication (Minimum) (AA, new in 2.2) | Signing in does not depend on memorizing or transcribing something, unless paste and password managers work |
| 4.1.2 | Name, Role, Value (A) | Custom controls expose their name, role and state to assistive technologies |
| 4.1.3 | Status Messages (AA) | Status changes (saved, failed, results loaded) are announced without moving the focus |

Each failure is a finding with its criterion: `WCAG 2.2 SC 1.4.3`.
