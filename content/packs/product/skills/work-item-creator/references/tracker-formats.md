# Tracker formats

Examples of how the tracker-neutral item of `references/item-format.md` lands in three common trackers and in a generic CSV. They are examples of format, not integrations: this skill never connects to a tracker. Every tracker-specific detail here is **[Not verified]**: field names, required columns and text formatting change with each tracker's version, process template and configuration. The person compares the file with their import screen before loading it.

## Ticket patterns

The ID format comes from `tickets.pattern` in `.exo/config.json`, never from the tracker's name. Common shapes, as the engine suggests them:

| Example | Pattern | Seen in |
|---|---|---|
| `PROJ-123` | `[A-Z][A-Z0-9]*-\d+` | Jira and many others |
| `#123` | `#\d+` | GitHub, GitLab |
| `AB#123` | `AB#\d+` | Azure Boards references from commits |

The tracker assigns the number. The skill only checks an ID the person brings back.

## CSV rules for every tracker

- UTF-8, one header row, one row per item.
- Quote a field that has a comma, a quote or a line break, and double the quotes inside it: `"Shows ""expired"" and keeps the total"`.
- Multi-line fields (description, acceptance criteria) stay in one quoted field, with line breaks inside.
- Plain lines with `-` bullets read well in every tracker; rich formatting in imported text depends on the tracker.
- Leave the ID column empty, or leave it out, for new items.

## Jira [Not verified]

The CSV importer maps each column to a field in a wizard, so the header names can be the team's; the usual ones:

```csv
Summary,Issue Type,Description,Labels,Parent,Story Points
"Apply percentage coupons to the cart total",Story,"Goal: shoppers see the discount of a valid coupon in their total before paying.
Scope:
- 1. Apply a percentage coupon to a cart total (src/coupons/rules.py)
Acceptance criteria:
- Given a cart of 80.00 and a valid 10% coupon, When the coupon is applied, Then the total is 72.00.
- Given a 0% coupon, When applied, Then the total stays 80.00.
Blocked by: none",coupons,PROJ-123,2
```

- **Parent:** the epic or parent issue key the person confirmed (`ticket_key`); the field that holds it differs between project types.
- **Story points** is usually a custom field; map the column to it in the wizard, or leave it out.
- **Sub-tasks** created in the same file need an internal ID column and a parent ID column that the wizard links; when in doubt, import the parents first and the sub-tasks after.
- **Dependencies** ("is blocked by") are links that the importer may not create: keep them in the description as `Blocked by: WI-1`, and the person links them once the keys exist.
- **Test cases:** a test management add-on has its own import format. Without one, keep them in the description under `Test cases:`.

## Azure Boards [Not verified]

The work item import takes a CSV whose headers are field display names. `Work Item Type` and `Title` are required:

```csv
Work Item Type,Title,Description,Acceptance Criteria,Story Points,Tags
User Story,"Reject expired coupon codes","Goal: shoppers get a clear refusal for an expired coupon.
Scope:
- 2. Load a coupon by code and reject expired ones (src/coupons/store.py)
Blocked by: none","- Given a coupon whose end date was yesterday, When a shopper enters its code, Then they see ""This coupon has expired"".
- Given an unknown code, When entered, Then they see ""We do not recognize this code"".",3,coupons; PROJ-123
```

- **The kind and the estimate depend on the process:** User Story and Story Points in Agile, Product Backlog Item and Effort in Scrum, Requirement and Size in CMMI. Use the ones the project has.
- **Acceptance Criteria** is its own field in the Agile and Scrum processes; elsewhere, append the criteria to the description.
- **Tags** are separated by semicolons.
- **Hierarchy:** the importer can build a tree from numbered title columns (`Title 1` for the parent, `Title 2` for its children). Without it, the person links parents after the import.
- **Commits** reference a work item as `AB#<id>`, which is why projects on Azure Boards often use the pattern `AB#\d+`.

## GitHub Issues [Not verified]

GitHub has no CSV import for issues. The person creates each issue in the web interface, pasting the item as Markdown, or with the host's CLI. Give one Markdown file per item, or one file with a section per item:

```markdown
**Goal:** shoppers can enter a coupon at checkout and pay the discounted total.

**Scope**
- [ ] 3. Accept a coupon code at checkout (src/api/checkout.py, tests/test_checkout.py)

**Acceptance criteria**
- Given a valid coupon, When the shopper submits it at checkout, Then the order is charged the discounted total.
- Given an expired coupon, When the shopper submits it at checkout, Then the order is not placed and the refusal is shown.

**Blocked by:** WI-1, WI-2 (replace with the issue numbers once they exist)

**Links:** specs/PROJ-123-add-coupons/tasks.md (Unit C)
```

- **Title:** in the issue's title field, not in the body.
- **Labels** have to exist in the repository before an issue can use them.
- **Parent and dependencies:** link sub-issues or write `Blocked by #<n>` once the numbers exist.
- **With the CLI,** the person may run `gh issue create --title "<title>" --body-file <file>` for each item. This skill shows that command when asked and never runs it.

## Generic CSV

For any other tracker, or as a neutral export the person adapts:

```csv
Ref,Kind,Title,Parent,Goal,Scope,Acceptance criteria,Estimate,Blocked by,Labels
WI-1,story,"Apply percentage coupons to the cart total",PROJ-123,"Shoppers see the discount of a valid coupon in their total before paying.","- 1. Apply a percentage coupon to a cart total","- Given a cart of 80.00 and a valid 10% coupon, When applied, Then the total is 72.00.
- Given a 0% coupon, When applied, Then the total stays 80.00.",,none,coupons
WI-3,story,"Accept a coupon code at checkout",PROJ-123,"Shoppers can enter a coupon at checkout and pay the discounted total.","- 3. Accept a coupon code at checkout","- Given a valid coupon, When submitted at checkout, Then the order is charged the discounted total.",,"WI-1, WI-2",coupons
```

## Markdown for any tracker

When the tracker has no import, or the team prefers to paste: the Markdown of `references/item-format.md`, one section per item. Every tracker accepts plain text, and the person keeps control of what goes in.
