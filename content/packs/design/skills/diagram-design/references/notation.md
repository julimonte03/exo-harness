# Notations: the subset to use

Use the smallest part of each notation that answers the question. A reader should understand the diagram with the legend alone, without knowing the notation's specification.

## C4 (architecture)

Four levels, each a zoom into one box of the level above: system context, containers, components, code. Skip the code level: the code is its own diagram. Deployment is a supplementary view.

| Element | Meaning | Label |
|---|---|---|
| Person | A human role that uses the system | `Customer` / `[Person]` / one line of what they do |
| Software system | Something that delivers value on its own, owned by one team | `Order platform` / `[Software system]` |
| Container | A separately runnable or deployable unit: an application, a service, a database, a queue, a front end, a job | `Orders API` / `[Container: Python, FastAPI]` / `Takes and tracks orders` |
| Component | A grouping of code behind an interface, inside one container | `Payment client` / `[Component: Python module]` |
| Deployment node | Where containers run: an environment, a region, a cluster, a server | `Production` / `[Deployment node: Kubernetes]` |
| Relationship | One direction of dependency or data | `Publishes order events to` / `[AMQP]` |
| Boundary | What belongs to a system, a container or a zone | A dashed rectangle with its name |

Rules:

- Every element has a name, a type and, from the containers level, a technology. A short description helps the reader who does not know the system.
- A relationship has one direction and one label. When two elements talk both ways for different reasons, draw two relationships.
- "Container" means runnable, not Docker. A database is a container; a library is not.
- External systems keep the same box shape as the system in focus; only the fill changes (`.exo/shared/executive-style.md`, section D).

## Light UML (behavior and code structure)

### Sequence

- Participants across the top, left to right in the order they first act. A person on the far left.
- Synchronous call: solid line with a filled arrow. Reply: dashed line. Asynchronous message: solid line with an open arrow.
- Fragments: `alt` (alternatives with a guard each), `opt` (optional), `loop` (with its condition), `par` (parallel). Nest at most two levels.
- Activation bars only when they help to see who waits.
- Notes for the one thing that is not obvious: a timeout value, an idempotency key.

### State machine

- States as adjectives or nouns. Initial state as a filled dot; final state as a dot in a circle.
- Transitions labeled `event [guard] / action`, all three optional; at least the event.
- Composite states only when a group of states shares the same exits (for example, any state can go to "Cancelled").

### Activity

- Start, actions as verb phrases, decisions as diamonds with guarded exits, merges, fork and join bars for parallel work, an end.
- Partitions (lanes) for who does each action.

### Class

- Only the classes that answer the question. Only the attributes and operations that matter for it.
- Association with multiplicity, aggregation and composition only when ownership matters, inheritance and realization. Visibility marks when the audience is developers.

### Use case

- Actors outside the system boundary, use cases inside as verb plus object ("Place order").
- `include` and `extend` sparingly; generalization between actors when roles share use cases.

The rules for each UML type, with examples in Mermaid and PlantUML, are in the `uml-visual-designer` skill.

## Basic BPMN (business processes)

| Element | Shape | Use |
|---|---|---|
| Start event | thin circle | What starts the process: "Order received" |
| End event | thick circle | Each outcome: "Order shipped", "Order rejected" |
| Intermediate event | double circle | Waiting for a message or a time: "Payment confirmed", "48 hours pass" |
| Task | rounded rectangle | One unit of work, verb plus object: "Check stock" |
| Exclusive gateway | diamond with an X, or empty | One path out of several; label each exit with its condition |
| Parallel gateway | diamond with a plus | All paths at once, then joined by another parallel gateway |
| Pool and lanes | horizontal bands | A pool per organization, a lane per role inside it |
| Sequence flow | solid arrow | Order of work inside a pool |
| Message flow | dashed arrow | A message between pools |

Rules: one start event per process, an end event per outcome, every gateway that splits has a matching one that joins (or each path ends), no sequence flow between pools.

In Mermaid, draw BPMN as a flowchart: stadium shapes for events, rounded rectangles for tasks, diamonds for gateways, one subgraph per lane. Say in the legend that it follows basic BPMN.

## Entity-relationship (data)

- Entities as boxes with their name in singular, the primary key and the attributes the question needs. Never real values.
- Crow's foot cardinality: exactly one, zero or one, one or many, zero or many, on both ends.
- Label the relationship with a verb phrase ("places").
- When several services share a store, group the entities by owner and say who writes each one.
- Mark personal data fields with a tag ("PII") when the question is about privacy, and never show their values.

## Mixing notations

Do not mix notations in one diagram. When a C4 containers diagram needs the order of calls, draw a separate sequence diagram that reuses the same names.
