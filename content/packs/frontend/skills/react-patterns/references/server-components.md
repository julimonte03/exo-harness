# Server and Client Components

Only for projects whose framework supports them (for example the Next.js App Router). Caching, revalidation and routing rules are the framework's: check its documentation for the installed version before relying on one.

## The model

- **Server Components** run on the server (at build or request time) and never in the browser. They can be `async`, await data, read files and use secrets. They have no state, effects, event handlers, browser APIs or context.
- **Client Components** are the components you already know: state, effects, handlers, browser APIs, context. They render on the server for the first HTML too, then hydrate in the browser.
- The server sends a serialized tree; the client code ships only for the Client Components.

## Directives

- `'use client'` at the top of a file, before the imports, marks an entry into client code. The module and everything it imports become client code.
- `'use server'` at the top of a file makes every export a Server Function. Inside a Server Component, `'use server'` as the first line of an async function makes that function a Server Function.
- Files without a directive are shared: they become server or client code depending on who imports them.

## Where to put the boundary

Push `'use client'` down to the leaves that need interactivity:

```tsx
// app/products/[id]/page.tsx (Server Component)
export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);              // server-only data access
  return (
    <article>
      <h1>{product.name}</h1>
      <p>{product.summary}</p>
      <AddToCartButton productId={product.id} />      {/* the only client part */}
    </article>
  );
}
```

```tsx
// components/AddToCartButton.tsx
'use client';

export function AddToCartButton({ productId }: { productId: string }) {
  const [pending, startTransition] = useTransition();
  return (
    <button disabled={pending} onClick={() => startTransition(() => addToCart(productId))}>
      Add to cart
    </button>
  );
}
```

A `'use client'` on the root layout turns the whole app into client code and loses the benefit.

## Server Components inside Client Components

A Client Component cannot import a Server Component, but it can receive one as `children` or another JSX prop:

```tsx
// Server
<Tabs>
  <OrderHistory />        {/* Server Component, rendered on the server */}
</Tabs>

// Client: Tabs only places what it receives
'use client';
export function Tabs({ children }: { children: ReactNode }) { /* ... */ }
```

## Props across the boundary

Serializable: primitives, plain objects and arrays, `Map`, `Set`, `Date`, typed arrays, JSX elements, promises, and Server Functions. Not serializable: ordinary functions, class instances, objects with a null prototype, symbols that are not global.

Pass the smallest data the client needs, not whole records: everything in props reaches the browser.

## Data

- Fetch in the Server Component that needs the data. Start independent requests together (`Promise.all`), or render sibling components that each fetch, inside Suspense boundaries, so they stream in parallel.
- To stream into a Client Component, pass the promise as a prop and read it with `use()` under a Suspense boundary.
- Deduplicate repeated reads of the same data in one request with the framework's or React's `cache` helpers.

## Server Functions are endpoints

Anyone can call a Server Function, with any arguments, outside your UI.

```ts
'use server';

import { z } from 'zod';

// Zod 4: z.uuid(); in Zod 3, z.string().uuid() (skill:zod has both).
const RenameInput = z.object({ listId: z.uuid(), name: z.string().trim().min(1).max(80) });

export async function renameList(raw: unknown) {
  const session = await requireSession();                     // authenticate
  const input = RenameInput.parse(raw);                       // validate
  const list = await lists.findById(input.listId);
  if (!list || list.ownerId !== session.userId) throw new Error('Not found');  // authorize
  await lists.rename(list.id, input.name);
  return { id: list.id, name: input.name };                   // only what the client may see
}
```

- Validate every argument and check authorization inside each function; the UI hiding a button proves nothing.
- Know the framework's protection against cross-site requests for Server Functions, and do not weaken it.
- Errors that reach the client must not carry internals, stack traces or other users' data.

## Keep server code on the server

- Import the `server-only` package in modules with secrets, database access or internal APIs: a client import then fails the build.
- Environment variables without the framework's public prefix stay on the server; anything with the public prefix is in the bundle.
- Providers (theme, data client, session for the client) are Client Components: wrap them in one `Providers` component that the server layout renders.
- A third-party component that uses hooks but has no `'use client'`: re-export it from a small file that has the directive.
