# Diagram tools: detect, choose, render

## Detect what the project uses

Search the repository, skipping dependency and build folders (`node_modules`, `vendor`, `dist`, `build`, `.venv`, `target`):

| Tool | Signals |
|---|---|
| Mermaid | ```` ```mermaid ```` blocks in Markdown; `.mmd` or `.mermaid` files; `@mermaid-js/mermaid-cli` or `mermaid` in `package.json`; a Mermaid plugin in the documentation site (`mkdocs.yml` with a `mermaid` custom fence, `@docusaurus/theme-mermaid`, `sphinxcontrib-mermaid`) |
| PlantUML | `.puml`, `.plantuml`, `.iuml` or `.pu` files; ```` ```plantuml ```` blocks; `@startuml` in any file; `sphinxcontrib-plantuml`, `asciidoctor-diagram` or a PlantUML plugin in the build |
| draw.io (diagrams.net) | `.drawio`, `.dio`, `.drawio.svg` or `.drawio.png` files |
| Structurizr | `workspace.dsl` or `workspace.json`; a `.dsl` file that starts with `workspace`; `structurizr` in scripts or CI |
| A diagram service | A Kroki or similar endpoint in the documentation config: the source format it renders (Mermaid, PlantUML) counts as that tool |

Choose:

1. The tool already used **for this kind of diagram**, in the same folder or document set.
2. Otherwise, the tool the project uses most.
3. Otherwise, **Mermaid in Markdown**.

When the project uses a tool that cannot express the type well (Mermaid has no native use case diagram; draw.io diffs poorly in review), say so and offer the alternative the project also has. Never add a second tool on your own: a new tool is the person's decision.

## Mermaid

- **Why it is the default:** the diagram is text in a Markdown block; most Git hosts, wiki engines and documentation sites render it; it shows in review diffs; it needs no install.
- **Version differences:** hosts embed different Mermaid versions. Use the syntax that has been stable for years: `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `classDiagram`, `erDiagram`, `gantt`, `timeline`. Avoid the newest shape syntax (`@{ shape: ... }`) unless the project already uses it. The C4 syntax (`C4Context`, `C4Container`) is still marked experimental: use it only when the project already does.
- **Configuration:** an `%%{init: {...}}%%` line at the top works on most hosts; newer versions also take a `config:` block in a front matter. Use the form the project already uses.
- **Accessibility:** `accTitle: <title>` and `accDescr: <one or two sentences>` inside the diagram give it an accessible name and description.
- **Render, when installed:** `mmdc -i diagram.mmd -o diagram.svg` (mermaid-cli). To check that a block parses without rendering, the host's preview is enough.

## PlantUML

- **Strong at:** every UML type, including use cases, and C4 through the C4 library that ships with PlantUML's standard library.
- **Includes:** use the standard library form, `!include <C4/C4_Container>`. Never `!include` a URL: rendering would fetch code from the network.
- **Style:** `skinparam` lines or a `<style>` block, in the diagram or in one shared file the diagrams `!include` by relative path.
- **Accessibility:** a `title`, and a `caption` or the alt text of the rendered image carrying the text alternative.
- **Render, when installed:** `plantuml -tsvg diagram.puml` (needs Java), or the project's documentation build.

## draw.io (diagrams.net)

- **Strong at:** free layout, large posters, pieces that non-developers edit.
- **Weak at:** review (the XML diffs poorly, compressed files not at all) and keeping style consistent by hand.
- **Edit as text:** keep the file uncompressed (in the editor, File > Properties > Compressed off) so you can read and change the XML. Each shape is an `mxCell` with a `style` string; change only the style and the labels unless the person asks for a new layout.
- **A `.drawio.svg` or `.drawio.png`** carries the diagram inside the image: edit it in the editor, or regenerate the image after changing the source.
- **Render, when installed:** the desktop app's command line, `drawio --export --format svg diagram.drawio`.

## Structurizr

- **Strong at:** C4 as a model: the elements are defined once and several views are generated from them, so names stay consistent across levels.
- **Style:** a `styles` block in the workspace, by tag. Never point `theme` at a URL: write the styles in the workspace.
- **Views:** `systemContext`, `container`, `component`, `deployment` and `dynamic` (a sequence-like view).
- **Render, when installed:** the project's Structurizr tooling (Lite or the CLI); the CLI can also export views to PlantUML or Mermaid for a repository that renders those.

## When nothing renders here

Give the source, the command that would render it, and the visual checks still pending (crossing lines, label overflow, the contrast of the real output). Never install a renderer, a font or a plugin to finish the task.
