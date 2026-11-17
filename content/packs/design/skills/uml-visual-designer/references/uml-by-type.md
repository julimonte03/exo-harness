# UML by type: what to draw and what to leave out

## Class

**Answers:** how the types of one module or one domain concept relate.

Include:

- The five to nine classes the question needs. A class outside the module that matters (a base class, an interface it implements) appears with its name only.
- The attributes and operations that explain the question, with types when the audience is developers. Never every getter and setter.
- Relations, with the arrow conventions of UML:
  - association: a solid line, with multiplicity on both ends (`1`, `0..1`, `1..*`, `*`) and a role name when it helps;
  - composition (filled diamond) when the part does not live without the whole; aggregation (hollow diamond) almost never: an association says the same;
  - inheritance: a solid line with a hollow triangle toward the parent;
  - realization: a dashed line with a hollow triangle toward the interface;
  - dependency: a dashed arrow, only when it explains the question.
- Stereotypes (`<<interface>>`, `<<entity>>`, `<<value object>>`) when they carry meaning.

Leave out: private helpers, framework base classes that every class has, generated code, and fields the question does not touch.

From the code: one `[Code] path:line` per class (its declaration) and per relation (the field, the parameter or the `extends`).

## Sequence

**Answers:** in what order the parties act in one scenario.

Include:

- **One scenario,** named in the title: the happy path or the one failure the question is about. A second scenario is a second diagram.
- **Participants,** seven at most, left to right in the order they first act: the person on the left, then the entry point, then inward. Group the internals of a service into one participant unless the question is about them.
- **Messages,** each a verb phrase with the important argument: `POST /orders (cart)`, `reserve(items)`. A synchronous call is a solid line with a filled arrow; the reply is dashed; an asynchronous message is a solid line with an open arrow.
- **Fragments:**
  - `alt` with a guard on each branch (`[payment accepted]`, `[timeout]`);
  - `opt` for an optional part;
  - `loop` with its condition (`[up to 3 attempts]`);
  - `par` for parallel calls.
  Nest two levels at most.
- **Notes** for the one fact that is not obvious: a timeout, an idempotency key, a transaction boundary.
- **Activation bars** only when waiting matters.

Leave out: logging, metrics, getters, and calls inside one class.

From the code: one `[Code] path:line` per message (the line that makes the call or sends the message).

## Activity

**Answers:** which steps and decisions a process follows, which run in parallel, and who does each.

Include:

- A start node, actions as verb phrases ("Check stock"), and an end node per outcome.
- Decisions as diamonds with a guard on every exit (`[in stock]`, `[out of stock]`), and a merge where the paths meet again.
- Fork and join bars for parallel work; every fork has its join.
- Partitions (lanes) when roles or systems matter, one per actor.
- Signals sent and received when the process waits for something outside.

Leave out: implementation details of each action; the action's name is enough.

From the code: one `[Code] path:line` per action and per decision (the call or the condition).

## State machine

**Answers:** which states one thing can be in, and which events move it.

Include:

- **One thing per diagram:** an order, a payment, a ticket.
- **States** as adjectives or nouns ("Pending payment", "Paid", "Shipped"), each a value the code actually stores or derives.
- **Transitions** labeled `event [guard] / action`; at least the event. Every transition the code allows, and only those.
- **The initial state** and **the final states** (a dot in a circle).
- **Composite states** when a group shares the same exit (any open state can go to "Cancelled"): draw the exit once from the composite.
- **A note** for a rule that the diagram cannot show (a time limit, who may trigger a transition).

Leave out: transient technical states that the business never sees, unless the question is about them.

From the code: the status field (`path:line`), the list of its values, and one `path:line` per transition (the line that sets the new state, with its condition). A value that the code defines but never sets is drawn and noted: it may be dead or set elsewhere.

## Use case

**Answers:** who can do what with the system.

Include:

- **Actors** outside the system boundary: human roles on the left, systems on the right. Generalization between actors when one role can do everything another can.
- **Use cases** inside the boundary as verb plus object ("Place order", "Refund payment"), each a goal the actor wants, not a screen or a step.
- **Associations** from each actor to its use cases, plain lines.
- **`include`** for a step shared by several use cases that is always done; **`extend`** for an optional variation. Use them sparingly: most diagrams need neither.

Leave out: the order of steps (that is an activity or a sequence), and use cases that no actor triggers.

From the code: the user-facing entry points (routes, commands, screens) and the role checks that guard them, one `path:line` each.

## Common limits

| Type | Elements | Nesting |
|---|---|---|
| Class | 5 to 9 classes | packages one level |
| Sequence | 7 participants, about 15 messages | fragments two levels |
| Activity | about 12 actions, 4 lanes | one level of sub-activity |
| State machine | about 9 states | composite states one level |
| Use case | 4 actors, about 9 use cases | none |

Past the limit, split: one diagram per scenario, per aggregate, per lane group, with the same names in each.
