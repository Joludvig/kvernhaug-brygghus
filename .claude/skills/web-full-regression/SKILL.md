---
name: web-full-regression
description: Run the full Kvernhaug Brygghus web/ validation sweep (Playwright, Chromium+Firefox, multiple viewports) before reporting a web/ round done. Use when a web/ change is ready for checkpoint/commit and needs functional + responsive + console-error verification, not for a tiny single-line CSS/copy tweak.
---

# Web full regression

Repeatable procedure for validating a `web/**` change. Encodes patterns that
have caused rework in past rounds — follow them to avoid re-deriving them.

## 1. Start a scratch server — never touch port 8000

Port 8000 is the user's persistent manual-review server. Start a temporary
server on a different port for automated checks:

```bash
py -3 -m http.server 8210   # any free port, not 8000
```

Kill it when done. Confirm port 8000 is still serving `index.html` (200)
before finishing.

## 2. Functional checks (Playwright, Python, sync API)

Write a throwaway script in the scratchpad directory. Known gotchas:

- The first-run modus dialog (`#modus-forstegang`) blocks clicks until
  dismissed — check `page.is_visible("#modus-forstegang")` and click a
  `.modus-knapp` first on every fresh page load.
- The mode/nav buttons live inside `.sidemeny` (off-screen drawer) —
  `.meny-knapp` toggles it open/closed; click `.sidemeny-lukk` to close it
  before a later action that could otherwise be intercepted by the still-open
  drawer.
- `window.confirm()`/`alert()` dialogs: register `page.once("dialog", ...)`
  right before the triggering action, never a persistent `page.on("dialog", ...)`
  for the whole script — a leftover persistent handler races with later
  `once()` handlers and raises "Dialog already handled" errors.
- `localStorage.clear()` via `context.add_init_script` re-runs on every
  `page.reload()` and wipes state before the reload's own `init()` reads it —
  use a one-time `page.evaluate("localStorage.clear()")` before the first
  `goto()` instead.
- Data objects like `maltData`/`humleData`/`gjaerData` are plain objects
  keyed by id (not arrays) — use `Object.keys(maltData)[0]`, not `maltData[0]`.

## 3. Responsive + cross-browser sweep

Chromium + Firefox × viewports `[1920, 1280, 768, 375]` (768/375 with
`has_touch=True`). For each combination, check:

- 0 console errors, 0 page errors
- `document.documentElement.scrollWidth <= clientWidth + 1` (no horizontal
  overflow)
- The specific interaction under test actually completes correctly

## 4. Report compactly

Summarize as counts ("N/N checks OK") with full detail only for failures —
don't echo every passing assertion. See testing policy:
[`.claude/rules/testing.md`](../../rules/testing.md).

## 5. Clean up

Kill the scratch-port server. Verify port 8000 still responds 200. Do not
commit/push unless explicitly asked — see the always-loaded rules in
[`CLAUDE.md`](../../../CLAUDE.md).
