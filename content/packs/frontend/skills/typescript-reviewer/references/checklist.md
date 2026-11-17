# TypeScript and JavaScript review checklist

The rule IDs that `typescript-reviewer` cites. Each item says what to look for, the usual signal in a diff, and what is not a finding. Security items carry their CWE; cite it next to the ID, with the OWASP Top 10:2025 category of that CWE from `.exo/shared/owasp-2025.md`, written with its year: `TS-SEC-1 (CWE-79, A05:2025 Injection)`. An item with several CWEs: cite the one that describes the finding.

## TS-TYPE Types

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-TYPE-1 | `any`, explicit or implied | `: any`, `as any`, `useState<any>`, untyped parameters in a file the compiler does not check strictly, `Function` or `object` as parameter types | `any` in a `.d.ts` shim for an untyped library, with a comment |
| TS-TYPE-2 | Cast without a check | `value as Product` on data nobody checked; `as unknown as T` | `as` right after a guard that proves it; `as const` |
| TS-TYPE-3 | Non-null assertion without a guarantee | `user!.id`, `map.get(key)!` where the value can be missing | The entry point's root element, with a comment |
| TS-TYPE-4 | External data used as a typed value | `JSON.parse(x) as T`, `(await res.json()) as T`, `localStorage` or `postMessage` data read field by field without validation | Parsed with a schema or a type guard; your own backend with a shared versioned contract, said in a comment |
| TS-TYPE-5 | Union not handled exhaustively | `switch` on a tag with no `never` check, so a new case falls through silently | — |
| TS-TYPE-6 | Suppressed errors | `// @ts-ignore`, `// @ts-nocheck`, `// eslint-disable` for type rules without a reason | `// @ts-expect-error <reason>` for a known limitation |
| TS-TYPE-7 | Compiler or lint settings loosened | `strict: false`, a strict flag turned off, `skipLibCheck` added to hide an error, rules disabled in the config | A setting changed as the stated goal of the change |
| TS-TYPE-8 | Optional fields where a union belongs | A type with several optional fields whose valid combinations are fixed (`paidAt?` and `failureReason?` both optional) | — |

## TS-ASYNC Async

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-ASYNC-1 | Floating promise | A call that returns a promise with no `await`, `return`, `.catch` or `void` with a reason; `fetch(...)` fired inside `try` without `await` | `void promise` with a comment that the failure is handled elsewhere |
| TS-ASYNC-2 | `async` callback where the caller ignores the promise | `items.forEach(async (x) => ...)`, async event handlers whose rejection nobody catches, `async` callbacks passed to `setTimeout` | `for ... of` with `await`, `Promise.all(items.map(...))` |
| TS-ASYNC-3 | Needless sequential awaits | Independent `await`s one after another in a hot path | Order that matters, or a deliberate limit on concurrency |
| TS-ASYNC-4 | Race between requests | An effect or handler that sets state from a response without aborting or ignoring stale ones (`AbortController`, a request ID) | Requests that cannot overlap |
| TS-ASYNC-5 | Unhandled rejection in server code | Express 4 async handlers without a wrapper; event emitters and streams without `error` listeners; top-level promises without `.catch` | Express 5 (forwards rejected promises); a central wrapper the project uses |
| TS-ASYNC-6 | Timers and listeners never cleared | `setInterval`, `addEventListener` or subscriptions without cleanup | Cleanup in the effect's return or in `finally` |

## TS-ERR Errors

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-ERR-1 | Swallowed error | `catch {}`, `catch (e) { console.log(e) }` on the main path, `.catch(() => {})`, a fallback value that makes a failure look like success | A documented best-effort path with a log |
| TS-ERR-2 | `catch` that cannot catch | `try { promiseReturningCall(); } catch` without `await` | — |
| TS-ERR-3 | Unchecked HTTP responses | `fetch` result used without checking `response.ok` or the status | A client wrapper that throws on non-2xx (check it) |
| TS-ERR-4 | Unsafe access to the caught value | `(e as Error).message`, `e.message` on `unknown` | `e instanceof Error ? e.message : String(e)` |
| TS-ERR-5 | Non-errors thrown or errors without cause | `throw 'failed'`, `throw { code }`, rethrowing a new error without `{ cause }` | — |
| TS-ERR-6 | Internal details to the client | Stack traces, SQL messages or exception text in API responses or UI | A generic message to the client and the detail in the server log |

## TS-SEC Security

| ID | What | Signal | CWE | Not a finding |
|---|---|---|---|---|
| TS-SEC-1 | Cross-site scripting | `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` with content a user or a third party controls; `v-html`; markdown rendered to HTML without a sanitizer | CWE-79 | React text interpolation; content sanitized with a vetted sanitizer right before rendering |
| TS-SEC-2 | Script URLs and dynamic code | `href` or `src` built from input without a scheme allow list (`javascript:`); `eval`, `new Function`, `setTimeout` with a string | CWE-79, CWE-95 | URLs checked against `https:` and `mailto:` |
| TS-SEC-3 | SQL and NoSQL injection | Template strings or concatenation in `knex.raw`, `db.query`, `sequelize.query`, `$queryRawUnsafe`; request objects passed as query filters (`{ email: req.body.email }` accepting `{ "$ne": null }`), `$where` | CWE-89, CWE-943 | Query builders, bound parameters (`knex.raw('... ?', [value])`), tagged `$queryRaw` |
| TS-SEC-4 | OS command injection | `child_process.exec` or `execSync` with input in the string; `spawn` with `shell: true` | CWE-78 | `execFile` or `spawn` with an argument array and no shell |
| TS-SEC-5 | Path traversal | `path.join(base, req.params.name)` or `res.sendFile(userPath)` with no check that the resolved path stays in the base; archive extraction without checking entry paths | CWE-22 | `path.resolve` plus a prefix check, or an allow list of names |
| TS-SEC-6 | Server-side request forgery | `fetch(req.query.url)`, `axios.get(userUrl)`, webhooks to user-supplied hosts without an allow list | CWE-918 | Fixed hosts; an allow list checked after resolving redirects |
| TS-SEC-7 | Prototype pollution | Deep merge or `set` of request data into objects (`merge({}, req.body)`, `obj[key] = value` with keys from input), `Object.assign` of parsed JSON into shared objects | CWE-1321 | Keys checked against an allow list, `Object.create(null)` maps, `Map` |
| TS-SEC-8 | Unsafe deserialization | `node-serialize`, `serialize-javascript` output passed to `eval`, YAML loaded with an unsafe schema, `vm` used as a sandbox for untrusted code | CWE-502 | `JSON.parse` followed by validation |
| TS-SEC-9 | Open redirect | `res.redirect(req.query.next)`, `window.location = params.get('return')` without checking it is a local path | CWE-601 | Relative paths only, or an allow list of hosts |
| TS-SEC-10 | Secrets in the client or in code | Keys or tokens in browser code, `VITE_*`, `NEXT_PUBLIC_*` or `REACT_APP_*` variables holding secrets, literals in source or config | CWE-798, CWE-200 | Public identifiers meant for the browser (a publishable key, an analytics ID) |
| TS-SEC-11 | Tokens in web storage | Session or access tokens written to `localStorage` or `sessionStorage`, where any XSS can read them | CWE-922 | `HttpOnly`, `Secure`, `SameSite` cookies |
| TS-SEC-12 | `postMessage` without origin checks | `window.addEventListener('message', ...)` that does not check `event.origin`; `postMessage(data, '*')` with sensitive data | CWE-346 | An exact origin check |
| TS-SEC-13 | Broken authentication checks | `jwt.decode` used instead of `verify`; `verify` without pinned `algorithms`; secrets or tokens compared with `===` | CWE-347, CWE-208 | `jwt.verify` with `algorithms`; `crypto.timingSafeEqual` on equal-length buffers |
| TS-SEC-14 | Missing authorization | A new route or server action without the project's auth middleware; objects loaded by an ID from the client without an ownership check | CWE-862, CWE-639 | Routes public on purpose |
| TS-SEC-15 | Permissive configuration | CORS `origin: '*'` or reflected origins with `credentials: true`; cookies without `HttpOnly`, `Secure`, `SameSite`; TLS checks off (`rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`) | CWE-942, CWE-614, CWE-295 | Development-only config that never ships |
| TS-SEC-16 | Sensitive data in logs | Request bodies, headers with tokens, card data or personal data in `console.log` or the logger | CWE-532 | Identifiers and masked values |
| TS-SEC-17 | Regular expressions open to ReDoS | Nested quantifiers (`(a+)+`, `(.*)*`) applied to input without a length limit | CWE-1333 | Bounded input, linear patterns |
| TS-SEC-18 | Weak randomness or hashing | `Math.random()` for tokens or IDs that must be unguessable; `md5` or `sha1` for passwords | CWE-330, CWE-916 | `crypto.randomUUID`, `crypto.getRandomValues`, `crypto.randomBytes`; `scrypt`, `argon2`, `bcrypt` |

## TS-REACT React

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-REACT-1 | Effect dependencies wrong | Values used inside `useEffect`, `useMemo` or `useCallback` missing from the dependency array, or the lint rule disabled | Stable refs and setters |
| TS-REACT-2 | Effect without cleanup | Subscriptions, timers, listeners or requests started in an effect with no cleanup | — |
| TS-REACT-3 | State mutated in place | `state.items.push(x); setState(state)`, sorting a state array in place | New arrays and objects |
| TS-REACT-4 | Unstable or index keys in dynamic lists | `key={index}` on lists that reorder, insert or delete; missing keys | Static lists |
| TS-REACT-5 | Derived state copied into state | `useState(props.value)` kept in sync with an effect | Computing it during render |
| TS-REACT-6 | Rules of hooks | Hooks called conditionally or in loops | — |

## TS-NODE Node runtime

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-NODE-1 | Blocking the event loop in request paths | `fs.readFileSync`, `crypto.pbkdf2Sync`, large `JSON.parse` or CPU loops inside handlers | Start-up code, scripts |
| TS-NODE-2 | Unbounded input | `express.json()` without a `limit` in a public API, uploads without size limits, pagination without a maximum | Limits set |
| TS-NODE-3 | Streams without error handling | `pipe` without `pipeline` or `error` listeners | `stream.pipeline` |
| TS-NODE-4 | `process.exit` in library code | Exits from modules other than the CLI entry point | The entry point |
| TS-NODE-5 | Configuration read everywhere | `process.env.X` read across modules instead of one config module validated at start-up | The config module |

## TS-TEST Tests

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-TEST-1 | New behavior without a test | New function, branch, route or component behavior with no test that exercises it | Pure refactors covered by existing tests |
| TS-TEST-2 | Test that cannot fail | No assertion, assertions only on mocks, `expect(true)`, an `await` missing so the assertion runs after the test ends | — |
| TS-TEST-3 | Real network or time | Tests that call real services, depend on `Date.now()` or sleep | Mocked fetch (MSW, a fake client), fake timers |
| TS-TEST-4 | Snapshot as the only check of logic | A large snapshot standing in for assertions on behavior | Small snapshots of stable output |
| TS-TEST-5 | Scenario of the spec without its test | In an SDD change, a scenario `S-n` with no test named for it | — |

## TS-STYLE Style

| ID | What | Signal | Not a finding |
|---|---|---|---|
| TS-STYLE-1 | Breaks the project's lint or naming rules | What the project's ESLint or Biome config would flag | Rules the project disables |
| TS-STYLE-2 | Debug leftovers | `console.log`, `debugger`, commented-out code, `.only` in tests | Intentional logs through the project's logger |
| TS-STYLE-3 | Dead or duplicated code | Unused exports, copies of an existing helper | — |
