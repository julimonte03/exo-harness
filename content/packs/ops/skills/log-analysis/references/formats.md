# Log formats, timestamps and normalization

## Recognize the format

| Format | Looks like | Parse with |
|---|---|---|
| JSON lines | `{"@timestamp":"2026-03-02T14:05:02.120Z","log.level":"error","message":"..."}` | `jq`, `ConvertFrom-Json` |
| logfmt | `ts=2026-03-02T14:05:02Z level=error msg="order not found" order=<id>` | `grep -o 'level=[a-z]*'`, `awk` on `key=value` pairs |
| Web access log (combined) | `203.0.113.10 - - [02/Mar/2026:14:05:02 +0000] "GET /checkout HTTP/1.1" 500 512 "-" "agent"` | `awk '{print $9}'` for the status, `$7` for the path |
| Syslog (RFC 3164) | `Mar  2 14:05:02 host app[123]: message` | the year and time zone are missing: ask, or take them from the export |
| Syslog (RFC 5424) | `<165>1 2026-03-02T14:05:02.120Z host app 123 ID47 - message` | split on spaces; the timestamp is ISO 8601 |
| Framework text | `2026-03-02 14:05:02,120 ERROR [main] c.e.OrderService - order not found` | `awk` on the leading fields; level is the third token here |
| Multi-line stack traces | a first line with a timestamp, then lines starting with spaces, `at `, `Caused by:` or `Traceback` | join continuation lines to the previous record before counting |

Read the first lines and a few lines from the middle before deciding: some files mix formats (a JSON logger plus raw output from a library).

## Timestamps

- **ISO 8601 with `Z` or an offset** (`2026-03-02T14:05:02Z`, `+01:00`): unambiguous. Convert offsets to UTC.
- **No zone** (`2026-03-02 14:05:02`): the zone of the host or the logger's configuration. Ask, or find it in the logging configuration, and say what you assumed.
- **Epoch seconds or milliseconds** (10 or 13 digits): convert, for example `jq '.ts / 1000 | todate'` for milliseconds.
- **Day before month or month before day:** check with a day above 12 before trusting the order.
- **Daylight saving changes:** a local-time log repeats or skips an hour; prefer UTC fields when the source has both.

Text sorting of ISO 8601 timestamps in UTC is the same as time order, which makes `sort` and string comparisons in `awk` safe.

## Normalization

To group messages that differ only in their values, replace the values with placeholders. Apply the rules in this order (the first ones are the most specific):

| Value | Pattern (extended regular expression) | Placeholder |
|---|---|---|
| UUID | `[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}` | `<uuid>` |
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | `<email>` |
| IPv4 | `([0-9]{1,3}\.){3}[0-9]{1,3}` | `<ip>` |
| Long hex (hashes, trace IDs) | `\b[0-9a-fA-F]{16,}\b` | `<hex>` |
| Quoted value | `"[^"]*"` or `'[^']*'` | `<str>` |
| Number | `\b[0-9]+(\.[0-9]+)?\b` | `<n>` |

- Normalize the message only, not the timestamp or the level.
- Keep the error type and the first frame of the stack trace in the signature: two different exceptions with the same message are different problems.
- Normalization is also masking: it removes emails, IPs and identifiers from what you show. It does not remove names or free text written by customers; summarize those.
- If a signature still has thousands of variants, look at what varies and add a rule.

## Baselines

- **Same hours, another day:** best for traffic with a daily cycle.
- **Same hours, a week before:** best when weekdays differ.
- **The hour before the start:** when there is no history, with care if traffic ramps up.
- Compare rates (per minute, or errors per request), not totals, when the windows have different lengths or traffic.
- An error present at the same rate in the baseline is background; still report it if it is high, as a separate finding.

## Request and trace IDs

- W3C trace context propagates a 32-hex trace ID (`traceparent` header); many loggers write it as `trace.id`, `traceId` or `trace_id`.
- Request IDs (`X-Request-ID` and similar) are set by a proxy or the first service; check that downstream services log the same one.
- When no ID is shared, correlate by time, host and path, and say the result is approximate.
