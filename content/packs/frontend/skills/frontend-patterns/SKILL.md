---
name: frontend-patterns
description: >-
  General patterns for React and TypeScript application code, whatever the
  React version: component composition (children, slots, compound
  components), custom hooks, where each piece of state lives (local, lifted,
  context, URL, server cache, form), data fetching with its loading, empty and
  error states, error boundaries, forms, performance (memoization, list keys,
  virtualization, code splitting) and folder structure, plus the
  anti-patterns to fix. React 19 features (Server Components, Actions, use(),
  useOptimistic) are in react-patterns. Use it when writing or refactoring
  components and hooks, when deciding where state belongs, when a component
  grows too big, or when organizing a React codebase. Triggers: "custom
  hook", "extract a hook", "prop drilling", "lift state up", "should this be
  a context", "where should this state live", "compound component",
  "refactor this component", "error boundary", "loading and error states",
  "folder structure for React".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# frontend-patterns

## Result

- Components and hooks that follow the patterns below and the project's own conventions: one clear job per component, state in the right home, every data state handled, no anti-pattern from the table at the end.
- In the answer: the pattern you chose and why, the files touched, the follow-ups, and the commands that check the change (with their result, or "not run").

## When

| Moment | What you do |
|---|---|
| SDD apply, a task that adds or changes components or hooks | Apply these patterns inside the task's files |
| SDD design | Give `sdd-design` the component tree, state ownership and data flow for the frontend part |
| On request | Write, refactor or review components and hooks; decide where state lives; organize folders |

- **Not for:** features that need React 19 or a framework (Server Components, Actions, `use()`, `useOptimistic`, transitions in depth: skill:react-patterns); tests (skill:react-testing); visual design and design tokens (skill:frontend-design); type design (`typescript`); runtime validation of data (`zod`).
- **Version:** these patterns work on React 16.8 and later. Before you suggest a hook or API, check the `react` version in the web package's `package.json`.

## 1. Read the neighbors first

1. Two files of the same kind as the one you are about to write (two components, two hooks): naming, named or default exports, prop types (`interface` or `type`), how they import (`@/` alias or relative), where their tests live.
2. The libraries already in use, from `package.json`: data (TanStack Query, SWR, RTK Query, or plain hooks over an API client), state (Redux, Zustand, Jotai, or context), forms (React Hook Form, Formik, or plain state), routing.
3. `.exo/context.md` conventions, when present: they win over this skill.

**Follow what is there.** A pattern from this skill that conflicts with the project's convention is a suggestion for the person, not a change you make.

## 2. Composition

- **One job per component.** Split when a file mixes data loading, state rules and markup that someone would want to reuse, or when it passes about 200 lines.
- **Children and slots before flags.** Pass content as `children` or as named element props (`header`, `actions`) instead of growing boolean props (`showHeader`, `compact`, `withIcon`). Flags that combine badly become a `variant` union.
- **Compound components** for widgets whose parts share state (tabs, accordions, menus): a parent owns the state and shares it through a small context; the parts read it. Details in `references/composition.md`.
- **Container and view** when data loading would block reuse or testing: a thin container gets the data, a view renders props. Do not split a component that has no reuse or test reason.
- **Controlled or uncontrolled:** a reusable input accepts `value` and `onChange` (controlled), and may offer `defaultValue` (uncontrolled). Never both for the same prop.
- **Never define a component inside another component's body:** it remounts on every render and loses its state.

## 3. Custom hooks

Write a hook when stateful logic is shared by two components, or when naming a concern makes a component readable (`useCartTotals`, `useInvoiceSearch`). A calculation with no state or effect is a plain function, not a hook.

- Name it `useX`; put it where the project keeps hooks (often `src/hooks/`), or next to its only user.
- Take an options object when there are more than two parameters; return an object with named fields (a pair like `[value, setValue]` may be a tuple).
- Model async state as a discriminated union, so impossible combinations cannot exist:

```ts
type Lookup<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; message: string };

export function useInvoice(id: string | null): Lookup<Invoice> {
  const [state, setState] = useState<Lookup<Invoice>>({ status: 'idle' });
  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    setState({ status: 'loading' });
    getInvoice(id, controller.signal).then(
      (data) => setState({ status: 'success', data }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Could not load the invoice';
        setState({ status: 'error', message });
      },
    );
    return () => controller.abort();
  }, [id]);
  return state;
}
```

- Every effect that subscribes, starts a timer or a request cleans up after itself.
- No hidden module-level state shared between components unless that is the point (a store), and then use the project's store.
- Test it through its component, or with `renderHook` when it is shared (skill:react-testing).

## 4. Where state lives

| Kind | Examples | Home |
|---|---|---|
| Local UI | open or closed, the draft of an input, hover | `useState` in the component that uses it |
| Shared by siblings | the selected tab and its panel | The closest common parent, passed down as props |
| URL | filters, sort, page, search query, selected id | The router's search params or path: a person can bookmark and share it |
| Server cache | products, orders, the current user's profile | The project's data library, or one hook per resource over the API client |
| Form | values, errors, touched fields, submitting | The project's form library, or one state object per form |
| App-wide, changes rarely | theme, locale, signed-in user, a cart used on many screens | A context provider per concern, near the top of the tree |
| App-wide, changes often | a live editor, a large client cache | The project's store (Zustand, Redux); not one big context |

- **Derive, do not duplicate.** A value you can compute from props or state is computed during render (`const total = items.reduce(...)`), not kept in a second state and synced with an effect.
- **One source of truth.** Copying a prop into state freezes it; use the prop, or reset the child with a `key` when the identity changes.
- **Prop drilling is fine for two or three levels.** Reach for context when many levels or many distant components need the same value. Memoize the context value (`useMemo`) and split contexts by how often they change, so one update does not re-render every consumer.
- `useReducer` when several values change together through named events (`added`, `removed`, `cleared`).
- Details and a context example are in `references/state-and-data.md`.

## 5. Data fetching

- **Use the data library the project has.** Without one, write one hook per resource over the project's API client; components never call `fetch` directly when a client exists.
- **Render every state:** loading (a skeleton the size of the content, so nothing jumps), empty (what it means and what to do), error (what happened, and a retry that keeps what the person typed), success. Partial results when some requests fail.
- **Races:** abort the request when the input changes or the component unmounts, or ignore stale responses.
- **No waterfalls:** start independent requests together (`Promise.all`, or parallel queries), and fetch at the route or page level instead of in each leaf when that creates a cascade.
- **Mutations:** disable the trigger while pending so it cannot be sent twice; on failure keep the input and show the error; an optimistic update rolls back on failure (with React 19, `useOptimistic` in skill:react-patterns).
- **Untrusted data:** validate API responses and stored values at the boundary (`zod` when the project uses it); never trust `JSON.parse` of browser storage without a fallback.

## 6. Errors and loading

- **Error boundaries** around each route and each independent widget, with a fallback that says what failed and offers a retry. Use the project's boundary component or library when it has one; otherwise a small class component.
- Boundaries do not catch errors in event handlers or in promises: handle those in state and show them.
- **Lazy routes and heavy screens** load with `lazy` and `Suspense`, with a fallback that keeps the layout.
- Avoid loading flashes: a spinner that appears for 50 ms is worse than none; keep the previous content while a refresh runs.

## 7. Forms

- Every field has a visible label; the error text is next to the field and linked to it (`aria-describedby`), with `aria-invalid` on the field.
- Validate on submit; after that, revalidate a field as the person fixes it. Move focus to the first invalid field.
- Disable submit only while submitting, not while invalid, so the person can see what is wrong.
- Keep validation rules in one module (or one schema) shared with tests, and with the server when the stack allows.
- Use the project's form library when it has one; a large form without one may justify it as a follow-up.

## 8. Performance

- **Measure first** with the React DevTools Profiler or the browser's performance panel. Most re-renders are cheap.
- `memo`, `useMemo` and `useCallback` only when the work is expensive, or when a stable reference matters (a memoized child, an effect dependency). With the React Compiler on, skip manual memoization (skill:react-patterns).
- **Keys:** stable ids from the data, never the array index for lists that reorder, filter or insert.
- **Long lists** (hundreds of rows): paginate, or virtualize with the project's library.
- **Code splitting:** lazy-load routes and heavy, rarely used screens. A new dependency is worth its size in the bundle.
- Keep state that changes on every keystroke low in the tree, so typing does not re-render the page.

## 9. Folder structure

- **Follow the existing structure.** Move files only when the task asks for it.
- A new codebase, or one that outgrew its folders: group by feature once there are several features (`features/cart/{components,hooks,api}`), with shared UI in `components/`, shared hooks in `hooks/`, the API client in `api/`, and route entries in `pages/` or `routes/`.
- Tests next to their file (`X.test.tsx`) or in `__tests__/`, as the project does.
- Barrel files (`index.ts`) at a folder boundary only; deep barrels slow builds, hide cycles and can defeat tree shaking.
- Layout guidance with an example tree is in `references/composition.md`, Folders.

## 10. Anti-patterns

| Symptom | Fix |
|---|---|
| `useEffect` that sets state computed from props or other state | Compute it during render; `useMemo` only if it is expensive |
| `useEffect` that reacts to a click or submit | Do the work in the event handler |
| A prop copied into state at mount | Use the prop; reset with `key` when its identity changes |
| Index as `key` in a list that changes order | A stable id from the data |
| `fetch` in an effect with no cleanup | Abort it, or ignore stale responses; better, the data library |
| A component of 300+ lines mixing data, rules and markup | Extract a hook for the logic and child components for the parts |
| Several boolean props that combine badly | Composition with children, or a `variant` union |
| A context value object created on every render | `useMemo`, and split the context by concern |
| `JSON.parse(localStorage.getItem(...))` with no guard | `try`/`catch` with a fallback, and validate the shape |
| A component declared inside another component | Move it to module level |
| Loading, empty or error state missing | Render all of them (section 5) |
| `any` in props or hook results | A real type (`typescript`) |

## Steps

1. Read the neighbors and the stack (section 1).
2. Pick the pattern for the job: composition, a hook, a state home, the data states.
3. Write the smallest change that does it. Keep the public props of existing components stable, or update every caller in the same change.
4. Write or update the tests (skill:react-testing).
5. Check with the project's typecheck, lint and test commands (`.exo/context.md` or the package scripts). A tool with no script runs from the installed packages only (`npm exec --no -- tsc --noEmit`), never through `npx`, which downloads what is not installed. When you cannot run them here, give the exact commands and review by reading.

## Return

```markdown
Pattern: compound Tabs (Tabs, Tabs.List, Tabs.Tab, Tabs.Panel) sharing the selected tab through a small context; it replaces three boolean props of SettingsPanel.
Files: src/components/Tabs.tsx (new), src/pages/Settings.tsx (uses it), src/components/Tabs.test.tsx (new).
Why: the flags combined badly (compact with icons broke the layout); the parts now render only what they receive.
Checks: npm run typecheck --workspace @acme/storefront; npm test --workspace @acme/storefront (not run in this session).
Follow-ups: the selected tab could live in the URL so it survives a reload (outside this task).
```

## Record

Inside a change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "frontend-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"frontend-patterns"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The change follows the neighbors' naming, exports, imports and folders.
- [ ] Each piece of state has one home from the table; nothing derived is stored.
- [ ] Every data flow renders loading, empty, error and success, and cancels or ignores stale requests.
- [ ] No anti-pattern from the table in the lines you wrote.
- [ ] Only APIs that the installed React version has; no new dependency the plan does not name.
- [ ] Tests updated, and the check commands in the answer with their result or "not run".
