---
name: cognitive-doc-design
description: >-
  Writes and reviews documentation that is understood on the first read: it
  starts from the reader and the question they bring, leads with the answer,
  goes from the general to the particular, keeps the cognitive load low (one
  idea per paragraph, one name per concept, recognition over recall), puts a
  concrete example next to each rule, and makes the page scannable with
  headings, lists and tables. It fits READMEs, how-to guides, reference
  pages, design notes, RFCs, onboarding guides and long PR descriptions, and
  leaves the sections of SDD artifacts to their phases. Use it when a
  document has to be written, when one feels long, dense or confusing, or
  before publishing docs for reviewers or newcomers. Triggers: "write the
  README", "make this doc easier to read", "this documentation is too
  dense", "restructure this guide", "write an onboarding guide", "review the
  docs for clarity", "nobody understands this page".
metadata:
  exo-pack: core
  exo-execution: inline
  exo-permissions: write-specs
---

# cognitive-doc-design

## Result

- **A document** (new or rewritten) where the first screen says what it is, who it is for and what to do next; the structure follows the reader's questions in order; each section goes from the general to the particular; every rule has an example; and the page scans.
- **Or a review** of an existing document: findings in the order that most improves comprehension, each with its location, the problem, what it costs the reader, and the fix as a before and after. A review edits nothing.

## When

- **Writing** a README, a how-to guide, a reference page, a design note or RFC, an onboarding guide, a troubleshooting page, or a long PR description.
- **Fixing** a document that feels long, dense or confusing, or that makes reviewers and newcomers ask the same questions again.
- **Inside an SDD change,** when a phase asks for clearer text: apply these criteria to the text inside the sections of its artifact, never to the sections themselves, which the templates fix (`.exo/shared/sdd-phase-common.md`, section C).
- **Not for:** the sections of `pr.md`, which skill:branch-pr owns (this skill can tighten the text inside them); architecture decision records (`architecture-decision-record`, pack `design`); code comments, review comments and team messages (skill:comment-writer); bug reports and feature requests (skill:issue-creation); reference docs generated from code.

## Inputs

1. **The draft or the existing document,** and where it lives.
2. **The reader:** their role, what they already know, what they must be able to do after reading, and how they arrive (a search, a link, an onboarding list). Ask once; the default is a developer new to the project.
3. **The facts:** the code, the commands (`.exo/context.md`) and the behavior the document describes. Check every claim against the project (skill:context-retrieval): a document with a wrong command is worse than none.
4. **The project's conventions:** the existing docs structure, tone and language. Keep them.

## Steps

The techniques with before-and-after examples are in `references/techniques.md`; skeletons for each kind of document in `references/doc-shapes.md`.

### 1. Name the reader and their question

Write one line: "`<reader>` comes here to `<question or task>`; after reading, they can `<outcome>`." With several readers, either one document per main question, or a short router at the top ("Setting up for the first time? Start at Install.").

### 2. Pick one mode per page

| Mode | The reader wants to | Shape |
|---|---|---|
| Tutorial | learn by doing, once | a guided path with a working result |
| How-to | get a task done | numbered steps, each with its expected result |
| Reference | look up a fact | tables and lists, complete and dry |
| Explanation | understand why or how | prose that builds from the big picture |

Mixing modes is the most common cause of a dense page: a how-to that stops to explain history, a reference that teaches. Split them and link them.

### 3. Lead with the answer

- The first lines say what this is, who it is for, and the shortest path: the one command, the main decision, the key number.
- Prerequisites and applicability (versions, platforms, permissions) come right after, before the steps.
- History, motivation and alternatives go later, or to an explanation page.

### 4. Go from the general to the particular

- Overview, then the main path, then the details, then the edge cases, then the reference.
- **Progressive disclosure:** what most readers need comes first; rare details go lower, to a linked page, or to an appendix.
- Each section opens with its point in one sentence, so a reader can stop there.

### 5. Lower the cognitive load

- **One idea per paragraph,** paragraphs of up to about four lines, short sentences, active voice, and the second person for instructions.
- **One name per concept.** Define a term once, where it first appears; add a glossary when there are more than about five.
- **Recognition over recall.** Repeat the value or the name where it is needed instead of "as mentioned above"; use a table to compare; put the example next to the rule.
- **Chunks:** lists for parallel items; numbered steps for a sequence, one action per step.
- **Signposts:** say what comes and where the reader is ("Three steps: install, configure, check").
- **Cut** hedges, filler, repetition and outdated passages (or mark them as outdated, with a date).

### 6. Add examples

- One concrete, minimal example for each rule, command or option, with its expected output.
- Examples that run: check every command, path and flag against the project.
- Synthetic data only: `<placeholder>` values, `example.com` addresses, no real names, secrets or customer data (`.exo/shared/data-protection.md`).

### 7. Make it scannable

- Headings that say something: a question or a task ("Run the tests locally"), never "Miscellaneous" or "Notes".
- At most three heading levels; a table of contents for long pages.
- Link texts that say where they go, never "click here".
- Code blocks with their language; tables for three or more attributes per item.
- Bold for the few terms a skimming reader must catch, not for emphasis everywhere.
- Diagrams and images with a text description; meaning never carried by color alone.

### 8. Check it

1. **Five-second test:** someone who reads only the title and the first lines knows what this is, whether it is for them, and what to do next.
2. **Cold read:** read it as the reader, with only what they know. Every term is defined before it is used; every step can be done as written.
3. **Facts:** every command, path, flag and number matches the project.
4. **Length:** every section serves the reader's question; the rest is cut or linked.

### 9. Deliver

- **New or small documents:** write them where the person says, or where the project keeps that kind of document.
- **Rewriting a long document:** show the new outline first (old heading → new heading) and rewrite after the person agrees. Keep the meaning: a factual doubt is a question, never a silent change.
- **Review only:** return the findings and edit nothing.

## Return

For a review, a short verdict and the findings, the most helpful first:

```markdown
**Reader:** a developer cloning the repository for the first time. **Verdict:** the setup works, but the reader meets it after three screens of history.

| # | Where | Problem | Cost to the reader | Fix |
|---|---|---|---|---|
| 1 | README.md:1-40 | History and architecture before any setup | Newcomers scroll three screens to find how to run it | Open with one line on what it is and the quick start; move the history to docs/history.md |
| 2 | README.md:52 | "the worker", "the consumer" and "the processor" name the same service | Readers think there are three services | Use "the worker" everywhere; define it once |
| 3 | README.md:60-75 | Setup as a paragraph with five commands inside | Steps get skipped | Numbered steps, one command each, with the expected output |
```

## Rules

- **Facts from the project,** checked. Never document a command or a flag you did not verify.
- **The reader's order, not the writer's.** The structure follows the questions the reader brings, not the order in which things were built.
- **Keep the meaning.** Clarity edits never change what the document says; doubts go to the person.
- **SDD sections are fixed.** Inside a change, only the text within a section changes, and only in the artifact of the phase that asked.
- **The project's voice.** Keep its language, tone and terms unless the person asks to change them.

## Record

Inside an SDD change, when a phase loaded this skill, add it before that phase's envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "cognitive-doc-design", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"cognitive-doc-design"'
```

`activation` is `requested` when the person asked for it. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Outside a change there is no record.

## Before you finish

- [ ] The reader and their question are named, and the page has one mode.
- [ ] The first lines answer what, for whom and what next.
- [ ] Sections go from the general to the particular, each opening with its point.
- [ ] One name per concept; every rule has an example; every example runs.
- [ ] Headings say something; lists, steps and tables replace walls of text.
- [ ] Every command, path and number was checked against the project; the meaning did not change.
