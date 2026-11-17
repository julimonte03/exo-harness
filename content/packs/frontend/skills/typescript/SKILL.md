---
name: typescript
description: >-
  Modern TypeScript 5.x for application code: strict compiler settings, types
  that make invalid states unrepresentable (discriminated unions with
  exhaustive checks, branded types, literal unions instead of enums),
  satisfies and as const for checked literals, type-only imports, narrowing
  instead of casting, unknown instead of any at the edges, generics only where
  they link inputs and outputs, and the built-in utility types. The project's
  tsconfig, TypeScript version and conventions come first. Use it when you
  write or change TypeScript, fix type errors, design the types of a new
  module or contract between modules, or tighten a tsconfig. Not for
  reviewing a diff (typescript-reviewer) or runtime validation schemas (zod).
  Triggers: "fix this type error", "type this properly", "design the types
  for", "discriminated union", "branded type", "use satisfies", "make the
  tsconfig strict", "get rid of any", "TypeScript generics".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: read-write
---

# typescript

## Result

- TypeScript that compiles under the project's tsconfig with no new errors, no new `any`, no unchecked casts, and types that reject the invalid states the domain forbids.
- The type check ran with the project's command, named with its result; or the exact command and what you checked by hand when you could not run it.
- In a design: the types of the new module or contract (unions, branded IDs, function signatures), ready for `sdd-design` to put in design.md, Data Shapes.

## When

- You write or change `.ts`, `.tsx`, `.mts` or `.cts` files, or fix a type error.
- You design the types of a module, a component's props, or a contract shared by a client and a server.
- Someone asks to tighten the compiler settings or remove `any`.
- **Not for:** reviewing someone else's diff (skill:typescript-reviewer); runtime validation of untrusted data (skill:zod, when the project uses Zod); React specifics such as hooks and component patterns (`react-patterns`); styling (skill:tailwind-4).
- **Precedence:** `.exo/context.md` (Commands, Conventions), the tsconfig and the neighboring code win over the defaults here. `frontend-engineering`, the stack router of this pack, sends TypeScript work here.

## 1. Know the project

Before writing types, read:

1. The `tsconfig.json` that covers the file (follow `extends` and project `references`): `strict` and the other checks, `target`, `module`, `moduleResolution`, `paths`, `verbatimModuleSyntax`, `isolatedModules`, `allowImportingTsExtensions`, `erasableSyntaxOnly`.
2. The TypeScript version in the nearest `package.json`. Use only what it has (`references/tsconfig.md`, Versions).
3. **How the code runs:** through a bundler (Vite, webpack, Next.js), through `tsc` output, or straight from source with Node's type stripping (Node 22.18+ and 24). Type stripping accepts only erasable syntax: no `enum`, no `namespace` with values, no constructor parameter properties, `import type` for type-only imports, and explicit `.ts` extensions in relative imports.
4. The lint rules (`typescript-eslint` config) and two or three neighbors of the file you touch: `type` or `interface`, naming, where shared types live.

## 2. Compiler settings

- Keep `strict: true`. It includes `noImplicitAny`, `strictNullChecks`, `useUnknownInCatchVariables` and the other strict checks.
- Recommended on top, for new projects or when the person asks to tighten: `noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax` (or `isolatedModules`), `erasableSyntaxOnly` under type stripping. The full table is in `references/tsconfig.md`.
- **Never loosen a flag** to make an error go away, and never flip flags in passing: tightening a tsconfig is its own change, because it surfaces errors across the code base.

## 3. Model the domain with types

Examples of each pattern are in `references/type-patterns.md`.

- **Discriminated unions** for values that are one of several shapes: one literal tag (`status`, `kind`, `type`) and only the fields each case has. No bag of optional fields where some combinations are invalid.

  ```ts
  type Payment =
    | { status: 'pending' }
    | { status: 'paid'; paidAt: string; receiptId: string }
    | { status: 'failed'; reason: string };
  ```

- **Exhaustive handling:** `switch` on the tag with a `never` check in `default`, so a new case breaks the build where it is not handled.
- **Literal unions** (`'in-stock' | 'low-stock' | 'out-of-stock'`) or an `as const` object with a derived union, instead of `enum`.
- **Branded types** for values that must not be mixed up (`ProductId` and `OrderId`, cents and units): `type ProductId = string & { readonly __brand: 'ProductId' }`, created only by a function that validates.
- **`readonly`** properties and `readonly T[]` for data a function must not change.
- **Derive instead of repeating:** `Pick`, `Omit`, indexed access (`Order['status']`) and `typeof` keep related types in sync.

## 4. Checked literals

- `satisfies` checks a value against a type and keeps its literal types: `const BADGES = { ... } satisfies Record<StockLevel, Badge>` fails when a level is missing and still knows each key.
- `as const` for literal tuples and objects that never change.
- Const type parameters (`function pick<const T extends readonly string[]>(keys: T)`) when a function must keep the literal types of its argument.
- An annotation (`const x: Foo = ...`) when you want the wider type on purpose.

## 5. Narrowing over casting

- Narrow with `typeof`, `in`, `instanceof`, equality on the tag, and type guard functions (`(x: unknown): x is Product`). TypeScript 5.5 infers simple predicates from `filter` callbacks.
- Assertion functions (`asserts value is Product`) for checks that throw.
- `as` only right after a check that proves it, at a boundary, with a comment. Never `as unknown as T`, never `as any`.
- The non-null assertion `!` only where the code guarantees the value and a comment says how (`document.getElementById('root')!` in the entry point is the usual case).
- `// @ts-expect-error <reason>` instead of `// @ts-ignore`, and only for a known compiler or library limitation.

## 6. The edges: unknown, never any

Data from outside the type system arrives as `unknown`: `JSON.parse`, `response.json()`, `localStorage`, `postMessage`, `process.env`, URL and form values, `catch` variables, third-party callbacks.

- Parse it before use: with skill:zod when the project uses Zod; otherwise with a type guard that checks every field you read.
- `response.json() as Promise<T>` and `JSON.parse(text) as T` are casts, not checks: acceptable only for your own backend with a shared, versioned contract, and say so in a comment.
- Replace an existing `any` with `unknown` plus narrowing, or with the real type; never with another `any`.

## 7. Generics with criteria

- A type parameter must link two places: an input and an output (`first<T>(items: readonly T[]): T | undefined`), or two inputs. Used once, it is just `unknown`.
- Constrain it (`T extends { id: string }`), give it a default when callers rarely set it, and prefer inference over explicit type arguments at call sites.
- `NoInfer<T>` (5.4) when one argument must not drive the inference.
- Conditional and mapped types belong in a few shared utility types, documented, not in application code.

## 8. Utility types

| Need | Use |
|---|---|
| Some fields optional, required or read-only | `Partial`, `Required`, `Readonly` |
| A subset of fields, or all but some | `Pick<T, K>`, `Omit<T, K>` |
| A map from a closed set of keys | `Record<K, V>` with `K` a literal union |
| The members of a union that match, or the rest | `Extract<U, M>`, `Exclude<U, M>` |
| A value without `null` or `undefined` | `NonNullable<T>` |
| A function's parameters, its return, an awaited value | `Parameters<F>`, `ReturnType<F>`, `Awaited<T>` |

Avoid `Function`, `Object`, `{}` and `object` as parameter types: name the shape.

## 9. Modules and imports

- `import type` and `export type` for type-only imports (required by `verbatimModuleSyntax` and by type stripping).
- Follow the project's path aliases (`@/components`) and its index files; do not add a new barrel file that re-exports a whole folder without need: it slows the build and the tests and hides cycles.
- Export the types a module's callers need; keep the rest local.

## 10. Errors

- `catch (error)` gives `unknown`: narrow with `error instanceof Error` before reading `message`; never `(error as Error).message` on values that may not be errors.
- Expected failures that the caller must handle (validation, not found, conflict) can be a result union (`{ ok: true; value: T } | { ok: false; error: E }`); unexpected ones are thrown `Error` subclasses with `cause`.
- Follow the error style the project already uses.

## 11. Check

Run the project's type check from `.exo/context.md` or `package.json` scripts (`tsc --noEmit`, `tsc -b`, `npm run typecheck`, the build), then its lint and tests. Report each exact command with its result.

- **Never install** a package or change the tsconfig to make the check pass.
- **When you cannot run it** (no shell permission, no `node_modules`): say so, give the exact command, and check by hand: every import resolves (aliases, extensions), each new union is handled exhaustively, no `any`, unchecked cast or `!` slipped in, and callers of every changed signature still match.

## Return

```text
TypeScript 5.6, strict, verbatimModuleSyntax, Node type stripping in packages/shared (from tsconfig.json and package.json).
Changed: packages/shared/src/types.ts (Payment union, ProductId brand), packages/web/src/api/client.ts.
Checks: npm run typecheck --workspace @shop/shared: not run (no shell); checked imports, exhaustive switches and callers by hand.
```

## Record

Inside an SDD change, the phase that loaded this skill records it; inline, before the phase envelope (`.exo/shared/capability-attribution.md`). A subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "typescript", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"typescript"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You read the tsconfig, the TypeScript version, how the code runs and the neighboring code before writing.
- [ ] No new `any`, `as unknown as`, `@ts-ignore` or unexplained `!`; data from outside is parsed, not cast.
- [ ] Unions have a tag and an exhaustive check; IDs that must not mix are branded where the project does so.
- [ ] Only syntax the project's TypeScript version and runtime accept (erasable syntax under type stripping).
- [ ] No compiler flag was loosened.
- [ ] The type check ran with its exact command, or is listed as not run with what you checked by hand.
