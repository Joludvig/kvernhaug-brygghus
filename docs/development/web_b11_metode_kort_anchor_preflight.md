# WEB PREP — `.hjelp-metode-kort` anchor scroll-margin: implementation preflight

*Written for issue #188 (OVERNIGHT PREP LANE comment, 2026-09-11).
Extends the B11 anchor-offset fix
([web_b11_anchor_offset_preflight.md](web_b11_anchor_offset_preflight.md),
landed in `dc396ed` "WEB FIX: B11 add JS-assisted hash correction + cover
`.hjelp-seksjon`") to the one selector B11 did not cover. That document's
`.hjelp-seksjon`/`.hjelp-artikkel`/`.hjelp-steg` analysis and the
JS-assisted hash correction it shipped are unaffected and out of scope
here.*

**Status: analysis/browser-evidence only. No `web/**` file is changed by
this document**, per the issue's explicit "Do NOT change product code in
this lane. Stop at review." instruction. Every claim below was
re-confirmed directly against current `master` at commit
`a77bbd54e871dcff655fb27a5de50508a51fe059`, and the recommended fix was
**built and measured in a real browser** on a disposable local branch,
then reverted before this document was written — see §3.

---

## 0. Executive summary

The original triage (issue #188 body) is confirmed still accurate on
current `master`: B11's scroll-margin fix
(`scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)`) was applied
to `.hjelp-seksjon`, `.hjelp-artikkel`, and `.hjelp-steg`
(`web/css/style.css:2352-2402`), but **not** to `.hjelp-metode-kort`
(`web/css/style.css:2452-2458`), which still carries no `scroll-margin-top`
at all. This is a straight omission, not a design decision — every other
help-page anchor container already uses the identical pattern.

Real-browser measurement (Chromium + Firefox, desktop 1280×900 + mobile
390×844, NO + EN, §2) confirms the practical effect: loading
`hjelp/humle.html#dry-hop` lands the card's `<h3>` **33–49px underneath**
the fixed compact nav (`.kompaktnav`), depending on viewport — consistent
across both engines and both locales, i.e. not a Chromium-only or
NO-only artifact.

**Recommended fix (§4), already measured as effective (§5):** add the
exact same one-line `scroll-margin-top` rule already used by the other
three selectors to `.hjelp-metode-kort`. This flips the measured overlap
from +41–49px (heading hidden under nav) to **−33px** (heading sits
~33px clear below the nav) in every one of the 8 browser/viewport/locale
combinations tested — the same fix, applied to the one selector it was
never extended to.

---

## 1. Current source truth (confirmed against current `master`)

### 1.1 Existing B11 coverage

`web/css/style.css:2352-2402`:

```css
.hjelp-seksjon {
  margin-top: 2.4rem;
  scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem);
}
...
.hjelp-artikkel {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
  scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem);
}
...
.hjelp-steg {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 1rem;
  scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem);
}
```

### 1.2 The uncovered selector

`web/css/style.css:2452-2458`:

```css
.hjelp-metode-kort {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
}
```

No `scroll-margin-top` at all — computed value defaults to `0px`
(confirmed at runtime, §2).

### 1.3 Anchor inventory (re-measured, matches the issue's original count exactly)

130 `<div class="hjelp-metode-kort" id="...">` anchors across 10 of the
12 `web/hjelp/*.html` pages (`index.html` and `utstyr-brewzilla.html`
have none), unchanged from the issue's original measurement:

| File | Anchor count |
|---|---|
| `sensorikk.html` | 21 |
| `gjaerhosting.html` | 18 |
| `vannkjemi.html` | 17 |
| `gjaervalg.html` | 15 |
| `klaring.html` | 15 |
| `sterke-ol.html` | 15 |
| `humle.html` | 11 |
| `trykkgjaering.html` | 9 |
| `bryggemetoder.html` | 8 |
| `bryggedag.html` | 1 |
| **Total** | **130** |

Every instance is a flat sibling `<div class="hjelp-metode-kort" id="...">`
containing an `<h3>` and one or more `<p>` — no nesting inside another
scroll-margin-bearing container carries the id itself (e.g.
`web/hjelp/humle.html:160`, `id="dry-hop"`), confirmed by inspecting all
10 files' markup shape. Because a browser's fragment-scroll targets the
exact element bearing the `id`, a scroll-margin on some ancestor
(`.hjelp-seksjon`, if present) never compensates for the child's own
missing rule — this is not a case of partial/indirect coverage.

`#dry-hop` specifically (`web/hjelp/humle.html:160`, linked from the
in-page TOC at `web/hjelp/humle.html:116`) is confirmed still present
and still an uncovered `.hjelp-metode-kort` instance, matching the
issue's illustrative example.

### 1.4 The scroll-correction mechanism (confirmed selector-agnostic)

`web/js/chrome.js:86-108`, `korrigerAnkerScroll()` (the B11 JS-assisted
hash correction):

```js
function korrigerAnkerScroll() {
  var hash = location.hash;
  if (!hash || hash.length < 2) return;
  var mal;
  try {
    mal = document.getElementById(decodeURIComponent(hash.slice(1)));
  } catch (e) {
    mal = null;
  }
  if (!mal) return;
  oppdater();
  mal.scrollIntoView();
  window.requestAnimationFrame(function () {
    oppdater();
    mal.scrollIntoView();
  });
}
```

This looks the target up purely by `id` via `getElementById` and calls
the browser's native `scrollIntoView()`, which itself consults whatever
`scroll-margin-top` is computed for that exact element. **The JS
correction mechanism is not the gap** — it already runs unconditionally
for `#dry-hop` (or any other `.hjelp-metode-kort` id) exactly as it does
for `.hjelp-artikkel`/`.hjelp-steg`; it simply has nothing to compensate
with, because the CSS property it relies on was never set for this
selector. This rules out Option B (a JS-side fix) entirely — the gap is
purely the one missing CSS declaration.

---

## 2. Reproduction evidence (real browser, current `master`)

Run via this project's existing Playwright Critical Browser Gate
infrastructure (`playwright.config.js`, `tests/playwright/helpers.js`),
scoped to a disposable scratch spec (not committed — see §6) that
navigates directly to `hjelp/humle.html#dry-hop` (fresh `goto()` with a
pre-existing hash, the exact "initial load with existing hash" scenario
B11's own preflight flagged as needing real-browser confirmation) and
measures `.kompaktnav`'s bounding box against `#dry-hop`'s `<h3>`
bounding box, plus the computed `scroll-margin-top` on `#dry-hop` itself.

**Matrix:** Chromium + Firefox × desktop (1280×900) + mobile (390×844) ×
NO + EN (`/hjelp/humle.html` vs `/en/hjelp/humle.html`) — 8 combinations,
all run against the local static server (`web/`, not production), per
this project's testing conventions.

| Engine | Viewport | Locale | `--kompaktnav-h` | Computed `scroll-margin-top` on `#dry-hop` | Nav bottom (px) | `<h3>` top (px) | Overlap (nav bottom − h3 top) |
|---|---|---|---|---|---|---|---|
| Chromium | 1280×900 | NO | 66px | `0px` | 65.98 | 17.05 | **+48.9px** |
| Chromium | 1280×900 | EN | 66px | `0px` | 65.98 | 16.83 | **+49.2px** |
| Chromium | 390×844 | NO | 58px | `0px` | 57.98 | 16.61 | **+41.4px** |
| Chromium | 390×844 | EN | 58px | `0px` | 57.98 | 17.22 | **+40.8px** |
| Firefox | 1280×900 | NO | 66px | `0px` | 66.00 | 17.17 | **+48.8px** |
| Firefox | 1280×900 | EN | 66px | `0px` | 66.00 | 16.97 | **+49.0px** |
| Firefox | 390×844 | NO | 58px | `0px` | 58.00 | 16.80 | **+41.2px** |
| Firefox | 390×844 | EN | 58px | `0px` | 58.00 | 17.40 | **+40.6px** |

A positive overlap means the heading top sits **above** the nav's bottom
edge — i.e. underneath the fixed nav, exactly the symptom the issue
reports. Confirmed identical in kind (not merely similar) across both
engines and both locales: the computed `scroll-margin-top` on `#dry-hop`
is literally `0px` in every case (the `var(--kompaktnav-h, 0px)` fallback
firing because no rule sets the property at all for this selector), so
the browser's native fragment-scroll places the card's own top edge at
`y≈0` regardless of the (correctly-populated) `--kompaktnav-h` value —
the nav simply has nothing to read.

---

## 3. Fix candidate — built and measured, then reverted

To avoid recommending an unverified fix, the candidate change (§4) was
applied on this run's disposable local branch, re-measured with the
identical scratch harness from §2, and then **reverted** (`git checkout
-- web/css/style.css`) before this document was written — consistent
with the issue's "No deploy or code change authorized" / "Do NOT change
product code in this lane" instruction. No commit contains the CSS
change; it exists only as measured evidence below.

---

## 4. Recommended fix

One-line CSS change, `web/css/style.css:2452-2458`, exactly mirroring
the pattern already used by `.hjelp-seksjon`/`.hjelp-artikkel`/
`.hjelp-steg`:

```css
.hjelp-metode-kort {
  background: var(--bg-sect);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1rem;
  scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem);
}
```

No other file needs to change:
- No `web/hjelp/*.html`/`web/en/hjelp/*.html` markup change — the fix is
  entirely in the shared stylesheet every help page already includes.
- No `web/js/chrome.js` change — §1.4 already establishes the JS
  correction mechanism is selector-agnostic and needs nothing added.
- No i18n/`scripts/generate_web_i18n_pages.py` involvement — this is a
  pure CSS/geometry fix with no translatable string, so
  `tests/test_generate_web_i18n_pages.py`'s NO/EN byte-match requirement
  is unaffected.

---

## 5. Verification evidence for the fix

Same 8-combination matrix as §2, re-run with the §4 change applied
locally:

| Engine | Viewport | Locale | Computed `scroll-margin-top` on `#dry-hop` | Nav bottom (px) | `<h3>` top (px) | Overlap (nav bottom − h3 top) |
|---|---|---|---|---|---|---|
| Chromium | 1280×900 | NO | 82px | 65.98 | 99.05 | **−33.06px** |
| Chromium | 1280×900 | EN | 82px | 65.98 | 98.83 | **−32.84px** |
| Chromium | 390×844 | NO | 74px | 57.98 | 90.61 | **−32.63px** |
| Chromium | 390×844 | EN | 74px | 57.98 | 91.22 | **−33.23px** |
| Firefox | 1280×900 | NO | 82px | 66.00 | 99.17 | **−33.17px** |
| Firefox | 1280×900 | EN | 82px | 66.00 | 98.97 | **−32.97px** |
| Firefox | 390×844 | NO | 74px | 58.00 | 90.80 | **−32.80px** |
| Firefox | 390×844 | EN | 74px | 58.00 | 91.40 | **−33.40px** |

Every combination flips from a positive overlap (heading under the nav)
to a negative offset of ~33px (heading clear of the nav, with headroom
close to the intended `1rem` (16px) margin plus the nav's own height) —
consistent across both engines, both viewports, and both locales. This
is the same real-browser confirmation method the original B11 preflight
could not obtain from source alone (its own §2/§9 flagged the
initial-load-with-hash timing question as unprovable without a browser
trace); here it is directly measured and positive.

---

## 6. Regression risks

- **Scope is provably limited to `.hjelp-metode-kort` instances.** The
  changed rule only adds a `scroll-margin-top` declaration — it does not
  touch `background`/`border`/`padding`/`margin-bottom`, so no visual
  layout change is expected outside of fragment-scroll landing position.
- **`.hjelp-seksjon`/`.hjelp-artikkel`/`.hjelp-steg` are untouched** —
  separate selectors, separate rule blocks; nothing about extending
  `--kompaktnav-h`'s consumers changes how `chrome.js` *produces* the
  value (unchanged from the same argument in the original B11 preflight,
  §7).
- **`.bygger-hoyre`'s sticky offset** (`web/css/style.css:2567`, the
  other existing `--kompaktnav-h` consumer) is a separate selector in a
  separate `@media (min-width: 1000px)` scope — unaffected.
- **Desktop before-scroll state is a no-op**, identical to the existing
  three selectors' behavior: `var(--kompaktnav-h, 0px)` falls back to
  `0px` whenever `.kompaktnav` is not `.synlig` (i.e. before the user has
  scrolled past the hero), so the rule degrades to exactly today's
  *absence* of a scroll-margin in that state — it cannot make any
  currently-working case worse.
- **No known nesting conflict**: §1.3 confirms every `.hjelp-metode-kort`
  anchor is a flat sibling `<div>`, not nested inside another
  scroll-margin-bearing element that could compound with this one — a
  browser only ever applies the scroll-margin of the exact element it
  scrolls to.
- **NO/EN parity**: §2/§5 both measured NO and EN pages directly (not
  inferred) — behavior is identical between locales in both the
  reproduction and the fix verification, as expected for a change that
  touches only the shared, locale-independent `web/css/style.css`.

---

## 7. Bounded acceptance tests

For a future implementation round that actually applies §4:

| # | Scenario | Viewport | Expected outcome |
|---|---|---|---|
| T1 | Load `hjelp/humle.html#dry-hop` directly (bookmark/shared-link simulation) | Mobile (390×844) | `#dry-hop`'s `<h3>` fully visible below `.kompaktnav`, not overlapped |
| T2 | Same as T1 | Desktop (1280×900) | Same as T1 |
| T3 | Same as T1/T2 on `web/en/hjelp/humle.html#dry-hop` | Both | Identical positioning to NO (locale parity) |
| T4 | Click an in-page TOC link to a `.hjelp-metode-kort` anchor on an already-loaded help page | Both | Target heading lands clear of `.kompaktnav`, consistent with T1-T3 |
| T5 | Spot-check at least one more `.hjelp-metode-kort` anchor on a second file (e.g. `vannkjemi.html#alkalitet`, `sensorikk.html#diacetyl`) | Both | Same outcome as T1 — confirms the fix is a shared-stylesheet effect, not `humle.html`-specific |
| T6 | `.hjelp-seksjon`/`.hjelp-artikkel`/`.hjelp-steg` anchors (regression check) | Both | Unchanged from current behavior |
| T7 | `.bygger-hoyre` sticky offset on `index.html`'s builder tab (regression check) | Desktop, scrolled past hero | Unchanged from current behavior |
| T8 | 0 console/page errors across T1-T7, Chromium and Firefox | Both | Baseline per `web-full-regression` skill |

**Source/unit-testable:**
- Confirm the single `scroll-margin-top` line lands at
  `web/css/style.css:2452-2458` and nowhere else (`git diff` review — no
  existing unit test targets `web/css/style.css` content directly).
- `python3 -m unittest tests.test_generate_web_i18n_pages -b` — not
  expected to be affected (no i18n/`web/en/**` change per §4), but this
  project's testing policy requires at least this focused run on any
  `web/**`-touching round.
- Full suite (`python3 -m unittest discover -s tests -b`) at the final
  checkpoint of the future implementation round.

**Already covered by real-browser evidence in this document (§2/§5):**
the Chromium+Firefox, desktop+mobile, NO+EN reproduction/fix-effectiveness
matrix for the primary `#dry-hop` case. T5 (a second anchor, second file)
was not independently re-measured in this preflight and is left for the
implementation round's own acceptance pass.

---

## 8. Non-goals

- No `web/**` product file is changed by this document — analysis only,
  per the issue's own hard guard.
- B09/B10/B11's already-landed `.hjelp-seksjon`/`.hjelp-artikkel`/
  `.hjelp-steg` coverage and JS-assisted hash correction are unaffected
  and out of scope here.
- No App/Core/Bryggeskole change.
- No deploy/FTP action.
- No change to `#98`/`#100` or owner-PC state/claims.
- Astra Audit #2 (referenced by the original issue #188 body) is a
  separate, independent measurement this document does not attempt to
  substitute for or pre-empt — it corroborates the same finding from a
  different angle (direct Playwright measurement vs. the audit's own
  method), which is offered as additional evidence, not as a replacement
  for that audit.
- This document does not itself commit §4 — it hands a future
  implementation round (a fresh `status:ready` on a new or reopened
  issue) an already-measured, ready-to-apply one-line change plus the
  acceptance matrix in §7.
