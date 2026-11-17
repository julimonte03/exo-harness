# Discovery brief

The shape of a discovery outside an SDD change: in the answer, or in the file the person names (for example `docs/discovery/<topic>.md`). Keep the headings; write `Open question:` where the evidence is missing. The example is synthetic: an internal web app to book meeting rooms.

## Template

```markdown
# Discovery: <topic>

## Job to be done

When <situation>, <user role> wants to <job>, so they can <outcome>.

- Today: <the workaround and what it costs, with sources>
- Frequency: <how often, for how many, with sources, or an open question>

## Hypotheses

| # | Kind | We believe | Evidence | Status |
|---|---|---|---|---|
| H1 | value | ... | ... | assumed (riskiest) |

Riskiest: H1. Test: <the cheapest method that gives a real answer>.

## Success metrics

| Metric | Baseline | Target | When | Source |
|---|---|---|---|---|
| Primary: ... | ... | ... | ... | ... |
| Guardrail: ... | ... | must not rise | ... | ... |

## User flows

<numbered steps, or a mermaid flowchart, with the failure paths>

## Acceptance criteria

#### <title>
- Given ...
- When ...
- Then ...

## MVP scope

- In: <the thin slice>
- Later: <item>: <why it can wait>
- Exit criteria: <what result continues, changes course or stops>

## Open questions

1. <question>: <why it matters>. Default if unanswered: <assumption>.
```

## Example

```markdown
# Discovery: recurring room bookings

## Job to be done

When a team lead sets up a weekly team meeting, they want to book the same room at the same time for the coming weeks in one go, so the team keeps its room and nobody rebooks it by hand every week.

- Today: leads book each week by hand (src/bookings/create.py:57 takes one date only); the help desk log shows "my weekly room was taken" as a common complaint.
- Frequency: Open question: how many bookings repeat weekly today.

## Hypotheses

| # | Kind | We believe | Evidence | Status |
|---|---|---|---|---|
| H1 | value | Team leads would set up at least one recurring booking a month | Help desk complaints about lost weekly rooms | assumed (riskiest) |
| H2 | usability | "Repeat weekly until <date>" on the booking form is clear enough | The form already has a date picker (src/web/BookingForm.tsx:30) | assumed |
| H3 | feasibility | Each occurrence can be stored as a normal booking with a series ID | Bookings are independent rows (src/bookings/model.py:12) | supported |
| H4 | viability | Long series will not block rooms other teams need | None | assumed |

Riskiest: H1. Test: ship weekly repeats up to 12 weeks, and count series created in the first month.

## Success metrics

| Metric | Baseline | Target | When | Source |
|---|---|---|---|---|
| Primary: share of weekly meetings booked as a series | none yet | at least 50% (proposal) | 30 days after release | the bookings table: rows with a series ID |
| Guardrail: help desk tickets about rooms blocked by unused series | 0 | must not rise above 2 a month | from release | the help desk log |

## User flows

1. The lead fills in the booking form and ticks "repeat weekly until" with an end date.
   1a. The end date is more than 12 weeks away: "a series can last up to 12 weeks". Back to 1.
2. The system checks every occurrence is free.
   2a. Some are taken: it lists them and offers to book only the free ones, or to cancel.
3. The system saves the series and shows each date booked.

## Acceptance criteria

#### A weekly series is booked
- Given the room "Atlas" is free every Tuesday from 10:00 to 11:00 for the next four weeks
- When the lead books it weekly until the fourth Tuesday
- Then they see four bookings confirmed, one per Tuesday

#### A series with a taken date
- Given the room "Atlas" is booked by someone else on the second Tuesday
- When the lead books it weekly for four Tuesdays
- Then they see that the second Tuesday is taken
- And they can book the three free Tuesdays or cancel

## MVP scope

- In: weekly repeats up to 12 weeks, the conflict list, cancelling the whole series.
- Later: other frequencies (every two weeks, monthly); cancelling a single occurrence (needs H1 first); releasing unused series automatically (needs H4 data).
- Exit criteria: fewer than 10 series in the first month means recurring bookings are not the main problem; look at the complaints again.

## Open questions

1. Who may book a series: anyone, or only team leads? It changes the permission check. Default if unanswered: anyone who may book the room.
```
