# WEB PREP — B09–B11 triage (analysis only)

*Produced for issue #124, part of #101 Phase 1 NEXT preparation. Supersedes
the B09/B10/B11 portion of #120. Docs-only — no `web/**` behavior was
changed to produce this file; every claim below is either backed by an
exact file:line source citation or explicitly flagged as requiring browser
verification.*

## Priority summary

| ID | Symptom | Proof level | Suggested priority |
|---|---|---|---|
| B09 | English brew log shows Norwegian taste-category labels (e.g. `Maltfylde` instead of `Malt body`) | Fully source-proven | **High** — single-line fix, clear regression vs. the pattern already used correctly elsewhere in the same codebase |
| B10 | Literal `<strong>…</strong>` markers visible instead of bold text in ~16 help "why it matters" paragraphs (NO + EN, 32 file instances) | Fully source-proven | **High** — visibly broken help content on both languages, in both the pre-rendered EN static file and after JS runs |
| B11 | Mobile fixed nav can cover the top of a help section reached via a deep link/anchor | Fully source-proven as a geometry defect; exact pixel overlap not measured | **Medium** — a11y/readability annoyance, not a functional break; smallest fix is a CSS constant change |

None of B09/B10/B11 share a fix location with each other. B10 does share
its root mechanism (`applyI18n()` in `web/js/i18n.js`) with B09's `t()`
substitution, but the actual code path each bug lives in is otherwise
independent — see "Coupling / dependencies" per section below.

---

## B09 — English brew-log system taste labels can remain Norwegian

### Source evidence

- `web/js/flavor.js:5-9` — `SMAKS_KATEGORIER` is a hardcoded Norwegian
  string array (`"Maltfylde"`, `"Brød"`, `"Toast"`, `"Karamell"`,
  `"Honning"`, `"Nøtter"`, `"Sjokolade"`, `"Kaffe"`, `"Røyk"`,
  `"Bitterhet"`, `"Furunål"`, `"Jordlig"`, `"Krydder"`, `"Sitrus"`,
  `"Tropisk"`, `"Fruktighet"`, `"Steinfrukt"`, `"Vinøs"`).
  `beregnSmaksprofil()` (`flavor.js:14`) uses these strings as the *keys*
  of the returned flavor-profile object (`poeng`). This data is entirely
  **system-generated** from recipe/malt/hop/yeast inputs — never
  user-entered text.
- `web/js/i18n.js:3752-3776` — `SMAKS_KATEGORI_EN` is the EN translation
  table for those exact keys, and `smaksKategoriVisning(kat)` is the
  dedicated display helper:
  ```js
  function smaksKategoriVisning(kat) {
    if (gjeldendeSprak() === "en") return SMAKS_KATEGORI_EN[kat] || kat;
    ...
  }
  ```
  The comment immediately above (`i18n.js:3748-3751`) states explicitly
  that the dict *keys* must never be translated/changed — only the
  on-screen labels, via this helper.
- **Correct usage elsewhere (proves the mechanism works):**
  - `web/js/radar.js:92` — `text.textContent = smaksKategoriVisning(kat);`
    (flavor-wheel chart axis labels).
  - `web/js/style.js:223` — `smaksKategoriVisning(smaksNavn).toLowerCase()`
    (style-match "desired sensory character" text).
- **The bug:** `web/js/brygg_page.js:90-101`, function
  `_byggSmakSliders(container, brew)`:
  ```js
  for (const kategori of Object.keys(predikert)) {
    ...
    label.textContent = t("brygg.smakKategori", {
      kategori,
      forventet: (predikert[kategori] || 0).toFixed(1).replace(".", ","),
    });
  ```
  `kategori` is a raw object key of `predikert`
  (`brew.snapshot.predicted.flavorProfile`, built by
  `beregnSmaksprofil()`) — it is passed straight into the `{kategori}`
  placeholder. `smaksKategoriVisning()` is never called on it here, unlike
  at `radar.js:92` and `style.js:223`.
- The i18n *template* itself is correctly localized —
  `web/js/i18n.js:512` (NO): `"brygg.smakKategori": "{kategori} (forventet {forventet})"`;
  `web/js/i18n.js:2255` (EN): `"brygg.smakKategori": "{kategori} (expected {forventet})"`
  — but `t()`'s placeholder substitution (`i18n.js:86-96`,
  `tekst.replaceAll(`{${k}}`, v)`) inserts whatever literal string it is
  given, with no translation step of its own.

### Root cause

`_byggSmakSliders()` is the one call site of `SMAKS_KATEGORIER`-derived
keys that forgot the `smaksKategoriVisning()` translation step already
established as the pattern in `radar.js` and `style.js`. Net effect: on
`web/en/bryggelogg.html`, a taste-adjustment slider reads e.g.
`Maltfylde (expected 3.4)` instead of `Malt body (expected 3.4)`.

### System-owned vs. user-entered

Fully **system-owned**. The brew log's actual free-text fields
(`notater`, `learning.nextTime`, etc.) are deliberately passed through
unmodified regardless of language — see the analogous, intentional
"never translate user content" pattern at `web/js/i18n.js:98-107`
(`visningsnavn()`). B09 is not about that path; it is exclusively about
the system-generated flavor-category keys.

### Fix touchpoint

`web/js/brygg_page.js:98-101` — wrap `kategori` in
`smaksKategoriVisning(kategori)` before passing it to `t()`, matching
`radar.js:92`/`style.js:223`.

### Regression risks

- Existing stored brew snapshots (`brew.snapshot.predicted.flavorProfile`)
  use the Norwegian keys as their canonical, persisted key names — the
  fix must translate only at *display* time, never rewrite persisted
  data, or NO-locale historical brews would break.
- `SMAKS_KATEGORIER` order/spelling must stay byte-identical to
  `SMAKS_KATEGORI_EN`'s key set, or the fallback `|| kat` in
  `smaksKategoriVisning()` will silently leak a Norwegian key again for
  any category added to one table but not the other.

### Smallest acceptance criteria

- On `web/en/bryggelogg.html`, every taste-adjustment slider label reads
  an English category name (matching `SMAKS_KATEGORI_EN`'s values), never
  a `SMAKS_KATEGORIER` raw string.
- `web/bryggelogg.html` (NO) is visually unchanged.
- No change to how `flavorProfile` keys are computed, stored, or read
  elsewhere (`flavor.js`, `radar.js`, `style.js` untouched).

### Browser requirement

None — fully provable and fixable/verifiable from source
(`smaksKategoriVisning()`'s logic is a pure, deterministic lookup).
A visual smoke check of the EN brew log after the fix is good practice
but not required to *prove* the bug or its fix.

---

## B10 — raw HTML markers such as `<strong>` can appear visibly in help

### Architecture (by design, and correctly used in the majority of cases)

- `web/js/i18n.js:109-121`, `applyI18n()`:
  - `[data-i18n]` → `el.textContent = t(...)` (escapes markup — plain text
    only).
  - `[data-i18n-html]` → `el.innerHTML = t(...)` (renders markup). The
    comment at `i18n.js:114-118` states this dual-attribute contract
    exists specifically so hardcoded, author-controlled
    `<strong>`/`<em>`/`<a href="#anchor">` content renders correctly, and
    that it is safe only because these strings are static/self-authored,
    never user input.
  - `scripts/generate_web_i18n_pages.py:311-333` mirrors the same
    contract for the static EN page generator: `_sett_tekst()` (line
    311-313) writes a `NavigableString` (HTML-escaped text) for
    `[data-i18n]`; `_sett_innhold_html()` (line 316-324) parses and
    injects real DOM nodes for `[data-i18n-html]`.
- This convention is **manual and unenforced** — nothing lints or tests
  that a key containing markup is only ever bound via `data-i18n-html`.

### Confirmed, concrete instance (source-proven, both languages)

Cross-referencing every `web/js/i18n.js` key whose string value contains
`<strong>`/`<em>`/`<b>`/`<br`/`<a ` against every `data-i18n="<key>"`
(plain, textContent) binding in `web/hjelp/**` and `web/en/hjelp/**`
(the `data-i18n-html` bindings were excluded — those are all correctly
wired) surfaces **16 distinct i18n keys, 32 file instances**, that embed
a literal `<strong>…:</strong>` lead-in but are bound to a `<p>` via
plain `data-i18n`, not `data-i18n-html`:

| Key | Files (NO + EN) |
|---|---|
| `hjelp.klaring.hvaErKlart.hvorfor` | `web/hjelp/klaring.html:139`, `web/en/hjelp/klaring.html:138` |
| `hjelp.klaring.gelatin.hvorfor` | `web/hjelp/klaring.html:189`, `web/en/hjelp/klaring.html:180` |
| `hjelp.klaring.chillHaze.hvorfor` | `web/hjelp/klaring.html:202`, `web/en/hjelp/klaring.html:191` |
| `hjelp.metoder.batchSparge.hvorfor` | `web/hjelp/bryggemetoder.html:161`, `web/en/hjelp/bryggemetoder.html:143` |
| `hjelp.metoder.flySparge.hvorfor` | `web/hjelp/bryggemetoder.html:167`, `web/en/hjelp/bryggemetoder.html:148` |
| `hjelp.idx.vannPh.hvorfor` | `web/hjelp/index.html:542`, `web/en/hjelp/index.html:462` |
| `hjelp.idx.vannCa.hvorfor` | `web/hjelp/index.html:548`, `web/en/hjelp/index.html:467` |
| `hjelp.idx.vannMg.hvorfor` | `web/hjelp/index.html:554`, `web/en/hjelp/index.html:472` |
| `hjelp.idx.vannNa.hvorfor` | `web/hjelp/index.html:560`, `web/en/hjelp/index.html:477` |
| `hjelp.idx.vannCl.hvorfor` | `web/hjelp/index.html:566`, `web/en/hjelp/index.html:482` |
| `hjelp.idx.vannSo4.hvorfor` | `web/hjelp/index.html:572`, `web/en/hjelp/index.html:487` |
| `hjelp.humle.senKok.hvorfor` | `web/hjelp/humle.html:151`, `web/en/hjelp/humle.html:143` |
| `hjelp.humle.whirlpool.hvorfor` | `web/hjelp/humle.html:157`, `web/en/hjelp/humle.html:148` |
| `hjelp.humle.mengde.hvorfor` | `web/hjelp/humle.html:181`, `web/en/hjelp/humle.html:168` |
| `hjelp.trykk.narTrykketPafores.hvorfor` | `web/hjelp/trykkgjaering.html:151`, `web/en/hjelp/trykkgjaering.html:143` |
| `hjelp.trykk.trykkTemperatur.hvorfor` | `web/hjelp/trykkgjaering.html:170`, `web/en/hjelp/trykkgjaering.html:159` |

Example (`web/hjelp/klaring.html:139`):
```html
<p class="hjelp-hvorfor" data-i18n="hjelp.klaring.hvaErKlart.hvorfor"><strong>Klart er ikke automatisk bedre, og uklart er ikke automatisk feil.</strong> Et krystallklart øl kan være underkarbonert...</p>
```
i18n source (`web/js/i18n.js`, NO block): the value literally contains
`<strong>Klart er ikke automatisk bedre, og uklart er ikke automatisk
feil.</strong>` — a `<strong>`-wrapped lead-in sentence, identical shape
in every row of the table above.

### Two independent points in the render pipeline where this is visible

1. **Static EN file, before any JS runs at all.** The generator
   (`scripts/generate_web_i18n_pages.py:311-313`, `_sett_tekst`) already
   baked the EN string into `web/en/hjelp/*.html` as an HTML-escaped text
   node, e.g. `web/en/hjelp/bryggemetoder.html:143`:
   ```html
   <p class="hjelp-hvorfor" data-i18n="hjelp.metoder.batchSparge.hvorfor">&lt;strong&gt;Why you'd choose this:&lt;/strong&gt; Quick and forgiving to carry out...</p>
   ```
   `&lt;`/`&gt;` are standard HTML entities for `<`/`>`; a browser decodes
   them back to the literal characters `<`/`>` for on-screen text
   display (they are inside a text node, not inside a tag, so they are
   never re-interpreted as markup). The visible on-screen text is
   therefore literally `<strong>Why you'd choose this:</strong> Quick
   and forgiving...` even before JavaScript executes.
2. **After `applyI18n()` runs (both NO and EN).** For the NO page, the
   *raw static source* actually is a real `<strong>` element (correctly
   bold on first paint), because the NO `web/hjelp/*.html` files are
   hand-authored HTML, not generator output — but `web/js/i18n.js`'s
   `applyI18n()` runs on every page load (NO included) and overwrites
   that same element's `textContent` with the i18n-sourced string, which
   contains the literal characters `<`, `s`, `t`, `r`, `o`, `n`, `g`,
   `>`, etc. `Element.textContent = "..."` never parses HTML — the
   browser displays those characters verbatim. So even the
   correctly-authored NO page regresses to visible raw markup as soon as
   the page's own i18n script runs, which happens on every normal page
   load.

Net effect: both the EN static file (pre-JS) and the post-`applyI18n()`
DOM (NO and EN) show literal `<strong>…:</strong>` text instead of bold
text, in 16 "why it matters" paragraphs across 5 help pages.

### A related, distinct instance in Style Match (not `web/hjelp/**`, flagged for completeness)

`web/js/i18n.js:1694` (NO) / `:3437` (EN),
`"stilmatch.sensoriskOnsket"`, is the only `stilmatch.*` string using
markdown-style `*…*` emphasis: `"Ønsket sensorisk preg av *{smak}* (har
{reell}, stilen ber om {krav}+)"`. It reaches the DOM via
`web/js/style.js:223` → `web/js/app.js:1295`
(`` `<li class="onsket">💭 ${escHtml(o)}</li>` ``) → `innerHTML`.
`escHtml()` (`web/js/recipe_engine.js:13-17`) only escapes
HTML-significant characters; it does not interpret or strip `*…*`
markdown, so literal asterisks reach the screen (e.g. `Desired sensory
character of *citrus* (has 3.2, style calls for 4.0+)`). Same class of
defect (a literal emphasis marker surviving to visible text), different
mechanism (markdown asterisk vs. an HTML tag, and a different i18n
key/render path entirely) — kept separate from the main B10 finding
above because it is a different literal character and a different file
family (`stilmatch.*`/Style Match, not `web/hjelp/**`).

### Root cause

Content-authoring inconsistency, not a wrong choice of *mechanism*. Both
attributes (`data-i18n` / `data-i18n-html`) exist and work correctly —
`web/hjelp/index.html` alone has 38 `class="hjelp-hvorfor"` paragraphs
bound via plain `data-i18n`, and only 6 of them embed `<strong>` markup.
Someone added an inline `<strong>` lead-in to these 16 specific "why it
matters" strings without switching the corresponding element's attribute
to `data-i18n-html`, and nothing catches the mismatch.

### Fix touchpoints

- The 32 `<p class="hjelp-hvorfor" data-i18n="...">` elements listed in
  the table above (NO: hand-edit; EN: regenerate via
  `scripts/generate_web_i18n_pages.py` after the NO source HTML is
  fixed, per the existing generator workflow) — change `data-i18n` to
  `data-i18n-html`.
- Separately, `web/js/app.js:1295` / `web/js/i18n.js:1694`+`:3437` for the
  Style Match asterisk case, if that is judged in-scope for the same
  fix round (different mechanism — either strip the `*…*` markdown from
  the i18n string, or render it with real `<em>` via a markup-aware path).

### Regression risks

- `tests/test_generate_web_i18n_pages.py` asserts committed `web/en/**`
  byte-matches a fresh generator run — regenerating EN output after a
  `data-i18n` → `data-i18n-html` change in the NO source is required, or
  that test will fail on the next round touching `web/**`.
- `data-i18n-html`'s safety argument (`i18n.js:114-118`) rests entirely on
  these strings being static/author-controlled. Do not repurpose any of
  these 16 keys for interpolated/user-adjacent content later without
  re-reviewing that assumption.
- Any *other* `hjelp.*.hvorfor`-style key that later gains inline markup
  needs the same paired attribute change — this is a recurring authoring
  hazard, not a one-time fix, since nothing enforces the pairing.

### Smallest acceptance criteria

- All 16 keys/32 file instances render actual bold text (a real
  `<strong>` DOM element), not literal `<strong>`/`</strong>` characters,
  on both `web/hjelp/**` and `web/en/hjelp/**`, both before and after
  `applyI18n()` runs.
- `tests/test_generate_web_i18n_pages.py` (the full suite, since this
  touches multiple `web/en/**` files) passes against the regenerated
  output.
- No other `hjelp.*` key's rendering changes.

### Browser requirement

None to *prove* the defect — HTML entity decoding and
`textContent`/`innerHTML` semantics are deterministic, spec-defined
behavior, and the static EN file evidence above already shows the
broken text baked into committed source. A visual check after the fix is
good practice, not a proof requirement.

---

## B11 — mobile help anchor can land under fixed navigation

### Source evidence

- **Anchor targets:** `<article class="hjelp-artikkel" id="...">` (e.g.
  `web/hjelp/index.html:132` `id="forste-oppskrift"`,
  `web/hjelp/index.html:195` `id="og"`) and
  `<div class="hjelp-steg" id="steg-N">` (e.g.
  `web/hjelp/bryggedag.html:153,167,181,195,209`,
  `id="steg-1"`…`id="steg-N"`). Referenced both by in-page TOC links
  (`href="#og"`) and by help-tooltip popovers' "Les mer" links
  (`web/js/help.js:10-108`, e.g. `lesMer: "hjelp/index.html#og"`).
- **Scroll mechanism:** no custom JS offset/`scrollIntoView` handling
  exists for these anchors specifically — the only `scrollIntoView`/hash
  handling in `web/js/*.js` is unrelated (`pantry_page.js:506`,
  `combobox.js:118` for form/dropdown scrolling; `i18n.js:182-191` only
  rewrites the language-switch link's `href` hash, it does not scroll).
  Help anchors rely entirely on the browser's **native** fragment
  navigation, which respects the target element's CSS
  `scroll-margin-top`.
- **Anchor compensation is a flat, unconditional `1rem` (16px):**
  `web/css/style.css:2358-2365` (`.hjelp-artikkel { ...; scroll-margin-top: 1rem; }`)
  and `:2390-2397` (`.hjelp-steg { ...; scroll-margin-top: 1rem; }`).
  Neither rule sits inside a `@media` query — the value is identical on
  mobile and desktop.
- **Fixed nav:** `web/css/style.css:216-` (`.kompaktnav { position:
  fixed; top: 0; left: 0; right: 0; z-index: 40; ...; }`, base padding
  `0.6rem 1.5rem`, 2px bottom border), toggled visible via the
  `.synlig` class. At the mobile breakpoint `@media (max-width: 640px)`
  (`web/css/style.css:270-309`): `.kompaktnav { padding: 0.55rem 1rem;
  }` and `.kompaktnav-logo { width: 34px; height: 34px; }`
  (`:293-304`) — i.e. on mobile the fixed bar's rendered height is
  approximately logo height (34px) + top/bottom padding
  (~0.55rem × 2 ≈ 17.6px) + bottom border (2px) ≈ **~54px**, versus the
  anchor's 16px `scroll-margin-top`.
- **Visibility timing:** `web/js/chrome.js:5-29`, `initHero()`:
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
  ...
  oppdater(); // runs immediately on script load, in addition to scroll/resize listeners
  ```
  On mobile, `.hero`'s height is capped (`max-height: 320px` at
  `≤640px`, `web/css/style.css:270-274`). A deep-linked help article/step
  sits well below the hero, so by the time `oppdater()` runs at load,
  `window.scrollY` (already moved by the native anchor jump) will
  typically already exceed `terskel`, making `.kompaktnav` visible
  right at/around the point the anchor jump lands.
- **The one existing compensation mechanism doesn't reach these
  elements:** `web/js/chrome.js:20-23` sets `--kompaktnav-h` specifically
  so other content can avoid landing under `.kompaktnav`
  (`web/css/style.css:2555-2561`'s comment states this intent
  explicitly). Its **only** consumer is
  `web/css/style.css:2555-2564`, scoped to `@media (min-width: 1000px)`
  and applied to `.bygger-hoyre` (the recipe-builder's sticky results
  panel on `index.html`) — never to `.hjelp-artikkel`/`.hjelp-steg`, and
  never at any mobile breakpoint. No other `scroll-padding-top` or
  `scroll-behavior` rule exists in `web/css/style.css`.

### Root cause

`.hjelp-artikkel`/`.hjelp-steg` compensate for the fixed nav with a flat
16px `scroll-margin-top`, unconditionally, at every viewport size — but
the fixed nav itself is roughly 54px tall on mobile (and a different,
unmeasured height on desktop, where the same 16px value is also used).
The one mechanism designed to solve exactly this class of problem
(`--kompaktnav-h`) exists in the codebase but was never wired to the
help-page anchor targets, only to the builder's sticky panel.

### Fix touchpoints

- `web/css/style.css:2358-2365` / `:2390-2397` — replace the flat
  `scroll-margin-top: 1rem` with something that accounts for
  `.kompaktnav`'s actual rendered height, e.g.
  `scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)`, mirroring
  the existing `.bygger-hoyre` pattern at `:2557-2564`.
- Note `--kompaktnav-h` is only non-zero once `.kompaktnav` has already
  been toggled `.synlig` by `chrome.js`'s `oppdater()` — a fix needs to
  confirm (in-browser) that this value is set *before* the native anchor
  jump happens on initial page load with a `#hash` already in the URL,
  or a purely CSS-side fix may still race JS execution timing. This
  timing question is the browser-verification gap noted below.

### Regression risks

- `--kompaktnav-h` is currently only consumed at `@media (min-width:
  1000px)` for `.bygger-hoyre`; extending its use to
  `.hjelp-artikkel`/`.hjelp-steg` at mobile widths must not
  accidentally add unwanted top-space on desktop help pages, where the
  existing flat `1rem` already works acceptably (no reported desktop
  symptom).
- `chrome.js`'s `oppdater()` sets `--kompaktnav-h` to `0px` whenever
  `.kompaktnav` is not `.synlig` — a `calc()`-based `scroll-margin-top`
  must degrade gracefully to the current 16px behavior in that state
  (already the case with the `var(--kompaktnav-h, 0px)` fallback
  pattern used at `:2562`).

### Smallest acceptance criteria

- On a mobile viewport, following a help deep link (TOC link or "Les
  mer" popover link, or a raw `#hash` URL) leaves the target
  `.hjelp-artikkel`/`.hjelp-steg`'s heading fully visible below
  `.kompaktnav`, not partially hidden under it.
- No visible regression to desktop help-page anchor positioning or to
  the existing `.bygger-hoyre` sticky-panel offset behavior.

### Browser requirement

**Required for full confirmation**, unlike B09/B10. Source alone proves
the *geometry mismatch exists* (16px compensation vs. ~54px fixed-header
height, and the absence of any other compensation reaching these
elements) — that much needs no browser. What source alone does **not**
settle: (a) the exact overlap in pixels at real device widths/font
scaling, since `.kompaktnav-logo`/padding sizes only bound an
approximate height; and (b) whether `--kompaktnav-h` is populated in
time relative to the browser's native anchor-jump on a fresh page load
with a `#hash` already in the URL (a load-order race that only a real
browser trace can settle). Both should be confirmed with real
Chromium+Firefox mobile-viewport checks before considering a fix
complete, per this project's testing policy for anything requiring
functional/visual browser verification.

---

## Coupling / dependencies

- **B09** touches only `web/js/brygg_page.js` (display-time fix) — no
  coupling to B10/B11, and explicitly must not touch `flavor.js`,
  `radar.js`, or `style.js`, which are already correct.
- **B10**'s main fix (16 keys, `data-i18n` → `data-i18n-html`) touches
  `web/hjelp/*.html` (NO source) plus a mandatory regeneration of the
  matching `web/en/hjelp/*.html` files via
  `scripts/generate_web_i18n_pages.py`, and will need a full
  `tests/test_generate_web_i18n_pages.py` run (per
  `.claude/rules/testing.md`) since it spans multiple `web/en/**` files.
  The Style Match asterisk sub-finding (`web/js/i18n.js`,
  `web/js/style.js`, `web/js/app.js`) is a separate code path and could
  be split into its own bounded issue without blocking the main B10 fix.
- **B11** touches only `web/css/style.css` (and possibly, if the load-order
  race in the browser requirement above turns out to matter,
  `web/js/chrome.js`) — no coupling to B09/B10.
- None of B09/B10/B11 touch `#116`/`#98`/`#100`, App/Core/Bryggeskole, or
  `raw_data/unmatched_malt.json`, consistent with this issue's hard
  scope.

## Proposed bounded issue titles

- **B09:** "web: translate system-owned flavor-category labels on the
  English brew log (`brygg_page.js` taste sliders)"
- **B10:** "web: fix 16 help `hvorfor` paragraphs rendering literal
  `<strong>` markup instead of bold text (wrong `data-i18n` vs.
  `data-i18n-html` binding)" — optionally split off a second, smaller
  issue for the Style Match `*…*` asterisk case if not folded into the
  same round.
- **B11:** "web: help-page anchor scroll offset doesn't account for the
  mobile fixed nav's real height (`--kompaktnav-h` not wired to
  `.hjelp-artikkel`/`.hjelp-steg`)"
