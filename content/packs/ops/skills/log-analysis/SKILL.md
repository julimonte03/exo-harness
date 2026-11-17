---
name: log-analysis
description: >-
  Analyzes logs whatever the tool: exported files, raw text, JSON lines, or
  query results from Elastic, OpenSearch, Loki, CloudWatch, Datadog, Splunk
  or journald. Identifies the format and the time zone, groups errors by
  normalized message, finds spikes and the minute they started against a
  baseline, spots signatures that are new, correlates them with deploys,
  configuration changes, traffic and infrastructure events, follows requests
  by ID, and tells the first cause apart from the downstream noise. Read-only,
  and never copies secrets or personal data from the logs into the
  conversation. Use it when someone shares a log file or an export, asks
  what is going on in the logs, sees a spike in errors, or wants to compare
  logs before and after a deploy. Triggers: "analyze this log", "what's going
  on in these logs", "pattern in the logs", "spike in errors", "why so many
  errors since", "group these errors", "parse this log file", "compare the
  logs before and after the deploy", "is this error new".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: read-only
---

# log-analysis

A log is evidence with a lot of noise. This skill turns it into a few facts: when the problem started, which errors are new, what they correlate with, and which one came first. It works on any source; skill:kibana-logs is the companion that finds the lines in an Elastic or OpenSearch stack.

## Result

- **The shape of the data:** source, format, time zone, time span, volume, fields available.
- **Rates against a baseline:** errors per minute by level, status, service or host, and the minute the problem started.
- **Error groups:** normalized signatures with count, first seen, last seen and where they appear, marking the ones that are **new** in the window.
- **Correlations:** with deploys, configuration and feature flag changes, traffic, dependency errors and infrastructure events, each with its timestamp.
- **A conclusion** with confidence and evidence: the earliest new signature, what looks like cause and what looks like symptom, and the next check.

## When

- Someone shares a log file, an export or query results; asks what is happening in the logs; sees a spike; wants a before and after comparison around a deploy.
- **Not for:** searching a log stack (Kibana, OpenSearch) or the runtime's logs where they live (skill:kibana-logs), declaring and running an incident (skill:incident-response), or fixing the bug once found (skill:debug-systematically).

## Rules

- **Read-only.** Read and filter with tools that only read (`grep`, `jq`, `awk`, `sort`, `uniq`, PowerShell's `Select-String` and `ConvertFrom-Json`). Install nothing; if a tool is missing, use another or say the command.
- **Clean first.** Before any excerpt reaches the conversation, a document or a subagent, remove secrets and personal data (skill:prompt-hygiene; when the security pack is not installed: `security/prompt-hygiene not installed — applying inline criteria`, with the inline criteria of `.exo/shared/phase-skill-map.md`). Prefer counts and normalized signatures to raw lines. A secret found in a log is pointed at (`file:line`), never copied; tell the person to rotate it.
- **Work on a slice.** Extract the window you need into your work folder, outside the repository, and never paste a whole log. Delete the slice when you are done.
- **Facts, then interpretation.** Every claim cites its count and window; correlation is not causation, so say how confident you are.
- **UTC.** Convert every timestamp to UTC, and say which time zone the source used.

## Steps

Commands for each step, in POSIX shell and PowerShell, are in `references/recipes.md`. Formats, timestamps and the normalization rules are in `references/formats.md`.

### 1. Inventory

- Where the log comes from (service, host, platform), and how it was exported.
- **Format:** JSON lines, logfmt, a web server access log, syslog, a framework's text format, multi-line stack traces.
- **Time:** the timestamp field and its time zone, first and last timestamps, gaps (a gap can be the outage itself, or a log shipper that stopped).
- **Volume:** lines in total and per minute.
- **Fields:** level, service, message, error type, status, path, request or trace ID, host, version.

### 2. Parse and slice

Turn each line into a record with at least time, level and message; join multi-line stack traces to their first line. Keep the window from about 30 minutes before the reported start to the end, plus a **baseline window** of the same length when things were normal (the same hours a day or a week before, or the hour before the start).

### 3. Rates and the start

Count per minute, by level, by status code, by service or host, in both windows. The start is the first minute where the rate leaves its baseline range and stays out. Report it with the numbers: "errors per minute went from 0 to 3 in the baseline to 60 to 90 from 14:05 UTC".

### 4. Group into signatures

- Normalize each message: replace numbers, UUIDs, hex IDs, emails, IPs, quoted values and path segments that hold IDs with placeholders, so that "order 123 not found" and "order 456 not found" become one signature (`references/formats.md`, Normalization).
- For each signature: count, first seen, last seen, hosts or pods, versions.
- **New signatures** (present in the window, absent or rare in the baseline) are usually where the answer is. Signatures with the same rate in both windows are background noise; set them aside and say so.

### 5. Correlate

Line up the start and the new signatures against what changed, with timestamps:

- **Deploys:** release tags, the CI or deploy history, the `version` field in the logs, container image changes, pod restarts.
- **Configuration and feature flags:** changes in the repository (`git log --since`), in the flag tool, in the environment.
- **Traffic:** the request rate in the access log; a spike in volume can explain a spike in errors.
- **Dependencies:** timeouts and connection errors towards a database, a queue or another service, and that service's own logs.
- **Infrastructure:** restarts, out-of-memory kills, autoscaling, node or zone events, certificate expiry, disk full.

A correlation is strong when the start matches within a minute or two, the errors are limited to the changed piece (only the new version, only the zone that failed over), and the errors stop when it is reverted.

### 6. Follow requests

Pick one or two failing requests by their trace or request ID, collect their lines from every source and sort them by time. The path of one request often shows the cause better than thousands of aggregated lines: where it entered, where it slowed down, where the first error appeared.

### 7. Separate cause from symptoms

- **Earliest first:** the signature that started first, closest to the start minute, is the best cause candidate.
- **Upstream before downstream:** a slow database produces timeouts in every service that calls it; those timeouts are symptoms.
- **Amplifiers:** retries multiply errors and load; a retry storm can outlast its cause.
- **Cascades:** one failing dependency, then pools exhausted, then health checks failing, then restarts. Read the chain in time order.
- **Missing lines** matter too: a log that stopped, or a heartbeat that disappeared.

### 8. Conclude

State the finding, its evidence and your confidence (high, medium, low), and the check that would confirm it: a query, a metric, a test, a revert in a non-production environment. Hand off to the skill that acts on it: skill:incident-response to mitigate, skill:debug-systematically to fix, skill:root-cause-5whys to learn.

## Return

```markdown
Source: checkout-api JSON logs, 3 pods, 2026-03-02 13:30 to 15:00 UTC (export timestamps already in UTC), 412,000 lines.
Baseline: 2026-02-23 same hours: 0 to 3 errors per minute.
Start: 14:05 UTC: 60 to 90 errors per minute until 14:32, then back to baseline.

| Signature | Count | First seen | Where | New? |
|---|---|---|---|---|
| ColumnNotFound: column <name> does not exist | 1,790 | 14:05:02 | version 2.41.0 only | yes |
| Timeout calling payments after <n> ms | 50 | 14:07:40 | all pods | no (40 in baseline) |

Correlation: deploy of v2.41.0 finished 14:03 (deploy history); errors only on pods running 2.41.0; errors stop at 14:32, when the rollback completed.
Cause candidate (high confidence): v2.41.0 reads a column that does not exist. Payment timeouts are background noise at baseline rate.
Next: confirm in the schema migration history; root cause with root-cause-5whys.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "log-analysis", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"log-analysis"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Never save log excerpts to memory; save the finding with skill:memory-protocol (`--type discovery` or `--type bugfix`).

## Before you finish

- [ ] Format, time zone, span and volume are stated; every time is in UTC.
- [ ] The start minute and the rates come with a baseline.
- [ ] Error groups are normalized signatures, and new ones are marked.
- [ ] Every correlation has timestamps, and the conclusion has a confidence and a next check.
- [ ] No secret, personal data or customer identifier reached the conversation; the working slice is outside the repository.
