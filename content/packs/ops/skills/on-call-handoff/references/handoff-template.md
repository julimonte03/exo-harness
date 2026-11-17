# Handoff template and example

## Guidance per section

| Section | Write | Avoid |
|---|---|---|
| Status | One color and one sentence that names the single most important thing | A paragraph; "all good" when something is open |
| Open incidents | The state now, the mitigation in place, the next step and who does it | The full story; link the incident record instead |
| Resolved this shift | One line each, and whether a postmortem is owed | Details already in the record |
| Temporary changes to undo | Exactly what was changed, how to undo it, and when it must be undone | "Some flags were changed" |
| Alerts | Counts, flapping alerts with a proposed fix, silences with their expiry | Pasting alert payloads |
| Changes | Versions and times; what is planned for the next shift | Commit lists; link the release |
| Watch-list | The risk, the signal, and the threshold that means "act now" | Vague worries without a signal |
| Pending tasks | One owner each, a due time, the ticket | Tasks owned by "the team" |
| Escalation | Roles and rotations | Personal phone numbers or emails |
| Questions | Decisions the incoming person must make or context they lack | Rhetorical questions |
| Unverified | What you could not confirm, and who can | Hiding uncertainty in other sections |

## Example (synthetic)

```markdown
# On-call handoff: payments platform

- **Shift:** 2026-03-02T08:00Z to 2026-03-02T20:00Z
- **From:** payments on-call (day) **To:** payments on-call (night)
- **Status:** yellow. The coupon flag is still off after the SEV2; turn it back on only after the fix ships.

## Open incidents
| ID | Severity | State | Current mitigation | Next step | Owner |
|---|---|---|---|---|---|
| INC-2041 | SEV3 | monitoring | Refund worker scaled from 2 to 4 replicas | Watch queue depth; scale back to 2 when it stays under 100 for an hour | incoming on-call |

## Resolved this shift
| ID | Severity | Summary | Postmortem |
|---|---|---|---|
| INC-2039 | SEV2 | Checkout 500s after v2.41.0; rolled back to v2.40.3 at 14:19 | owed by payments tech lead, due 2026-03-06 |

## Temporary changes to undo
| What | Why | Undo by | How to undo | Owner |
|---|---|---|---|---|
| Feature flag `coupons-v2` off | Mitigation of INC-2039 | When the fix for INC-2039 is deployed | Turn the flag on in the flag tool; watch checkout 5xx for 15 minutes | payments tech lead |
| Refund worker at 4 replicas | INC-2041 | 2026-03-03T08:00Z at the latest | Scale back to 2 with the deploy pipeline's scale job | incoming on-call |
| Alert "refund queue depth" silenced | Known during INC-2041 | Expires 2026-03-02T23:00Z by itself | Nothing; confirm it re-arms | incoming on-call |

## Alerts
- Noisy or flapping: "payments p99 latency" fired 6 times, each under 3 minutes; proposed fix: require 10 minutes above the threshold (ticket PAY-881).
- Silenced: "refund queue depth" until 23:00Z (see above).
- Missing: nothing alerted on the coupon errors before checkout 5xx crossed 2%; follow-up in the INC-2039 postmortem.

## Changes
- Deployed this shift: checkout-api v2.41.0 at 14:03 (rolled back at 14:19); payments-worker v1.18.2 at 10:30.
- Planned next shift: none. Freeze: none.

## Watch-list
- Disk of the payments database replica at 78%, growing about 1% a day; act at 85% (runbook: payments-db-disk).
- Nightly settlement batch at 02:00Z; it failed once last week. Signal: the "settlement finished" log line by 03:00Z.

## Pending tasks
| Task | Owner | Due | Ticket |
|---|---|---|---|
| Fix the flapping latency alert | payments on-call (day) | 2026-03-04 | PAY-881 |
| Update the rollback runbook: the pipeline job was renamed | incoming on-call | 2026-03-03 | PAY-882 |

## Escalation
- Payments service: payments tech lead rotation
- Database: database team on-call rotation
- Customer communication: support duty manager

## Questions for the incoming person
- If the fix for INC-2039 lands tonight, do you want to re-enable `coupons-v2` during the night or wait for the day shift?

## Unverified
- Whether the 10:30 deploy of payments-worker included the retry change; the release notes are not published yet (payments tech lead can confirm).
```

The ticket IDs in the example (`INC-2041`, `PAY-881`) are synthetic; in a real handoff, use the IDs the team gives you, following `tickets.pattern` when the project has one.
