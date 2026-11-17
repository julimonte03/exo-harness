---
name: root-cause-5whys
description: >-
  Finds the root cause of an incident, a bug or a recurring failure with 5
  Whys: a precise problem statement, a chain of causes where every link has
  evidence, the trigger told apart from the systemic causes that let it have
  impact, and one branch per cause when there is more than one. Knows when 5
  Whys is not enough and switches to a fault tree or a list of contributing
  factors. Blameless: it asks why the system allowed the mistake, never who
  made it. Ends with actions that prevent or detect each cause, each with an
  owner role and a check that proves it is done. Use it after an incident,
  in a postmortem, after fixing a bug that should not have reached users, or
  when the same failure keeps coming back. Triggers: "root cause", "5 whys",
  "why did this happen", "RCA", "postmortem analysis", "how do we prevent
  this from happening again", "it happened again", "contributing factors".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# root-cause-5whys

The trigger is what happened last; the root cause is what let it hurt. A deploy with a bug is a trigger. The missing test, the review that could not see the risk, and the alert that fired late are the causes worth fixing.

## Result

- **A problem statement** that is specific, observable and free of any cause.
- **One or more why-chains,** each link a fact with its evidence or a hypothesis marked as such with how to verify it.
- **The causes, classified:** the trigger, the causes it passed through (why it happened, why it was not caught, why the impact was so large), and the contributing factors.
- **Actions:** each one tied to a cause, typed (prevent, detect, mitigate, process), with an owner role, a due date and a check that proves it is done.

It goes in the postmortem's section "Root cause and contributing factors" when one exists, in the file the person names, or in the answer.

## When

- After an incident is mitigated (skill:incident-response, section Postmortem), after a bug fix that reached users, or when the same failure returns.
- **Not during the incident:** mitigation comes first. Note hypotheses in the timeline and analyze later.
- **Not to find the defect itself:** that is debugging (skill:debug-systematically). This skill explains why the defect existed, why nothing caught it and why it hurt as much as it did.
- **Never for blame,** performance reviews or deciding who pays for the outage.

## Rules

- **Evidence for every link.** A commit, a `path:line`, a log query, a metric, a document, a timeline entry. A link without evidence is a hypothesis: write `Hypothesis:` and the check that would confirm it.
- **Blameless language.** "The pipeline allowed a migration without a dry run", never "the engineer forgot". When the answer to a why is a person's action, ask why the system made that action easy, likely or invisible. Phrasing guide in `references/beyond-5whys.md`, Blameless language.
- **Stop at something you can change.** A cause in the system: a design, a default, a test, a check, an alert, a process step, a missing tool. "Human error", "bad luck", "not enough time" and "the vendor failed" are not root causes; ask one more why about what we control.
- **More than one cause is normal.** Follow each branch; do not force a single line.
- **No personal data or names** in the analysis; roles and services only. Clean excerpts with skill:prompt-hygiene (when the security pack is not installed: `security/prompt-hygiene not installed — applying inline criteria`, with the inline criteria of `.exo/shared/phase-skill-map.md`).

## Steps

### 1. State the problem

One or two sentences: what happened, where, when, and the impact, measured. No cause and no blame in it.

- Good: "Between 14:05 and 14:32 UTC on 2026-03-02, about 30% of checkout requests failed with HTTP 500."
- Bad: "The bad deploy broke checkout." (a cause, and a vague one)

### 2. Gather the facts

The incident timeline, the diff and the PR of the suspect change, the tests and the pipeline run, logs and metrics around the start (skill:log-analysis), the alerts and when they fired, and the runbook used. Read only what you need; for four or more files inside an SDD change, delegate the reading as `.exo/shared/sdd-phase-common.md`, section G, says.

### 3. Ask why, three times over

Run the chain for three questions. Each one usually ends in a different cause:

1. **Why did it happen?** From the symptom back to the trigger and beyond.
2. **Why was it not caught earlier?** Tests, review, static checks, staging, canary, alerts.
3. **Why was the impact so large?** Blast radius, rollout speed, missing fallback, time to detect, time to mitigate.

For each answer: "Why?" again, until the stop rule holds. Five is a guide, not a quota: two can be enough, seven can be needed.

```text
Problem: 30% of checkout requests failed with 500 for 27 minutes.
Why 1: checkout-api threw a column-not-found error on every order with a coupon. [log query <name>, 14:05-14:32]
Why 2: v2.41.0 read the column coupon_code, renamed to promo_code by the payments schema migration the day before. [commit <sha>, migration <file>:12]
Why 3: the rename shipped without the consumers being updated. [PR <link> has no consumer change]
Why 4: nothing checks the consumers of a shared table when its schema changes. [no contract test; CI config <file>]
Root cause (happened): shared tables change without a consumer contract check.

Why not caught: the staging data set has no orders with coupons. [seed script <file>:40]
Root cause (not caught): staging data does not cover the coupon path.

Why so large: the release went to 100% of pods at once. [deploy config <file>:8]
Root cause (impact): no canary step for checkout-api.
```

### 4. Branch when an answer has two causes

When a why has two true answers, follow both. Draw them as a small tree in text when it helps. A cause shared by several branches is usually the most valuable one to fix.

### 5. Check the chain backwards

Read it from the root to the symptom with "therefore": "Shared tables change without a consumer check, therefore the rename shipped without the consumers, therefore checkout read a column that no longer existed, therefore orders with a coupon failed." If a "therefore" does not follow, a link is missing or wrong.

### 6. Know when 5 Whys is not enough

Switch technique, and say so, when:

- several conditions had to hold at the same time (only fails with high load **and** a cold cache **and** the new client): use a fault tree with AND and OR gates;
- there is no single chain, but many small factors (a confusing dashboard, a stale runbook, a tired on-call, a noisy alert): list the contributing factors by category;
- the failure is intermittent and the evidence is thin: write the competing hypotheses and the data needed to choose, instead of a chain that pretends to be certain.

Both techniques, with templates, are in `references/beyond-5whys.md`. A complete worked example is in `references/worked-example.md`.

### 7. Turn causes into actions

At least one action per root cause, preferring, in this order:

1. **Prevent:** remove the cause (a contract test, a safer default, a guard in the code, a schema change process).
2. **Detect:** catch it earlier (a test in CI, a canary, an alert on the right signal).
3. **Mitigate:** limit the impact (gradual rollout, a fallback, a faster rollback).
4. **Process:** a checklist or a review step, only when the three above are not possible.

Each action has:

- **a check** that proves it is done ("a branch that renames a shared column fails CI", not "improve testing");
- **an owner role** and a due date, agreed with the person;
- **a ticket** when the project tracks work: with `tickets.pattern` in `.exo/config.json`, the person files it and gives you the ID; never invent one.

"Be more careful", "communicate better" and "add more monitoring" are not actions.

## Write it

```markdown
## Root cause and contributing factors

**Problem:** between 14:05 and 14:32 UTC, about 30% of checkout requests failed with HTTP 500.

**Trigger:** release v2.41.0 of checkout-api read a column the payments migration had renamed the day before.

| Question | Root cause | Evidence |
|---|---|---|
| Why it happened | Shared tables change without a consumer contract check | migration <file>:12; CI config <file> |
| Why it was not caught | Staging data has no orders with coupons | seed script <file>:40 |
| Why the impact was large | checkout-api releases go to every pod at once | deploy config <file>:8 |

**Contributing factors:** the alert threshold (2%) fired after 2 minutes only because traffic was high.

| ID | Action | Root cause | Type | Owner | Due | Check |
|---|---|---|---|---|---|---|
| A-1 | Contract test for consumers of the payments tables | No consumer check | prevent | payments tech lead | YYYY-MM-DD | A rename on a branch fails CI |
| A-2 | Coupon orders in the staging seed | Staging data gap | detect | QA lead | YYYY-MM-DD | The seed creates coupon orders; smoke test covers them |
| A-3 | Canary step at 10% for 15 minutes | No canary | mitigate | platform lead | YYYY-MM-DD | Pipeline shows the canary stage on the next release |
```

- **Where it goes:** the postmortem, started from the template of skill:incident-response, when it exists; otherwise the file the person names, or the answer. Inside an SDD change, never write into the change root: return the analysis as text for the phase that owns the artifact (for example the Intent of the fix's proposal.md).
- **Outside a change,** save the root cause with skill:memory-protocol (`exo mem save --type bugfix` or `--type gotcha`), without personal data.

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "root-cause-5whys", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"root-cause-5whys"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The problem statement is measurable and holds no cause.
- [ ] Every link has evidence, or is marked as a hypothesis with its check.
- [ ] The three questions (happened, not caught, impact) each have a root cause or a reason why not.
- [ ] No root cause is "human error"; the language is blameless and has no names.
- [ ] Every root cause has an action with an owner role, a due date and a verifiable check.
