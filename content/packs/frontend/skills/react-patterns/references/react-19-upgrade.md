# Upgrading from React 18 to 19

An upgrade is its own change, with the person's approval: in SDD, a change whose plan names the new versions. Never bump React inside another task.

## Before

1. **Be on 18.3 first.** It is 18.2 plus warnings for every API that 19 removes. Run the app and the tests on 18.3 and fix those warnings.
2. **Check every library that touches React:** router, data library, UI kit, form library, Testing Library, animation, charts. Read each changelog for React 19 support and the version that brings it. A library whose peer range stops at `react@^18` blocks the upgrade; forcing it with `overrides` needs its own testing and the person's decision.
3. **Note the test command** and the current result, so a regression is visible.

## The bump

- Upgrade `react`, `react-dom`, `@types/react` and `@types/react-dom` together, to the same major.
- Upgrade Testing Library to a version that supports React 19.
- The React team publishes codemods for this migration: a migration recipe for the code and a preset for the TypeScript types. They download and run a package, so the person runs them on a clean branch, and the diff gets a review like any other.

## Removed APIs and their replacements

| Removed | Use |
|---|---|
| `ReactDOM.render`, `ReactDOM.hydrate` | `createRoot`, `hydrateRoot` from `react-dom/client` |
| `unmountComponentAtNode` | `root.unmount()` |
| `findDOMNode` | A ref to the DOM node |
| `propTypes` checks on components | TypeScript types, or a runtime schema at the boundary |
| `defaultProps` on function components | Default values in the parameters (`{ size = 'md' }`); class components keep `defaultProps` |
| String refs (`ref="input"`) | `useRef`, `createRef` or a callback ref |
| Legacy context (`contextTypes`, `getChildContext`) | `createContext` and `useContext` |
| `act` from `react-dom/test-utils` | `act` from `react` |
| `react-test-renderer/shallow` | Testing Library |
| `createFactory`, module pattern factories | JSX or `createElement` |
| UMD builds | A bundler, or an ES module CDN |

## Behavior changes to test

- **Errors during render** are no longer re-thrown: uncaught ones go to `window.reportError`, caught ones to `console.error`. `createRoot` accepts `onUncaughtError` and `onCaughtError` to send them to the project's error reporting.
- **StrictMode** reuses the results of `useMemo` and `useCallback` from the first of its double renders.
- **Suspense** shows the nearest fallback sooner when a component suspends, and renders the siblings afterwards. Loading sequences may look different; check the screens with several boundaries.
- **Forms with `action`** reset their uncontrolled fields after a successful Action.

## TypeScript changes

- `useRef` needs an argument: `useRef<HTMLInputElement>(null)`, `useRef<number | undefined>(undefined)`.
- A ref callback must not return a value by accident: `ref={(el) => (node = el)}` becomes `ref={(el) => { node = el; }}`, since a returned function is now a cleanup.
- The global `JSX` namespace is gone: use `React.JSX` (`import type { JSX } from 'react'`).
- The props of a `ReactElement` default to `unknown` instead of `any`: type them where the code reads them.

## After

1. Typecheck, lint, run the tests and the app; compare with the result noted before.
2. Adopt the new features gradually, each where it pays: Actions and `useActionState` in forms, `useOptimistic` where waiting hurts, `ref` as a prop in new components, `<Context>` as a provider. Remove `forwardRef` over time, not in one sweep.
3. Turning on the React Compiler is a separate decision and a separate change.
