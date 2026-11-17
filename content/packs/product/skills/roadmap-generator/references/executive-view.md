# Executive view

The one-page view of a roadmap, for an audience that has a few minutes: what we will achieve, how confident we are, what could go wrong, and what we need from them. It is derived from the detailed roadmap (`references/roadmap-model.md`), never the other way round: a card that disagrees with the detail is wrong.

## Layout

From top to bottom:

1. **Headline:** one sentence with the main outcome and its horizon. "By the end of Q3, most delivery changes happen without a call to support."
2. **Summary cards:** three to five, one per objective (or per workstream when that is how the audience thinks).
3. **Timeline:** the horizons or quarters, with the initiatives by name and the committed milestones.
4. **Top risks:** at most three, each with its mitigation in a few words.
5. **Decisions needed:** what the audience is asked to approve, choose or unblock, each with a date.
6. **Footer:** owner role, version and date, the confidence legend, "Later is not a commitment", and where the detailed roadmap lives.

## Summary cards

Each card has the same five lines, in the same order:

| Line | Content | Example |
|---|---|---|
| Title | Two or three words | Self-service |
| Objective | The outcome | Customers solve delivery changes alone |
| Target | Metric, baseline and target, with the date | 50% of reschedules self-served by Q3 (from 0%) |
| Now | The initiative in progress that moves it | Reschedule before dispatch |
| Confidence | High, medium or low, with a word on why | High: in progress, owned |

Never more than five cards. A sixth objective means the roadmap has too many; say so instead of shrinking the cards.

## Timeline in Mermaid

A `timeline` for horizons or quarters. Name the initiatives as in the detail, with their IDs, so a reader can find them:

```mermaid
%%{init: {"theme": "neutral"}}%%
timeline
  title Delivery experience, 2027
  section Now
    Self-service : I-1 Reschedule before dispatch : I-2 Carrier spike
    Compliance : I-3 Accessibility fixes : M-1 Audit, 2027-06-30 (committed)
  section Next
    Fewer calls : I-4 Proactive delay notices
    Self-service : I-5 Reschedule after dispatch
  section Later
    Self-service : I-6 Time window at checkout
```

A `gantt` only when every bar and milestone has a real date (committed or a target the person set). Label targets as such:

```mermaid
%%{init: {"theme": "neutral"}}%%
gantt
  title Committed and target dates, 2027
  dateFormat YYYY-MM-DD
  axisFormat %b
  section Self-service
    I-1 Reschedule before dispatch (target) :active, i1, 2027-01-11, 2027-03-26
  section Compliance
    I-3 Accessibility fixes (target) :i3, 2027-02-01, 2027-05-28
    M-1 Audit (committed) :milestone, m1, 2027-06-30, 0d
```

Check that the diagram renders where the audience will see it (the repository host, the docs site, the slide tool) before delivering it.

## Neutral style

The default when the project has no executive style:

- Mermaid's `neutral` theme; black or dark gray text on white; gray for structure.
- One accent color at most, for what needs attention (a risk, a decision). Meaning never depends on color alone: label it.
- One sans-serif font family, three sizes at most (headline, card title, body).
- Generous white space; aligned cards of equal size; no shadows, gradients or 3D.
- Confidence shown with words (high, medium, low), optionally with a filled, half or empty marker.

## Executive style

- **With the `design` pack:** follow its `executive-style.md` contract for layout, colors, typography and tone, with the values of `.exo/brand.json` when the project has one.
- **Without the pack, with `.exo/brand.json`:** read the keys it has. Use a primary color for headings and card borders, the neutral or background colors for fills, the font family for text, and the logo only where the file says it may go. Map onto Mermaid only what you understood (`themeVariables` such as `primaryColor`, `primaryTextColor`, `lineColor`, `fontFamily`, with the theme set to `base`), and ask about the rest.
- **Without either:** the neutral style. Never invent brand colors, fonts or a logo.

## Visual brief

When the team builds the page in a slide or design tool, give a brief instead of (or with) the Mermaid diagram. It describes the page so anyone, or a design skill, can build it without guessing:

```markdown
# Visual brief: <roadmap name>, executive view

- Format: one slide, 16:9 (or one A4 page, landscape)
- Style: <neutral | executive-style.md of the design pack, with .exo/brand.json>
- Headline (top, largest text): "<headline>"
- Cards (one row, equal width, left to right):
  1. <title> | <objective> | <target> | Now: <initiative> | Confidence: <level>
  2. ...
- Timeline (middle, full width): columns Now | Next | Later; rows <workstreams>;
  items as labeled boxes with their IDs; committed milestones as diamonds with the date
- Risks (bottom left, up to three lines): <R-1 in a few words>; ...
- Decisions needed (bottom right): <decision, by date>; ...
- Footer (smallest text): <owner role> · v<n>, <date> · Confidence: high / medium / low · Later is not a commitment · Detail: <path>
- Do not include: internal hostnames, people's names, customer names, unconfirmed dates
```

## Quality checks

Run them before the view reaches its audience. They are the inline criteria when `executive-visual-quality-gate` (pack `design`) is not installed:

1. **One message:** the headline says the main outcome; someone who reads only it knows what the year is about.
2. **Glanceable:** the cards and the timeline read in under a minute; no paragraph longer than two lines.
3. **Consistent with the detail:** every card, initiative, ID, date and confidence matches the detailed roadmap.
4. **Honest dates:** every date is a milestone labeled committed (with its source) or target; Later has none.
5. **Plain words:** no internal jargon or acronyms the audience does not use; outcomes, not system names.
6. **Accessible:** text contrast of at least 4.5:1 against its background, meaning never carried by color alone, readable when printed in grayscale.
7. **Clean:** no personal names, customer names, internal hostnames, URLs or secrets (for an external audience, also no internal risks or capacity).
8. **Footer complete:** owner role, version, date, confidence legend, and where the detail lives.

Report each check as passed or failed with the fix; fix the failures before delivering.
