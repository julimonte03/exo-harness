---
name: typescript-reviewer
description: >-
  Reviews a TypeScript or JavaScript diff, read-only: type safety (any,
  unchecked casts, non-null assertions, unvalidated external data), async
  correctness (floating promises, missing awaits, races, unhandled
  rejections), error handling, and Node and web security (injection, XSS,
  prototype pollution, SSRF, path traversal, open redirects, secrets in client
  bundles or logs). Every finding has a severity, its path:line, a rule ID
  from a stable checklist and a fix as text, and the review ends with a
  verdict line. Runs the project's type check and linter only if it has them.
  Use it when someone asks for a review of TypeScript, JavaScript, React or
  Node code, a branch or a pull request, or before a PR on a Node or frontend
  project; in SDD verify its Critical and High findings go to Issues Found.
  Not for accessibility audits or writing code. Triggers:
  "review this TypeScript", "review my changes", "code review this PR",
  "review the staged diff", "is this Node code safe", "check this component
  for bugs".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: read-only
---

# typescript-reviewer

## Result

A review of the TypeScript and JavaScript files a diff touches: a findings table ordered by severity, each finding with its `path:line`, what is wrong, its rule ID from `references/checklist.md` (with the CWE when it is a security finding) and a fix as text; the tools that ran and the ones that could not; what was not reviewed; and a last line `Verdict: approve` or `Verdict: request changes`. You change nothing.

## When

- Someone asks for a review of TypeScript or JavaScript code (`.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs`, `.cjs`): staged or uncommitted changes, a branch, a pull request, or files they name.
- Before opening a PR on a Node, React or other TypeScript project, when the person wants a stack-specific review.
- In SDD verify, as a stack complement to skill:harness-review, when the stack router (`frontend-engineering`) or the person asks for it.
- **Not for:** writing or fixing code (skill:typescript after the review); accessibility (skill:accessibility-audit); visual design and design-system fit (`frontend-design`, `judge-frontend`); a dependency audit (skill:security-scan-node); the full review of a change with its gates (skill:harness-review and skill:security-code-review).

## Permissions

- **Read-only.** Read and search files; run read-only git (`git diff`, `git diff --cached`, `git log`, `git show`, `git status`).
- Run only the type check, lint and test commands of `.exo/context.md` or `package.json` scripts, and only when the project has the tool installed. Never install a package, never run `npx` on a package the project does not have (it downloads it), never run a formatter or a linter in fix mode, never edit, stage, stash or commit.
- Never copy a secret or personal data into a finding: point at `path:line` and say what kind of data it is (`.exo/shared/data-protection.md`).

## Steps

1. **Scope.** Find the diff: `git diff --cached --stat` for staged changes, `git diff --stat` for unstaged ones, `git diff <target>...HEAD --stat` for a branch. Review the TypeScript and JavaScript files, plus what they depend on: `tsconfig.json`, `package.json` and lockfiles when they change, environment and build config (`vite.config.*`, `.env.example`).
2. **Context.** Read `.exo/context.md`, the tsconfig that covers each file, and the workspace layout in a monorepo (which package is browser code, which is server code: the rules differ). In an SDD change, also the spec and, when present, design.md and tasks.md: a scenario without a test is a finding.
3. **Whole files.** Read each changed file in full, not only its hunks. Follow every new input (request body, query, params, headers, cookies, URL, `postMessage`, storage, third-party response) to where it is used (query, command, path, HTML, URL, object key, log), one call into callers and callees when the flow leaves the file.
4. **Tools, when the project has them.** The type check (`tsc --noEmit`, `npm run typecheck`), the linter (`eslint`), the tests. Report each exact command with its result. When you cannot run them (no shell permission, no `node_modules`), give the exact command and review those points by hand; never report a result you did not see.
5. **Walk the checklist** below, category by category, with `references/checklist.md`.
6. **Confirm** each finding (Confirm before reporting), rate it (Severity) and write the fix as text.
7. **Return** the review (Return).

## What to look for

| Category | Look for | Rule IDs |
|---|---|---|
| Types | `any` (explicit or implied), `as` casts with no check, `as unknown as`, `!` without a guarantee, `@ts-ignore`, external data used as a typed value, non-exhaustive unions, loosened tsconfig flags | TS-TYPE |
| Async | Promises not awaited or returned, `async` callbacks in `forEach`, sequential awaits that could run together, races between requests, effects without cancellation, unhandled rejections | TS-ASYNC |
| Errors | Empty or swallowing `catch`, `catch` that cannot catch (around a promise not awaited), `(e as Error).message`, thrown non-errors, responses used without checking `ok` or status | TS-ERR |
| Security, web | `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `javascript:` URLs, `eval` and `new Function`, `postMessage` without an origin check, tokens in `localStorage`, secrets in client bundles (`VITE_*`, `NEXT_PUBLIC_*`), open redirects | TS-SEC |
| Security, Node | SQL or NoSQL built from input, `child_process.exec` with input, path traversal, SSRF, prototype pollution, unsafe deserialization, JWT decoded without verification, secrets compared with `===`, missing authorization, permissive CORS, stack traces in responses, secrets or personal data in logs | TS-SEC |
| React | Effect dependencies, missing cleanup, state mutated in place, unstable keys, derived state copied into state | TS-REACT |
| Node runtime | Sync I/O or heavy CPU in request handlers, unbounded bodies, streams without error handlers, `process.exit` in library code | TS-NODE |
| Tests | New behavior without a test, tests that cannot fail, real network or time, snapshot-only tests for logic | TS-TEST |
| Style | Departures from the project's lint and naming conventions, dead code, debug leftovers (`console.log`, `debugger`) | TS-STYLE |

Each ID (`TS-SEC-1`, `TS-ASYNC-2`) is defined in `references/checklist.md` with its signals, what is not a finding, and the CWE for security items. React findings here stay light: deep component patterns belong to `react-patterns`.

## Confirm before reporting

- **Evidence:** a finding names what happens, where (`path:line`) and why it is wrong. For security, the source of the input, the sink and the missing control; "could be unsafe" without a path from input to sink is not a finding.
- **Framework protections count:** React escapes text by default, parameterized query builders (knex bindings, Prisma, Drizzle) bind values, Express 5 forwards rejected promises from async handlers to the error middleware. No finding unless the diff bypasses them (`dangerouslySetInnerHTML`, `knex.raw` with a template string, Express 4 async handlers without a wrapper).
- **Where the code runs matters:** a value in browser code is public; `process.env` in server code is not. Check the package before calling something a leak.
- **In scope:** what the diff adds or changes, and old code the diff now reaches. A problem that exists without the diff goes under Follow-ups, not in the table.
- **Unsettled:** when the control may live where you cannot see it (a gateway, a sanitizing backend), start the finding with `Unconfirmed:` and say what would settle it.

## Severity

The levels of `.exo/shared/judge-common.md`, section D, read for a TypeScript or JavaScript diff:

| Severity | Examples |
|---|---|
| Critical | Injection reachable from input (SQL, command, `eval`); XSS with content another user controls; prototype pollution from a request body; a real secret in the diff or in a client bundle; an entry point that changes data without authorization; data loss in the main flow |
| High | Wrong result in the main flow; an error swallowed on the main path, so a failure looks like success; a floating promise whose failure is lost; external data used as a typed value on a path that breaks or misbehaves when it is wrong; SSRF or path traversal behind sign-in; tokens in `localStorage`; new behavior with no test at all |
| Medium | An edge case or error path; a race between requests; an effect without cleanup; `any` on an exported API; a missing check of `response.ok`; a missing test for an edge case |
| Low | Style, naming, a clearer type, debug leftovers with no effect |

Never raise or lower a severity to reach a verdict; the person decides what to fix.

## Verdict

- `Verdict: approve` when no finding is Critical or High.
- `Verdict: request changes` when one is, or when part of the diff that matters could not be reviewed (minified or generated code, a file too large): say what under Not reviewed.

## Return

```markdown
# TypeScript review: staged diff (2 files)

Tools: npm run typecheck --workspace @shop/web: not run (no shell permission); checked imports and types by hand. eslint: not configured.

| # | Severity | path:line | Finding | Rule | Fix |
|---|---|---|---|---|---|
| 1 | Critical | packages/web/src/components/ReviewList.tsx:24 | Review text from other shoppers is rendered with `dangerouslySetInnerHTML`, so a review can run script in every visitor's session | TS-SEC-1 (CWE-79) | Render it as text; if rich text is required, sanitize it with the project's sanitizer before rendering |
| 2 | High | packages/web/src/components/ReviewList.tsx:12 | `res.json()` is stored as `any` and read as reviews without a check | TS-TYPE-4 | Type it `unknown` and parse it (a schema or a type guard) before use |
| 3 | Medium | packages/web/src/components/ReviewList.tsx:10 | The effect fetches without an abort, so a fast product change can show the previous product's reviews | TS-ASYNC-4 | Abort the request in the effect cleanup |

## Not reviewed

None.

## Follow-ups

- packages/api/src/routes/orders.js:14 (not in the diff): the admin token is compared with `===`; use `crypto.timingSafeEqual` on equal-length buffers.

Verdict: request changes
```

- Order the table by severity, Critical first. Number the rows; IDs are the checklist rule IDs, not finding numbers.
- `path:line` points at the line that shows the problem; a whole-file finding (no test) points at the file or folder.
- Keep fixes as text or a one-line snippet; never rewrite the code for the person.

## In an SDD change

- **Verify:** it runs where the verify runs (`sdd-verifier`, read-only, in fresh context, or the session that runs the verify). Each Critical and High finding goes to Issues Found of `verify-record.md`, which `sdd-verify` writes, with its severity, `path:line`, impact and fix. This skill writes no gate and no file.
- **Before the PR** (`branch-pr`): the same review on `git diff <target>...HEAD`; the person decides each finding.
- **Judges** (`judge-code-reviewer`, `judge-security`, `judge-frontend`) may reuse these rule IDs in their findings.

## Record

Inline, before the phase envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "typescript-reviewer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"typescript-reviewer"'
```

`activation` is `requested` when the person asked for the review and `auto` when the stack router or a phase loaded it. Findings the person decides not to fix go to `dismissed_followups` with their reason, recorded by the orchestrator; never dismiss one yourself. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every changed TypeScript and JavaScript file was read in full, and each new input was followed to its use.
- [ ] You knew which code runs in the browser and which on the server before judging a leak.
- [ ] Each finding has a severity, `path:line`, a rule ID (and a CWE for security) and a fix as text.
- [ ] Tools ran only if the project has them; the commands that could not run are named, with what you checked by hand.
- [ ] Nothing outside the diff is in the table; it is under Follow-ups.
- [ ] No secret or personal data is copied into the review, and no file was changed, staged or committed.
- [ ] The last line is `Verdict: approve` or `Verdict: request changes`.
