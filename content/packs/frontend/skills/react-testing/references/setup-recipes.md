# React testing recipes

Copy only what the project needs, and adapt names and paths to its layout. Every snippet assumes the library it uses is already installed; if it is not, it is a follow-up for the person.

## Vitest

The `test` block lives in `vite.config.ts` (with `defineConfig` from `vitest/config`) or in `vitest.config.ts`:

```ts
test: {
  environment: 'jsdom',            // or 'happy-dom'
  setupFiles: ['./src/test/setup.ts'],
  // globals: true,                // only if the project already uses it
}
```

A setup file, with only the lines whose library is installed:

```ts
// src/test/setup.ts
import '@testing-library/jest-dom/vitest';   // jest-dom matchers
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './server';           // MSW, see below

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup();                 // needed when globals are off
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());
```

Without a setup file, put `afterEach(cleanup)` at the top of each test file that renders more than once.

## Jest

- `testEnvironment: 'jsdom'` (the `jest-environment-jsdom` package) and `setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts']`.
- In the setup file: `import '@testing-library/jest-dom';`. Jest exposes `afterEach` globally, so Testing Library cleans up by itself.
- `jest.mock`, `jest.fn` and `jest.spyOn` replace `vi.mock`, `vi.fn` and `vi.spyOn`. Path aliases need `moduleNameMapper`.

## Render with providers

```tsx
// src/test/render.tsx
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router';

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', ...options }: RenderOptions & { route?: string } = {},
) {
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
  );
  return render(ui, { wrapper: Wrapper, ...options });
}
```

Import `MemoryRouter` from the package the app already uses (`react-router` or `react-router-dom`). Add the other providers of the app root (data client with `retry: false`, theme, i18n) the same way.

## Network with MSW (v2)

```ts
// src/test/server.ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const handlers = [
  http.get('*/api/products', () =>
    HttpResponse.json([{ id: 'p-1', name: 'Mug', priceCents: 1200, available: 3 }]),
  ),
];

export const server = setupServer(...handlers);
```

Override one response in a test:

```ts
server.use(http.get('*/api/products', () => HttpResponse.json({ error: 'down' }, { status: 503 })));
expect(await screen.findByRole('alert')).toHaveTextContent('Could not load products');
```

Node's `fetch` does not resolve relative URLs against the simulated page, so a client whose base is relative (`/api`) fails in tests. Give it an absolute base in the test environment (the variable the client already reads, for example a `VITE_*` value in the runner's `env`), or mock the client module instead. The `*/` prefix in the handlers above matches the path on any origin.

## Without MSW: mock the API client

```ts
import { vi } from 'vitest';
import { fetchProducts } from '@/api/client';

vi.mock('@/api/client', () => ({ fetchProducts: vi.fn() }));

it('shows the error when products cannot load', async () => {
  vi.mocked(fetchProducts).mockRejectedValue(new Error('Request failed with 503'));
  render(<Catalog />);
  expect((await screen.findByRole('alert')).textContent).toContain('503');
});
```

`vi.mock` is hoisted above the imports; a factory that needs variables from the test file uses `vi.hoisted`. Reset mocks between tests (`vi.clearAllMocks()` in `afterEach`, or `clearMocks: true` in the config).

## A form, end to end inside the component

```tsx
it('shows the field error and does not submit', async () => {
  const onSubmit = vi.fn();
  const user = userEvent.setup();
  render(<SignupForm onSubmit={onSubmit} />);

  await user.type(screen.getByLabelText('Email'), 'not-an-email');
  await user.click(screen.getByRole('button', { name: 'Create account' }));

  expect(screen.getByText('Enter a valid email address')).toBeInTheDocument();
  expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  expect(onSubmit).not.toHaveBeenCalled();
});
```

Without user-event and jest-dom: `fireEvent.change(input, { target: { value: 'not-an-email' } })`, `fireEvent.click(button)`, `expect(screen.getByText(...)).toBeTruthy()` and `expect(input.getAttribute('aria-invalid')).toBe('true')`.

## A hook

```ts
import { act, renderHook } from '@testing-library/react';

it('caps a line at the maximum quantity', () => {
  const { result } = renderHook(() => useBasket());
  act(() => result.current.add({ id: 'p-1', name: 'Mug', priceCents: 1200 }, 99));
  expect(result.current.items[0].quantity).toBe(10);
});
```

## Accessibility with axe

- jest-axe: `import { axe, toHaveNoViolations } from 'jest-axe'; expect.extend(toHaveNoViolations);`, then `expect(await axe(container)).toHaveNoViolations();`.
- vitest-axe: follow the package's setup; it adds the same `toHaveNoViolations` matcher.
- Run it for each state that changes the markup: closed and open, empty and with errors. jsdom does not compute layout, so contrast and target size are not checked here.

## Flaky tests

| Symptom | Usual cause | Fix |
|---|---|---|
| Passes alone, fails in the suite | State shared between tests: storage, module mocks, MSW handlers, a singleton store | Reset in `afterEach`; create stores per test |
| "Found multiple elements" | Renders from earlier tests still mounted | `afterEach(cleanup)` when globals are off |
| Fails on some days or machines | Real dates or time zones | Pass the date in, or `vi.setSystemTime(new Date(2030, 0, 15))` |
| Fails now and then on CI | Fixed waits, or an assertion that runs before the update | `findBy` or `waitFor`; never `setTimeout` in a test |
| `act` warning | An update after the test stopped waiting (a promise that resolves late) | Await the UI change it causes |
| Random failures with generated data | Random values without a seed | Fixed values, or a seeded generator |
| A `waitFor` that sometimes passes too early | Side effects inside the callback, or a query that matches the old state | Only assertions inside; assert on the new state |
