# Gate: <gate>

<!--
One file per gate: <change-root>/gates/<gate>.md, written by the skill that runs the gate.
Keep the marker below with the gate name (snake_case, the same as the file name):
`exo gate publish` uses it to keep a single PR comment per gate.
-->

<!-- exo-gate:<gate> -->

## Verdict

<!-- APPROVED or ESCALATED, then one sentence of reason: "APPROVED: no blocking finding." -->

## Findings

<!--
| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | src/auth/login.py:42 | User input reaches the SQL query unescaped | A03:2021 Injection |
-->

## Approval

<!--
Requires tech_lead approval: yes | no
Source: skill <skill name>
"yes" when the verdict is ESCALATED or a Critical or High finding stays open.
-->
