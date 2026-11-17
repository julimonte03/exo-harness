# Readability rules and checks

A diagram is read in seconds or not at all. These rules come before any styling.

## Size

- **7±2 primary elements** per view: the boxes the reader must understand. Boundaries, legend entries and notes do not count. With more than nine:
  - **zoom:** an overview with the parts grouped, and a second diagram inside the group that matters;
  - **group:** put related elements in a boundary and draw the boundary's relations once;
  - **cut:** leave out what does not serve the question, and say so in a note ("logging and monitoring omitted").
- **Connectors:** about one and a half times the number of elements at most. When every box talks to every other, the diagram shows a mesh, not an answer: group or split.
- **Text:** about 30 characters per label line, three lines per element at most. A label that needs a paragraph is a note or a sentence under the diagram.

## Labels

- **Elements:** the name the team uses in conversation, then the type and the technology, then at most one line of responsibility.
- **Connectors:** a verb phrase that reads in the direction of the arrow: "Sends orders to", "Reads customer data from", "Publishes order events to". Never "uses", "calls" or "data" alone, and never an unlabeled arrow (sequence diagrams excepted: their messages are the labels).
- **Decisions:** a question ("Stock available?") with every exit labeled ("Yes", "No").
- **States:** adjectives or nouns ("Paid"); transitions with their event.
- **Names are consistent:** the same element has the same name in every diagram of the set, in the code and in the documents.
- **Acronyms:** spelled out on first use, or in the legend, unless the audience uses them every day.

## Layout

- **One reading direction:** left to right for flows and context, top to bottom for hierarchies, sequences and deployment nesting.
- **The focus in the middle** of a context diagram, or at the start of a flow.
- **Lines:** no crossings that a different order of the elements would avoid; straight or orthogonal, never a tangle; arrows that end on the box, not inside it.
- **Alignment:** elements of the same level on one row or column; equal spacing between peers.
- **Whitespace:** more space between groups than inside them.
- **Direction of arrows** is consistent: the arrow points from the caller to the callee, or along the flow of data. Say which in the legend when it could be read both ways.

## Legend

- Every color, shape and line style the diagram uses, with what it means. Nothing the diagram does not use.
- A short line under the diagram is enough for a few entries: "Blue: the order platform. Gray: external systems. Dashed line: asynchronous. Orange edge: new in this release."
- Name the notation when the audience may not know it: "Basic BPMN", "C4 containers view".

## Text alternative

- One or two sentences: the message, then the main elements and relations. Not a list of every box.
- Example: "Orders reach the warehouse through one queue. Customers order in the shop front end, which calls the Orders API; the API stores each order and publishes an event that the warehouse system consumes."
- In Mermaid, `accTitle` and `accDescr`. For an image, the alt text in the document. For a slide, the alt text of the figure.

## Check before you show it

- [ ] The title states the takeaway; the subtitle states type, scope and date.
- [ ] One question answered; one focus; at most one highlight.
- [ ] 7±2 primary elements; connectors not a mesh.
- [ ] Every connector labeled with a verb phrase; every decision exit labeled.
- [ ] Names match the code, the documents and the other diagrams of the set.
- [ ] No avoidable crossing lines; one reading direction.
- [ ] Legend complete and minimal; notation named when needed.
- [ ] Contrast of every pair checked (`.exo/shared/executive-style.md`, section G); color is never the only carrier of meaning.
- [ ] Text alternative present.
- [ ] Unconfirmed elements dashed and listed as questions.
- [ ] Source, date and owner in the footer; style marker in the source.
- [ ] No secrets, personal data, internal addresses or account names; sanitized if it leaves the team.

## What only a rendered image shows

Without a renderer, list these as pending: label overflow and truncation, crossing lines created by the layout engine, the real size of text at the size it will be shown, and the contrast of anti-aliased thin lines.
