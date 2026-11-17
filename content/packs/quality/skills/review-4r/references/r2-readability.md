# R2 Readability

**The question:** can the next person understand this change and safely change it again?

Only readability and maintainability. Whether the code works is R3's; how it fails is R4's.

## Look for

| Area | Look for |
|---|---|
| Names | Names say what a thing is or does; no abbreviations only the author knows; the same concept has the same name everywhere |
| Size and purpose | Each function does one thing; a function that needs "and" to describe it should be split |
| Complexity | Deep nesting, long chains of conditions, flags that change what a function does; early returns where they help |
| Duplication | Logic copied instead of reused; a second way of doing something the code base already does |
| Leftovers | Dead code, commented-out blocks, debug prints, unused imports and parameters |
| Comments | They explain why, not what; none contradicts the code; public functions say what they promise |
| Magic values | Numbers and strings with meaning get a name |
| Types and contracts | Inputs and outputs are explicit (types, data classes, schemas) rather than loose dictionaries or internal attributes |
| Conventions | The change follows `.exo/context.md` and the code around it: layout, naming, error style, test style |
| Messages | Errors and output tell the reader what happened and what to do |

## How to judge

- Read the change as someone who has to modify it next month, without the author at hand.
- Compare with the neighbors: a style that differs from the file it lives in is a finding even if it is a good style elsewhere.
- Prefer one finding per pattern, with its locations, over the same finding many times.

## Severity

- Low by default: naming, comments, small duplication, leftovers that do not change behavior.
- Medium: complexity or duplication that makes the next change likely to break something; a contract so loose that callers must read the implementation.
- High only when the readability problem hides a defect; then say which defect, so R3 or R4 can own it.
