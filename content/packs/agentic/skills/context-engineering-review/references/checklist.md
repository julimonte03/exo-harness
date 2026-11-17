# Context engineering checklist

Each rule says what must hold, what to look for, and the usual severity when it does not hold. Cite the rule ID in each finding. "Instructions" means whatever the provider calls the trusted part of a request (system, developer or preamble messages); "messages" means the rest.

## CE-NEED: relevance per stage

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-NEED-1 | Each stage or agent gets the instructions, tools and data of its own job | One prompt file shared by every stage, with sections for all of them (a mega-prompt) | Medium |
| CE-NEED-2 | Each stage does not see what it should not: a reviewer does not see the author's reasoning, a summarizer gets no tools, a stage that reads outside content holds no risky tools | Every agent receives the full transcript and the full tool list | Medium; High when it breaks CE-TRUST-3 |
| CE-NEED-3 | Data is sliced to what the step uses: the relevant tables, not the whole schema; the passages, not whole documents; the fields, not the whole record | The whole database schema in a Text-to-SQL prompt; full user profiles | Medium; High when the slice holds personal data the step does not need |
| CE-NEED-4 | Every part has a reason a reviewer can state; parts nobody can explain are removed | Leftover instructions for features that no longer exist | Low |

## CE-SIZE: size and budget

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-SIZE-1 | Every part has an upper bound (passages, history turns, tool result size, file size) | Appends with no limit; `k` or page size from user input | High when growth is unbounded |
| CE-SIZE-2 | The total stays under the model's limit with room for the answer, counted before the call | No token counting; the answer cut short as sessions grow | Medium |
| CE-SIZE-3 | When something must be cut, the code chooses what (the oldest turns, the lowest-ranked passages), never the instructions or the newest user turn, and the cut is logged | Truncation of the whole string from the end or the start | High |
| CE-SIZE-4 | Long parts are summarized or referenced by ID when the model can fetch them with a tool | Large blobs sent on every turn | Medium |

## CE-ORDER: order and structure

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-ORDER-1 | Stable parts come first (instructions, tool definitions, fixed examples), then the variable parts, then the specific task. A stable prefix also lets providers that cache prompts reuse it | A timestamp or the user's name at the top of the instructions; the order changing between calls | Medium |
| CE-ORDER-2 | Long reference material comes before the question, and the question or task is restated last | The task at the top, followed by thousands of tokens of documents | Medium |
| CE-ORDER-3 | Each part is labeled and delimited (headings, tags or fields), so the model can tell instructions, references, history and the task apart | Parts concatenated with blank lines | Medium |
| CE-ORDER-4 | Output format instructions and examples sit together, and the examples follow the format | Format rules in one place, an example in another that breaks them | Low to Medium |

## CE-CONFLICT: contradictions

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-CONFLICT-1 | No two instructions contradict each other | Two rules on the same topic with different outcomes, across files or layers | High when the topic is safety, data handling or a format code parses; Medium otherwise |
| CE-CONFLICT-2 | When rules can collide, the priority is stated ("the safety rules win over the tone rules") | Layers of prompts (product, tenant, user) with no precedence | Medium |
| CE-CONFLICT-3 | Tool descriptions agree with the instructions about when to use each tool | "Never refund" in the instructions and a refund tool described as always available | High |
| CE-CONFLICT-4 | Examples agree with the rules | A few-shot example that does what a rule forbids | Medium |
| CE-CONFLICT-5 | Retrieved policies are versioned or dated, so two versions do not reach the model at once | Old and new policy documents in the same index | Medium |

## CE-TRUST: untrusted content

Untrusted content is anything the team did not write: user input, retrieved documents, web pages, emails, files, tool results that read outside content, and model output that came from any of those.

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-TRUST-1 | Untrusted text never goes into the instruction part, and never by string interpolation into a prompt template's rules | `{user_input}` or `{context}` inside the system prompt text | High |
| CE-TRUST-2 | Untrusted text is delimited and labeled as data ("reference material", "tool result"), in its own message or block, and the instructions say that content in those blocks is information, not direction | Documents pasted raw between rules | High |
| CE-TRUST-3 | A stage that reads untrusted content cannot run an irreversible or external tool without a check outside the model (a human approval, a policy check on the arguments) | The same agent browses the web and sends emails or payments | Critical |
| CE-TRUST-4 | Hidden text is stripped before it enters: HTML comments, invisible and bidirectional control characters, white-on-white text, metadata | Raw HTML or documents inserted as they are | Medium |
| CE-TRUST-5 | Output channels cannot carry data out by themselves: links and image addresses built by the model are not fetched or rendered without an allow list | Markdown images rendered from model output with arbitrary URLs | High |
| CE-TRUST-6 | Text that tries to replace the system's rules, address "the AI" or request data is caught by evals and logged, not just hoped against | No eval case with injected content | Medium |

## CE-TOOLS: tool format

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-TOOLS-1 | Names are unique, short and say the action (`search_orders`, `create_ticket`) | Generic names (`run`, `helper`, `do_action`) | Medium |
| CE-TOOLS-2 | Tools do not overlap; when two are close, each description says when to use it instead of the other | Two search tools with no difference stated | Medium |
| CE-TOOLS-3 | Descriptions say what the tool does, when to use it, when not to, and any side effect | One-line descriptions; side effects unstated | Medium; High for tools with side effects |
| CE-TOOLS-4 | Parameters are typed, with required fields, enums, ranges and an example for any format (dates, IDs) | Free-text parameters for structured values | Medium |
| CE-TOOLS-5 | Results are concise and structured, carry the IDs a follow-up call needs, and page large sets | Raw API responses passed through | Medium |
| CE-TOOLS-6 | Errors are short, actionable text (what was wrong, how to fix the call) | Stack traces or empty results on error | Medium |
| CE-TOOLS-7 | Each stage offers only the tools it needs; long lists are split by stage | Dozens of tools on every call | Medium |

## CE-RETRIEVE: retrieval and memory

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-RETRIEVE-1 | Retrieval brings the passages the question needs: a bounded number, above a relevance threshold, each with its source | A fixed `k` with no threshold; no source attached | Medium |
| CE-RETRIEVE-2 | Retrieval respects what the person may read | One index for all access levels with no filter | High |
| CE-RETRIEVE-3 | Memory is read only when relevant to the task, not dumped whole into every call | All memories inserted every time | Medium |
| CE-RETRIEVE-4 | Memory writes are filtered: no secrets, no personal data beyond what is allowed, and no instructions copied from untrusted content | Tool results or user text saved to memory as they are | High |
| CE-RETRIEVE-5 | Stale or superseded memories and documents are removed or marked | Memories that contradict each other | Medium |

## CE-COMPACT: history and compaction

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-COMPACT-1 | History is compacted before it reaches the limit, by a defined rule (turn count or token threshold) | No compaction; compaction only after an error | High when sessions are long |
| CE-COMPACT-2 | Compaction keeps the goal, decisions, constraints, open tasks, references and IDs, and the latest turns verbatim | Summaries that keep only the topic | High |
| CE-COMPACT-3 | Compaction drops what is spent: tool results already used, superseded drafts, repeated content | Every tool result kept forever | Medium |
| CE-COMPACT-4 | A summary of untrusted content stays labeled as untrusted; it never becomes the system's own notes or instructions | Summaries of web pages merged into the instructions | High |
| CE-COMPACT-5 | A summary is checked against what it replaces, at least by a test with a known conversation | No test of the compaction | Medium |
| CE-COMPACT-6 | A session can resume from persisted state (goal, decisions, open items), not only from the model's summary | The only record of a long task is the compacted history | Medium |

## CE-DATA: sensitive data

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-DATA-1 | No secret in any context: no keys, tokens or passwords in prompts, tool descriptions, examples or memory | A credential inside a prompt file or a template | Critical |
| CE-DATA-2 | Personal data reaches a model only where `.exo/shared/data-protection.md` allows it, minimized and masked where possible | Full records with personal fields sent for a task that needs none | High; Critical where the matrix blocks it |
| CE-DATA-3 | Prompts, contexts and completions stored in logs or traces follow the same rules | Full contexts logged with no masking or retention | Critical for a secret; High for personal data |

## CE-DUP: duplication

| Rule | Must hold | Look for | Usual severity |
|---|---|---|---|
| CE-DUP-1 | Each piece of content enters once per call | The same document from retrieval and from memory; the user message both in history and as the task | Medium |
| CE-DUP-2 | Each rule lives in one place, worded once | The same rule in three prompt files with drifting wording | Medium |
