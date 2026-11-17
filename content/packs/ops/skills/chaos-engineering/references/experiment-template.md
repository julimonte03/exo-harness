# Experiment card and GameDay

## Experiment card

Copy this into the experiment file. Nothing runs until every field above "Run log" is filled and the approvals are recorded.

```markdown
# Chaos experiment: <short title>

- **Date and window:** YYYY-MM-DD HH:MM to HH:MM UTC
- **Environment:** <staging | test | production>
- **Status:** planned | approved | run | analyzed

## Question

What we believe and want to check, and why it matters (link to the incident, the postmortem action or the design that raised it).

## Steady state

- **Metric:** <user-facing metric, dashboard and query>
- **Normal range:** <range measured on YYYY-MM-DD>

## Hypothesis

When <fault> happens to <target>, <metric> stays within <range> because <mechanism>.

## Fault

- **What:** <fault>
- **Target:** <exact instance, service, route, percentage of traffic>
- **Blast radius:** <who and what can be affected, worst case>
- **Time box:** <minutes>
- **Inject command:** <exact command, to be proposed and approved before running>
- **Stop command:** <exact command> (checked on YYYY-MM-DD HH:MM)
- **Recovery check:** <the metric back in its normal range within N minutes>

## Abort conditions

- <metric beyond a safety range for N minutes>
- <any alert outside the target>
- <data integrity check fails>
- <time box ends>
Anyone can call abort.

## Preparation

- **Dashboards:** <names>
- **Expected alerts:** <names>, and which ones must not fire
- **People informed:** <on-call of the environment, owners of the target and its dependencies> on YYYY-MM-DD
- **Rollback if the stop fails:** <runbook or steps>

## Approvals

| Role | Decision | Date |
|---|---|---|
| Service owner | approved for <environment> | YYYY-MM-DD |
| On-call of the environment | informed | YYYY-MM-DD |

Production also requires: the same experiment passed in <non-production environment> on YYYY-MM-DD.

## Run log (UTC)

| Time | Action or observation |
|---|---|
| | Steady state confirmed: <value> |
| | Fault injected (approved by <role>) |
| | <observations every minute> |
| | Fault stopped (<reason: time box or abort rule n>) |
| | Recovery confirmed: <value> |

## Results

- **Hypothesis:** held | refuted, with the numbers
- **Time to detect:** <alert and time, or "not detected">
- **Time to recover:** <automatic or manual, minutes>
- **Surprises:**
- **Observability gaps:**

## Actions

| ID | Action | Owner (role) | Check |
|---|---|---|---|

## Next experiment

<the same at a wider radius, or a new question>
```

## GameDay

A GameDay runs planned experiments with the team present. It tests people, runbooks and communication as well as systems.

### Before

- Pick one to three experiments with complete cards; non-production unless the service owner approved production in writing.
- Name the roles: a facilitator (runs the agenda, calls aborts), an operator per experiment (runs the approved commands), observers who watch dashboards, a scribe, and the responders who will handle what happens, ideally people who did not design the experiment.
- Tell the people on call and the owners of nearby systems, with the window.
- Decide whether the responders know the fault in advance (a walkthrough) or not (a drill). Start with walkthroughs.

### Agenda (about two hours)

1. **Briefing (15 min):** goals, safety rules, abort conditions, roles, the stop commands.
2. **Steady state check (5 min):** dashboards normal; if not, postpone.
3. **Experiments (20 to 30 min each):** inject on approval, responders follow the runbook, the scribe logs, the facilitator watches the abort conditions.
4. **Recovery check (10 min):** everything back to normal, every fault removed.
5. **Debrief (30 min):** questions below, actions with owners.

### Debrief questions

- Did the hypothesis hold? What surprised us?
- How did we notice? How long did it take?
- Did the runbook work as written? Which step was wrong or missing?
- Did the right alerts fire, at the right severity, with a useful message?
- What would have happened at night, with one person on call?
- What do we change, who owns it, and how do we check it is done?

Write the debrief into each experiment card's Results and Actions.
