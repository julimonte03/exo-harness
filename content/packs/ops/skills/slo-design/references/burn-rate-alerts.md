# Burn-rate alerts

## The math

- **Error budget:** `1 - target`. For 99.9%, the budget is 0.1% of valid events.
- **Error ratio:** bad events / valid events over a window, the complement of the SLI.
- **Burn rate:** `error ratio / (1 - target)`. A burn rate of 1 spends the budget exactly over the SLO window; 2 spends it in half the window.
- **Budget spent in a window:** `burn rate × window / SLO window`. Burn rate 14.4 over 1 hour, with a 30-day (720-hour) SLO window: `14.4 × 1 / 720 = 2%`.
- **Time to exhaustion** at a constant burn rate: `SLO window / burn rate`. At 14.4, a 30-day budget lasts about 50 hours; at 6, 5 days.

The alert threshold on the error ratio is `burn rate × (1 - target)`. For 99.9% and burn rate 14.4: an error ratio above 1.44%.

## The standard set

| Severity | Burn rate | Long window | Short window | Budget spent when it fires | Error ratio threshold at 99.9% |
|---|---|---|---|---|---|
| Page | 14.4 | 1 h | 5 min | 2% | 1.44% |
| Page | 6 | 6 h | 30 min | 5% | 0.6% |
| Ticket | 1 | 3 days | 6 h | 10% | 0.1% |

- **Why two windows per alert:** the long window makes the alert significant (a one-minute blip does not page); the short window, about one twelfth of the long one, makes it clear quickly once the problem is fixed, instead of paging for an hour after recovery.
- **Why several alerts:** the fast one catches outages within minutes; the slow ones catch a steady leak that would spend the budget in days without ever looking dramatic.
- With a 28-day window instead of 30, the budget shares change slightly; keep the burn rates and recompute the shares if the policy depends on them.

## Prometheus example

Recording rules for the error ratio over each window, then the alerts. Adapt metric names, labels and the target.

```yaml
groups:
  - name: checkout-slo
    rules:
      - record: slo:checkout_confirm_errors:ratio_rate5m
        expr: |
          sum(rate(http_requests_total{service="checkout", route="/confirm", code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="checkout", route="/confirm"}[5m]))
      # repeat the rule for the windows 30m, 1h, 6h and 3d (ratio_rate30m, ratio_rate1h, ratio_rate6h, ratio_rate3d)

      - alert: CheckoutConfirmBudgetBurnFast
        expr: |
          slo:checkout_confirm_errors:ratio_rate1h > (14.4 * 0.001)
          and
          slo:checkout_confirm_errors:ratio_rate5m > (14.4 * 0.001)
        labels:
          severity: page
        annotations:
          summary: "Checkout confirm is spending its 30-day error budget 14.4 times too fast"
          runbook_url: "<link to the runbook in the repository or wiki>"

      - alert: CheckoutConfirmBudgetBurnMedium
        expr: |
          slo:checkout_confirm_errors:ratio_rate6h > (6 * 0.001)
          and
          slo:checkout_confirm_errors:ratio_rate30m > (6 * 0.001)
        labels:
          severity: page

      - alert: CheckoutConfirmBudgetBurnSlow
        expr: |
          slo:checkout_confirm_errors:ratio_rate3d > (1 * 0.001)
          and
          slo:checkout_confirm_errors:ratio_rate6h > (1 * 0.001)
        labels:
          severity: ticket
```

Other platforms (cloud monitoring services, vendor tools) have their own SLO and burn-rate features: use them with the same burn rates and windows when the project already does, instead of hand-written rules.

## Low traffic

With few requests, one failure can be a large share of a window and page at night for nothing.

- **Minimum events:** add a condition that the long window has at least N valid events (for example 100) before the alert can fire.
- **Longer windows** for the fast alert, accepting slower detection.
- **Synthetic probes** that generate a steady number of requests, so the ratio means something.
- **Group** several small endpoints of the same journey into one SLI.
- **A ticket instead of a page** when the service is not critical out of hours, written in the policy.

## Latency SLOs

The same alerts work for latency: the error ratio is "requests slower than the threshold / valid requests". The threshold must be a histogram bucket boundary (or the platform's equivalent) so the ratio can be computed exactly.

## Common mistakes

- Paging on the raw error rate (`> 1%` for 5 minutes): noisy at night with low traffic, and blind to a slow leak.
- A burn-rate alert without a runbook link.
- Alerts on causes (CPU, memory) as pages: keep them as dashboards or tickets, and page on the SLO.
- Changing the target without recomputing the thresholds.
