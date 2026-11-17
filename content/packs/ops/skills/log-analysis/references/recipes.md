# Recipes

Read-only commands for each step of `log-analysis`. Replace the file names and fields with the ones of the log at hand. Run them on a slice in your work folder, outside the repository.

## 1. Inventory

```bash
wc -l app.log                                   # volume
head -3 app.log; sed -n '50000,50002p' app.log  # format at the start and in the middle
head -1 app.log | cut -c1-25; tail -1 app.log | cut -c1-25   # first and last timestamps (text logs)
jq -r '.["@timestamp"]' app.json | sort | sed -n '1p;$p'      # first and last (JSON)
jq -r 'keys[]' app.json | sort | uniq -c | sort -rn | head -30 # fields present (JSON)
```

PowerShell:

```powershell
(Get-Content app.log | Measure-Object -Line).Lines
Get-Content app.log -TotalCount 3
Get-Content app.json -TotalCount 1 | ConvertFrom-Json | Get-Member -MemberType NoteProperty
```

## 2. Slice the window

```bash
# ISO timestamps at the start of the line
awk '$1 >= "2026-03-02T13:30" && $1 < "2026-03-02T15:00"' app.log > <work>/window.log
awk '$1 >= "2026-02-23T13:30" && $1 < "2026-02-23T15:00"' app.log > <work>/baseline.log

# JSON lines
jq -c 'select(.["@timestamp"] >= "2026-03-02T13:30" and .["@timestamp"] < "2026-03-02T15:00")' app.json > <work>/window.json

# join multi-line stack traces to their first line (lines that do not start with a date)
awk '/^[0-9]{4}-[0-9]{2}-[0-9]{2}/ { if (rec) print rec; rec = $0; next } { rec = rec " | " $0 } END { if (rec) print rec }' app.log > <work>/joined.log
```

## 3. Rates per minute

```bash
# text logs: the minute is the first 16 characters of an ISO timestamp
grep -E ' (ERROR|FATAL) ' <work>/window.log | cut -c1-16 | sort | uniq -c

# JSON lines
jq -r 'select(.["log.level"] == "error") | .["@timestamp"][0:16]' <work>/window.json | sort | uniq -c

# access log: 5xx per minute ([02/Mar/2026:14:05:02 +0000] in field 4)
awk '$9 ~ /^5/ { print substr($4, 2, 17) }' access.log | sort | uniq -c

# by status code, by host, by version
jq -r '.["http.response.status_code"]' <work>/window.json | sort | uniq -c | sort -rn
jq -r 'select(.["log.level"] == "error") | .["service.version"]' <work>/window.json | sort | uniq -c
```

PowerShell:

```powershell
Get-Content window.json | ConvertFrom-Json |
  Where-Object { $_.'log.level' -eq 'error' } |
  Group-Object { $_.'@timestamp'.Substring(0, 16) } |
  Select-Object Name, Count
```

## 4. Signatures

```bash
# normalize the message and count signatures (text logs; message after the level)
grep -E ' ERROR ' <work>/window.log \
  | sed -E 's/.* ERROR //' \
  | sed -E 's/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/<uuid>/g' \
  | sed -E 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<email>/g' \
  | sed -E 's/([0-9]{1,3}\.){3}[0-9]{1,3}/<ip>/g' \
  | sed -E 's/[0-9a-fA-F]{16,}/<hex>/g' \
  | sed -E 's/"[^"]*"/<str>/g' \
  | sed -E 's/[0-9]+/<n>/g' \
  | sort | uniq -c | sort -rn | head -20 > <work>/signatures-window.txt

# same for the baseline, then the signatures that are new
# (strip the counts, compare the sets)
sed -E 's/^ *[0-9]+ //' <work>/signatures-window.txt | sort > <work>/w.txt
sed -E 's/^ *[0-9]+ //' <work>/signatures-baseline.txt | sort > <work>/b.txt
comm -23 <work>/w.txt <work>/b.txt              # only in the window: new signatures

# first and last time a signature appears
grep -n 'ColumnNotFound' <work>/window.log | sed -n '1p;$p' | cut -c1-40
```

With JSON, group on the error type first; it is already normalized:

```bash
jq -r 'select(.["log.level"] == "error") | .["error.type"] // "none"' <work>/window.json | sort | uniq -c | sort -rn
```

## 5. Correlate

```bash
git log --since="2026-03-02T12:00Z" --until="2026-03-02T15:00Z" --format='%cI %h %s'   # repository changes
git tag --sort=creatordate --format='%(creatordate:iso-strict) %(refname:short)' | tail  # releases
jq -r 'select(.["log.level"] == "error") | [.["@timestamp"][0:16], .["service.version"]] | @tsv' <work>/window.json | sort | uniq -c
kubectl get events -n <namespace> --sort-by=.lastTimestamp                              # restarts, OOM kills
```

Deploy history usually lives in the CI or deploy tool; ask the person for the times of the deploys in the window when it is not in the repository.

## 6. Follow a request

```bash
grep -h '<trace-id>' svc-a.log svc-b.log svc-c.log | sort
jq -s -c 'map(select(.["trace.id"] == "<trace-id>")) | sort_by(.["@timestamp"]) | .[] | {t: .["@timestamp"], svc: .["service.name"], lvl: .["log.level"], err: .["error.type"]}' *.json
```

## Masking a sample before showing it

```bash
perl -pe '
  s/\b(Bearer|Basic)\s+[A-Za-z0-9._~+\/=-]+/$1 <redacted>/gi;
  s/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*/<jwt>/g;
  s/("?(?:token|access_token|refresh_token|password|passwd|secret|api_?key|authorization|cookie)"?\s*[:=]\s*)("[^"]*"|[^\s,;&}]+)/$1<redacted>/gi;
  s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/user\@example.com/g;
  s/\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/203.0.113.10/g;
' sample.log
```

It masks `Authorization: Bearer` and `Basic` headers, JWTs, secret keys as `key=value`, `key: value` or JSON (`"password": "..."`), emails and IPv4 addresses. `perl` behaves the same on Linux, macOS and Git for Windows; `sed` does not (the case-insensitive `I` flag is GNU only).

A regular expression never catches everything: read the masked sample before you paste it, and summarize free text written by people instead of quoting it.
