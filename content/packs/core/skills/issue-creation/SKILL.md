---
name: issue-creation
description: >-
  Writes issues the team can act on, for whatever tracker the project uses:
  bug reports with a specific title, context, minimal steps to reproduce,
  expected against actual result, environment, frequency, impact and a
  suggested priority, and evidence without secrets or personal data; and
  feature requests with the problem, who has it, the proposal and acceptance
  criteria. It follows the repository's issue templates when there are any,
  never invents an ID (the tracker assigns it, and the ID the person brings
  back is checked against tickets.pattern), keeps vulnerabilities out of
  public trackers, and calls no tracker API: it writes the text or a file,
  and the person files it. Use it when someone wants to report a bug, open an
  issue, file a feature request, or turn an error, a log or a failing test
  into a ticket. Triggers: "create an issue", "report a bug", "open a
  feature request", "file a ticket for this error", "write up this bug",
  "turn this stack trace into an issue".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-specs
---

# issue-creation

## Result

- **An issue ready to file:** its kind (bug, feature request or task), a title, a body in the repository's template or the default one, suggested labels and priority, and the related items.
- **A bug** carries a summary, the environment, the steps to reproduce, the expected and the actual result, the frequency, the impact with a suggested priority, the evidence (cleaned), a workaround when there is one, and the suspected cause marked as a hypothesis.
- **A feature request** carries the problem and who has it, the proposal, acceptance criteria in Given/When/Then, the alternatives and what is out of scope.
- **The person files it.** Afterwards, the ID they bring back is checked against `tickets.pattern`, and the issue can start an SDD change.

## When

- **A bug shows up** while working: a failing test, an error in the logs, behavior that contradicts the spec or the docs.
- **Someone asks** to report a bug, open an issue, file a feature request, or log technical debt as a task.
- **An error, a stack trace or a failing test** has to become a ticket.
- **A bug outside the scope of the current change:** file it instead of fixing it there.
- **Not for:** refining an existing backlog item (`refinement-assistant`, pack `product`); work items from an approved plan (`work-item-creator`, pack `product`); a security vulnerability in a public tracker (step 2); a production incident in progress, which follows the team's incident process; fixing the bug, which is a change of its own.

## Inputs

1. **What happened:** the person's description, the error, the failing test, the log excerpt.
2. **The repository's rules:** issue templates (`.github/ISSUE_TEMPLATE/`, `.gitlab/issue_templates/`), `CONTRIBUTING.md` and `SECURITY.md` when they exist, and `.exo/context.md` for versions and commands.
3. **The code involved,** with `path:line` (skill:context-retrieval), and `git log` for a recent change that may explain it.
4. **The environment:** the version or commit (`git rev-parse --short HEAD`), the operating system, the runtime and browser versions, and the configuration that matters (names and non-secret values).
5. **The ticket settings:** `tickets.pattern` and `tickets.example` in `.exo/config.json`.

## Steps

The default templates, the title patterns and the tracker fields are in `references/templates.md`; cleaning evidence and the priority scale in `references/evidence-and-priority.md`.

### 1. Pick the kind and the template

- Bug, feature request or task.
- **The repository's template wins:** fill every field it asks for, in its order. An issue form (a `.yml` template) has labeled fields: answer each one under its label.
- Without a template, use the default in `references/templates.md`.
- One problem per issue. Two symptoms with possibly different causes are two issues that link each other.

### 2. Keep vulnerabilities private

If the bug lets someone bypass access control, inject code or queries, read data they should not, or exposes a secret:

- Do not draft a public issue. Say why, and point at `SECURITY.md` or the private reporting channel the project names; without one, ask the person who handles security reports.
- Draft the private report with what is needed to understand and fix it, and no working exploit.
- A secret in the evidence is never copied: point at `path:line` and tell the person to remove it and rotate it.

### 3. Reproduce it (bugs)

- **Minimal steps** from a known state (a fresh install, a given branch, a seed), numbered, one action each, with exact inputs: synthetic values only.
- **Try it** when it is safe and cheap: a command or a test that reproduces it is the best evidence. Name it, with its output. If you could not reproduce it, say so, and how often the person sees it.
- **Expected,** with its source: the spec (`CAP-<capability>-FR-n`), the docs, or the behavior of an earlier version.
- **Actual:** the exact message, status code or exit code, and what the user sees.

### 4. Write the environment

The version or commit, the operating system, the runtime and browser versions, the configuration flags that matter (names and non-secret values), and the data conditions, described ("an order with three items and an expired coupon"), never copied from production.

### 5. Add the evidence, cleaned

- Short excerpts: the error line and the frames of the stack that point at the project's code, up to about 20 lines.
- Before anything goes in, apply `prompt-hygiene` (pack `security`). Without it, say `security/prompt-hygiene not installed — applying inline criteria` and remove secrets, tokens, personal data, customer identifiers and, for a tracker outside the organization, internal hostnames and URLs; write `<redacted>` where something was removed.
- Screenshots: say what they show, and crop or blur personal data before attaching them.
- The tracker is an external system: Internal data only in the organization's own tracker, and only Public data in a public one (`.exo/shared/data-protection.md`, section C).

### 6. Suggest impact and priority

Who is affected (which roles, how many), what they cannot do, whether there is a workaround, and whether data, money or security is at risk. Map it to the team's scale, or to the default in `references/evidence-and-priority.md`, and label it **suggested**: the team triages.

### 7. Write the title

- **Bug:** the symptom, where, and the condition: "Checkout returns 500 when the coupon has expired". Never "Bug in checkout" or "Fix coupons".
- **Feature request:** the capability and who gets it: "Customers can reschedule a delivery before dispatch".
- Up to about 80 characters, no ID: the tracker adds it.

### 8. Separate facts from hypotheses

A suspected cause goes under its own heading, `Hypothesis`, with `path:line` and the commit that may have introduced it. Never present it as the cause, and never turn the issue into a redesign.

### 9. Deliver

- The text in the answer, or a file the person names, outside any change folder; committed during a change, that file is a project document, written with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C). The person files it, in the tracker's web page or with its CLI; this skill never runs a tracker's CLI or API.
- **Duplicates:** this skill cannot search the tracker. Ask the person to check for an existing issue with the key words of the title before filing.
- **The ID, once filed:** with a ticket pattern, check the ID the person brings back against it (the whole ID has to match). If it does not, say so with `tickets.example` and ask once more. Never invent one; without a pattern, there is no ID to check.
- **Next:** if the project has the `sdd` pack and the person wants to fix it now, offer to start a change with `sdd-new`. It asks for the ticket once (`.exo/shared/sdd-phase-common.md`, section E), and the person answers with the issue's ID; never pass the ID on yourself.

## Return

```markdown
**Title:** Checkout returns 500 when the coupon has expired

**Kind:** bug · **Suggested priority:** high (see Impact)

## Summary
Submitting the checkout form with an expired coupon returns a 500 page instead of the "coupon expired" message.

## Steps to reproduce
1. On branch main (commit `<short-sha>`), run `make dev` and seed the demo data: `make seed`.
2. Add any product to the cart and enter the coupon `EXPIRED10` (expired in the seed data).
3. Submit the checkout form.

## Expected
The form shows "This coupon has expired" and keeps the cart (CAP-coupons-FR-2, scenario S-3).

## Actual
A 500 error page instead of the message; the order is not placed.

## Environment
Commit `<short-sha>`, Python 3.12, Chrome 131 on Windows 11; default configuration.

## Frequency
Always, with any expired coupon.

## Impact
Every shopper who enters an expired coupon is blocked at checkout, and nothing tells them that removing the coupon lets them continue. No data or money at risk. Suggested priority: high (it blocks a core journey with no workaround users can find).

## Evidence
Server log at step 3: `KeyError: 'discount'`, raised at `src/api/checkout.py:88` and called from `src/api/routes.py:31`. The excerpt holds no personal data.

## Workaround
Remove the coupon before submitting; support can tell shoppers to do so.

## Hypothesis
`apply_coupon` returns `None` for expired coupons since `<short-sha>` (`src/coupons/rules.py:40`), and checkout reads `result["discount"]` without checking.

## Related
Possibly introduced by commit `<short-sha>` (see Hypothesis). No known duplicate: search the tracker for "expired coupon" before filing.
```

Then: "File it in your tracker; send me the ID if you want me to check it, or to start a change to fix it."

## Rules

- **No tracker access.** Never call a tracker's API or CLI, and never create, edit or close an issue: the person does.
- **No invented IDs.** The tracker assigns them; you check the one the person brings back.
- **Clean evidence.** No secrets, no personal data, no customer identifiers; vulnerabilities go to the private channel.
- **Facts apart from hypotheses.**
- **The repository's templates win** over the defaults here.

## Record

Inside an SDD change (for example, a bug found during apply that is outside the plan), a phase that runs inline records the decision before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "issue-creation", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add decisions '{"summary": "Out-of-scope bug filed by the person as PROJ-610 instead of fixing it in this change", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] The kind and the template are right, and every field the template asks for is filled.
- [ ] A vulnerability went to the private channel, not to a public issue.
- [ ] The steps are minimal and numbered, with expected (and its source) against actual.
- [ ] The environment and the frequency are stated.
- [ ] The evidence is short and clean: no secrets, personal data or customer identifiers.
- [ ] The title names the symptom, the place and the condition; the priority is labeled suggested.
- [ ] The hypothesis is separate; no ID was invented.
