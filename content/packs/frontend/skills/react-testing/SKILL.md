---
name: react-testing
description: >-
  Writes and fixes tests for React components, hooks and pages with Testing
  Library and the project's runner (Vitest or Jest): queries by role and
  label, user-event interactions, async UI with findBy and waitFor, network
  mocked at the boundary with MSW or a mocked API client, accessibility
  assertions with axe, renderHook for custom hooks, and the line between a
  component test and an end-to-end test. Uses only the test libraries the
  project already has and says which command runs the tests. Use it when
  someone asks to test a component, a hook or a page, when a component test
  fails or is flaky, or when reviewing React tests. Triggers: "test this
  component", "write tests for this React component", "React Testing
  Library", "vitest test for", "getByRole", "mock the API in my tests",
  "MSW", "jest-axe", "renderHook", "my component test is flaky".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# react-testing

## Result

- Test files that describe behavior the way a person sees it: what is on the screen, what they do, what changes. They follow the project's layout and runner, and use only libraries the project already has.
- In the answer: the behaviors covered, the exact command that runs the tests, and whether it ran here and what it gave. Never claim a test passes if it did not run.

## When

| Moment | What you do |
|---|---|
| SDD apply, a task with component or hook tests | Write the tests the task names (Red first), as `sdd-apply` and `code-generation` say |
| SDD tasks or design, Test Plan | Name the component tests per scenario, and leave the cross-page journeys to end-to-end tests |
| On request | Write, fix or review the tests the person names |

- **Not for:** journeys across pages with routing and a real backend (skill:playwright); pure functions that render nothing (a plain unit test in the same runner, no Testing Library); visual regression.
- **Accessibility:** role queries and axe catch part of the problems. The criteria and the verify gate are skill:accessibility-audit.

## 1. Read the test setup

Before writing a line, find out what the project has. Read the web package's `package.json`, the runner config and one existing test.

| Look for | Where | Why it matters |
|---|---|---|
| Runner | `vitest` or `jest` in devDependencies; `test` in `vite.config.*` or `vitest.config.*`; `jest.config.*` | Imports, mocks (`vi` or `jest`) and the command |
| DOM environment | `environment: 'jsdom'` or `'happy-dom'`; `testEnvironment` in Jest | Without one, `render` fails |
| Globals | `globals: true` in Vitest | Without it, import `describe`, `it`, `expect`, `vi` from `vitest`; see Cleanup |
| Setup files | `setupFiles` (Vitest, Jest) or `setupFilesAfterEnv` (Jest) | Matchers, MSW server, polyfills already wired |
| Libraries | `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `msw`, `jest-axe` or `vitest-axe` | Use only what is there |
| Layout | Co-located `X.test.tsx`, or `__tests__/` folders, or a `tests/` tree | Put the new file where its neighbors are |
| Providers | Router, data client, theme, i18n, store in `main.tsx` or the app root | A component that uses them needs them in the test |
| Aliases | `paths` in `tsconfig.json`, `resolve.alias` in the runner config | Import the way the neighbors import |

**What is missing:** use the fallback and suggest the library as a follow-up. Never add a dependency the plan does not name.

| Missing | Use instead | Suggest |
|---|---|---|
| `user-event` | `fireEvent` (it fires one event, not the full sequence a person makes) | `@testing-library/user-event` |
| `jest-dom` matchers | Plain assertions: `expect((button as HTMLButtonElement).disabled).toBe(true)`, `expect(screen.queryByText('Saved')).toBeNull()` | `@testing-library/jest-dom` |
| `msw` | Mock the project's API client module (`vi.mock('@/api/client')`), not `fetch` deep inside | `msw` |
| An axe integration | Role and name queries, plus the manual criteria of skill:accessibility-audit | `vitest-axe` or `jest-axe` |

**Cleanup:** Testing Library unmounts after each test only when the runner exposes a global `afterEach`. Vitest without `globals: true` does not, so renders pile up between tests and queries find duplicates. Add `afterEach(cleanup)` in the test file, or once in a setup file when the project has one.

## 2. Decide what to test

- **Behavior, not implementation.** Assert on what the person sees, hears and can do: text, roles, enabled or disabled controls, the callback called with the right arguments. Never on internal state, hook calls, class names or the component tree.
- **One behavior per test,** named as a sentence: `it('disables the plus button at the line limit')`.
- **Every state:** loading, empty, error with its recovery, success; the limits (the maximum, zero, a long name); disabled and pending controls.
- **From the spec:** in a change, each scenario `S-n` that a component test proves gets its test, named as test-spec.md says.
- **Do not duplicate:** logic that lives in a pure function gets a unit test there; the component test checks that the component uses it, once.

## 3. Queries

Pick the first one that works, in this order:

1. `getByRole('button', { name: 'Add to cart' })`: what assistive technology sees. Use `name` almost always.
2. `getByLabelText('Email')`: form fields.
3. `getByPlaceholderText`: only when there is no label (and that is an accessibility finding).
4. `getByText`: non-interactive text.
5. `getByDisplayValue`: the current value of a field.
6. `getByAltText`, `getByTitle`.
7. `getByTestId`: last resort, for elements with no accessible role or text.

- `getBy` throws when the element is missing; `queryBy` returns `null` (use it to assert absence); `findBy` waits for it (async).
- `screen` for queries; `within(region)` to scope to one card, row or dialog.
- If you cannot find an element by role or label, the component probably has an accessibility bug: report it instead of falling back to a test id.

## 4. Interactions and async

- With user-event: `const user = userEvent.setup()` before `render`, then `await user.click(...)`, `await user.type(...)`, `await user.keyboard('{Enter}')`, `await user.tab()`.
- Without it: `fireEvent.click(...)`, `fireEvent.change(input, { target: { value: '94105' } })`.
- **Async UI:** `await screen.findByRole(...)` for something that appears; `await waitFor(() => expect(...))` with only assertions inside, never side effects; `waitForElementToBeRemoved` for spinners.
- **No fixed sleeps.** Fake timers (`vi.useFakeTimers()`) only for debounce or timeouts; with user-event, pass `advanceTimers: vi.advanceTimersByTime` to `setup`.
- `act` warnings mean an update happened after the test stopped looking: await the UI change that causes it.

## 5. Network and providers

- **MSW when the project has it:** handlers at the network boundary, one server started in the setup file with `onUnhandledRequest: 'error'`, and `server.use(...)` in a test to override one response (an error, an empty list). The component and its data code run for real.
- **Without MSW:** mock the API client module and return resolved or rejected promises per test. Mock at the module boundary the components import, never the component's own hooks.
- **Providers:** a `renderWithProviders` helper in the project's test utilities when several tests need the same wrappers. A component with links needs a router: wrap it in `MemoryRouter` (with `initialEntries` for a route). A data client gets a fresh instance per test, with retries off.
- Recipes for each runner are in `references/setup-recipes.md`.

## 6. Hooks

- Test a hook through the component that uses it when it has only one user.
- A shared hook: `renderHook(() => useThing(args), { wrapper })`, then `act(() => result.current.doSomething())` and assert on `result.current`.
- A hook that reads browser storage: set `localStorage` before rendering, clear it after each test, and cover the broken value (invalid JSON) when the hook should survive it.

## 7. Accessibility in tests

- Role and name queries already check that controls have a role and an accessible name.
- With an axe integration: `expect(await axe(container)).toHaveNoViolations()` once per meaningful state (closed, open, with errors). It catches only part of the failures; it does not replace the review of skill:accessibility-audit.
- Keyboard paths matter: `await user.tab()` and assert focus with `expect(document.activeElement).toBe(element)` (or `toHaveFocus()` with jest-dom).

## 8. Component test or end-to-end test

| Question | Component test (this skill) | End-to-end (skill:playwright) |
|---|---|---|
| What runs | One component or page, in a simulated DOM | The built app in a real browser |
| Network | Mocked at the boundary | A real or seeded backend; mocked only when there is none |
| Speed and count | Fast; many | Slow; few |
| Good for | States, validation, limits, callbacks, accessible names | The critical journeys across pages: buy, sign in, pay |
| Not good for | Routing across pages, real layout, browser APIs jsdom lacks | Every edge case of one component |

When a behavior needs layout, scrolling, real focus management across pages or a real browser API, it belongs in an end-to-end test.

## 9. Flaky tests

Common causes and fixes are in `references/setup-recipes.md`, Flaky tests: shared state between tests (storage, module mocks, MSW handlers not reset), missing cleanup, fixed waits, dates and time zones (fix the date: pass it in, or `vi.setSystemTime`), random data without a seed, and assertions inside `waitFor` that pass by luck.

## 10. Run them

- Take the command from `.exo/context.md`, test-spec.md or the package scripts (for example `npm test --workspace <package>`, or `npm test --workspace <package> -- <file>` for one file). To call the runner directly, use the installed one: `npm exec --no -- vitest run <file>`. Never `npx vitest` or `npx jest`: without `node_modules`, npx downloads and runs a package instead of failing.
- When you cannot run commands in this session, say so, give the exact command for the person, and review the test by reading: imports, providers, cleanup, every query against the component's real text and roles.
- A test you write first in Red must fail for the expected reason: an assertion, not an import error.

## Return

```markdown
Tests: packages/storefront/src/components/CartPanel.test.tsx (new)
- shows the empty message when there are no lines
- disables the plus button at the line limit
- removes a line with its Remove button
Command: npm test --workspace @acme/storefront (not run in this session: no shell for npm)
Notes: wrapped in MemoryRouter (the panel renders links); afterEach(cleanup), since Vitest runs without globals.
Follow-ups: @testing-library/user-event is not installed; fireEvent is used instead.
```

## Record

Inside a change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "react-testing", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"react-testing"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Only libraries the project has; what is missing is a follow-up, not a new dependency.
- [ ] Queries by role and label first; no test id where a role or label works.
- [ ] Each test checks one behavior the person can see, including loading, empty, error and limits where they apply.
- [ ] Providers, cleanup and mocks are set up and reset between tests.
- [ ] No fixed sleeps; async UI awaited with `findBy` or `waitFor`.
- [ ] The exact test command is in the answer, with its result or "not run".
