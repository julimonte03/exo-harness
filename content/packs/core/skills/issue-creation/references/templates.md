# Issue templates

The default bodies `issue-creation` uses when the repository has no template of its own, the title patterns, and where common trackers put each field. A repository template always wins. Tracker-specific details are **[Not verified]**: they change with the tracker's version and configuration.

## Bug

```markdown
## Summary

<One or two sentences: what fails, where, and for whom.>

## Steps to reproduce

1. <Known starting state: branch or version, seed data, account role>
2. <One action per step, with exact synthetic inputs>
3. ...

## Expected

<What should happen, and the source: spec ID, docs, or the earlier version that did it.>

## Actual

<What happens: the exact message, status or exit code, what the user sees.>

## Environment

- Version or commit: <...>
- Operating system: <...>
- Runtime and browser: <...>
- Configuration that matters: <names and non-secret values>

## Frequency

<Always | intermittent: about N out of M tries | once so far>

## Impact

<Who is affected, what they cannot do, workaround or none.> Suggested priority: <level> (<reason>).

## Evidence

<Short, cleaned excerpts: the error line and the frames in the project's code. path:line references.>

## Workaround

<What users can do meanwhile, or "None known".>

## Hypothesis

<Optional. Suspected cause, with path:line and the commit; clearly not a confirmed cause.>

## Related

<Other issues, the change or the PR that may have introduced it.>
```

## Feature request

```markdown
## Problem

<Who has the problem (a role), in which situation, and what it costs them today. Evidence when there is any.>

## Proposal

<What should be possible, described as behavior, not as a screen or a technical solution.>

## Acceptance criteria

1. Given <state>, When <action>, Then <observable result>.
2. ...

## Alternatives considered

<Other ways to solve it, including doing nothing, and why the proposal is better.>

## Out of scope

<What this request does not ask for.>
```

A request that is still fuzzy (no clear user, problem or value) is better served by a discovery first: `product-discovery` (pack `product`) when the project has it.

## Task or technical debt

```markdown
## What

<The work, in one or two sentences.>

## Why now

<The cost of leaving it: incidents, slowness, risk, blocked work. Evidence.>

## Done when

- <Observable condition, for example "the test suite runs without the deprecation warnings of <library>">

## Notes

<Constraints, related code (path:line), risks.>
```

## Titles

| Weak | Better |
|---|---|
| Bug in checkout | Checkout returns 500 when the coupon has expired |
| Login broken | Sign-in loops back to the form after a password reset on Safari |
| Slow | Order history takes over 10 seconds with more than 500 orders |
| Fix coupons | Expired coupons are accepted when the cart has one item |
| New feature: delivery | Customers can reschedule a delivery before dispatch |
| Refactor | Replace the deprecated date library in invoices |

Pattern for bugs: **symptom + where + condition**. For features: **who + can + capability**. For tasks: **verb + object + reason when short**.

## Repository templates

- **GitHub:** Markdown templates and issue forms (`.yml`) live in `.github/ISSUE_TEMPLATE/`. An issue form shows labeled fields; answer each one under its label, and respect its required fields and dropdown options. A `config.yml` there may disable blank issues or point security reports elsewhere.
- **GitLab:** Markdown templates live in `.gitlab/issue_templates/`; the person picks one when creating the issue.
- **Other trackers** keep templates in the tracker itself, not in the repository: ask the person for the fields their tracker shows, or use the defaults above.

## Where fields land [Not verified]

| Default section | Jira | Azure Boards (Bug) | GitHub or GitLab |
|---|---|---|---|
| Title | Summary | Title | Title |
| Steps, expected, actual | Description | Repro Steps | Body |
| Environment | Environment field, when the project uses it; otherwise Description | System Info | Body |
| Suggested priority | Priority (the team sets it on triage) | Priority and Severity | A label, when the repository uses priority labels |
| Kind | Issue type (Bug, Story, Task) | Work item type (Bug, User Story, Product Backlog Item, Task) | A label (`bug`, `enhancement`) or an issue type, when configured |

The person files it in the tracker's web page, by import, or with the tracker's CLI; this skill writes the text and never runs any of them.
