---
name: chaos-engineering
description: >-
  Designs and runs chaos experiments that produce evidence about resilience:
  a question worth asking, a steady-state metric from the user's side, a
  falsifiable hypothesis, the smallest fault and blast radius that test it,
  objective abort conditions with a stop command checked beforehand, a run
  in a non-production environment first, a timestamped run log, and the
  findings turned into actions. Never injects a fault in production without
  the explicit, recorded approval of the service owner; it proposes every
  fault and stop command and waits for the go-ahead. Use it for resilience
  reviews, GameDays, failure injection, hardening before a launch, or to
  check that a fallback, a retry, a timeout or a failover really works.
  Triggers: "chaos test", "chaos engineering", "failure injection",
  "GameDay", "what happens if the database goes down", "resilience test",
  "test our failover", "kill a pod and see", "does the fallback work".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# chaos-engineering

A chaos experiment is a controlled test of a belief about the system: "if this dependency fails, users still check out". It is not breaking things to see what happens. The value is in the hypothesis, the safety around the fault, and what the team changes afterwards.

## Result

- **An experiment card** from `references/experiment-template.md`: the question, the steady state, the hypothesis, the fault and blast radius, the abort conditions, the stop command, the environment, the people informed, and the approvals.
- **A run log** with timestamps: what was injected, what was observed, when it stopped.
- **Findings:** whether the hypothesis held, time to detect and to recover, the surprises, and the alerts that fired or stayed silent.
- **Actions** with owners and checks, and the next experiment.

## When

- Before a launch or a peak, after an architectural change, to check a fallback, retry, timeout, circuit breaker or failover that has never been exercised, after an incident that revealed a weak spot, or to plan a GameDay.
- **Not:**
  - during an active incident, a change freeze, a peak event, or when on-call is short-handed;
  - on a system whose steady state cannot be observed live (first: SLIs with skill:slo-design and dashboards);
  - as a replacement for unit and integration tests of the retry or fallback code (skill:debug-systematically when they misbehave);
  - without a hypothesis.

## Safety rules

These hold for every experiment; no request overrides them.

1. **Non-production first.** The same experiment passes in a non-production environment before anyone considers production.
2. **Production needs explicit approval** from the service owner, recorded in the card with the date and the window, plus the on-call people informed. Without it, the experiment does not run in production, whatever else is said.
3. **Nothing runs without the full card:** hypothesis, live steady-state metric, abort conditions, a stop command, blast radius, time box, people informed.
4. **The agent proposes, the person runs or approves.** Every inject, observe and stop command is shown with what it does and how to stop it; it runs only after the go-ahead. The stop command is checked first (a dry run, or running it with no fault active).
5. **Smallest blast radius first:** one instance before a zone, latency before an outage, one percent of traffic before all of it. Widen only after a clean run.
6. **No faults that destroy data:** no deleting volumes, corrupting records or dropping tables, in any environment holding data someone needs. Data-loss scenarios are tested with restores into an isolated copy.
7. **Stay in scope:** never target shared dependencies, other teams' systems or third parties without their owners' agreement.
8. **Install nothing.** Use the fault tooling the project or platform already has (`references/fault-catalog.md`); if there is none, use manual injection (stopping a process, a firewall rule in a test environment) or propose a tool for the person to decide.

## Steps

### 1. Pick the question

Candidates come from past incidents and postmortems (skill:root-cause-5whys actions), dependencies without a fallback, recent architecture changes, and configuration nobody has seen work (timeouts, retries, failover). Rank by impact if the belief is wrong, times uncertainty. Pick one.

### 2. Define the steady state

A metric users feel, observed live, with its normal range: checkout success rate, p99 latency of the main API, orders per minute, messages processed per minute. Take it from the SLIs (skill:slo-design). Measure the normal range just before the experiment.

### 3. Write the hypothesis

`When <fault> happens to <target>, <steady-state metric> stays within <range> because <mechanism>.`

Example: "When one of the three cache nodes stops, checkout success stays above 99.5% and p99 under 900 ms, because the client fails over to the other nodes within 5 seconds." It must be falsifiable: a number, a range, a time.

### 4. Choose the fault and the blast radius

The smallest fault that tests the hypothesis, its target, the environment, and the time box (5 to 15 minutes is common). Faults by layer (instances, network, dependencies, resources, configuration, time), with the usual tools and their stop commands, are in `references/fault-catalog.md`.

### 5. Write the abort conditions and the stop

- **Abort when** any objective threshold is crossed: the steady-state metric leaves a wider safety range (for example success below 98% for 1 minute), an unrelated alert pages, a data integrity check fails, a system outside the scope degrades, or the time box ends.
- **Anyone can call abort,** and nobody argues during the run.
- **Stop:** the exact command or action that removes the fault, checked beforehand, and how to verify recovery (the metric back in its normal range).

### 6. Prepare

- Dashboards open for the steady state and for the target; the expected alerts listed.
- People informed: on-call for the environment, owners of the target and of anything it calls, and a channel for the run.
- Approvals recorded in the card (production always needs the service owner's).
- Rollback ready: what to do if the stop does not restore the steady state (restart, failover back, the runbook of skill:runbook-writer).

### 7. Run

1. Confirm the steady state is normal now. If not, do not start.
2. Propose the inject command; run it on the go-ahead; note the time.
3. Observe and log: the metric every minute, alerts, logs, what the system did.
4. Abort the moment a condition holds. Otherwise stop at the end of the time box.
5. Verify recovery and note the time.

Never widen the blast radius or add a second fault during a run: that is a new experiment with its own card.

### 8. Analyze

- **Hypothesis held or refuted,** with the numbers.
- **Time to detect** (did an alert fire, and when) and **time to recover** (automatic or manual).
- **Surprises:** behavior nobody expected, even if the metric held.
- **Observability gaps:** what you could not see.

A refuted hypothesis is a success of the experiment: it found a weakness before users did. If it caused real user impact, treat it as an incident (skill:incident-response) and learn from it like one.

### 9. Turn findings into actions

Each finding gets an action in the actions table of `references/experiment-template.md`, the same format as the rest of the pack: the finding it addresses, its type, an owner role, a due date and a check that proves it is done (often: "re-run this experiment and see it hold"). Runbooks that were wrong or missing go to skill:runbook-writer. Plan the next experiment, possibly one step wider.

## GameDays

A GameDay runs one or more experiments with the team present, to exercise people and runbooks as much as systems. The agenda, roles and debrief questions are in `references/experiment-template.md`, GameDay.

## Where it goes

- The folder the project uses for resilience work (look for `docs/chaos/`, `docs/resilience/` or `docs/gamedays/`), as `YYYY-MM-DD-<slug>.md`. If there is none, propose `docs/chaos/` and create it only after the person says yes; until then, keep the card in the answer.
- **Inside an SDD change,** the experiment card is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C). Until then, return the experiment design as text, also for the phase that owns an artifact that needs it (for example the Test Plan of design.md). Fault injection code or configuration is code: apply phase, when the plan lists it.

## Return

```markdown
Experiment: cache node loss (staging), 2026-03-10 10:00-10:15 UTC
Hypothesis: when 1 of 3 cache nodes stops, checkout success stays above 99.5% and p99 under 900 ms, because clients fail over within 5 s.
Fault: stop cache-node-2 in staging (proposed command shown; run by the person at 10:02).
Abort: (1) success below 98% for 30 s, or (2) any alert outside staging. Stop: start cache-node-2 (checked at 09:55).
Result: refuted. From 10:02:20 success fell to 96.8% and p99 reached 4.2 s. Abort called at 10:02:50 (abort condition 1); cache-node-2 started at 10:02:55; success back above 99.5% at 10:03:10.
Finding: the client keeps a 30 s DNS cache, so it retried the dead node until the entry expired.
Actions: A-1 set the client's DNS cache to 5 s (platform lead; check: re-run holds). A-2 alert on cache client errors (on-call lead).
Next: re-run in staging after A-1; production only with the owner's approval.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "chaos-engineering", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add decisions '{"summary": "Cache node loss experiment approved for staging only", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change, save surprising findings with skill:memory-protocol as a `discovery`.

## Before you finish

- [ ] The card is complete: hypothesis with numbers, live steady state, abort conditions, a checked stop, blast radius, time box, people informed.
- [ ] The experiment ran in non-production first; production, if any, has the service owner's recorded approval.
- [ ] Every inject and stop command was proposed and approved before it ran; nothing was installed.
- [ ] The run log has timestamps, and recovery was verified.
- [ ] Every finding has an action with an owner and a check.
