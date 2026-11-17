# Type patterns

Worked examples for `typescript`. Adapt names and style to the project.

## Discriminated union with an exhaustive check

```ts
export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled';

export type OrderEvent =
  | { kind: 'placed'; at: string }
  | { kind: 'paid'; at: string; receiptId: string }
  | { kind: 'cancelled'; at: string; reason: string };

function assertNever(value: never): never {
  throw new Error(`Unhandled case: ${JSON.stringify(value)}`);
}

export function describe(event: OrderEvent): string {
  switch (event.kind) {
    case 'placed':
      return `Placed at ${event.at}`;
    case 'paid':
      return `Paid (receipt ${event.receiptId})`;
    case 'cancelled':
      return `Cancelled: ${event.reason}`;
    default:
      return assertNever(event);
  }
}
```

Adding `{ kind: 'refunded'; ... }` to the union makes `assertNever(event)` fail to compile until `describe` handles it. With no runtime helper, `default: { const unreachable: never = event; throw new Error(String(unreachable)); }` does the same.

## Closed sets without enum

```ts
export const STOCK_LEVELS = ['in-stock', 'low-stock', 'out-of-stock'] as const;
export type StockLevel = (typeof STOCK_LEVELS)[number];

export const isStockLevel = (value: string): value is StockLevel =>
  (STOCK_LEVELS as readonly string[]).includes(value);
```

The array is the runtime list (for selects, validation), the union is the type, and both stay in sync. It is erasable syntax, so it works under Node's type stripping where `enum` does not.

## Branded IDs and units

```ts
declare const brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [brand]: B };

export type ProductId = Brand<string, 'ProductId'>;
export type Cents = Brand<number, 'Cents'>;

export function toCents(value: number): Cents {
  if (!Number.isInteger(value) || value < 0) throw new RangeError(`Invalid cents: ${value}`);
  return value as Cents; // the only cast: right after the check
}
```

A `Cents` cannot be passed where a plain dollar `number` is expected by mistake, and the only way to build one is the function that checks it. With Zod, `z.string().brand<'ProductId'>()` gives the same type from a schema.

## satisfies for lookup tables

```ts
type Badge = { tone: 'success' | 'warning' | 'danger'; label: (available: number) => string };

const BADGES = {
  'in-stock': { tone: 'success', label: () => 'In stock' },
  'low-stock': { tone: 'warning', label: (n) => `Only ${n} left` },
  'out-of-stock': { tone: 'danger', label: () => 'Sold out' },
} satisfies Record<StockLevel, Badge>;
```

A missing level, an extra key or a wrong tone fails to compile, and `BADGES['low-stock'].tone` keeps its literal type `'warning'`. An annotation (`const BADGES: Record<StockLevel, Badge>`) would check too, but widen the values.

## Parsing unknown data with a guard

```ts
export function isProduct(value: unknown): value is Product {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === 'string' &&
    typeof v.name === 'string' &&
    Number.isInteger(v.priceCents) &&
    Number.isInteger(v.available)
  );
}

const data: unknown = await response.json();
if (!Array.isArray(data) || !data.every(isProduct)) throw new Error('Unexpected products payload');
```

For more than a few fields, or nested shapes, a schema library (`zod` in this pack) is shorter and keeps the type and the check in one place.

## Assertion function

```ts
export function assertDefined<T>(value: T, name: string): asserts value is NonNullable<T> {
  if (value === null || value === undefined) throw new Error(`${name} is required`);
}
```

## Result union for expected failures

```ts
export type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E };

export async function placeOrder(input: PlaceOrderInput): Promise<Result<Order, ApiError>> {
  const response = await fetch('/api/orders', { method: 'POST', body: JSON.stringify(input) });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) return { ok: false, error: toApiError(response.status, body) };
  return { ok: true, value: parseOrder(body) };
}
```

Callers must check `ok` before reading `value`, so the error path cannot be forgotten. Use it for failures the caller handles; keep throwing for bugs and outages.

## Generics: when they pay and when they do not

```ts
// Good: T links the input to the output.
export function byId<T extends { id: string }>(items: readonly T[]): Map<string, T> {
  return new Map(items.map((item) => [item.id, item]));
}

// Pointless: T appears once; this is just `(value: unknown) => string`.
function show<T>(value: T): string {
  return String(value);
}
```

## Typing a component's props

```tsx
type ButtonProps = React.ComponentPropsWithoutRef<'button'> & {
  variant?: 'primary' | 'secondary';
};

export function Button({ variant = 'primary', ...props }: ButtonProps) {
  return <button data-variant={variant} {...props} />;
}
```

Extend the native element's props instead of re-declaring `onClick`, `disabled` and the rest; use a union for variants, not a free `string`.
