# State and data patterns

## Context for app-wide state

One provider per concern, its value memoized, and a hook that fails clearly outside the provider:

```tsx
interface SessionValue {
  user: User | null;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const signOut = useCallback(async () => {
    await endSession();
    setUser(null);
  }, []);
  const value = useMemo(() => ({ user, signOut }), [user, signOut]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error('useSession must be used inside <SessionProvider>');
  return value;
}
```

- **Split by rate of change.** A value that changes on every keystroke in the same context as the signed-in user re-renders every consumer of both. Put them in separate contexts, or move the fast one to a store.
- **Split state and actions** when many components only call actions: one context for the state, one for the stable actions object.
- A prop passed down two or three levels is simpler than a context; do not add a provider for one consumer.

## A reducer for related changes

```ts
type CartEvent =
  | { type: 'added'; product: Product; quantity: number }
  | { type: 'quantity-set'; productId: string; quantity: number }
  | { type: 'cleared' };

function cartReducer(lines: CartLine[], event: CartEvent): CartLine[] {
  switch (event.type) {
    case 'added':
      return addLine(lines, event.product, event.quantity);
    case 'quantity-set':
      return setQuantity(lines, event.productId, event.quantity);
    case 'cleared':
      return [];
  }
}
```

The reducer is a pure function: test it without rendering. Because it declares its return type, the compiler flags a new event type that the `switch` does not handle; a `default` branch that assigns the event to a `never` variable makes the check explicit.

## URL state

Anything a person would bookmark, share or expect to survive a reload (filters, sort, page, a search query, the selected item) lives in the URL. With React Router:

```tsx
const SORT_KEYS = ['name', 'price', 'newest'] as const;
type SortKey = (typeof SORT_KEYS)[number];

function isSortKey(value: string | null): value is SortKey {
  return value !== null && (SORT_KEYS as readonly string[]).includes(value);
}

const [params, setParams] = useSearchParams();
const requested = params.get('sort');
const sort: SortKey = isSortKey(requested) ? requested : 'name';   // anything else falls back

function changeSort(next: SortKey) {
  setParams((current) => {
    current.set('sort', next);
    return current;
  }, { replace: true });
}
```

- Parse and validate what comes from the URL, as `isSortKey` does: a person can type anything there, and a cast (`as SortKey`) would only hide it. With zod in the project, `z.enum(SORT_KEYS).catch('name').parse(requested)` does the same.
- `replace: true` for changes that should not fill the back button history (typing in a filter); push for real navigation (opening an item).
- Debounce or defer the expensive work that a fast-changing query triggers, not the URL update itself.

## Browser storage

```ts
function readStored<T>(key: string, fallback: T, isValid: (value: unknown) => value is T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const value: unknown = JSON.parse(raw);
    return isValid(value) ? value : fallback;
  } catch {
    return fallback;   // invalid JSON, or storage blocked by the browser
  }
}
```

- Storage holds what a person may lose without harm (a guest cart, a preference). Never tokens with long lives, secrets or personal data beyond what the feature needs.
- Writes can fail too (quota, private mode): wrap `setItem` and keep the app working.
- A schema (`zod` when the project uses it) is the cleanest `isValid`.

## Server state

**With a data library** (TanStack Query, SWR, RTK Query): one query key or endpoint per resource, the library handles caching, deduplication, retries and refetching. Keep the request functions in the API layer and the hooks thin:

```ts
export function useProducts() {
  return useQuery({ queryKey: ['products'], queryFn: ({ signal }) => fetchProducts(signal) });
}
```

**Without one:** a hook per resource over the API client, as in the skill (section 3), with abort on change and a discriminated union for the states. When several screens need the same data, or caching and refetching become a problem, suggest a data library as a follow-up instead of growing a home-made cache.

## Mutations and optimistic updates before React 19

```tsx
async function toggleFavorite(product: Product) {
  const previous = favorites;
  setFavorites(toggle(previous, product.id));      // optimistic
  try {
    await saveFavorite(product.id, !previous.includes(product.id));
  } catch (error) {
    setFavorites(previous);                        // roll back
    setNotice(`Could not save ${product.name}. Try again.`);
  }
}
```

- Use it only when the success rate is high and the rollback is clear to the person.
- With React 19, `useOptimistic` inside an Action does the rollback for you (skill:react-patterns).
- Payments, orders and anything with money wait for the server: show a pending state instead.

## Waterfalls

```ts
// Waterfall: the second request waits for the first for no reason.
const user = await fetchUser(id);
const orders = await fetchOrders(id);

// Parallel:
const [user, orders] = await Promise.all([fetchUser(id), fetchOrders(id)]);
```

In components, a parent that renders a loading state until its data arrives, and a child that only then starts its own request, is the same waterfall. Fetch both at the route level, or let the data library prefetch.
