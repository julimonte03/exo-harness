# Zod 3 and Zod 4

Write the API of the version the project has installed. Migrating a project from 3 to 4 is its own change: it touches every schema and needs the person's approval.

## Imports

| Package version | Import | API |
|---|---|---|
| `zod@^3` | `import { z } from 'zod'` | Zod 3 |
| `zod@3.25.x` | `import { z } from 'zod/v4'` | Zod 4, shipped inside 3.25 for incremental migration |
| `zod@^4` | `import { z } from 'zod'` | Zod 4 (`zod/v3` keeps the old API available) |
| `zod@^4` | `import * as z from 'zod/mini'` | Zod 4 Mini: functions instead of methods (`z.optional(z.string())`), smaller bundles |

Zod 4 needs TypeScript 5.5 or later with `strict` on.

## What changed

| Zod 3 | Zod 4 | Note |
|---|---|---|
| `z.string().email()`, `.url()`, `.uuid()`, `.datetime()` | `z.email()`, `z.url()`, `z.uuid()`, `z.iso.datetime()` | The methods still work but are deprecated |
| `{ message: '...' }`, `invalid_type_error`, `required_error`, `errorMap` | `{ error: '...' }` or `{ error: (issue) => '...' }` | One option for every error customization; `message` still works, deprecated |
| `.strict()`, `.passthrough()` | `z.strictObject({...})`, `z.looseObject({...})` | The methods still work, deprecated |
| `A.merge(B)` | `A.extend(B.shape)` or `z.object({ ...A.shape, ...B.shape })` | `.merge` deprecated |
| `error.format()`, `error.flatten()` | `z.treeifyError(error)`, `z.flattenError(error)` | Top-level functions; `z.prettifyError(error)` gives readable text |
| `error.errors` | `error.issues` | Read `issues` |
| `.default(value)` parses the default | `.default(value)` returns it as is when the input is `undefined`; `.prefault(value)` parses it | The default must match the output type |
| `z.nativeEnum(MyEnum)` | `z.enum(MyEnum)` | `z.enum` accepts enum-like objects |
| `z.record(valueSchema)` | `z.record(keySchema, valueSchema)` | One-argument form removed |
| `z.number()` accepts `Infinity` | Rejects infinite values; `z.int()` for safe integers | — |
| `z.coerce.number()` input type `number` | Input type `unknown` | Matters for `z.input` |
| Refinements wrap the schema (`ZodEffects`), so `.min()` cannot follow `.refine()` | Refinements live inside the schema; you can keep chaining | — |
| `ctx.path` inside `superRefine` | Removed | Pass `path` to `ctx.addIssue` |
| `z.function()` is a schema | A function factory, not a schema | Rarely used in validation code |
| — | `z.stringbool()`, `z.templateLiteral()`, `z.file()`, `z.toJSONSchema()`, `.meta()` and registries | New in 4 |
| — | `z.codec()` for two-way decode and encode | New in 4.1 |

## Migration steps, when the person approves one

1. Upgrade the package; keep importing `zod/v3` in files not migrated yet, or migrate from `zod/v4` in 3.25 file by file.
2. Replace deprecated string methods with top-level formats, `message` with `error`, `.strict()` and `.passthrough()` with the object constructors.
3. Replace `.flatten()` and `.format()` with the top-level functions, and `error.errors` with `error.issues`.
4. Check every `.default()`: if the default must go through the schema (a transform), use `.prefault()`.
5. Check every one-argument `z.record` and every `z.nativeEnum`.
6. Run the type check and the tests; inferred types change where defaults and coercion changed.
