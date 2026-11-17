# API review checklist

Go through the endpoints the change adds or touches, then their entries in the contract. Each item names the section of `SKILL.md` it comes from. Report only what applies, with `path:line`.

## Resources and methods (sections 2 and 3)

- [ ] Paths are plural nouns in kebab-case, without verbs; actions are subresources (`POST /loans/{id}/renewal`).
- [ ] The method matches the semantics: GET has no side effects; PUT and DELETE are idempotent; POST is used for creation and actions.
- [ ] Nesting stays at one level of ownership.

## Status codes (section 4)

- [ ] 201 comes with `Location`; 204 has no body.
- [ ] Each error has the right family: client mistakes are 4xx, unexpected failures 5xx.
- [ ] The business-error status (409 or 422) matches the rest of the API.
- [ ] No 200 with an error in the body; no 500 for invalid input.

## Requests and responses (sections 5 and 6)

- [ ] Request bodies are validated at the edge, with the list of invalid fields in the 400.
- [ ] Bodies are DTOs, not entities: no internal fields, no lazy relations, no mass assignment.
- [ ] Error bodies follow the API's format (problem details by default) with a stable code.
- [ ] No stack traces, SQL, class names or file paths in any response.

## Collections (section 7)

- [ ] Every growing collection is paginated, with a default and a maximum size.
- [ ] The order is stable (a tie-breaker on the ID).
- [ ] Sort and filter fields are allow-listed; an unknown one is a 400.

## Idempotency and concurrency (section 8)

- [ ] A POST with side effects is idempotent (a key, or a unique natural key) or the design says why it does not need to be.
- [ ] Contended updates use `If-Match`/`ETag` or a version field.

## Compatibility (section 9)

- [ ] No breaking change to an existing endpoint without a new version or a deprecation period (`references/http-reference.md`, Breaking changes).
- [ ] Deprecated endpoints send `Deprecation` and `Sunset`.

## Security (section 10)

- [ ] Every endpoint is authenticated, or explicitly public by decision.
- [ ] Authorization is checked per object on the server; client-sent owner IDs are not trusted.
- [ ] No secrets, tokens or personal data in paths or query strings.
- [ ] Abuse-prone endpoints have a rate limit.
- [ ] Responses with personal data are `Cache-Control: no-store`.

## Contract (section 11)

- [ ] The OpenAPI file changed with the code: every path, parameter, schema and status code, including errors.
- [ ] The contract and the code agree: the same paths, the same status codes, the same field names and types.
- [ ] Examples use synthetic data only.
