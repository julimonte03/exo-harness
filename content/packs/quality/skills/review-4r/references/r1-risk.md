# R1 Risk

**The question:** what can this change break, expose or make irreversible?

Only risk. Readability, correctness and failure handling belong to the other lenses; a deep security review belongs to skill:judge-security and to `security-code-review` (pack `security`). Point at what needs one of them.

## Security

The OWASP Top 10:2021 items that apply to what changed, the edition the `security` pack uses. Cite the item with its edition (`OWASP A03:2021`), never the bare number, and the CWE when it helps.

| Look for | Item |
|---|---|
| A new entry point without authentication, or without a check of what the caller may touch | A01:2021, A07:2021 |
| Untrusted input reaching a query, a shell command, a template, HTML or a file path without parameters or encoding | A03:2021, A01:2021 (CWE-22) |
| Secrets in code, configuration, tests or fixtures; keys or passwords compared with `==` | CWE-798, CWE-208 |
| Weak or home-made cryptography for sensitive data; plain HTTP for credentials or personal data | A02:2021 |
| Deserialization of untrusted data into objects | A08:2021 |
| A URL from a user fetched by the server without an allow list | A10:2021 |
| Debug modes, verbose errors or permissive settings in what ships | A05:2021 |

## Data

- Secrets or personal data in logs, console output, error messages, responses or analytics (`.exo/shared/data-protection.md`). Always High or above.
- Data leaving the system: a new destination, a third party, an export. Who receives what, and whether the project allows it.
- Data kept longer, or in more places, than before.

## Blast radius

- Who depends on what changed: callers, public functions and APIs, shared modules, configuration defaults, file formats other tools read.
- How many users or records a failure touches, and whether it fails loudly or quietly.

## Irreversibility

- Migrations, deletes, overwrites of user files, data format changes, published contracts, messages sent to people, money moved.
- For each: is there a backup, a dry run, a rollback, or a way to tell it went wrong before it is too late?

## Supply chain and money

- A new or upgraded dependency: maintained, pinned, from the expected source, with a license the project accepts. Name it for the dependency audit.
- Calculations with money, rounding, currencies or taxes.

## Severity

- Critical: exploitable by anyone who reaches the entry point; a secret in code; irreversible loss of data.
- High: secrets or personal data in logs or output; a missing authorization check behind sign-in; an irreversible step without a way back.
- Medium: a missing layer of defense; a wide blast radius with no safeguard; an unpinned dependency.
- Low: hardening suggestions.
