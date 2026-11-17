---
name: slo-design
description: >-
  Designs service level objectives from the user's point of view: picks the
  user journeys that matter, defines SLIs as good events over valid events
  (availability, latency, freshness, correctness), sets targets and windows
  from the measured baseline and what users need, computes the error budget,
  turns it into multi-window burn-rate alerts that page only when the budget
  is really at risk, and writes the error budget policy. Tells SLIs, SLOs and
  SLAs apart. Writes the SLO document; alert rules are proposed in the
  project's own alerting format. Use it when a new service launches, when
  alerts are noisy or miss real outages, or when someone asks for SLOs, an
  error budget or an availability target. Triggers: "define SLOs", "SLI",
  "error budget", "burn rate alerts", "alert design", "what availability
  should we target", "our alerts are too noisy", "SLA vs SLO", "reliability
  targets for the new service", "how many nines".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: write-specs
---

# slo-design

An SLO is a promise about what users experience, with a budget for failure. It answers two questions for a team: are users happy enough, and can we afford to take risks this month. Alerts built on it page when users are hurt, not when a CPU graph looks scary.

## Result

- **An SLO document** per service, from `references/slo-template.md`: the user journeys, each SLI with its exact definition and measurement, the target and window, the error budget, the burn-rate alerts, the error budget policy, and the review date.
- **Alert rules proposed** in the format the project already uses (Prometheus rules, a cloud monitoring policy, a vendor's monitor definition), as a diff for the person.
- **Inside an SDD change,** the targets as non-functional requirements for the spec, returned as text (section Inside an SDD change).

## When

- A new service or a new critical journey goes to production; alerts are noisy, page for things users never notice, or stayed silent during an outage; someone asks for SLOs, an error budget, an availability target or a burn-rate alert; an incident consumed a lot of budget and the targets need review.
- **Not for:** sizing resources for a peak (skill:capacity-planning, which uses the SLO as its bar); running an incident (skill:incident-response); writing the runbook that an alert links to (skill:runbook-writer).

## Rules

- **From the user's side.** An SLI measures what a user experiences (a request served correctly and fast enough, data fresh enough), as close to the user as is reliable. CPU, memory and queue depth are causes to diagnose, not SLIs.
- **Measured, not invented.** Targets start from the baseline of the last weeks. Without data, say so: propose an initial target labeled as provisional and make measuring it the first action. Never present a number you did not measure as a baseline.
- **Not 100%.** No target is 100%: every dependency, deploy and network has failures, and a 100% target leaves no room to change anything.
- **Few SLOs.** One to three per journey. More dilutes attention.
- **SLA is a contract.** An SLA has consequences for the organization and belongs to whoever signs contracts; the internal SLO is stricter than any SLA so the team reacts before the contract is breached. This skill never changes an SLA.
- **The person decides the targets** and the policy; you propose them with the numbers that support them.
- **Proposing is not applying.** Alert rules and dashboards are configuration: they are proposed as a diff; applying them is a change the person asks for (inside an SDD change, it belongs to the apply phase).

## Steps

The SLI types with their measurement points and example queries are in `references/sli-menu.md`. The burn-rate math, the alert table and the rule examples are in `references/burn-rate-alerts.md`.

### 1. Journeys and users

List the critical user journeys of the service: sign in, search, checkout, the main API call, a nightly export. For each: who the user is (a person, another service, a partner), and what "working" means to them: fast, correct, fresh, available. Rank them; start with the top one or two.

### 2. Choose the SLIs

For each journey, the SLI as a ratio: **good events / valid events**, over a window.

- **Request-driven:** availability (requests answered without a server error), latency (requests answered faster than a threshold).
- **Pipelines and jobs:** freshness (data younger than a threshold when read), correctness, coverage.
- **Storage:** durability.

Write the **specification** (what it means in plain words) and the **implementation** (where and how it is measured: load balancer logs, server metrics, client telemetry, synthetic probes) with the exact query. Decide and write down the exclusions: health checks, requests rejected because of the client (most 4xx), traffic from load tests.

### 3. Measure the baseline

Compute each SLI over the last four weeks, or as long as data exists, with the query of step 2: the overall value, the worst day, and the incidents that dragged it down. Use the project's metrics, or logs when there are no metrics (skill:log-analysis). Write the source and the period.

### 4. Set target and window

- **Window:** a rolling 28 or 30 days is the common choice, and a rolling window has no reset: a bad day keeps counting until it leaves the window, while a calendar month forgets it on the first. Only 28 days holds whole weeks (four), so every weekday weighs the same; 30 days matches the monthly reports, but its mix of weekdays shifts as it rolls.
- **Target:** at or slightly below what the baseline shows the service already achieves when users are happy, and above the level where they complain. Check it against what each dependency can deliver: a service cannot be more available than the dependencies it needs on every request, unless it has a fallback.
- **The cost of each nine:**

| Target | Budget in 30 days |
|---|---|
| 99% | 7 h 12 min |
| 99.5% | 3 h 36 min |
| 99.9% | 43 min 12 s |
| 99.95% | 21 min 36 s |
| 99.99% | 4 min 19 s |

  A target whose budget is shorter than the time it takes to detect and roll back a bad deploy is a target the team will miss on every incident.

### 5. Error budget

Budget = 1 − target, as a share of the valid events in the window, and as minutes for a steady service. Example: 99.9% over 30 days with 10 million requests is 10,000 failed requests, or 43 minutes of full outage.

### 6. Burn-rate alerts

Alert on how fast the budget is being spent, not on every error. Burn rate 1 spends the whole budget exactly in the window; burn rate 14.4 spends 2% of a 30-day budget in one hour. The usual setup, with a long and a short window per alert so it fires fast and clears fast:

| Severity | Burn rate | Long window | Short window | Budget spent when it fires |
|---|---|---|---|---|
| Page | 14.4 | 1 h | 5 min | 2% |
| Page | 6 | 6 h | 30 min | 5% |
| Ticket | 1 | 3 days | 6 h | 10% |

Each alert links to its runbook (skill:runbook-writer). For low-traffic services, add a minimum request count or use longer windows (`references/burn-rate-alerts.md`, Low traffic). Propose the rules in the project's alerting format.

### 7. Error budget policy

Write what happens as the budget is spent, agreed with the service owner:

- **Budget left:** ship normally; planned risk (migrations, experiments) is fine.
- **Budget exhausted over the window:** pause risky releases, and put reliability work first until the SLI is back above target; exceptions for urgent fixes and security patches, approved by the owner.
- **One incident spends more than 20% of the budget:** it gets a postmortem (skill:incident-response, Postmortem).
- **Budget never touched for a quarter:** the target may be too loose, or the team too cautious; review it.

The policy is a decision tool, not a punishment.

### 8. Review

A review date (monthly at first, then quarterly): compare the SLI with user complaints and incidents, and adjust the SLI, the target or the alerts. Record each change and its reason in the document.

## Where it goes

- The folder the project uses for SLOs (look for `docs/slo/`, `slo/` or `docs/reliability/`), as `<service>.md`. If there is none, propose `docs/slo/` and create it only after the person says yes; until then, keep the document in the answer.
- Alert rules: proposed as a diff to the project's alerting configuration, for the person to apply.

## Inside an SDD change

- **Spec and design:** return the targets as text for the phase that owns the artifact: non-functional requirements in the format of `.exo/shared/sdd-phase-common.md`, section C, for `sdd-spec` to number (`CAP-<capability>-NFR-n`), for example "99.9% of checkout requests over a rolling 30 days are answered without a server error". Never write into the change root yourself.
- **The SLO document:** it is a project document, never a file of the change root: any phase may write it with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3 and 4; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C).
- **The alert rules** are configuration: the apply phase writes them when the plan lists them.

## Return

```markdown
Service: checkout-api. Journey: a customer confirms an order.
SLI (availability): confirm requests answered with a status other than 5xx / all confirm requests, excluding health checks; measured at the load balancer.
Baseline: 99.96% over the last 28 days (worst day 99.71%, during the 2026-03-02 incident).
Proposed SLO: 99.9% over a rolling 30 days. Budget: 43 min, or about 9,000 failed confirms at current traffic.
SLI (latency): confirm requests answered in under 800 ms / all confirm requests. Baseline 99.2%. Proposed SLO: 99% over 30 days.
Alerts: page at burn rate 14.4 (1 h and 5 min) and 6 (6 h and 30 min); ticket at 1 (3 days and 6 h); rules proposed for monitoring/rules/checkout.yml.
Policy: as in the template; owner to confirm.
Open: no client-side telemetry, so latency excludes the network to the customer.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "slo-design", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add decisions '{"summary": "Checkout availability SLO 99.9% over 30 days", "rationale": "baseline 99.96%; rollback takes about 15 minutes", "by": "human"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change, save the agreed targets with skill:memory-protocol as a `decision`.

## Before you finish

- [ ] Every SLI is a good-over-valid ratio from the user's side, with its exact query and exclusions.
- [ ] Every target comes from a measured baseline, or is labeled provisional with a plan to measure.
- [ ] No target is 100%, and each budget is longer than the time to detect and roll back.
- [ ] Alerts are burn-rate based, link to a runbook, and are proposed, not applied.
- [ ] The policy and the review date are written, and the person agreed to the targets.
