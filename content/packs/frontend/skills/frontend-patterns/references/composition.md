# Composition patterns

Examples in TypeScript with function components. Adapt names, exports and file layout to the project.

## Slots instead of flags

Before: every new need adds a boolean, and some combinations break.

```tsx
<Panel title="Billing" showHeader compact withIcon icon={<CardIcon />} showFooter />
```

After: the caller passes the parts it wants; the panel only lays them out.

```tsx
interface PanelProps {
  header?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  density?: 'comfortable' | 'compact';
}

export function Panel({ header, actions, children, density = 'comfortable' }: PanelProps) {
  return (
    <section className={`panel panel--${density}`}>
      {header && <header className="panel__header">{header}</header>}
      <div className="panel__body">{children}</div>
      {actions && <footer className="panel__actions">{actions}</footer>}
    </section>
  );
}
```

A string union (`density`) replaces flags that are really one choice among several.

## Compound components

The parent owns the state; the parts read it from a small context. The context is private to the module, and a part used outside its parent fails with a clear message.

```tsx
const TabsContext = createContext<{ selected: string; select: (id: string) => void } | null>(null);

function useTabs() {
  const value = useContext(TabsContext);
  if (!value) throw new Error('Tabs parts must be used inside <Tabs>');
  return value;
}

export function Tabs({ defaultTab, children }: { defaultTab: string; children: ReactNode }) {
  const [selected, select] = useState(defaultTab);
  const value = useMemo(() => ({ selected, select }), [selected]);
  return <TabsContext.Provider value={value}>{children}</TabsContext.Provider>;
}

Tabs.List = function TabList({ label, children }: { label: string; children: ReactNode }) {
  return <div role="tablist" aria-label={label}>{children}</div>;
};

Tabs.Tab = function Tab({ id, children }: { id: string; children: ReactNode }) {
  const { selected, select } = useTabs();
  return (
    <button
      role="tab"
      id={`tab-${id}`}
      aria-selected={selected === id}
      aria-controls={`panel-${id}`}
      tabIndex={selected === id ? 0 : -1}
      onClick={() => select(id)}
    >
      {children}
    </button>
  );
};

Tabs.Panel = function TabPanel({ id, children }: { id: string; children: ReactNode }) {
  const { selected } = useTabs();
  if (selected !== id) return null;
  return <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`}>{children}</div>;
};
```

A real tab widget also moves between tabs with the arrow keys; the keyboard pattern of each widget is in `accessibility-audit/references/aria-patterns.md` in the skills folder. Prefer the project's component library when it already has the widget.

## Container and view

```tsx
// The container gets the data and handles its states.
export function OrderHistory() {
  const orders = useOrders();
  if (orders.status === 'loading') return <OrderListSkeleton />;
  if (orders.status === 'error') return <ErrorNotice message={orders.message} onRetry={orders.retry} />;
  return <OrderList orders={orders.data} />;
}

// The view only renders props: easy to reuse, to test and to show in a component catalog.
export function OrderList({ orders }: { orders: Order[] }) {
  if (orders.length === 0) return <EmptyState title="No orders yet" />;
  return <ul>{orders.map((order) => <OrderRow key={order.id} order={order} />)}</ul>;
}
```

Split this way only when the view has a reason to exist alone: reuse, a component catalog, or tests without network.

## Controlled and uncontrolled components

```tsx
interface QuantityInputProps {
  value?: number;            // controlled
  defaultValue?: number;     // uncontrolled
  onChange?: (value: number) => void;
  max: number;
}

export function QuantityInput({ value, defaultValue = 1, onChange, max }: QuantityInputProps) {
  const [inner, setInner] = useState(defaultValue);
  const current = value ?? inner;
  function set(next: number) {
    const clamped = Math.min(Math.max(next, 1), max);
    if (value === undefined) setInner(clamped);
    onChange?.(clamped);
  }
  // ...render buttons and an input that call set()
}
```

A component is controlled or uncontrolled for its whole life; switching between the two (value starting as `undefined` and later set) is a bug React warns about.

## Polymorphic components

An `as` prop (`<Button as="a" href="...">`) is convenient but hard to type and easy to misuse: a link styled as a button must still be a link, and a button must still be a button. Prefer two components (`Button`, `ButtonLink`) that share styles, unless the project's design system already has a typed `as`.

## Folders

Follow the existing layout. When a project has none, or has outgrown a flat `components/` folder:

```text
src/
  app/ or main.tsx          entry, providers, router
  pages/ or routes/         one entry per route; thin, compose features
  features/
    cart/
      components/           CartDrawer.tsx, CartLine.tsx
      hooks/                useCart.ts
      api.ts                requests of this feature, over the shared client
      index.ts              the feature's public surface
    checkout/
  components/               shared UI with no feature knowledge (Button, Dialog, Price)
  hooks/                    shared hooks (useMediaQuery, useDebouncedValue)
  api/                      the shared API client
  lib/                      pure helpers
  test/                     test setup and render helpers
```

- A feature imports shared folders and other features' public `index.ts`, never their internals.
- Move to features gradually, one feature per change, and only when a task asks for it.
