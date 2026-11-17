# The context map

One table per stage or agent, with the parts in the order the model receives them. It is the backbone of the review: most findings are visible as soon as the map is complete.

## Columns

| Column | What goes there |
|---|---|
| `#` | Position in the request, from the first part to the last |
| Part | Instructions, fixed examples, tool definitions, memory, retrieved passages, history, tool results, the user input, the task restated |
| Source | `path:line` of the code or file that produces it; for a template placeholder, the template line and the code that fills it |
| Trust | `trusted` (written by the team), `untrusted` (anything else), `mixed` (history, memory) |
| Size | An estimate in tokens, with its bound: `~1.5k`, `up to ~8k (k=10, 800 each)`, `unbounded` |
| Needed for | The reason the stage needs it; "unclear" is a finding |
| Changes per call | `no` for stable parts, `yes` for parts that vary; stable parts belong first |

## Estimating size

- About four characters per token for English prose; code, JSON, tables and many other languages use more tokens per character.
- For a bound, multiply: passages times passage size, turns times average turn, results times the truncation limit.
- If the project already has a tokenizer installed that runs offline, you may use it; never call a service to count.
- Compare the total with the model's context limit when the configuration states it, leaving room for the answer and the tool calls of the remaining steps.

## Tracing untrusted content

For each untrusted part, follow it through the system:

1. Which stages receive it, directly or through a summary, memory or another agent's output.
2. Which tools those stages hold, and which of them are irreversible or external.
3. What stands between the content and those tools: a delimiter alone is not a control; a human approval or a policy check on the tool's arguments is.

Write the path as one line per untrusted part: "web page text → research agent (tools: fetch, notes) → summary → writer agent (tools: send_email): no check before send_email".

## Example

Support assistant, answer stage. Names and paths are invented.

| # | Part | Source | Trust | Size | Needed for | Changes per call |
|---|---|---|---|---|---|---|
| 1 | Instructions | services/assistant/prompts/system.md:1-38 | trusted | ~1.5k | rules, tone, format | no |
| 2 | Tool definitions (9) | services/assistant/tools/registry.py:12-140 | trusted | ~2.5k | actions | no |
| 3 | Memory: customer preferences | services/assistant/memory.py:44 | mixed | up to ~300 | personalization | yes |
| 4 | History, every turn and tool result | services/assistant/history.py:30 | mixed | unbounded | continuity | yes |
| 5 | Knowledge base passages (k=10), placed inside the instructions | services/assistant/prompts/system.md:40, services/assistant/rag.py:22 | untrusted | up to ~8k | grounding | yes |
| 6 | User message | services/assistant/api.py:18 | untrusted | up to ~4k | the task | yes |

**Total:** about 4k stable plus up to ~12.3k variable, plus an unbounded history; the configured limit is not in the repository.

**Untrusted paths:**

- passages → answer stage (tools: create_ticket, issue_refund): no check before issue_refund.
- user message → history → every later call: delimited as user turns, but tool results in history are not labeled.

**What the map already shows:** part 5 is untrusted text inside the instructions (CE-TRUST-1); part 4 has no bound (CE-SIZE-1); the stage that reads passages holds a financial tool (CE-TRUST-3, and AR-HITL-1 in the reliability review).

## The target map

For the stage with the worst findings, propose the corrected table: the same columns, with the parts reordered, bounded and labeled, and the tools trimmed to the stage's job. It turns the findings into one picture the team can implement.
