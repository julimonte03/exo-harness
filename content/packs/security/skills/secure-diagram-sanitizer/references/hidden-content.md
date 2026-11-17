# Hidden content, per format

What a viewer, or anyone who gets the file, can reach besides the rendered picture. Check each place for the format at hand; when a place cannot be checked here, list it under Not checked.

## Diagram sources

| Format | Places |
|---|---|
| Mermaid | `%%` comments; `accTitle` and `accDescr`; `click` lines with links or callbacks; `link` lines; notes; subgraph titles; the init block (fonts and theme only, usually harmless) |
| PlantUML | `'` and `/' … '/` comments; `note` blocks; `legend`, `header`, `footer`, `caption`; `[[link]]` URLs on elements; `!include` paths; sprite and image references |
| Structurizr DSL | `//` and `#` comments; descriptions, `url` properties, `properties { }` blocks, `perspectives`, documentation and decision folders the workspace links |
| draw.io | labels; tooltips; links on shapes; custom data properties (Edit Data); hidden layers; other pages of the same file; the diagram embedded in a `.drawio.svg` or `.drawio.png` |

Remove source comments in the copy rather than relabeling them, except the style marker (`exo-style:`). A link that points inside the organization goes; a link to a public standard may stay.

## Images

| Format | Places |
|---|---|
| SVG | `<title>`, `<desc>`, `<metadata>`, XML comments, `href` and `xlink:href` targets, embedded `data:` images, font names that reveal internal font packages, the editor's attributes (draw.io stores the whole diagram in a `content` attribute) |
| PNG, JPEG | text in the pixels (screenshots, labels); metadata: author, software, file paths, camera and location data; the draw.io diagram inside a `.drawio.png` |

Text in pixels cannot be found by search: look at the image if you can, and otherwise list it as a residual risk. Replace a screenshot with a redrawn diagram when it shows hosts, addresses or names.

## Documents and slides

| Format | Places |
|---|---|
| Markdown | link targets and reference-style link definitions; image alt text and image paths; HTML comments; front matter; embedded HTML |
| Word processors and PDFs | comments; tracked changes; hidden text; headers and footers; document properties (author, company, manager, template path); embedded objects and spreadsheets; bookmarks and hyperlinks |
| Slide decks | speaker notes; hidden slides; comments; the slide master and layouts (logos, footers); alt text of images; embedded charts with their data sheets; document properties |
| Spreadsheets embedded or attached | hidden sheets, rows and columns; named ranges; formulas that reference internal paths; cell comments |

These binary formats usually cannot be edited safely as text here. Give the person the list of replacements and the places to check in their editor (its document inspector removes properties, comments and hidden content), or rebuild the piece as text. Install nothing to open or convert them.

## Around the file

- **The file name and the folder path** of the shared copy: `prd-cluster-a-network.drawio` says too much, and so does a copy that keeps the original's name. Name the copy for its content (`network-overview.shared.drawio`), and ask the person where it goes.
- **The commit or the message** that shares it: the copy may go to the repository only if the person wants it there; its commit message and PR text follow the same rules.
- **Version history:** sharing a file from a repository or a wiki can expose its earlier versions. Share the copy as a new file, not as a new version of the original.
