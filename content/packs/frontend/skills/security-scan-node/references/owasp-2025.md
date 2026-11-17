# OWASP Top 10:2025 for Node projects

How `security-scan-node` maps findings. Cite the category as `A03:2025` and add the CWE, which is the stable identifier. The 2021 column helps when another skill (`security-code-review`, `judge-security`) cites the 2021 list for the same problem.

## The categories

| 2025 | Name | Closest 2021 category |
|---|---|---|
| A01:2025 | Broken Access Control | A01:2021, plus A10:2021 Server-Side Request Forgery |
| A02:2025 | Security Misconfiguration | A05:2021 |
| A03:2025 | Software Supply Chain Failures | A06:2021 Vulnerable and Outdated Components, widened to the whole supply chain |
| A04:2025 | Cryptographic Failures | A02:2021 |
| A05:2025 | Injection | A03:2021, cross-site scripting included |
| A06:2025 | Insecure Design | A04:2021 |
| A07:2025 | Authentication Failures | A07:2021 Identification and Authentication Failures |
| A08:2025 | Software or Data Integrity Failures | A08:2021 |
| A09:2025 | Security Logging and Alerting Failures | A09:2021 Security Logging and Monitoring Failures |
| A10:2025 | Mishandling of Exceptional Conditions | New; it gathers error handling that fails open or leaks |

When a finding fits two categories, pick the one that names its root cause and keep the CWE.

## Dependency findings

| Finding | Category | CWE |
|---|---|---|
| A package with a known vulnerability | A03:2025 | CWE-1395 |
| Unpinned versions, missing lockfile, untrusted sources, install scripts, typosquats | A03:2025 | CWE-829, CWE-1357 |
| Deprecated or unmaintained package | A03:2025 | CWE-1104 |
| Integrity or signature mismatch, tampered package | A08:2025 | CWE-494 |
| Registry over plain HTTP, TLS verification off for the registry | A02:2025 | CWE-295, CWE-319 |

## Code patterns

Severities assume the input comes from a request, a message or a user; lower it only when the code proves the input is trusted.

| Pattern | Signal in Node or browser code | Category | CWE | Usual severity |
|---|---|---|---|---|
| SQL injection | Template strings or concatenation in `knex.raw`, `db.query`, `sequelize.query`, `$queryRawUnsafe` | A05:2025 | CWE-89 | Critical |
| NoSQL injection | Request objects used as query filters; `$where` | A05:2025 | CWE-943 | High |
| OS command injection | `child_process.exec` or `execSync` with input; `spawn` with `shell: true` | A05:2025 | CWE-78 | Critical |
| Code injection | `eval`, `new Function`, `vm.runInNewContext` on input; `setTimeout` with a string | A05:2025 | CWE-95 | Critical |
| Cross-site scripting | `dangerouslySetInnerHTML`, `innerHTML`, `document.write` with untrusted content; `javascript:` URLs from input | A05:2025 | CWE-79 | High; Critical when stored |
| Template injection | User input compiled as a template (lodash `template`, Handlebars `compile`, EJS) | A05:2025 | CWE-1336 | Critical |
| Prototype pollution | Deep `merge`, `defaultsDeep`, `set` or `Object.assign` of request data; `obj[key] = value` with keys from input | A08:2025 | CWE-1321 | High |
| Unsafe deserialization | `node-serialize`, YAML with unsafe schemas, `serialize-javascript` output evaluated | A08:2025 | CWE-502 | Critical |
| Missing script integrity | Third-party scripts from a CDN without `integrity` and `crossorigin` | A08:2025 | CWE-353 | Medium |
| Missing authorization | A new route without the project's auth middleware; objects loaded by client IDs without an ownership check | A01:2025 | CWE-862, CWE-639 | High to Critical |
| Path traversal | `path.join(base, req.params.x)`, `res.sendFile(userPath)` without a resolved-prefix check | A01:2025 | CWE-22 | High |
| Server-side request forgery | `fetch(req.query.url)`, outbound calls to user-supplied hosts without an allow list | A01:2025 | CWE-918 | High |
| Open redirect | `res.redirect(req.query.next)` without a local-path check | A01:2025 | CWE-601 | Medium |
| Permissive CORS | `origin: '*'` or reflected origins with `credentials: true` | A02:2025 | CWE-942 | High |
| Debug or verbose errors in production | Stack traces in responses, `NODE_ENV` checks missing, `x-powered-by` left on | A02:2025 | CWE-489, CWE-209 | Medium |
| TLS verification off | `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0` | A02:2025 | CWE-295 | High |
| Insecure cookies | Session cookies without `HttpOnly`, `Secure` or `SameSite` | A02:2025 | CWE-614, CWE-1004 | Medium |
| Weak randomness | `Math.random()` for tokens, IDs or codes that must be unguessable | A04:2025 | CWE-330 | High |
| Weak hashing of passwords | `md5`, `sha1` or a fast hash for passwords | A04:2025 | CWE-916 | High |
| Hard-coded secrets | Keys and tokens in source, config or client bundles (`VITE_*`, `NEXT_PUBLIC_*`) | A04:2025 | CWE-798 | Critical when real |
| Tokens in web storage | Access or session tokens in `localStorage` | A07:2025 | CWE-922 | High |
| Broken token checks | `jwt.decode` instead of `verify`; `verify` without `algorithms`; secrets compared with `===` | A07:2025 | CWE-347, CWE-208 | High |
| No limits on abuse | Login or reset without rate limits; `express.json()` without `limit`; regular expressions open to ReDoS on input | A06:2025 | CWE-307, CWE-770, CWE-1333 | Medium |
| Secrets or personal data in logs | Request bodies, tokens or card data in `console.log` or the logger | A09:2025 | CWE-532 | High |
| Security events not logged | Failed sign-ins, permission changes, admin actions with no log | A09:2025 | CWE-778 | Low to Medium |
| Errors that fail open | `catch` in an auth or validation path that calls `next()` or returns success; unhandled rejections that leave a request half-done | A10:2025 | CWE-636, CWE-755 | High |
| Unchecked results | Responses used without checking status; `await` missing on a check that can fail | A10:2025 | CWE-252 | Medium |

## Writing the finding

- One finding per weakness and location: `PAT-1 | High | packages/api/src/routes/preferences.js:12 | <what and why> | A08:2025, CWE-1321`.
- Say the source, the sink and the missing control. A pattern with no path from input is hardening (Low) at most.
- Never write a working exploit or payload; describe the weakness and the fix in text.
