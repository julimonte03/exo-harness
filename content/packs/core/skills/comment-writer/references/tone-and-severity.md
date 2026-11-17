# Tone and severity

The tone pass and the severity scale of `comment-writer`. The goal is text the reader can act on without feeling judged: warm, direct and specific.

## Substitutions

| Instead of | Write | Why |
|---|---|---|
| "You forgot to..." | "This path does not ..." | About the code, not the person |
| "Why didn't you...?" | "Could we ...? Because ..." | A suggestion with its reason, not an accusation |
| "Obviously", "clearly", "just", "simply" | (delete) | Makes the reader feel slow when it is not obvious to them |
| "This is wrong." | "This returns X when Y, but the spec expects Z." | Says what is wrong and how you know |
| "Bad naming." | "`tmp` could say what it holds, for example `pending_refunds`." | Specific and actionable |
| "Please fix ASAP!!!" | "This blocks the release on Friday: could it land by Thursday?" | Urgency with its reason and a date |
| "Any thoughts?" | "Should we A or B? I lean to A because ..." | A clear question with a proposal |
| "LGTM" alone, on a risky change | "Approved. I checked the migration on a copy of staging data; the rollback works too." | Says what the approval covers |
| Sarcasm or jokes about the code | (delete) | Reads worse in writing than it sounds |

## Questions versus statements

- **Ask** when you might be missing context: "Is this called before the user is loaded?"
- **State** when you know, with the evidence: "This runs before the user is loaded (`app.py:30` registers it first)."
- Do not disguise a blocking request as a question: "Could you maybe consider...?" on a security hole is unclear. Say it is blocking.

## Severity scale

The default labels, after the Conventional Comments convention. Use the team's own scale when it has one.

| Label | Blocks the merge? | Use it for |
|---|---|---|
| `issue (blocking)` | yes | A bug, a security hole, data loss, a broken contract or API, missing tests for the behavior the change adds |
| `issue (non-blocking)` | no | A real problem that can be fixed in a follow-up the author agrees to |
| `suggestion (non-blocking)` | no | A better way that is not required: readability, a simpler approach, a small performance gain |
| `question` | until answered, when the answer may change the code | Missing context; an assumption to check |
| `nitpick (non-blocking)` | no | Taste: naming, wording, formatting a linter does not enforce |
| `praise` | no | Something done well, named specifically |
| `thought` | no | An idea for later, not for this change |

- **Blocking needs a reason** the author can verify: the scenario that breaks, the rule, the data at risk.
- **Style that a tool could catch** is one suggestion to add the rule, not a comment on every line.
- **When most comments are nitpicks,** say so in the summary: "Nothing blocking; all optional."

## Readers in their second language

- Short sentences, one idea each; the subject first.
- No idioms or wordplay ("nit", "LGTM" and "bikeshedding" are fine only if the team uses them).
- Spell out the reason; do not rely on tone to carry meaning.
- Prefer concrete words: "fails when the list is empty" over "is fragile".

## Urgency in team messages

| Urgency | Signal | Example first line |
|---|---|---|
| Now (production impact) | The incident channel or process the team uses; mention the on-call role | "Checkout errors for all card payments since 10:05; on-call, please look" |
| Today | A deadline in the first line | "Need a decision on the JPY rounding by 16:00 to ship today" |
| This week | A date | "Review wanted by Thursday" |
| Whenever | Say so | "No rush: an idea for the next planning" |

Never manufacture urgency; never hide it either.

## What never goes in a comment or message

- Secrets, tokens, passwords, keys or connection strings, even partly masked: point at the location and tell the owner to rotate them.
- Personal data of customers or colleagues, and customer identifiers: describe them ("the customer of order `<order-id>`") or link the item in the organization's own tracker.
- Raw production logs: a short excerpt, cleaned of the above, or a link to the log query in the organization's own tool.
- Internal hostnames, URLs or IP addresses in a channel outside the organization.
