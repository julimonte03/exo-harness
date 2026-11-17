---
name: frontend-engineering
description: >-
  The frontend engineering role for TypeScript and React web apps, and the
  router of the frontend pack: it reads the web package's stack (React
  version, framework, build tool, styling, state and data libraries, tests),
  applies the role's principles (component boundaries, where state lives,
  data fetching and its states, Core Web Vitals, client-side security,
  accessibility) and decides which skill of the pack to load for the task.
  It is the stack router that the SDD design and apply phases load when the
  frontend pack is installed. Use it at the start of any frontend task in a
  web package (a new screen, component, hook, form or client data flow, a
  frontend refactor) or to plan the frontend side of a design; not for server
  code. Triggers: "frontend task", "add a feature to the web app", "how
  should I structure this in React", "plan the frontend side", "frontend
  conventions", "frontend architecture", "Core Web Vitals", "which frontend
  skill should I use".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: read-write
---

# frontend-engineering

## Result

- A short frontend plan for the task: the stack with its evidence (`path:line`), the skills of the pack to load, the files to touch, where the state lives, and the risks for performance, security and accessibility.
- In design, that plan feeds the frontend parts of design.md, which `sdd-design` writes. In apply, the code follows it and the skills it loaded.
- The router writes no file of its own.

## When

| Moment | What you do |
|---|---|
| design, as the stack router (`.exo/shared/phase-skill-map.md`) | Plan the frontend part (section 4); `sdd-design` writes it |
| apply, as the stack router | Load the skills each task needs, follow the conventions, run the checks (section 5) |
| On request | Any frontend task in a web package |

- **Scope:** the web packages the task touches. In a monorepo, server packages (an Express or Nest API, workers) follow `.exo/context.md` and their own stack pack, not this router.
- **Not for:** a change with no frontend file.

## 1. Read the stack

Read these, keep the `path:line` of each fact, and stop as soon as you know enough for the task:

1. **`.exo/context.md`**, when it exists: its commands and conventions win over everything below.
2. **The manifests:** the root `package.json` (workspaces) and the web package's `package.json`:
   - `react` and `react-dom` versions;
   - framework or build tool (Next.js, React Router framework mode, Remix, Vite, a custom bundler);
   - router, styling (Tailwind, CSS Modules, CSS-in-JS, plain CSS, a design-token package), data and state libraries, schema library (zod), forms;
   - test runner and libraries (Vitest or Jest, Testing Library, MSW, axe), end-to-end tool (Playwright, Cypress), lint config;
   - the scripts: dev, build, test, lint, typecheck.
3. **`tsconfig.json`:** `strict`, path aliases (`@/*`), module resolution.
4. **The folders:** components, hooks, pages or routes, the API client, styles, tests. Then two neighbor files of the kind you are about to write.

**Version gates:** React 19 features only with `react` 19 or later; Server Components only with a framework that supports them (a client-only Vite app has none). skill:react-patterns has the table.

## 2. Route to the skills

| The task involves | Load |
|---|---|
| Components, custom hooks, where state lives, data fetching and its states, forms, error boundaries, folders | skill:frontend-patterns |
| Server and Client Components, Actions, `use()`, `useOptimistic`, transitions, Suspense, a React upgrade | skill:react-patterns |
| A new or restyled screen, visual quality, design tokens, empty and error states | skill:frontend-design |
| Types: unions, generics, narrowing, strict-mode errors | `typescript` |
| Validating untrusted data: API responses, form input, browser storage, environment variables | `zod` |
| Styling with Tailwind CSS 4 | `tailwind-4` |
| Component and hook tests | skill:react-testing |
| End-to-end tests of user journeys | skill:playwright |
| Accessibility criteria, or an audit of a UI | skill:accessibility-audit |
| A dependency or lockfile change | skill:security-scan-node |
| A review of a TypeScript or JavaScript diff | `typescript-reviewer` |

- **Load only what the task needs:** usually one or two skills besides this router. Inside an SDD phase, the map's limit of five skills per delegation applies (`.exo/shared/phase-skill-map.md`); the phase's own choices come first.
- **Skip what the stack does not have:** no Tailwind, no `tailwind-4`; no zod and the plan does not add it, no `zod` (validate by hand at the boundary instead).
- **A skill that is not installed** degrades as `.exo/shared/skill-resolver.md` says: `frontend/<skill> not installed — applying inline criteria`, then apply the principles of section 3, and record it.

## 3. The role's principles

The short version; details and checklists are in `references/performance-and-security.md`.

**Components**
- One job per component; compose with `children` before adding flags; reuse the project's components and design system first.
- Typed props, no `any`; follow the neighbors' naming, exports and folders.

**State**
- Name the kind of each piece of state: local UI, shared by siblings, URL, server cache, form, app-wide. Each kind has one home (skill:frontend-patterns, section 4).
- Derive values during render instead of storing and syncing them.

**Data**
- One API client; components do not call `fetch` directly when a client exists.
- Every request has loading, empty, error and success states; it is cancelled or ignored when stale; independent requests start together.
- Untrusted data is validated at the boundary.

**Performance and Core Web Vitals** (at the 75th percentile of real visits)
- LCP (Largest Contentful Paint) at most 2.5 s, INP (Interaction to Next Paint) at most 200 ms, CLS (Cumulative Layout Shift) at most 0.1.
- Split routes and heavy screens with `lazy`; weigh every new dependency against its bundle size; give images and media their dimensions; keep long work off the main thread during interactions.

**Client-side security**
- No HTML from untrusted data without sanitizing it; URLs from data are checked before `href` or `src`.
- Everything in the bundle is public: build-time variables exposed to the client (`VITE_*`, `NEXT_PUBLIC_*`) never hold secrets.
- No long-lived tokens or personal data in browser storage, URLs, logs or analytics (`.exo/shared/data-protection.md`). Hiding a control is not authorization: the server checks it too.

**Accessibility**
- Native semantic elements, labels, visible focus, keyboard paths. skill:accessibility-audit has the criteria and the verify gate.

## 4. In design

Give `sdd-design` the frontend content of design.md:

| design.md section | Frontend content |
|---|---|
| Architecture Overview | The component tree of each screen: what is reused (`path:line`) and what is new |
| Modules / Files | Each component, hook, style and test file, in the project's folders |
| Data Shapes | Props of new components, API types, the state shape and the home of each piece |
| Sequence Of Operations | User action, state change, request, and the states the screen shows on the way |
| Error Handling | Loading, empty, error and recovery for every component that loads or sends data |
| Test Plan | Component tests per scenario (skill:react-testing); end-to-end tests for the critical journeys (skill:playwright) |
| Risks & Mitigations | Bundle and Web Vitals risks, client-side security, accessibility |

A new visual style, a new dependency or a React upgrade is a decision for the person, written in the design.

## 5. In apply

- Follow `code-generation` and the skills you loaded. Touch only the files of the task.
- **Checks:** typecheck, lint and tests with the exact commands of `.exo/context.md` or of the web package's scripts (for example `npm test --workspace <package>`, `npx tsc --noEmit -p <package dir>`). When you cannot run a command in this session, give it to the person and say it did not run; never claim it passed.
- A dependency the plan does not name is a follow-up, not code.

## Return

When the person asks for a plan, or before a frontend task that spans several files:

```markdown
## Frontend plan: saved filters on the invoice list
- Stack: react ^18.3.1 (apps/portal/package.json:12), Vite client-only app, TypeScript strict (apps/portal/tsconfig.json:7), Vitest with Testing Library, plain CSS with tokens from @acme/tokens; no Tailwind, no zod.
- Skills: frontend-patterns (URL state, a hook), react-testing (tests). Not loaded: react-patterns (nothing React 19 here), tailwind-4 (no Tailwind).
- Files: src/pages/Invoices.tsx (toolbar), src/hooks/useInvoiceFilters.ts (new), src/hooks/useInvoiceFilters.test.ts (new).
- State: the filters live in the URL search params, so a saved view is a link; the list stays server data.
- Risks: re-filtering a long list on every keystroke (defer it); the filter text is untrusted (parse it).
- Checks: npm test --workspace @acme/portal; npx tsc --noEmit -p apps/portal (not run in this session).
```

## Record

Inside a change, a phase that runs inline records the skill and each skill it loaded before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list them in the envelope notes and the orchestrator records them.

```bash
exo change record <change> --add capabilities_used '{"name": "frontend-engineering", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"frontend-engineering"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The stack facts have their `path:line`; `.exo/context.md` was followed when present.
- [ ] Only the skills the task needs were loaded, and the ones skipped have a reason.
- [ ] State, data states, Web Vitals, client-side security and accessibility were considered for this task.
- [ ] No new dependency, visual style or React upgrade without the person or the plan.
- [ ] The check commands are in the answer, with their result or "not run".
