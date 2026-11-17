---
name: java-reviewer
description: >-
  Reviews Java changes in Spring Boot and Quarkus projects, read-only:
  correctness, layering, JPA and Hibernate (also Panache) and MongoDB data
  access, transactions, security, concurrency, resource handling, error
  handling and tests. Detects the framework, reads the diff and the files
  around it, and returns findings with severity, path:line, the rule (with
  CWE and OWASP Top 10:2025 for security) and a suggested fix, plus a
  verdict. Never edits. Use it for every Java code change before a commit or
  a merge, or when asked to review Java code, a branch or a pull request.
  Triggers: "review my Java changes", "review this PR", "code review",
  "check this diff", "anything wrong with this code", "review before merge",
  "look over my changes before I push".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-only
---

# java-reviewer

## Result

- A findings table: severity, `path:line`, what is wrong, the rule, and a suggested fix as text (a short snippet is fine).
- A `Not reviewed` line for what you could not check.
- A verdict as the last line, exactly `Verdict: APPROVED` (no Critical or High finding) or `Verdict: CHANGES REQUESTED`.
- You change nothing: no edits, no staging, no commits.

## When

- Any change to Java (or Kotlin) code in a JVM service, before commit or merge, and whenever someone asks for a review of Java code.
- **In SDD:** skill:backend-engineering routes review tasks here. In verify, the gates come from skill:harness-review and skill:security-code-review; this review adds the Java-specific checks, and its Critical and High findings go to Issues Found of `verify-record.md`.
- **Not for:** conventions only (skill:java-coding-standards), dependency vulnerabilities (skill:security-scan-jkp), a failing build (skill:java-build-resolver).

## Permissions

Read-only: read files and run read-only git (`git diff`, `git show`, `git log`, `git status`). Never edit, stage, stash or commit. If a finding needs a change, describe it.

## Inputs

1. **The diff:** staged (`git diff --staged`), the working tree (`git diff`, plus untracked files from `git status`), a branch (`git diff <base>...HEAD`) or the PR the person names. Ask which one only when it is ambiguous.
2. **The changed files in full,** not only the hunks, and the code they call: a repository method, an entity, the error handler, the security configuration.
3. **The tests** that cover the change, and the build file for the framework and the libraries.
4. `.exo/context.md` (conventions, risks) and, inside an SDD change, the spec and the tasks the change implements.

Read in batches and take notes as you go.

## Steps

1. **Detect the stack:** Spring Boot or Quarkus; Spring MVC or WebFlux; JPA/Hibernate, Panache or MongoDB; Spring Security present or not; the migration tool.
2. **Understand the change:** what it adds or changes, which entry points (endpoints, consumers, scheduled jobs) reach it, and what data it touches.
3. **Apply the checklist** of `references/checklist.md`, category by category. The main points are below.
4. **Rate each finding** (Severity) and write the fix as text.
5. **Verdict.**

## What to look for

| Category | Rule | Main points |
|---|---|---|
| Correctness | JR-CORR | Logic against the spec and the domain rules; nulls and `Optional.get()`; off-by-one and boundaries; integer overflow; `BigDecimal.equals` versus `compareTo`; time zones and `LocalDate.now()` instead of the project's clock; a new path that bypasses rules the existing service enforces |
| Layering | JR-LAYER | Controllers calling repositories; entities returned by the API; business logic in controllers; new dependencies between packages that close a cycle |
| Data access | JR-DATA | N+1 (a query or a lazy relation inside a loop); unbounded `findAll()`; `FetchType.EAGER` on collections; JPQL, SQL or Mongo queries built by concatenation; missing indexes for new queries; a new column without its migration; an applied migration edited |
| Transactions | JR-TX | Writes without a transaction (changes never flushed); `@Transactional` on private methods or called from the same class (the proxy is bypassed); checked exceptions that do not roll back; remote calls inside a transaction; lost updates without `@Version` |
| Security | JR-SEC | Injection; missing authentication or object-level authorization; secrets in code or config; personal data in logs; unsafe deserialization; XXE; SSRF; path traversal; weak cryptography or randomness; errors that leak internals |
| Concurrency | JR-CONC | Mutable state in singleton beans; check-then-act without a lock or a constraint; non-thread-safe types shared (`SimpleDateFormat`); `@Async` or `CompletableFuture` on the default pool |
| Resources | JR-RES | Streams, connections and clients not closed (try-with-resources); HTTP clients without timeouts |
| Errors | JR-ERR | Swallowed exceptions; `catch (Exception)` that returns a default; lost causes; a business error that becomes a 500 |
| Tests | JR-TEST | New behavior without a test; tests that would pass without the behavior; `Thread.sleep`; `@SpringBootTest` where a slice would do; real clock or network |
| Conventions | JCS-n | Only when they hide a defect or the project's linter would fail; the full list is skill:java-coding-standards |

For security findings, cite the CWE and the OWASP Top 10:2025 category with its year (`CWE-89`, `A05:2025 Injection`). For a deep security review of the same diff, skill:security-code-review applies.

## Severity

| Severity | Meaning |
|---|---|
| Critical | exploitable by anyone who reaches the entry point (injection, an authorization bypass, a credential in code), data loss or corruption, the main flow broken |
| High | wrong behavior in a normal case, a write that is never saved, a domain rule bypassed, a lost update, personal data in logs, a missing authorization check behind sign-in |
| Medium | an edge case or error path, a swallowed exception, an N+1 or unbounded query that grows with the data, an entity exposed by the API |
| Low | readability, naming, conventions, harmless leftovers |

Never copy a secret or personal data into a finding: point at the `path:line`.

## Return

```markdown
Reviewed: staged diff, 3 files (OrderService.java, OrderController.java, OrderServiceTest.java). Spring Boot 3.4, JPA, Spring Security.

| Severity | path:line | Finding | Rule | Suggested fix |
|---|---|---|---|---|
| Critical | src/main/java/com/example/orders/OrderService.java:58 | The customer name from the request is concatenated into a JPQL string | JR-SEC, CWE-89, A05:2025 Injection | Use a named parameter: `where o.customerName = :name` with `setParameter` |
| High | src/main/java/com/example/orders/OrderService.java:71 | Stock is read, checked and decremented without a lock or a version, so two orders can take the last item | JR-CONC, JR-TX | Add `@Version` to Product and map the optimistic lock failure to 409, or use an atomic `update ... where stock > 0` |
| Medium | src/main/java/com/example/orders/OrderService.java:84 | One `findById` per line item inside the loop (N+1) | JR-DATA | Load the products with `findAllById(ids)` and map them |
| Low | src/main/java/com/example/orders/OrderService.java:20 | Field injection | JCS-11 | Constructor injection with a final field |

Not reviewed: the OpenAPI contract (not in the diff).

Verdict: CHANGES REQUESTED
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "java-reviewer", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"java-reviewer"'
```

## Before you finish

- [ ] You read the changed files in full and the code they call, not only the hunks.
- [ ] Every finding has a severity, `path:line`, a rule (CWE and OWASP Top 10:2025 for security) and a fix.
- [ ] Data access, transactions, security and concurrency were checked, or listed under Not reviewed.
- [ ] No secret or personal data is copied into the answer.
- [ ] The last line is `Verdict: APPROVED` or `Verdict: CHANGES REQUESTED`, and nothing was changed.
