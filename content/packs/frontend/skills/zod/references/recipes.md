# Zod 4 recipes

Worked examples for `zod`. Names follow a small shop; adapt them to the project, and to Zod 3 syntax when that is what it has (`references/v3-to-v4.md`).

## A shared contract

```ts
// packages/shared/src/schemas.ts
import { z } from 'zod';
import { MAX_CART_LINES, MAX_QTY_PER_LINE } from './limits.ts';

export const OrderLineSchema = z.object({
  productId: z.string().min(1),
  quantity: z.int().min(1).max(MAX_QTY_PER_LINE),
});

export const PlaceOrderSchema = z
  .object({
    email: z.string().trim().toLowerCase().pipe(z.email({ error: 'Enter a valid email address' })),
    promoCode: z.string().trim().toUpperCase().min(1).optional(),
    lines: z.array(OrderLineSchema).min(1, { error: 'Your cart is empty' }).max(MAX_CART_LINES),
  })
  .refine((order) => new Set(order.lines.map((l) => l.productId)).size === order.lines.length, {
    error: 'Each product can appear only once',
    path: ['lines'],
  });

export type PlaceOrderInput = z.infer<typeof PlaceOrderSchema>;
```

- The limits come from the module that already defines them, so the schema and the business rules cannot drift.
- The cross-field rule sets `path`, so the error lands on `lines`.
- Both the browser and the server import `PlaceOrderSchema` and `PlaceOrderInput`.

## An Express handler

```ts
import { z } from 'zod';
import { PlaceOrderSchema } from '@shop/shared';

router.post('/', async (req, res) => {
  const result = PlaceOrderSchema.safeParse(req.body);
  if (!result.success) {
    throw new HttpError(422, 'Invalid order', z.flattenError(result.error).fieldErrors);
  }
  res.status(201).json(await orders.placeOrder(result.data));
});
```

A CommonJS server loads the shared schema the way it loads the rest of the shared package (`require('@shop/shared')`; Node 22.12 and later can `require` an ES module without top-level `await`). Never copy the schema into the server.

A small middleware keeps handlers short when many routes validate:

```ts
export const validateBody =
  <S extends z.ZodType>(schema: S) =>
  (req: Request, _res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return next(new HttpError(422, 'Invalid input', z.flattenError(result.error).fieldErrors));
    }
    req.body = result.data;
    next();
  };
```

## Query strings and route params

```ts
const ListQuery = z.object({
  page: z.coerce.number().int().min(1).default(1),
  status: z.enum(['pending', 'paid', 'shipped', 'delivered', 'cancelled']).optional(),
});

const query = ListQuery.parse(req.query); // inside a handler whose errors become 400
```

Query values arrive as strings: coerce them, and set the limits that protect the database (a maximum page size).

## A form in React

```tsx
const [errors, setErrors] = useState<Partial<Record<keyof PlaceOrderInput, string>>>({});

function handleSubmit(values: z.input<typeof PlaceOrderSchema>) {
  const result = PlaceOrderSchema.safeParse(values);
  if (!result.success) {
    const fields = z.flattenError(result.error).fieldErrors;
    setErrors(Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, v?.[0]])));
    return;
  }
  void submitOrder(result.data);
}
```

With `react-hook-form` already in the project, pass the schema through `zodResolver(PlaceOrderSchema)` instead. Either way, the server parses again.

## A response from another service

```ts
const RateSchema = z.object({ currency: z.string().length(3), rate: z.number().positive() });

const response = await fetch(url, { signal });
if (!response.ok) throw new Error(`Rates service answered ${response.status}`);
const rate = RateSchema.parse(await response.json());
```

`parse` here, because a malformed answer is an outage to report, not a user mistake to explain.

## Environment variables

```ts
const Env = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DATABASE_URL: z.url(),
  ADMIN_API_TOKEN: z.string().min(32),
  ENABLE_CACHE: z.stringbool().default(false),
});

export const config = Env.parse(process.env);
```

If parsing fails, the process stops at start-up with the names of the missing or invalid variables. Never log the values of secret variables.

## A tagged union

```ts
const PaymentEvent = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('authorized'), amountCents: z.int().positive() }),
  z.object({ kind: z.literal('declined'), reason: z.string() }),
]);
```

The inferred type is a discriminated union, so a `switch` on `kind` is exhaustive in TypeScript too.

## Testing a schema

```ts
it('rejects repeated products on the lines field', () => {
  const result = PlaceOrderSchema.safeParse({
    email: 'buyer@example.com',
    lines: [{ productId: 'p1', quantity: 1 }, { productId: 'p1', quantity: 2 }],
  });
  expect(result.success).toBe(false);
  expect(z.flattenError(result.error!).fieldErrors.lines).toEqual(['Each product can appear only once']);
});
```

One valid example per schema, and one failing example per refinement and limit, asserting the path and the message.
