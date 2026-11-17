# Visual self-review

Go through this list before you call a UI done. What only a running browser can confirm goes to "Check in a browser" in the design note.

## Fit with the product

- [ ] Every component that exists in the project is reused; nothing is a near-copy of an existing one.
- [ ] Colors, sizes, spacing, radii, shadows and motion come from tokens; no raw value where a token exists.
- [ ] Class names and file locations follow the project's convention.
- [ ] Any new style is approved, or marked as waiting for approval with the fallback used.

## Hierarchy

- [ ] Squinting at the screen, the most important thing is the first thing you see.
- [ ] One primary action per view, visibly stronger than the rest.
- [ ] Headings follow the type scale, in order (one `h1`, no skipped levels).
- [ ] Related items are grouped by space; unrelated ones are separated.

## Typography

- [ ] At most two typefaces, two or three weights.
- [ ] Body text around 16 px, lines of 45 to 75 characters, line height 1.4 to 1.6.
- [ ] Numbers in tables use tabular figures and align right.

## Layout

- [ ] Shared left edges and consistent gutters.
- [ ] At 320 px wide: no sideways scrolling (except data tables and maps), nothing overlaps, targets stay at least 24 by 24 px.
- [ ] At 768 and 1280 px: the layout uses the space without stretching lines past about 75 characters.
- [ ] At 200% zoom: everything still reachable and readable.
- [ ] Images and media keep their dimensions while loading; no layout shift.

## Color and contrast

- [ ] Text 4.5:1 (large text 3:1); control boundaries and focus indicators 3:1, against their real background.
- [ ] Color never carries meaning alone.
- [ ] In dark mode, when the project has it: every state checked in both themes.

## Interaction

- [ ] Hover, focus-visible, active, disabled and pending states exist for every control.
- [ ] The focus order follows the reading order; focus is never lost after an action (a dialog closing, an item removed).
- [ ] Motion explains a change, lasts 150 to 400 ms, and stops with reduced motion.

## States and copy

- [ ] Loading, empty (first use or no results), error with a way out, success, partial and long content are designed where they apply.
- [ ] Buttons say what they do; errors say what happened and what to do.
- [ ] No placeholder copy, no lorem ipsum, no emoji standing in for icons.
