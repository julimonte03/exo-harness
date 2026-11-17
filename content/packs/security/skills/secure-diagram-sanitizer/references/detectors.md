# Detectors: how to find each category

Search the original with `rg` or `grep` (case-insensitive), then read every hit in context. The patterns below find candidates; reading decides. They also miss things: after the searches, read the whole text once more, looking for names.

## Learn the organization's names first

Before searching, collect what identifies this organization, so you can search for it:

- The domains of the Git remote (`git remote -v`), of internal links in the README, and of email-like strings in configuration.
- The organization and repository names in the remote URL and in package names (`@<scope>/`, group IDs such as `com.<org>`).
- Environment codes in deployment files and CI (`prd`, `prod`, `uat`, `qa`, `stg`, `dev` as prefixes or suffixes).
- Cloud account aliases, cluster names and region names in infrastructure as code.
- Codenames and team names in the documents.

Each of these becomes a search term. Never copy them into anything that leaves the conversation.

## Secrets (Critical)

| Signal | Pattern hint |
|---|---|
| Assignments | `(password\|passwd\|pwd\|secret\|token\|api[_-]?key\|client[_-]?secret)\s*[:=]` |
| Authorization headers | `authorization:`, `bearer `, `basic ` followed by a long value |
| Credentials inside a URL | a user and a password before the `@` of a URL: `://[^/\s:@]+:[^/\s@]+@` |
| Connection strings | `password=` or `pwd=` inside a `;`-separated string; driver URLs with a user and password |
| Provider key formats | the prefixes of cloud access keys, code host tokens and chat tokens that the engine's scanner knows (`.exo/shared/data-protection.md`, section D) |
| Tokens | three base64url segments joined by dots (a signed token); long random strings next to the words key, token or secret |
| Private keys | a PEM header that says PRIVATE KEY |
| Signed links | query parameters such as `sig=`, `signature=`, `X-Amz-Signature=`, `token=` |

Remove the whole value, and the line or attribute that holds it. A placeholder (`<your-token>`, `${API_KEY}`) is not a secret; leave it.

## Personal data (Restricted)

| Signal | Pattern hint |
|---|---|
| Emails | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`; keep `example.com`, `example.org`, `example.net` |
| Phone numbers | `\+\d[\d\s-]{7,}` and local formats |
| Card numbers | 13 to 19 digits, possibly grouped, that pass the Luhn check |
| IBANs | two letters, two digits, then up to 30 letters and digits |
| National IDs | the formats the project enables in `data_protection.pii` of `.exo/config.json` |
| Names of people | no pattern: owners in footers, assignees, "contact" boxes, authors in metadata, sample data in tables. Read for them |

Replace a person with their role. Never keep a real person's name in a shared piece, not even an employee's: use the team or the role.

## Internal URLs and hostnames (Internal)

| Signal | Pattern hint |
|---|---|
| URLs | `https?://[^\s"'<>)]+`; then keep only public sites the piece needs to cite (standards, public docs) |
| Internal suffixes | `\.(internal\|corp\|local\|lan\|intra\|intranet\|private)\b` |
| The organization's domains | each domain collected above, with any subdomain |
| Single-label hosts | short names in connection settings or labels: `db01`, `app-prd-03`, `jumpbox` |
| Names with environment codes | `[-_.](prd\|prod\|uat\|qa\|stg\|stage\|dev)\d*\b` |

## IP addresses and networks (Internal)

| Signal | Pattern hint |
|---|---|
| IPv4 | `\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b` |
| Private and special ranges | `10.`, `172.16.` to `172.31.`, `192.168.`, `100.64.` to `100.127.`, `169.254.` |
| IPv6 | groups of hex digits separated by colons; unique local addresses start with `fd` |

The documentation ranges are `/24` blocks (and `2001:db8::/32` for IPv6): map single addresses into them, consistently. For a larger subnet, use a label with its size when the size matters: `<subnet-a> (/16)`. Loopback (`127.0.0.1`, `::1`) reveals nothing and may stay.

## Ports (Internal)

| Signal | Pattern hint |
|---|---|
| After a host | `:\d{2,5}\b` |
| In settings and rules | `port[s]?\s*[:=]\s*\d+`, port ranges in firewall or security group rules |

Keep the protocol, drop the number: `HTTPS` instead of `:443`, `PostgreSQL` instead of `:5432`. Management and debug ports (SSH, database admin consoles, metrics endpoints) go entirely in a public piece.

## Cloud accounts and resources (Internal)

| Signal | Pattern hint |
|---|---|
| Account numbers | 12-digit numbers near the words account or ARN |
| Subscription and tenant IDs | GUIDs: `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` |
| Project IDs and resource IDs | `arn:` strings, `/subscriptions/…/resourceGroups/…` paths, `projects/<id>/` paths |
| Storage and registries | bucket and container names, registry hosts and image paths, key vault and secret store names |

## Repositories and code hosts (Internal)

| Signal | Pattern hint |
|---|---|
| Git URLs | `git@<host>:`, `https://<host>/<org>/<repo>` |
| Package scopes and feeds | `@<scope>/`, internal registry URLs, group IDs |
| Paths | `path:line` evidence comments, absolute paths with user or organization names |

## Environments, infrastructure and organization identifiers (Internal)

- Cluster, namespace, node pool, server and data center names; region and zone combinations that reveal where the organization runs.
- Ticket IDs (`[A-Z][A-Z0-9]+-\d+` and the project's `tickets.pattern`), codenames, internal team names, customer and tenant names.
- Exact versions on internet-facing elements (`nginx/1.`, `Apache/2.`, framework versions in labels).

Replace each with its generic role, numbered by first appearance: `production`, `cluster-1`, `region-1`, `TICKET-1`, `Project A`, `Customer A`.

## When a search finds too much

A broad pattern (any hostname, any 12-digit number) can hit the content of the piece itself. Read the context: a version number is not an IP address, a year range is not a port. When unsure whether a value identifies the organization, replace it; a generic label never leaks.
