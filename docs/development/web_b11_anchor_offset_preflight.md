# WEB PREP — B11 mobile help anchor offset: implementation preflight

*Part of #101 Phase 1 Web Stabilization, day queue #153 Q7. Written for
issue #166. Supersedes/expands only the B11 portion of
[web_b09_b11_triage.md](web_b09_b11_triage.md) into an
implementation-ready contract — that document's B09/B10 findings are
untouched and out of scope here.*

**Status: docs-only preflight. No `web/**` file is changed by this
document.** Every claim below was re-read directly from repo source at
commit `05fd70753f4653f8c726af9fafa166410af08083` (current `master` at
the time this issue was created) — the triage document's B11 citations
were revalidated line-by-line against that commit and are confirmed
unchanged (see §1).

---

## 0. Executive summary

B11 is a **CSS constant mismatch**, not a missing mechanism: the fixed
mobile nav bar (`.kompaktnav`, ~54px tall on mobile) already exposes its
own live height as a CSS custom property (`--kompaktnav-h`, maintained
by `web/js/chrome.js`), and that exact property is already used
elsewhere in the codebase to solve this identical class of problem
(`.bygger-hoyre`'s sticky offset). The help-page anchor targets
(`.hjelp-artikkel`, `.hjelp-steg`) simply never consume it — they use a
flat, unconditional `scroll-margin-top: 1rem` (16px) at every viewport
size instead, so a mobile deep link can land a heading directly under
the fixed nav.

The recommended fix (§5) is **CSS-only**: replace the flat
`scroll-margin-top: 1rem` on both selectors with
`scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)`, exactly
mirroring `.bygger-hoyre`'s existing pattern. Source alone cannot prove
this is *sufficient* for the initial-load, pre-existing-`#hash` case
(§2) — that is the one part of this preflight that requires real-browser
verification before a future round can call B11 done, and this document
recommends that verification happen **before** committing to the
JS-assisted fallback in §4, not preemptively alongside it.

---

## 1. Current source truth (revalidated against current master)

All of the following were re-confirmed against `05fd70753f4653f8c726af9fafa166410af08083` — no drift from the
`web_b09_b11_triage.md` citations was found.

### 1.1 The fixed nav

`web/css/style.css:216-229`:

```css
.kompaktnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 40;
  background: var(--warm-bg);
  border-bottom: 2px solid var(--gold);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
  padding: 0.6rem 1.5rem;
  transform: translateY(-100%);
  opacity: 0;
  transition: transform 0.2s ease, opacity 0.2s ease;
  pointer-events: none;
}
```

Mobile override, `@media (max-width: 640px)` (`web/css/style.css:270-309`):

```css
.kompaktnav {
  padding: 0.55rem 1rem;
}
/* ... */
.kompaktnav-logo {
  width: 34px;
  height: 34px;
}
```

Rendered mobile height ≈ 34px logo + (0.55rem × 2 ≈ 17.6px padding) +
2px bottom border ≈ **~54px**. This is an arithmetic bound from the CSS
values, not a measured pixel value — see §6 for why an exact figure
needs a real device/browser.

### 1.2 The one existing height-aware compensation mechanism

`web/js/chrome.js:5-29`, `initHero()`:

```js
function oppdater() {
  var terskel = hero.offsetHeight - kompaktnav.offsetHeight;
  var synlig = window.scrollY > terskel;
  kompaktnav.classList.toggle("synlig", synlig);
  document.documentElement.style.setProperty(
    "--kompaktnav-h",
    (synlig ? kompaktnav.offsetHeight : 0) + "px"
  );
}

window.addEventListener("scroll", oppdater, { passive: true });
window.addEventListener("resize", oppdater);
oppdater(); // runs once immediately, in addition to the listeners above
```

`--kompaktnav-h` is set to `.kompaktnav`'s *actual measured*
`offsetHeight` when visible (`.synlig`), or `0px` when not — i.e. it is
a live, JS-computed value, not a CSS constant guess.

Its **only current consumer**, `web/css/style.css:2524-2542` block
containing `.bygger-hoyre` (2557-2564), scoped to
`@media (min-width: 1000px)`:

```css
.bygger-hoyre {
  position: sticky;
  /* --kompaktnav-h settes av web/js/chrome.js til .kompaktnav sin høyde
     NÅR den er synlig, ellers 0px -- .hero selv er ikke sticky, så det
     er kun når den faste kompaktnav-bjelken faktisk vises (etter at
     hero-banneret er scrollet forbi) at høyrekortet trenger en offset
     for å ikke havne under den. */
  top: calc(var(--kompaktnav-h, 0px) + 1rem);
  z-index: 1;
}
```

This is a **desktop-only** consumer (`min-width: 1000px`) of a property
that is computed identically on every viewport — nothing about
`--kompaktnav-h` itself is desktop-specific.

### 1.3 The anchor targets and their current, flat compensation

`web/css/style.css:2358-2365`:

```css
.hjelp-artikkel {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
  scroll-margin-top: 1rem;
}
```

`web/css/style.css:2390-2397`:

```css
.hjelp-steg {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 1rem;
  scroll-margin-top: 1rem;
}
```

Neither rule sits inside a `@media` query — `scroll-margin-top: 1rem`
(16px) applies identically at every viewport width, versus a fixed nav
that is ~54px tall on mobile (§1.1) and a different, unmeasured height
on desktop (out of scope for B11 per the triage doc — no reported
desktop symptom).

Confirmed markup shapes, unchanged from the triage doc:
- `<article class="hjelp-artikkel" id="...">`, e.g.
  `web/hjelp/index.html:132` (`id="forste-oppskrift"`),
  `web/hjelp/index.html:194` (`id="og"`).
- `<div class="hjelp-steg" id="steg-N">`, e.g.
  `web/hjelp/bryggedag.html:153,167,181,195,209,223,237,251,265,279,293,307,321,335,349`
  (`id="steg-1"` … `id="steg-15"`, 15 confirmed instances, one more than
  the triage doc's illustrative `steg-1`…`steg-N` list).

### 1.4 Deep-link entry points

- In-page TOC links, `href="#<id>"`, within the same `web/hjelp/*.html`
  page.
- Help-tooltip popover "Les mer" links, `web/js/help.js:10,15,20,25,30,…`
  (confirmed 20 occurrences across the file), all of the shape
  `lesMer: "hjelp/index.html#og"` — a **cross-page** navigation that
  lands directly on a `#hash` URL, i.e. always an "initial load with an
  existing hash" case (§2), never an in-page click on an already-loaded
  document.

### 1.5 Script load order (confirmed identical across every `web/hjelp/*.html` page)

All six help pages
(`index.html`, `bryggedag.html`, `klaring.html`, `bryggemetoder.html`,
`humle.html`, `trykkgjaering.html`) load, at the very end of `<body>`,
in this exact order, with **no `defer`/`async` attribute**:

```html
<script src="../js/i18n.js"></script>
<script src="../js/preferences.js"></script>
<script src="../js/chrome.js"></script>
```

`chrome.js`'s `initHero()`/`oppdater()` (§1.2) therefore only runs once
the parser reaches this point near the end of the document — i.e. after
essentially all of the page's HTML has already been parsed, but its
exact ordering relative to the browser's own native fragment-scroll is
the open question in §2.

### 1.6 No existing JS anchor-offset handling

Confirmed (unchanged from the triage doc): the only `scrollIntoView`/
hash-adjacent JS in `web/js/*.js` is unrelated to help anchors —
`pantry_page.js:506` and `combobox.js:118` handle form/dropdown
scrolling; `i18n.js`'s hash handling (`web/js/i18n.js:182-191`) only
rewrites the language-switch link's `href` hash, it does not scroll.
Help anchors rely entirely on the browser's native fragment navigation,
which respects `scroll-margin-top`.

---

## 2. Timing/geometry analysis

### Q1 — Is `scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)` sufficient for in-page clicks after JS has initialized?

**Yes, with high confidence from source alone.** Once
`chrome.js:oppdater()` has run at least once (which happens
synchronously at script-load time, §1.5, and again on every `scroll`
event), `--kompaktnav-h` correctly reflects `.kompaktnav`'s live
`offsetHeight` whenever it is `.synlig`. An in-page TOC click on an
already-loaded, already-scrolled help page happens strictly *after*
`oppdater()` has already run at least once and typically after several
`scroll`-triggered re-runs, so `--kompaktnav-h` is guaranteed live and
correct at click time. This case needs no browser trace to be confident
about — it is the same mechanism `.bygger-hoyre` already relies on
successfully at desktop widths (§1.2), just consumed at a different
viewport/selector pair.

### Q2 — On a fresh page load with an existing `#hash`, is `--kompaktnav-h` populated before the browser's effective final anchor position, or is a small JS post-init/hash correction required?

**This is the genuine open question — source alone cannot settle it,
and this preflight does not claim otherwise.** What source *does*
establish, precisely:

- The HTML Standard's "scroll to the fragment" algorithm re-runs
  automatically during document load (triggered by layout/style changes)
  and is not a single one-shot event tied to a specific script's
  execution order — so there is no source-level guarantee that the
  browser's *last* fragment-scroll pass happens strictly before or
  strictly after `chrome.js` finishes executing at the end of `<body>`.
- What source *can* bound: `chrome.js` runs after `i18n.js` and
  `preferences.js`, with no `defer`/`async`, at the very end of the
  document (§1.5) — so it is not blocked behind any deferred/async
  script, and `oppdater()`'s first synchronous call happens essentially
  as soon as the browser has parsed that far. On a typical connection
  this is well before the "load" event and well before most browsers'
  *final* automatic re-scroll pass (browsers commonly re-attempt the
  fragment scroll after images/layout settle), which is favorable — but
  "typical" and "commonly" are not proofs, and mobile Safari in
  particular has historically had its own fragment-scroll timing quirks
  that only a real device/browser trace can confirm or refute.
- Because `scroll-margin-top` is a **passive, declarative** CSS property
  consulted by the browser's *own* native fragment-scroll algorithm
  (not something `chrome.js` applies imperatively), the moment that
  matters is not "when does `chrome.js` run" but "what is the *current
  computed value* of `--kompaktnav-h` at the exact instant the browser
  performs its (possibly repeated) native scroll-to-fragment pass." If
  the browser's relevant pass happens before `oppdater()`'s first call,
  `--kompaktnav-h` is still at its unset/inherited default (effectively
  `0px`, per the `var(--kompaktnav-h, 0px)` fallback), and the anchor
  lands using only the flat `1rem` fallback — not wrong, but not yet
  improved over today's behavior for that specific pass. If the browser
  re-runs the fragment-scroll pass again after `chrome.js` has set the
  property (the common case per the HTML Standard's repeated-attempt
  behavior noted above), the corrected offset applies on that later
  pass.

**Conclusion:** the CSS-only fix is likely to work correctly on the
common case (a later native re-scroll pass picks up the corrected
`--kompaktnav-h`), and even in the worst case degrades no worse than
*today's* behavior (the same flat `1rem` fallback) rather than
introducing a new regression — but "likely" is exactly why this needs
the real Chromium+Firefox mobile-viewport confirmation in §6 before a
future round can close B11 on the strength of the CSS change alone.

### Q3 — Can the fix stay CSS-only? If not, prove why `chrome.js` must participate.

See §4/§5: **recommended as CSS-only**, justified by the degrade-no-worse-than-today argument above. `chrome.js` is not proven to
*need* new code — it already produces the exact value the fix consumes
(§1.2) — but whether the CSS-only fix is *sufficient in practice* for
every browser's fragment-scroll timing is the one claim this document
cannot make without the browser evidence in §6. §4 documents the
JS-assisted fallback and the specific, falsifiable observation that
would justify it, so a future round is not left guessing what "if not"
would even mean.

---

## 3. Option A — CSS-only fix (recommended, see §5)

Replace the flat `scroll-margin-top: 1rem` on both `.hjelp-artikkel`
(`web/css/style.css:2364`) and `.hjelp-steg`
(`web/css/style.css:2396`) with:

```css
scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem);
```

**No `@media` scoping needed for the property itself** — the `var(...,
0px)` fallback already makes it a no-op (identical to today's flat
`1rem`) whenever `--kompaktnav-h` is unset or `0px` (i.e. whenever
`.kompaktnav` is not `.synlig`, which per `chrome.js:oppdater()`'s
threshold logic (`terskel = hero.offsetHeight - kompaktnav.offsetHeight`)
is the normal case on desktop before scrolling past the hero, and on
any viewport before the user has scrolled far enough for the compact
nav to appear at all).

**Tradeoffs:**
- Pro: zero new JS, zero new event listeners, reuses a mechanism already
  proven correct for `.bygger-hoyre` (§1.2), smallest possible diff (2
  one-line CSS changes).
- Pro: degrades gracefully to *exactly* today's behavior whenever
  `--kompaktnav-h` is `0px` — cannot make any currently-working case
  worse.
- Con: entirely dependent on the browser's own native fragment-scroll
  timing relative to `chrome.js`'s execution (§2, Q2) for the
  initial-load-with-hash case — the one thing this document cannot
  prove from source, only bound.

## 4. Option B — JS-assisted fallback (only if §6 disproves Option A)

If the browser evidence in §6 shows the initial-load case is **not**
reliably corrected by Option A alone (i.e. the native fragment-scroll's
relevant pass consistently completes *before* `--kompaktnav-h` is set,
with no later re-scroll pass observed to correct it), the smallest
addition that keeps the fix CSS-first is a one-time, load-time
correction in `chrome.js`'s `initHero()`:

```js
// Illustrative only — not implemented by this document, and only to be
// added if §6's browser evidence proves Option A insufficient.
if (location.hash) {
  oppdater(); // ensure --kompaktnav-h is current before...
  var target = document.getElementById(location.hash.slice(1));
  if (target) target.scrollIntoView(); // ...re-triggering the scroll
}
```

**Tradeoffs:**
- Pro: removes all dependency on browser-specific native re-scroll
  timing — the correction is explicit and synchronous once
  `chrome.js` has run.
- Con: a second, JS-triggered scroll after the browser's own native
  jump is visually a "double scroll" if the native jump already landed
  close to correct — needs to be verified not to introduce a visible
  jump/flicker on the browsers where the native behavior was already
  adequate.
- Con: couples help-anchor correctness to `chrome.js`, which today has
  no help-page-specific knowledge at all (§1.6) — a larger, more
  invasive change than Option A, and per `.claude/rules/web.md`'s
  "static HTML/CSS/vanilla JS" resident rule, still stays within the
  existing no-build-step constraint but is a real behavior change to a
  shared, all-pages script, not a page-local one.
- Con: `location.hash` on cross-page "Les mer" navigations (§1.4) needs
  to be re-verified to still be populated at the same script-execution
  point once a JS correction is added — no reason from source to expect
  otherwise, but this is exactly the class of claim this document
  defers to the browser evidence in §6 rather than asserting from
  source alone.

This option is documented for completeness and to give a future round
an already-reasoned fallback — it is **not** a second thing to implement
alongside Option A "just in case." Implement Option A first, verify
against §6, and only reach for Option B if that verification actually
fails.

---

## 5. Recommended implementation boundary

**Implement Option A only, first.** Two one-line CSS changes:

- `web/css/style.css:2364` — `.hjelp-artikkel`'s `scroll-margin-top`.
- `web/css/style.css:2396` — `.hjelp-steg`'s `scroll-margin-top`.

Both changed from `1rem` to `calc(var(--kompaktnav-h, 0px) + 1rem)`, the
exact pattern already established at `web/css/style.css:2562`. No
`web/js/chrome.js` change in the first implementation pass. A future
round should only add Option B if the acceptance matrix in §8, run for
real per §6, shows the initial-load-with-hash case is not adequately
corrected by the CSS-only change.

---

## 6. Exact files/selectors/functions a future implementation round touches

| File | Selector/function | Change |
|---|---|---|
| `web/css/style.css:2358-2365` | `.hjelp-artikkel` | `scroll-margin-top: 1rem` → `scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)` |
| `web/css/style.css:2390-2397` | `.hjelp-steg` | Same change as above |
| `web/js/chrome.js:5-29` | `initHero()` / `oppdater()` | **Not touched** in the recommended first pass (§5) — only if Option B (§4) is later justified by browser evidence |

No `web/hjelp/*.html`/`web/en/hjelp/*.html` markup change is required —
the fix is entirely in the shared stylesheet, which every help page
already includes identically. No `web/js/i18n.js` or
`scripts/generate_web_i18n_pages.py` involvement — this is not an i18n
change, so `tests/test_generate_web_i18n_pages.py`'s NO/EN
byte-match requirement is unaffected (no `web/en/**` regeneration
needed for this fix specifically).

---

## 7. Preserving desktop and `.bygger-hoyre` behavior

- `.bygger-hoyre`'s own rule (`web/css/style.css:2557-2564`) is
  **untouched** by this fix — it is a separate selector, separate
  `@media (min-width: 1000px)` scope, reading the same
  `--kompaktnav-h` property but with its own `+ 1rem` offset and `top`
  property (not `scroll-margin-top`). Nothing about extending
  `--kompaktnav-h`'s *consumers* changes how `chrome.js` *produces* the
  value, so `.bygger-hoyre`'s behavior is provably unaffected by source
  alone (it does not depend on any other CSS rule's use of the same
  custom property).
- Desktop help-page anchor behavior: no reported symptom exists for
  desktop (per the triage doc), and the `calc(var(--kompaktnav-h,
  0px) + 1rem)` fallback degrades to exactly today's `1rem` whenever
  `--kompaktnav-h` is `0px` — which is the common desktop state before
  scrolling past the hero. Once a desktop user *has* scrolled past the
  hero and `.kompaktnav` is visible, the new rule would add whatever
  `.kompaktnav`'s actual desktop height is (unmeasured — no `@media
  (max-width: 640px)` override applies at desktop widths, so it reverts
  to the base `0.6rem 1.5rem` padding, §1.1) on top of the existing
  `1rem` — a **larger** offset than today's flat `1rem` for that
  specific desktop case. This is very likely the *correct* fix (desktop
  help anchors sitting under a visible, un-compensated-for fixed nav
  would be the same bug just at a different breakpoint) but was not the
  bug reported by B11 — the acceptance matrix (§8) includes an explicit
  desktop regression check for this specific behavior change rather
  than assuming it is risk-free.

---

## 8. Bounded acceptance matrix

| # | Scenario | Viewport | Expected outcome |
|---|---|---|---|
| M1 | Click an in-page TOC link (`href="#<id>"`) on an already-scrolled-past-hero help page | Mobile (≤640px) | Target `.hjelp-artikkel`/`.hjelp-steg` heading fully visible below `.kompaktnav`, not overlapped |
| M2 | Follow a help-tooltip "Les mer" link (cross-page, lands on `#hash` on initial load) | Mobile (≤640px) | Same as M1, on the very first paint after navigation — this is the case §2/Q2 flags as unproven from source alone |
| M3 | Load a raw `hjelp/*.html#<id>` URL directly (bookmark/shared-link simulation) | Mobile (≤640px) | Same as M2 |
| M4 | Same M1-M3 scenarios | Desktop (≥1000px, before scrolling past hero) | No visible change vs. today (fallback `1rem` still applies, `.kompaktnav` not yet `.synlig`) |
| M5 | Same M1-M3 scenarios, after scrolling far enough that `.kompaktnav` is `.synlig` | Desktop (≥1000px) | Anchor lands below the now-visible `.kompaktnav`, per §7's larger-offset analysis — confirm this reads as correct, not as an unwanted gap |
| M6 | `.bygger-hoyre` sticky offset on `index.html`'s builder tab | Desktop (≥1000px), scrolled past hero | Unchanged from current behavior (regression check, not a new behavior) |
| M7 | Resize from desktop to mobile width mid-session (responsive check) | Both | No console errors, no layout jump beyond the intended anchor-offset change itself |
| M8 | NO and EN parity for every scenario above | Both | Identical positioning behavior on `web/hjelp/**` and `web/en/hjelp/**` — this is a pure CSS/geometry fix with no i18n-string involvement, so no text difference is expected, only confirm no page-specific CSS override exists that would make EN behave differently (none is known to exist, but not independently re-verified across all 6×2 pages in this preflight) |
| M9 | 0 console/network errors across all scenarios above, Chromium and Firefox | Both | Baseline per `web-full-regression` skill |

## 9. Browser plan (Chromium + Firefox, mobile viewport)

Required, per this project's testing policy for anything needing
functional/visual browser verification (`.claude/rules/testing.md`)
and consistent with the triage doc's own "Browser requirement: Required"
call for B11:

1. Run scenarios M1-M3 and M9 in **Chromium**, mobile viewport (e.g.
   375×667 or the project's existing standard mobile viewport from the
   `web-full-regression` skill), on at least two help pages: one using
   `.hjelp-artikkel` (`index.html`) and one using `.hjelp-steg`
   (`bryggedag.html`).
2. Repeat step 1 in **Firefox** at the same viewport(s) — this is the
   step that actually answers §2/Q2, since fragment-scroll timing is
   engine-specific and cannot be inferred from one engine's behavior.
3. Run scenarios M4-M6 in both engines at a desktop viewport (≥1000px)
   as the regression check.
4. Run M7 (resize) and M8 (NO/EN parity spot-check) in at least one
   engine; a full 6-page × 2-language matrix is not required if M1-M6
   pass on the two representative pages in step 1 — flag this as a
   scope decision for whoever runs the future implementation round, not
   a hard requirement asserted here.

## 10. Focused test plan

**Source/unit-testable (can run without a browser):**
- Confirm the two exact `scroll-margin-top` line edits land at
  `web/css/style.css:2364`/`:2396` and nowhere else (a `git diff` review
  is sufficient — no existing unit test targets `web/css/style.css`
  content directly).
- `tests/test_generate_web_i18n_pages.py` — not expected to be affected
  (no `web/en/**`/i18n change per §6), but this project's testing policy
  requires at least this focused run on any `web/**`-touching round
  (`.claude/rules/testing.md`) to positively confirm that expectation
  rather than assume it: `python3 -m unittest
  tests.test_generate_web_i18n_pages -b`.
- Full suite (`python3 -m unittest discover -s tests -b`) at the final
  checkpoint of the future implementation round, per
  `.claude/rules/testing.md`.

**Requires real-browser/manual verification (cannot be source/unit
tested):**
- Everything in §8/§9 — geometry, fragment-scroll timing, and visual
  overlap are runtime browser behaviors with no unit-test surface in
  this repo (`tests/` has no browser/E2E coverage,
  `.claude/rules/testing.md`).

## 11. Non-goals

- No `web/**` product file is changed by this issue/document — it is
  analysis-only, per the issue's own hard guard.
- B09/B10 (from `web_b09_b11_triage.md`) are unaffected and out of
  scope here.
- No App/Core/Bryggeskole change.
- No deploy/FTP action.
- No change to `#98`/`#100` or owner data.
- Option B (§4) is documented, not implemented, and not recommended as
  a first pass — a future round should only build it if the browser
  evidence in §6/§9 actually requires it.
- This document does not itself run the Chromium/Firefox verification
  in §9 — it specifies the plan for a future implementation round to
  execute once B11 is actually being fixed, consistent with this
  issue's docs-only scope.
