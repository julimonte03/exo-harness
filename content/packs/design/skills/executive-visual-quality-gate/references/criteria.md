# Review criteria

Each criterion lists what to check, how, and the usual severity of a failure. The style values come from `.exo/shared/executive-style.md` (cited below as "the contract") and from `.exo/brand.json` when it exists.

## EVQ-MSG: one message per piece

Check:

- The title states the takeaway as a sentence ("All order traffic passes through one gateway"), not a topic ("Architecture", "Q3 update").
- The piece supports exactly that message: nothing in it argues something else.
- When the person stated the intended message, the title and the piece say it.
- In a deck, each slide has its own message; read only the titles in order: they tell the story.
- In a document, the summary at the top states the message, the impact and what is asked of the reader.

Severity: no message or a title that contradicts the content, High; a topic title on an otherwise clear piece, High for executives, Medium for a technical audience.

## EVQ-HIER: hierarchy and focus

Check:

- One focus: the element the message is about stands out by color (`primary`), size or position. Everything else is quiet.
- At most one highlight (`accent`), and it marks what the message is about (new, changed, at risk).
- The reading order is obvious: one direction, the start where the eye lands first (top left, or the center of a context diagram).
- Size and weight follow importance: the title is the largest text; labels are larger than annotations.

Severity: no focus, or several competing highlights, Medium; a highlight on the wrong element (it draws the eye away from the message), High.

## EVQ-DENS: density

Check:

- **Diagram:** count the primary elements (boxes the reader must understand; not boundaries, legend entries or notes). 7±2 is the target.
- **Connectors:** about one and a half per element at most; a mesh means the diagram needs grouping or splitting.
- **Slide:** one idea; at most five bullets of one line, or one figure with a caption; roughly 40 words of body text at most.
- **Document:** a summary of three to five lines first; headings that say what each section concludes; paragraphs of a few sentences.

Severity: 10 to 12 primary elements, Medium; more than 12, High; a slide with two ideas, Medium; a document without a summary, Medium for executives.

## EVQ-READ: legibility

Check:

- **Text size** at the size it will be shown (contract, section C): diagram labels 14 px and never below 12 px at 100%; slides never below 14 pt; documents never below 9 pt printed or 12 px on screen. A diagram scaled down to fit a slide shrinks its text: estimate the shown size.
- **Labels:** about 30 characters per line, three lines per element at most; the name, the type and technology, at most one line of responsibility.
- **Connectors:** labeled with a verb phrase in the direction of the arrow (sequence messages count as labels); decisions with every exit labeled.
- **Layout:** no crossing lines that another order of the elements would avoid; arrows end on boxes; aligned rows and columns.
- **Words:** acronyms spelled out on first use or in the legend; the same name for the same thing across the set; sentence case.

Severity: text below the minimum, High; unlabeled connectors or decision exits, Medium; avoidable crossings, Medium; wording and alignment, Low.

## EVQ-STYLE: consistency with the style

Check:

- **Palette:** every color is a token of the contract or of `.exo/brand.json`. Off-palette colors are a finding; list the value and the token it should be.
- **Roles:** the same role looks the same everywhere (contract, section D): focus, inside, people, external, data stores, boundaries, connectors.
- **Fonts:** the stack of the contract or of the brand; two weights at most; no italics for emphasis in diagrams.
- **The style marker** (contract, section I) is in the source and matches the current style source: `neutral` without `.exo/brand.json`, or `brand <hash>` with the current `git hash-object .exo/brand.json`. A stale hash means the piece predates a brand change. A pending marker (`exo-style: neutral (pending)`) on a piece presented as final means its style was never approved.
- **The set:** pieces meant to be shown together share titles, legend placement, footers and names.
- **The logo,** when used: from `logo.path` of the brand, not stretched, recolored or cropped, with clear space, never inside a diagram.
- **Voice:** titles and captions follow `voice.tone` and avoid `voice.avoid` when the brand sets them.

Severity: off-palette colors or a mixed set, Medium; a missing, stale or pending marker, Medium; a distorted logo, Medium; voice, Low.

## EVQ-A11Y: accessibility

Check:

- **Contrast,** computed for every pair the piece uses (contract, section G): text 4.5:1 (large text 3:1), connectors and the edges of shapes that carry meaning 3:1 against what is next to them. Report each failing pair with both values, the ratio, the threshold and the nearest passing value.
- **Color never alone:** status, categories and highlights also show as text, a shape or a line style; the legend explains them in words.
- **Text alternative:** every figure has one (Mermaid `accTitle` and `accDescr`, alt text in the document, alt text of the slide figure) that states the message and the main relations, not "diagram".
- **Reading order** in documents and slides follows the visual order: headings in sequence, the figure next to the text that cites it.
- **Motion:** no animation that carries information alone.

Severity: text failing AA, or meaning by color alone, High; a figure without a text alternative, High when published, Medium in an internal draft; an edge failing 3:1, Medium.

## EVQ-LEG: legend and notation

Check:

- Every color, shape and line style the piece uses is in the legend, and nothing the piece does not use.
- The notation is named when the audience may not know it ("C4 containers view", "basic BPMN", "UML sequence").
- Footer: source, date, owner (a team or a role, never a person's name) and, when shared, the level (Internal or Public).

Severity: no legend on a diagram that uses more than one color or line style, Medium; an incomplete legend, Low to Medium; no source or date, Medium.

## EVQ-TRUE: accuracy

Check:

- Elements and relations against the code or the design they come from: names, directions, technologies. Sample at least three, and every one the message relies on.
- Numbers against their source and date; totals add up; units shown.
- Unconfirmed elements are marked as such (dotted, "(inferred)") and none is presented as fact.
- The "as of" date is recent enough for the claim.

Severity: a claim that contradicts its source, Critical; an unconfirmed element presented as fact, High; a missing date on a figure with numbers, Medium.

## EVQ-SENS: sensitive information

Check everything a viewer can reach, not only the visible text: source comments, alt text, notes, hidden layers or slides, speaker notes, file names, document properties, embedded images with text, link targets.

| Destination | Not allowed |
|---|---|
| Any | Secrets of any kind (Critical, `.exo/shared/data-protection.md`): keys, tokens, passwords, connection strings, signed links |
| Any | Personal data of real people (Restricted): names of customers, emails, phone numbers, documents, account numbers |
| Outside the organization | Internal URLs, hostnames, IP addresses, ports, cloud account and subscription IDs, repository names, environment and cluster names, internal ticket IDs |

Severity: any of the above for its destination, Critical. Point at the location and name the kind of data; never copy it into the finding. Recommend the sanitizer before the piece is shared.

## Slides and documents: quick checks

- **Deck:** a title slide with the message; one agenda slide at most; titles that read as a story; a closing slide with the decision or the ask; slide numbers; sources on the slides that show data.
- **Document:** summary first; numbered figures with captions that state their message; tables with units and aligned numbers; no orphan headings; links that work and point where they say.
