# Worked example: a nightly report that silently stopped

A synthetic case, start to finish. Names, services and numbers are invented.

## Problem statement

"The nightly sales report was not delivered to the finance mailbox from 2026-05-04 to 2026-05-07 (four nights). Nobody noticed until a finance analyst asked on the fifth morning."

It is measurable (four nights, a delivery that did not happen), it has no cause in it, and it already hints at two questions: why it failed, and why nobody noticed for four days.

## Facts gathered

- The scheduler shows the job `sales-report` as `Succeeded` on each of the four nights. [scheduler history, job `sales-report`]
- The job log has `0 rows exported` on those nights; earlier nights export about 3,000 rows. [log query `service.name:sales-report and message:"rows exported"`]
- On 2026-05-03 the warehouse view `daily_sales` was replaced to add a currency column; the new view filters on `region_code`, renamed from `region`. [migration `warehouse/migrations/0142_daily_sales.sql:9`]
- The report job queries `daily_sales WHERE region = :region`; the warehouse returns zero rows instead of an error because a compatibility alias `region` exists and is always null. [job `reports/sales.py:57`; migration line 14]
- The job sends the email only when there are rows. [`reports/sales.py:88`]
- No alert watches the report: the only monitor is "job failed", and the job never failed. [alert rules file `monitoring/jobs.yml`]

## Why-chains

```text
Why it happened
Problem: no report for four nights.
Why 1: the job exported 0 rows, and it skips the email when there are no rows. [log; sales.py:88]
Why 2: its query filters on region, which the new view keeps only as an always-null alias. [sales.py:57; migration 0142:14]
Why 3: the view changed without anyone checking the queries that read it. [migration PR has no consumer review]
Why 4: there is no list of the consumers of warehouse views, so the author could not know the job read it. [no catalog or ownership file]
Root cause: warehouse views change without a known list of consumers.

Why it was not caught
Why 1: the job reported success. [scheduler history]
Why 2: success means "the process exited 0", not "the report was delivered". [job definition]
Why 3: the job treats zero rows as a normal outcome. [sales.py:88]
Root cause: the job's success signal does not reflect its purpose, and an empty export is not treated as suspicious.

Why the impact was large (four days)
Why 1: nobody watches report deliveries; finance noticed by chance. [alert rules]
Root cause: no freshness monitor on the report.
```

## Checking backwards

"Views change without a known list of consumers, therefore the job's query was not updated, therefore it read an always-null alias, therefore it exported zero rows, therefore it sent no email." Each "therefore" holds.

"The job's success means exit 0, therefore it reported success with zero rows, therefore no alert fired." Holds.

## Why 5 Whys was enough here

One chain per question, every link with evidence, and no condition that needed another to hold at the same time. Had the failure appeared only on some nights, a fault tree or competing hypotheses would have been the better tool.

## Actions

| ID | Action | Cause | Type | Owner (role) | Due | Check | Ticket |
|---|---|---|---|---|---|---|---|
| A-1 | Record the consumers of each warehouse view in an ownership file reviewed in migration PRs | Views change without known consumers | prevent | data platform lead | 2026-05-29 | A migration PR that touches `daily_sales` lists `sales-report` as a consumer | <ID> |
| A-2 | Fail the job when an export that is never empty returns zero rows | Success signal does not reflect the purpose | detect | reports owner | 2026-05-15 | A run against an empty view exits non-zero in a test | <ID> |
| A-3 | Freshness alert: page when the report has not been delivered by 07:00 | No freshness monitor | detect | on-call lead | 2026-05-15 | The alert fires in staging when the job is paused | <ID> |
| A-4 | Drop the compatibility alias, or make it computed, so old queries fail loudly | Silent always-null alias | prevent | data platform lead | 2026-06-12 | A query on `region` errors in the warehouse test suite | <ID> |

Four actions, each with a check that a reviewer can see, none of them "be more careful".
