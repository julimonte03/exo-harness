# Playwright config, auth and CI

Adapt the paths, ports and scripts to the project. Read its `package.json` scripts and dev server config before you copy a value.

## A starting config

```ts
// playwright.config.ts, next to the web package's package.json
import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.E2E_PORT ?? 5173);
const baseURL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: `npm run dev -- --port ${PORT} --strictPort`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
```

- **`webServer`** starts the app before the tests. Use the project's own script (`dev`, or `preview` after a build, which is closer to production). When the app needs a backend, start it too: `webServer` accepts an array of servers.
- **`E2E_BASE_URL`** lets CI or a person point the suite at an app that is already running (a preview deploy), and skips `webServer`.
- **More browsers:** add `firefox` and `webkit` projects when the product supports them; keep one browser for the quick local loop.
- A dev server that proxies `/api` to a backend port needs that backend running; otherwise mock those requests (`page.route`) and say so.

## Keep the unit runner out of e2e

```ts
// vite.config.ts or vitest.config.ts
import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
});
```

Jest: `testPathIgnorePatterns: ['/node_modules/', '/e2e/']`. And keep Playwright from picking up component tests: `testDir: './e2e'` does that.

## Authentication once, reused

```ts
// e2e/auth.setup.ts
import { expect, test as setup } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('sign in', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.E2E_USER_EMAIL ?? '');
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('button', { name: 'Account' })).toBeVisible();
  await page.context().storageState({ path: authFile });
});
```

```ts
// in playwright.config.ts
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
    dependencies: ['setup'],
  },
],
```

- The variables are set locally (a git-ignored env file the person keeps) and as secrets of the CI job. A test account only, never a real person's.
- Signing in through the API (a request fixture that posts to the login endpoint and saves the cookies) is faster than the UI; keep one UI sign-in test for the form itself.
- Tests that need another role get their own setup and storage file.

## Data helpers

```ts
// e2e/fixtures.ts (data part)
import { test as base } from '@playwright/test';

type Order = { id: string };

export const test = base.extend<{ newOrder: Order }>({
  newOrder: async ({ request }, use) => {
    const response = await request.post('/api/test-support/orders', {
      data: { email: `buyer-${Date.now()}@example.com` },
    });
    const order = (await response.json()) as Order;
    await use(order);
    await request.delete(`/api/test-support/orders/${order.id}`);
  },
});
```

The endpoints are examples: use the API the project already has, or a seed script, and never a production environment.

## Network mocking

```ts
test.beforeEach(async ({ page }) => {
  await page.route('**/api/products', (route) =>
    route.fulfill({ json: [{ id: 'p-1', name: 'Mug', priceCents: 1200, available: 3 }] }),
  );
});
```

- Mock only what the journey cannot get from a test backend, and keep the payloads in the shapes of the API types (import the type, so a change in the API breaks the mock at compile time).
- `route.fulfill({ status: 503, json: { error: 'down' } })` covers the error states that are hard to produce for real.
- `page.route` applies to the page's requests only; requests made by the test with `request` are not mocked.

## CI, host-agnostic

Steps for any CI system (the YAML syntax is the host's):

1. Use a Node image of the version in `engines` or `.nvmrc`, or the official Playwright image with the same version as `@playwright/test` (it has the browsers and their system libraries).
2. `npm ci` at the workspace root.
3. `npx playwright install --with-deps chromium`, unless the image already has the browsers.
4. Start the backend when the journeys need it (a service container with a seeded database), or rely on `webServer`.
5. `npx playwright test` from the web package, with `CI=true`.
6. Always keep `playwright-report/` and `test-results/` as artifacts (on failure too), for a week or so.

Sharding a slow suite: run `npx playwright test --shard=<i>/<n> --reporter=blob` in `n` parallel jobs, collect the `blob-report/` folders, and `npx playwright merge-reports --reporter html <folder>` in a final job.

## Debugging commands

| Command | Use |
|---|---|
| `npx playwright test --ui` | Run and watch tests, with time travel through each step |
| `npx playwright test <file>:<line> --debug` | Step through one test with the inspector |
| `npx playwright test --repeat-each=10 <file>` | Reproduce a flaky test |
| `npx playwright show-trace <trace.zip>` | Open a trace from CI |
| `npx playwright codegen <url>` | Record steps to discover locators; rewrite the result into page objects |
