# States and copy

Every component that loads, sends or shows data has these states. Design each one before the happy path is polished: they are what people see when something goes wrong.

## Loading

- **Short waits (under about a second):** keep the previous content, dim it or show a small inline indicator. Avoid a spinner that flashes for a moment.
- **First load:** a skeleton with the same shape, size and count as the content, so nothing moves when the data arrives.
- **Long waits:** say what is happening ("Preparing your report, this can take a minute") and let the person leave and come back when possible.
- **Buttons that send:** disabled while pending, with a label that says so ("Saving..."), so nobody sends twice.
- Announce a load that finishes out of view with a polite status message (`role="status"`).

## Empty

Two different situations; name which one it is.

| Situation | Say | Offer |
|---|---|---|
| First use: nothing exists yet | What will appear here and why it is useful | The action that creates the first item |
| No results: a filter or search hides everything | That nothing matches, and which filters are on | One action that widens the result: clear the search, show hidden items, reset filters |

```text
No invoices match your filters.
Paid invoices are hidden.             [Show paid invoices]
```

- Keep the filters visible next to the empty state, so the person sees why.
- An illustration is optional; when present, it is decorative (`alt=""`) and quiet.

## Error

- **What happened, in plain words, and what to do next.** Never a raw status code, a stack trace or an internal message on its own.
- **A way out:** retry, go back, contact support. Keep what the person typed.
- **Where:** next to the field for a field error; at the top of the form, with links to the fields, when there are several; in place for a widget that failed; a page-level message only when the page cannot work.
- Announce it: field errors linked to their field, form and page errors in an alert region.

| Instead of | Write |
|---|---|
| "Error 500" | "We could not load your orders. Try again in a moment." |
| "Invalid input" | "Enter a 5-digit ZIP code." |
| "Something went wrong" (alone) | "We could not save your changes. Your text is still here; try again." |
| "You entered a wrong date" | "The end date must be after the start date." |

## Success

- Confirm the result with what matters ("Order 1042 is placed. We sent the receipt to your email.") and the next step.
- A short confirmation for small actions (a toast or an inline check) that does not steal focus; a page or panel for big ones (a purchase).
- Toasts disappear on their own only when the message is not essential, and never in less than about five seconds.

## Partial

- Show what loaded and mark what did not, in place: "Recommendations are unavailable right now."
- One failing widget never blanks the page.

## Disabled and unavailable

- A disabled control says why nearby, or in its label ("Sold out"), or it is hidden when it never applies to this person.
- Do not disable a submit button just because the form is invalid: let the person submit and show the errors.

## Long and unusual content

- Long names wrap, or truncate with the full text available (a tooltip is not enough on touch screens: show it on the detail view).
- Big numbers and currencies keep their alignment (tabular figures in tables).
- Many items paginate, load more or virtualize; zero, one and many look right.
- Translated text can be 30% longer: leave room.

## Copy rules

- **Buttons:** a verb and its object: "Add to cart", "Save changes", "Delete project". The destructive one says what it destroys.
- **Labels:** short nouns; the hint goes in help text, not the placeholder.
- **Sentence case** everywhere; no ALL CAPS sentences; no exclamation marks in errors.
- **Same word, same thing:** "cart" everywhere, not "cart", "bag" and "basket".
- **Numbers, money and dates** through the project's formatting helpers and locale.
- **Tone:** the brand's when `.exo/brand.json` defines one; otherwise plain, direct and friendly, without jokes in errors.
