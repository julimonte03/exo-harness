# Checks by system shape

Add the checks of every shape the system has; most systems mix several. Cite the closest rule of `checklist.md` in each finding, or the shape and the check number (`RAG-3`).

## Tool-using assistant

1. Every tool is classified (read, reversible write, irreversible or external), and the classification is in the code, next to the tool, not only in a document.
2. The irreversible tools follow AR-HITL-1, AR-HITL-2 and AR-IDEM-1.
3. Tool descriptions say when not to use the tool; overlapping tools are merged or told apart (see the context engineering review).
4. A conversation that crosses a session boundary resumes from persisted state, not from the model's memory of it.

## RAG (retrieval-augmented generation)

1. **Empty or weak retrieval** has its own path: below a relevance threshold, the system says it does not know or asks, instead of answering from the model alone. (RAG-1)
2. **Grounding:** answers cite the retrieved passages, and a check (deterministic or graded) catches claims with no support before they reach the person. (RAG-2)
3. **Permissions:** retrieval filters by what the person may read, at query time; an index that mixes access levels without a filter is at least High. (RAG-3)
4. **Freshness:** the index has a known update schedule, and stale or deleted documents leave it. (RAG-4)
5. **Bounds:** the number of passages and their total size are limited (AR-TOOL-4). (RAG-5)
6. **Index down:** the system degrades as AR-DEGR-2 says. (RAG-6)
7. **Evaluation** measures retrieval (did the right passages come back?) apart from generation (was the answer right given them?). (RAG-7)
8. **Retrieved text is data:** a passage that contains instructions does not change what the system does (see the context engineering review). (RAG-8)

## Multi-agent

1. **Roles:** each agent has one job, its own tools and its own slice of context; one agent owns each side effect. (MA-1)
2. **Termination:** handoffs and sub-agent depth are bounded (AR-LOOP-4); two agents cannot pass a task back and forth forever. (MA-2)
3. **Contracts:** handoffs carry a defined input and output, validated, not the whole transcript (AR-STATE-2). (MA-3)
4. **Shared state:** concurrent agents do not overwrite each other's results; conflicts have a rule. (MA-4)
5. **Cost:** the multiplier of agents times steps times tokens is inside the run budget (AR-COST-1, AR-COST-3). (MA-5)
6. **Tracing:** one trace links the spans of every agent of a run (AR-OBS-1). (MA-6)
7. **Failure of one agent:** the orchestrator decides (retry, skip, escalate) and the final answer says what is missing. (MA-7)

## Text-to-SQL and data agents

1. **Credentials:** a read-only database user, limited to the schemas and tables the use case needs; never the application's write user. Write capability is at least High. (SQL-1)
2. **Validation:** generated SQL is parsed before it runs: a single statement, read only (no data or schema changes), only allowed tables and columns. (SQL-2)
3. **Limits:** a statement timeout, a row limit, and a cost or plan check for expensive queries. (SQL-3)
4. **Personal data:** sensitive columns are excluded or masked in the allowed views, and results that reach the model follow `.exo/shared/data-protection.md`. (SQL-4)
5. **Result size:** large results are summarized or paged before they enter the context (AR-TOOL-4). (SQL-5)
6. **Transparency:** the person can see the query that produced the answer. (SQL-6)
7. **Evaluation:** a gold set of questions with the expected results, compared by result, not by SQL text. (SQL-7)

## Reflection loops

Three kinds, each bounded with AR-LOOP-5:

1. **Process reflection:** is the plan working? The agent re-plans after failures, with a limit on re-plans and a stop when progress stalls. (RFL-1)
2. **Data reflection:** is the retrieved or queried data enough and consistent? The agent checks coverage and contradictions before answering, and says when the data does not support an answer. (RFL-2)
3. **Draft reflection:** is the answer right and complete? A critique against explicit criteria, a revision, and an exit when the criteria pass or the rounds run out. (RFL-3)

For each, check that the criterion is measurable (a rubric, a schema, a test), that the round limit is in code, and that the trace shows each round.

## Workflow with model steps

A mostly deterministic pipeline with some model calls (classify, extract, summarize):

1. Each model step has an input and output contract, validated (AR-TOOL-5). (WF-1)
2. Each step retries on its own, with AR-TIME-3, and failed items go to a dead-letter queue or a review list, not lost. (WF-2)
3. Batch runs are idempotent per item (AR-IDEM-1, AR-IDEM-2). (WF-3)
4. Low-confidence outputs go to a person instead of the next step. (WF-4)
