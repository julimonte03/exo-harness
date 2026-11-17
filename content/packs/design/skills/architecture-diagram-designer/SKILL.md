---
name: architecture-diagram-designer
description: >-
  Builds architecture diagrams of a system, C4 system context, containers
  and components plus deployment, from the code or from design.md, in the
  executive style of the design pack (neutral by default, .exo/brand.json
  when present). Every element and relation that comes from the code cites
  the path:line it was found at, in the diagram source and in an evidence
  table; what the code cannot confirm is drawn dashed and asked, never
  invented. Uses the project's diagram tool, Mermaid by default. Inside an
  SDD change it hands the diagrams to the phase that owns the document. Use
  it when someone wants to see how a system is built, what it talks to,
  where it runs, or to document the architecture of a repository or a
  design. Triggers: "architecture diagram", "C4 diagram", "context diagram",
  "container diagram", "component diagram", "deployment diagram", "draw our
  architecture", "map the services", "how is this system built",
  "visualize the design".
metadata:
  exo-pack: design
  exo-execution: inline
  exo-permissions: write-specs
---

# architecture-diagram-designer

An architecture diagram is a claim about the system. This skill draws only what the code or the design says, shows where each piece comes from, and keeps each view to one level of zoom.

## Result

- One diagram per C4 level the question needs (context, containers, components of one container, deployment), in the project's diagram tool, styled with `.exo/shared/executive-style.md`.
- **Evidence:** a `[Code] path:line` comment next to each element and relation in the diagram source, and an evidence table under the diagram (element or relation, source, confidence). Elements from design.md cite `[Doc] path`.
- **Open questions:** each unconfirmed element or relation, drawn dashed with "(inferred)" in its label, and asked in the answer.
- Saved where the project keeps architecture diagrams, or returned as text to the phase that owns the document.

## When

| Moment | What you do |
|---|---|
| Someone asks to see or document the architecture | Build the levels the question needs from the code |
| SDD design phase, a change with a new container, integration or deployment | Draw the target architecture from the design draft and give it to `sdd-design` for design.md, Architecture Overview |
| Adoption of an existing repository | Draw the as-is architecture from the code and from `.exo/discovery/` when it exists |
| A review of drift | Compare the diagrams the repository has with the code and list what changed |

- **Not for:** flows, states and data diagrams (skill:diagram-design); UML classes, sequences and use cases (skill:uml-visual-designer); the threat model's data flow (the `threat-modeling` skill of the `security` pack).
- **Build on skill:diagram-design** for the type, the tool, the readability rules, the styling and the first-use approval of the style. Read its `SKILL.md` before the first diagram.

## Levels

| Level | Question | Shows | Leaves out |
|---|---|---|---|
| System context | Who uses the system, and what does it depend on or feed? | The system as one box, people, external systems | Technology, internals |
| Containers | Which runnable pieces make it up, and how do they talk? | Applications, services, front ends, jobs, databases, queues, with technology and protocols | Classes, modules |
| Components | What is inside one container? | The main modules of that container and what they call | Other containers' internals |
| Deployment | Where does it run? | Environments, regions, clusters, nodes, network zones, the container instances in each | Code structure |

- Start at the level the question asks for; when unclear, offer context plus containers.
- Draw components for the one or two containers that matter, never for all of them.
- Keep names identical across levels: the box "Orders API" in the containers view is the boundary "Orders API" in its components view.

## Steps

### 1. Scope

Write the question, the audience, the level or levels, and the boundary of "the system": a repository, a set of repositories, or a product. Say what is out of scope.

### 2. Sources

In this order, and say which ones you used:

1. **design.md** of the change, when the diagram is for a design: the target architecture. The code then shows only the current state.
2. **The code and its configuration:** deployment descriptors, manifests, entry points, clients, connection settings. Where to look for each kind of element is in `references/code-evidence.md`.
3. **The project's documents:** existing diagrams, ADRs, `.exo/context.md`, and in an adopted repository `.exo/discovery/` (the inventory and the extracted units).
4. **The person**, for what none of the above says.

Read 1 to 3 files inline. For a broad read (several services, many manifests), delegate it to a read-only explorer when the agent has one (`sdd-explorer` when the `sdd` pack is installed) with the list of what to find, or read in small batches and summarize as you go. Never run the system, its build or its containers to discover the architecture: read only.

### 3. Inventory

List before drawing, each with its evidence:

- **People and roles** that use the system (from authentication roles, user-facing entry points, the README).
- **External systems:** third-party APIs, other teams' services, identity providers, payment and email services (from HTTP clients, SDK dependencies, configuration keys).
- **Containers:** each deployable unit, its technology and its responsibility (from build files, deployment descriptors, entry points).
- **Data stores and queues:** databases, caches, buckets, topics (from drivers, connection settings, migrations, infrastructure as code).
- **Relations:** who calls whom, synchronous or asynchronous, the protocol, and what flows (from clients, routes, producers and consumers).
- **For components:** the modules of the container and their dependencies (from the package structure and imports).
- **For deployment:** environments, regions, clusters, nodes and network zones (from infrastructure as code and deployment manifests).

### 4. Evidence and confidence

| Marker | Meaning |
|---|---|
| `[Code] path:line` or `[Code] path:start-end` | Seen in the code or its configuration |
| `[Doc] path` | Stated in a document of the project |
| `[Inferred: high\|medium\|low]` | Deduced: a naming convention, an environment variable whose target is not in the repository |

- **Cite the place, never the value.** A connection setting is `[Code] config/settings.py:22 (ORDERS_DB_URL)`, the name of the variable, never its content.
- **Inferred elements** are drawn dashed with "(inferred)" in the label, and each one becomes a question for the person. Low confidence never goes on an executive diagram without the person's confirmation.
- **Never invent** a container, a relation or a technology to complete a level. A gap stays a gap, said in a note.

### 5. Draw

1. Pick the tool and apply the style as skill:diagram-design says, including the first-use approval.
2. Use the C4 roles of the contract (`.exo/shared/executive-style.md`, section D): the system or container in focus in `primary`, its insides in `primary_tint`, people in `secondary`, external systems in `neutral_fill`, the one highlight in `accent`.
3. Templates for each level, in Mermaid and PlantUML, are in `references/c4-templates.md`. In Mermaid, use a flowchart with C4 roles by default: it renders on more hosts and takes the style better than the experimental C4 syntax, which you use only when the project already does.
4. Put the evidence of each element and relation as a comment in the source, on the line before it.
5. Label every relation with a verb phrase and, from the containers level, the protocol.
6. Keep 7±2 primary elements. A system with more containers gets an overview with groups (by domain or by team) and one containers view per group.

### 6. Evidence table and questions

Under each diagram:

```markdown
| Element or relation | Source | Confidence |
|---|---|---|
| Orders API (Python, FastAPI) | [Code] services/orders/pyproject.toml:8; [Code] services/orders/app/main.py:14 | high |
| Orders database (PostgreSQL) | [Code] services/orders/app/db.py:9 (ORDERS_DB_URL); [Code] deploy/compose.yaml:31 | high |
| Orders API → Payments service | [Code] services/orders/app/payments_client.py:20 (PAYMENTS_BASE_URL) | medium: the target of the variable is not in the repository |
| Warehouse system consumes order events | [Inferred: low] topic name `orders.created` in services/orders/app/events.py:12 | low |
```

Then the open questions, one per unconfirmed element or relation.

### 7. Hand over

- **Outside a change:** show the diagrams, the evidence and the questions; save them after the person agrees, where the project keeps architecture diagrams (`docs/architecture/`, `docs/diagrams/` or the folder already used), or embedded in the README or ADR that needs them.
- **Inside an SDD change:** design.md belongs to `sdd-design` (`.exo/shared/sdd-phase-common.md`, section C). Return the diagram and its evidence as text for its Architecture Overview, or save the diagram outside the change folder and let the phase link it. Never edit a phase artifact yourself.
- **Before an executive audience:** offer skill:executive-visual-quality-gate. **Before it leaves the team:** skill:secure-diagram-sanitizer (pack `security`); when it is not installed, say `security/secure-diagram-sanitizer not installed — applying inline criteria`, replace internal hostnames, URLs, IP addresses, ports and account, repository and environment names with consistent generic labels, and keep the list of replacements out of the shared piece.

## Return

```markdown
**The order platform: three services behind one gateway** (containers, as of 2026-11-17; saved in docs/architecture/containers.md)

Sources: the code at `<commit>` (compose file, three service manifests, clients); no design.md.
Elements: 6 containers, 2 external systems, 1 person; 1 relation inferred (dashed).
Evidence: table under the diagram, `[Code]` comment per element in the source.
Questions:
1. Does the warehouse system consume `orders.created`? Only the topic name suggests it (services/orders/app/events.py:12).
2. Where does PAYMENTS_BASE_URL point in production? The repository does not say.
Style: neutral, approved earlier (memory). Contrast: all pairs pass.
Next: a components view of the Orders API, if you want the zoom.
```

## Record

Inside an SDD change, a phase that runs inline records the skill before its envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it.

```bash
exo change record <change> --add capabilities_used '{"name": "architecture-diagram-designer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"architecture-diagram-designer"'
exo change record <change> --add knowledge_used '{"source": "code", "ref": "deploy/compose.yaml:31"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Each diagram is one C4 level and answers the question of its level.
- [ ] Every element and relation from the code has its `[Code] path:line` in the source and in the evidence table; values of settings are never copied, only their names.
- [ ] Nothing invented: unconfirmed items are dashed, marked "(inferred)" and asked.
- [ ] Names are identical across levels, the code and the documents.
- [ ] 7±2 primary elements per view; every relation labeled with a verb, and with the protocol from the containers level.
- [ ] Style from `.exo/shared/executive-style.md`, approved on first use, contrast checked, style marker in the source.
- [ ] Inside a change, the diagrams went to the phase that owns the document; no phase artifact was edited.
- [ ] Nothing sensitive in the piece; sanitized before it leaves the team.
