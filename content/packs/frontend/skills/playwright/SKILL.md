---
name: playwright
description: >-
  Writes, refactors and debugs end-to-end browser tests with Playwright: the
  Page Object Model, selector priority (role, label, text, then test id),
  web-first assertions and auto-waiting instead of fixed sleeps, fixtures,
  test data isolated per test, saved authentication state, network mocking
  when there is no test backend, traces for flaky tests, and the CI job.
  Exploring the running app through a browser MCP server is optional; without
  one it works from the routes, the components and the existing tests. Use it
  when someone asks for an end-to-end or browser test of a user journey, wants
  to set up e2e tests in a web project, or has a flaky or broken e2e test.
  Triggers: "e2e test", "end-to-end test", "browser test", "Playwright",
  "page object", "test the checkout flow in a real browser", "flaky e2e
  test", "playwright.config", "set up e2e tests".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: read-write
---

# playwright

## Result

- End-to-end specs for user journeys, with page objects and fixtures in the project's layout, that run in parallel without depending on each other, locally and in CI.
- In the answer: the journeys covered, how the data is isolated, the commands to run them, and whether they ran here.

## When

| Moment | What you do |
|---|---|
| SDD design or tasks, Test Plan | Name an end-to-end test for each critical journey of the spec; leave component states to component tests |
| SDD apply | Write the e2e specs the task names |
| On request | Write, refactor or debug e2e tests; set up Playwright in a web project |

- **Not for:** the states, validation and limits of one component (skill:react-testing); pure logic (unit tests); load testing.
- **Few and valuable:** an e2e test is slow and costly to keep. Cover the journeys that lose money or users when they break (sign in, search, add to cart, pay), not every branch.

## 1. Read what exists

1. `@playwright/test` in the web package's or the root's devDependencies; `playwright.config.*`; the e2e folder and its specs, page objects and fixtures.
2. The app: its routes (router config or `app/` and `pages/` folders), the components on the journey (their labels, roles and button texts), and the API client (which requests each step makes).
3. How the app starts and with which data: the dev or preview script, the backend it calls (dev proxy, `baseURL` variables), seed scripts, a test database.
4. The CI file, to see where a new job fits.

**Without Playwright in the project:** adding it is a new dependency. In an SDD change, the plan must name it; outside one, the person agrees first. Write the config and the specs, and give the person the install commands to run: `npm install --save-dev @playwright/test` (in the web package; `--workspace <package>` from a workspace root) and `npx playwright install chromium`. Never run an install yourself.

**Exploring the running app:** a browser MCP server can help to see the real roles and texts, but it is optional and an organization may block MCP servers. Without one, read the components: never use a selector you have not seen in the code or in the running app.

## 2. Layout

Follow the project's layout when it has one. Otherwise, next to the web package's `package.json`:

```text
playwright.config.ts
e2e/
  fixtures.ts            test.extend with page objects and data helpers
  pages/
    catalog.page.ts
    cart.page.ts
  checkout.spec.ts       one file per journey
```

- `testDir: './e2e'` in the config.
- **Keep the unit runner out of `e2e/`:** Vitest's default include matches `*.spec.ts`. Add `exclude: [...configDefaults.exclude, 'e2e/**']` to its `test` block (`configDefaults` from `vitest/config`), or `testPathIgnorePatterns` in Jest.
- Ignore the outputs in `.gitignore`: `test-results/`, `playwright-report/`, `blob-report/`, `playwright/.auth/`.

The full config, the auth setup and the CI steps are in `references/config-and-ci.md`.

## 3. Selectors

In this order, the same as the people and assistive technology that use the page:

1. `page.getByRole('button', { name: 'Place order' })`
2. `page.getByLabel('Email')`
3. `page.getByPlaceholder(...)`: only when there is no label
4. `page.getByText('Your cart is empty.')`
5. `page.getByAltText(...)`, `page.getByTitle(...)`
6. `page.getByTestId('order-total')`: last resort, with a `data-testid` the team agrees to keep

- Never CSS classes, XPath, generated ids or `nth-child` chains: they break with every restyle.
- Scope with chaining: `page.getByRole('article').filter({ hasText: 'Mug' }).getByRole('button', { name: 'Add to cart' })`.
- An element you cannot reach by role or label is usually an accessibility bug: report it (skill:accessibility-audit) instead of hiding it behind a test id.

## 4. Page objects

One class per page or large region, with locators as fields and methods named after what the person does:

```ts
import type { Locator, Page } from '@playwright/test';

export class CartPage {
  readonly drawer: Locator;
  readonly checkoutLink: Locator;

  constructor(private readonly page: Page) {
    this.drawer = page.getByRole('complementary', { name: 'Shopping cart' });
    this.checkoutLink = this.drawer.getByRole('link', { name: 'Checkout' });
  }

  line(name: string): Locator {
    return this.drawer.getByRole('listitem').filter({ hasText: name });
  }

  async remove(name: string) {
    await this.line(name).getByRole('button', { name: 'Remove' }).click();
  }
}
```

- **Assertions live in the specs.** Page objects expose locators; the spec says what must be true.
- No waits, sleeps or test data inside page objects.
- Keep them thin: a method per user intention, not per click.

## 5. Fixtures

Inject page objects and data with `test.extend`, so every spec starts the same way:

```ts
import { test as base } from '@playwright/test';
import { CartPage } from './pages/cart.page';
import { CatalogPage } from './pages/catalog.page';

export const test = base.extend<{ catalog: CatalogPage; cart: CartPage }>({
  catalog: async ({ page }, use) => { await use(new CatalogPage(page)); },
  cart: async ({ page }, use) => { await use(new CartPage(page)); },
});
export { expect } from '@playwright/test';
```

A fixture that creates data (a user, an order) cleans it up after `use`. Expensive setup that tests can share safely goes in a worker-scoped fixture.

## 6. Waiting

- **Web-first assertions:** `await expect(locator).toBeVisible()`, `toHaveText`, `toHaveURL`, `toHaveCount`. They retry until the timeout.
- Actions (`click`, `fill`) wait for the element to be visible, enabled and stable.
- **Never `page.waitForTimeout`.** Not `networkidle` as a general wait either. Wait for what the person would see, or for one specific response with `page.waitForResponse` when nothing visible changes.
- Do not read a value and assert on it later (`expect(await locator.textContent()).toBe(...)`): it does not retry. Assert on the locator.

## 7. Test data and isolation

- **Each test owns its data:** create it in a fixture or through the API before the test, with unique names, and remove it after. No test depends on another one or on the order they run in; `fullyParallel: true` should pass.
- **A test backend is best:** the real API with a seeded database, started by the config's `webServer` or by CI.
- **No test backend:** mock at the browser boundary with `page.route('**/api/products', route => route.fulfill({ json: [...] }))`. Say in the answer which journeys run against mocks: they no longer prove the contract with the API.
- Browser storage starts empty in each test's context; seed it with `storageState` or `page.addInitScript` when a journey needs a saved cart or a session.
- Synthetic data only: `example.com` emails, placeholder names, the published test cards of the payment provider.

## 8. Authentication

- A setup project signs in once through the UI or the API and saves `storageState` to `playwright/.auth/user.json`; the other projects reuse it (`references/config-and-ci.md`).
- Credentials come from environment variables (`process.env.E2E_USER_EMAIL`, `process.env.E2E_USER_PASSWORD`), set locally and as CI secrets. Never in code, fixtures or the repo, and never in the answer.
- The `.auth` folder is in `.gitignore`.

## 9. Flaky and broken tests

1. Reproduce: `npx playwright test <file> --repeat-each=10`, or with `--workers=1` to rule out shared data.
2. Read the trace (`trace: 'on-first-retry'` in the config, then `npx playwright show-trace <trace.zip>`) or open `--ui`.
3. Fix the cause, never the symptom: a fixed wait becomes a web-first assertion; shared data becomes per-test data; a selector that matches two elements gets scoped; an animation gets awaited or disabled for tests.
4. Retries in CI hide flakiness: report a test that passes only on retry as flaky (the HTML report marks it).

## 10. CI

Host-agnostic steps for the project's CI:

1. Install dependencies from the lockfile (`npm ci`).
2. Install the browsers the config uses: `npx playwright install --with-deps chromium`, or use the official Playwright container image of the same version.
3. Start the app and its backend, or let `webServer` do it.
4. `npx playwright test` with `CI=true` (two retries, `forbidOnly`).
5. Keep `playwright-report/` and `test-results/` as job artifacts, also when the job fails.
6. Shard when the suite is slow: `--shard=1/4` per parallel job, then merge the blob reports.

## 11. Run them

- Locally: `npx playwright test` (from the folder with the config), `--ui` to explore, `--debug` to step through, `npx playwright show-report` for the last report.
- When you cannot run commands in this session, say so, give the exact commands, and review by reading: every locator against the component's real role and accessible name, every step against the route it lands on, and the data each test needs.

## Return

```markdown
E2E: packages/storefront/e2e/checkout.spec.ts (new), page objects in e2e/pages/, fixtures in e2e/fixtures.ts
- adds a product from the catalog and sees it in the cart
- an empty checkout form shows the email error
Data: GET /api/products mocked with page.route (no test backend in the repo); the journey does not prove the API contract.
Setup: playwright.config.ts (testDir ./e2e, webServer npm run dev); Vitest now excludes e2e/**.
Run (not run here): npm install --save-dev @playwright/test; npx playwright install chromium; npx playwright test
```

## Record

Inside a change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "playwright", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"playwright"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every locator uses a role, label or text seen in the code or the running app; test ids only as a last resort.
- [ ] No `waitForTimeout`, no reading values before asserting; web-first assertions only.
- [ ] Each test creates and cleans its own data and runs in any order; mocks are named in the answer.
- [ ] Page objects hold locators and intentions; assertions are in the specs.
- [ ] No credentials in code; auth state and reports are git-ignored; the unit runner skips `e2e/`.
- [ ] No dependency installed by you; the commands are in the answer, with their result or "not run".
