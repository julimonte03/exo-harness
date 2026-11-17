# Without a log stack: local and exported logs

The same search as in Kibana or OpenSearch, on files and on the logs that the runtime keeps. Every command here only reads. Run them on copies or exports when the person prefers, and mask what you paste.

## Pin the window

Logs in files rarely have an index on time; filter by the timestamp prefix, which sorts as text when it is ISO 8601:

```bash
# lines between 13:30 and 14:59 UTC on 2026-03-02, ISO timestamps at the start of the line
awk '$1 >= "2026-03-02T13:30" && $1 < "2026-03-02T15:00"' app.log
```

When the timestamps are in local time or another format, convert them to UTC first (skill:log-analysis covers the common formats) and say which time zone the file uses.

## Plain text logs

```bash
grep -c ' ERROR ' app.log                                # count
grep -n -E ' (ERROR|FATAL) ' app.log | head -50          # first matches, with line numbers
grep -E ' ERROR ' app.log | grep -v '/health'            # exclude noise
grep -B 5 -A 20 '<request-id>' app.log                   # context around one request
zgrep -h ' ERROR ' app.log.*.gz | wc -l                  # rotated and compressed files
grep -h -o 'error=[A-Za-z]*' app.log | sort | uniq -c | sort -rn | head   # top error types
```

## JSON lines

ECS loggers often write dotted keys (`"log.level": "error"`); others nest them (`{"log": {"level": "error"}}`). Check one line first: `head -1 app.json | jq .`

```bash
# dotted keys
jq -c 'select(.["log.level"] == "error")' app.json | head
jq -r 'select(.["log.level"] == "error") | .["error.type"]' app.json | sort | uniq -c | sort -rn

# nested keys
jq -c 'select(.log.level == "error") | {t: .["@timestamp"], svc: .service.name, err: .error.type, trace: .trace.id}' app.json

# one request across files, in time order
jq -s -c 'map(select(.["trace.id"] == "<trace-id>")) | sort_by(.["@timestamp"]) | .[]' svc-a.json svc-b.json

# errors per minute
jq -r 'select(.["log.level"] == "error") | .["@timestamp"][0:16]' app.json | sort | uniq -c
```

Project only the fields you need (`{t: ..., err: ...}`), so personal data in other fields never reaches the screen.

## Containers and services

```bash
kubectl logs deployment/<name> -n <namespace> --since-time=2026-03-02T13:30:00Z --timestamps
kubectl logs <pod> -n <namespace> --previous            # the container that crashed before the restart
kubectl get events -n <namespace> --sort-by=.lastTimestamp   # restarts, OOM kills, scheduling
docker logs --since 2026-03-02T13:30:00 --until 2026-03-02T15:00:00 --timestamps <container>
journalctl -u <unit> --since "2026-03-02 13:30" --until "2026-03-02 15:00" -o short-iso
journalctl -u <unit> --since "2026-03-02 13:30" -o json | jq -r '.MESSAGE'
```

These read the runtime's logs; they need the access the person already has. Never run `kubectl delete`, `kubectl rollout`, `docker rm` or anything else that changes the system from this skill.

## PowerShell (Windows)

```powershell
Select-String -Path app.log -Pattern ' ERROR ' | Select-Object -First 50
(Select-String -Path app.log -Pattern ' ERROR ').Count
Get-Content app.json | ConvertFrom-Json | Where-Object { $_.'log.level' -eq 'error' } | Select-Object '@timestamp', 'error.type'
Get-Content app.json | ConvertFrom-Json | Group-Object 'error.type' | Sort-Object Count -Descending | Select-Object Count, Name -First 10
Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Level = 2; StartTime = '2026-03-02 13:30' } -MaxEvents 50
```

## Exports from a log platform

A CSV or JSON export from Kibana, OpenSearch Dashboards, CloudWatch, Loki, Datadog or Splunk is a file like any other: read its header or first record, then apply the recipes above. Hand the analysis itself (grouping, baselines, correlation) to skill:log-analysis.

## Big files

- Count before printing; `head` every listing.
- Filter by time first, then by level, then by text.
- Prefer `grep -F` for fixed strings; it is much faster than a regular expression.
- Never load a multi-gigabyte file into the conversation or into memory; extract the slice you need into your work folder, outside the repository, and delete it when done.
