# Reliability checklist

Each rule says what must hold, what to look for in the code, and the usual severity when it does not hold. Cite the rule ID in each finding. The names in "Look for" are common spellings, not requirements: agent frameworks, graph runtimes and hand-written loops name these things differently.

## AR-LOOP: loops and stop conditions

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-LOOP-1 | Every agent loop has a hard step limit enforced in code | `while True` or recursion around the model call; settings such as `max_steps`, `max_iterations`, `max_turns`, `recursion_limit`; a limit only in the prompt does not count | High; Critical when each step can take a side effect or spend without a budget |
| AR-LOOP-2 | The loop ends on a structured signal: a finish tool, a schema, a stop reason | String matching on the model's text ("DONE", "Final answer:") | Medium |
| AR-LOOP-3 | Repetition is detected: the same tool with the same arguments several times stops the loop or changes the strategy | A history of calls compared before executing | Medium |
| AR-LOOP-4 | Handoffs between agents and the depth of sub-agents are bounded | Agents that can call each other; spawning without a depth or count limit | High |
| AR-LOOP-5 | Reflection, critique and repair loops have a round limit and a measurable exit | "Improve until good" loops; a judge call with no threshold | Medium |
| AR-LOOP-6 | Hitting a limit gives a defined outcome: a partial answer, an escalation or a clear error, plus a trace event | An exception that escapes to the user, or a silent cut | Medium |

## AR-TOOL: tool errors

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-TOOL-1 | Tool exceptions are caught at the tool boundary and returned to the model as a short, actionable error (what failed, whether retrying can help) | Bare `except: pass`; errors converted to an empty result; exceptions that end the run | High when the agent then answers as if it had succeeded |
| AR-TOOL-2 | Arguments from the model are validated against the tool's schema before running, with a bounded number of corrections | Arguments passed straight into a query, a path or a command | High; Critical when they reach a shell, a query or a file path unchecked |
| AR-TOOL-3 | Unknown tool names and malformed calls are rejected with an error the model can act on | A dispatcher that throws on an unknown name | Medium |
| AR-TOOL-4 | Tool output is limited in size and shape before it enters the context | Whole documents, full query results or raw HTML returned | Medium |
| AR-TOOL-5 | Structured model output is parsed with a bounded repair path and a fallback | Parsing without a retry limit, or with no handling of invalid output | Medium |
| AR-TOOL-6 | Each tool has the least privilege it needs, and each stage gets only the tools it needs | One service account with write access behind read tools; every tool offered at every step | High |

## AR-TIME: timeouts and retries

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-TIME-1 | Every model call and every tool call has a timeout | Client constructors and HTTP calls without a timeout; library defaults of minutes or none | High |
| AR-TIME-2 | The whole run has a deadline, and cancellation stops pending calls | A run that can outlive the request that started it; no cancellation path | Medium |
| AR-TIME-3 | Retries apply only to retryable errors (timeouts, rate limits, server errors), with exponential backoff, jitter, a cap, and the server's retry-after when given | Retry on every exception; fixed sleeps; unbounded retries | Medium; High when the retried call has a side effect (see AR-IDEM) |
| AR-TIME-4 | Retries are not multiplied across layers (client library, application, queue redelivery) without a total cap | Several retry layers for the same call | Medium |

## AR-IDEM: idempotency

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-IDEM-1 | Side-effecting tools take or derive an idempotency key (for example the run ID plus the step) so a retry or a repeated decision does not repeat the effect | Create, send, pay or delete calls without a key or a uniqueness check | High; Critical for money or external messages |
| AR-IDEM-2 | A resumed or replayed run skips the side effects already done | Checkpoints that record decisions but not completed effects | High |
| AR-IDEM-3 | Multi-step effects are transactional or have compensation | Partial failure leaves half-done work with no cleanup | Medium |

## AR-COST: cost limits

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-COST-1 | A budget per run (tokens or money) is enforced, with quotas per user or tenant | Token counting with no stop; no quota | High when combined with an unbounded loop; Medium otherwise |
| AR-COST-2 | Context growth is bounded: history trimmed or compacted, tool output truncated | The whole conversation and every tool result appended forever | Medium (see skill:context-engineering-review) |
| AR-COST-3 | Fan-out is bounded: parallel sub-agents, parallel tool calls, batch sizes | Parallel calls over an unbounded list | High |
| AR-COST-4 | Spend is monitored with alerts | No metric of cost per run or per day | Medium |
| AR-COST-5 | The model of each step fits its job: smaller models for routing and classification | The largest model for every step | Low |

## AR-OBS: observability

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-OBS-1 | A trace per run with a span per model call (model, tokens, latency, stop reason) and per tool call (name, status, latency), and a correlation ID across services | One log line per run; no tokens; no tool status | Medium |
| AR-OBS-2 | Traces and logs keep no secrets and no unmasked personal data, and have a retention period | Full prompts and tool results logged as they are | High (`.exo/shared/data-protection.md`) |
| AR-OBS-3 | Metrics and alerts on tool error rate, limit hits, fallbacks, cost and latency | No alerts | Medium |
| AR-OBS-4 | The prompt version and model version of each run are recorded | Prompts edited in place with no version | Medium |

## AR-EVAL: evaluation

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-EVAL-1 | A versioned eval set of representative tasks with expected outcomes or graded criteria | An `evals/` folder, test fixtures of conversations; none at all | Medium; High for a system that takes actions |
| AR-EVAL-2 | Evals run on every prompt, tool, model or retrieval change, with a pass threshold that blocks or alerts | A CI job or a documented command; evals run by hand once | Medium |
| AR-EVAL-3 | The set includes failures: tool errors, empty retrieval, ambiguous requests, injected instructions in content | Only happy paths | Medium |
| AR-EVAL-4 | Deterministic checks where possible; model-graded checks calibrated against human labels | A model judging itself with no calibration | Low to Medium |
| AR-EVAL-5 | Production failures flow back: sampled traces are reviewed and new failures become eval cases | No review loop | Low |

## AR-HITL: humans in the loop

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-HITL-1 | Irreversible, external, financial and privileged actions wait for an explicit human approval, with a summary of what will happen, enforced in code before execution | Tools that act as soon as the model calls them; an approval asked only in the prompt | Critical |
| AR-HITL-2 | The approval comes from the authenticated person through the application, never from content the model read or from the model itself | An "approved" flag the model can set; approval parsed from a message or a document | Critical |
| AR-HITL-3 | Bulk actions have a preview and a blast-radius limit (records per run) | Loops over all records with no cap | High |
| AR-HITL-4 | An escalation path hands the case to a person, with context, when the agent is unsure or hits a limit | No way out but an answer | Medium |
| AR-HITL-5 | Every action taken is in an audit log: who asked, what the agent did, who approved | Side effects with no record | Medium |

## AR-DEGR: degradation

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-DEGR-1 | A model or provider failure leads to a tested fallback (another model with compatible tool support and context size, a cached answer, a simpler flow) or an honest error | One provider with no fallback on a user-facing path; a fallback model that lacks the tools | High on user-facing paths; Medium elsewhere |
| AR-DEGR-2 | A failed dependency (index, database, tool) makes the agent say what it could not do, not guess | Empty results passed to the model as if they were an answer | High |
| AR-DEGR-3 | Circuit breakers or rate limits protect failing tools and the provider quota | Retry storms against a failing tool | Medium |
| AR-DEGR-4 | The final output is checked before it reaches a person or a system: schema, citations for grounded answers, query validation | Model output used as is | Medium; High when it drives an action |

## AR-STATE: state across steps and agents

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| AR-STATE-1 | Run and conversation state is persisted where it must survive, with a schema, and isolated between concurrent runs of the same user or session | In-memory state in a multi-instance service; shared mutable globals | High |
| AR-STATE-2 | Agents hand off an explicit, minimal contract (inputs, outputs, ownership of each artifact), not the whole transcript | Every agent reading and writing everything | Medium |
| AR-STATE-3 | Long-term memory writes are filtered: no secrets or personal data, and no instructions taken from untrusted content | Tool output saved to memory as is | High |

## Security checks to keep when the security pack is missing

- Untrusted content (user input, retrieved documents, web pages, tool output) never triggers an irreversible action without AR-HITL-1 and AR-HITL-2.
- Credentials live in the tool's runtime, never in the prompt, the context or a trace.
- Tool arguments that reach a shell, a query or a path are validated (AR-TOOL-2).
