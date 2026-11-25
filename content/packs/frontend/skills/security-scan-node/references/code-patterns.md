# Insecure code patterns for Node projects

The Node and browser patterns that `security-scan-node` looks for in the changed files. Each one names its CWE; its OWASP Top 10:2025 category comes from that CWE in `.exo/shared/owasp-2025.md`, written with its year (`A05:2025`), and the same file has the categories of dependency and supply-chain findings.

## Patterns

Severities assume the input comes from a request, a message or a user; lower it only when the code proves the input is trusted. A row with several CWEs: cite the one that describes the finding (a `jwt.decode` without verification is CWE-347; a token compared with `===` is CWE-208).

| Pattern | Signal in Node or browser code | CWE | Usual severity |
|---|---|---|---|
| SQL injection | Template strings or concatenation in `knex.raw`, `db.query`, `sequelize.query`, `$queryRawUnsafe` | CWE-89 | Critical |
| NoSQL injection | Request objects used as query filters; `$where` | CWE-943 | High |
| OS command injection | `child_process.exec` or `execSync` with input; `spawn` with `shell: true` | CWE-78 | Critical |
| Code injection | `eval`, `new Function`, `vm.runInNewContext` on input; `setTimeout` with a string | CWE-95 | Critical |
| Cross-site scripting | `dangerouslySetInnerHTML`, `innerHTML`, `document.write` with untrusted content; `javascript:` URLs from input | CWE-79 | High; Critical when stored |
| Template injection | User input compiled as a template (lodash `template`, Handlebars `compile`, EJS) | CWE-1336 | Critical |
| Prototype pollution | Deep `merge`, `defaultsDeep`, `set` or `Object.assign` of request data; `obj[key] = value` with keys from input | CWE-1321 | High |
| Unsafe deserialization | `node-serialize`, YAML with unsafe schemas, `serialize-javascript` output evaluated | CWE-502 | Critical |
| Missing script integrity | Third-party scripts from a CDN without `integrity` and `crossorigin` | CWE-353 | Medium |
| Missing authorization | A new route without the project's auth middleware; objects loaded by client IDs without an ownership check | CWE-862, CWE-639 | High to Critical |
| Path traversal | `path.join(base, req.params.x)`, `res.sendFile(userPath)` without a resolved-prefix check | CWE-22 | High |
| Server-side request forgery | `fetch(req.query.url)`, outbound calls to user-supplied hosts without an allow list | CWE-918 | High |
| Open redirect | `res.redirect(req.query.next)` without a local-path check | CWE-601 | Medium |
| Permissive CORS | `origin: '*'` or reflected origins with `credentials: true` | CWE-942 | High |
| Debug or verbose errors in production | Stack traces in responses, `NODE_ENV` checks missing, `x-powered-by` left on | CWE-489, CWE-209 | Medium |
| TLS verification off | `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0` | CWE-295 | High |
| Insecure cookies | Session cookies without `HttpOnly`, `Secure` or `SameSite` | CWE-614, CWE-1004 | Medium |
| Weak randomness | `Math.random()` for tokens, IDs or codes that must be unguessable | CWE-330 | High |
| Weak hashing of passwords | `md5`, `sha1` or a fast hash for passwords | CWE-916 | High |
| Hard-coded secrets | Keys and tokens in source, config or client bundles (`VITE_*`, `NEXT_PUBLIC_*`) | CWE-798 | Critical when real |
| Tokens in web storage | Access or session tokens in `localStorage` | CWE-922 | High |
| Broken token checks | `jwt.decode` instead of `verify`; `verify` without `algorithms`; secrets compared with `===` | CWE-347, CWE-208 | High |
| No limits on abuse | Login or reset without rate limits; `express.json()` without `limit`; regular expressions open to ReDoS on input | CWE-307, CWE-770, CWE-1333 | Medium |
| Secrets or personal data in logs | Request bodies, tokens or card data in `console.log` or the logger | CWE-532 | High |
| Security events not logged | Failed sign-ins, permission changes, admin actions with no log | CWE-778 | Low to Medium |
| Errors that fail open | `catch` in an auth or validation path that calls `next()` or returns success; unhandled rejections that leave a request half-done | CWE-636, CWE-755 | High |
| Unchecked results | Responses used without checking status; `await` missing on a check that can fail | CWE-252 | Medium |

## Writing the finding

- One finding per weakness and location: `PAT-1 | High | packages/api/src/routes/preferences.js:12 | <what and why> | CWE-1321, A08:2025 Software or Data Integrity Failures`.
- Say the source, the sink and the missing control. A pattern with no path from input is hardening (Low) at most.
- Never write a working exploit or payload; describe the weakness and the fix in text.
