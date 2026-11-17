# Gate format: prompt_spec_review

The gate file is `<change-root>/gates/prompt_spec_review.md`, from `.exo/shared/templates/gate.md`. `exo speclint` checks:

- the marker `<!-- exo-gate:prompt_spec_review -->`, with the same name as the file;
- a Verdict section whose first word is `APPROVED` or `ESCALATED`;
- in Approval, the lines `Requires tech_lead approval: yes|no` and `Source: skill prompt-spec-review`.

Findings has one subsection per mode: `### Design approval`, written in design, and `### Conformance`, added in verify. A rewrite keeps `### Design approval` as it was.

The examples below belong to a synthetic change, `add-volume-discount` (the canvas of `reasons-canvas-author/references/canvas-example.md`).

## Findings table

| Column | Approval mode | Conformance mode |
|---|---|---|
| Severity | the gap's severity, or `-` when there is none | the gap's severity, or `-` |
| File:line | `<change-root>/canvas.md`, with the line when it helps | the code (`path:line`), or the canvas item for a missing file |
| Finding | what is missing, contradicted or vague, and the fix | what the code does against what the canvas says, and the fix |
| Rule/OWASP | the canvas section and item, and the source it disagrees with (`S-3`, `TM-1`, a design.md section) | the canvas section and item (`Operations 4`, `Safeguards 2`, `Structure`, `Norms 1`); add the OWASP item, with its edition (`OWASP A01:2021`, `.exo/shared/judge-common.md`, section D), or the CWE for a security Safeguard |

## 1. Approval mode, approved

```markdown
# Gate: prompt_spec_review

<!-- exo-gate:prompt_spec_review -->

## Verdict

APPROVED: the person approved the canvas as the contract for the code.

## Findings

### Design approval

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| Low | specs/add-volume-discount/canvas.md:44 | Norms 4 could name the log field; kept as is at the person's request | Norms 4 |

Canvas checked against spec.md (2 requirements, 4 scenarios) and design.md: complete and coherent.
Approved by the person on 2026-11-17: "Approve. The tiers and the rounding are exactly what finance asked for."

## Approval

Requires tech_lead approval: no
Source: skill prompt-spec-review
```

## 2. Approval mode, no approval

An unattended run, or the person asked for changes that are not done yet.

```markdown
# Gate: prompt_spec_review

<!-- exo-gate:prompt_spec_review -->

## Verdict

ESCALATED: nobody approved the canvas; the run was unattended.

## Findings

### Design approval

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| - | specs/add-volume-discount/canvas.md | Complete and coherent with spec.md and design.md; waiting for the person's approval | spdd-common, section E |

No explicit approval in this run. A person must approve the canvas before the code is trusted to follow it.

## Approval

Requires tech_lead approval: yes
Source: skill prompt-spec-review
```

## 3. Conformance mode, with gaps

The design approval stays as it was; the conformance result is added.

```markdown
# Gate: prompt_spec_review

<!-- exo-gate:prompt_spec_review -->

## Verdict

ESCALATED: Operations 4 is not implemented and one file is outside Structure.

## Findings

### Design approval

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| - | specs/add-volume-discount/canvas.md | Complete and coherent with spec.md and design.md | spdd-common, section B |

Approved by the person on 2026-11-17: "Approve."

### Conformance

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | src/billing/invoice.py:52 | A discount larger than the subtotal is stored and the total goes negative; Operations 4 asks `close()` to raise `InvalidInvoice` and keep the invoice open. Check before storing | Operations 4; Safeguards 2 |
| Medium | src/billing/report.py:1 | New module that no Operation or Structure item explains (scope creep). Remove it, or bring it into the canvas through a logic correction | Structure |
| Low | src/billing/discounts.py:20 | The helper is named `calc`; the project spells names out | Norms 2 |

Checked: Operations 1 to 6, Norms 1 to 4, Safeguards 1 to 4, against `git diff main...HEAD` (5 files).

## Approval

Requires tech_lead approval: yes
Source: skill prompt-spec-review
```

## 4. Conformance mode, everything holds

```markdown
### Conformance

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| - | - | Every Operation, Norm and Safeguard holds; every changed file is in Structure | - |

Checked: Operations 1 to 6, Norms 1 to 4, Safeguards 1 to 4, against `git diff main...HEAD` (4 files).
```

With only Medium and Low gaps and every changed file in Structure, the rows list them and the Verdict is still `APPROVED`, for example `APPROVED: every Operation and Safeguard holds; 1 Low gap in Norms 2.` The gaps also go to Issues Found of `verify-record.md`.

The Verdict is `APPROVED` only when the design approval was `APPROVED` too; otherwise it stays `ESCALATED` and says that the canvas never had a person's approval.

## Rules

- Quote the person's approval exactly, with the date. Never paraphrase it, and never write one that did not happen.
- Point at locations; never copy secrets or personal data into a finding.
- A verify that runs again rewrites `### Conformance`; a new approval in design rewrites `### Design approval`.
