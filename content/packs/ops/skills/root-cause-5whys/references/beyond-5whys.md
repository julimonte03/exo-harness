# Beyond 5 Whys

5 Whys works when one chain of causes explains the failure. When it does not, use one of these, and say in the analysis which one you used and why.

## Fault tree

For failures that need several conditions at once, or that have several independent paths.

- The top event is the problem statement.
- Below it, the conditions that lead to it, joined by gates:
  - **AND:** all children must hold for the parent to happen. Breaking any one child prevents the parent: a cheap child to break is a good action.
  - **OR:** any child is enough. Each child needs its own action, or the parent needs a guard.
- Expand each condition until you reach something you can change or measure.

```text
TOP: duplicate charges for some customers (OR)
├── A: client retries a payment after a timeout (AND)
│   ├── A1: gateway latency above the 5 s client timeout   [metric <name>]
│   ├── A2: client retries without an idempotency key       [client code <file>:88]
│   └── A3: server does not deduplicate by order ID         [handler <file>:41]
└── B: a manual replay of the payments queue                [runbook step 4]
    └── B1: the replay tool does not skip processed messages [tool <file>:20]
```

Here A is an AND: fixing A2 or A3 alone stops branch A, and A3 also covers B if the deduplication is server-side. That makes A3 the strongest action.

## Contributing factors

For failures with no single chain: many small conditions made the incident possible, longer or worse. List them by category and mark the ones you will act on.

| Category | Questions |
|---|---|
| Design and code | Unsafe defaults? Missing validation, timeout, fallback, idempotency? |
| Change process | Review that could not see the risk? A big release? No canary? A migration without a dry run? |
| Testing | A path with no test? Staging data that does not cover it? Flaky tests ignored? |
| Detection | Alert missing, late, noisy or on the wrong signal? Dashboards that hid it? |
| Response | Runbook missing or stale? Access that took too long? Unclear ownership? |
| Environment | Capacity, quotas, certificates, dependencies, a change by a third party? |
| Organization | Too much work in progress? Knowledge held by one person? Handoff gaps? |

Each factor gets evidence, like a link of a why-chain. Not every factor needs an action; the ones that recur in several incidents do.

## Competing hypotheses

For intermittent failures with thin evidence. Instead of a chain that pretends to be certain:

| Hypothesis | Explains | Does not explain | Data that would decide |
|---|---|---|---|
| Connection pool exhaustion under bursts | Errors cluster at the top of the hour | Errors on a quiet Sunday | Pool metrics at 1-minute resolution for a week |
| DNS resolution failures | Errors on several services at once | Why only one region | Resolver logs; error type in client logs |

The actions are then the instrumentation that decides between them, plus a cheap mitigation for the most likely one.

## Blameless language

| Instead of | Write |
|---|---|
| The engineer forgot to update the consumers | The rename shipped without the consumers; nothing in the process pointed at them |
| Ops ran the wrong command | The runbook step allowed running the command against production without a confirmation |
| QA missed it | No test covered orders with coupons, and the staging data had none |
| The on-call was slow | The page reached the on-call 12 minutes after the start; the alert waits 10 minutes |
| Careless, sloppy, should have known | (remove; describe the condition that made the mistake easy) |

- Write about actions and conditions, not about people's qualities.
- Hindsight is not evidence: what is obvious now was not obvious with the information available then. Describe what the person could see at the time.
- When someone volunteers "it was my fault", thank them and record the condition instead.

## Anti-patterns

- **Stopping at the trigger:** "the deploy had a bug" ends nothing; ask why the bug reached users.
- **Stopping at a person:** "human error" is where the analysis starts, not where it ends.
- **A cause that is a solution in disguise:** "the root cause is that we lack Kubernetes" names a tool, not a condition.
- **Too many actions:** fifteen actions with no owner close nothing. Three to six strong ones.
- **Actions without a check:** if you cannot tell when it is done, it will never be done.
- **The analysis written by one person alone:** review it with the people who responded; they know the conditions.
