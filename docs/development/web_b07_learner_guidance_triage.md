# Web B07 — Learner guidance vs hidden content (analysis only)

*Part of #101 Phase 1 NEXT preparation, audit finding B07. Supersedes the B07 portion of #123 (superseded before producing a merged deliverable). GitHub-only, static-source audit of `web/**` — no product code touched, no fix implemented. Everything below is either quoted directly from the current `web/**` source or explicitly flagged as needing a live browser check.*

## How to read this

- **Source**: exact file/line evidence, checked against the repository at the time of writing.
- **Contradiction proof**: `source-proven` (the guidance text and the hidden target are both quoted directly from source, with the CSS rule that hides the target) or `browser verification required` (the static evidence is suggestive but the actual rendered/announced behavior needs a live check).
- **Severity**: `MUST FIX` (guidance names or clearly points at specific hidden content the reader cannot act on), `SHOULD FIX` (a real gap, but softer — partially actionable, or lower-frequency trigger).
- NO and EN are generated from the same DOM/JS (`web/en/**` is machine-generated from the NO source, see `.claude/rules/web.md`) — every finding below applies **identically to both locales** unless stated otherwise; each finding quotes both the `no` and `en` blocks of the relevant `web/js/i18n.js` key to confirm the same structural gap exists in both.

## The visibility mechanism (source-proven)

Learner/Master mode is a single CSS contract, confirmed to apply **only to the builder page** (`web/index.html` / `web/js/app.js`) — no other `web/**` page defines or reads `.mester-only`, `modus-laerling`, or `modus-mester` (confirmed by grep across `web/*.html`, `web/js/*.js`):

```css
/* web/css/style.css:1651-1658 */
@media screen {
  body.modus-laerling .mester-only {
    display: none !important;
  }
}
```

`web/js/app.js:337-339` (`settModus`) toggles `body.classList` between `modus-laerling`/`modus-mester`; `web/js/app.js:355-365` (`initModus`) defaults a first-ever visit to `laerling` (Learner). Any element carrying `.mester-only` is therefore fully removed from the Learner-mode render tree (not merely visually de-emphasized) — a screen reader gets nothing, a sighted user gets nothing, until the user switches to Master mode.

## Prioritized table

| # | Learner-visible guidance | Source | Hidden target it names/implies | Target's hiding mechanism | Contradiction proof | Severity |
|---|---|---|---|---|---|---|
| 1 | `stilanalyse.ingenTreff` — "…adjust the ingredients or **see nearby styles below**." | `web/js/app.js:1348` sets `#stil-headline-info` (not `.mester-only`) whenever `a.stil === "Kreativt Brygg"` (no style matches well enough) | "Nearby styles" list (`builder.stilanalyse.nearbyTittel` + `#stil-alternativ-liste`) | Whole block wrapped `<div class="mester-only">`, `web/index.html:346-352` | source-proven | MUST FIX |
| 2 | `veiledning.samlet` — "…**See «Nearby styles» below** for a concrete alternative that might fit better." | `web/js/veiledning.js:100` (`_byggSamletOppsummering`), rendered into `#stil-veiledning-auto` (`index.html:342`) and `#stil-veiledning-manuell` (`index.html:357`) — neither is `.mester-only` | Same "Nearby styles" block as #1 | Same `.mester-only` wrapper, `web/index.html:346-352` | source-proven | MUST FIX |
| 3 | `veiledning.tips` (OG) — "Tip: **more malt or higher brewhouse efficiency** will bring the recipe closer to the style." | `web/js/veiledning.js:32/39` (`_FELT_TIPS.og`), surfaced via `_feltNivaOgSetning` → same two containers as #2 | Brewhouse-efficiency field (`#effektivitet`) | Field's whole row wrapped `<div class="felt-rad mester-only">`, `web/index.html:189-191` | source-proven | SHOULD FIX (half the tip — "more malt" — stays actionable; only the efficiency alternative is unreachable) |

All three fire from the same subsystem (`web/js/veiledning.js` + `web/js/app.js` `renderStilPanel()`/`renderStilManuell()`/`_renderVeiledning()`) and all three point at content hidden by the single CSS rule quoted above. None of the three call sites check `body.classList.contains("modus-laerling")` or any other mode signal before rendering — confirmed by reading `veiledning.js` in full and `app.js:1331-1400` (`renderStilPanel`, `renderStilManuell`) — the guidance text is generated identically regardless of active mode.

---

## MUST FIX

### 1. "No style matches — see nearby styles below" fires with the list already hidden

`web/js/app.js:1346-1349`:

```js
if (a.stil === "Kreativt Brygg") {
  headlineInfo.textContent = t("stilanalyse.ingenTreff");
  autoContainer.innerHTML = "";
}
```

`web/js/i18n.js:427` (no): `"Ingen stil i biblioteket treffer godt nok ennå — juster ingrediensene eller se nærliggende stiler under."`
`web/js/i18n.js:2170` (en): `"No style in the library matches closely enough yet — adjust the ingredients or see nearby styles below."`

This is written into `#stil-headline-info` (`web/index.html:339`), a plain `<div>` with no `.mester-only` class — visible in both modes. It fires whenever the current recipe doesn't score close enough to any known style at all (`a.stil === "Kreativt Brygg"`, the style-matcher's own "no good match" fallback, `web/js/style.js`) — a routine state for any recipe still far from a target style, not a rare edge case.

The "nearby styles" it tells the Learner to look at:

```html
<!-- web/index.html:346-352 -->
<div class="mester-only">
  <p class="hjelpetekst" id="bu-gu-tekst"></p>
  <div class="stil-alternativer">
    <div class="stil-seksjon-tittel" data-i18n="builder.stilanalyse.nearbyTittel">Nærliggende stiler</div>
    <div id="stil-alternativ-liste"></div>
  </div>
</div>
```

`display: none !important` under `body.modus-laerling` (`web/css/style.css:1651-1658`, quoted above). A first-time visitor — who defaults to Learner mode (`app.js:355-365`) — is told in the very first "no match yet" message to go read a section that does not exist anywhere on their screen; there is no in-page way for a Learner-mode reader to discover that the referenced content requires switching to Master mode.

### 2. "See «Nearby styles» below for a concrete alternative" — same target, second trigger

`web/js/veiledning.js:83-101` (`_byggSamletOppsummering`), called from `byggStilVeiledning` (`veiledning.js:104-122`), called from `_renderVeiledning` (`web/js/app.js:1314-1329`), which is invoked for both:
- the auto/numeric-nearest-style path — `renderStilPanel()`, `app.js:1355`, target container `#stil-veiledning-auto` (`index.html:342`);
- the manually-selected-style path — `renderStilManuell()`, `app.js:1399`, target container `#stil-veiledning-manuell` (`index.html:357`).

Neither container carries `.mester-only`. Trigger condition (`veiledning.js:88-101`): at least two of `{og, ebc, ibu, fg}` deviate from the style's typical range and generate a defined adjective (`_KONSEPT_ADJEKTIV`) — a common state for a recipe that isn't yet well-tuned to any style, not a rare corner case.

`web/js/i18n.js:1699` (no): `"Oppskriften din er {adjektiver} enn typisk for {stil}. Se «Nærliggende stiler» under for et konkret alternativ som kan passe bedre."`
`web/js/i18n.js:3442` (en): `"Your recipe is {adjektiver} than typical for {stil}. See «Nearby styles» below for a concrete alternative that might fit better."`

Points at the identical hidden block quoted under finding #1 (`web/index.html:346-352`). Notably, this text can also render inside `#stil-veiledning-manuell` — the "Valgt stil" (manually chosen style) section — which sits visually *below* the auto section's hidden "Nearby styles" block; a Learner reading the manual-style guidance is pointed at a list that isn't even part of the section they're looking at, compounding the disorientation once Master mode is later discovered.

---

## SHOULD FIX

### 3. OG deviation tip recommends adjusting a field that isn't on screen

`web/js/veiledning.js:73-79` (`_feltNivaOgSetning`), only for `niva === "tydelig"` (a clear, not marginal, deviation — using the same 0.5-normalized threshold `style.js` already treats internally as "critical", per the file's own comment, `veiledning.js:6-8`):

```js
if (niva === "tydelig" && _FELT_TIPS[spraak][felt]) {
  tekst += t("veiledning.tips", { tips: _FELT_TIPS[spraak][felt][avvik.retning] });
}
```

`web/js/veiledning.js:32` (no, `og.under`): `"mer malt eller høyere brygghuseffektivitet"`
`web/js/veiledning.js:39` (en, `og.under`): `"more malt or higher brewhouse efficiency"`
(symmetric `over` variants at the same lines: `"mindre malt eller lavere brygghuseffektivitet"` / `"less malt or lower brewhouse efficiency"`)

Wrapped into `web/js/i18n.js:1698` (no): `" Tips: {tips} vil trekke oppskriften nærmere stilen."` / `web/js/i18n.js:3441` (en): `" Tip: {tips} will bring the recipe closer to the style."` — same two containers as finding #2.

The field named:

```html
<!-- web/index.html:189-191 -->
<div class="felt-rad mester-only">
  <label for="effektivitet"><span data-i18n="builder.grunndata.effektivitet">Brygghuseffektivitet (%)</span> ...</label>
  <input type="number" id="effektivitet" min="1" max="100" step="1" value="75">
</div>
```

Also hidden by the same `.mester-only` CSS rule. Rated `SHOULD FIX` rather than `MUST FIX` because the tip is a two-option "or" — "more malt" *is* actionable in Learner mode (malt rows are never `.mester-only`) — so the guidance is only partially, not entirely, dead; a Learner can still act on it, just not via the option the tip leads with second.

**Checked and cleared (no contradiction found) — kept here so the negative result isn't re-derived later:**
- The FG tip ("a yeast with lower/higher attenuation") names the attenuation-override field (`#attenuation-override-rad`, `index.html:232`) — confirmed **not** `.mester-only`; its show/hide (`app.js:864,869,1655,1818`) is driven by whether a library yeast is selected, not by Learner/Master mode. Visible in Learner mode whenever relevant.
- The IBU tip ("longer boil time or higher alpha acid") names `humle-tid`/`humle-alfa` (`index.html:392,396`) — confirmed **not** `.mester-only`.
- The EBC tip ("more/less specialty malt") and ABV tip ("more malt/higher OG") name no specific control at all, hidden or not.
- The `effektivitet` "?" help-button tooltip content (`web/js/help.js:52-56,104-108`) is itself inside the same `.mester-only` row as the field it explains (`index.html:190`) — hidden together with its trigger, so a Learner-mode reader is never shown an orphaned tooltip trigger for it. Consistent, not a defect.
- `malt.prosent.*` messages and the "Mål-IBU" (`humle-maal-ibu`) per-addition field are only ever surfaced from within their own `.mester-only` rows (`index.html:212-216`, `406-411`) — no Learner-visible text elsewhere references either concept by name.
- The standalone handbook (`web/hjelp/**`, linked via `nav.hjelp` in every page's side drawer, and via the `effektivitet`/`utgjaering`/etc. "Les mer →" tooltip links) is a static reference book with no Learner/Master gating of its own — its content isn't hidden by mode, so it's out of this issue's "Learner-mode guidance vs hidden content" scope; if a handbook page describes a Master-only feature without saying so, that is the stale-content class of problem B08 (see #123's original B08 scope) covers, not this issue.

---

## Smallest bounded future fix (sketch only — not implemented here)

Not a fix spec — a sketch of "done" for a future implementation issue, so scope is bounded when this moves past analysis. Two independent, minimal-diff options exist for findings #1/#2 (and by extension #3, since all three share the same root cause: mode-blind guidance text generation):

**Option A — suppress the mode-blind sentence when in Learner mode.** `_renderVeiledning`/`renderStilPanel`/`renderStilManuell` (`app.js`) would check `document.body.classList.contains("modus-laerling")` before appending the "see nearby styles" / efficiency-tip clauses, or `byggStilVeiledning`/`_byggSamletOppsummering` (`veiledning.js`) would accept the current mode and omit those specific i18n interpolations. Requires new "OG deviates, but no nearby-styles pointer" and "OG deviates, malt-only tip" text variants for Learner mode (`veiledning.js` `_FELT_TIPS`/`veiledning.samlet` would need Learner-safe alternates) — a real content-writing task, not a code-only change.

**Option B — stop hiding "Nearby styles"/`#effektivitet` from Learner mode**, if product judgment is that this content is actually appropriate for Learner (a product decision, not assumed here — Roadmap V2.1's Phase 1 NOW/W1-W5 items don't cover this, and B06 already found unrelated issues in this same `.mester-only` gating elsewhere, so any change to what `.mester-only` covers should be considered once, deliberately, rather than per-finding).

Choosing between A and B (or a mix — e.g. B for "Nearby styles" since #1/#2 together are the higher-frequency, fully-blocking case, A for the OG efficiency tip since it's already half-actionable) is exactly the kind of decision this analysis-only issue is scoped to surface, not make.

## Regression risks (for whichever fix is chosen later)

- Any Learner-mode text change must stay symmetric across `web/js/i18n.js`'s `no`/`en` blocks (`.claude/rules/testing.md` / `tests/test_generate_web_i18n_pages.py` enforces NO/EN key symmetry structurally, but not wording-level correctness — a manual bilingual check is still needed).
- `_byggSamletOppsummering`/`_feltNivaOgSetning` are pure, DOM-independent functions (per `veiledning.js`'s own file-header comment, mirroring `recipe_engine.js`'s DOM-independence convention, `.claude/rules/web.md`) — any mode check added here would need to take mode as a parameter, not read `document.body` directly, to preserve that separation.
- The `Kreativt Brygg` / `stilanalyse.ingenTreff` fallback (finding #1) and the `.stil-veiledning`-driven tips/summary (findings #2/#3) are two structurally different code paths that happen to converge on the same hidden target — a fix to one does not automatically fix the other; both need to be addressed together or the "SUPERSEDED"-style partial-fix risk from a prior round (cf. AGENT_WORKFLOW.md's own documented supersession pattern) repeats here.
- No `tests/` coverage exists for either code path's rendered text content today (`veiledning.js`/`style.js`'s guidance strings are not under `tests/test_generate_web_i18n_pages.py`, which covers the generator/i18n-symmetry contract, not in-page conditional rendering) — a future fix should consider what, if anything, could guard this contract (see below).

## Acceptance cases (sketch, for a future implementation issue)

1. In Learner mode, with a recipe scoring `Kreativt Brygg` (no style match), the "no match" message either omits the "see nearby styles below" clause or the clause is true (the referenced content is actually visible).
2. In Learner mode, with a recipe deviating in ≥2 of `{og, ebc, ibu, fg}` from a matched/selected style, the guidance summary either omits the "see «Nearby styles» below" clause or the clause is true.
3. In Learner mode, with OG deviating "tydelig"/"clearly" from style, the tip either omits the brewhouse-efficiency alternative or that alternative is reachable (i.e., `#effektivitet` is visible) at the moment the tip is shown.
4. Switching Learner → Master → Learner (mid-session, no reload) does not leave a stale guidance sentence referencing content whose visibility just changed — `renderStilPanel()`/`renderStilManuell()` already re-run on relevant state changes; the future fix must confirm they also re-run (or are called) on a mode switch itself, which is **not yet confirmed either way** — VERIFY IN BROWSER / re-check `app.js`'s mode-switch handler (`app.js:376`, the `modus-knapp` click listener) at implementation time.
5. Both NO and EN read naturally after the fix — not merely symmetric key names (existing `tests/test_generate_web_i18n_pages.py` already guards key symmetry; wording quality needs a human bilingual read, same as B06's own acceptance sketch).
6. A future static regression guard is at least considered: e.g. a test asserting that no i18n value reachable from a non-`.mester-only` container contains the literal string `nearbyTittel`'s NO/EN text ("Nærliggende stiler"/"Nearby styles") by cross-referencing which templates/containers are `.mester-only` — feasible in principle (similar in spirit to B06's suggested `for`/`id`-pairing static check) but would need a real DOM-parsing pass over `web/index.html`, not plain string grep, to avoid false positives from the legitimate mode-aware container-based fix (Option A above) that intentionally still contains that string in Master mode's rendered output.

## Browser verification needed

None of the three findings above depend on a live browser check to *prove the contradiction* — the guidance text and the hiding CSS rule are both directly quoted from static source, and `settModus`/`initModus` are read in full to confirm no other suppression logic exists. A future *fix* round would still want a live check of:
- exact screen-reader behavior when `.mester-only` content is removed via `display: none !important` mid-session (a mode switch after the guidance text is already on screen) — does anything (e.g. an `aria-live` region) announce the guidance sentence changing or disappearing;
- real visual/layout confirmation that `#stil-veiledning-manuell`'s reference to the auto-section's "Nearby styles" (finding #2's manual-mode case) doesn't already read as obviously wrong to a real Master-mode user for an unrelated reason (e.g. spatial distance from the referenced block).

## Dependencies / coupling

- **W5 (#118, brew-completion state preflight)** and **B06 (accessibility inventory, this doc's format template)**: no code overlap — different files/containers. Not touched, not blocked by this analysis.
- **#116 / #98 / #100**: not touched.
- **App / Core / Bryggeskole**: not touched — this is a Web-only, `.mester-only` CSS-contract-specific finding; App has no Learner/Master mode split (Roadmap V2.1, "Product roles": App "may remain denser and more advanced than Web" by design, not gated by a mode toggle).
- **B08 (handbook staleness, originally the other half of #123)**: explicitly out of scope here (see "Checked and cleared" above) — if #123's B08 portion is picked up as its own bounded issue later, it should independently audit `web/hjelp/**` rather than relying on anything in this document.
- **`raw_data/unmatched_malt.json`**: not touched.

---

## Explicitly out of scope for this issue (per its own hard-scope list)

No `web/**` product file, i18n string, CSS rule, or JS logic was edited to produce this triage. B07 was not implemented. No deploy occurred. i18n was not touched. App/Core/Bryggeskole, `#116`/`#98`/`#100`, W5, and `raw_data/unmatched_malt.json` were not touched.
