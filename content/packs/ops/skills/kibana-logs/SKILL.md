---
name: kibana-logs
description: >-
  Searches logs in Elasticsearch, Kibana, OpenSearch or OpenSearch
  Dashboards: writes KQL, Lucene or PPL queries, pins an absolute time range
  in UTC, narrows by service, environment, level and fields, counts and
  aggregates before reading documents, compares with a baseline window, and
  follows one request across services by its trace or request ID. Without a
  log stack it falls back to grep and jq on local or exported logs. Read-only:
  it never writes to the cluster, and never copies secrets or personal data
  from the logs into the conversation. Use it when someone needs to find
  errors in production logs, investigate an incident in the logs, follow a
  request ID, or write a query for Kibana, Elastic or OpenSearch. Triggers:
  "search in Kibana", "check the logs", "errors in prod", "Kibana query",
  "KQL", "OpenSearch query", "PPL query", "find this request ID in the
  logs", "trace this request", "what do the logs say".
metadata:
  exo-pack: ops
  exo-execution: inline
  exo-permissions: read-only
---

# kibana-logs

Finds the log lines that matter in an Elastic or OpenSearch stack, or in plain files when there is no stack. It finds; skill:log-analysis analyzes what was found (patterns, spikes, correlation). The name says Kibana, but Elasticsearch, OpenSearch and OpenSearch Dashboards are covered the same way, and none of them is required.

## Result

- **Queries ready to paste:** KQL or Lucene for Kibana and OpenSearch Dashboards, PPL for OpenSearch, or a read-only API request body, each with its index or data view and an **absolute time range in UTC**.
- **What they returned:** counts, a histogram over time, the top error types or messages, a comparison with a baseline window, and a few representative documents, masked.
- **The next query** to run, or the conclusion and the handoff (to skill:log-analysis, skill:incident-response or skill:debug-systematically).
- Without a log stack: the same search as `grep` or `jq` commands on local or exported logs (`references/local-fallback.md`).

## When

- Errors in production or another shared environment, an incident investigation, a request or trace ID to follow, or a query that someone needs written or fixed.
- **Not for:** analyzing a log file or an export that is already in hand (skill:log-analysis); metrics dashboards or alert design (skill:slo-design).

## Rules

- **Read-only.** Only search and read APIs (`_search`, `_count`, `_field_caps`, `_sql`, `_query`, `_plugins/_ppl`, `_plugins/_sql`, `_cat/indices`). Never index, update, delete, reindex, change mappings, close indices or touch index lifecycle policies, even when asked to "clean up" logs: that is a change for the people who own the cluster.
- **Access comes from the person or the project.** Three ways, in this order:
  1. the person runs the query in Kibana or OpenSearch Dashboards and pastes masked results or aggregations;
  2. a tool the project has already configured: an MCP server for Elastic or OpenSearch, or an endpoint in an environment variable (`$ES_URL`) with credentials the person set in the environment or the tool's configuration;
  3. local or exported files (`references/local-fallback.md`).
  Credentials never go through the conversation: do not read, print or repeat their values, and never put them in a command line you show.
- **External destinations.** An MCP server or endpoint that leaves the organization is an external system: check what each call sends (`.exo/shared/data-protection.md`, section C).
- **Clean what comes back.** Log documents carry tokens, emails, IPs, names and customer IDs. Prefer aggregations over raw documents, select only the fields you need, and mask every sample before it reaches the conversation (skill:prompt-hygiene; when the security pack is not installed: `security/prompt-hygiene not installed — applying inline criteria`, with the inline criteria of `.exo/shared/phase-skill-map.md`). A secret found in a log is pointed at (index, document ID, field), never copied; tell the person to rotate it.
- **Install nothing.** No new tools, plugins or clients; say which command you would run and continue with what exists.
- **Be kind to the cluster.** Narrow time ranges, filters before free text, no leading wildcards on large indices, `size: 0` with aggregations to count.

## Steps

The syntax of KQL, Lucene, PPL and the Query DSL, with the common field names, is in `references/query-languages.md`.

### 1. Frame the search

- What you are looking for: an error, a request, a user-facing symptom, a change in volume.
- Which service and environment.
- **The window:** from about 30 minutes before the reported start to now (or to the end of the incident), in UTC. Write it as absolute timestamps: `2026-03-02T13:30:00Z` to `2026-03-02T15:00:00Z`. A relative range ("last 15 minutes") gives a different answer every time someone opens the query.
- Known identifiers: trace ID, request ID, order ID (an internal identifier, never a customer's personal data), pod or host, version.

### 2. Find the data and its fields

- The index pattern or data view (`logs-*`, `filebeat-*`, `<service>-logs-*`, a data stream such as `logs-<dataset>-<namespace>`).
- The field names: many stacks use ECS (`service.name`, `log.level`, `message`, `error.type`, `error.message`, `http.response.status_code`, `trace.id`, `service.version`, `host.name`, `kubernetes.pod.name`). Others have their own; check with the field list of the data view or `_field_caps` before writing filters.
- Keyword versus text: exact filters work on keyword fields (`service.name`, or `<field>.keyword` in older mappings); free text searches work on `message`.

### 3. Count first

Before reading any document, count by level, service and status in the window:

```text
KQL:  service.name : "checkout-api" and log.level : ("error" or "fatal")
PPL:  source = logs-* | where `service.name` = 'checkout-api' and `log.level` = 'error' | stats count() by span(`@timestamp`, 1m)
```

A histogram per minute shows when the errors started; the start time is often the most useful fact of the whole search.

### 4. Narrow

Add one filter at a time and watch the count: the status code, the endpoint (`url.path`), the error type, the version (`service.version`), the host or pod. If one filter keeps most of the errors, it is a dimension of the problem: "only pods on v2.41.0", "only `/checkout/confirm`".

### 5. Group

Top error types or messages in the window (a terms aggregation, `stats count() by error.type` in PPL, or the field statistics of Discover). When the messages contain IDs, group by `error.type` or by a normalized message (skill:log-analysis, Group).

### 6. Compare with a baseline

The same query on a normal window: the same hours the day before or a week before. Report the ratio: "1,840 errors against 35 in the same hour last week". An error that is just as frequent in the baseline is noise, not the cause.

### 7. Follow one request

With a `trace.id` or request ID, query it across all services and sort by `@timestamp`:

```text
KQL:  trace.id : "<trace-id>"
```

Read the request's story: where it entered, which services it reached, where the first error appeared, and what came back to the user. When there is no shared ID, correlate by time window, host and endpoint, and say the correlation is approximate.

### 8. Sample and mask

Pick two or three representative documents per error group, keep only the fields that explain the error (`@timestamp`, `service.name`, `log.level`, `error.type`, `error.message`, `trace.id`, `url.path`), and mask the rest as skill:prompt-hygiene says before showing them.

### 9. Report

What you searched (index, query, absolute window), what you found (counts, start time, dimensions, top errors, baseline ratio), masked samples, and the next step. Give a share link with the absolute time range when the person works in Kibana or OpenSearch Dashboards, so others see the same result.

## Without a log stack

When there is no Elastic or OpenSearch, or the person has an export, run the same search on files with `grep`, `jq`, `zgrep`, `kubectl logs --since-time`, `docker logs --since`, `journalctl --since`, or `Select-String` in PowerShell. All read-only. Recipes in `references/local-fallback.md`.

## Return

```markdown
Search: index logs-*, 2026-03-02T13:30:00Z to 2026-03-02T15:00:00Z
Query (KQL): service.name : "checkout-api" and log.level : "error"
Found: 1,840 errors; 35 in the same window a week before. Start: 14:05 UTC (first minute above 5 per minute).
Dimensions: 99% on service.version 2.41.0; 97% on url.path /checkout/confirm.
Top errors: ColumnNotFound (1,790), Timeout calling payments (50).
Sample (masked): 14:06:12Z checkout-api error ColumnNotFound "column coupon_code does not exist" trace.id=<trace-id> customer=CUST-1
Next: follow trace <trace-id> across services; compare with the deploy at 14:03 (skill:log-analysis, Correlate).
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes. An MCP server used for the search is recorded too, as type `mcp`:

```bash
exo change record <change> --add capabilities_used '{"name": "kibana-logs", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "<mcp-server-name>", "type": "mcp", "activation": "auto"}'
exo change record <change> --add knowledge_used '{"source": "mcp", "ref": "logs-* 2026-03-02T13:30Z..15:00Z, service.name checkout-api"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Never save log samples to memory; save the finding (the start time, the cause) with skill:memory-protocol.

## Before you finish

- [ ] Every query has its index or data view and an absolute time range in UTC.
- [ ] Counts and a baseline came before samples.
- [ ] Only read APIs were used; nothing was written to the cluster.
- [ ] Every sample is masked; no secret, personal data or customer identifier reached the conversation.
- [ ] Credentials were never read, printed or requested.
