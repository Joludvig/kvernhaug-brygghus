# Web B06 — Accessibility control inventory (analysis only)

*Part of #101 Phase 1 NEXT preparation, audit finding B06. GitHub-only, static-source audit of `web/**` — no product code touched, no fixes implemented. Everything below is either quoted directly from the current `web/**` source or explicitly flagged as needing a live browser check.*

## How to read this

- **Source**: exact file/line evidence, checked against the repository at the time of writing.
- **Accessible name source**: which mechanism (if any) currently gives the control a name exposed to assistive tech — `<label for>`, `aria-label`, `aria-labelledby`, wrapping `<label>`, `title`, or **none** (visual-only: placeholder, adjacent unlabelled text, or icon glyph).
- **Severity**: `MUST FIX` (no accessible name / not operable by keyboard / fails a WCAG 2.1 AA success criterion outright), `SHOULD FIX` (works but with a real gap — e.g. AA passes but the experience is degraded, or an established pattern in this same codebase isn't followed consistently), `VERIFY IN BROWSER` (can't be proven or refuted from static source alone).
- NO and EN are generated from the same DOM/JS (`web/en/**` is machine-generated from the NO source, see `.claude/rules/web.md`) — every finding below therefore applies **identically to both locales** unless stated otherwise. Confirmed by comparing the relevant i18n keys in `web/js/i18n.js` (e.g. `brygg.ogLabel`/`brygg.fgLabel`/`brygg.smakKategori` lines ~486–518 (NO) vs ~2229–2261 (EN) — same structural gap in both).

**A useful cross-check found while auditing**: this codebase already contains the *correct* pattern for several of the gaps below, implemented elsewhere in the same file tree. That is cited throughout as proof the fix is a known, established, minimal-diff pattern — not a redesign.

---

## Prioritized table

| # | Control | File:line | Gap | Severity |
|---|---|---|---|---|
| 1 | Malt row quantity (`kg`) input | `web/index.html:373` | Historical evidence: no `<label>`/`aria-label`; placeholder `"kg"` only. **FIXED in #142 / PR #143** — `aria-label`+`data-i18n-aria-label="builder.malt.mengdeAriaLabel"` added. | FIXED (#142 / PR #143) |
| 2 | Malt row percent (`%`) input | `web/index.html:375` | Historical evidence: same — placeholder `"%"` only. **FIXED in #142 / PR #143** — `aria-label`+`data-i18n-aria-label="builder.malt.pctAriaLabel"` added. | FIXED (#142 / PR #143) |
| 3 | Hop row alpha-acid input | `web/index.html:392` | Historical evidence: same — placeholder `alfa` only. **FIXED in #142 / PR #143** — `aria-label`+`data-i18n-aria-label="builder.humle.alfaAriaLabel"` added. | FIXED (#142 / PR #143) |
| 4 | Hop row grams input | `web/index.html:394` | Historical evidence: same — placeholder `gram` only. **FIXED in #142 / PR #143** — `aria-label`+`data-i18n-aria-label="builder.humle.gramAriaLabel"` added. | FIXED (#142 / PR #143) |
| 5 | Hop row time (min) input | `web/index.html:396` | Historical evidence: same — placeholder `"60"`; also the only sibling numeric field with **no `data-i18n-placeholder`** at all (alpha/gram both have one), so its placeholder text was hardcoded and never localized. **FIXED in #142 / PR #143** — `aria-label`+`data-i18n-aria-label="builder.humle.tidAriaLabel"` and `data-i18n-placeholder="builder.humle.tidPlaceholder"` added. | FIXED (#142 / PR #143) |
| 6 | Hop target-IBU input | `web/index.html:408` | **Correction (Chief review, #142 prep):** already wrapped in a `<label>` (`web/index.html:407-409`), so it already has a correct programmatic accessible name via the wrapping-label mechanism. Not a gap. | — (reference-quality, already correct) |
| 7 | Brew-log OG / volume / FG inputs | `web/bryggelogg.html:121-130` | Historical evidence: sibling `<label>` with no `for`, input had no `id` — zero programmatic association. **FIXED in implementation by #144** — per-brew `id`/`for` wiring added (deployment/live status tracked separately on issue #144). | FIXED (implementation, #144) |
| 8 | Brew-log tasting sliders (18 flavor categories, `input[type=range]`) | `web/js/brygg_page.js:90-118` | Historical evidence: `<label>` built with `textContent` but never linked (`for`/`id`) to its slider; same orphaned-label bug repeated per category, per brew. **FIXED in implementation by #150** — per-brew, per-index `id`/`for` wiring added (deployment/live status tracked separately on issue #150). | FIXED (implementation, #150) |
| 9 | Brew-log "next time" / "what worked" / "what changed" textareas | `web/bryggelogg.html:151,155,157` | Historical evidence: same orphaned-label bug. **FIXED in implementation by #144** — per-brew `id`/`for` wiring added (deployment/live status tracked separately on issue #144). | FIXED (implementation, #144) |
| 10 | Ingredient combobox (malt/hop/yeast/style search) keyboard highlight | `web/js/combobox.js:113-118` | Arrow-key highlight is CSS-only (`.is-active` class); no `aria-activedescendant` on the input, no `id` on `<li role="option">`, no `aria-controls` linking input → listbox | MUST FIX |
| 11 | "?" inline help buttons (concept tooltips) | `web/css/style.css:1777-1804`, `web/js/help.js:112-193` | Touch/click target ~20.8px (`.hjelp-knapp`, 1.3rem) / ~16.8px (`.hjelp-knapp-liten`) — under WCAG 2.5.8 AA's 24×24px minimum (these buttons sit inline within label text, so the SC's "inline exception" may apply — a judgment call needing a rendered-layout check, see VERIFY IN BROWSER); popover never receives focus on open and focus is never returned to the trigger on close; trigger has no `aria-expanded` until *after* first use (attribute is only ever set inside `_apneHjelp`/`_lukkHjelp`, never present in the initial HTML) | MUST FIX (focus) / SHOULD FIX (target size, pending the inline-exception check) / SHOULD FIX (initial `aria-expanded`) |
| 12 | First-visit Learner/Master mode dialog | `web/index.html:92-105`, `web/js/app.js:348-381` | `role="dialog" aria-modal="true"` but no focus moved into the dialog on open, no focus trap, no dedicated Escape handler (only backdrop-click closes it, via `_lukkModusForstegang`) | MUST FIX |
| 13 | Brew-log tasting-judgment button group (yes/maybe/no) | `web/bryggelogg.html:133-137` | Historical evidence: `role="group"` with no `aria-label`/`aria-labelledby`. **FIXED in implementation by #144** — `aria-label` added using `t("brygg.sporsmalSmaking")` ("Ville du brygget dette igjen?" / "Would you brew this again?"), **not** `t("brygg.smakSporsmal")` (a documentation mapping error caught and corrected during #144 — see the SHOULD FIX section below for the full correction). Deployment/live status tracked separately on issue #144. | FIXED (implementation, #144) |
| 14 | Side drawer (`#sidemeny`) | `web/js/chrome.js:29-77` | Focus correctly moves to first link on open and restores to the opening button on close (good — see below); but no focus trap while open, so Tab can reach page content behind the visible backdrop | SHOULD FIX / VERIFY IN BROWSER |
| 15 | 18-axis flavor wheel (radar SVG) | `web/js/radar.js:53-57` | One generic `aria-label` (`builder.smaksprofil.ariaLabel`) summarizes the whole chart; the 18 individual category values are not exposed as text to assistive tech, only as SVG geometry/`<text>` labels without values | SHOULD FIX / VERIFY IN BROWSER |
| 16 | Yeast selector, attenuation override, pantry item form, equipment form | `web/index.html:228-234,120-149`, `web/pantry.html:85,132-148` | **No gap** — correct `<label for>`/`id` or `aria-labelledby` pairing already in place | — (reference-quality, cited as the fix pattern) |
| 17 | Standalone ABV calculator OG/FG fields | `web/verktoy.html:86-91` | **No gap** — same visible labels ("Målt OG"/"Målt FG") as finding #7, but correctly wired with `for`/`id` here | — (proves #7 is an inconsistency, not a technical limitation) |
| 18 | Remove ("✕") buttons on malt/hop rows, brew-log delete, Mine oppskrifter delete | `web/index.html:378,399`, `web/js/brygg_page.js:153-154`, `web/js/mine_oppskrifter_page.js:77-82` | **No gap** — `aria-label` (+ `title`) present on every icon-only remove/delete button found in the codebase; Mine oppskrifter's is even parameterized per-recipe-name so multiple delete buttons in a list stay distinguishable | — |
| 19 | Learner/Master toggle buttons, unit toggle, pantry type toggle | `web/js/app.js:340-341`, `web/js/chrome.js:88-96`, `web/pantry.html:124-126` | **No gap** — `aria-pressed` correctly kept in sync with state on every toggle | — |
| 20 | Mobile-relevant actions | — | No swipe-only or touch-only affordances found (confirmed by grep across all of `web/js/*.js` for touch/swipe/pointer/bottom-nav/FAB patterns — zero matches); same controls as desktop, laid out via `@media` breakpoints (`web/css/style.css:270,1176,1401,1954,2246,...`); most tap targets meet the 44px guideline (`input/select/textarea` `min-height: 2.75rem`, `.fjern-knapp` `min-height/width: 2.6rem`) except `.hjelp-knapp` (finding #11) | Folded into #11 |
| 21 | Yeast/style combobox mount's `aria-labelledby` | `web/index.html:229,203`, `web/js/app.js:1808-1822` | The HTML wires `aria-labelledby` on a mount `<div>` that JS then discards via `.replaceWith(combobox.el)` — the working accessible name actually comes from the `aria-label` the `Combobox` constructor sets on its own `<input>` (`combobox.js:29`), so the `aria-labelledby` markup is dead/orphaned once JS runs. Not currently broken (the `aria-label` fallback works), but redundant and worth cleaning up so the two mechanisms can't drift or conflict | SHOULD FIX |

---

## MUST FIX

### 1–5. Malt/hop numeric inputs — FIXED in #142 / PR #143

**Status: FIXED in implementation.** Implemented in #142 / PR #143 (product head `cfd4e81e0eded8b339d8d09360636c2dffac5bc4`). Deployment/live status is tracked separately on issue #142 under the Kvernhaug Web lifecycle rule `MERGED ≠ DEPLOYED/LIVE`. These are no longer active MUST FIX implementation findings — the section below is retained as historical evidence of the original defect and how it was fixed, not as a description of the current deployment state.

**Correction (Chief review, #142 prep):** the original draft of this section grouped six inputs (#1–6) as missing an accessible name. That is not correct for the sixth: `.humle-maal-ibu` (`web/index.html:407-409`) is already wrapped in a `<label>` and therefore already has a correct programmatic accessible name. It was never part of this MUST FIX group — see its own row in the prioritized table above. The real gap covered exactly five inputs, #1–5, all now fixed.

**Historical evidence (pre-fix state)** — `web/index.html:370-413` (the `<template id="malt-rad-mal">` / `<template id="humle-rad-mal">` used by `leggTilMaltRad()`/`leggTilHumleRad()` in `web/js/app.js`), as it read before #142:

```html
<input type="number" class="malt-mengde" min="0" step="0.05" value="1" placeholder="kg">
...
<input type="number" class="malt-pct mester-only" min="0" max="100" step="0.1" placeholder="%">
...
<input type="number" class="humle-alfa" min="0" step="0.1" placeholder="alfa" data-i18n-placeholder="builder.humle.alfaPlaceholder">
...
<input type="number" class="humle-gram" min="0" step="1" value="10" placeholder="gram" data-i18n-placeholder="builder.humle.gramPlaceholder">
...
<input type="number" class="humle-tid" min="0" step="1" value="60" placeholder="min">
```

(`.humle-maal-ibu` is intentionally omitted from this list — see the correction above.)

None of these five inputs had a `<label>`, `aria-label`, or `aria-labelledby` — no programmatic label / accessible-name mechanism was found for any of them in source. Each is followed by a `<span class="enhet">` (unit text, e.g. `kg`/`%α`/`g`/`min`) that was visually adjacent but **not** programmatically associated (no `id`/`aria-labelledby` link). The source defect was that missing name/association; placeholder text does not supply one — it is not linked via any accessible-name attribute and disappears once a value is typed — which relates to WCAG 3.3.2 (Labels or Instructions) among the applicable success criteria, cited here as context rather than as the complete accessible-name requirement.

**How it was fixed (#142 / PR #143):** each of the five inputs gained a hand-authored Norwegian `aria-label` plus a matching `data-i18n-aria-label` attribute (`builder.malt.mengdeAriaLabel`, `builder.malt.pctAriaLabel`, `builder.humle.alfaAriaLabel`, `builder.humle.gramAriaLabel`, `builder.humle.tidAriaLabel`), using the pre-existing `applyI18n()` mechanism in `web/js/i18n.js` — the same mechanism already used elsewhere in this codebase (see finding #18/#19), not a new one. `.humle-tid` additionally gained `data-i18n-placeholder="builder.humle.tidPlaceholder"` to localize what had been a hardcoded placeholder. Both NO and EN string entries were added to `TEKSTER` in `web/js/i18n.js`, and `web/en/index.html` was regenerated via `scripts/generate_web_i18n_pages.py`. Verified locally in Chromium (NO+EN, multiple malt/hop rows): each field now exposes the intended field-specific accessible name (e.g. "Maltmengde (kg)" / "Malt amount (kg)"), with no `id` collisions across repeated rows.

The searchable ingredient picker in the *same* row (`.combobox-mount`) **does** get a correct `aria-label` via `Combobox({ ariaLabel: t(...) })` (`web/js/app.js:406,672,1811-1837`) — so the picker is fine, only the raw numeric fields next to it are not.

**Existing correct pattern to copy** (same visible concept, different page): `web/verktoy.html:86-91` and `web/index.html:143-144,147-148,228-234` all pair a `<label for="x">` with `<input id="x">`. The unit span could reuse the `aria-labelledby` idiom already used for `#gjaer-velger-mount` (`web/index.html:228-229`: `<label id="gjaer-label">…</label><div aria-labelledby="gjaer-label">`).

### 7. Brew-log OG / Volume / FG measurement fields — FIXED in implementation by #144

**Status: FIXED in implementation.** Implemented in #144 (B06 batch 2). Deployment/live status is tracked separately on issue #144 under the Kvernhaug Web lifecycle rule `MERGED ≠ DEPLOYED/LIVE`. This is no longer an active MUST FIX implementation finding — the section below is retained as historical evidence of the original defect and how it was fixed, not as a description of the current deployment state.

**Historical evidence (pre-fix state)** — `web/bryggelogg.html:121-130`, as it read before #144:

```html
<label class="brygg-og-label"></label>
<input type="number" class="brygg-og" step="0.001" inputmode="decimal">
<label class="brygg-fg-label"></label>
... 
<label class="brygg-volum-label"></label>
<input type="number" class="brygg-volum" step="0.1" inputmode="decimal">
...
<label class="brygg-fg-label"></label>
<input type="number" class="brygg-fg" step="0.001" inputmode="decimal">
```

Text was filled in at runtime (`web/js/brygg_page.js:162-163,188`: `kort.querySelector(".brygg-og-label").textContent = t("brygg.ogLabel")`, etc.) but **no `for`/`id` was ever set**, in the template or in JS. The `<label>` and `<input>` were DOM siblings only — visually adjacent, not programmatically linked. Same visible strings ("Målt OG"/"Målt FG") were already correctly wired in `web/verktoy.html:86-91` (finding #17) — that was the exact fix pattern (add a stable `id` to each input, add matching `for` to each label).

**How it was fixed (#144):** the brew log can render multiple `.brygg-kort` cards simultaneously (one per active brew, all cloned from the same `<template>`), so a bare static `id` like `"brygg-og"` would collide across cards — `web/js/brygg_page.js` now assigns a per-brew-scoped `id` (`` `${brew.brewId}-og` ``, `` `${brew.brewId}-volum` ``, `` `${brew.brewId}-fg` ``, reusing the existing `brew.brewId` from `_genererBrewId()` in `brew_storage.js` as the DOM-id namespace — no new persistent identity introduced) via a small helper (`_kobleBryggFeltIder()`) run unconditionally right after cloning each card, so hidden fields get their id/for pairing too, not just the fields visible in the card's current phase. Verified locally in Chromium (NO+EN, 4 concurrent brew cards across bryggedag/gjæring/smaking/forkastet phases): each `id`/`for` pair resolves correctly (`input.labels` returns exactly the intended `<label>`), no duplicate ids across cards, before or after save/re-render.

### 8. Brew-log tasting sliders — FIXED in implementation by #150

**Status: FIXED in implementation.** Implemented in #150 (B06 batch 3). Deployment/live status is tracked separately on issue #150 under the Kvernhaug Web lifecycle rule `MERGED ≠ DEPLOYED/LIVE`. This is no longer an active MUST FIX implementation finding — the section below is retained as historical evidence of the original defect and how it was fixed, not as a description of the current deployment state.

`web/js/brygg_page.js:90-113` (pre-fix):

```js
function _byggSmakSliders(container, brew) {
  container.innerHTML = "";
  const predikert = (brew.snapshot.predicted && brew.snapshot.predicted.flavorProfile) || {};
  const faktisk = (brew.sensing && brew.sensing.flavorProfile) || {};
  for (const kategori of Object.keys(predikert)) {
    const rad = document.createElement("div");
    rad.className = "brygg-smak-rad";
    const label = document.createElement("label");
    label.textContent = t("brygg.smakKategori", { kategori, forventet: ... });
    const input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = String(SMAKS_SKALA_MAKS);
    input.step = "0.5";
    input.className = "brygg-smak-slider";
    input.dataset.kategori = kategori;
    input.value = ...;
    rad.appendChild(label);
    rad.appendChild(input);
    container.appendChild(rad);
  }
}
```

This ran once per flavor category (up to all 18 in `SMAKS_KATEGORIER`, `web/js/flavor.js:5-9`) every time a brew reaches the "smaking" (tasting) phase. Neither `label` nor `input` ever got an `id`/`for` — this was the single highest-severity finding in this inventory: up to 18 unnamed `<input type="range">` controls per brew — no programmatic label / accessible-name mechanism was found for any of them in source, so a screen reader had no per-slider name to announce for which flavor axis (Maltfylde, Karamell, Sitrus, …) it adjusts. **How it was fixed (#150):** the same loop now assigns a deterministic, brew-scoped `input.id` (`` `${brew.brewId}-smak-${indeks}` ``, an index over `Object.keys(predikert)` — never derived from translated category display text) and sets `label.htmlFor` to that same id; `input.dataset.kategori` remains the canonical (untranslated) key `_lesSmakSliders()` reads, unchanged. Live browser verification (screen reader announcement, multi-card id uniqueness) is tracked as owner/manual pending — see "VERIFY IN BROWSER" below.

### 9. Brew-log "next time" / "what worked" / "what changed" notes — FIXED in implementation by #144

**Status: FIXED in implementation.** Implemented in #144 (B06 batch 2). Deployment/live status is tracked separately on issue #144 under the Kvernhaug Web lifecycle rule `MERGED ≠ DEPLOYED/LIVE`. This is no longer an active MUST FIX implementation finding — the section below is retained as historical evidence of the original defect and how it was fixed, not as a description of the current deployment state.

**Historical evidence (pre-fix state)** — `web/bryggelogg.html:150-159`, as it read before #144:

```html
<label class="brygg-nesteganglabel"></label>
<textarea class="brygg-nestegang" rows="3"></textarea>
<details class="brygg-laering-mer">
  <summary class="brygg-laering-summary"></summary>
  <label class="brygg-fungerte-label"></label>
  <textarea class="brygg-fungerte" rows="2"></textarea>
  <label class="brygg-endret-label"></label>
  <textarea class="brygg-endret" rows="2"></textarea>
</details>
```

Same orphaned-label pattern as #7, text populated the same way in `web/js/brygg_page.js:239,244,246,285` — same fix. One additional detail worth noting: `.brygg-nestegang` does get a `placeholder` fallback (`brygg_page.js:241`), but `.brygg-fungerte`/`.brygg-endret` ("what worked" / "what changed") got **neither** a `for`/`id` link **nor** a placeholder — those two fields had zero accessible name and zero visual fallback hint, the weakest case in this group.

**How it was fixed (#144):** covered by the same `_kobleBryggFeltIder()` helper and per-brew-scoped `id` scheme described under finding #7 above (`` `${brew.brewId}-nestegang` ``, `` `${brew.brewId}-fungerte` ``, `` `${brew.brewId}-endret` ``) — one mechanism, one file, both findings fixed in the same pass since they share the exact same fix pattern. `.brygg-nestegang`/`.brygg-nesteganglabel` are also reused in the `forkastet` (discarded) render branch (`brygg_page.js:281-286`) — verified locally that the discarded-brew card's "Next time" textarea keeps its correct `id`/`for` pairing there too, not only in the smaking/ferdig branch.

### 10. Ingredient combobox — incomplete ARIA combobox pattern

`web/js/combobox.js`:

- Line 26-28: `role="combobox"`, `aria-expanded`, `aria-autocomplete="list"`, optional `aria-label` — correct start.
- Line 34: `list.setAttribute("role", "listbox")` — correct.
- Line 82: `li.setAttribute("role", "option")` — correct.
- Line 113-118 (`_move`, arrow-key navigation): highlight is applied/removed via `classList.add/remove("is-active")` only. **No `id` is ever assigned to the `<li>` options**, **no `aria-controls` on the input pointing at the listbox `<ul>`**, and **no `aria-activedescendant` set on the input** as the highlight moves.

Net effect: sighted mouse/keyboard users see the highlighted option move; the source facts are that no option `<li>` has an `id`, and neither `aria-controls` nor `aria-activedescendant` is ever set on the input — the two most load-bearing attributes of the standard WAI-ARIA Combobox pattern, both currently missing. Whether/what a screen reader announces (or fails to announce) as the highlight moves is not asserted here — **VERIFY IN BROWSER** (NVDA/VoiceOver) is required to confirm actual behavior. This affects all four comboboxes built from this shared class (malt, hop, yeast, style — `web/js/app.js:403-409,663-673,1808-1813,1833-1838`) identically in both NO and EN.

Two smaller, related notes on the same widget:
- Optgroup headers (`.combobox-gruppe-header`) are deliberately marked `aria-hidden="true"` per the file's own comment ("grouping is purely visual"). Defensible as-is — it means screen-reader users get a flat, ungrouped list while sighted users see grouped sections, which is a reasonable simplification rather than a defect — but worth recording since it's a real, intentional divergence in experience between input modalities.
- The yeast (`#gjaer-velger-mount`) and style (`#stil-velger-mount`) pickers wire `aria-labelledby` on their HTML mount `<div>`, but `app.js` immediately `.replaceWith()`s that div with the `Combobox`'s own element (whose accessible name instead comes from an `aria-label` the constructor sets directly on its `<input>` — `combobox.js:29`). The `aria-labelledby` markup in `index.html` therefore never actually applies to anything live once the page runs; the fallback `aria-label` happens to cover for it, so this is not currently broken, just dead/redundant markup worth cleaning up (see finding #21 in the prioritized table).

### 11. "?" help buttons — target size and focus handling

`web/css/style.css:1777-1804`:

```css
.hjelp-knapp {
  width: 1.3rem;   /* ≈ 20.8px */
  height: 1.3rem;
  border-radius: 50%;
  ...
}
.hjelp-knapp-liten {
  width: 1.05rem;  /* ≈ 16.8px */
  height: 1.05rem;
}
```

Both sizes are below the WCAG 2.2 §2.5.8 (AA) 24×24 CSS-pixel minimum target size (2.2 is not yet a hard requirement under a 2.1 AA target, but is worth flagging given how many of these buttons exist across the builder — every malt/hop alpha-acid unit span and the yeast attenuation label carries one). Mitigating factor worth stating plainly rather than resolving unilaterally: SC 2.5.8 has an "inline" exception for a target that sits within a line of text, and every `.hjelp-knapp` found does sit inline next to its label text (e.g. `<span>OG</span> <button class="hjelp-knapp hjelp-knapp-liten">?</button>`) — whether that exception actually applies depends on the rendered layout, not the CSS box size alone, so this is listed as SHOULD FIX pending a live check rather than an outright MUST FIX.

`web/js/help.js:112-193` (`_apneHjelp`/`_lukkHjelp`/`initHjelp`): the popover (`role="dialog"`, line 165) never receives focus when opened (no `.focus()` call anywhere in the file), and focus is never restored to the triggering "?" button when the popover closes (via Escape, outside click, or its own close button, line 133/139/183-185/189). A keyboard user can open the popover but has no way to reach its "Les mer →" link or ✕ close button without first tabbing there from wherever focus already was. Additionally, the trigger buttons (e.g. `web/index.html:233,393`) have no `aria-expanded` attribute in their initial markup at all — the attribute is only ever added by `_apneHjelp`/removed by `_lukkHjelp` (`help.js:117,157`), so before first use assistive tech has no way to know the button is a disclosure control.

### 12. First-visit Learner/Master mode dialog — no focus management

`web/index.html:92-105`:

```html
<div class="modus-forstegang no-print" id="modus-forstegang" role="dialog" aria-modal="true" aria-labelledby="modus-forstegang-tittel" hidden>
  <h2 id="modus-forstegang-tittel" ...>Hvordan vil du brygge?</h2>
  ...
  <div class="modus-bryter" role="group" aria-label="Velg modus" ...>
    <button type="button" class="modus-knapp" data-modus="laerling">...</button>
    <button type="button" class="modus-knapp" data-modus="mester">...</button>
  </div>
</div>
```

`web/js/app.js:355-381` (`initModus`) shows the dialog is `hidden = false`'d when no mode preference is stored yet, but no code moves focus into it (no `.focus()` call in `initModus`/`_lukkModusForstegang`), there is no focus trap, and the only listed close path is a backdrop click (line 380) — no dedicated `Escape` handler exists for this dialog (compare `web/js/app.js:1095-1103`, the equipment modal, which does have both an `Escape` listener and an explicit `.focus()` call on open, line 1130). `aria-modal="true"` asserts to assistive tech that background content is inert while this is open, which is not actually enforced (no focus trap), and a modal dialog opened via `hidden=false` without moving focus into it leaves keyboard focus wherever it was on the page — likely the `<body>` — when the dialog appears, on both first-ever page load, in both languages.

---

## SHOULD FIX

- **#13 — FIXED in implementation by #144.** Historical evidence: `web/bryggelogg.html:133-137`: `<div class="modus-bryter brygg-dom-bryter" role="group">` had no `aria-label`/`aria-labelledby`. **Correction to this section's own original framing (caught during #144):** the text above previously pointed at `.brygg-smak-sporsmal` (populated with `t("brygg.smakSporsmal")`, "Ble ølet omtrent som du forventet?") as visually supplying the judgment group's question — that was wrong. The judgment buttons (yes/maybe/no) answer the *earlier*, general `.brygg-sporsmal` question (populated with `t("brygg.sporsmalSmaking")`, "Ville du brygget dette igjen?" — see `brygg_page.js:230`), a **separate** question from the flavor-match prompt `.brygg-smak-sporsmal` supplies further down the same card. **How it was fixed (#144):** `aria-label` added to `.brygg-dom-bryter` using the existing `t("brygg.sporsmalSmaking")` key — not `t("brygg.smakSporsmal")` — no new i18n key, no visible text change, `role="group"` kept. `.brygg-smak-sporsmal`/`brygg.smakSporsmal` are unchanged and remain used exclusively for the separate flavor-match prompt. Deployment/live status tracked separately on issue #144.
- **#14** — `web/js/chrome.js:29-77` (`initSidemeny`): genuinely good focus handling already exists — `apne()` moves focus to the first focusable element in the drawer (line 51: `var forsteLenke = meny.querySelector("a, button"); if (forsteLenke) forsteLenke.focus();`) and `lukk()` restores focus to whichever button opened it (line 60: `if (sisteApnetFra) sisteApnetFra.focus();`), plus a global `Escape` handler (line 73-75). The one gap: no focus trap, so `Tab`/`Shift+Tab` from the last/first focusable drawer item can reach the backdrop-covered page content behind it. Needs a live check to confirm actual tab order behavior (see below) before deciding whether a trap is worth the added complexity for a drawer that isn't strictly modal.
- **#15** — `web/js/radar.js:53-57`: `aria-label` on the `<svg>` names the chart as a whole (`t("builder.smaksprofil.ariaLabel")`) but the 18 per-axis values are rendered only as SVG `<text>` positioned around the polygon (lines 77-93) with no accompanying accessible data table or `aria-describedby` value summary. Whether this actually matters depends on how the chart is used (decorative sensory summary vs. something a user needs the exact numbers from) — recommend a product decision, not an assumed fix.

## VERIFY IN BROWSER

1. **Announcement behavior for the now-linked tasting-slider range controls (#8, FIXED in implementation by #150) and the still-unlabeled combobox arrow-key highlight (#10)** — this inventory deliberately does not assert an exact screen-reader utterance for either; a real NVDA/VoiceOver pass is needed to confirm what is actually announced. #8's browser verification (id uniqueness across multiple simultaneous cards, `input.labels` resolution, NO/EN category names) is owner/manual pending — see #150. (#1–5 are now FIXED and browser-verified per #142/PR #143 above; #6 was never a gap.)
2. **Combobox aria-activedescendant fix (#10)** and **help popover focus (#11)** — once implemented, needs a real screen reader pass (NVDA/VoiceOver) to confirm announcements are correct, not just "attributes present."
3. **Side-drawer focus trap (#14)** — needs an actual Tab-key walk-through with the drawer open to confirm whether focus really does leak to background content, and whether that's perceptible/harmful in practice (the backdrop is only a visual overlay, not `inert`/`aria-hidden` on the rest of the page — worth confirming background content doesn't get `Tab`-focused invisibly under the backdrop).
4. **Modal dialog inert background (#12)** — confirm with a screen reader whether background content (page body) is actually reachable via swipe/virtual cursor while `#modus-forstegang` is open, despite `aria-modal="true"`.
5. **Touch target sizing (#11, `.hjelp-knapp`)** — confirm real fat-finger tap success rate on a phone; CSS size alone doesn't account for padding/hit-area tricks that might not be present here.
6. **Radar chart per-axis values (#15)** — confirm with a screen reader exactly what, if anything, is announced when focus reaches or a user inspects the flavor-wheel SVG.
7. **Color-only state cues** — `.modus-knapp`/`.enhet-knapp`/pantry-type-knapp active states: confirmed these all also set `aria-pressed` (not color-only, see finding #19), but the exact focus-visible/active visual contrast in both light states should still get a quick manual contrast check — out of grep-able scope for this static pass.

---

## Suggested minimal acceptance criteria

Not a fix spec — a sketch of "done" for a future implementation issue, so scope is bounded when this moves past analysis:

1. Every form control in `web/index.html`'s malt/hop row templates has a real accessible name (`aria-label` or `aria-labelledby`, matching the localized unit/field concept) in both NO and EN. **FIXED in #142 / PR #143.**
2. Every `<label>`/`<input>`/`<textarea>` pair currently built in `web/js/brygg_page.js` and `web/bryggelogg.html` gets a matching `id`/`for`, including the per-category tasting sliders. **OG/Volume/FG and the three learning textareas (#7, #9) FIXED in implementation by #144; the tasting-slider half of this item (#8) FIXED in implementation by #150.** The judgment group's accessible name (#13) is also now FIXED in implementation by #144, via `aria-label` rather than `id`/`for` (a static group name needs no per-brew id).
3. `web/js/combobox.js` sets `aria-controls` (input → listbox `id`) and `aria-activedescendant` (input → highlighted option `id`) on every keyboard highlight move, and clears `aria-activedescendant` when the list closes.
4. `web/js/help.js` popovers move focus to themselves (or their first focusable element) on open and restore focus to the triggering button on close; trigger buttons carry `aria-expanded="false"` in their initial markup.
5. `#modus-forstegang` either gains a focus trap + initial `.focus()` on its first button, or (simpler, if product wants it) drops `aria-modal="true"` if a lighter, non-trapping treatment is intentionally preferred — a product decision, not assumed here.
6. `.hjelp-knapp`/`.hjelp-knapp-liten` meet a minimum 24×24 CSS px hit target (padding can achieve this without changing the visual glyph size).
7. Regression coverage: since `tests/` has no browser/DOM assertions today (per `.claude/rules/testing.md`), any fix here still needs the manual Playwright sweep (`web-full-regression` skill) rather than a new automated a11y test, unless the fix round explicitly adds one.

## Suggested browser matrix

Matches the existing manual sweep's matrix (per `.claude/rules/testing.md`, `web-full-regression` skill) plus one screen reader per platform family, since none of the above can be confirmed by source reading alone:

| Combination | Why |
|---|---|
| Chromium desktop + NVDA (Windows) | Most common desktop screen reader pairing |
| Safari desktop or iOS + VoiceOver | Confirms combobox/dialog focus behavior on the platform most likely to diverge from Chromium's ARIA computed-role mapping |
| Firefox desktop | Already in the existing regression matrix; cross-check ARIA live-region (`aria-live="polite"` save-status messages) timing, which can differ from Chromium |
| Mobile Chrome/Safari, touch-only | Confirms `.hjelp-knapp` real-world tap success and whether the side-drawer backdrop actually blocks background touch interaction |

## Tests that could guard the contract

- A future `tests/test_generate_web_i18n_pages.py`-style static check could assert, for a fixed allow-list of `<label>`/`<input>` id pairs (e.g. every `id` referenced by a `for=` attribute in `web/index.html`, `web/bryggelogg.html`, `web/pantry.html`, `web/verktoy.html`), that the referenced `id` actually exists in the same document — a cheap regression guard against exactly the drift found in `web/bryggelogg.html` here, without needing a real browser.
- No such check exists today; `tests/` currently has zero DOM/browser-level assertions for `web/**` beyond the i18n generator's own output-parity checks (`.claude/rules/testing.md`).

---

## Explicitly out of scope for this issue (per its own hard-scope list)

No `web/**` product file, i18n string, or ARIA attribute was edited to produce this inventory. No accessibility fix was implemented. No deploy occurred. W5 was not started. `#116`/`#98`/`#100`, App/Core/Bryggeskole, and `raw_data/unmatched_malt.json` were not touched.
