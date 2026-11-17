# ARIA patterns for custom widgets

What the W3C ARIA Authoring Practices Guide (APG) expects from the widgets that show up most in diffs, summarized in this skill's words. When a widget is not here or the case is unusual, read its pattern in the APG. Cite a failure with the WCAG criterion it breaks (usually 2.1.1, 2.4.3 or 4.1.2) and the pattern name: `WCAG 2.2 SC 4.1.2 Name, Role, Value (A); APG Tabs pattern`.

## Rules before any pattern

1. **Native first.** A `button`, `a href`, `input`, `select`, `details` or `dialog` brings its role, keyboard behavior and states for free. A custom widget is justified only when no native element does the job.
2. **No ARIA is better than wrong ARIA.** A role promises a keyboard behavior; a role without that behavior is worse than none.
3. **Do not override native semantics** (`role="button"` on a heading) and do not repeat them (`role="button"` on a `button`).
4. **Every interactive element is focusable and has a name:** visible text, `aria-labelledby`, or `aria-label` when there is no visible text. The name contains the visible label (2.5.3).
5. **States follow the UI:** `aria-expanded`, `aria-selected`, `aria-checked`, `aria-pressed`, `aria-current`, `aria-disabled` change when the UI changes.
6. **Never hide focusable content** with `aria-hidden="true"`; use `inert` or remove it from the tab order too.

## Patterns

| Pattern | Roles and states | Keyboard | Common failures |
|---|---|---|---|
| Button | native `button`; or `role="button"`, `tabindex="0"`; toggle with `aria-pressed` | Enter and Space activate | `div` with a click handler only; Space not handled on a custom button |
| Link | native `a` with `href` | Enter follows it | `a` without `href` used as a button; a button styled as a link that navigates |
| Disclosure (show/hide) | a button with `aria-expanded` and `aria-controls` pointing at the panel | Enter and Space toggle | the toggle is a heading or a `div`; `aria-expanded` never changes |
| Accordion | each header is a button inside a heading, with `aria-expanded`; panels optionally `role="region"` | Enter and Space toggle; arrow keys between headers are optional | headers not focusable; the whole header row is a `div` |
| Dialog (modal) | `role="dialog"` (or native `dialog`), `aria-modal="true"`, a name from its title | focus moves inside on open; Tab cycles inside; Escape closes; focus returns to the opener | focus stays behind the dialog; the page behind is still reachable; no way to close with the keyboard |
| Alert dialog | `role="alertdialog"`, name and description | as Dialog; focus on the safest action | destructive action focused by default |
| Drawer or side panel | a modal drawer is a Dialog; a non-modal one is a region with a name | as Dialog when modal | treated as modal visually but focus can leave it |
| Tabs | `tablist`, `tab` with `aria-selected` and `aria-controls`, `tabpanel` labelled by its tab | Tab enters the tab list on the active tab; arrow keys move between tabs; Home and End | every tab in the tab order; arrow keys not handled; no `aria-selected` |
| Menu button | a button with `aria-haspopup="menu"` and `aria-expanded`; the menu `role="menu"` with `menuitem` | Enter, Space or Down open it and focus the first item; arrows move; Escape closes and returns focus | a site navigation built as `role="menu"` (use a list of links instead) |
| Combobox (autocomplete) | input `role="combobox"` with `aria-expanded`, `aria-controls` and `aria-activedescendant`; popup `listbox` with `option` | Down opens and moves; Enter selects; Escape closes | suggestions not announced; focus jumps into the list; no visible focus on the active option |
| Listbox | `listbox` with `option` and `aria-selected`; `aria-multiselectable` when it applies | arrows move; Space selects in multi-select; type-ahead optional | options built from `div` with click only |
| Radio group | native radios in a `fieldset` with a `legend`; or `radiogroup` with `radio` and `aria-checked` | Tab enters the group on the checked radio; arrows move and select | each option a separate Tab stop; ratings and segmented controls built from `span` |
| Checkbox | native checkbox; or `role="checkbox"` with `aria-checked` (`mixed` for partial) | Space toggles | toggle implemented on a `div` with no state |
| Switch | `role="switch"` with `aria-checked`, or a native checkbox | Space toggles (Enter optional) | state only shown by color (1.4.1) |
| Slider | `role="slider"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax` and `aria-valuetext` when the number is not meaningful | arrows change by a step; Page Up and Page Down by more; Home and End | drag only (2.5.7); value not announced |
| Spinbutton (stepper) | native number input; or `role="spinbutton"` with value attributes; increment and decrement buttons with names | Up and Down change the value | the plus and minus controls are unnamed icons or `div` elements |
| Tooltip | `role="tooltip"`, referenced by `aria-describedby` from its trigger | appears on focus and hover; Escape dismisses | only on hover; disappears when the pointer moves onto it (1.4.13); holds essential content |
| Carousel | a region with a name; slide picker as tabs or buttons; a pause control | rotation stops on focus and hover; a visible pause button | auto-rotation with no pause (2.2.2) |
| Table and grid | data tables use `table`, `th` with `scope`, a caption; `grid` only for interactive cells | a grid moves with arrow keys | layout built with `div` and no table semantics; `grid` role on a plain data table |
| Breadcrumb | a `nav` with a name, a list of links, `aria-current="page"` on the last | links | the current page not marked |
| Landmarks | `header`, `nav`, `main`, `aside`, `footer`; one `main`; several `nav` each with a name | skip link to `main` | no `main`; every region unnamed |
| Alert and status | `role="alert"` for urgent messages, `role="status"` or `aria-live="polite"` for the rest; the container exists before the message is inserted | focus does not move | the live region is created together with its text, so nothing is announced |

## Focus management

- **Open:** move focus to the first meaningful element of a dialog, drawer or menu, or to the dialog itself with its title as name.
- **Close:** return focus to the element that opened it; if that element is gone, to a logical place nearby.
- **Route change in a single-page app:** move focus to the new page's main heading, or announce the new title.
- **Removed content:** when the focused element disappears (an item deleted from a list), move focus to the next item or to the list.
