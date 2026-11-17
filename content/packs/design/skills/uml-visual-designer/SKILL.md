---
name: uml-visual-designer
description: >-
  Draws readable UML diagrams: class, sequence, activity, state machine and
  use case, in Mermaid or PlantUML depending on what the project already
  uses (Mermaid when it uses neither), with the light subset of UML a reader
  understands without training and the executive style of the design pack.
  Each diagram answers one question: one scenario per sequence, one thing
  per state machine, only the classes the question needs. When it comes from
  the code, every class, message and transition cites its path:line, and
  nothing is invented. Use it when someone mentions UML or needs to show
  interactions between actors and systems, the lifecycle of an entity, the
  structure of a module, the steps of an activity or who can do what.
  Triggers: "UML diagram", "class diagram", "sequence diagram", "activity
  diagram", "state machine", "state diagram", "use case diagram", "lifecycle
  of", "how do these classes relate", "message flow between".
metadata:
  exo-pack: design
  exo-execution: inline
  exo-permissions: write-specs
---

# uml-visual-designer

UML is useful when it is small. This skill uses the part of UML that a reader understands with a legend, draws one question per diagram, and grounds every element in the code or in the person's words.

## Result

- One UML diagram per question, in Mermaid or PlantUML, styled with `.exo/shared/executive-style.md`, with a title that states the takeaway, a legend, a text alternative, and the style marker in the source.
- From the code: a `[Code] path:line` comment for each class, message or transition in the source, and the list of what is unconfirmed as questions.
- Saved where the project keeps diagrams, embedded in the document that needs it, or returned as text to the phase that owns that document.

## When

| Need | Diagram |
|---|---|
| How types in the code relate | Class |
| In what order the parties act in one scenario | Sequence |
| Which steps, decisions and parallel work a process has, and who does each | Activity |
| Which states one thing goes through and what moves it | State machine |
| Who can do what with the system | Use case |

- **Not for:** C4 architecture, components and deployment (skill:architecture-diagram-designer); flows in BPMN, data models and other diagrams (skill:diagram-design).
- **Build on skill:diagram-design** for the readability rules, the styling in each tool and the first-use approval of the style. Read its `SKILL.md` before the first diagram.

## Steps

### 1. The question

One sentence: what the reader must understand, for whom. "What happens when a payment times out" is a sequence; "can a shipped order be cancelled" is a state machine. When the person only says "UML of the module", offer the two or three questions that fit, each with its diagram.

### 2. The tool

1. Look for what the project already uses (`.puml` files, `@startuml`, Mermaid blocks, the documentation site's plugins), as the tools reference of skill:diagram-design describes.
2. **PlantUML** when the project uses it: it covers every UML type.
3. **Mermaid** when the project uses it or uses neither: `classDiagram`, `sequenceDiagram`, `stateDiagram-v2`, and a `flowchart` for activity.
4. **Use case diagrams** have no Mermaid type. In a Mermaid project, draw them as a flowchart with actors outside a system boundary and use cases as stadiums inside, and say in the legend that it approximates UML. If the project also has PlantUML, offer it.

Install nothing: when no renderer is available, give the command that would render it and continue with the source.

### 3. The facts

- **From the code:** read the classes, the call path or the status field that answers the question. Read 1 to 3 files inline; for a broader read, delegate to a read-only explorer when the agent has one, or read in small batches.
  - Class: the types, their relevant fields and methods, inheritance, and the references between them.
  - Sequence: follow one call path from its entry point, message by message, including the error path the question is about.
  - State machine: the status field, its allowed values and every place that changes it, with its condition.
  - Activity: the steps of the job or the handler, its branches and its parallel parts.
  - Use case: the user-facing entry points and the roles that guard them.
- **From the person or a document:** say so, and cite the document.
- **Never invent** a class, a message, a state or a transition. What the code does not show is drawn dotted or noted "(inferred)" and asked: in UML a dashed line already means a reply, a dependency or a realization.

### 4. Draw it small

The rules for each type, what to include and what to leave out, are in `references/uml-by-type.md`. In short:

- **Class:** only the classes the question needs, five to nine; only the members that matter; multiplicity on associations.
- **Sequence:** one scenario; participants in the order they first act, seven at most; replies dashed; `alt`, `opt` and `loop` nested two levels at most.
- **Activity:** a start, actions as verb phrases, decisions with labeled exits, fork and join for parallel work, lanes for roles, an end per outcome.
- **State machine:** states as adjectives or nouns, transitions as `event [guard] / action`, an initial state and the final states.
- **Use case:** actors outside the boundary, use cases as verb plus object inside, `include` and `extend` only when they explain something.

### 5. Style

Apply the roles of the contract (`.exo/shared/executive-style.md`, section D): the element in focus (the class under discussion, the service whose behavior the sequence shows, the state the question is about) in `primary`; its peers in `primary_tint`; people in `secondary`; outside systems in `neutral_fill`; one highlight in `accent` at most. Syntax and styling for each type are in `references/mermaid-uml.md` and `references/plantuml-uml.md`. Put the style marker in the source and the evidence comments on the line before each element.

### 6. Title, legend, text alternative

- **Title:** the takeaway: "A timed-out payment is retried once, then the order is released", not "Payment sequence".
- **Legend:** the line styles and colors used, and the notation ("UML sequence: solid arrows are calls, dashed arrows are replies").
- **Text alternative:** in Mermaid, `accTitle` and `accDescr`; in PlantUML, a `title` and a caption or the image's alt text.

### 7. Check, show, save

Run the readability checklist of skill:diagram-design. Show the diagram with a short note: the question, the type and tool and why, the sources, what is unconfirmed. Save it after the person agrees, as skill:diagram-design says; **inside an SDD change**, return it as text to the phase that owns the document (`.exo/shared/sdd-phase-common.md`, section C); a diagram file of its own is a project document, written as skill:diagram-design says (with the person's approval, once the plan lists it). Before an executive audience, offer skill:executive-visual-quality-gate; before it leaves the team, skill:secure-diagram-sanitizer (pack `security`). When that skill is not installed, say `security/secure-diagram-sanitizer not installed — applying inline criteria`, replace internal names, addresses, ports and account names with consistent generic labels, and keep the list of replacements out of the shared piece.

## Return

```markdown
**A timed-out payment is retried once, then the order is released** (sequence; saved in docs/diagrams/payment-timeout.md)

Question: what happens when the payment provider does not answer. Audience: the team and support leads.
Tool: Mermaid (the repository already uses it). Participants: 4. Fragments: one `alt`, one `opt`.
Sources: services/orders/app/service.py:61-97, services/orders/app/payments_client.py:20-44.
Unconfirmed: whether support is notified after the release (dotted note); the code has a TODO at service.py:95.
Style: neutral, approved earlier. Contrast: all pairs pass.
```

## Record

Inside an SDD change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "uml-visual-designer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"uml-visual-designer"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] One question per diagram, stated in the title as a takeaway.
- [ ] The tool is the one the project uses (Mermaid when none); nothing was installed; a Mermaid use case diagram says it approximates UML.
- [ ] Only the light UML subset, within the limits of `references/uml-by-type.md`.
- [ ] Every element from the code cites its `path:line`; nothing invented; the unconfirmed is dotted or noted and asked.
- [ ] Style from `.exo/shared/executive-style.md`, approved on first use, contrast checked, style marker in the source.
- [ ] Legend and text alternative present.
- [ ] Inside a change, the diagram went to the phase that owns the document.
