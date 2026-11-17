# Audit rubric

The checks of step 3 of `skill-improver`, one table per dimension, with the usual finding and its fix. Severity follows step 4 of the skill: High for harm or a broken contract, Medium for misfires and inconsistent results, Low for readability.

## 1. Description and triggers

| Check | Typical finding | Fix |
|---|---|---|
| Says what it produces | "Helps with releases" | Name the result: "Writes release notes from the commits since the last tag, grouped by type" |
| Says when | No "Use it when" | Add the situations in the asker's words |
| Real triggers | None, or single words ("release", "notes") | Five to eight full phrases people type |
| Specific | Loads on any mention of a common word | Narrow the situations; add what it is not for |
| No overlap | Claims requests a neighbor handles | Draw the line in both descriptions, or drop the trigger |
| Within 1024 characters | Validator error | Cut adjectives and second examples |
| No "always use" wording | "MUST be used for every change" | Say when it applies instead; a reviewer flags load-on-everything wording |

**Overlap test:** take each trigger and each neighbor's description. If a person typing the trigger could reasonably want the neighbor, the trigger is ambiguous.

## 2. Frontmatter and metadata

| Check | Typical finding | Fix |
|---|---|---|
| Only standard top-level fields | `triggers:` or `permissions:` at the top level | Move to the description, or to `metadata` with the `exo-` prefix |
| Name equals the folder | `name: release_notes` in `release-notes/` | kebab-case, equal to the folder |
| `exo-pack` true | Says `core`, lives in another pack | Fix the value (engine content only) |
| `exo-execution` true | `subagent` without `exo-subagent`, or a skill that talks with the person declared as a subagent | Fix the pair; subagents cannot ask the person |
| `exo-permissions` true | `read-only` but a step writes a file; `write-code` but it only writes docs | The value that matches the most the body does |

## 3. Structure and size

| Check | Typical finding | Fix |
|---|---|---|
| Result first | The skill opens with background | Move the result to the top, in a few lines |
| When, with what it is not for | Only positive cases | Add the near misses and their skills |
| Numbered steps | A wall of prose | One step per action, each with its default and stop condition |
| Return with an example | No output format | A short synthetic example of the output |
| Record (inside a change) | Missing, or uses a field the schema does not have | The `exo change record` commands of `capability-attribution.md` |
| Closing checklist | Missing | Verifiable boxes, one per key rule |
| Size | Over 500 lines (validator warning), or over 300 with long examples | Move details to `references/`, one topic per file |

## 4. Steps

**Vague words** that hide a decision:

| Vague | Ask | Replace with |
|---|---|---|
| "Handle errors appropriately" | Which errors, and what then? | "If the build fails, stop and show the first error; do not retry" |
| "Ensure quality" | Checked how? | "Run `<test command>`; it must pass" |
| "As needed", "if necessary" | Decided by whom, from what signal? | The condition: "when the diff touches a migration" |
| "Etc.", "and so on" | What else, exactly? | The complete list, or "for example" with the rule |
| "Use best practices" | Which ones? | The two or three practices that matter here |
| "Properly", "correctly" | Against what? | The criterion or the source |

**Other step findings:**

- A question without a default: the agent stalls or guesses. Add the default and what to do in an unattended run.
- A failure without a stop condition: the agent improvises. Say: ask once, stop with `needs-input`, or degrade and say so.
- A command without exact flags or paths. Write the real command.
- Steps out of order: a step uses what a later step produces.
- A decision that belongs to the person (lowering a tier, dismissing a finding, pushing, deleting) taken by the agent. Make it a question.

## 5. Examples

| Check | Typical finding | Fix |
|---|---|---|
| Present | Rules with no example | One short example per important rule |
| Short | 80-line example inside `SKILL.md` | An excerpt there; the full example in a reference |
| Consistent | The example breaks a rule of the skill (an invented ID, a missing section) | Fix the example; readers copy examples, not rules |
| Synthetic | A real-looking email, token or card number | `<placeholder>` values; no test card numbers either |

## 6. Limits and safety

| Check | Typical finding | Fix |
|---|---|---|
| Says what it never does | No limits section | A Rules section with the hard limits |
| Destructive commands confirmed | Deletes, resets or force-pushes without asking | Ask first; never force-push or skip hooks |
| Data protection | Logs or tickets pasted to the model as they are | Clean them first (`data-protection.md`) |
| Installs nothing | "Install the scanner with ..." as a step | Name the command for the person, then continue by hand |
| Nothing the validator flags | Download-and-run, sending data out, asking for credentials, hidden text | Remove it; describe attacks without the literal phrase |
| No vendor lock-in | A step that requires one organization's tool | Make it optional, with an open fallback |

## 7. Coherence with the contracts

| Contract | Check |
|---|---|
| `sdd-phase-common.md`, section C | A non-phase skill never writes a phase's artifact; it returns text, or writes its own files outside the change folder |
| `phase-skill-map.md` | The trigger in the skill matches the map's row; a skill of an optional pack named by the map has its inline criteria row |
| `skill-resolver.md` | Degradation uses the exact sentence `<pack>/<skill> not installed — applying inline criteria` and records `"resolution": "none"` |
| `capability-attribution.md` | Record commands use real fields and real values (`activation`, `resolution`); subagents never record |
| `data-protection.md` | No Critical data anywhere; Restricted data only under a waiver; Internal data only to the organization's own systems |
| Tickets (`tickets.pattern`) | No invented IDs; IDs the person gives are checked against the pattern; no tracker named as a requirement |
| CI and review | No host required; host examples marked as examples |
| Language | Everything installed in projects is in English |

## 8. References

| Check | Typical finding | Fix |
|---|---|---|
| `skill:` resolves | Points at a skill of a pack not declared in `requires` or `optional` | Backticks with the pack and the degradation sentence |
| Shared paths reachable | Cites a contract of a pack its own pack does not require | Cite it by name with its pack, and degrade when it is missing |
| Cited files exist | `references/<file>` cited but missing | Create it or fix the path |
| No orphans | A reference nobody cites | Cite it where it helps, or delete it |
| One level deep | A reference that sends the reader to another reference | Merge, or cite both from `SKILL.md` |
