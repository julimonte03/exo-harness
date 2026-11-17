---
name: diagram-design
description: >-
  The diagram system of the project: picks the diagram type from the question
  it must answer (context, containers, components, sequence, flow, states,
  deployment, data), the notation (C4, light UML, basic BPMN, ER) and the
  tool the project already uses (Mermaid by default because it renders in the
  repository; PlantUML, draw.io or Structurizr when the project has them),
  keeps every view readable (7±2 elements, verb labels, a legend, a text
  alternative) and applies the executive style of the design pack: neutral by
  default, .exo/brand.json when the project has one. The first time in a
  project it shows a sample of the style and waits for approval before
  producing diagrams in series. Use it whenever someone needs a diagram or
  asks which diagram fits. Triggers: "draw a diagram", "diagram this",
  "make a flowchart", "sequence diagram for", "state diagram", "ER diagram",
  "visualize this process", "mermaid diagram", "which diagram should I use",
  "clean up this diagram".
metadata:
  exo-pack: design
  exo-execution: inline
  exo-permissions: write-specs
---

# diagram-design

A diagram answers one question for one audience. This skill decides which diagram answers it, in which notation and tool, and makes it readable and consistent with the project's style. The specialized skills of the pack build on it.

## Result

- One diagram per question, as source text in the project's diagram tool (Mermaid unless the project uses another), with a title that states the takeaway, a legend, a text alternative, its source and date, and the style marker in the source.
- Saved where the project keeps its diagrams, or embedded in the document that needs it, or returned as text to the phase that owns that document.
- A short note in the answer: the question it answers, the type and notation chosen and why, the facts it rests on, what is unconfirmed, and how to render it.

## When

| Need | Who does it |
|---|---|
| Any diagram: a flow, a sequence, states, data, a timeline | This skill |
| Architecture from the code or from design.md: C4 context, containers, components, deployment | skill:architecture-diagram-designer, which uses this skill |
| UML: classes, sequence, activity, states, use cases | skill:uml-visual-designer, which uses this skill |
| Review a piece before an executive audience | skill:executive-visual-quality-gate |
| Share a piece outside the team | skill:secure-diagram-sanitizer (pack `security`) |
| A chart of data (bars, lines, trends) | Not a diagram: use the project's charting tools |

When `secure-diagram-sanitizer` is not installed, say `security/secure-diagram-sanitizer not installed — applying inline criteria`, and before the piece leaves the team remove secrets, personal data, internal URLs, hostnames, IP addresses, ports and account, repository and environment names, replacing each with a consistent generic label, and never put the list of replacements in the piece.

## The style

The style is the contract `.exo/shared/executive-style.md`. Read it before the first diagram of the session:

1. Load `.exo/brand.json` when it exists, key by key, with the neutral default for what is missing (section H of the contract). Say which keys came from the neutral default.
2. Check the contrast of every pair the diagram uses (section G). A failing pair gets a warning and the nearest passing value.
3. **First use in the project** (section I): unless memory or an existing diagram shows that the person already approved this style source, make the first diagram a small sample, show it with the colors, fonts and roles in use, and ask "Use this style for the diagrams and documents of this project?" Produce nothing else until they answer. When they approve, save the convention as section I says. If they asked for several diagrams, the others wait.

## Steps

### 1. The question and the audience

Write one sentence each:

- **Question:** what the reader must understand ("how an order reaches the warehouse").
- **Audience:** executives, architects, developers, operations, a partner. It sets the level of detail and the vocabulary.
- **Destination:** a repository document, a slide, a page outside the team. A destination outside the team means sanitizing before it leaves.

When the person gives only "diagram the system", ask which question it must answer, offering the two or three that fit what you see.

### 2. The type

| The question | Type |
|---|---|
| Who uses the system and what does it talk to? | System context |
| Which runnable pieces exist and how do they talk? | Containers |
| What is inside one container? | Components |
| In what order do the parties act in one scenario? | Sequence |
| Which steps and decisions does a process follow? Who does each step? | Flow (flowchart, UML activity, or BPMN with lanes) |
| Which states can a thing be in, and what moves it? | State machine |
| Where does it run: nodes, networks, regions? | Deployment |
| Which data exists, how is it related, who owns it? | Data (entity-relationship or data flow) |

Signs, edge cases and the less common types (timeline, swimlane, quadrant, layer stack, decision tree) are in `references/diagram-types.md`. One question, one diagram: a diagram that answers two questions answers neither.

### 3. The notation

- **C4** for architecture: context, containers, components, deployment.
- **Light UML** for behavior and structure in the code: sequence, state, activity, class.
- **Basic BPMN** for business processes with roles and handoffs: events, tasks, gateways, lanes.
- **Entity-relationship** (crow's foot) for data.

Use only the subset the audience reads without training. The elements of each notation, and what to leave out, are in `references/notation.md`.

### 4. The tool

The tool the project already uses for this kind of diagram wins. Look for Mermaid blocks in Markdown and `.mmd` files, PlantUML (`.puml`), draw.io (`.drawio`, `.drawio.svg`) and Structurizr (`workspace.dsl`), and for the plugins of the documentation site. With nothing in the repository, use **Mermaid in Markdown**: most Git hosts and documentation tools render it, it diffs well in review and it needs no install.

How to detect each tool, what renders where, and the render commands are in `references/tools.md`. **Install nothing**: when a render tool is missing, give the command that would run and continue with the source.

### 5. The facts

- Every element and relation comes from somewhere: the code (`path:line`), a document of the project, or the person. Never invent a component, a relation or a technology to complete the picture.
- What you cannot confirm is drawn as unconfirmed (dashed, "(inferred)" in the label) and listed as a question for the person.
- From the code, read 1 to 3 files inline; for a broader read, delegate it to a read-only explorer when the agent has one, or read in small batches. For architecture from the code, use skill:architecture-diagram-designer, which cites the source of every element.

### 6. The structure

1. List the elements and the relations before drawing.
2. Keep 7±2 primary elements. More than nine: split into an overview and a zoom, or group into boundaries.
3. Choose one reading direction: left to right for flows and context, top to bottom for hierarchies and sequences.
4. One focus: the element the question is about. One highlight at most, for what is new or at risk.
5. Label every connector with a verb phrase in the direction of the arrow.

The readability rules, with the checks to run before showing it, are in `references/readability.md`.

### 7. The style in the tool

Map each element to its role (section D of the contract) and apply the palette, the fonts and the line styles through the tool's own mechanism: an init block and class definitions in Mermaid, `skinparam` in PlantUML, style strings in draw.io, a `styles` block in Structurizr. Snippets for each tool are in `references/tool-styling.md`. Put the style marker in the source.

### 8. Title, legend and text alternative

- **Title:** the takeaway as a sentence. **Subtitle:** type, scope and "as of" date.
- **Legend:** every color, shape and line style used, and nothing else.
- **Text alternative:** one or two sentences with the message and the main relations. In Mermaid, `accTitle` and `accDescr`; elsewhere, the alt text of the image or a caption.
- **Footer:** source, date, owner as a team or a role.

### 9. Check and render

Run the checklist of `references/readability.md`. Render it when the project has a renderer (`references/tools.md`) and look at the result; when you cannot render, say so and list what still needs a visual check. Before an executive audience, offer skill:executive-visual-quality-gate.

### 10. Show and save

Show the diagram and the note. Then save it, after the person agrees, in this order of preference:

1. Embedded in the document that needs it (a README, an ADR, a design document), next to the text it supports.
2. In the folder where the project keeps diagrams (`docs/diagrams/`, `docs/architecture/` or similar).
3. With none, `docs/diagrams/<slug>.md`: the title, the diagram block, the legend and the source line.

**Inside an SDD change,** each artifact has an owner (`.exo/shared/sdd-phase-common.md`, section C): return the diagram as text to the phase that owns the document (for example `sdd-design` for design.md, Architecture Overview), or save it outside the change folder. Never edit another phase's artifact.

A complete example, with its note, is in `references/examples.md`.

## Return

```markdown
**Order flow, as of 2026-11** (saved in docs/diagrams/order-flow.md)

Question: how an order reaches the warehouse. Audience: operations leads.
Type: flow with two lanes (shop, warehouse), basic BPMN in a Mermaid flowchart.
Facts: src/orders/service.py:40-88 (order states), src/warehouse/consumer.py:12 (queue consumer).
Unconfirmed: whether cancelled orders notify the warehouse (drawn dashed; question for the person).
Style: neutral, approved on 2026-11-17 (memory). Contrast: all pairs pass.
Render: shows in the repository host's Markdown preview; for an image, copy the block to order-flow.mmd and run `mmdc -i order-flow.mmd -o order-flow.svg` (mermaid-cli, not installed here).
```

## Record

Inside an SDD change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "diagram-design", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"diagram-design"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] The diagram answers one question, stated in the title as a takeaway.
- [ ] Type, notation and tool are the ones that fit the question and the project; nothing was installed.
- [ ] 7±2 primary elements, every connector labeled with a verb, one focus, at most one highlight.
- [ ] Every element comes from the code, a document or the person; the unconfirmed ones are dashed and listed as questions.
- [ ] The style follows `.exo/shared/executive-style.md`, with the brand keys that apply, the contrast checked and the style marker in the source; the first use in the project was approved.
- [ ] Legend, text alternative, source and date are there.
- [ ] Nothing sensitive in the piece; a piece leaving the team was sanitized.
- [ ] Inside a change, no other phase's artifact was edited.
