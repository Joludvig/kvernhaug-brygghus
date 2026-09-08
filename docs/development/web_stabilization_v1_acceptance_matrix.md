# Web Stabilization V1 — acceptance / test matrix (synthesis only)

*Part of #101 Phase 1 Web Stabilization V1 preparation (issue #133). Synthesizes
the already-merged analysis-only triages —
[web_w5_brew_completion_preflight.md](web_w5_brew_completion_preflight.md),
[web_b06_accessibility_inventory.md](web_b06_accessibility_inventory.md),
[web_b07_learner_guidance_triage.md](web_b07_learner_guidance_triage.md),
[web_b08_handbook_drift_triage.md](web_b08_handbook_drift_triage.md),
[web_b09_b11_triage.md](web_b09_b11_triage.md) — into one practical
acceptance/test matrix, reconciled against #101's own Web Stabilization V1
Definition of Done. **This document does not implement, fix, or re-analyze
anything** — every row below is a pointer back to an already-recorded,
source-proven finding, not a new claim. No `web/**` file was touched to
produce it.*

**Status: docs-only, execution/testing companion to #101. Does not rewrite
#101 and does not start W5/B06–B11 implementation.**

---

## 1. How to read this matrix

Each finding below inherits its evidence, severity, and classification
verbatim from its source triage — this document adds only the seven
cross-cutting dimensions #133 asked for, plus a **trigger bucket** (§3) so a
future implementation round knows how much of the regression sweep it
actually owes.

| Dimension | Meaning |
|---|---|
| **Trust invariant** | The one-sentence promise to the user this finding threatens if left unfixed — not the bug mechanism (already documented in the source triage), the *stake*. |
| **Static test possible** | Can `tests/` (Python, no browser) prove this, today or after a small addition? Almost always **No** for behavior/rendering, per `.claude/rules/testing.md` — `tests/` has zero DOM/browser assertions for `web/**` beyond `test_generate_web_i18n_pages.py`'s i18n-generator/key-symmetry contract. |
| **Browser-required case** | What a live-browser check must actually confirm, phrased as an observable outcome, not a repeat of the source triage's own prose. |
| **NO/EN** | Does the finding/fix need bilingual verification? (Almost every `web/**` finding does, since `web/en/**` is generated from NO source — `.claude/rules/web.md`.) |
| **Learner/Master (L/M)** | Does the finding depend on, or need checking in, both modes, one mode only, or neither (mode-independent)? |
| **Metric/US** | Does the finding depend on, or need checking in, both unit systems? |
| **Viewport** | Which of the roadmap's three representative breakpoints (mobile 390×844, tablet 768×1024, desktop) the finding needs checked. |
| **Chromium/Firefox** | Both engines, or is there a specific reason to expect divergence in only one (e.g. ARIA computed-role mapping, `aria-live` timing)? |
| **Screen reader (SR)** | Required, recommended, or not applicable — per each source triage's own "VERIFY IN BROWSER" list, never invented here. |
| **Persistence** | Does the finding/fix need a save → reload → reopen (or equivalent) round-trip check? |
| **Console/page-error** | Baseline requirement for every `web/**` browser check (§2) — flagged here only where a finding specifically risks throwing (e.g. a null-DOM read). |
| **Production verification** | Does closing this finding require a live-production check per `CLAUDE.md`'s "Normal flyt" (read-only verification against `kvernhaugbrygghus.no` after the user's own manual deploy), or is a scratch-server / Playwright check on the branch sufficient? |

**Legend used in tables**: `Y` = yes/required, `N` = no/not applicable,
`—` = not asserted by the source triage (browser verification still open),
`Both` = both values of that dimension apply.

---

## 2. Minimal reusable browser matrix

Defined once here so later fixes cite it instead of reinventing regression
scope per round. Two layers:

### 2.1 Baseline sweep (`web-full-regression` skill, unchanged) — MUST for every finding needing any browser check at all

- Chromium + Firefox × viewports `[1920, 1280, 768, 375]` (768/375 with
  `has_touch=True`).
- For every combination: 0 console errors, 0 page errors,
  `document.documentElement.scrollWidth <= clientWidth + 1` (no horizontal
  overflow), plus the specific interaction under test.
- Full procedure/gotchas: `.claude/skills/web-full-regression/SKILL.md`.

### 2.2 Reconciliation note — viewport numbers do not match byte-for-byte

The roadmap's Definition of Done (item 9) specifies **390×844** (mobile) and
**768×1024** (tablet); the existing `web-full-regression` skill's matrix uses
**375** (mobile) and **768** (tablet), with no explicit height value for
either. These are close (375 vs 390 is a ~4% width difference; the skill
never pins viewport *height* at all) but **not identical**, and this
document cannot silently pick one without asserting a change to an existing,
already-in-use skill. Recorded here as an open reconciliation item (§5), not
resolved by this synthesis.

### 2.3 Add-on layers, only when the finding requires them

| Add-on | When required | Source |
|---|---|---|
| Screen reader pass (NVDA/Windows + Chromium; VoiceOver/iOS or macOS + Safari) | Any `SR: Required` row below | B06 §"Suggested browser matrix" |
| `aria-live` timing cross-check (Firefox specifically) | Save-status / live-region findings | B06 §"Suggested browser matrix" |
| Real device or touch-emulated tap-target check | `.hjelp-knapp` sizing (B06 #11), any touch-only interaction | B06 finding #11, #20 |
| Deep-link / `#hash` load-order trace | B11 only | B09_B11 triage, B11 "Browser requirement" |
| Bilingual (NO+EN) manual prose read | Any i18n/help wording fix (B07, B08, B09, B10) | each source triage's own "Regression risks"/"Acceptance cases" |
| `tests/test_generate_web_i18n_pages.py` (full run, not just a subset) | Any change spanning multiple `web/en/**` files (e.g. B10's 16-key fix) | `.claude/rules/testing.md`, B09_B11 triage §B10 |

---

## 3. Trigger-frequency buckets

Every finding in §4 is tagged with exactly one bucket, answering "how much
of the sweep does a future fix for this actually owe":

| Bucket | Definition |
|---|---|
| **ALWAYS** | Run for every `web/**` change, regardless of what it touches — the baseline sweep (§2.1) itself. |
| **STATE** | Only when the change touches save/autosave/localStorage, brew/recipe identity, or draft↔saved↔variant transitions. |
| **I18N/HELP** | Only when the change touches `web/js/i18n.js`, any `data-i18n(-html)` binding, or `web/hjelp/**` content. |
| **A11Y/FOCUS** | Only when the change touches labels, ARIA attributes, focus management, or keyboard navigation. |
| **V1-GATE** | Only required once, as part of declaring Web Stabilization V1 complete (#101's own DoD) — not owed by every individual fix round. |

---

## 4. Finding-by-finding matrix

### 4.1 W1–W4 (B01/B02/B03/B05) — completed baseline, no dedicated triage document in this synthesis's source set

**W1 (B01, units), W2 (B02, ABV visible-state), W3 (B03, draft/saved/variant
clarity), and W4 (B05, custom yeast transition) are already implemented,
merged, deployed, and live** from previously completed stabilization rounds
— confirmed by Chief's exact-head review of this document (PR #135,
2026-09-08). This section records a **source-set / documentation gap in this
synthesis**, not an implementation gap: only W5/B04 has a merged preflight
analysis among the five source documents this issue was asked to reconcile
— confirmed by `ls docs/development/web_*` finding only the five documents
listed in this file's header. This synthesis cannot fabricate acceptance
rows for W1–W4 without inventing findings no source backs, which would
violate the same "source-proven, not asserted" discipline every input
document already follows.

**Recorded here as a documentation gap, not a pending-implementation gap**:
if useful for audit consistency later, a retrospective evidence-summary
document (e.g. `web_w1_units_contract_preflight.md` /
`web_w2_abv_visible_state_preflight.md` /
`web_w3_draft_saved_variant_preflight.md` /
`web_w4_custom_yeast_preflight.md`, or a combined document) could be produced
mirroring W5's format, so DoD items 2–4 have the same documented evidentiary
trail DoD item 5 (W5/B04) already has via §4.2 below. This would be
retrospective record-keeping only — **not** a prerequisite or gate for any
further implementation, since W1–W4's product behavior already shipped.

### 4.2 W5 / B04 — brew completion state (source: `web_w5_brew_completion_preflight.md`)

Acceptance scenarios A1–A9 are already fully specified in the source
document's own §9 table — not reproduced verbatim here to avoid drift
between two copies of the same table; this section adds only the
cross-cutting dimensions.

| ID | Item | Trust invariant | Static test possible | Browser-required case | NO/EN | L/M | Metric/US | Viewport | Chromium/FF | SR | Persistence | Console/page-err | Prod verify | Bucket |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W5-1 (A1–A3) | "Avslutt" without a taste judgment leaves the brew invisibly stuck in "Under arbeid" (`brygg_page.js:198-278,403`) | A brew the user marked finished must either appear as finished or visibly say it isn't fully done — never silently vanish into limbo | N — filter/state logic has no `tests/` coverage today | Confirm actual list placement + badge text for A1/A2/A3 in a real browser, per the chosen contract (§6 of source doc, not yet decided) | Y (`brygg.fase.*`, `brygg.avsluttKnapp`, list titles) | N/A (no Learner/Master branching found in bryggelogg, §2.10 of source) | N/A | Desktop + mobile (390×844) — brew-log cards reflow at breakpoints | Both | N | Y (save→reload→reopen must show the same list placement) | Y (baseline) | N until fix ships; then Y | STATE |
| W5-2 (A4) | Forkastet-first precedence must hold even for a `done`-tagged brew | A discarded brew must never reappear as "finished" | N | Confirm `bryggFase()`'s forkastet-first branch still wins after any W5 fix | N/A (state logic, not text) | N/A | N/A | Desktop | Chromium (regression-only) | N | Y | Y | N until fix ships | STATE |
| W5-3 (A5) | Double "Start brygging" click creates two independent active brews with no warning (`app.js:1676-1693`) | Starting a brew once should not silently double-create brew records the user didn't ask for | N | Confirm actual observed behavior (bug vs. intentional) — open question, source doc §10.4 | N/A | N/A | N/A | Desktop | Chromium | N | Y (both brews must persist correctly on reload) | Y | N (still an open product question, §10.4) | STATE |
| W5-4 (A6) | "Neste gang" note on a still-`active` brew shown as prior experience before it's `done` | A note attached to an unfinished brew must not misrepresent itself as settled, finished experience | N | Confirm the note actually renders in the builder pre-`done`, and confirm whether that's intended (source doc §10.2) | Y (`builder.brygg.erfaringTittel`) | N/A | N/A | Desktop | Chromium | N | Y | Y | N (product decision pending) | STATE |
| W5-5 (A7) | NO/EN parity for any new badge/knapp text a W5 fix introduces | Both languages must describe the same state truthfully | Y — `tests/test_generate_web_i18n_pages.py` (key symmetry) once new keys exist | Manual bilingual read (symmetry ≠ correct wording) | Y | N/A | N/A | N/A | N/A | N | N | N/A | N | I18N/HELP |
| W5-6 (A8) | Zero console/network errors across the whole W5 scenario set | A completion-state fix must not introduce new runtime errors | N | Full baseline sweep (§2.1) across the A1–A9 scenario set | N/A | N/A | N/A | All (§2.1) | Both | N | N/A | Y (this **is** the check) | N until fix ships | ALWAYS |
| W5-7 (A9, conditional) | `.kbhbrew` import fallback defaults an incomplete import to `status:"done"` (`brew_storage.js:774`) — only relevant if/when import UI ships | An imported, incomplete brew must not silently claim to be finished | N | Only testable once import UI exists — currently no UI calls `importerBrygg()` | Y (if import UI ships) | N/A | N/A | N/A | N/A | N | Y | Y | N | STATE (dormant until import UI ships) |

**DoD item 5** ("Brew status/list placement is coherent") depends entirely
on W5-1/W5-2 above being resolved per whichever of source-doc §6's
Alternative A/B/C Chief selects — not yet decided (open question, source
doc §10.2).

### 4.3 B06 — accessibility control inventory (source: `web_b06_accessibility_inventory.md`)

All 21 findings share the same cross-cutting shape (accessible names, focus
management), so tabulated together; MUST FIX items (#1–12) and SHOULD FIX
items (#13–15, #21) are both included, reference-quality "no gap" rows
(#16–19) are excluded (nothing to test).

| ID | Item | Trust invariant | Static test possible | Browser-required case | NO/EN | L/M | Viewport | Chromium/FF | SR | Console/page-err | Prod verify | Bucket |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B06-1..6 | Malt/hop numeric inputs have no accessible name (`index.html:373-408`) | Every input a user can act on must be nameable by assistive tech | N — a future `for`/`id` static-pairing check is *proposed* (source §"Tests that could guard the contract") but doesn't exist yet | Confirm actual SR announcement pre/post fix | Y | Both (fields exist in both modes; `.mester-only` only hides the `%` field) | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y (after fix ships) | A11Y/FOCUS |
| B06-7 | Brew-log OG/Volume/FG — orphaned `<label>` (`bryggelogg.html:121-130`) | Same as above, measurement entry specifically | N | Confirm SR announcement pre/post fix | Y | N/A | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-8 | 18 unlabeled tasting sliders per brew (`brygg_page.js:90-113`) — highest-severity single finding in B06 | Every one of up to 18 per-brew sensory controls must be independently nameable | N | Confirm SR announces each of 18 axes distinctly post-fix | Y | N/A | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-9 | Brew-log notes textareas — orphaned labels, 2 of 3 have no placeholder fallback either (`bryggelogg.html:150-159`) | Free-text reflection fields must be nameable | N | Confirm SR announcement post-fix | Y | N/A | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-10 | Combobox missing `aria-controls`/`aria-activedescendant` (`combobox.js:113-118`) — affects malt/hop/yeast/style pickers identically | Keyboard users navigating a searchable list must know what's highlighted | N | Confirm SR announces highlight moves post-fix, all 4 combobox instances | Y | Both | Desktop (combobox is a desktop-pattern-heavy interaction; mobile still needs the touch check) | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-11 | Help "?" buttons — focus not moved on open/close, no initial `aria-expanded`, target size below 24×24 (pending inline-exception check) | Keyboard-only users must be able to reach and dismiss inline help | N | Confirm focus lands in popover and returns to trigger; confirm tap success rate at real widths | Y | Both | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-12 | First-visit mode dialog — no focus trap/initial focus/Escape handler (`index.html:92-105`) | A first-time modal must not strand keyboard focus outside itself | N | Confirm Tab order + Escape behavior in real browser | Y | N/A (this dialog *sets* the mode, so it fires before either mode is active) | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-13 | Tasting judgment button group — `role="group"` with no accessible name (`bryggelogg.html:133-137`) | A grouped control set needs a group-level name, not just visible adjacent text | N | Confirm SR reads a group name post-fix | Y | N/A | Mobile + desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y | A11Y/FOCUS |
| B06-14 | Side drawer — no focus trap (already has correct open/close focus handling) | Tab from the last drawer item should not reach hidden background content | N | Real Tab-key walkthrough with drawer open | N/A | N/A | Mobile + desktop | Both | Recommended | Y | Y | A11Y/FOCUS |
| B06-15 | Radar chart — 18 per-axis values not exposed as text (`radar.js:53-57`) | A sighted user's flavor-wheel numbers should be available to non-sighted users too, if the numbers matter (product call) | N | Confirm what, if anything, SR announces for per-axis values | Y | N/A | Desktop | Both, +NVDA/VoiceOver | **Y required** | Y | Y (if fixed) | A11Y/FOCUS |
| B06-21 | Dead `aria-labelledby` on yeast/style combobox mount, superseded by JS-set `aria-label` | Not currently broken — cleanup only, to prevent future drift | N | N/A (not a live bug) | N | N | N | N | N | N | N | A11Y/FOCUS (low priority) |

**DoD item 8** ("Central controls have useful accessible names") maps
directly onto B06-1 through B06-13 above; item 6 partially overlaps B06-12
(mode dialog) but is really a W1–W4 concern (§4.1).

### 4.4 B07 — Learner guidance pointing at hidden content (source: `web_b07_learner_guidance_triage.md`)

| ID | Item | Trust invariant | Static test possible | Browser-required case | NO/EN | L/M | Viewport | Chromium/FF | SR | Persistence | Console/page-err | Prod verify | Bucket |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B07-1 | "No style match — see nearby styles below" fires while the block is `.mester-only`-hidden (`app.js:1346-1349`) | Guidance shown to a Learner must point at something that Learner can actually see | N — `tests/` has no coverage of conditional rendering | Confirm mode-switch (Learner→Master→Learner) doesn't leave a stale sentence; confirm any `aria-live` announces the change | Y | **Learner-only** trigger, but fix must work correctly when re-entering Master too | Desktop + mobile | Chromium (baseline) | Recommended (does anything announce the disappearing guidance?) | N/A | Y | Y (after fix) | I18N/HELP |
| B07-2 | "See «Nearby styles» below" — same hidden target, second call site (`veiledning.js:83-101`) | Same as B07-1 | N | Same as B07-1, plus confirm this doesn't also render inside `#stil-veiledning-manuell` misleadingly | Y | Learner-only trigger | Desktop + mobile | Chromium | Recommended | N/A | Y | Y | I18N/HELP |
| B07-3 | OG deviation tip names the hidden `#effektivitet` field as one of two options (`veiledning.js:32,39`) | A tip should not name an unreachable control as if it were available | N | Confirm the malt-only half remains actionable pre-fix; confirm full tip post-fix | Y | Learner-only trigger | Desktop | Chromium | N | N/A | Y | Y (after fix) | I18N/HELP |

**DoD item 6** ("Learner ↔ Master switching preserves recipe state and
explains hidden calculation assumptions") is the direct product-level
statement B07-1/2/3 are concrete counter-evidence against today — none of
the three call sites check the active mode before rendering (source doc's
own confirmation, reading `veiledning.js` and `app.js:1331-1400` in full).

### 4.5 B08 — handbook / current-Web drift (source: `web_b08_handbook_drift_triage.md`)

| ID | Item | Trust invariant | Static test possible | Browser-required case | NO/EN | Viewport | Chromium/FF | Console/page-err | Prod verify | Bucket |
|---|---|---|---|---|---|---|---|---|---|---|
| B08-1 | Handbook describes an in-Web "💧 Vannkjemi" module that doesn't exist (App-only) | Handbook text must never send a Web user looking for a feature Web doesn't have | N — this class of drift is inherently semantic, not structural (source doc's own conclusion) | None needed to prove the defect (fully static); a post-fix read-through is good practice, not required | Y | N/A (content-only) | N/A | N/A | Y (content-only, but still deploy-then-verify per CLAUDE.md) | I18N/HELP |
| B08-2 | Handbook describes an in-Web "Prosessprofil" panel (Hochkurz/Dekoksjon/reiterated mash) that doesn't exist (App-only) | Same as B08-1 | N | None needed | Y | N/A | N/A | N/A | Y | I18N/HELP |
| B08-3 | "Skriv ut" panel link points at `index.html` instead of `utskrift.html` | A handbook link must land the reader on the feature it names | N | Click-through confirmation the link now resolves correctly | Y | N/A | Chromium (link check) | N/A | Y | I18N/HELP |
| B08-4 | "Mine lagrede oppskrifter lenger ned" — feature moved to its own page | Location claims must match actual navigation | N | None needed (fully static) | Y | N/A | N/A | N/A | Y | I18N/HELP |
| B08-5 | Builder footer self-inconsistent ("pantry" stale, "vannkjemi" confirms B08-1, "sensorisk analyse" ambiguous/product call) | The product's own chrome must not contradict its own navigation | N | None needed for pantry/vannkjemi; "sensorisk analyse" needs a product decision first | Y | N/A | N/A | N/A | Y | I18N/HELP |

**DoD item 7** ("NO/EN system text is coherent in tested flows") is the
umbrella DoD item all of B08 (plus B07, B09, B10) sit under — B08's five
findings are specifically the "content describes the wrong current state"
subset of that, distinct from B07's "content points at genuinely
inaccessible content" and B09/B10's "content renders visibly broken" cases.

### 4.6 B09/B10/B11 (source: `web_b09_b11_triage.md`)

| ID | Item | Trust invariant | Static test possible | Browser-required case | NO/EN | Viewport | Chromium/FF | SR | Console/page-err | Prod verify | Bucket |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B09 | EN brew log shows Norwegian taste-category labels (`brygg_page.js:90-101`) | An English-locale user should never see untranslated system-generated labels | N (deterministic lookup, but no `tests/` today exercises the actual DOM string) | Visual smoke check of EN brew log post-fix — "good practice, not required to prove the bug" per source doc | Y (EN-only symptom, but NO must stay visually unchanged) | Mobile + desktop | Chromium (baseline) | N | N (fix is display-only) | Y | I18N/HELP |
| B10 | 16 keys / 32 file instances render literal `<strong>` text instead of bold, in both NO and EN, both pre- and post-`applyI18n()` | Help content must render as authored, not as raw markup characters | Y — `tests/test_generate_web_i18n_pages.py` full run required once `web/en/**` is regenerated (spans multiple files) | Visual check that all 16 keys render real bold text, both locales, both pre-JS (static EN file) and post-JS (`applyI18n()`) | Y | N/A (text rendering, not layout) | Chromium (baseline) | N | N | Y | I18N/HELP |
| B10 (Style Match sub-case) | `*…*` markdown asterisks visible in "desired sensory character" text (`style.js:223`→`app.js:1295`) | Same trust invariant as B10 main case, different mechanism | N | Visual check post-fix | Y | N/A | Chromium | N | N | Y (if fixed in same round) | I18N/HELP |
| B11 | Mobile fixed nav (~54px) can cover a deep-linked help anchor (16px `scroll-margin-top` compensation) | Following a help link should land the reader at readable content, not partially hidden text | N | **Required**: exact pixel overlap at real widths; **required**: `--kompaktnav-h` populated before native anchor-jump on fresh load with `#hash` already in URL (load-order race) | N/A (geometry, not text) | Mobile (390×844) primarily; confirm no desktop regression | Both Chromium+Firefox specifically (source doc's own requirement, unlike B09/B10) | N | Y | Y | A11Y/FOCUS (readability) |

---

## 5. Open questions / gaps this synthesis surfaces but does not resolve

Per "say so instead of guessing" — carried forward from the source triages,
not new claims:

1. **W1–W4 (B01/B02/B03/B05) have no dedicated triage document in this
   synthesis's source set** (§4.1) — a documentation/audit-trail gap, not an
   implementation gap: these items are already implemented, merged, and
   deployed (Chief review confirmation, PR #135). DoD items 2, 3, 4, and
   part of 6 therefore rest on the roadmap's own one-line descriptions plus
   their already-shipped status, rather than on a source-proven finding
   list the way W5/B04, B06, B07, B08, and B09–B11 already have — a gap in
   this synthesis's documentation coverage, not in DoD completion.
2. **Viewport number mismatch** (§2.2) between the DoD's 390×844/768×1024
   and the `web-full-regression` skill's 375/768 (no pinned height) —
   needs an explicit reconciliation decision (update the skill, or confirm
   the difference is immaterial) before DoD item 9 can be called
   unambiguously satisfied.
3. **W5's own open questions** (source doc §10, items 2–5): which of
   Alternative A/B/C (§6) Chief wants for the completion-state fix; whether
   double `active`-brew creation (§5 pt. 2) is in scope for W5 or a separate
   issue; whether "Neste gang" pre-`done` visibility (§5 pt. 3) is
   intentional; and whether B04 in the original audit is actually finding 1
   (the source doc itself cannot confirm this without the original audit
   text).
4. **B06's product-judgment items**: whether the radar chart's 18 per-axis
   values need text exposure at all (#15), and whether `.hjelp-knapp`'s
   inline-exception applies to the 24×24 target-size rule (#11) — both
   flagged `SHOULD FIX pending a live/product check`, not `MUST FIX`, in
   the source.
5. **B07's Option A vs. B** (suppress mode-blind text vs. stop hiding the
   target content) is an explicit, unmade product decision in the source
   document — this synthesis does not make it either.
6. **B08-5's "full sensorisk analyse" clause** is explicitly `ambiguous` in
   its own source triage — a product judgment call, not resolved here.
7. **No automated guard exists today** for the semantic class of drift B08
   represents (handbook prose vs. live product truth) — the source triage
   itself concludes this is a poor fit for the existing static i18n-parity
   suite; this synthesis does not propose a new one either.

---

## 6. Dependencies / coupling (rolled up from all five sources)

- None of W5/B04, B06, B07, B08, or B09–B11 touch `#116`/`#98`/`#100`,
  App/Core/Bryggeskole, or `raw_data/unmatched_malt.json` — every source
  triage confirms this independently for its own scope.
- B06 and B07 are file-disjoint (different containers/controls) — no fix
  ordering constraint between them.
- B08-1 and B08-2 share the same defect pattern (App-only Bryggmester
  feature narrated as if in Web) and could reasonably be combined into one
  fix issue, per B08's own note — not decided here.
- B09 and B10 both flow through `web/js/i18n.js`'s `t()`/`applyI18n()`
  mechanism but live in otherwise-independent code paths (per B09_B11
  triage's own "Coupling / dependencies" section) — fixing one does not
  fix the other.
- W1–W4 already shipped as completed prerequisites; their absence of a
  dedicated triage document (§4.1, §5.1) means this synthesis cannot assert
  or rule out **documented** coupling between them and W5/B06/B07 — a
  documentation gap, not an implementation-status question and not an
  assumed "no coupling."

---

## 7. Explicitly out of scope for this issue (per its own hard-scope list)

No `web/**` product file, test, i18n string, CSS, or JS was edited to
produce this synthesis. #101 was not rewritten. W5/B06–B11 implementation
was not started. `#116`/`#98`/`#100`, App/Core/Bryggeskole, deploy, and
`raw_data/unmatched_malt.json` were not touched.
