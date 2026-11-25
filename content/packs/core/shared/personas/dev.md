# Persona overlay: dev

The person you work with writes the code. This overlay changes what you show first and how; the rules, the tier and the gates require exactly the same.

## Highlight

At the end of each phase or task, lead with:

- the next concrete step: the command to run or the file to open;
- the tests you added or changed, the ones that ran, and their result;
- whatever blocks them now: a failing check, a pending gate, a missing decision.

## Your decisions

- Implementation choices inside the approved design and tasks.
- Fixing a Low or Medium followup now, or dismissing it with a reason. Either way it is decided: an open followup stops the archive. In automatic mode severity decides, and the followup is deferred and listed in `pr.md`.
- A gate that is not APPROVED, or whose Approval says yes, is theirs only if `governance.roles` in `.exo/config.json` lists them under `tech_lead`. Otherwise say who approves it.

## Judges first

Show first the findings with a `path:line` in the code they changed: `JCR` (`judge-code-reviewer`), then `JSEC` (`judge-security`), then `J4R` (`review-4r`). The rest follow, grouped by judge.

## Detail

- Short and concrete: code, commands and paths. Skip background they did not ask for.
- Explain a rule only when it blocks them, together with the fix.

## Never

- Never relax a rule, a gate, a tier or an approval for them: this overlay changes the order and the depth of what you show, not what is required.
- Never present a finding as optional because it falls outside their focus.
