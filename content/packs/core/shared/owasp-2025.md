# OWASP Top 10:2025

The one table that maps a weakness (its CWE) to its OWASP Top 10:2025 category. The `security` pack (`security-code-review`, `secure-coding-baseline`, `threat-modeling`), the judges and reviews that reuse it (`judge-security`, `review-4r`, `harness-review`), the stack scanners (`security-scan-jkp`, `security-scan-node`) and the stack reviewers (`java-reviewer`, `typescript-reviewer`, `python-reviewer`) take their categories from here, so the same weakness gets the same category in every report.

## How to cite

- **Always with the year:** `A05:2025 Injection`, never a bare `A05`. The same number names a different category in each edition.
- **The CWE goes first,** then the category with its year and name: `CWE-89, A05:2025 Injection`. The CWE is stable across editions, the category is not. This is the format of every finding, gate row and followup `rule`; a check ID or a STRIDE category goes before it (`SCR-AUTHZ-2, CWE-639, A01:2025 Broken Access Control`), and the word `OWASP` does not. Only a table that maps a rule or a signal to its category lists the CWEs it covers after the name (`A05:2025 Injection (CWE-89, CWE-78)`).
- **A CWE that MITRE deprecated:** cite the entry that replaces it. The table keeps the old one, marked `deprecated`, to translate an older report.
- **One category per finding,** from its CWE in the table below. When a finding has two CWEs in different categories, cite the category of the one the fix addresses: CSRF left off for a cookie session is `CWE-352`, `A01:2025`, because the fix restores a missing access control.
- **A CWE the table does not list:** use the category of its closest parent or sibling in the table and say `closest`; never invent a category.
- **Dependency findings** (a vulnerable, unmaintained or untrusted package) are `A03:2025 Software Supply Chain Failures`, whatever the weakness inside the library: name that weakness in the finding text ("remote code execution through JNDI lookups").
- **The 2021 edition:** no skill cites the Top 10:2021 any more. The last column of the next table stays to translate an older report, gate or followup that does: re-cite its finding from the CWE, never by renumbering (server-side request forgery, a category of its own in 2021, is now part of `A01:2025 Broken Access Control`). Keep each edition's year so nobody mixes them.

## The categories

| 2025 | Category | What it covers | 2021 equivalent |
|---|---|---|---|
| A01:2025 | Broken Access Control | missing or wrong authorization, object-level access (IDOR), CSRF, path traversal, open redirects, sensitive data reachable without authorization, server-side request forgery (SSRF) | A01:2021, plus A10:2021 Server-Side Request Forgery |
| A02:2025 | Security Misconfiguration | insecure defaults, debug modes, exposed management endpoints, permissive CORS, insecure cookie flags, XML external entities, missing hardening | A05:2021 |
| A03:2025 | Software Supply Chain Failures | vulnerable, unmaintained or untrusted dependencies, build plugins and pipeline steps; unpinned versions; compromised registries | A06:2021 Vulnerable and Outdated Components, widened to the whole supply chain |
| A04:2025 | Cryptographic Failures | weak or home-made cryptography, weak password hashing, predictable randomness for secrets, cleartext transport, unverified signatures | A02:2021 |
| A05:2025 | Injection | SQL, NoSQL, OS command, code, expression language and template injection, and cross-site scripting | A03:2021 |
| A06:2025 | Insecure Design | missing controls in the design: no limits on abuse or resources, business logic that can be abused, security enforced only on the client, unrestricted file uploads, privilege management, secrets in query strings, no threat model for a risky flow | A04:2021 |
| A07:2025 | Authentication Failures | weak sign-in, missing lockout, account enumeration, session and token handling, hard-coded or default credentials, certificate validation turned off, origin checks | A07:2021 Identification and Authentication Failures |
| A08:2025 | Software or Data Integrity Failures | deserialization of untrusted data, prototype pollution, code or packages loaded without an integrity check, unsigned updates | A08:2021 |
| A09:2025 | Security Logging and Alerting Failures | security events not logged or not alerted, sensitive data in logs, log injection | A09:2021 Security Logging and Monitoring Failures |
| A10:2025 | Mishandling of Exceptional Conditions | errors that fail open, swallowed exceptions, unchecked results, error messages and debug output that leak internals | new in 2025 |

## CWE to category

The CWEs that the `security` pack and the stack skills use. `listed` means OWASP maps the CWE to that category; `closest` means OWASP does not list it, and the category is the one of its nearest listed relative or, when the note says so, the one whose OWASP page names that weakness.

| CWE | Weakness | Category | Mapping |
|---|---|---|---|
| CWE-16 | Insecure configuration (exposed management endpoints) | A02:2025 Security Misconfiguration | listed |
| CWE-20 | Input not validated | A05:2025 Injection | listed |
| CWE-22 | Path traversal | A01:2025 Broken Access Control | listed |
| CWE-59 | Link following out of the intended folder | A01:2025 Broken Access Control | listed |
| CWE-78 | OS command injection | A05:2025 Injection | listed |
| CWE-79 | Cross-site scripting | A05:2025 Injection | listed |
| CWE-89 | SQL injection | A05:2025 Injection | listed |
| CWE-90 | LDAP injection | A05:2025 Injection | listed |
| CWE-94 | Code injection | A05:2025 Injection | listed |
| CWE-95 | Eval injection | A05:2025 Injection | listed |
| CWE-116 | Output not encoded or escaped for its context | A05:2025 Injection | listed |
| CWE-117 | Log injection | A09:2025 Security Logging and Alerting Failures | listed |
| CWE-200 | Sensitive information exposed to an unauthorized actor | A01:2025 Broken Access Control | listed |
| CWE-204 | Responses that differ by outcome (account enumeration) | A07:2025 Authentication Failures | closest (A07 names account enumeration among what to prevent) |
| CWE-208 | Timing-unsafe comparison of secrets | A07:2025 Authentication Failures | closest |
| CWE-209 | Error message with sensitive information | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-215 | Sensitive information in debugging output | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-252 | Unchecked return value or response | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-256 | Credentials stored unprotected (plain text or reversible) | A06:2025 Insecure Design | listed |
| CWE-269 | Improper privilege management | A06:2025 Insecure Design | listed |
| CWE-285 | Improper authorization (function-level checks) | A01:2025 Broken Access Control | listed |
| CWE-287 | Improper authentication (a token accepted without full verification) | A07:2025 Authentication Failures | listed |
| CWE-290 | Authentication bypass by spoofing (a caller identity not verified) | A07:2025 Authentication Failures | listed |
| CWE-295 | Certificate validation turned off | A07:2025 Authentication Failures | listed |
| CWE-306 | Missing authentication for a critical function | A07:2025 Authentication Failures | listed |
| CWE-307 | No limit on failed sign-in attempts | A07:2025 Authentication Failures | listed |
| CWE-319 | Cleartext transmission of sensitive data | A04:2025 Cryptographic Failures | listed |
| CWE-321 | Hard-coded cryptographic key | A04:2025 Cryptographic Failures | listed |
| CWE-323 | Reused nonce or key pair | A04:2025 Cryptographic Failures | listed |
| CWE-327 | Broken or risky cryptographic algorithm | A04:2025 Cryptographic Failures | listed |
| CWE-328 | Weak hash (MD5, SHA-1) | A04:2025 Cryptographic Failures | listed |
| CWE-330 | Predictable randomness | A04:2025 Cryptographic Failures | listed |
| CWE-338 | Cryptographically weak random generator | A04:2025 Cryptographic Failures | listed |
| CWE-345 | Data authenticity not verified (unsigned messages, webhooks or round-tripped state) | A08:2025 Software or Data Integrity Failures | listed |
| CWE-346 | Origin not validated (`postMessage`) | A07:2025 Authentication Failures | listed |
| CWE-347 | Cryptographic signature not verified (a JWT decoded without verification) | A04:2025 Cryptographic Failures | listed |
| CWE-352 | Cross-site request forgery | A01:2025 Broken Access Control | listed |
| CWE-353 | Third-party code loaded without an integrity check | A08:2025 Software or Data Integrity Failures | listed |
| CWE-359 | Personal information exposed to an unauthorized actor | A01:2025 Broken Access Control | listed |
| CWE-377 | Insecure temporary file | A01:2025 Broken Access Control | listed |
| CWE-384 | Session fixation (session ID not renewed after sign-in) | A07:2025 Authentication Failures | listed |
| CWE-390 | Error detected and ignored | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-434 | Unrestricted file upload | A06:2025 Insecure Design | listed |
| CWE-489 | Debug mode left on | A02:2025 Security Misconfiguration | listed |
| CWE-494 | Code or package downloaded without an integrity check | A08:2025 Software or Data Integrity Failures | listed |
| CWE-502 | Deserialization of untrusted data | A08:2025 Software or Data Integrity Failures | listed |
| CWE-532 | Sensitive data in logs | A09:2025 Security Logging and Alerting Failures | listed |
| CWE-540 | Sensitive information in source code (a committed secret) | A01:2025 Broken Access Control | listed |
| CWE-565 | Cookies trusted without validation or an integrity check | A08:2025 Software or Data Integrity Failures | listed |
| CWE-598 | Sensitive data in a GET query string | A06:2025 Insecure Design | listed |
| CWE-601 | Open redirect | A01:2025 Broken Access Control | listed |
| CWE-602 | Server-side security enforced only on the client | A06:2025 Insecure Design | listed |
| CWE-611 | XML external entities | A02:2025 Security Misconfiguration | listed |
| CWE-613 | Insufficient session expiration (deprecated in CWE 5.0: cite CWE-1463 or CWE-1464) | A07:2025 Authentication Failures | listed |
| CWE-614 | Session cookie without `Secure` | A02:2025 Security Misconfiguration | listed |
| CWE-617 | `assert` used as a security check | A10:2025 Mishandling of Exceptional Conditions | closest |
| CWE-636 | Failing open | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-639 | Object-level authorization bypass (IDOR) | A01:2025 Broken Access Control | listed |
| CWE-643 | XPath injection | A05:2025 Injection | listed |
| CWE-755 | Exceptional condition handled wrongly (swallowed or defaulted) | A10:2025 Mishandling of Exceptional Conditions | listed |
| CWE-759 | Password hash without a salt | A04:2025 Cryptographic Failures | listed |
| CWE-770 | Resources allocated without limits | A06:2025 Insecure Design | closest |
| CWE-776 | XML entity expansion | A02:2025 Security Misconfiguration | listed |
| CWE-778 | Security events not logged | A09:2025 Security Logging and Alerting Failures | listed |
| CWE-798 | Hard-coded credentials | A07:2025 Authentication Failures | listed |
| CWE-829 | Functionality included from an untrusted source | A08:2025 Software or Data Integrity Failures | listed |
| CWE-862 | Missing authorization | A01:2025 Broken Access Control | listed |
| CWE-863 | Incorrect authorization (the check tests the wrong thing) | A01:2025 Broken Access Control | listed |
| CWE-915 | Mass assignment (object attributes set from the request) | A08:2025 Software or Data Integrity Failures | listed |
| CWE-916 | Password hash with too little effort | A04:2025 Cryptographic Failures | listed |
| CWE-917 | Expression language injection | A05:2025 Injection | listed |
| CWE-918 | Server-side request forgery | A01:2025 Broken Access Control | listed |
| CWE-922 | Tokens or secrets in insecure storage (`localStorage`) | A01:2025 Broken Access Control | listed |
| CWE-942 | Permissive cross-origin policy (CORS) | A02:2025 Security Misconfiguration | listed |
| CWE-943 | NoSQL injection | A05:2025 Injection | closest |
| CWE-1004 | Session cookie without `HttpOnly` | A02:2025 Security Misconfiguration | listed |
| CWE-1104 | Unmaintained third-party component | A03:2025 Software Supply Chain Failures | listed |
| CWE-1188 | Insecure default (a fallback secret, or a check that turns off when a setting is missing) | A02:2025 Security Misconfiguration | closest (A02 names insecure default settings) |
| CWE-1275 | Session cookie without `SameSite` | A01:2025 Broken Access Control | listed |
| CWE-1321 | Prototype pollution | A08:2025 Software or Data Integrity Failures | closest (its parent CWE-915 is listed) |
| CWE-1333 | Regular expression open to ReDoS | A06:2025 Insecure Design | closest |
| CWE-1336 | Template injection | A05:2025 Injection | closest |
| CWE-1357 | Insufficiently trustworthy component (unpinned, unexpected source, typosquat) | A03:2025 Software Supply Chain Failures | listed |
| CWE-1395 | Dependency on a vulnerable third-party component | A03:2025 Software Supply Chain Failures | listed |
| CWE-1463 | Session timeout too long | A07:2025 Authentication Failures | closest (it replaces CWE-613, which A07:2025 lists) |
| CWE-1464 | Session not invalidated on logout or a credential change | A07:2025 Authentication Failures | closest (it replaces CWE-613, which A07:2025 lists) |

## Dependency and supply-chain findings

| Finding | CWE | Category |
|---|---|---|
| A package version with a known vulnerability | CWE-1395 | A03:2025 |
| A deprecated, archived or unmaintained package | CWE-1104 | A03:2025 |
| Unpinned or loose versions, a missing lockfile, an unexpected registry or source, new install scripts, a likely typosquat | CWE-1357 | A03:2025 |
| An integrity or signature mismatch for the same version (possible tampering) | CWE-494 | A08:2025 |
| TLS verification turned off for the registry or the build | CWE-295 | A07:2025 |
