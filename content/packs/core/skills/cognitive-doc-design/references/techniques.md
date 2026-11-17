# Techniques, with before and after

Each technique of `cognitive-doc-design`, with a small synthetic example. Apply the ones the document needs; a short page rarely needs all of them.

## Lead with the answer

Before:

```markdown
# Invoices service

This service was created in 2021 when the billing team decided to split the monolith.
After several iterations, it now handles invoice generation, numbering and PDF rendering.
To run it locally you will need Python and a database...
```

After:

```markdown
# Invoices service

Generates, numbers and renders the invoices of every order. For developers working on billing.

**Quick start:** `make dev`, then open http://localhost:8000/health.

Needs Python 3.12 and Docker. History and design: docs/architecture.md.
```

The reader learns what it is, whether it is for them, and the one command, in four lines.

## General to particular

Before: a page that starts with the retry settings of one queue, then explains what the queues are for.

After, in this order:

1. What the queues are for, in two sentences.
2. The main flow: an order event goes in, an invoice comes out.
3. The settings most people change (concurrency, retries), with their defaults.
4. The rare ones (dead-letter handling, manual replays), lower or on a linked page.

## One idea per paragraph

Before:

> The exporter runs every night and writes a CSV to the shared bucket, and if it fails it retries three times, and the file name has the date, and you can also run it by hand with the CLI, which is useful when the nightly run failed, but remember to pass the date.

After:

> The exporter runs every night and writes a CSV named `invoices-<date>.csv` to the shared bucket.
>
> A failed run retries three times. After that, run it by hand for the missing date:
>
> `invoices export --date 2027-03-01`

## One name per concept

Before: "the worker", "the consumer", "the processor" and "the job runner" in the same page, for one service.

After: "the worker" everywhere, defined once: "**The worker** reads order events from the queue and creates the invoices." If the code calls it something else, say so once: "(`InvoiceConsumer` in the code)".

## Recognition over recall

Before: "Set the timeout to the value described in the previous section."

After: "Set the timeout to 30 seconds, the same as the gateway's."

Before: three paragraphs describing three plans and their limits.

After:

| Plan | Invoices per month | PDF branding | Support |
|---|---|---|---|
| Free | 50 | no | community |
| Team | 2,000 | yes | email |
| Business | unlimited | yes | email and phone |

## Signposts

Before: a long page of setup instructions with no overview.

After: "Setting up takes three steps: install the tools, configure the database, and check that the tests pass. Each step ends with a command that tells you it worked."

## Steps with their results

Before:

> Install the dependencies and run the migrations, then start the server.

After:

```markdown
1. Install the dependencies: `pip install -e ".[dev]"`
   You should see `Successfully installed invoices`.
2. Create the database tables: `invoices migrate`
   You should see `Applied 12 migrations`.
3. Start the server: `invoices serve`
   http://localhost:8000/health answers `ok`.
```

## Examples next to rules

Before: "Invoice numbers must follow the series format."

After: "Invoice numbers are the series, a dash and a six-digit counter: `A-000123`. The counter restarts every year."

## Headings that say something

| Weak | Better |
|---|---|
| Overview | What the invoices service does |
| Configuration | Change the retry settings |
| Miscellaneous | (split: each item goes where a reader would look for it) |
| FAQ | Why is my invoice number skipped? / How do I re-render a PDF? |
| Notes | Known limits |

## Progressive disclosure

- Keep the main path short; move what fewer than about one reader in five needs to a lower section or a linked page.
- In Markdown that supports it, a `<details>` block can fold a long log or an optional step; never fold something every reader needs.
- Link with what the reader gets: "Replaying failed events (only after an outage)", not "see here".

## Cutting

| Cut | Example |
|---|---|
| Hedges | "It is generally recommended that you might want to" → "Run" |
| Filler | "It is important to note that", "Basically", "As you may know" |
| Repetition | The same setup in the README and in docs/setup.md: keep one, link from the other |
| Outdated text | A section on the old deploy script: delete it, or mark it "Outdated since 2027-01" with the replacement |

## Accessible documents

- Every image and diagram has a text description, or the text around it says the same.
- Meaning is never carried by color alone ("the red rows" → "the rows marked Failed").
- Tables have a header row; no layout tables.
- Link texts make sense out of context, for readers who jump from link to link.
