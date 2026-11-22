# Security review checklist

The criteria of `security-code-review`, also reused by `judge-security` (pack `quality`). Each check has a stable ID: cite it in the Rule/OWASP column of a gate, or in the `rule` of a judge finding, together with its CWE and the OWASP Top 10:2025 category of that CWE, written with its year (`SCR-AUTHZ-2, A01:2025, CWE-639`). The categories come from `.exo/shared/owasp-2025.md`, which lists every CWE of this checklist. The category is the one of the section, unless the row names another one for its CWE: then cite that one (`SCR-AUTHN-6, A02:2025, CWE-614`). A section with two categories names the one of each row.

## How the IDs work

- `SCR-<category>-<n>`. An ID never changes meaning and is never reused.
- A new check takes the next free number of its category. A check that stops applying stays in its table, marked `retired`.
- A finding cites the most specific check. When two apply, cite both (`SCR-INJ-1, SCR-ERR-1`).
- "Signals" are where to look; they are not findings by themselves. "Not a finding" lists the usual false positives.
- The secure coding rules (`SCB-n` of `secure-coding-baseline`) are the same controls seen from the writer's side; a review finding may cite both.

## SCR-INJ Injection (A05:2025 Injection)

| ID | Check | CWE |
|---|---|---|
| SCR-INJ-1 | A SQL statement is built with concatenation, interpolation or string formatting of a value that input can reach. | CWE-89 |
| SCR-INJ-2 | A NoSQL query takes an input object or a raw JSON string as a filter, so input can inject operators. | CWE-943 |
| SCR-INJ-3 | A process is started through a shell, or with a command string, that includes input. | CWE-78 |
| SCR-INJ-4 | An LDAP filter or an XPath expression includes input without the library's escaping. | CWE-90, CWE-643 |
| SCR-INJ-5 | Input is evaluated as code or rendered as a template: `eval`, dynamic imports, expression languages, server-side templates built from user text. | CWE-94, CWE-917, CWE-1336 |
| SCR-INJ-6 | An identifier that cannot be bound (sort column, table, field name) comes from input without a fixed allow-list. | CWE-89 |

- **Signals:** raw query helpers, string building next to `execute`/`query`, process APIs with a shell flag, template engines fed with request text.
- **Not a finding:** the ORM's query builder or bound parameters with the value; a value that is a constant or comes from an allow-list in code.

## SCR-AUTHN Broken authentication (A07:2025 Authentication Failures)

| ID | Check | CWE |
|---|---|---|
| SCR-AUTHN-1 | A new or changed entry point (route, handler, consumer, job, webhook, CLI command) that reads or changes data has no authentication, and the plan does not say it is public. | CWE-306 |
| SCR-AUTHN-2 | A token is accepted without full verification: signature with an expected algorithm, expiry, issuer, audience. | CWE-287; CWE-347 is A04:2025 Cryptographic Failures |
| SCR-AUTHN-3 | Sessions: the session ID is not renewed after login or a privilege change, never expires, or logout does not invalidate it on the server. | CWE-384, CWE-1463, CWE-1464 |
| SCR-AUTHN-4 | Login, password reset, one-time codes or similar endpoints have no attempt limit. | CWE-307 |
| SCR-AUTHN-5 | Tokens, reset codes, API keys or signatures are compared with a regular equality instead of a constant-time comparison. Passwords are never compared at all: they are checked with the library's verify function against a salted slow hash (SCR-CRYPTO-2). | CWE-208 |
| SCR-AUTHN-6 | Session or authentication cookies lack `Secure`, `HttpOnly` or `SameSite`. | CWE-614, CWE-1004, both A02:2025 Security Misconfiguration; CWE-1275 (`SameSite`) is A01:2025 Broken Access Control |
| SCR-AUTHN-7 | A webhook or a service-to-service call is accepted without verifying its signature or the caller's identity. | CWE-290; CWE-345 is A08:2025 Software or Data Integrity Failures |

- **Signals:** new routes or handlers, decorators or middleware lists, token parsing code, cookie settings.
- **Not a finding:** a route covered by the project's global authentication filter (check that the diff does not exempt it).

## SCR-AUTHZ Broken authorization (A01:2025 Broken Access Control)

| ID | Check | CWE |
|---|---|---|
| SCR-AUTHZ-1 | An entry point that changes or returns protected data performs no authorization check. | CWE-862 |
| SCR-AUTHZ-2 | Object-level access: an object is loaded by an ID from input and the caller's right to that object (owner, tenant, share) is not checked. | CWE-639 |
| SCR-AUTHZ-3 | Function-level access: an admin or internal action checks the role only on the client, or not at all. | CWE-285; CWE-602 is A06:2025 Insecure Design |
| SCR-AUTHZ-4 | The check is wrong: it tests the role but not the tenant, compares the wrong field, or can be skipped by a parameter. | CWE-863 |
| SCR-AUTHZ-5 | Mass assignment: request fields are bound to a model, so a caller can set fields such as role, owner or price. | CWE-915, A08:2025 Software or Data Integrity Failures |
| SCR-AUTHZ-6 | A state-changing request authenticated by cookies has no protection against cross-site request forgery. | CWE-352 |
| SCR-AUTHZ-7 | An open redirect: a redirect target comes from input without an allow-list. | CWE-601 |
| SCR-AUTHZ-8 | A permissive cross-origin policy: any origin, or a reflected origin, together with credentials. | CWE-942, A02:2025 Security Misconfiguration |

- **Signals:** lookups by ID from the path or body, `find`/`get` without a filter on the caller, new admin routes, request-to-model binding.
- **Not a finding:** a query that already filters by the caller's ID or tenant taken from the session.

## SCR-SECRET Exposed secrets (A07:2025 Authentication Failures, A01:2025 Broken Access Control)

| ID | Check | CWE |
|---|---|---|
| SCR-SECRET-1 | A credential, key, token or connection string with a password is written in code, tests, fixtures, scripts or committed configuration. | CWE-798, A07:2025; CWE-321 is A04:2025 Cryptographic Failures |
| SCR-SECRET-2 | A secret file (`.env`, a private key, a certificate store) is added to the repository. | CWE-540, A01:2025 |
| SCR-SECRET-3 | A secret travels in a URL or a query string. | CWE-598, A06:2025 Insecure Design |
| SCR-SECRET-4 | A secret reaches a response, an error message or a client-side bundle. | CWE-200, A01:2025 |
| SCR-SECRET-5 | A secret has a hard-coded fallback value when the environment variable is missing. | CWE-798, A07:2025; CWE-1188 |

- **Signals:** assignments to names such as `password`, `secret`, `token`, `key`; long random-looking strings; new config files.
- **Not a finding:** a placeholder (`${DB_PASSWORD}`, `<your-token>`), a variable name, a published test value. Never copy the value into the finding.

## SCR-DESER Unsafe deserialization (A08:2025 Software or Data Integrity Failures)

| ID | Check | CWE |
|---|---|---|
| SCR-DESER-1 | Untrusted data goes into a native object deserializer or a loader that can build arbitrary types. | CWE-502 |
| SCR-DESER-2 | A JSON or YAML library has polymorphic type handling or a full loader turned on for untrusted input. | CWE-502 |
| SCR-DESER-3 | An XML parser processes external entities or DTDs on untrusted input. | CWE-611, CWE-776, both A02:2025 Security Misconfiguration |
| SCR-DESER-4 | Data round-tripped through the client (cookies, hidden fields, tokens of state) is trusted without a signature check. | CWE-565, CWE-345 |

- **Not a finding:** data-only parsing into explicit types; deserialization of data the service wrote and signed itself.

## SCR-SSRF Server-side request forgery (A01:2025 Broken Access Control)

The 2025 edition folds server-side request forgery into Broken Access Control.

| ID | Check | CWE |
|---|---|---|
| SCR-SSRF-1 | The server makes a request to a URL or host that input controls, without an allow-list of hosts and schemes. | CWE-918 |
| SCR-SSRF-2 | The allow-list is checked on the text of the URL but not on the resolved address, or redirects are followed to hosts outside it. | CWE-918 |
| SCR-SSRF-3 | A component that fetches resources on its own (an HTML-to-PDF renderer, an image proxy, a webhook tester, an XML parser) gets input that can point it at internal addresses. | CWE-918; CWE-611 is A02:2025 Security Misconfiguration |

- **Signals:** HTTP clients called with a variable URL, "fetch from URL" or "import from link" features, callbacks configured by users.
- **Not a finding:** a fixed base URL in configuration with only a validated path segment from input.

## SCR-PATH Path traversal and file handling (A01:2025 Broken Access Control)

| ID | Check | CWE |
|---|---|---|
| SCR-PATH-1 | A file path is built from input without canonicalizing it and checking that it stays inside the intended folder. | CWE-22 |
| SCR-PATH-2 | An archive is extracted without checking that every entry stays inside the target folder. | CWE-22 |
| SCR-PATH-3 | An upload has no size limit, no content check, a user-chosen name, or is stored where it can be served or run. | CWE-434, A06:2025 Insecure Design |
| SCR-PATH-4 | Symbolic links are followed out of the intended folder. | CWE-59 |

- **Not a finding:** a file chosen from a server-side map by an ID; a generated name inside a fixed folder.

## SCR-XSS Cross-site scripting (A05:2025 Injection)

| ID | Check | CWE |
|---|---|---|
| SCR-XSS-1 | Input is written into HTML without encoding for its context, or through a raw-HTML API (`innerHTML`, raw template filters, framework escape hatches). | CWE-79 |
| SCR-XSS-2 | Input lands in a URL attribute without a scheme check (`javascript:` links), or inside a script block or an event handler. | CWE-79 |
| SCR-XSS-3 | Stored content from users is rendered as HTML without a vetted sanitizer. | CWE-79 |

- **Not a finding:** templates with auto-escaping on and no raw output in the diff.

## SCR-DEP Risky dependencies (A03:2025 Software Supply Chain Failures)

| ID | Check | CWE |
|---|---|---|
| SCR-DEP-1 | A dependency is added that the plan does not name, or that looks unmaintained (no recent release, archived repository). | CWE-1104 |
| SCR-DEP-2 | An added or upgraded version has a known high or critical vulnerability that the code can reach. | CWE-1395 |
| SCR-DEP-3 | A manifest changes without its lockfile, or a version is unpinned (ranges, latest tags, CI actions by branch name). | CWE-1357 |
| SCR-DEP-4 | Code is downloaded and run without a pinned version or an integrity check (install hooks, remote scripts, build plugins). | CWE-494, A08:2025 Software or Data Integrity Failures |
| SCR-DEP-5 | The package name is a look-alike of a well-known package, or comes from a registry other than the project's. | CWE-1357 |

- **Category:** a dependency finding is `A03:2025` whatever the weakness inside the library; name that weakness in the finding text. Only a missing integrity check (SCR-DEP-4) is `A08:2025` (`.exo/shared/owasp-2025.md`, dependency findings).
- **Signals:** manifest and lockfile hunks, CI files, Dockerfiles. For known vulnerabilities, use the result of the stack's dependency scan (`security-scan-node` or `security-scan-jkp`, which verify loads when a lockfile changes) instead of guessing from version numbers; without one, say that SCR-DEP-2 was not checked.

## SCR-LOG Sensitive data in logs (A09:2025 Security Logging and Alerting Failures)

| ID | Check | CWE |
|---|---|---|
| SCR-LOG-1 | A log line, metric label, trace attribute or error report includes a password, token, key, session ID or connection string. | CWE-532 |
| SCR-LOG-2 | It includes personal data: names, emails, phone numbers, national IDs, card or account numbers, addresses, free text written by people. | CWE-532, CWE-359 |
| SCR-LOG-3 | A whole request, response or user object is logged as is. | CWE-532 |
| SCR-LOG-4 | Logged input keeps its line breaks or control characters, so it can forge entries. | CWE-117 |
| SCR-LOG-5 | A new security-relevant action (login, denied access, permission change, payment) leaves no log entry. | CWE-778 |

- **Not a finding:** an internal, non-personal ID or a masked value (`****1234`); structured logging that escapes fields.

## SCR-CRYPTO Weak cryptography (A04:2025 Cryptographic Failures)

| ID | Check | CWE |
|---|---|---|
| SCR-CRYPTO-1 | A broken or weak algorithm or mode is used for security: MD5, SHA-1, DES, RC4, ECB. | CWE-327, CWE-328 |
| SCR-CRYPTO-2 | Passwords are stored encrypted, in plain text, or hashed with a fast hash. | CWE-916; CWE-256 is A06:2025 Insecure Design |
| SCR-CRYPTO-3 | Tokens, reset codes, nonces or keys come from a non-cryptographic random generator. | CWE-330, CWE-338 |
| SCR-CRYPTO-4 | Home-made cryptography: custom algorithms, padding or key derivation, or a reused nonce. | CWE-327, CWE-323 |
| SCR-CRYPTO-5 | TLS certificate or host name validation is turned off, or sensitive data travels without TLS. | CWE-319; CWE-295 is A07:2025 Authentication Failures |

## SCR-ERR Exceptional conditions (A10:2025 Mishandling of Exceptional Conditions)

| ID | Check | CWE |
|---|---|---|
| SCR-ERR-1 | A response to the caller includes a stack trace, a query, a file path, a version or an internal host name. | CWE-209 |
| SCR-ERR-2 | A security check fails open: an exception, a timeout or a missing setting results in access. | CWE-636 |
| SCR-ERR-3 | Authentication errors tell which part failed, so accounts can be enumerated. | CWE-204, A07:2025 Authentication Failures |
| SCR-ERR-4 | Debug mode or detailed error pages are on in the configuration that ships. | CWE-489, A02:2025 Security Misconfiguration |
| SCR-ERR-5 | Debug output (a debug endpoint, a verbose log level, a dump on error) carries secrets, personal data or internals in what ships. | CWE-215 |
| SCR-ERR-6 | An exception on a security or data path is swallowed or turned into a default: an empty `catch`, or a catch-all that returns success, an empty result or a default value, so the caller carries on as if nothing failed. | CWE-755, CWE-390 |
| SCR-ERR-7 | The result of a call that matters is not checked: a verification, a permission lookup, a write or a send whose failure or error code is ignored. | CWE-252 |
| SCR-ERR-8 | A security check is written as an assertion, which an optimized build or a runtime flag removes, or which crashes instead of denying. | CWE-617 |
| SCR-ERR-9 | A multi-step operation that fails midway is not rolled back, and leaves half-granted access, a partial write or money moved without its record. | CWE-755 |

- **Signals:** `catch` and `except` blocks, error handlers and middleware, default branches, the return values of verification, permission and write calls, `assert`, debug flags and error page settings.
- **Not a finding:** an error caught where it happens, logged, and turned into a generic answer that denies or stops (that is the fix); an assertion in a test; detailed errors in a configuration that cannot ship.
