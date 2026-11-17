# Executive style contract

The visual style of the diagrams, slides and documents that the skills of the `design` pack produce: `diagram-design`, `architecture-diagram-designer` and `uml-visual-designer` apply it, and `executive-visual-quality-gate` checks it. Other packs read section H for the shape of `.exo/brand.json`.

The style is neutral by default. A project that wants its own brand writes `.exo/brand.json`, and its keys replace the neutral values one by one.

## A. Principles

1. **One message per piece.** The title says the takeaway as a sentence; everything in the piece supports it.
2. **One focus.** The element the message is about stands out; everything else is quiet.
3. **Hierarchy before decoration.** Size, weight, position and space first; color last.
4. **Restraint.** One accent at most. Status colors only for status, always with text.
5. **Consistency.** The same role always looks the same: shape, color, line and label form.
6. **Accessible by default.** Contrast meets WCAG 2.2 AA (section G), color never carries meaning alone, and every piece has a text alternative.
7. **Nothing sensitive.** No secrets, personal data or internal addresses in a piece (`.exo/shared/data-protection.md`). Before a piece leaves the team, it is sanitized.

## B. Where the style comes from

In this order, per key:

1. What the person asks for this piece ("use the accent for the new service").
2. `.exo/brand.json`, when it exists and the key is there and valid (section H).
3. The neutral default (sections C to F).

Never mix two brands in one piece, and never invent brand values. A project's UI design tokens are for its UI, not for its diagrams; use them only when the person asks.

## C. The neutral default

### Colors

| Token | Value | Role |
|---|---|---|
| `ink` | `#1d2125` | Text, titles |
| `ink_muted` | `#5b6470` | Secondary text: technology, descriptions, connector labels, footers |
| `canvas` | `#ffffff` | Background of the piece |
| `surface` | `#f5f7f9` | Panels, table headers, zones |
| `line` | `#7d8794` | Connectors, boundaries and the edges of neutral shapes |
| `line_subtle` | `#d5dbe1` | Decoration only: dividers, grid lines. Never the only edge of something that carries meaning |
| `primary` | `#0a58a8` | The focus: the system in scope, the key element |
| `on_primary` | `#ffffff` | Text on `primary` |
| `primary_tint` | `#e7f0fa` | Elements inside the focus (containers, components), with a `primary` edge |
| `secondary` | `#2f3b4c` | People and actors |
| `on_secondary` | `#ffffff` | Text on `secondary` |
| `neutral_fill` | `#e9edf1` | External systems and anything outside the scope, with a `line` edge |
| `accent` | `#a34f00` | The one highlight: what is new, what changes, what is at risk |
| `on_accent` | `#ffffff` | Text on `accent` |
| `success` | `#187a35` | Status: done, healthy |
| `warning` | `#946200` | Status: at risk, degraded |
| `danger` | `#b3261e` | Status: failing, blocked |
| `info` | `#0a58a8` | Status: informational (same as `primary`) |

### Contrast, already computed

| Pair | Ratio | Enough for |
|---|---|---|
| `ink` on `canvas` | 16.2:1 | all text |
| `ink` on `surface` | 15.1:1 | all text |
| `ink` on `primary_tint` | 14.1:1 | all text |
| `ink` on `neutral_fill` | 13.8:1 | all text |
| `ink_muted` on `canvas` | 6.0:1 | all text |
| `ink_muted` on `neutral_fill` | 5.1:1 | all text |
| `ink_muted` on `primary_tint` | 5.2:1 | all text |
| `on_primary` on `primary` | 7.1:1 | all text |
| `primary` on `canvas` | 7.1:1 | all text, edges |
| `on_secondary` on `secondary` | 11.4:1 | all text |
| `on_accent` on `accent` | 5.7:1 | all text |
| `accent` on `canvas` | 5.7:1 | all text, edges |
| `success` on `canvas` | 5.4:1 | all text |
| `warning` on `canvas` | 5.2:1 | all text |
| `danger` on `canvas` | 6.5:1 | all text |
| `line` on `canvas` | 3.6:1 | connectors and edges (3:1) |
| `line` on `neutral_fill` | 3.1:1 | edges (3:1) |
| `line_subtle` on `canvas` | 1.4:1 | decoration only |
| `ink` on `primary` | 2.3:1 | fails: never dark text on `primary` |

Recompute any pair you change (section G).

### Typography

- **Family:** the system stack, `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`; for code and identifiers, `ui-monospace, "SF Mono", Menlo, Consolas, monospace`. A tool that takes one font name gets `sans-serif` (or the tool's own generic sans name).
- **Weights:** two, regular (400) and semibold (600). No italics for emphasis in diagrams.
- **Case:** sentence case everywhere. Capitals only for short tags and acronyms the audience knows.
- **Sizes:**

| Where | Title | Labels and body | Secondary text | Never below |
|---|---|---|---|---|
| Diagram, at 100% | 20 to 24 px, semibold | 14 px | 12 px | 12 px |
| Slide (16:9) | 28 to 36 pt | 18 to 24 pt | 14 to 16 pt | 14 pt |
| Document | scale of 1.25 from the body | 11 pt printed, 16 px on screen | one step down | 9 pt printed, 12 px on screen |

### Space

- An 8-pixel grid. Inside a shape, at least 8 px of padding; between unrelated shapes, at least 32 px; around the whole diagram, 24 px.
- Slides keep a safe margin of 5% of the width on every side. Documents keep page margins of 2.5 cm (1 in) and lines of 60 to 75 characters.
- Related elements sit closer than unrelated ones. Align to shared edges; never center everything.

## D. Roles in a diagram

| Role | Shape | Fill | Edge | Text |
|---|---|---|---|---|
| System or element in focus | rounded rectangle | `primary` | `primary` | `on_primary` |
| Element inside the focus (container, component) | rounded rectangle | `primary_tint` | `primary`, 1.5 px | `ink` |
| Person or actor | rounded shape labeled "Person" (stick figure in UML) | `secondary` | `secondary` | `on_secondary` |
| External system, out of scope | rounded rectangle | `neutral_fill` | `line` | `ink` |
| Data store | cylinder | as its owner (inside or outside the focus) | as its owner | as its owner |
| Queue or topic | horizontal cylinder, or a rectangle labeled "Queue" | as its owner | as its owner | as its owner |
| Boundary (system, team, network zone) | rectangle, dashed | none or `surface` | `line`, dashed | label `ink_muted`, top left |
| The highlight (new, changed, at risk) | the element's own shape | unchanged | `accent`, 3 px | a short tag such as "New" |
| Not confirmed (inferred, planned) | the element's own shape | unchanged | dashed | "(inferred)" or "(planned)" in the label |
| Connector, synchronous | solid line, 1.5 px, arrow toward the callee | — | `line` | label `ink_muted` |
| Connector, asynchronous | dashed line, arrow toward the consumer | — | `line` | label `ink_muted` |

- **Labels on elements:** the name, then the type and technology in brackets on a second line, then at most one line of responsibility: `Orders API` / `[Container: Python]` / `Takes and tracks orders`. About 30 characters per line, three lines at most.
- **Labels on connectors:** a verb phrase in the direction of the arrow, with the protocol when it helps: `Publishes order events to [AMQP]`.
- **Status color** never alone: the element also says the status in words.

## E. What an executive diagram looks like

From top to bottom:

1. **Title:** the takeaway as a sentence. "Orders reach the warehouse through one queue", not "Architecture".
2. **Subtitle:** what it shows and as of when: "System context · as of 2026-11 · from the code at `<commit>`".
3. **The diagram:** one focus, 7±2 primary elements, reading left to right or top to bottom, no crossing lines that can be avoided.
4. **Legend:** every color, shape and line style that the diagram uses, and nothing it does not use. Under the diagram, as a short line or a small table.
5. **Footer:** the source, the date, the owner (a team or a role, never a person's name) and, when the piece is shared, its level (Internal or Public).
6. **Text alternative:** one or two sentences with the message and the main relations, for the alt text or the diagram's accessible description.

A diagram that needs more than nine primary elements becomes two: an overview and a zoom into the part that matters.

## F. Slides and documents

- **Slides:** one idea per slide; the title is the takeaway as a sentence; at most five bullets of one line each, or one figure with a caption; the source in the footer at 14 pt. No logo on content slides unless `.exo/brand.json` gives one and the person wants it.
- **Documents:** a summary of three to five lines first (the decision or the message, the impact, what is asked of the reader), then the detail. Headings say what the section concludes. Each figure has a number, a caption that states its message, and its source.
- **Tables:** left-aligned text, right-aligned numbers with the same decimals, units in the header, no vertical rules, a `surface` header row.
- **Numbers and dates:** the same format in the whole piece; dates as `YYYY-MM-DD` or the month written out; every figure with its source and date.

## G. Contrast

**Thresholds** (WCAG 2.2 AA):

- Text: 4.5:1. Large text, 24 px or more, or 18.66 px (14 pt) or more in semibold: 3:1.
- Connectors, edges of shapes that carry meaning, icons and focus marks: 3:1 against what is next to them.
- Decoration and disabled elements: no minimum, but they never carry meaning.

**The ratio:** for each color, take each sRGB channel `c` from 0 to 1, linearize it (`c / 12.92` when `c <= 0.04045`, otherwise `((c + 0.055) / 1.055) ^ 2.4`), and compute the luminance `L = 0.2126 R + 0.7152 G + 0.0722 B`. The ratio is `(L_light + 0.05) / (L_dark + 0.05)`.

**The nearest color that passes,** when a pair fails:

1. If the failing color is a fill with text on it, try the other text color first (`ink` or `#ffffff`). If it passes, propose it: the brand color stays as it is.
2. Otherwise keep the hue and the saturation of the failing color, and move its lightness away from the background (darker on a light background, lighter on a dark one) in steps of half a percent until the pair passes. Propose that value.
3. Say the key, the ratio, the threshold and the proposal: "`colors.accent` `#f0a000` on `canvas` is 2.2:1 and needs 3:1 as an edge; the nearest that passes is `#ca8600` (3.0:1), and `#a16b00` (4.5:1) as text."

When Python is available, this computes both:

```python
import colorsys

def luminance(hex_color):
    channels = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

def nearest(color, background, target):
    rgb = [int(color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    hue, light, sat = colorsys.rgb_to_hls(*rgb)
    step = -0.005 if luminance(background) > 0.18 else 0.005
    while 0 <= light <= 1:
        candidate = "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(hue, light, sat))
        if ratio(candidate, background) >= target:
            return candidate
        light += step
    return None
```

Use the passing value in the draft and say so; the person decides whether to keep it. A pair that still fails because the person wants it stays in the piece only with their explicit decision, and the answer says so.

## H. `.exo/brand.json`

Optional, owned by the person. Write or change it only when the person asks, with the text they approved. Every key is optional.

```json
{
  "version": 1,
  "name": "Example Org",
  "colors": {
    "primary": "#4a2c82",
    "on_primary": "#ffffff",
    "secondary": "#1f5f5b",
    "accent": "#f0a000",
    "neutrals": {
      "ink": "#1d2125",
      "ink_muted": "#5b6470",
      "canvas": "#ffffff",
      "surface": "#f5f7f9",
      "line": "#7d8794"
    },
    "status": {
      "success": "#187a35",
      "warning": "#946200",
      "danger": "#b3261e"
    }
  },
  "typography": {
    "heading": "\"Example Sans\", system-ui, sans-serif",
    "body": "system-ui, -apple-system, \"Segoe UI\", Roboto, sans-serif",
    "mono": "ui-monospace, Menlo, Consolas, monospace"
  },
  "logo": {
    "path": "docs/brand/logo.svg",
    "path_on_dark": "docs/brand/logo-inverse.svg",
    "alt": "Example Org logo"
  },
  "voice": {
    "tone": "plain, confident and brief; no jargon in titles",
    "avoid": ["exclamation marks", "internal acronyms without expansion"],
    "terms": {"customer": ["client", "account holder"]}
  }
}
```

| Key | Value | Used for | When missing or invalid |
|---|---|---|---|
| `version` | `1` | The shape of the file | Read it as version 1. A higher version: use the keys you know and say so |
| `name` | text | Footers, alt text of the logo | Leave it out |
| `colors.primary`, `colors.secondary`, `colors.accent` | `#rrggbb` or `#rgb` | The roles of section D | The neutral value |
| `colors.on_primary`, `colors.on_secondary`, `colors.on_accent` | color | Text on those fills | `#ffffff` or `ink`, whichever has the higher contrast |
| `colors.primary_tint` | color | Elements inside the focus | With a brand `primary`, a tint of it: each channel 10% of `primary` and 90% of `canvas`. Otherwise the neutral value |
| `colors.neutrals.*` (`ink`, `ink_muted`, `canvas`, `surface`, `line`, `line_subtle`, `neutral_fill`) | color | Text, background, edges, outer fills | The neutral value |
| `colors.status.*` (`success`, `warning`, `danger`, `info`) | color | Status, always with text | The neutral value |
| `typography.heading`, `typography.body`, `typography.mono` | a font stack | Titles; labels and body; code | The neutral stack. A stack that does not end in a generic family gets `sans-serif` (or `monospace`) added |
| `logo.path`, `logo.path_on_dark` | a path relative to the repository root, SVG or PNG | Slide masters and document covers; never inside a diagram | No logo |
| `logo.alt` | text | The logo's text alternative | `<name> logo` |
| `voice.tone` | text | Titles, captions, labels and summaries | Plain, direct and neutral |
| `voice.avoid` | list of text | What titles and copy must not do | Nothing extra |
| `voice.terms` | an object: the preferred term and the terms it replaces | Consistent wording | The project's own terms |

**Rules:**

- **No file:** the neutral default, entirely. Do not suggest creating one unless the person asks about branding.
- **A file that does not parse as JSON:** the neutral default, entirely; tell the person the file is unreadable and where it fails. Never repair it on your own.
- **A missing or invalid key:** the neutral value for that key only. Say once, in the answer, which keys came from the neutral default and which values were invalid, with their key path.
- **Unknown keys:** ignore them.
- **Contrast:** check every pair the piece uses with the brand values (section G). A pair below AA gets a warning and the nearest value that passes; the file stays untouched.
- **The logo** is read only from the repository. A path that does not exist, or a URL, means no logo: say so. Never download a logo or a font, never stretch, recolor or crop the logo, and keep clear space around it of at least its own height divided by four.
- **Fonts:** name them only; never embed font files or load web fonts. The viewer's machine falls back along the stack.
- **The voice** shapes wording, never facts: it does not soften a risk or round a number.

## I. First use in a project

Before a skill produces diagrams or documents in series in a project, the person sees the style once and approves it.

1. **The style source:** `neutral`, or `brand <hash>` when `.exo/brand.json` exists, where `<hash>` is the first seven characters of `git hash-object .exo/brand.json` (without git, just `brand`).
2. **Already approved** when either holds:
   - memory has the convention with topic key `design/executive-style` for the same style source (`exo mem search "executive style" --json`, then `exo mem get <id>`);
   - a diagram in the repository carries the style marker (below) with the same source.
3. **Otherwise, show a sample:** the first piece the person asked for, kept small, and under it the colors, fonts and roles in use, and the keys that came from the neutral default. Ask: "Use this style for the diagrams and documents of this project?" Produce nothing else until they answer.
4. **On approval,** save it (the `memory-protocol` skill):

   ```bash
   exo mem save --type convention --title "Executive style approved" --topic-key design/executive-style --content "Style source: neutral. Approved by the person on 2026-11-17."
   ```

5. **On changes,** adjust the sample and ask again. A change to the brand itself is a change to `.exo/brand.json`: show the JSON and let the person write it, or write it when they ask.
6. **Unattended runs** (no person to answer): produce only the first piece, say "style pending approval" in the answer, and stop the series.

When `.exo/brand.json` appears, disappears or changes, the style source changes and the approval is asked again.

**The style marker** is a comment in the source of every diagram, never in the rendered image:

| Tool | Marker |
|---|---|
| Mermaid | `%% exo-style: neutral` |
| PlantUML | `' exo-style: neutral` |
| Structurizr DSL | `// exo-style: neutral` |
| draw.io | a data property `exo-style` on the diagram itself (Edit Data with nothing selected) |

With a brand, the value is `brand <hash>`. The marker tells the next session, and the quality review, which style a diagram was made with.
