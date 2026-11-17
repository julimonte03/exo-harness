# From Tailwind 3 to Tailwind 4

Use this when a project still on Tailwind 3 moves to 4, or when old class names show up in a Tailwind 4 project. An upgrade is its own change, approved by the person, on a clean branch.

## Setup

| Tailwind 3 | Tailwind 4 |
|---|---|
| `@tailwind base; @tailwind components; @tailwind utilities;` | `@import "tailwindcss";` |
| `tailwind.config.js` with `theme.extend` | `@theme { ... }` in the main stylesheet; a JavaScript config still loads with `@config "./tailwind.config.js";` during a transition |
| `content: [...]` globs | Automatic source detection; `@source "<path>";` for extra paths, `@source not "<path>";` to exclude |
| `tailwindcss` as a PostCSS plugin, plus `autoprefixer` and `postcss-import` | `@tailwindcss/postcss` (imports and prefixes are built in), or `@tailwindcss/vite`, or `@tailwindcss/cli` |
| `plugins: [require('@tailwindcss/typography')]` | `@plugin "@tailwindcss/typography";` |
| `darkMode: 'class'` | `@custom-variant dark (&:where(.dark, .dark *));` |
| `prefix: 'tw-'` with `tw-flex` | `@import "tailwindcss" prefix(tw);` with `tw:flex` |
| `theme()` in CSS | CSS variables (`var(--color-brand-600)`); `theme(--breakpoint-xl)` only inside media queries |
| `container` options in the config | `@utility container { margin-inline: auto; padding-inline: 1rem; }` |
| `addUtilities` and `addComponents` in JavaScript plugins | `@utility` in CSS |
| `@layer utilities { .x { ... } }` for custom utilities | `@utility x { ... }` |

## Renamed utilities

| Tailwind 3 | Tailwind 4 |
|---|---|
| `shadow-sm` | `shadow-xs` |
| `shadow` | `shadow-sm` |
| `drop-shadow-sm` | `drop-shadow-xs` |
| `drop-shadow` | `drop-shadow-sm` |
| `blur-sm` | `blur-xs` |
| `blur` | `blur-sm` |
| `backdrop-blur-sm` | `backdrop-blur-xs` |
| `backdrop-blur` | `backdrop-blur-sm` |
| `rounded-sm` | `rounded-xs` |
| `rounded` | `rounded-sm` |
| `outline-none` | `outline-hidden` (the new `outline-none` sets `outline-style: none`) |
| `ring` (3px) | `ring-3` (`ring` is now 1px) |

## Removed utilities

| Tailwind 3 | Tailwind 4 |
|---|---|
| `bg-opacity-50`, `text-opacity-50`, `border-opacity-50` and the rest | Opacity modifiers: `bg-black/50`, `text-brand-600/75` |
| `flex-shrink-0`, `flex-grow` | `shrink-0`, `grow` |
| `overflow-ellipsis` | `text-ellipsis` |
| `decoration-slice`, `decoration-clone` | `box-decoration-slice`, `box-decoration-clone` |

## Changed behavior

| What | Tailwind 3 | Tailwind 4 | What to do |
|---|---|---|---|
| Default border color | `gray-200` | `currentColor` | Add the color to every `border` that relied on the default (`border border-gray-200`), or set a base style |
| Default ring | 3px, `blue-500` | 1px, `currentColor` | `ring-3 ring-blue-500` where the old look is wanted |
| Placeholder color | `gray-400` | current text color at 50% | Set `placeholder:text-...` where it matters |
| Buttons | `cursor: pointer` | `cursor: default` (the browser default) | Add `cursor-pointer` or a base style if the project wants it |
| `hover:` | Always | Only on devices that can hover | Never hide information behind hover |
| `space-x-*`, `space-y-*` | Margin on `> * + *` | Margin on `> :not(:last-child)` | Prefer `gap` in flex and grid layouts |
| Variant stacking | Right to left | Left to right | Reverse stacked variants such as `first:*:pt-0` to `*:first:pt-0` |
| CSS variables in arbitrary values | `bg-[--brand-color]` | `bg-(--brand-color)` | Rewrite; prefer a theme token when one exists |
| Important modifier | `!flex` | `flex!` (the prefix form still works, deprecated) | Use the suffix in new code |
| Colors | `rgb` palette | `oklch` palette | Small visual shifts; compare screens after upgrading |
| Gradients | `bg-gradient-to-r` | `bg-linear-to-r`, plus `bg-radial` and `bg-conic` | Use the new names in new code |

## Steps

1. Check the browser targets: Tailwind 4 needs Safari 16.4+, Chrome 111+ and Firefox 128+.
2. On a clean branch, with the person's agreement, run the upgrade tool (`npx @tailwindcss/upgrade`, Node 20 or later). It updates dependencies, moves the config into CSS and renames classes.
3. Review its diff: the theme in `@theme`, the plugins as `@plugin`, the dark mode variant, the renamed classes.
4. Fix what the tool cannot know: borders that relied on the default color, rings, dynamic class names built from strings, classes in places it did not scan.
5. Replace `tailwind-merge` 2.x with 3.x if the project uses it.
6. Build, run the visual or component tests, and compare the main screens in light and dark mode.
