---
name: zod
description: >-
  Runtime validation with Zod 4 at the trust boundaries of a TypeScript app:
  request bodies, query and route params, forms, environment variables, JSON
  from storage and third-party responses. Parse once at the edge with parse or
  safeParse, infer the TypeScript types from the schema instead of writing
  them twice, add refinements and transforms, return field errors a person can
  act on, and share one schema between the browser and the server, which
  always validates again. Knows the Zod 3 to 4 changes. Use it when a project
  uses Zod, or adopts it, and you validate input, parse JSON, define the
  contract between client and server, or turn validation errors into
  messages. Triggers: "validate the request body", "validate this form",
  "parse this JSON safely", "schema for this payload", "infer the type from
  the schema", "safeParse", "share the validation between client and server",
  "validate env vars".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# zod

## Result

- Untrusted data is parsed once, where it enters (an HTTP handler, a form submit, a config loader, a client reading a response), by a schema that is the single source of its TypeScript type.
- Invalid data is rejected with field errors in the project's error format, never with a stack trace or the raw `ZodError`.
- A schema used by both sides lives in one shared module, and the server validates again whatever the browser already checked.
- The type check and the schema tests ran with the project's commands, or are listed as not run with what you checked by hand.

## When

- **Boundaries:** HTTP request bodies, query strings, route params and headers; form values; `process.env`; `JSON.parse` of files, `localStorage` and messages; responses from third-party APIs; webhook payloads.
- **Not for:** values passed between typed functions inside the app (the compiler already checks them: skill:typescript); business rules that need the database, such as stock or uniqueness (keep them in the service); styling or UI (skill:tailwind-4, `react-patterns`).
- **A project without Zod:** adding it is a dependency change. Propose it with the reason and wait for the person's approval; otherwise validate with type guards (skill:typescript, section 6).
- **Precedence:** `.exo/context.md`, the project's existing schemas and its error format win over the defaults here. `frontend-engineering`, the stack router of this pack, sends validation work here.

## 1. Know the project

1. **Version:** `zod` in the nearest `package.json`. `^4` (or imports from `zod/v4`) is Zod 4; `^3` is Zod 3. Write the API of the installed version; the differences are in `references/v3-to-v4.md`. `zod/mini` is the tree-shakable functional API: follow it if the project uses it.
2. **Where schemas live:** next to the handler, in a `schemas` module, or in a shared workspace package. Add to that place.
3. **Error format:** what the API returns on invalid input today (status code, body shape, for example `{ error, details }`), and how forms show field errors.
4. **Integrations already present:** a form library resolver (`@hookform/resolvers/zod`), a router or RPC layer that takes schemas (tRPC, Hono, Fastify type providers). Use them; do not add new ones without approval.

## 2. Parse at the edge, once

- Parse where the data enters and pass the typed result inward. Inner functions take `PlaceOrderInput`, not `unknown`, and never parse again.
- Define schemas at module level, not inside handlers or components, so they are built once.
- **The server always validates,** even when the browser used the same schema: the request can come from anywhere.
- Strip what you do not expect: `z.object` drops unknown keys by default; use `z.strictObject` when extra keys must be an error, never `z.looseObject` for input you then spread into a database row (mass assignment).

## 3. parse or safeParse

| Use | When |
|---|---|
| `schema.safeParse(data)` | Input from a person or a client: branch on `result.success` and return field errors |
| `schema.parse(data)` | Configuration at start-up (fail fast and loud), and internal invariants where invalid data is a bug |
| `parseAsync` or `safeParseAsync` | The schema has async refinements or transforms |

Never wrap `parse` in `try` and swallow the error; when you need the branch, use `safeParse`.

## 4. Schemas

Write schemas with Zod 4 idioms (`references/recipes.md` has full examples):

```ts
import { z } from 'zod';

export const OrderLineSchema = z.object({
  productId: z.string().min(1).brand<'ProductId'>(),
  quantity: z.int().min(1).max(10),
});

export const PlaceOrderSchema = z.object({
  email: z.string().trim().toLowerCase().pipe(z.email({ error: 'Enter a valid email address' })),
  promoCode: z.string().trim().toUpperCase().optional(),
  lines: z.array(OrderLineSchema).min(1).max(25),
});

export type PlaceOrderInput = z.infer<typeof PlaceOrderSchema>;
```

- String formats are top-level in Zod 4: `z.email()`, `z.url()`, `z.uuid()`, `z.iso.datetime()`, `z.iso.date()`.
- Numbers: `z.int()` for integers, `.min` and `.max` from the domain's limits (import the constants the code already has instead of repeating numbers).
- Closed sets: `z.enum(['pending', 'paid'])`, or `z.enum` over an existing `as const` array so the list stays in one place.
- Shapes that vary by a tag: `z.discriminatedUnion('kind', [...])`.
- `.optional()` (may be missing), `.nullable()` (may be `null`), `.default(value)` (missing becomes the value, which must match the output type).
- `.brand<'ProductId'>()` when the inferred type must not mix with other strings.

## 5. Infer the types

- `z.infer<typeof Schema>` (the same as `z.output`) is the type after parsing; `z.input<typeof Schema>` is what goes in, which differs when there are transforms, defaults or coercion. Type form state with `z.input` and handler arguments with `z.infer`.
- Do not keep a hand-written interface next to the schema: export the inferred type and delete the duplicate.

## 6. Refinements

- `.refine(check, { error: '...', path: ['field'] })` for one rule; the `path` puts the error on the field the person must fix.
- For a rule across fields (an end date after a start date, no repeated product in the lines), refine the object and set the `path` to the field that is wrong.
- For several issues from one check, `.superRefine((value, ctx) => { ctx.addIssue({ code: 'custom', message: '...', path: [...] }) })`; Zod 4 also offers `.check()` for this.
- Keep refinements pure and fast; anything that needs I/O (a database lookup) belongs in the service, after parsing.

## 7. Transforms and coercion

- Normalizing methods (`.trim()`, `.toLowerCase()`, `.toUpperCase()`) keep the type. Normalize before a format check, with `.pipe`, as the email in section 4 does: checks run in the order they are written.
- `.transform(fn)` changes the output type; chain more validation after it with `.pipe(schema)`: `z.string().transform((s) => s.replace(/\s|-/g, '')).pipe(z.string().regex(/^\d{13,19}$/))`.
- `z.coerce.number()`, `z.coerce.date()` for query strings and form fields, which arrive as strings; `z.stringbool()` for boolean environment variables (`"true"`, `"1"`, `"yes"`).
- Zod 4.1 codecs (`z.codec`) when a value must be decoded on input and encoded back on output (an ISO string and a `Date`).

## 8. Errors for people

- **Forms:** `z.flattenError(result.error).fieldErrors` gives `{ field: [messages] }`; show the first message next to each field and focus the first invalid field (skill:accessibility-audit covers how errors are announced).
- **APIs:** return the project's error status and shape, with field errors in it. In Zod 3, the same comes from `error.flatten()`.

  ```ts
  const result = PlaceOrderSchema.safeParse(req.body);
  if (!result.success) {
    throw new HttpError(422, 'Invalid order', z.flattenError(result.error).fieldErrors);
  }
  const order = await orders.placeOrder(result.data);
  ```

- **Messages:** write them for the person (`'Enter a valid email address'`), with the `error` option in Zod 4 (`message` in Zod 3). Never echo the received value back when it may be personal data.
- **Logs and CLIs:** `z.prettifyError(error)` gives readable text. Never send the full `ZodError` or its internal paths to a browser in production.

## 9. One schema, two sides

- Put the schema and its inferred type in the module both sides import (a shared workspace package, a `shared/` folder). The browser uses it for instant feedback; the server parses with the same schema before any other work.
- Rules only the server can check (stock, ownership, uniqueness, prices from the catalog) stay on the server, after parsing, and their errors use the same field error shape.
- A shared schema is a contract: changing it changes both sides in the same change. Removing or tightening a field breaks old clients; say so in the design.
- A shared package that runs on Node from source keeps erasable syntax and explicit `.ts` imports (skill:typescript, section 1).

## 10. Environment and configuration

Parse `process.env` once at start-up, in the config module, with `parse`, so a missing variable stops the process with a clear message. Never print the values of secret variables in the error: name the variable.

## 11. Tests

For each schema: one valid example, and for each refinement and each limit one invalid example that asserts the error's path and message. Test a handler's 422 response once with the real schema. Use the project's test runner and naming.

## 12. Check

Run the type check and the tests of `.exo/context.md` or `package.json` scripts and report each exact command with its result. When you cannot run them, give the exact commands and check by hand: imports resolve, `z.infer` replaced every duplicate interface, each boundary parses before use, and every error path returns the project's format. Never install Zod or a resolver without the person's approval.

## Return

```text
Zod 4.1 (packages/shared/package.json); schemas in packages/shared/src/schemas.ts.
Changed: PlaceOrderSchema (duplicate lines refinement, email normalized), packages/api/src/routes/orders.js (safeParse, 422 with fieldErrors).
Checks: npm test --workspace @shop/api: not run (no shell); checked imports and the 422 shape by hand.
```

## Record

Inside an SDD change, the phase that loaded this skill records it; inline, before the phase envelope (`.exo/shared/capability-attribution.md`). A subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "zod", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"zod"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You wrote the API of the installed Zod version, in the place the project keeps its schemas.
- [ ] Every boundary you touched parses once, before use; nothing inside parses again.
- [ ] Types come from `z.infer` or `z.input`; no duplicate interface is left.
- [ ] Invalid input returns field errors in the project's format, with messages for people and no internal details.
- [ ] The server validates everything the browser validates, plus its own rules.
- [ ] No dependency was added without approval.
- [ ] Each refinement and limit has a test, and the checks ran or are listed as not run.
