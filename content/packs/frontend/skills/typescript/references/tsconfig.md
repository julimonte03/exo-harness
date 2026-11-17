# Compiler settings and versions

What `typescript` checks in a tsconfig, and which features each TypeScript version brings. Change a tsconfig only when the task is to change it; never loosen a flag to silence an error.

## Flags

| Flag | In `strict` | What it catches | Recommendation |
|---|---|---|---|
| `strict` | — | Turns on the strict family below | Always on |
| `noImplicitAny` | yes | Parameters and variables that fall back to `any` | On |
| `strictNullChecks` | yes | Use of values that can be `null` or `undefined` | On |
| `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization` | yes | Unsound function assignments, wrong `call` and `apply` arguments, class fields never set | On |
| `useUnknownInCatchVariables` | yes | `catch (e)` typed `unknown` instead of `any` | On |
| `alwaysStrict`, `noImplicitThis` | yes | Sloppy mode, untyped `this` | On |
| `noUncheckedIndexedAccess` | no | `array[i]` and `record[key]` typed with `\| undefined` | On for new code bases; turning it on later surfaces many errors: its own change |
| `exactOptionalPropertyTypes` | no | `prop?: string` no longer accepts an explicit `undefined` | Optional; strict but noisy with many libraries |
| `noImplicitOverride` | no | Overriding a method without `override` | On when the code uses classes |
| `noFallthroughCasesInSwitch` | no | A `case` that falls into the next without `break` or `return` | On |
| `noImplicitReturns` | no | Code paths that return nothing in a function that returns a value | On |
| `noUnusedLocals`, `noUnusedParameters` | no | Dead variables and parameters | Often left to the linter |
| `verbatimModuleSyntax` | no | Type-only imports written without `import type` | On for ESM projects (5.0+) |
| `isolatedModules` | no | Code a single-file transpiler (esbuild, SWC, Babel) cannot compile | On with bundlers; implied by `verbatimModuleSyntax` |
| `erasableSyntaxOnly` | no | `enum`, `namespace` with values, parameter properties: syntax that type stripping cannot remove | On when Node runs the code from source (5.8+) |
| `allowImportingTsExtensions` | no | Allows `./pricing.ts` in imports | Needed under type stripping with `noEmit` |
| `rewriteRelativeImportExtensions` | no | Rewrites `.ts` imports to `.js` when `tsc` emits | When the same code runs from source and from build output (5.7+) |
| `skipLibCheck` | no | Skips type checks of `.d.ts` files | Common for speed; it hides broken library types |

## Module settings

| Runtime | `module` and `moduleResolution` |
|---|---|
| Bundler (Vite, webpack, esbuild, Next.js) | `module: "ESNext"` (or `"preserve"`), `moduleResolution: "bundler"` |
| Node, compiled with `tsc` | `module: "nodenext"` (or `"node20"` in 5.9+); `moduleResolution` follows |
| Node, from source with type stripping | `module: "nodenext"` or `"ESNext"` with `"bundler"`, plus `allowImportingTsExtensions`, `noEmit`, `verbatimModuleSyntax`, `erasableSyntaxOnly` |
| A library for others | `nodenext`, with declaration output and `exports` in `package.json` |

`paths` aliases (`"@/*": ["src/*"]`) must be mirrored in the bundler or test runner config (Vite `resolve.alias`, Jest `moduleNameMapper`); check both when you add one.

## Versions

Use a feature only if the project's TypeScript version has it.

| Version | Feature |
|---|---|
| 4.9 | `satisfies` |
| 5.0 | Const type parameters, `verbatimModuleSyntax`, `moduleResolution: "bundler"`, standard decorators, `export type *` |
| 5.2 | `using` and `await using` declarations for disposable resources |
| 5.3 | Import attributes (`import data from './x.json' with { type: 'json' }`) |
| 5.4 | `NoInfer<T>`; narrowing kept inside closures after the last assignment |
| 5.5 | Inferred type predicates (`items.filter((x) => x !== undefined)` narrows), `isolatedDeclarations`, regular expression syntax checks |
| 5.6 | Errors on conditions that are always truthy or always nullish |
| 5.7 | `rewriteRelativeImportExtensions`; errors on variables that are never initialized |
| 5.8 | `erasableSyntaxOnly`; `module: "node18"`; finer checks of conditional return expressions |
| 5.9 | `import defer`; `module: "node20"` |

For a newer major version, read its release notes before relying on a default: defaults and deprecations change between majors.
