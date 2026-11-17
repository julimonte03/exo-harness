---
name: frontend-design
description: >-
  Designs and builds distinctive, production-grade UI on top of the
  project's own components and design tokens: pages, screens, components,
  dashboards and landing pages with a clear visual direction, hierarchy,
  typography, spacing, color, responsive layout, motion, microcopy and every
  state (loading, empty, error, success). Neutral style by default; an
  optional .exo/brand.json supplies the brand where the project has no
  tokens, and any new visual style waits for the person's approval. It is the
  conditional skill of the SDD apply phase when a change touches UI. Use it
  when someone asks to build, restyle or polish a screen or a component, to
  design an empty, loading or error state, or to make a UI look less generic.
  Triggers: "design this page", "build a landing page", "make this look
  better", "polish the UI", "restyle this component", "dashboard layout",
  "empty state", "make it look professional", "visual hierarchy", "use our
  design tokens".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: write-code
---

# frontend-design

## Result

- UI code that looks deliberate and belongs to the product: built from the project's components and tokens, with every state designed, responsive, at the accessibility baseline, and with no new visual style the person did not approve.
- A short design note in the answer: the direction, the components and tokens used, anything new and whether it was approved, the states covered, and what still needs a look in a browser.

## When

| Moment | Trigger | What you do |
|---|---|---|
| SDD apply (Conditional, `.exo/shared/phase-skill-map.md`) | The change touches UI | Build the task's UI with these rules |
| SDD design | The design has a screen or a component | Give `sdd-design` the layout, the components reused, the states and any new token, marked as needing approval |
| On request | Build, restyle or polish a UI | The same rules, in the files the person names |

- **Not for:** the accessibility audit and its gate (skill:accessibility-audit), although the baseline below applies here; component structure and state (skill:frontend-patterns); Tailwind specifics (`tailwind-4`); an independent review of a UI change (skill:judge-frontend).
- **When this skill is not installed,** the phase map's inline criteria apply: reuse the project's components and design tokens, and add no new visual style without the person's approval. Everything below builds on those two rules.

## 1. Where the style comes from

In this order:

1. **The project's design system:** its components (a folder, a component library), its tokens (a token package, CSS custom properties, a theme object, the Tailwind theme), and the fonts and icons already in use. These win.
2. **`.exo/brand.json`, when it exists:** the organization's brand (colors, typography, logo, tone). Use it for what the project does not define yet, and for the tone of the copy. Its shape is the `executive-style.md` contract of the `design` pack; without that pack, read the keys the file has and ask when one is unclear. If it disagrees with the tokens in the code, the code wins: tell the person about the difference, and never rewrite tokens to match it on your own.
3. **The neutral default** (`references/neutral-default.md`), when there is neither: a system font stack, a neutral gray scale, one accent, a 4-pixel spacing scale, with its contrast already checked.

- Read the token values when they are in the repo. When they come from a package whose source is not there (you see only the import), use the token names the code already uses and list the visual check as pending.
- **A new visual style** is any color, font, size, spacing value, radius, shadow, icon set or component variant that those sources do not have. It needs the person's approval: in an SDD change it is written in design.md; otherwise ask before adding it, and meanwhile use the closest existing token.
- **Never hard-code a value where a token exists.**

## 2. Take stock before you design

1. The screens closest to the one you are building: layout, spacing, headings, buttons, forms, and how they show loading and errors.
2. The component catalog (Storybook or similar) when the project has one.
3. **The styling approach:** CSS files, CSS Modules, CSS-in-JS, utility classes (with Tailwind, also load `tailwind-4`), the class naming (BEM, utilities), and where the classes the components use are defined. If the styles are not in the repo (a shared package, a stylesheet loaded from elsewhere), say so and follow the same class conventions; never introduce a second styling system.
4. Breakpoints, dark mode and reduced-motion handling that already exist.

## 3. Choose a direction

Before writing code, write three to five lines:

- who uses the screen and their main task;
- the one thing the screen must make obvious;
- the density: a data-heavy tool or an airy page;
- one distinctive element that serves the purpose: a confident type scale on a landing page, a strong highlight of the key figure on a dashboard, an empty state that invites the first action.

Distinctive within the brand, never against it. Avoid the generic look:

- every section centered, the same card grid repeated;
- gradients, glows and glass effects with no root in the brand;
- cards inside cards, borders and shadows on everything;
- emoji as icons, lorem ipsum, "Welcome to our platform" copy;
- light gray text for style, below the contrast minimum;
- more than two typefaces, or several accents competing.

## 4. Layout and hierarchy

- One primary action per view; secondary actions look secondary.
- Build hierarchy with size, weight and space before color.
- A type scale from the base size with one ratio (for example 1.25); body text around 16 px, lines of 45 to 75 characters, line height 1.4 to 1.6.
- Spacing only from the scale. Related items sit closer than unrelated ones, and the rhythm repeats.
- Align to a grid: shared left edges, consistent gutters.
- **Responsive:** mobile first; breakpoints where the content breaks, not at device names. Check at 320, 768 and 1280 px wide and at 200% zoom; at 320 CSS px nothing scrolls sideways except data tables and maps.
- Images and media keep their dimensions or aspect ratio, so the page does not jump while they load.

## 5. Color

- From tokens, by role (text, muted text, surface, border, accent, danger, success, warning), not raw hues.
- **Contrast:** 4.5:1 for text, 3:1 for large text (24 px, or 19 px bold), and 3:1 for the boundaries of controls and for focus indicators.
- Never color alone to carry meaning: pair it with text or an icon.
- Dark mode only when the project has it; then both themes come from tokens.

## 6. Every state

| State | Design it so that |
|---|---|
| Loading | A skeleton with the shape and size of the content; nothing jumps when data arrives; long waits say what is happening |
| Empty | It says why it is empty (first use, or no results for a filter) and offers one clear action |
| Error | It says what happened and what to do, offers a retry, and keeps what the person typed |
| Success | It confirms the result and points to the next step |
| Partial | What loaded is usable; what failed says so in place |
| Disabled | It is clear why, or the control is hidden when it never applies |
| Long content | Long names, big numbers and many items wrap or truncate without breaking the layout; the full text stays reachable |

Copy patterns and examples for each state are in `references/states-and-copy.md`.

## 7. Microcopy

- Buttons say what happens, with a verb: "Place order", "Save changes", not "Submit" or "OK".
- Errors give the cause and the way out, without blame: "Card number is not valid. Check the digits and try again."
- Sentence case, the same term for the same thing everywhere, money and dates formatted with the project's helpers.
- The tone comes from `.exo/brand.json` when it defines one; otherwise plain and friendly.

## 8. Motion

- Only to explain a change: something appears or leaves, a state changes, an action gets feedback.
- 150 to 250 ms for small elements, up to about 400 ms for large ones; ease out when entering, ease in when leaving.
- Animate `transform` and `opacity`, not layout properties.
- Respect `prefers-reduced-motion`: remove the motion that is not essential.

## 9. Accessibility baseline

Native, semantic elements (`button`, `a`, `label`, headings in order, landmarks); a visible focus indicator at 3:1; targets of at least 24 by 24 px; the contrast above; text alternatives for meaningful images; nothing that traps the keyboard. The full criteria, and the `accessibility_review` gate in verify, are skill:accessibility-audit.

## 10. Build it

1. Reuse the existing components; compose them before you create new ones. A new variant of a shared component needs approval, like any new style.
2. Apply tokens through the project's mechanism: CSS custom properties, the theme object, utility classes.
3. Keep the markup semantic and the styles where the project keeps them, with its class naming.
4. Review your result with `references/visual-review.md`, and list what only a browser can confirm.
5. Run the project's lint, typecheck and tests. When you cannot run them here, give the exact commands.

## Return

```markdown
Direction: a calm invoice list where the amount due and the due date stand out; one accent, for the primary action only.
Built: src/components/EmptyResults.tsx (new), used in src/pages/Invoices.tsx; reuses Button and the status badge classes.
Tokens: colors.textMuted, colors.accent, space.4 from @acme/tokens (values not in the repo: check them in a browser).
New style: none. (Or: a "subtle" Button variant, waiting for approval; the secondary variant is used meanwhile.)
States: loading skeleton of eight rows, empty with "Show paid invoices", error with retry.
Check in a browser: the layout at 320 px, the focus ring on the new button, the contrast of the muted text.
```

## Record

Inside a change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "frontend-design", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"frontend-design"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The style comes from the project's components and tokens, then `.exo/brand.json`, then the neutral default; nothing hard-coded where a token exists.
- [ ] Every new visual style is approved, or listed as waiting for approval with the fallback used.
- [ ] Loading, empty, error, success and long content are designed where they apply.
- [ ] The accessibility baseline holds: semantic elements, visible focus, contrast, target size.
- [ ] No second styling system and no new dependency the plan does not name.
- [ ] The design note is in the answer, with what still needs a browser check.
