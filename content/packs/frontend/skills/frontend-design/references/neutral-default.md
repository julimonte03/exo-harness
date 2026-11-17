# The neutral default

Use it only when the project has no design system and there is no `.exo/brand.json`. It is quiet on purpose: the content and one accent carry the page. Adding it to a project is a new visual style, so the person approves it first.

## Tokens as CSS custom properties

```css
:root {
  /* Color: light theme */
  --color-bg: #ffffff;
  --color-surface: #f5f7f9;
  --color-text: #1d2125;
  --color-text-muted: #5b6470;
  --color-border: #d5dbe1;          /* decoration only: dividers, card edges */
  --color-border-strong: #7d8794;   /* boundaries of inputs and controls */
  --color-accent: #0a58a8;
  --color-on-accent: #ffffff;
  --color-danger: #b3261e;
  --color-success: #187a35;
  --color-warning: #946200;
  --color-focus: #0a58a8;

  /* Type */
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.25rem;    /* 20px */
  --text-xl: 1.5625rem;  /* 25px */
  --text-2xl: 1.953rem;  /* 31px */
  --text-3xl: 2.441rem;  /* 39px */
  --leading-body: 1.5;
  --leading-heading: 1.2;

  /* Space: 4px steps */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;

  /* Shape and depth */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgb(16 24 32 / 0.08);
  --shadow-md: 0 4px 12px rgb(16 24 32 / 0.12);

  /* Motion */
  --duration-fast: 150ms;
  --duration-base: 220ms;
  --ease-out: cubic-bezier(0.2, 0, 0, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f1318;
    --color-surface: #171c22;
    --color-text: #e8ecf0;
    --color-text-muted: #96a0ab;
    --color-border: #2a3139;
    --color-border-strong: #6b7480;
    --color-accent: #4c95f0;
    --color-on-accent: #0f1318;
    --color-danger: #f07167;
    --color-success: #4cc271;
    --color-warning: #e0a83a;
    --color-focus: #4c95f0;
  }
}

@media (prefers-reduced-motion: reduce) {
  :root { --duration-fast: 0ms; --duration-base: 0ms; }
}
```

Add the dark theme only when the product needs one.

## Contrast, already checked

| Pair | Ratio | Enough for |
|---|---|---|
| text on bg | 16.2:1 | all text |
| text on surface | 15.1:1 | all text |
| text-muted on bg | 6.0:1 | all text |
| text-muted on surface | 5.6:1 | all text |
| accent on bg (links) | 7.1:1 | all text |
| on-accent on accent (buttons) | 7.1:1 | all text |
| danger on bg | 6.5:1 | all text |
| success on bg | 5.4:1 | all text |
| warning on bg | 5.2:1 | all text |
| border-strong on bg | 3.6:1 | control boundaries (3:1) |
| border on bg | 1.4:1 | decoration only, never the only edge of a control |
| dark: text on bg | 15.7:1 | all text |
| dark: text-muted on bg | 7.0:1 | all text |
| dark: accent on bg | 6.1:1 | all text |
| dark: border-strong on bg | 3.9:1 | control boundaries (3:1) |

Recompute any pair you change, with the formula in `accessibility-audit/references/wcag-22-checklist.md` in the skills folder.

## Usage rules

- **One accent,** for the primary action, links and focus. Danger, success and warning only for status, always with text.
- **Type:** the system stack, two weights (400 and 600). Headings use the scale; body text stays at `--text-base`.
- **Space:** components inside use `--space-2` to `--space-4`; between sections `--space-8` to `--space-16`.
- **Depth:** borders for structure, `--shadow-sm` for raised cards, `--shadow-md` only for overlays (menus, dialogs).
- **Focus:** `outline: 2px solid var(--color-focus); outline-offset: 2px;` on `:focus-visible`, never removed.
- **Breakpoints:** start from 320 px; add one around 48rem and one around 80rem when the content needs them; cap reading width around 70ch.

## A starting component

```css
.button {
  font: 600 var(--text-base) / 1 var(--font-sans);
  min-height: 2.75rem;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: var(--color-accent);
  color: var(--color-on-accent);
  transition: background-color var(--duration-fast) var(--ease-out);
}
.button--secondary {
  background: var(--color-bg);
  color: var(--color-text);
  border-color: var(--color-border-strong);
}
.button:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

A disabled control is exempt from the contrast minimum, but it still needs a reason the person can find.
