---
name: backend-and-api
description: >-
  Designs and reviews REST APIs and the backend behind them, in any language:
  resources and URIs, HTTP methods with their safety and idempotency, status
  codes, request validation, errors as RFC 9457 problem details, pagination,
  filtering and sorting, versioning and breaking changes, idempotency keys,
  concurrency with ETags, caching and rate limits, and the OpenAPI contract
  kept in sync with the code. Follows the conventions the API already has.
  Use it when adding or changing an endpoint, designing an API contract,
  choosing status codes or an error format, or reviewing an API for
  consistency. Triggers: "design the endpoint", "which status code", "REST
  API design", "error response format", "paginate this endpoint", "version
  the API", "update the OpenAPI spec", "is this endpoint RESTful", "propose
  the endpoints".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-write
---

# backend-and-api

## Result

- **Designing:** for each endpoint, the method and path, the request and response bodies, the status codes and error codes, pagination, idempotency and authorization, consistent with the API that exists, plus the OpenAPI contract updated in the same change.
- **Reviewing:** findings with severity, `path:line`, the rule they break and a suggested fix, in the format of Return.
- The details (status codes, headers, problem details, pagination shapes, breaking changes) are in `references/http-reference.md`; the review checklist is in `references/review-checklist.md`.

## When

- An endpoint is added or changed, an API contract is designed, a status code or error format must be chosen, or someone asks whether an API is well designed.
- **In SDD:** skill:backend-engineering loads it in design (the endpoints go to design.md, Data Shapes and Error Handling) and in apply (the code and the contract).
- **Not for:** how Spring wires controllers and validation (skill:springboot-patterns), securing endpoints (skill:springboot-security), or a full review of a Java diff (skill:java-reviewer).

## 1. Read what exists

1. **The contract:** an OpenAPI file (`openapi.yaml`, `openapi.json`, often under `src/main/resources/static/` or `api/`), or the annotations that generate it (springdoc `@Operation`, `@Schema`). Note whether the project is contract-first (the file generates code) or code-first.
2. **The controllers and the error handler** (`@RestControllerAdvice`, exception mappers): paths, naming, the error body, the status codes in use.
3. **`.exo/context.md`:** API conventions, consumers, versioning policy.

**Consistency beats preference.** If the API already has its own error body or its own convention for business errors (422 or 409), use it for the new endpoint, and propose any migration as a separate follow-up.

## 2. Resources and URIs

- Plural nouns, lowercase, kebab-case: `/members`, `/loan-requests`. No verbs in paths.
- Identify with path parameters: `/members/{memberId}`. Treat IDs as opaque strings for clients.
- Nest one level for ownership: `/members/{memberId}/loans`. Deeper nesting becomes a query filter.
- An action that is not create, read, update or delete becomes a subresource you create: `POST /loans/{id}/renewal`, `POST /orders/{id}/cancellation`.
- Filters, sorting and pagination go in the query string, never in the body of a GET.

## 3. Methods

| Method | Safe | Idempotent | Use |
|---|---|---|---|
| GET | yes | yes | read a resource or a collection |
| POST | no | no | create in a collection, or run an action subresource |
| PUT | no | yes | replace the whole resource at a known URI |
| PATCH | no | not by default | partial update (JSON Merge Patch, RFC 7396, or JSON Patch, RFC 6902) |
| DELETE | no | yes | remove; repeating it does not fail with 500 |

## 4. Status codes

Use the smallest set that tells clients what to do; the full table is in `references/http-reference.md`.

- **Success:** 200 with a body; 201 with a `Location` header and the created resource; 202 when the work continues asynchronously (with a link to follow it); 204 without a body.
- **Client errors:** 400 malformed or invalid input; 401 not authenticated; 403 authenticated but not allowed; 404 not found, or not visible to this caller; 409 conflict with the current state (a duplicate, a lost race); 412 an `If-Match` precondition failed; 415 wrong media type; 422 a valid request that breaks a business rule, when the API uses it; 429 too many requests, with `Retry-After`.
- **Server errors:** 500 for unexpected failures, 503 when a dependency is down, with a generic body.
- Never 200 with an error inside the body, and never 500 for a client mistake.

## 5. Requests and validation

- Validate at the edge: types, required fields, lengths, ranges, formats and enums, with the framework's validation (Bean Validation in Java). Reject what fails with 400 and the list of invalid fields.
- Business rules stay in the domain and return the business error (409 or 422).
- Set limits: body size, collection sizes, string lengths, page size.
- Request and response bodies are DTOs, never persistence entities: an entity in the body leaks internal fields, invites mass assignment and breaks when the schema changes.

## 6. Errors

Return RFC 9457 problem details (`application/problem+json`) unless the API already has another format:

```json
{
  "type": "https://example.com/problems/loan-limit-reached",
  "title": "Loan limit reached",
  "status": 422,
  "detail": "Student members can have 3 active loans.",
  "instance": "/loans",
  "code": "loan_limit_reached",
  "errors": [{"field": "bookId", "message": "must not be null"}]
}
```

- A stable machine-readable `code` (or `type`) that clients can branch on; a human `detail` without internals.
- Never stack traces, SQL, class names, file paths or versions in the body. Log them on the server, without personal data.
- Document every error response of every operation in the contract.

## 7. Collections

- **Always paginate** a collection that can grow. A default page size and a maximum (for example 20 and 100); clamp or reject larger values, and say which.
- **Offset pagination** (`page`, `size`) for small, stable sets. **Cursor (keyset) pagination** for large or fast-changing data: an opaque `cursor` built from the sort key and the ID.
- **Stable order:** sort by the requested field plus the ID as a tie-breaker, or pages repeat and skip items.
- **Filtering and sorting:** query parameters with an allow list of fields (`?status=active&sort=-dueOn`); an unknown field is a 400.
- Return the page metadata (`page`, `size`, `totalElements` or `nextCursor`) or `Link` headers, consistently across the API.

## 8. Idempotency and concurrency

- A POST that charges, books or sends something accepts an `Idempotency-Key` header; the same key and body return the first response, a different body with the same key is rejected, a request still in flight with the same key gets 409. A natural key with a unique constraint is enough for simpler cases.
- **Lost updates:** return an `ETag` (or a `version` field) and require `If-Match` on PUT, PATCH and DELETE of contended resources; a mismatch is 412, a missing header 428 when the API requires it.

## 9. Versioning and compatibility

- Prefer additive changes: a new optional field, a new endpoint, a new enum value that clients were told to tolerate.
- **Breaking changes** (the list is in `references/http-reference.md`) need a new version, chosen by the project's convention: the path (`/v2/...`), a media type, or a header. Keep the old version during a deprecation period and announce it with the `Deprecation` and `Sunset` headers and a link to the migration notes.
- Never change the meaning of an existing field or status code in place.

## 10. Caching, limits and security

- `Cache-Control` on cacheable GETs, `ETag` with `If-None-Match` for 304s; `no-store` on responses with personal or sensitive data.
- Rate limits on expensive or abuse-prone endpoints (sign-in, search, exports), with 429 and `Retry-After`.
- Every endpoint is authenticated unless the design says it is public; authorization is checked per object, on the server (OWASP API Security Top 10, API1:2023 Broken Object Level Authorization). Never trust an owner ID sent by the client. The implementation is in skill:springboot-security.
- No secrets, tokens or personal data in URLs: they end up in logs and browser history.

## 11. The contract

- Update the OpenAPI file in the same change as the code: paths, parameters, request and response schemas, every status code, examples with synthetic data.
- **Contract-first:** change the file first, then the code that implements it. **Code-first:** change the annotations and check the generated contract.
- When you cannot run the project's contract linter or generator, edit the file by hand, say which command checks it (from `.exo/context.md` or the build), and mark it not run.

## Return

**A design**, one block per endpoint, then the contract change:

```markdown
| Endpoint | Request | Success | Errors |
|---|---|---|---|
| POST /orders/{id}/cancellation | empty; header Idempotency-Key | 200 Order (cancelled) | 404 not_found · 409 order_not_cancellable (already shipped) · 403 not the owner |
| GET /orders?status=&sort=&page=&size= | query only; size max 100 | 200 page of OrderSummary, sorted by createdAt desc then id | 400 invalid_filter |

Contract: openapi.yaml gains the cancellation path and the order_not_cancellable error example.
```

**A review:**

```markdown
| Severity | path:line | Finding | Rule | Fix |
|---|---|---|---|---|
| Medium | src/main/java/com/example/orders/OrderController.java:42 | Returns the JPA entity Order, exposing internal fields | DTOs, not entities (section 5) | Return an OrderResponse record |
| Low | api/openapi.yaml:88 | POST /orders documents 201 but not its 409 | Document every error (section 6) | Add the 409 response with its code |
```

Severities: **Critical** (data exposed or corrupted, an authorization hole), **High** (a broken contract for existing clients, a missing check that the spec requires), **Medium** (an inconsistency clients will trip on, an undocumented error), **Low** (naming, documentation).

## Record

Inside an SDD change, record the skill when it ran inline (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "backend-and-api", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"backend-and-api"'
```

## Before you finish

- [ ] The new endpoints follow the conventions of the existing API (paths, error body, business error status).
- [ ] Every endpoint has its method, success status, error statuses with codes, and authorization stated.
- [ ] Collections are paginated with a default, a maximum and a stable order.
- [ ] Side-effecting POSTs are idempotent or say why not; contended updates handle lost updates.
- [ ] No entity in a request or response body; no secrets or personal data in URLs.
- [ ] The OpenAPI contract changed with the code, or the answer says what it needs.
