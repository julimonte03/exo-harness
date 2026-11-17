# Query languages and fields

Syntax for the languages `kibana-logs` writes. Values in angle brackets are placeholders. Every example assumes the time range is pinned outside the query (the time picker, or a `range` filter in the API) unless it shows one.

## Where each language runs

| Tool | Languages |
|---|---|
| Kibana, Discover and dashboards | KQL (default), Lucene; ES\|QL in recent versions |
| OpenSearch Dashboards, Discover | DQL (the OpenSearch name for its KQL-like language), Lucene |
| OpenSearch Dashboards, Query Workbench and log analytics | PPL, SQL |
| Elasticsearch API | Query DSL (`_search`, `_count`), SQL (`_sql`), ES\|QL (`_query`) |
| OpenSearch API | Query DSL (`_search`, `_count`), PPL (`_plugins/_ppl`), SQL (`_plugins/_sql`) |

## KQL (and DQL)

| Need | Query |
|---|---|
| Exact value | `service.name : "checkout-api"` |
| Several values | `log.level : ("error" or "fatal")` |
| Combine | `service.name : "checkout-api" and log.level : "error"` |
| Exclude | `not url.path : "/health"` |
| Range | `http.response.status_code >= 500` |
| Date range in the query | `@timestamp >= "2026-03-02T13:30:00Z" and @timestamp < "2026-03-02T15:00:00Z"` |
| Field exists | `error.type : *` |
| Prefix | `kubernetes.pod.name : checkout-api-*` |
| Phrase in text | `message : "connection refused"` |
| One request | `trace.id : "<trace-id>"` |

- Quote phrases; without quotes, several words in a text field match any of them.
- Operators `and`, `or`, `not` are case-insensitive; use parentheses to group.
- No regular expressions and no fuzzy matching: switch to Lucene for those.
- A leading wildcard (`*timeout`) scans every term; avoid it on large indices.

## Lucene

| Need | Query |
|---|---|
| Exact value | `service.name:"checkout-api"` |
| Combine | `service.name:"checkout-api" AND log.level:error` |
| Exclude | `NOT url.path:"/health"` or `-url.path:"/health"` |
| Inclusive range | `http.response.status_code:[500 TO 599]` |
| Date range | `@timestamp:[2026-03-02T13:30:00Z TO 2026-03-02T15:00:00Z}` (`]` inclusive, `}` exclusive) |
| Field exists | `_exists_:error.type` |
| Regular expression | `error.message:/time.?out/` |
| Fuzzy | `message:timout~1` |

- `AND`, `OR`, `NOT` must be uppercase.
- Escape special characters with a backslash: `+ - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /`.
- Regular expressions run on terms, not on the whole text; on text fields they match single words.

## PPL (OpenSearch)

A pipeline of commands separated by `|`:

```text
source = logs-*
| where service.name = 'checkout-api' and log.level = 'error'
| where `@timestamp` >= '2026-03-02 13:30:00' and `@timestamp` < '2026-03-02 15:00:00'
| stats count() as errors by span(`@timestamp`, 1m)
```

| Need | Command |
|---|---|
| Filter | `where http.response.status_code >= 500` |
| Keep some fields | `fields @timestamp, service.name, error.type, trace.id` |
| Count per group | `stats count() as n by error.type` |
| Sort descending | `sort - n` |
| First rows | `head 10` |
| Most frequent values | `top 10 error.type` |
| Rare values | `rare error.type` |
| One row per value | `dedup trace.id` |
| Histogram | `` stats count() by span(`@timestamp`, 5m) `` |

- Quote a name with backticks when it has special characters (`@timestamp`, hyphens). If the engine rejects a dotted name, quote it with backticks too.
- String literals use single quotes.

## ES|QL (Elastic, recent versions)

```text
FROM logs-*
| WHERE service.name == "checkout-api" AND log.level == "error"
| WHERE @timestamp >= "2026-03-02T13:30:00Z" AND @timestamp < "2026-03-02T15:00:00Z"
| STATS errors = COUNT(*) BY minute = DATE_TRUNC(1 minute, @timestamp)
| SORT minute
```

Use it only when the person's stack has it; KQL works everywhere Kibana does.

## Query DSL through the API (read-only)

Count errors per minute and the top error types, without returning documents:

```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "term": { "service.name": "checkout-api" } },
        { "term": { "log.level": "error" } },
        { "range": { "@timestamp": { "gte": "2026-03-02T13:30:00Z", "lt": "2026-03-02T15:00:00Z" } } }
      ]
    }
  },
  "aggs": {
    "per_minute": { "date_histogram": { "field": "@timestamp", "fixed_interval": "1m" } },
    "top_errors": { "terms": { "field": "error.type", "size": 10 } },
    "by_version": { "terms": { "field": "service.version", "size": 5 } }
  }
}
```

A few documents of one group, with only the fields that explain it:

```json
{
  "size": 3,
  "_source": ["@timestamp", "service.name", "log.level", "error.type", "error.message", "trace.id", "url.path"],
  "query": { "bool": { "filter": [ { "term": { "error.type": "ColumnNotFound" } } ] } },
  "sort": [ { "@timestamp": "asc" } ]
}
```

When the project has an endpoint configured in the environment, the request goes from a file, with the credentials that the environment or the tool's configuration already holds:

```bash
curl -s "$ES_URL/logs-*/_search" -H "Content-Type: application/json" --data-binary @query.json
```

Only `_search`, `_count`, `_field_caps`, `_sql`, `_query`, `_plugins/_ppl`, `_plugins/_sql` and `_cat/indices`, and through `_sql` and `_plugins/_sql` only `SELECT`, `SHOW` and `DESCRIBE` statements (OpenSearch runs a `DELETE` there when its cluster allows it). Never a request that indexes, updates, deletes or changes settings.

## Common fields

| Meaning | ECS field | Other names seen in the wild |
|---|---|---|
| Time | `@timestamp` | `timestamp`, `time`, `ts` |
| Service | `service.name` | `app`, `application`, `service`, `kubernetes.labels.app` |
| Environment | `service.environment` | `env`, `environment`, `kubernetes.namespace` |
| Version | `service.version` | `version`, `image.tag`, `container.image.tag` |
| Level | `log.level` | `level`, `severity`, `loglevel` |
| Message | `message` | `msg`, `log` |
| Error type | `error.type` | `exception.class`, `error.kind` |
| Error message | `error.message` | `exception.message` |
| Stack trace | `error.stack_trace` | `exception.stacktrace`, `stack` |
| HTTP status | `http.response.status_code` | `status`, `response_code` |
| Path | `url.path` | `path`, `request.path`, `uri` |
| Trace | `trace.id` | `traceId`, `trace_id` |
| Request | `http.request.id` | `request_id`, `requestId`, `x_request_id` |
| Host and pod | `host.name`, `kubernetes.pod.name` | `hostname`, `pod` |

Check the real names in the data view's field list or with `_field_caps` before filtering; a filter on a field that does not exist returns zero hits, not an error.

## Performance

- Filters (`term`, `range`, the KQL field filters) are cached and cheap; free text and wildcards are not.
- Narrow the time range first; a query over months on a busy cluster can slow it for everyone.
- `size: 0` with aggregations counts without moving documents.
- Terms aggregations on high-cardinality fields (request IDs, messages with IDs) are expensive; aggregate on `error.type` or `url.path` instead.
- In Discover, add only the columns you need; wide documents with large `message` fields render slowly.

## Kibana and OpenSearch Dashboards tips

- Set the time picker to absolute dates before sharing anything.
- Pin a filter (the pill) to keep it while you switch views.
- The field statistics or "visualize" action on a field shows its top values in the current window.
- The surrounding documents view shows the lines just before and after one document from the same source: useful to see what led to an error.
- Share with a link that includes the absolute time range, not a relative one.
- A CSV export goes to the person; it is masked before anyone pastes it anywhere.
