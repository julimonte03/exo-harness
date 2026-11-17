---
name: runbook-writer
description: >-
  Writes operational runbooks that someone can follow at 3 a.m. under
  pressure: what the alert or symptom means and its impact, how to confirm it,
  a diagnosis decision tree, mitigation steps with exact commands and the
  signal that proves each one worked, rollback, when and to whom to escalate,
  and how to test the runbook before it is needed. Commands come from the
  project (its scripts, manifests, pipelines and CLIs), never invented; every
  step that changes a system is marked, needs the operator's go-ahead, and
  says how to undo it. Use it when an alert has no fix path, a new service or
  job goes live, an incident depended on knowledge one person had, or someone
  asks to document an operational procedure. Triggers: "write a runbook",
  "create a runbook for this alert", "document the on-call procedure",
  "playbook for", "how do we fix this when it happens again", "operational
  procedure", "update the runbook", "this alert has no runbook".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# runbook-writer

A runbook is read by a tired person who did not write it, during an outage. It has to say what to do first, how to know whether it worked, and when to stop and call someone. Background goes last.

## Result

- **A runbook file** from `references/runbook-template.md`, in the project's runbook folder, one per alert or symptom.
- **Commands that exist:** each one checked against the project (a script, a Makefile target, a pipeline job, a manifest name, the CLI's help), with placeholders for what changes per environment.
- **Read-only steps and changing steps told apart:** every step that changes a system is marked `[changes state]`, says its undo, and is run only with the operator's go-ahead.
- **A link from the alert:** the change to the alert rule's runbook annotation, proposed for the person to apply.
- **A test plan** for the runbook and a "Last tested" line.

## When

- An alert fires and nobody knows what to do; a new service, job or dependency goes to production; an incident needed someone's tribal knowledge; a postmortem action asks for a runbook (skill:root-cause-5whys); an existing runbook was wrong during an incident.
- **Not for:** a design document, a postmortem (skill:incident-response), or a task that runs often enough to be automated: say so, and suggest the automation alongside the runbook.

## Rules

- **Action first.** The first screen says what the alert means and the first three things to check. Explanations go to Background.
- **Never invent a command.** Take it from the project: scripts, `Makefile`, `package.json` scripts, pipeline definitions, Helm values, Kubernetes manifests, Terraform, existing runbooks. Check its options with its help output when you can run it read-only. If you cannot confirm a command, write it with `(unverified)` and list it under the runbook's open questions.
- **Writing never runs.** While writing the runbook you may run read-only commands to confirm names and outputs, never one that prints a credential (Secret objects, `-o yaml` or `-o json` on secrets, `env` or `printenv`, `kubectl exec`: skill:incident-response, Rules); you never run a changing step "to see if it works". Testing a changing step happens in a non-production environment, with the person's approval (section Test).
- **Destructive steps need two things:** the explicit approval of the incident commander or service owner, written as a step, and a backup or a way back stated before it (data deletion, failover with possible data loss, purging a queue, restoring a backup over live data).
- **No secrets.** Commands read credentials from the place the team already uses (a secret store, the CLI's login, environment variables), shown as names (`$DB_PASSWORD` is never echoed). No tokens, passwords or connection strings with credentials in the runbook.
- **No personal data or contact details.** Escalate to roles and rotations.
- **Placeholders are explicit:** `<namespace>`, `<region>`, `<release>`, with where to find each value.

## Steps

### 1. Scope

- The trigger: an alert (its exact name and expression) or a symptom ("users report slow search").
- The service, its owners, its dependencies, and who will read this (first-line on-call, the owning team).
- Prerequisites: the access and tools the operator needs, and how to get them before the night they need them.

### 2. Gather the knowledge

- The alert rule and its threshold; the dashboards that show the signal.
- The code and configuration of the failing path: timeouts, retries, pools, queues, limits.
- Past incidents and postmortems for this alert; the existing runbook, if any, and where it was wrong.
- The people who fixed it before: ask the person to fill the gaps you cannot read, in one message with numbered questions.

### 3. Write the decision tree

Diagnosis as a short tree of observable checks, each leading to a mitigation or the next check:

```text
1. Is the error rate above 5% on all pods, or on some?
   - Some pods: go to M1 (restart the unhealthy pods).
   - All pods: go to 2.
2. Did a deploy finish in the 30 minutes before the alert?
   - Yes: go to M2 (roll back).
   - No: go to 3.
3. Is the database p99 latency above 200 ms?
   - Yes: go to M3 (database saturation) and escalate to the database rotation.
   - No: escalate to the service owner with the checks done so far.
```

### 4. Write the steps

Each mitigation step has the same parts:

```markdown
### M2. Roll back the last release [changes state]

Run only with the incident commander's go-ahead.

1. Find the previous release: `<release-tool> history <service> -n <namespace>` (read-only).
   Expected: a list with the current release on top; note the one below it.
2. Roll back: `<release-tool> rollback <service> <previous-revision> -n <namespace>`
   Expected: "Rollback was a success" within 2 minutes.
3. Verify: the 5xx ratio on dashboard <name> falls under 0.5% within 10 minutes.
   If it does not: go to Escalation.
Undo: roll forward with the same command and the revision noted in step 1.
```

- Exact, copyable commands with placeholders; the expected output; the signal that proves success; what to do if it does not appear.
- Prefer the project's own pipeline or scripts over raw commands: they carry its checks.
- Offer the dry-run form when the tool has one (`--dry-run=server`, `plan`, `--check`) before the real one.
- Keep steps idempotent where possible, so running one twice does no harm.

### 5. Rollback and escalation

- **Rollback** for every changing step, or "no undo: this is why it is safe" when there is none.
- **Escalation:** when (the time spent without improvement, the severity of skill:incident-response, a destructive step ahead) and to whom (roles and rotations), with what to hand over (the checks done, the steps run, the times).

### 6. Test the runbook

Pick the cheapest test that gives confidence, and record it in the runbook's "Last tested" line:

1. **Read-through** with someone who did not write it: every step understood without asking.
2. **Dry run** of the read-only steps against the real system, and of the changing steps in a non-production environment, with the person's approval.
3. **GameDay:** trigger the condition on purpose in a safe environment and follow the runbook (skill:chaos-engineering).

Review it after every use in an incident and at least every six months; a runbook nobody tested is a draft.

### 7. Link and publish

- Write the file as `<service>-<alert-slug>.md` in the folder the project uses for runbooks (look for `docs/runbooks/`, `runbooks/` or `ops/runbooks/`). If there is none, propose `docs/runbooks/` and create it only after the person says yes; until then, keep the runbook in the answer. Update the folder's index when it has one.
- Propose the alert change that points at it (for example a `runbook_url` annotation in a Prometheus rule), as a diff for the person: changing alert rules is a configuration change, not part of writing the runbook.
- **Inside an SDD change,** the runbook is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C). Until then, return its outline as text for the phase that owns the plan.

A full example is in `references/example-runbook.md`.

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "runbook-writer", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"runbook-writer"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The first screen says what the alert means and what to check first.
- [ ] Every command comes from the project or is marked `(unverified)` and listed as an open question.
- [ ] Every changing step is marked `[changes state]`, has an undo, and asks for the go-ahead; destructive steps name who approves and the way back.
- [ ] Every step has an expected output or a success signal, and the runbook has an escalation path by role.
- [ ] No secrets, personal data or contact details; a test plan and a "Last tested" line are present.
