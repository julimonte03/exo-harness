# Performance and client-side security

Checklists behind section 3 of the skill. Apply what fits the task; a small change does not need a performance audit.

## Core Web Vitals

Measured on real visits, at the 75th percentile, per page type.

| Metric | Good | What it measures |
|---|---|---|
| LCP, Largest Contentful Paint | at most 2.5 s | When the main content (the hero image, the first heading block, the main list) is painted |
| INP, Interaction to Next Paint | at most 200 ms | How long the page takes to respond visibly to clicks, taps and keys, across the visit |
| CLS, Cumulative Layout Shift | at most 0.1 | How much visible content jumps without the person causing it |

### Usual causes and fixes

| Symptom | Usual cause | Fix |
|---|---|---|
| Slow LCP | The main image is lazy-loaded, has no priority, or is huge | Load the LCP image eagerly with high fetch priority, in a modern format, sized for the viewport |
| Slow LCP | The content waits for a large JavaScript bundle and then a request chain | Split the bundle by route, start the data request early (in the route or loader), render on the server when the framework supports it |
| Slow LCP | Render-blocking fonts or styles | Preload the critical font, `font-display: swap`, only the weights in use |
| Slow INP | A long task on each keystroke or click (filtering a big list, heavy re-renders) | Defer the expensive part (`useDeferredValue` or a transition), memoize measured hot spots, virtualize long lists |
| Slow INP | Third-party scripts on the main thread | Load them after the page is interactive, or drop them |
| High CLS | Images, ads or embeds without dimensions | Set `width` and `height`, or `aspect-ratio` |
| High CLS | Content inserted above what the person is reading (banners, late data) | Reserve the space, or insert below; skeletons the size of the content |
| High CLS | Web fonts swapping with different metrics | A fallback font with adjusted metrics, or `size-adjust` |

### Measuring

- **In the field:** the project's real-user monitoring, or the `web-vitals` library reporting to the project's own analytics, when it has them.
- **In the lab:** the browser's performance panel and Lighthouse, on a throttled profile. A lab score is a hint, not the metric.
- **Bundle:** the build's own report or a bundle analyzer the project has. Compare before and after a new dependency.

### Budgets

When the project has none, propose one in design rather than inventing it in apply: for example, the JavaScript of the first route under a target size compressed, and no new dependency over a size threshold without a reason in the design.

## Client-side security

Everything that runs in the browser can be read and changed by the person using it. The server enforces every rule that matters; the client only makes the right path easy.

### Rendering untrusted data

- React escapes text in JSX. The holes are `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, and `eval`-like calls (`new Function`, string arguments to `setTimeout`).
- HTML that must be rendered (rich text from a CMS, user content) goes through a sanitizer the project already uses, with an allow-list, every time it is rendered.
- URLs from data or users are checked before they reach `href`, `src`, `action` or `window.location`: allow `https:` (and `mailto:` or relative paths when needed), reject `javascript:` and `data:` for links.
- Values interpolated into styles or CSS-in-JS from user input are restricted to known options.

### Secrets and configuration

- Anything bundled is public, including build-time variables exposed to the client (`VITE_*`, `NEXT_PUBLIC_*`, `REACT_APP_*`). They hold only public configuration: API base URLs, public keys meant for browsers.
- Privileged keys and admin tokens live on the server. A screen that needs one in the client means the server is missing an endpoint.
- Source maps in production expose the source; publish them only to the error-reporting service, if the team wants that.

### Sessions and storage

- Prefer sessions in cookies set by the server with `HttpOnly`, `Secure` and `SameSite`. Tokens in `localStorage` are readable by any script on the page.
- A token or secret typed by a person for one action (an admin form) stays in component state for that action only: never in storage, the URL, logs or analytics.
- Browser storage holds what can be lost or read without harm: preferences, a guest cart. Validate it when reading: a person can edit it.
- No personal data or tokens in URLs (they end up in logs, history and referrers), client logs, error reports or analytics events (`.exo/shared/data-protection.md`).

### Requests and other windows

- Same-origin requests by default; credentials sent only to the project's own API.
- Links that open a new tab: `rel="noopener noreferrer"` (modern browsers imply `noopener`, but keep it explicit for third-party pages).
- `postMessage`: send with an explicit target origin; when receiving, check `event.origin` before using `event.data`.
- Embedding third-party pages: `iframe` with `sandbox` and only the permissions it needs.

### Headers and third parties

- A Content Security Policy is the strongest defense against injected scripts; when the project has one, new code must not need `unsafe-inline` or `unsafe-eval`.
- Each third-party script runs with the page's full power: add one only with the person's approval, prefer self-hosted or subresource integrity, and load it late.
- New npm dependencies are attack surface too: the stack's dependency scan in verify covers them (skill:security-scan-node).

### Access control

- Hiding a button, a route or a menu item is a convenience, not a control. Every action and every piece of data is authorized by the server; when you see a client-only check, point at the server gap.
