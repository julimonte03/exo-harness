---
name: react-patterns
description: >-
  React 18 and 19 features and when to use each, checked against the
  installed React version and framework before anything is suggested: hooks
  discipline (rules of hooks, dependencies, cleanup, effects only to sync
  with external systems), Server and Client Components and the 'use client'
  boundary, Server Functions, Actions with useActionState and useFormStatus,
  useOptimistic, use() for promises and context, transitions and
  useDeferredValue, Suspense with error boundaries, ref as a prop, the React
  Compiler and when manual memoization still matters, and the upgrade from 18
  to 19. General component and state patterns are in frontend-patterns. Use
  it when someone wants to use or understand one of these features, asks
  whether the project can, or plans a React upgrade. Triggers: "server
  component", "use client", "server action", "useActionState",
  "useOptimistic", "useFormStatus", "use() hook", "Suspense", "useTransition",
  "useDeferredValue", "React 19", "upgrade React", "forwardRef", "React
  Compiler".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# react-patterns

## Result

- The right React feature for the job, among those the installed version and framework actually have, applied in code or explained with its trade-offs.
- When the feature the person asks for is not available: the version with its `path:line`, what the feature needs, and the options (the equivalent for the installed version, or an upgrade as its own change). Never code that calls an API the installed React does not export.

## When

| Moment | What you do |
|---|---|
| SDD design | Pick the React features the design relies on, and check they exist in the installed version |
| SDD apply | Apply them in the task's files |
| On request | Explain, apply or compare these features; plan an upgrade from 18 to 19 |

- **Not for:** general composition, custom hooks, state placement, data fetching states and folder structure (skill:frontend-patterns); tests (skill:react-testing); type design (`typescript`).

## 1. Check the version and the framework first

Always, before suggesting any feature below:

1. The `react` and `react-dom` versions in the web package's `package.json` (and the lockfile when the range is loose). Keep the `path:line`.
2. The framework: Next.js (App Router or Pages Router), React Router in framework mode, Remix, or a client-only app (Vite, a custom bundler). Look at the dependencies and the config files.
3. Whether the React Compiler is on: `babel-plugin-react-compiler` in the build config, or the framework's compiler option.

| Feature | Needs |
|---|---|
| `useTransition`, `startTransition`, `useDeferredValue`, `useId`, `useSyncExternalStore`, automatic batching, `createRoot` | React 18 |
| Actions (async functions in transitions), `useActionState`, `useOptimistic`, `use()`, `<form action={fn}>`, `useFormStatus` (from `react-dom`), ref as a prop, `<Context>` as its own provider, cleanup functions in ref callbacks, `<title>` and `<meta>` rendered from components | React 19 |
| `<Activity>`, `useEffectEvent` | React 19.2 |
| Server Components, `'use client'`, Server Functions (`'use server'`) | React 19 and a framework or bundler that supports them (for example the Next.js App Router). A client-only app has none |
| React Compiler | A build plugin; React 19, or 17 and 18 with its runtime package |

**Not available:** say it with the evidence (`react ^18.3.1 at apps/portal/package.json:12: useOptimistic needs React 19`), then offer the equivalent for the installed version (sections below) and, if it is worth it, an upgrade as a separate change (`references/react-19-upgrade.md`). Never upgrade React in passing, inside another task. For anything newer than this table, read the changelog of the installed version.

## 2. Hooks discipline

- **Rules of hooks:** call hooks at the top level of a component or another hook, never in conditions, loops or after an early return. `use()` is the exception: it may be called conditionally.
- **Dependencies:** every value from the component that an effect, `useMemo` or `useCallback` reads is in its dependency array. Keep the lint rule (`react-hooks/exhaustive-deps`) on; never silence it to stop a loop: fix the cause (move the object inside the effect, derive it, or read it through an effect event).
- **Effects only synchronize with something outside React:** a subscription, a timer, the DOM, a non-React widget, a request. Derived values and responses to events do not need effects (skill:frontend-patterns, Anti-patterns).
- **Cleanup:** every effect that subscribes, listens, starts a timer or a request returns a cleanup. StrictMode runs effects twice in development (mount, unmount, mount) to show the missing ones: never disable StrictMode to hide them.
- **Effect events** (React 19.2): `useEffectEvent` reads the latest props and state inside an effect without making the effect re-run. Before 19.2, keep the latest value in a ref updated in an effect.
- **External stores:** `useSyncExternalStore` for a store that lives outside React (browser APIs, a non-React state library), not an effect plus `useState`.
- **Ids:** `useId` for `id`, `htmlFor` and `aria-*` relations, never `Math.random()`.

## 3. Server and Client Components

Only in a framework that supports them. In short (details in `references/server-components.md`):

- **Server by default.** Components render on the server unless their module starts with `'use client'`, or is imported, directly or not, from a module that does.
- **`'use client'` at the leaves** that need state, effects, event handlers or browser APIs. It marks an entry into client code: everything that module imports ships to the browser.
- **Props that cross into a Client Component must be serializable:** plain data, JSX, promises, and Server Functions. No class instances, no ordinary functions.
- **Pass Server Components as `children`** (or other JSX props) to Client Components instead of importing them there.
- **Secrets and server-only code** stay in modules guarded with the `server-only` package; a client import of one then fails at build time.
- **Fetch data in Server Components,** close to where it is used, in parallel; pass a promise to a Client Component and read it with `use()` when the client part should stream.
- **Server Functions are public endpoints:** anyone can call them with any arguments. Validate the input (`zod` when the project uses it), authenticate and authorize inside each one, and return only what the client may see.

## 4. Actions and forms (React 19)

An Action is an async function run in a transition. With a form:

```tsx
import { useActionState } from 'react';
import { useFormStatus } from 'react-dom';

type SubscribeState = { error: string | null; done: boolean; email: string };

async function subscribe(previous: SubscribeState, formData: FormData): Promise<SubscribeState> {
  const email = String(formData.get('email') ?? '').trim();
  if (!email.includes('@')) return { error: 'Enter a valid email address', done: false, email };
  try {
    await saveSubscription(email);
    return { error: null, done: true, email: '' };
  } catch {
    return { error: 'Could not subscribe. Try again.', done: false, email };   // keep what they typed
  }
}

function SubmitButton() {
  const { pending } = useFormStatus();          // must render inside the <form>
  return <button type="submit" disabled={pending}>{pending ? 'Subscribing...' : 'Subscribe'}</button>;
}

export function NewsletterForm() {
  const [state, formAction] = useActionState(subscribe, { error: null, done: false, email: '' });
  if (state.done) return <p role="status">Thanks! Check your inbox.</p>;
  return (
    <form action={formAction}>
      <label htmlFor="newsletter-email">Email</label>
      <input
        id="newsletter-email"
        name="email"
        type="email"
        defaultValue={state.email}
        aria-describedby="newsletter-error"
      />
      {state.error && <p id="newsletter-error" role="alert">{state.error}</p>}
      <SubmitButton />
    </form>
  );
}
```

- `useActionState` returns `[state, formAction, isPending]`; the action receives the previous state first, then the form data.
- After the Action, React resets the uncontrolled fields of a `<form action>`, also when your function returned an error state. Keep what the person typed by returning it in the state and using it as the field's `defaultValue`, as `email` does above, or with controlled fields.
- `useFormStatus` reads only the status of the form that contains the component.
- **React 18 equivalent:** an `onSubmit` handler with `event.preventDefault()`, a `submitting` state that disables the button, and the error in state.

## 5. Optimistic updates (React 19)

```tsx
const [optimisticItems, addOptimistic] = useOptimistic(items, (current, added: Item) => [...current, added]);

async function addItemAction(formData: FormData) {
  const item = toItem(formData);
  addOptimistic(item);                 // shown at once
  await saveItem(item);                // when the Action ends, the real state replaces it
}
```

- Call the update function inside an Action or `startTransition`. When the Action finishes or fails, the optimistic value is dropped and the real state shows: tell the person when it failed.
- Not for money, orders or anything the person must not believe happened before it did.
- **React 18 equivalent:** set the state at once, keep the previous value, and roll back on error (skill:frontend-patterns, `frontend-patterns/references/state-and-data.md` in the skills folder). A change that only updates local state has nothing to wait for: it needs no optimistic layer.

## 6. `use()` (React 19)

- `use(promise)` suspends until the promise settles; the nearest Suspense boundary shows its fallback and the nearest error boundary catches a rejection.
- The promise must come from outside the render: a Server Component, a loader, or a cache. A promise created during a Client Component's render is recreated on every render and never settles from React's point of view.
- `use(SomeContext)` reads a context, and may be called in a condition or loop.
- **React 18 equivalent:** a data library with Suspense support, or a hook with loading and error states.

## 7. Transitions and deferred values

- `useTransition` (`[isPending, startTransition]`) marks an update as non-urgent: switching tabs, applying a filter to a large list. The old UI stays interactive and `isPending` can dim it. In React 19 the function may be async (an Action).
- `useDeferredValue(value)` lets an expensive render lag behind a fast input: type in a search box, and the long result list re-renders with the deferred query.
- Never put the controlled input's own value in a transition: the field would lag behind the keyboard.
- Updates inside a transition do not show a Suspense fallback again for content already on screen; the old content stays until the new one is ready.

## 8. Suspense and error boundaries

- Place a Suspense boundary where a loading state makes sense to the person (a panel, a route), with a fallback the size of the content.
- Put an error boundary with a retry next to each Suspense boundary that loads data; Suspense does not handle errors.
- One boundary per independent region, so a slow widget does not hide the whole page.
- In a client-only app, Suspense works with `lazy` for code splitting and with data libraries that support it.

## 9. Refs

- React 19: a function component receives `ref` as a regular prop; `forwardRef` is no longer needed in new code. A ref callback may return a cleanup function.
- React 18: keep `forwardRef` for components that expose a DOM node.
- `useImperativeHandle` only for imperative APIs a parent really needs (`focus()`, `scrollToItem()`); state and data still flow through props.

## 10. The React Compiler and memoization

- **Compiler on:** do not add `useMemo`, `useCallback` or `memo` by hand; it memoizes for you. Keep components and hooks pure (no mutation of props, state or values during render) and keep the hooks lint rules on, since the compiler skips code that breaks them. Existing manual memoization can stay.
- **Compiler off:** memoize only measured costs, or where a stable reference matters (a memoized child, an effect dependency).
- Turning the compiler on is a build change of its own, with the person's approval: suggest it, do not slip it into a task.

## Return

```markdown
Version: react ^18.3.1 (apps/portal/package.json:12), client-only Vite app (no Server Components), no React Compiler.
Asked: move the invoice list to a Server Component and read its data with use().
Answer: not available here. use() needs React 19; Server Components need React 19 and a framework that supports them.
- Now: keep the list a client component with its loading, empty and error states, and start its request at the route level to avoid the waterfall (frontend-patterns).
- Later: a React 19 upgrade as its own change gives use() (references/react-19-upgrade.md); Server Components also need a framework, a larger decision for the person.
```

## Record

Inside a change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "react-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"react-patterns"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The React version, the framework and the compiler were checked, with `path:line`, before any feature was used.
- [ ] No API that the installed version does not export; the gap is explained with its options.
- [ ] Effects only synchronize with external systems, list every dependency and clean up.
- [ ] Server Functions validate input and check authorization; nothing server-only is imported by client code.
- [ ] No React upgrade or compiler switch slipped into another task.
