# HTTP reference for API design

## Status codes

| Code | Name | Use it when | Notes |
|---|---|---|---|
| 200 | OK | a read, or an update or action that returns the resource | |
| 201 | Created | a POST created a resource | `Location: /resources/{id}` and the resource in the body |
| 202 | Accepted | the work continues asynchronously | a link to a status resource the client can poll |
| 204 | No Content | success without a body (a DELETE, an update that returns nothing) | never with a body |
| 304 | Not Modified | `If-None-Match` matched the current `ETag` | no body |
| 400 | Bad Request | malformed JSON, wrong types, failed validation | list the invalid fields |
| 401 | Unauthorized | no credentials, or invalid or expired ones | `WWW-Authenticate` header |
| 403 | Forbidden | authenticated, but not allowed to do this | use 404 instead when revealing that the resource exists is a leak |
| 404 | Not Found | no such resource, or the caller may not know it exists | |
| 405 | Method Not Allowed | the path exists, the method does not | `Allow` header |
| 406 | Not Acceptable | the `Accept` header asks for a format the API cannot produce | |
| 409 | Conflict | the request conflicts with the current state: a duplicate, an invalid state transition, a lost race | |
| 412 | Precondition Failed | `If-Match` did not match the current `ETag` | the client reloads and retries |
| 413 | Content Too Large | the body is over the limit | |
| 415 | Unsupported Media Type | the `Content-Type` is not accepted | |
| 422 | Unprocessable Content | well-formed and valid, but a business rule rejects it | some APIs use 409 or 400 here: keep the project's choice |
| 428 | Precondition Required | the API requires `If-Match` and it is missing | |
| 429 | Too Many Requests | rate limit reached | `Retry-After` header |
| 500 | Internal Server Error | an unexpected failure | generic body; details only in the server log |
| 502 / 504 | Bad Gateway / Gateway Timeout | an upstream dependency failed or timed out | |
| 503 | Service Unavailable | overloaded or in maintenance | `Retry-After` when known |

### 400 or 422 for validation

Both are defensible; the API must pick one and keep it. A common split: 400 for input that fails syntax or field validation (missing, wrong type, too long), 422 (or 409) for input that is valid but breaks a rule that depends on the state (the member has reached their loan limit).

## Problem details (RFC 9457)

Media type `application/problem+json`. Members:

| Member | Meaning |
|---|---|
| `type` | a URI that identifies the problem type; `about:blank` when there is none |
| `title` | a short summary of the type, the same for every occurrence |
| `status` | the HTTP status code |
| `detail` | this occurrence, for humans; no internals |
| `instance` | a URI for this occurrence (the request path, or an error ID) |
| extensions | anything else: `code`, `errors` (field errors), `traceId` |

Spring Framework 6 has `ProblemDetail` and `ErrorResponseException`; `spring.mvc.problemdetails.enabled=true` makes Spring's own exceptions use it.

## Useful headers

| Header | Direction | Use |
|---|---|---|
| `Location` | response | the URI of a created resource (201) or of a status resource (202) |
| `ETag` / `If-Match` / `If-None-Match` | both | optimistic concurrency (412) and conditional GETs (304) |
| `Idempotency-Key` | request | safe retries of a POST with side effects |
| `Retry-After` | response | with 429 and 503 |
| `Cache-Control` | response | `no-store` for personal data; `max-age` for cacheable reads |
| `Deprecation` / `Sunset` | response | an endpoint or version that will go away, and when |
| `Link` | response | pagination (`rel="next"`) or the migration notes of a deprecated version |

## Pagination shapes

Offset:

```json
{
  "items": [{"id": "41", "title": "Signals"}],
  "page": 0,
  "size": 20,
  "totalElements": 135,
  "totalPages": 7
}
```

Cursor:

```json
{
  "items": [{"id": "41", "title": "Signals"}],
  "nextCursor": "eyJ0aXRsZSI6IlNpZ25hbHMiLCJpZCI6NDF9",
  "size": 20
}
```

- A count (`totalElements`) costs a second query; drop it for large tables (Spring Data `Slice` instead of `Page`).
- The cursor encodes the last sort key and ID; the next query is `where (sort_key, id) > (:lastKey, :lastId) order by sort_key, id limit :size`.

## Breaking changes

Any of these breaks existing clients and needs a new version or a deprecation period:

- removing or renaming a field, an endpoint, a query parameter or an enum value;
- changing a field's type, format or meaning (cents to units, a number to a string);
- making an optional request field required, or adding a required request field;
- tightening validation on existing input;
- changing a success or error status code, or an error code clients branch on;
- changing the default sort, the default page size or the pagination style;
- changing authentication or the permissions an existing call needs.

Usually safe: a new endpoint, a new optional request field, a new response field, a new error code on a new path, a looser limit.

## Rate limits

- Per client (API key, user or IP when anonymous), on the endpoints that are expensive or abused: sign-in, password reset, search, exports, anything that sends messages.
- Return 429 with `Retry-After`; optionally `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`.
- Enforce it at the gateway when there is one; otherwise in the service (a token bucket such as Bucket4j).
