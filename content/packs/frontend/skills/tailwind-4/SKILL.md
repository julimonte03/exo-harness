---
name: tailwind-4
description: >-
  Styles components with Tailwind CSS 4: the CSS-first configuration
  (@import "tailwindcss", @theme, @custom-variant, @utility, @source), design
  tokens as theme variables that generate the utilities, a cn() helper for
  conditional and merged classes, variants as maps of complete class names,
  dark mode through semantic tokens, and no hex colors, var() calls in
  className or arbitrary values outside the theme. Knows what changed from
  Tailwind 3 and how to upgrade. Use it when you style or restyle components
  in a project that uses Tailwind, add a color, font or spacing token, set up
  dark mode, clean up class names, or move a project from Tailwind 3 to 4.
  Triggers: "style this component with Tailwind", "Tailwind classes",
  "add a theme color", "dark mode with Tailwind", "clean up these classes",
  "conditional classes", "upgrade to Tailwind 4", "tailwind.config to @theme".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# tailwind-4

## Result

- Components styled only with utilities that the project's theme generates: no hex or `rgb()` colors in markup, no `var()` inside `className`, no arbitrary values (`[...]`) where a theme value exists or should exist.
- Conditional classes built with the project's `cn()` helper, and variants as maps of complete class strings.
- A new design token, when one is needed, added once to `@theme` (after the person approves it) and used through its utility.
- The build or the project's checks ran, named with their result; or the exact command and what you checked by hand.

## When

- You style or restyle components in a project with Tailwind CSS 4 (`tailwindcss` 4.x in `package.json`, `@import "tailwindcss"` in a stylesheet).
- You add or change theme tokens, dark mode, custom utilities or variants.
- The project is on Tailwind 3 and the person asks to upgrade (`references/v3-to-v4.md`).
- **Not for:** a project without Tailwind: follow its own styling (CSS modules, plain CSS, CSS-in-JS) and do not add Tailwind without the person's approval; the visual design itself (`frontend-design`); accessibility audits (skill:accessibility-audit); component logic (skill:typescript, `react-patterns`).
- **Precedence:** `.exo/context.md`, the project's stylesheet and its existing components win over the defaults here. `frontend-engineering`, the stack router of this pack, sends styling work here.

## 1. Know the setup

Read before writing a class:

1. **Version and integration:** `tailwindcss` in `package.json`, and how it runs: `@tailwindcss/vite`, `@tailwindcss/postcss` or `@tailwindcss/cli`. A `tailwind.config.js` without `@config` in the CSS, or `@tailwind base;` directives, means Tailwind 3: do not mix syntaxes.
2. **The main stylesheet:** the file with `@import "tailwindcss";`. Read every `@theme` block: those variables are the colors, fonts, spacing, radii, shadows and breakpoints you may use.
3. **Helpers:** a `cn()` function (usually `lib/utils.ts` or `lib/cn.ts`), `class-variance-authority` or `tailwind-variants` for component variants, a prefix (`@import "tailwindcss" prefix(tw);` makes every class `tw:...`).
4. **Dark mode:** the default (`prefers-color-scheme`) or a `@custom-variant dark` for a class or data attribute.
5. Two or three existing components that look like the one you will touch: spacing scale, radius, how states are styled.

## 2. Theme variables, not literals

Tokens live in `@theme`, and each namespace generates utilities:

```css
@import "tailwindcss";

@theme {
  --color-brand-600: oklch(0.55 0.2 260);
  --color-success: oklch(0.62 0.17 150);
  --font-display: "Inter", sans-serif;
  --radius-card: 0.75rem;
  --breakpoint-3xl: 120rem;
}
```

This gives `bg-brand-600`, `text-success`, `font-display`, `rounded-card` and the `3xl:` variant, and exposes each value as a CSS variable (`var(--color-success)`) for plain CSS.

- **No hex, `rgb()` or named colors in markup:** `text-[#15803d]` and `style={{ color: '#15803d' }}` become `text-success`. If the color is not in the theme, propose the token (name and value) and add it to `@theme` once the person approves; never sneak in a one-off.
- **No `var()` in `className`:** `bg-[var(--color-brand-600)]` and `bg-(--color-brand-600)` become `bg-brand-600`. The parenthesis form is only for a runtime variable that is not a theme token (`bg-(--avatar-color)` set inline per user).
- **Arbitrary values only outside the theme's reach:** a one-off layout value with no token and no reuse (`grid-cols-[1fr_auto]`), with a short comment when it is not obvious. Never for colors, font sizes, spacing or radii that the design system defines.
- **Removing defaults:** `--color-*: initial;` inside `@theme` drops the default palette when the project wants only its own colors.
- **Tokens that point at other variables** go in `@theme inline` (section 5).

## 3. Class names in components

- **Complete class names only.** Tailwind finds classes by scanning the source as text; `bg-${tone}-600` is never generated. Map values to full strings:

  ```tsx
  const toneClass = {
    'in-stock': 'text-success',
    'low-stock': 'text-warning',
    'out-of-stock': 'text-danger',
  } satisfies Record<StockLevel, string>;
  ```

- **Conditional and overridable classes with `cn()`:** `clsx` for conditions plus `tailwind-merge` (3.x for Tailwind 4) so a later class wins over a conflicting earlier one:

  ```ts
  import { clsx, type ClassValue } from 'clsx';
  import { twMerge } from 'tailwind-merge';

  export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
  }
  ```

  ```tsx
  <span className={cn('rounded-full px-2 text-sm', toneClass[level], className)} />
  ```

  If the project has no `cn()`, adding it (and its two dependencies) is a dependency change: propose it and wait for approval; until then, use template strings of complete classes.
- **Variants:** a map like the one above, or `cva` when the project already uses it. Do not introduce `cva` for one component.
- **Accept `className`** on reusable components and merge it last with `cn()`, so callers can adjust spacing without forking the component.
- **Order** classes as the project's Prettier plugin (`prettier-plugin-tailwindcss`) sorts them, when it has one.
- **Extract components, not `@apply` chains.** Repeated markup becomes a component. `@apply` is for styling markup you do not control (third-party widgets, rendered Markdown) and base element styles; in CSS modules and Vue or Svelte `<style>` blocks, add `@reference "<path to main stylesheet>";` first so `@apply` sees the theme.

## 4. States, motion and accessibility

- Every interactive element keeps a visible focus style: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600`, or the project's ring utility. Never remove the outline without a replacement (`outline-hidden` keeps an outline in forced-colors mode; `outline-none` removes it completely).
- `hover:` only applies on devices that can hover, so never put information only in a hover state.
- `motion-safe:` and `motion-reduce:` around animations; `sr-only` for text meant only for screen readers.
- `disabled:`, `aria-expanded:`, `aria-[invalid=true]:` and `data-[state=open]:` variants style real states instead of extra classes.
- Contrast between text and background tokens must meet WCAG 2.2 AA; check new token pairs with skill:accessibility-audit.

## 5. Dark mode

- **Semantic tokens** keep markup free of `dark:` on every element. Define the raw values per mode and map them in `@theme inline`:

  ```css
  :root {
    --surface: oklch(0.99 0 0);
    --on-surface: oklch(0.21 0.01 260);
  }
  .dark {
    --surface: oklch(0.18 0.01 260);
    --on-surface: oklch(0.96 0 0);
  }
  @theme inline {
    --color-surface: var(--surface);
    --color-on-surface: var(--on-surface);
  }
  ```

  Then `bg-surface text-on-surface` works in both modes.
- **The `dark:` variant** follows `prefers-color-scheme` by default. For a toggle, declare it once: `@custom-variant dark (&:where(.dark, .dark *));` (or a `[data-theme=dark]` selector, matching how the app sets the mode).
- Use `dark:` directly only for one-off differences that no semantic token covers.

## 6. Custom utilities, variants and sources

- `@utility` for a reusable utility the theme cannot express: `@utility content-auto { content-visibility: auto; }`. It works with every variant (`hover:content-auto`).
- `@custom-variant` for a project-wide state: `@custom-variant theme-contrast (&:where([data-contrast=more] *));`.
- `@source "../node_modules/@acme/ui";` when classes live in a package the automatic detection skips (it ignores `.gitignore`d folders and `node_modules`); `@source not "./legacy";` to exclude a folder.
- `@plugin "@tailwindcss/typography";` loads a plugin the project already depends on.

## 7. Upgrading from Tailwind 3

Only when the person asks: it touches the build, the config and many class names. The renamed utilities, the changed defaults and the steps are in `references/v3-to-v4.md`.

- The official upgrade tool is `npx @tailwindcss/upgrade`; it downloads a package and rewrites files. Propose it, run it only with the person's agreement on a clean branch, then review its diff.
- Tailwind 4 targets Safari 16.4+, Chrome 111+ and Firefox 128+. If the project must support older browsers, say so before upgrading: stay on 3.4.

## 8. Check

Run the project's build or dev check from `.exo/context.md` or `package.json` scripts (`npm run build`, the lint with its Tailwind plugin, visual or component tests), and report each exact command with its result.

- **Never install** Tailwind, a plugin or a helper without the person's approval.
- **When you cannot run the build:** say so, give the exact command, and check by hand: every class you wrote exists in the default theme or the project's `@theme`, no hex color, `var()` in `className` or dynamic class name is left, every changed interactive element keeps a focus style, and dark mode tokens are defined for both modes. A quick search helps: `#[0-9a-fA-F]{3,8}` and `-\[` inside `className` attributes.

## Return

```text
Tailwind 4.1 with @tailwindcss/vite; theme in packages/web/src/index.css; cn() in packages/web/src/lib/cn.ts.
Changed: packages/web/src/components/StockBadge.tsx (tone map with text-success, text-warning, text-danger instead of hex values).
Tokens: none added. Checks: npm run build --workspace @shop/web: not run (no shell); classes checked against @theme by hand.
```

## Record

Inside an SDD change, the phase that loaded this skill records it; inline, before the phase envelope (`.exo/shared/capability-attribution.md`). A subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "tailwind-4", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"tailwind-4"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You read the main stylesheet's `@theme` and the neighboring components before writing classes.
- [ ] No hex, `rgb()` or named colors, no `var()` in `className`, no arbitrary values where a token exists.
- [ ] No dynamic class names; variants are maps of complete strings; conditions go through `cn()`.
- [ ] New tokens were approved by the person and added once to `@theme`.
- [ ] Interactive elements keep a visible focus style; dark mode works through tokens.
- [ ] No package was added without approval; the build ran or is listed as not run with what you checked by hand.
