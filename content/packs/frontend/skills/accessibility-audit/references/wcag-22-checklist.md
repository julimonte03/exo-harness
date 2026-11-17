# WCAG 2.2, levels A and AA: what to look for in code

Every success criterion of WCAG 2.2 at levels A and AA (31 at A, 24 at AA), by number, name and level, with what to check in a diff. The checks are this skill's own reading of each criterion, not the normative text: when a case is borderline, read the criterion and its Understanding document in the W3C recommendation. `2.2` marks the criteria new in WCAG 2.2.

Cite a failure as `WCAG 2.2 SC <number> <name> (<level>)`, for example `WCAG 2.2 SC 1.4.3 Contrast (Minimum) (AA)`.

## 1. Perceivable

| SC | Name (level) | Check in the changed UI |
|---|---|---|
| 1.1.1 | Non-text Content (A) | Images, icons and charts that carry meaning have a text alternative; decorative ones are hidden from assistive technologies (`alt=""`, `aria-hidden`); icon-only controls have a name |
| 1.2.1 | Audio-only and Video-only (Prerecorded) (A) | Recorded audio has a transcript; silent video has a text or audio alternative |
| 1.2.2 | Captions (Prerecorded) (A) | Recorded video with sound has captions |
| 1.2.3 | Audio Description or Media Alternative (Prerecorded) (A) | Visual information in video is described, in audio or in a text alternative |
| 1.2.4 | Captions (Live) (AA) | Live video with sound has captions |
| 1.2.5 | Audio Description (Prerecorded) (AA) | Recorded video has audio description of what is only visible |
| 1.3.1 | Info and Relationships (A) | Structure shown visually is in the markup: headings, lists, tables with headers, labels tied to fields, groups (`fieldset` and `legend`) |
| 1.3.2 | Meaningful Sequence (A) | The reading order in the DOM matches the order that makes sense; CSS reordering does not scramble it |
| 1.3.3 | Sensory Characteristics (A) | Instructions do not rely only on shape, position, size or sound ("press the round button on the right") |
| 1.3.4 | Orientation (AA) | Nothing locks the screen to portrait or landscape unless it is essential |
| 1.3.5 | Identify Input Purpose (AA) | Fields that ask for the user's own data have the right `autocomplete` value (name, email, postal code, card fields) |
| 1.4.1 | Use of Color (A) | Color is never the only way to convey state, errors, links within text or chart series |
| 1.4.2 | Audio Control (A) | Sound that plays on its own for more than 3 seconds can be paused or muted |
| 1.4.3 | Contrast (Minimum) (AA) | Text against its background: at least 4.5:1, or 3:1 for large text (see Contrast below) |
| 1.4.4 | Resize Text (AA) | Text can grow to 200% without loss: no fixed heights that clip it, no viewport settings that block zoom |
| 1.4.5 | Images of Text (AA) | Text is real text, not an image, except logos |
| 1.4.10 | Reflow (AA) | At 320 CSS pixels wide (400% zoom) content fits without horizontal scrolling, except maps, tables and similar |
| 1.4.11 | Non-text Contrast (AA) | Control borders, focus indicators, icons and chart parts that matter have at least 3:1 against what is next to them |
| 1.4.12 | Text Spacing (AA) | Content survives larger line height, letter, word and paragraph spacing: no fixed heights or overflow hidden on text |
| 1.4.13 | Content on Hover or Focus (AA) | Tooltips and popovers can be dismissed (Escape), can be hovered without vanishing, and stay until dismissed |

## 2. Operable

| SC | Name (level) | Check in the changed UI |
|---|---|---|
| 2.1.1 | Keyboard (A) | Everything works with the keyboard: native interactive elements, or custom ones with a role, `tabindex="0"` and key handlers |
| 2.1.2 | No Keyboard Trap (A) | Focus can always leave a component with standard keys; a modal keeps focus inside on purpose and releases it on close |
| 2.1.4 | Character Key Shortcuts (A) | Single-key shortcuts (letters, digits, punctuation) can be turned off or remapped, or work only while their component has focus |
| 2.2.1 | Timing Adjustable (A) | Time limits can be turned off, adjusted or extended, unless essential |
| 2.2.2 | Pause, Stop, Hide (A) | Carousels, auto-updating feeds and animations that last more than 5 seconds can be paused, stopped or hidden |
| 2.3.1 | Three Flashes or Below Threshold (A) | Nothing flashes more than three times per second |
| 2.4.1 | Bypass Blocks (A) | A skip link or landmarks let users jump past repeated navigation |
| 2.4.2 | Page Titled (A) | Each page and route sets a title that says what it is |
| 2.4.3 | Focus Order (A) | Tab order follows the visual and logical order; no positive `tabindex`; focus moves into dialogs and back when they close |
| 2.4.4 | Link Purpose (In Context) (A) | A link's text, with its sentence or list item, says where it goes; no bare "click here" |
| 2.4.5 | Multiple Ways (AA) | A page can be found in more than one way (navigation, search, sitemap), except steps of a process |
| 2.4.6 | Headings and Labels (AA) | Headings and labels describe their topic or purpose |
| 2.4.7 | Focus Visible (AA) | The focused element is visibly marked; `outline: none` needs a replacement style |
| 2.4.11 | Focus Not Obscured (Minimum) (AA, 2.2) | Sticky headers, footers, banners and non-modal panels never hide the focused element entirely |
| 2.5.1 | Pointer Gestures (A) | Multipoint or path gestures (pinch, swipe) have a single-pointer alternative (buttons) |
| 2.5.2 | Pointer Cancellation (A) | Actions fire on release (`click`), not on press, or can be aborted or undone |
| 2.5.3 | Label in Name (A) | The accessible name contains the visible label text, ideally at its start, so voice control works |
| 2.5.4 | Motion Actuation (A) | Shaking or tilting the device is never the only way to do something, and can be turned off |
| 2.5.7 | Dragging Movements (AA, 2.2) | Anything done by dragging (sliders, sortable lists, maps) also works with single clicks or taps |
| 2.5.8 | Target Size (Minimum) (AA, 2.2) | Pointer targets are at least 24 by 24 CSS pixels, or spaced so a 24-pixel circle on each does not overlap another; inline links in text are exempt |

## 3. Understandable

| SC | Name (level) | Check in the changed UI |
|---|---|---|
| 3.1.1 | Language of Page (A) | The `html` element has the right `lang` |
| 3.1.2 | Language of Parts (AA) | Passages in another language carry their own `lang` |
| 3.2.1 | On Focus (A) | Focusing an element never submits, navigates or opens something unexpected |
| 3.2.2 | On Input (A) | Changing a field's value does not change context (submit, navigate) without warning |
| 3.2.3 | Consistent Navigation (AA) | Repeated navigation keeps the same relative order across pages |
| 3.2.4 | Consistent Identification (AA) | Components with the same function have the same name and icon across pages |
| 3.2.6 | Consistent Help (A, 2.2) | Help (contact details, a help link, a chat) keeps the same relative place across pages |
| 3.3.1 | Error Identification (A) | Input errors are detected and described in text, tied to the field (not only a red border) |
| 3.3.2 | Labels or Instructions (A) | Every field has a visible label or instructions; a placeholder alone is not a label; required fields and formats are stated |
| 3.3.3 | Error Suggestion (AA) | When the fix is known, the message says how to fix it ("use the format MM/YY") |
| 3.3.4 | Error Prevention (Legal, Financial, Data) (AA) | Submissions with legal or financial effect, or that change user data, can be reviewed, confirmed or reversed |
| 3.3.7 | Redundant Entry (A, 2.2) | Data the user already gave in the same process is filled in or offered, not asked again, unless essential |
| 3.3.8 | Accessible Authentication (Minimum) (AA, 2.2) | Signing in does not require memorizing or transcribing (passwords can be pasted and filled by managers; codes can be pasted); a puzzle needs an alternative |

## 4. Robust

| SC | Name (level) | Check in the changed UI |
|---|---|---|
| 4.1.2 | Name, Role, Value (A) | Every control exposes its name, its role and its state (expanded, selected, checked, disabled) to assistive technologies; custom widgets follow their ARIA pattern |
| 4.1.3 | Status Messages (AA) | Results, confirmations and errors that appear without a page change are announced (a live region or role `status` or `alert`) without moving focus |

**4.1.1 Parsing** is obsolete in WCAG 2.2 and removed from it. Standards still based on WCAG 2.1 (some versions of EN 301 549) list it; browsers now handle what it covered, so do not report it unless the project's target standard requires it.

## Contrast

1. Take the two colors in sRGB, each channel from 0 to 255.
2. For each channel: `c = value / 255`; then `c = c / 12.92` if `c <= 0.04045`, otherwise `c = ((c + 0.055) / 1.055) ^ 2.4`.
3. Relative luminance: `L = 0.2126 * R + 0.7152 * G + 0.0722 * B`.
4. Ratio: `(L_lighter + 0.05) / (L_darker + 0.05)`, from 1:1 to 21:1.

| Content | Minimum (AA) |
|---|---|
| Normal text | 4.5:1 (1.4.3) |
| Large text: at least 24 CSS pixels, or 18.66 CSS pixels bold | 3:1 (1.4.3) |
| Control boundaries, focus indicators, meaningful icons and graphics | 3:1 against the adjacent colors (1.4.11) |
| Disabled controls, logos, pure decoration | no requirement |

Report the ratio you computed and both colors (`#767676 on #ffffff: 4.54:1`). Text over images or gradients: check the worst spot, or list it as not checked.

## Testing hints

- **Component tests:** queries by role and accessible name (`getByRole('button', { name: 'Add to cart' })` in Testing Library) prove 4.1.2 and 2.5.3; a test that tabs through the form proves 2.1.1 and 2.4.3.
- **Keyboard pass by hand:** Tab and Shift+Tab through the flow, Enter and Space on controls, arrow keys inside composite widgets, Escape on dialogs and popovers.
- **Zoom and reflow:** 200% text zoom and a 320-pixel-wide viewport.
- **Screen readers** (NVDA or JAWS on Windows, VoiceOver on macOS and iOS, TalkBack on Android): what a static review cannot confirm goes to Not checked.
