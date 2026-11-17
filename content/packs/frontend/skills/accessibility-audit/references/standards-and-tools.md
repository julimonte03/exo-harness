# Standards and tools

## Which standard

| Standard | What it is | How to use it here |
|---|---|---|
| WCAG 2.2 (W3C) | The web content guidelines; levels A, AA and AAA | The baseline: levels A and AA, criterion by criterion (`wcag-22-checklist.md`) |
| EN 301 549 | The European standard for accessibility of ICT products and services, used in public procurement and to meet the European Accessibility Act | Cite it only when the project must meet it; for web content it points back to WCAG level AA |
| ARIA Authoring Practices Guide (W3C) | How custom widgets should behave: roles, states, keyboard | The reference for every custom widget (`aria-patterns.md`) |

`.exo/context.md`, the proposal or the person may say which standard and version the project must meet (a contract, a public-sector rule, a market). When nothing says so, audit against WCAG 2.2 AA and say so in the verdict.

## EN 301 549 in practice

- **Web content** is its clause 9. In the versions based on WCAG 2.1, each web requirement is numbered `9.` followed by the WCAG criterion number: clause 9.1.4.3 is WCAG SC 1.4.3. Meeting WCAG 2.2 AA covers those requirements, because WCAG 2.2 keeps the WCAG 2.1 criteria apart from the obsolete 4.1.1 Parsing, which those versions still list.
- **Beyond web pages,** the standard has clauses for non-web documents (10), software and mobile apps (11), documentation and support services (12), and ICT with video (7: captions and audio description in players) or two-way voice (6). A web app that plays video, ships downloadable documents or offers support channels may fall under those too.
- **Versions change.** A revision aligned with WCAG 2.2 has been in preparation. Check the version the project must meet before citing a clause number, and cite it as `EN 301 549 <version> clause <n>`.
- When the project must meet the standard, add the clause next to the WCAG criterion in the gate's Rule/OWASP column: `WCAG 2.2 SC 1.4.3 Contrast (Minimum) (AA); EN 301 549 clause 9.1.4.3`.

## Automated tools

Optional. Use them only when the project already has them, through its own scripts or test command; never install one or fetch it to run it. Without them, the manual review is the audit.

| Tool | Where projects usually have it | What it reports |
|---|---|---|
| axe-core | `jest-axe` or `vitest-axe` in component tests; `@axe-core/playwright` or `cypress-axe` in end-to-end tests | Rule violations in the rendered DOM, tagged with WCAG criteria |
| pa11y, pa11y-ci | a script in the manifest or a CI step | Page-level violations, with axe or another runner |
| Lighthouse, Lighthouse CI | a CI step or an `lhci` config | An accessibility score from a subset of axe rules |
| Lint rules | `eslint-plugin-jsx-a11y`, `eslint-plugin-vuejs-accessibility`, the template rules of `angular-eslint`, the accessibility warnings of the Svelte compiler | Static problems in JSX and templates |

- Report the exact command, the number of violations, and each one mapped to its criterion and `path:line` when the tool gives it.
- **A clean run is not conformance.** Automated checks find only part of the failures (keyboard behavior, focus order, meaningful names and reading order need a person or a careful review). Always do the manual review.
- A tool that is not there is a follow-up, not a finding: "Consider adding `jest-axe` to the component tests" goes to the answer, never as a gate row.

## Reporting

- **One finding per failure and place,** even when several criteria apply: list them all in the Rule column.
- **Impact in plain words:** who is blocked (keyboard users, screen reader users, people with low vision, people who zoom, voice control users) and what they cannot do.
- **The fix as text:** the native element or the pattern to use, the attribute or style to add. Never apply it yourself in verify.
- **Not checked:** what needs the running UI, a real device or a screen reader, listed apart from the findings.
