# OWASP Top 10:2025

Write each category with its year (`A05:2025 Injection`): the other security skills of the engine (`security-code-review`, `judge-security`) cite the 2021 edition, and the same number means different things in each.

| 2025 | Category | What it covers | 2021 equivalent |
|---|---|---|---|
| A01:2025 | Broken Access Control | missing or wrong authorization, object-level access (IDOR), path traversal, CORS mistakes, and server-side request forgery (SSRF) | A01:2021, plus A10:2021 SSRF |
| A02:2025 | Security Misconfiguration | insecure defaults, debug modes, verbose errors, exposed admin or Actuator endpoints, missing hardening, XML external entities | A05:2021 |
| A03:2025 | Software Supply Chain Failures | vulnerable, outdated or untrusted dependencies, build plugins and pipeline steps; unpinned versions; compromised registries | A06:2021 Vulnerable and Outdated Components, widened |
| A04:2025 | Cryptographic Failures | weak or home-made cryptography, weak hashes for passwords, predictable randomness, disabled TLS validation, unencrypted sensitive data | A02:2021 |
| A05:2025 | Injection | SQL, NoSQL, OS command, LDAP, expression language and template injection, and cross-site scripting | A03:2021 |
| A06:2025 | Insecure Design | missing controls in the design: no limits, no threat model for a risky flow, business logic abuse | A04:2021 |
| A07:2025 | Authentication Failures | weak sign-in, credential stuffing, session and token handling, hard-coded credentials | A07:2021 Identification and Authentication Failures |
| A08:2025 | Software or Data Integrity Failures | deserialization of untrusted data, unsigned updates, integrity of data and code not verified | A08:2021 |
| A09:2025 | Security Logging and Alerting Failures | security events not logged or not alerted, sensitive data in logs, log injection | A09:2021 Security Logging and Monitoring Failures |
| A10:2025 | Mishandling of Exceptional Conditions | errors that fail open, swallowed exceptions, unhandled edge cases, error messages that leak internals | new in 2025 |

## Mapping rules

- **Dependency findings** are `A03:2025 Software Supply Chain Failures`, whatever the vulnerability inside the library is. Mention the library's own weakness in the finding text (for example "remote code execution through JNDI lookups").
- **Code findings** take the category of the weakness: an injected query is A05, a deserialized request body is A08, an unchecked URL fetch is A01.
- **When two fit,** choose the one the fix addresses: CSRF disabled for a cookie session is A01 (the access control is missing), not A02.
- Always add the CWE: it is stable across editions.
