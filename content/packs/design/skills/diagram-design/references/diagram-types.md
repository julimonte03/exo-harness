# Choosing the diagram type

Start from the question, never from the diagram you like to draw. If two types fit, pick the one with fewer elements for the same answer.

## The eight main types

### System context

- **Answers:** who uses the system, and which other systems it depends on or feeds.
- **Elements:** the system in focus (one box), people and roles, external systems. No technology, no internal parts.
- **Signs it fits:** a new reader, an executive audience, a scope discussion, an integration inventory.
- **Signs it does not:** the question is about how the system is built inside (containers) or in what order things happen (sequence).
- **Mermaid:** a flowchart with C4 roles, or `C4Context` when the project already uses the C4 syntax.

### Containers

- **Answers:** which separately runnable or deployable pieces make up the system (applications, services, databases, queues, front ends, jobs) and how they talk.
- **Elements:** containers with their technology, data stores, queues, the people and external systems from the context that touch them. Protocols on the connectors.
- **Signs it fits:** onboarding developers, deciding where a change lands, reviewing integration styles.
- **Signs it does not:** a single deployable with internal modules: that is a components diagram.

### Components

- **Answers:** what is inside one container: its main modules, their responsibilities and the dependencies between them.
- **Elements:** components of one container only, plus the containers and systems they call.
- **Signs it fits:** a refactor, a review of a module boundary, a complex service.
- **Signs it does not:** the audience is executive (too much detail), or the code structure changes weekly (it will be wrong soon; link the code instead).

### Sequence

- **Answers:** in what order the parties act in one scenario, including the replies and the failure path that matters.
- **Elements:** participants (people, containers, systems) across the top, messages in time order, optional and alternative fragments, activation where it helps.
- **Signs it fits:** an integration, an authentication flow, a timeout or retry discussion, an incident timeline across services.
- **Signs it does not:** several scenarios at once (draw one per scenario), or the order does not matter (a containers diagram is enough).

### Flow

- **Answers:** which steps and decisions a process follows, and, with lanes, who does each step.
- **Variants:**
  - **Flowchart** for an algorithm or a simple process.
  - **UML activity** when there is parallel work (fork and join).
  - **BPMN with lanes** when roles, handoffs and waiting matter (a business process, an approval).
- **Elements:** a start, steps as verb phrases, decisions as questions with labeled exits, an end for each outcome.
- **Signs it does not:** the thing has states that persist between events (a state machine), or the question is who calls whom (sequence).

### State machine

- **Answers:** which states one thing can be in (an order, a payment, a ticket) and which events move it between them.
- **Elements:** states as adjectives or nouns ("Paid", "Shipped"), transitions labeled `event [guard] / action`, an initial state, final states.
- **Signs it fits:** status fields in the code, lifecycle rules, "can it go from X to Y?" questions.
- **Signs it does not:** the steps are actions of people, not states of a thing (a flow).

### Deployment

- **Answers:** where the containers run: environments, nodes, clusters, regions, network zones, and what crosses each boundary.
- **Elements:** deployment nodes nested by level (environment, region, cluster, node), the container instances in each, the network boundaries, load balancers and gateways.
- **Signs it fits:** infrastructure as code, an operations audience, availability or latency questions, a security review of network zones.
- **Signs it does not:** the audience is executive and the question is only "what talks to what" (containers).

### Data

- **Answers:** which data exists and how it is related (entity-relationship), or how data moves and where it is stored (data flow).
- **Elements, entity-relationship:** entities, key attributes only, relations with cardinality (crow's foot), ownership by service when several services share a store.
- **Elements, data flow:** external entities, processes, data stores and the flows between them, labeled with the data they carry. The threat model uses this form with trust boundaries.
- **Signs it fits:** schema design, a migration, data ownership, privacy questions (where personal data goes).

## Less common types

| Type | Answers | Notes |
|---|---|---|
| Timeline | What happens when: milestones, a roadmap, an incident | Mermaid `timeline` or `gantt`; dates as `YYYY-MM-DD`; at most about ten milestones |
| Swimlane | Who does which step, with handoffs | A flow with lanes; in Mermaid, one `subgraph` per lane |
| Quadrant | How items compare on two dimensions | Mermaid `quadrantChart`; label the axes with both ends ("Low effort", "High effort") |
| Layer stack | Which layers a platform has and what each provides | Stacked boxes, top to bottom from the user to the infrastructure |
| Decision tree | Which option follows from a few questions | A flowchart with questions as decisions and options as end points |
| Class | How types in the code relate | skill:uml-visual-designer |
| Use case | Who can do what with the system | skill:uml-visual-designer |
| Mind map | How ideas group | Mermaid `mindmap`; fine for workshops, weak for decisions |

## When the question is not clear

Offer the person two or three questions the diagram could answer, each with the type it leads to:

> "Which of these should the diagram answer? (1) Who uses the order system and what it connects to — a context diagram. (2) Which services make it up and how they talk — a containers diagram. (3) What happens when a customer places an order — a sequence diagram."

## Several diagrams

When the person needs a set (an architecture overview, an onboarding pack), build it as levels that zoom in: context, then containers, then the one or two components diagrams that matter, plus the sequence of the main scenario. Each diagram links to the next level, uses the same names for the same elements, and stays within 7±2 primary elements.
