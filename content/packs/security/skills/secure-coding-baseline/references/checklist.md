# Secure coding checklist

The detailed checks behind each rule of `secure-coding-baseline`. Use it while writing code and as the list for the `secure_coding_check` gate. Item IDs are stable (`SCB-3.2`): cite them in findings. Examples are language-neutral sketches; follow the project's own libraries and conventions.

## SCB-1 Validate and encode untrusted input

| ID | Check | CWE |
|---|---|---|
| SCB-1.1 | Every new input (request field, header, cookie, path or query parameter, uploaded file, message, third-party response) is validated on the server before use, even when the client also validates. | CWE-20, CWE-602 |
| SCB-1.2 | Validation is an allow-list: expected type, length, range, character set or format. A deny-list of "bad characters" is not validation. | CWE-20 |
| SCB-1.3 | Invalid input is rejected with a clear, generic error; it is not "fixed up" silently and passed on. | CWE-20 |
| SCB-1.4 | Structured input (JSON, XML, CSV) is parsed with a real parser and checked against a schema or a typed model; unknown fields are rejected or ignored, never bound to internal attributes. | CWE-915 |
| SCB-1.5 | Output is encoded for its context with the framework's encoder: HTML body, HTML attribute, URL component, JavaScript, CSS. Templates keep auto-escaping on; raw-HTML escape hatches get input that is already sanitized with a vetted sanitizer. | CWE-79, CWE-116 |
| SCB-1.6 | URLs that come from input are parsed, and only allowed schemes (`https`, sometimes `mailto`) and, for redirects or outbound calls, allowed hosts pass. | CWE-601, CWE-918 |
| SCB-1.7 | File names and paths from input never reach the file system directly: map them to an ID, or canonicalize the path and check that it stays inside the intended folder. | CWE-22 |
| SCB-1.8 | Uploads have a size limit, a content type checked from the content (not only the extension) and a storage location outside the web root, with a generated name. | CWE-434 |

## SCB-2 Parameterized queries

| ID | Check | CWE |
|---|---|---|
| SCB-2.1 | SQL uses bound parameters or the ORM's query builder. Raw SQL helpers get parameters, never interpolated values. | CWE-89 |
| SCB-2.2 | Identifiers that cannot be bound (a sort column, a table name) come from a fixed allow-list in code, never from input as is. | CWE-89 |
| SCB-2.3 | NoSQL queries never take an input object as a filter; build the filter from validated scalar values so input cannot inject operators. | CWE-943 |
| SCB-2.4 | Processes run with an argument list and no shell. If a shell cannot be avoided, every argument is a fixed value or strictly validated. | CWE-78 |
| SCB-2.5 | LDAP filters, XPath expressions and template strings never interpolate input; use the library's escaping or binding. | CWE-90, CWE-643, CWE-1336 |
| SCB-2.6 | No evaluation of input as code (`eval`, dynamic imports, expression languages, server-side template rendering of user text). | CWE-94, CWE-917 |

```text
Not this:  query("SELECT * FROM orders WHERE id = " + order_id)
This:      query("SELECT * FROM orders WHERE id = ?", [order_id])
```

## SCB-3 Authentication and authorization on every entry point

| ID | Check | CWE |
|---|---|---|
| SCB-3.1 | Every new or changed entry point (route, handler, message consumer, scheduled job, CLI command, webhook) states who may call it, and the code enforces it. Public endpoints are public on purpose, and the plan says so. | CWE-306 |
| SCB-3.2 | Authorization is checked on the server for the specific object: the caller owns it, or their role and tenant allow the action on it. An ID in the URL or body is never proof of access. | CWE-639, CWE-863 |
| SCB-3.3 | Deny by default: a new route inherits the project's authentication middleware; opting out is explicit and reviewed. | CWE-862 |
| SCB-3.4 | Function-level checks: admin and internal actions verify the role on the server, not by hiding a button. | CWE-285 |
| SCB-3.5 | Tenancy: every query on tenant data filters by the caller's tenant, taken from the session, not from input. | CWE-639 |
| SCB-3.6 | Tokens are fully verified: signature with an expected algorithm, expiry, issuer and audience. A token that fails any check is rejected. | CWE-347, CWE-287 |
| SCB-3.7 | Sessions: a new session ID after login and privilege change, expiry and logout that invalidate it on the server, cookies with `Secure`, `HttpOnly` and `SameSite`. | CWE-384, CWE-1463, CWE-1464, CWE-614, CWE-1004 |
| SCB-3.8 | State-changing requests authenticated by cookies are protected against cross-site request forgery (the framework's token or `SameSite` plus an origin check). | CWE-352 |
| SCB-3.9 | Login, password reset and similar endpoints limit attempts. Secrets and tokens are compared in constant time. | CWE-307, CWE-208 |

## SCB-4 Fail closed

| ID | Check | CWE |
|---|---|---|
| SCB-4.1 | A security decision that throws, times out or gets an unexpected value results in "deny". No `catch` that logs and continues past an authorization or validation check. | CWE-636 |
| SCB-4.2 | Missing security configuration (no key, no allow-list, no issuer) stops the start-up or the request; it never falls back to "no check". | CWE-636, CWE-1188 |
| SCB-4.3 | Feature flags and switch statements on roles or states have a default branch that denies. | CWE-636 |
| SCB-4.4 | A partial failure in a multi-step operation leaves the system in a safe state: no half-granted access, no money moved without its record. | CWE-755 |

## SCB-5 Secrets from the environment or a secret manager

| ID | Check | CWE |
|---|---|---|
| SCB-5.1 | No credential, key, token or connection string with a password in code, tests, fixtures, committed config, scripts or docs. Use the variable name (`${DB_PASSWORD}`) or a placeholder (`<your-token>`). | CWE-798, CWE-321 |
| SCB-5.2 | Secrets are read at runtime from the environment or the project's secret manager, and the code fails closed when one is missing (SCB-4.2). | CWE-798 |
| SCB-5.3 | Secrets never travel in URLs or query strings, where proxies and logs keep them. | CWE-598 |
| SCB-5.4 | Secrets never reach the client side (browser bundles, mobile apps) unless they are designed to be public. | CWE-200 |
| SCB-5.5 | New secret files (`.env`, keys, certificates) stay out of the repository; the project documents an example file with placeholders. The `pre-commit` hook blocks the usual names (`.exo/shared/data-protection.md`, section D). | CWE-540 |

If you find a real secret in the code: do not copy it anywhere, point at `path:line`, tell the person to remove it and to rotate it.

## SCB-6 No secrets or personal data in logs

| ID | Check | CWE |
|---|---|---|
| SCB-6.1 | No log line, metric label, trace attribute or error report includes passwords, tokens, keys, session IDs, card or account numbers, national IDs, emails, phone numbers or free text written by people. | CWE-532, CWE-359 |
| SCB-6.2 | Whole objects (requests, users, payloads) are never logged as is; log selected, non-personal fields, or use the project's masking logger. | CWE-532 |
| SCB-6.3 | Logged input has line breaks and control characters neutralized, or goes into a structured field, so it cannot forge log entries. | CWE-117 |
| SCB-6.4 | Security events are logged with who (an internal ID), what and when: failed logins, denied access, validation failures at trust boundaries, changes to permissions. | CWE-778 |
| SCB-6.5 | Logs and error trackers that leave the system are external systems in the data protection matrix: Restricted data does not go there without a waiver. | CWE-359 |

## SCB-7 Safe deserialization

| ID | Check | CWE |
|---|---|---|
| SCB-7.1 | Untrusted data is never fed to native object deserializers or loaders that can build arbitrary types (language-native binary serialization, YAML full loaders, polymorphic JSON type handling). | CWE-502 |
| SCB-7.2 | Use data-only formats (JSON, protocol buffers) mapped to explicit types, with a schema or typed model. | CWE-502 |
| SCB-7.3 | XML parsers have external entities and DTD processing turned off. | CWE-611, CWE-776 |
| SCB-7.4 | Data that must round-trip through the client (state, cookies) is signed or encrypted with a vetted library and verified before use. | CWE-345, CWE-565 |

## SCB-8 Cryptography only with vetted libraries

| ID | Check | CWE |
|---|---|---|
| SCB-8.1 | No home-made cryptography: no custom algorithms, modes, padding or key derivation. Use the high-level API of the platform or a well-known library. | CWE-327 |
| SCB-8.2 | No MD5, SHA-1, DES, RC4 or ECB mode for anything security-related. | CWE-327, CWE-328 |
| SCB-8.3 | Passwords are stored with a slow adaptive hash with a salt (Argon2, bcrypt, scrypt, PBKDF2), never encrypted or hashed with a fast hash. | CWE-916, CWE-759 |
| SCB-8.4 | Tokens, IDs that grant access, nonces and keys come from a cryptographically secure random generator. | CWE-330, CWE-338 |
| SCB-8.5 | Encryption uses authenticated modes (for example AES-GCM) with unique nonces; keys come from SCB-5, never from code. | CWE-323, CWE-321 |
| SCB-8.6 | TLS certificate and host name validation stay on, in every environment the code can reach. Data in transit goes over TLS. | CWE-295, CWE-319 |

## SCB-9 Errors that leak nothing

| ID | Check | CWE |
|---|---|---|
| SCB-9.1 | Responses to the caller have a generic message and a reference ID; no stack trace, SQL, file path, library version or internal host name. | CWE-209 |
| SCB-9.2 | Authentication errors do not tell which part failed ("user not found" versus "wrong password"). | CWE-204 |
| SCB-9.3 | Debug modes and detailed error pages are off in the configuration that ships. | CWE-489 |
| SCB-9.4 | Exceptions are not swallowed: they are logged on the server (with SCB-6) and turned into the generic error. | CWE-390 |

## SCB-10 Dependency hygiene

| ID | Check | CWE |
|---|---|---|
| SCB-10.1 | A new dependency is named in the plan. Otherwise it is a follow-up, not code. | CWE-1104 |
| SCB-10.2 | It is maintained (recent releases, an owner), comes from the official registry, and its name is checked against look-alike packages. | CWE-1104, CWE-829 |
| SCB-10.3 | Its version is pinned through the lockfile, and the lockfile is part of the change. | CWE-829 |
| SCB-10.4 | It has no known high or critical vulnerability. The stack pack's dependency scan skill runs it when installed; otherwise use the ecosystem's audit command from `.exo/context.md`. | CWE-1104 |
| SCB-10.5 | No step downloads and runs code (install scripts, remote scripts piped into a shell, unpinned CI actions) without a pinned version or an integrity check. | CWE-494 |
| SCB-10.6 | Prefer the standard library or an existing dependency over a new one for small needs. | CWE-1104 |
