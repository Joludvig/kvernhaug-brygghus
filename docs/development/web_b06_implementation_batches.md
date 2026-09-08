# Web B06 — Accessibility implementation batching plan (analysis only)

*Part of #101 Phase 1 NEXT preparation. Builds on the merged
[web_b06_accessibility_inventory.md](web_b06_accessibility_inventory.md) (21
findings, source-proven, `web/**`). Docs-only — no `web/**` file, i18n
string, or ARIA attribute is edited by this document; no fix is
implemented; no batch below is opened as an issue by this document itself.
Everything below is either quoted/cited directly from current `web/**`
source or explicitly flagged as needing a live browser check, exactly as
the inventory it builds on does.*

## How to read this

- **Batch** = the smallest unit this plan recommends implementing and
  reviewing as one bounded future issue/PR.
- Each batch lists the inventory finding numbers it covers (`#N` refers to
  the numbering in `web_b06_accessibility_inventory.md`'s prioritized
  table), then the nine fields the parent issue asked for: exact
  files/functions/selectors; exact acceptance criteria; NO/EN
  implications; keyboard/focus cases; mobile implications; screen-reader
  verification needed vs. source-testable; static test opportunities;
  regression risks; dependencies on W5/B07/B08/B09-B11.
- Where this plan's grouping **disagrees** with the candidate grouping
  listed in the parent issue's own "at minimum assess" bullet list, that
  disagreement is called out explicitly with the source evidence behind
  it — the issue asked for an assessment, not a restatement.

---

## Proposed batch order

| Order | Batch | Findings | Severity | Regression risk |
|---|---|---|---|---|
| 1 | Malt/hop numeric input accessible names | #1–5 | **COMPLETED — implemented in #142 / PR #143** | Low |
| 2 | Brew-log OG/FG/Volume/textareas + judgment-group label | #7, #9, #13 | **COMPLETED IN IMPLEMENTATION — implemented by #144** | Low–Medium |
| 3 | Brew-log tasting sliders | #8 | MUST FIX — **next pending implementation batch** | Medium–High |
| 4 | Shared combobox ARIA + dead `aria-labelledby` cleanup | #10, #21 | MUST FIX (+1 SHOULD FIX) | High |
| 5 | Help popover focus handling + initial `aria-expanded` | #11 (focus half) | MUST FIX | Medium |
| 6 | Touch-target sizing | #11 (size half), #20 | SHOULD FIX | Low |
| 7 | First-visit Learner/Master dialog focus handling | #12 | MUST FIX | Low |
| 8 | Side-drawer focus trap | #14 | SHOULD FIX | Low (blocked on a UX decision) |
| 9 | Radar chart per-axis values | #15 | SHOULD FIX | Low (blocked on a product decision) |

## Rationale for this order

1. **All MUST FIX batches (1–4) before any SHOULD FIX batch.** Matches the
   parent issue's instruction to "prioritize trust/operability over
   cosmetic cleanup" — every SHOULD FIX item here is either genuinely
   lower-severity (#13's group label, #20 folded into #11) or explicitly
   blocked on a product/UX decision the inventory itself declined to make
   (#14, #15).
2. **Within the MUST FIX tier, ascending regression risk/blast radius.**
   Batch 1 touches a template with no shared-state hazards. Batch 2 is
   mechanically identical (add `id`/`for`) but must additionally get
   per-brew-card `id` uniqueness right (see Batch 2 below). Batch 3 is the
   only MUST FIX batch that generates `id`s in a loop and has two live
   cross-issue coordination points (B09, W5 — see below). Batch 4 (the
   combobox) is placed **last** among MUST FIX batches deliberately: it is
   a single shared component instantiated by four different pickers on the
   same page simultaneously (malt/hop rows repeat it per row), so it is
   the single highest blast-radius change in this whole plan — landing it
   after 1–3 lets whatever `id`-uniqueness convention those batches settle
   on (see Batch 2/3) be reused here instead of invented fresh under more
   risk.
3. **Batches 8 and 9 are last because they cannot start at all yet** — the
   inventory itself flags both as needing an explicit product/UX decision
   before an acceptance criterion can even be written (see each batch
   below). Scheduling them at the end reflects that blocker, not low
   priority relative to Batch 6/7 as such.

---

## Batch 1 — Malt/hop numeric input accessible names

**Status: COMPLETED — implemented in #142 / PR #143** (exact head
`cfd4e81e0eded8b339d8d09360636c2dffac5bc4`). Everything below this line is
retained as the original planning record for reference; it is no longer a
future/pending batch.

**Findings:** #1–5 (malt kg, malt %, hop alpha-acid, hop grams, hop time —
all MUST FIX, no accessible name — now fixed). **Correction (Chief review, #142 prep):**
finding #6 (hop target-IBU, `web/index.html:408`) is not part of this batch
— `.humle-maal-ibu` is already wrapped in a `<label>` and already has a
correct accessible name; it was not touched.

- **Files/functions/selectors:** `web/index.html` — `<template
  id="malt-rad-mal">` (`:373,375`) and `<template id="humle-rad-mal">`
  (`:392,394,396`); populated per-row by `leggTilMaltRad()` /
  `leggTilHumleRad()` in `web/js/app.js`. New/changed i18n keys land in
  `web/js/i18n.js` (NO block ~486–518, EN block ~2229–2261, per the
  inventory's own citation).
- **Acceptance criteria:** each of the five inputs gets a real accessible
  name (`aria-label` is the minimal-diff choice here, since these are
  templated rows with no natural static `id` to hang a `<label for>` on
  without also solving cross-row `id` uniqueness for no reason — `aria-label`
  needs none). Name text matches the localized unit/field concept (e.g.
  "Mengde (kg)" not just "kg", to avoid duplicating the adjacent
  `.enhet` span verbatim with no field context). `humle-tid`'s placeholder
  gap (finding #5: hardcoded `"60"`, no `data-i18n-placeholder`) is fixed
  in the same pass since it's the same template file and the same kind of
  attribute addition. Existing visible placeholder text and `.enhet` unit
  spans are unchanged.
- **NO/EN implications:** new i18n keys need both NO and EN entries,
  regenerated through the normal `scripts/generate_web_i18n_pages.py`
  pipeline per `.claude/rules/web.md` — no new mechanism needed, this is
  the same key-adding process every other Web round already uses.
- **Keyboard/focus cases:** none — these inputs are already natively
  focusable and operable; this batch adds a name, not new interaction.
- **Mobile implications:** none — no layout/size change.
- **Screen-reader verification needed vs. source-testable:** the
  attribute addition itself is fully source-testable (grep for
  `aria-label` presence on each selector). The inventory's own "VERIFY IN
  BROWSER" item 1 (current pre-fix announcement) becomes moot once fixed;
  a lightweight live check (NVDA/VoiceOver reads the new name once per
  input type) is still worth doing but is low-stakes since the fix is a
  static attribute, not new logic.
- **Static test opportunities:** the inventory itself suggests (its
  "Tests that could guard the contract" section) a static `id`/`for`
  cross-reference check across `web/index.html`/`bryggelogg.html`/
  `pantry.html`/`verktoy.html`. Since this batch uses `aria-label` rather
  than `id`/`for`, a simpler static check for this batch specifically
  would be: grep the five selectors in `web/index.html` and assert each
  carries an `aria-label` attribute — cheap, no browser needed, but only
  covers "an attribute exists," not "the announced name is correct."
- **Regression risk:** Low — pure attribute addition on template markup
  used identically today; no `id` uniqueness concern since `aria-label`
  is used, not `id`/`for`.
- **Dependencies on W5/B07/B08/B09-B11:** none. Different files entirely
  (`web/index.html` malt/hop builder templates vs. brew-log/handbook
  files those touch).

**Issue/PR (actual):** #142 / PR #143 — *"WEB FIX — B06 batch 1: accessible names for malt/hop numeric inputs"*.

---

## Batch 2 — Brew-log OG/FG/Volume + textareas + judgment-group label

**Status: COMPLETED IN IMPLEMENTATION — implemented by #144.** Deployment/
live status is tracked separately on issue #144 under the Kvernhaug Web
lifecycle rule `MERGED ≠ DEPLOYED/LIVE`. Everything below this line is
retained as the original planning record for reference; it is no longer a
future/pending batch. **One correction to the plan below, caught during
#144 implementation:** the judgment-group `aria-label` acceptance criterion
originally named the wrong i18n key (`brygg.smakSporsmal`) — see the two
corrected bullets below for the fix (the actual implementation uses
`brygg.sporsmalSmaking`). The actual per-field `id` scheme implemented is
also slightly simpler than sketched below: `` `${brew.brewId}-og` `` etc.
(no extra `"brygg-"` prefix — `brew.brewId` already reads as `brew-<uuid>`,
so the prefix was redundant) — see the accessibility inventory's #7/#9
entries for the exact scheme and verification evidence.

**Findings:** #7 (OG/FG/Volume, MUST FIX — now fixed), #9
(nextTime/whatWorked/whatChanged textareas, MUST FIX — now fixed), #13
(tasting judgment-group label, SHOULD FIX — now fixed; see "why #13 is here,
not with #14/#15" below).

- **Files/functions/selectors:** `web/bryggelogg.html` template (`:121-130`
  OG/FG/Volume labels+inputs, `:133-137` judgment `role="group"`, `:150-159`
  the three textareas) plus the label-population call sites in
  `web/js/brygg_page.js`. **Important source correction to the inventory's
  own framing:** these three findings are *not* all in the same render
  branch. `.brygg-og`/`.brygg-volum` are populated in the `fase ===
  "bryggedag"` branch (`brygg_page.js:156-183`); `.brygg-fg` in the `fase
  === "gjaering"` branch (`:184-197`); the three textareas and the
  judgment group are populated in the `fase === "smaking" || "ferdig"`
  branch (`:198-280`), and `.brygg-nestegang`/`.brygg-nesteganglabel`
  specifically are *also* reused in the `fase === "forkastet"` branch
  (`:281-286`). They share a fix **mechanism** (add `id`+`for`, or a plain
  `aria-label` for the group) and a **file**, not a render branch.
- **Acceptance criteria:**
  - OG/FG/Volume (#7): each input gets a stable `id`, each sibling
    `<label>` gets a matching `for` (mirroring the working pattern already
    in `web/verktoy.html:86-91`, finding #17).
  - Textareas (#9): same `id`/`for` pattern; `.brygg-fungerte`/
    `.brygg-endret` additionally lose their "zero accessible name and zero
    placeholder" gap the inventory flags as the weakest case in this group.
  - Judgment group (#13): add `aria-label` (not `aria-labelledby`, see
    next bullet) matching `t("brygg.sporsmalSmaking")`'s content
    ("Ville du brygget dette igjen?" / "Would you brew this again?"), on
    the `role="group"` div at `bryggelogg.html:133-137`. **Correction
    (caught during #144 implementation):** this bullet originally named
    `t("brygg.smakSporsmal")` — that key is the *separate* flavor-match
    question ("Ble ølet omtrent som du forventet?") shown further down the
    same card, not the question the judgment buttons answer. The judgment
    buttons answer the card's general `.brygg-sporsmal` question, which is
    populated with `brygg.sporsmalSmaking` — that is the correct key to
    reuse here.
  - **Cross-cutting acceptance criterion this batch must not skip:** the
    brew log can render **multiple brew cards on the same page
    simultaneously** (one `.brygg-kort` per active brew, from the same
    cloned template) — so `id`s must be **scoped per brew**, e.g.
    `` `brygg-${brew.brewId}-og` ``, not a bare `"brygg-og"` that would
    collide across cards. This is the dominant regression risk for this
    batch and is not stated explicitly anywhere in the inventory itself
    (which audits the template once, not its multi-instance runtime
    behavior). For the judgment group, prefer `aria-label` over
    `aria-labelledby` specifically to sidestep this same multi-card `id`
    problem entirely (a static label string needs no `id` to reference).
- **NO/EN implications:** none beyond existing `t()` keys already used for
  these labels — no new i18n key needed for #7/#9 (the `id`/`for`
  attributes carry no visible/translatable text). #13's `aria-label` reuses
  the existing `brygg.sporsmalSmaking` key (see the correction above — not
  `brygg.smakSporsmal`) already rendered visually elsewhere on the same
  card — no new key.
- **Keyboard/focus cases:** none — no new focus management, just
  programmatic name/association wiring on already-focusable controls.
- **Mobile implications:** none.
- **Screen-reader verification needed vs. source-testable:** the `id`/`for`
  wiring itself is source-testable (present/matching). The inventory's own
  "VERIFY IN BROWSER" item 1 applies here too for pre/post-fix announcement
  confirmation — worth a quick live check, low-stakes for the same reason
  as Batch 1.
- **Static test opportunities:** this batch is the best-fit candidate for
  the inventory's own suggested test ("Tests that could guard the
  contract"): a static check that every `id` referenced by a `for=` in
  `web/bryggelogg.html` actually exists in the same document. Since this
  batch is what *introduces* those `id`/`for` pairs, adding that guard
  test in the same PR (rather than a later one) directly protects the
  fix it just made.
- **Regression risk:** Low–Medium. Low for the mechanism itself (static
  attribute wiring); Medium if the per-card `id`-uniqueness requirement
  above is missed, since a duplicate `id` across two simultaneously
  rendered brew cards is a real, silent multi-card bug this codebase does
  not currently test for anywhere.
- **Dependencies on W5/B07/B08/B09-B11:** OG/FG/Volume (`bryggedag`/
  `gjaering` branches) have **no** overlap with W5. The textareas and
  judgment group (`smaking`/`ferdig` branch) **do** share a render region
  with the exact code W5 discusses (`web/js/brygg_page.js:198-277`,
  including the "Avslutt" button at `:262-269` that W5's own analysis
  flags as settable before a judgment is recorded) — see Batch 3 below for
  the fuller discussion, since the sliders in that same branch are the
  larger overlap. Practical guidance: if a W5 implementation round is
  in flight concurrently, expect this batch's diff on the textarea/
  judgment-group lines to need a straightforward rebase, not a redesign —
  W5's own scope is the completion *state machine*, not the tasting
  fields' markup.
- **Why #13 is grouped here, not with #14/#15 (deviation from the parent
  issue's own candidate list):** the parent issue's suggested grouping
  puts the judgment-group SHOULD FIX item alongside the side-drawer and
  radar SHOULD FIX items (all three are, after all, SHOULD FIX). This plan
  disagrees: #14 (side-drawer focus trap) and #15 (radar per-axis values)
  are each explicitly blocked on an unresolved product/UX decision per the
  inventory's own text (see Batches 8–9), while #13 is a one-line,
  decision-free `aria-label` addition using the exact same mechanical
  fix pattern as #7/#9 in the exact same file family. Bundling a
  ready-to-ship one-liner into an issue that cannot start until someone
  makes two unrelated UX calls would delay it for no technical reason.

**Issue (actual):** #144 — *"WEB FIX — B06 batch 2: brew-log field labels + judgment group"*

---

## Batch 3 — Brew-log tasting sliders

**Status: next pending implementation batch** (Batch 2 is completed — see
above).

**Findings:** #8 (MUST FIX — up to 18 unlabeled `<input type="range">` per
brew, the inventory's own highest-severity single finding).

- **Files/functions/selectors:** `web/js/brygg_page.js`, `_byggSmakSliders()`
  (`:90-113`), called from the `fase === "smaking" || "ferdig"` branch
  (`:224`).
- **Acceptance criteria:** inside the existing `for (const kategori of
  Object.keys(predikert))` loop, assign `input.id` and `label.htmlFor =
  input.id` for every slider, using a **brew-scoped** id, e.g.
  `` `brygg-${brew.brewId}-smak-${kategori}` `` — reusing the same
  per-card-uniqueness convention Batch 2 should already have established
  (see that batch's cross-cutting criterion), so both batches agree on one
  naming scheme rather than inventing two. `container.innerHTML = ""` at
  the top of the function already clears prior nodes on every rebuild, so
  there is no stale-`id` leak risk across re-renders of the same card.
- **NO/EN implications:** none directly from the `id`/`for` fix itself.
  **However**, see the B09 dependency below — the *label text* this exact
  loop builds (`label.textContent = t("brygg.smakKategori", { kategori,
  ... })`, line 98) is the literal site of a separate, already-triaged bug.
- **Keyboard/focus cases:** none new — sliders are already focusable/
  operable; this only adds the missing name.
- **Mobile implications:** none.
- **Screen-reader verification needed vs. source-testable:** the `id`/`for`
  wiring is source-testable. The inventory explicitly lists this as one of
  the controls needing a live NVDA/VoiceOver pass (its "VERIFY IN BROWSER"
  item 1) given the volume of controls (up to 18 per card) — this is the
  batch most worth an actual live screen-reader tab-through, not just a
  spot check, precisely because of that volume.
- **Static test opportunities:** same static `id`/`for` existence check
  suggested for Batch 2 would also cover this batch's generated markup, if
  the test is written to run against a rendered DOM snapshot rather than
  static HTML source (these `id`s only exist after `_byggSmakSliders()`
  runs, unlike Batch 2's template-authored ones) — likely out of reach for
  a pure-source static test given `.claude/rules/testing.md`'s stated "no
  browser/DOM assertions" boundary; flagged here as a real gap rather than
  assumed solvable.
- **Regression risk:** Medium–High — the only MUST FIX batch that
  generates `id`s in a loop (correctness depends on the loop, not just a
  fixed template edit) and the batch with by far the largest number of
  individual controls affected per brew card (up to 18) and per page
  (× number of concurrently rendered cards).
- **Dependencies on W5/B07/B08/B09-B11 — two concrete, source-proven
  points, not a general "same area" caveat:**
  - **B09 (same line):** `web/js/brygg_page.js:98-101` — the exact
    `label.textContent = t("brygg.smakKategori", { kategori, ... })` call
    this batch must touch to add `label.htmlFor` — is also the exact
    reported defect site for B09 ("English brew log shows Norwegian taste
    labels," `docs/development/web_b09_b11_triage.md`): `kategori` is
    passed to `t()` raw instead of through `smaksKategoriVisning(kategori)`
    (`web/js/i18n.js:3773-3776`), so the interpolated category name stays
    Norwegian in the EN UI. Whoever implements this batch will produce a
    diff on the same three lines B09's own future fix would touch. This
    plan does **not** ask this batch to fix B09 (out of this issue's hard
    scope, and B09 has its own separate triage doc) — it flags the
    unavoidable **same-line collision** so the batch's implementer/reviewer
    picks one of two safe paths: (a) implement both fixes together in one
    PR once both are authorized, since they touch the same three lines
    anyway, or (b) implement this batch alone and expect B09's future PR
    to need a small rebase on top, not the reverse. Silently landing both
    independently, unaware of each other, is the one path likely to
    produce an avoidable merge conflict on identical lines.
  - **W5 (same render branch):** the whole `fase === "smaking" ||
    "ferdig"` branch this function is called from (`brygg_page.js:198-280`)
    is the exact region `docs/development/web_w5_brew_completion_preflight.md`
    discusses for its brew-completion state-machine gap (the "Avslutt"
    button at `:262-269` settable before `sensing.judgment` exists). W5's
    own scope is the completion state machine, not this function's
    internals, so there is no functional coupling — but if a W5
    implementation round restructures *when or whether* this branch
    renders (e.g. gating the tasting UI behind an explicit "not yet judged"
    state), this batch's diff inside that same branch will need a rebase.
    Sequencing recommendation: if both are active in the same period,
    land W5 first to avoid this batch rebasing on top of a
    restructured branch; there is no correctness reason to block this
    batch on W5, only a rebase-avoidance one.

**Future issue title:** *"WEB FIX — B06 batch 3: accessible names for brew-log tasting sliders (#8) — note same-line B09 collision, see triage doc"*

---

## Batch 4 — Shared combobox ARIA + dead `aria-labelledby` cleanup

**Findings:** #10 (MUST FIX — incomplete ARIA combobox pattern), #21
(SHOULD FIX — dead `aria-labelledby` markup on the yeast/style mount divs).

- **Files/functions/selectors:** `web/js/combobox.js` (`role="combobox"`
  setup `:26-28`, `role="listbox"` `:34`, `role="option"` `:82`, arrow-key
  `_move()` `:113-118`); `web/index.html` `#gjaer-velger-mount` (`:228-229`)
  and `#stil-velger-mount` (`:203,229` per the inventory) markup cleanup for
  #21; call sites in `web/js/app.js` (`:403-409,663-673,1808-1813,1833-1838`)
  for all four instances (malt, hop, yeast, style).
- **Acceptance criteria:** every `<li role="option">` gets a unique `id`;
  the combobox `<input>` gets `aria-controls` pointing at its own
  `<ul role="listbox">` `id`; `aria-activedescendant` on the input is kept
  in sync with the highlighted option in `_move()` and cleared when the
  list closes/blurs. #21: remove (or leave inert but documented) the
  `aria-labelledby` attributes on the two mount `<div>`s that `app.js`
  currently discards via `.replaceWith()` — no behavior change since the
  `Combobox` constructor's own `aria-label` already covers naming; this is
  a pure dead-markup cleanup riding along in the same PR since it's the
  same subsystem and the same author will already be reading this exact
  code path.
- **NO/EN implications:** none — no new visible/translatable text, only
  ARIA plumbing.
- **Keyboard/focus cases:** this is the one batch that changes actual
  interaction semantics, not just naming — the arrow-key highlight must
  correctly move `aria-activedescendant` in lockstep with the existing
  `.is-active` CSS class it already moves, for **all four** combobox
  instances (malt, hop, yeast, style) and, for malt/hop specifically,
  across an arbitrary number of simultaneously mounted rows.
- **Mobile implications:** none directly (this is a keyboard-interaction
  fix); no touch-target size change.
- **Screen-reader verification needed vs. source-testable:** the
  attribute/ID wiring itself is source-testable; **whether the
  announcement is actually correct as the highlight moves is explicitly
  the inventory's "VERIFY IN BROWSER" item 2** and cannot be confirmed by
  source reading alone — a real NVDA/VoiceOver pass is required before
  this batch can be called done, not optional polish.
- **Static test opportunities:** a static check could assert every
  `Combobox` instantiation site still passes `ariaLabel`/that the shared
  class's constructor still sets the expected attributes — but the actual
  keyboard-highlight-to-`aria-activedescendant` sync can only be verified
  live (it's runtime DOM state, not static markup); flagged as a real
  testing-boundary gap, consistent with `.claude/rules/testing.md`'s "no
  browser/DOM assertions in `tests/`" statement.
- **Regression risk:** **High — the highest of any batch in this plan.**
  `Combobox` is one shared class instantiated by four different pickers,
  two of which (malt, hop) can have an arbitrary, user-controlled number
  of simultaneous instances on one page (one per ingredient row). Every
  generated `id` (for both the `<ul>` and each `<li>`) must be unique
  **across all currently-mounted combobox instances at once**, not just
  within one instance — a naming scheme like a per-instance counter or a
  row-index/ingredient-slot prefix is needed; getting this wrong risks
  breaking keyboard navigation for the entire recipe builder, not one
  isolated control.
- **Dependencies on W5/B07/B08/B09-B11:** none — `combobox.js` is a
  self-contained shared component untouched by any of those four docs.
- **Recommendation:** land this batch in isolation (no other batch bundled
  into the same PR) and give it its own dedicated manual regression pass
  (`web-full-regression` skill) beyond what any other batch here needs,
  given the blast radius above.

**Future issue title:** *"WEB FIX — B06 batch 4: complete ARIA combobox pattern across malt/hop/yeast/style pickers (#10, #21)"*

---

## Batch 5 — Help popover focus handling + initial `aria-expanded`

**Findings:** #11, focus/disclosure half only (MUST FIX — popover never
receives focus on open, focus never restored on close, `aria-expanded`
missing from initial markup).

- **Files/functions/selectors:** `web/js/help.js` (`_apneHjelp`/
  `_lukkHjelp`/`initHjelp`, `:112-193`); trigger buttons across
  `web/index.html` (e.g. `:233,393`) and any other page using the same
  "?" pattern, for the initial `aria-expanded="false"` markup addition.
- **Acceptance criteria:** on open, focus moves into the popover (its
  first focusable element, e.g. the "Les mer →" link, is the simplest
  choice already implied by the inventory's own wording); on close — via
  Escape, outside click, or the popover's own close button, all three
  existing close paths (`help.js:133/139/183-185/189`) — focus returns to
  the triggering "?" button; every trigger button's **initial** markup
  (not just the attribute set/removed at runtime) carries
  `aria-expanded="false"`.
- **NO/EN implications:** none — no new visible text.
- **Keyboard/focus cases:** this is a pure focus-management batch — the
  entire point is the three transitions above (open→popover,
  close-via-any-path→trigger, and the disclosure state being knowable
  before first interaction).
- **Mobile implications:** none directly — this is keyboard/focus
  behavior; the touch-target sizing half of the same finding is
  deliberately a **separate** batch (see Batch 6) since it's pure CSS with
  a different risk/verification profile.
- **Screen-reader verification needed vs. source-testable:** the
  `aria-expanded` initial-markup addition is source-testable. The focus
  transitions require a live check — inventory's own "VERIFY IN BROWSER"
  item 2 groups this with the combobox fix as needing a real NVDA/
  VoiceOver pass once implemented, not just an attribute-presence check.
- **Static test opportunities:** a static check could assert every "?"
  trigger button carries `aria-expanded` in its authored HTML (cheap grep)
  — does not prove the focus-transition behavior itself.
- **Regression risk:** Medium — the fix is likely a small, single change
  inside the shared `_apneHjelp`/`_lukkHjelp` functions (low multiplicity
  risk, since there's one implementation, not one per trigger), but the
  **verification surface** is broad: many trigger instances across
  multiple pages (every malt/hop unit span, yeast attenuation label, etc.)
  should each get at least a spot-check, not just the shared function
  reviewed in isolation.
- **Dependencies on W5/B07/B08/B09-B11:** none — `help.js` is untouched by
  any of those four docs.

**Future issue title:** *"WEB FIX — B06 batch 5: help-popover focus management and initial aria-expanded (#11 focus half)"*

---

## Batch 6 — Touch-target sizing

**Findings:** #11, size half only (SHOULD FIX, pending the inline-exception
judgment call), #20 (folded into #11 per the inventory itself — no
additional touch/swipe-only affordances found elsewhere).

- **Files/functions/selectors:** `web/css/style.css` — `.hjelp-knapp`
  (`:1777-1792`, fixed `width:1.3rem; height:1.3rem; padding:0`, ~20.8px),
  `.hjelp-knapp-liten` (`:1800-1804`, overrides to `width:1.05rem;
  height:1.05rem`, ~16.8px).
- **Acceptance criteria:** both classes reach a minimum 24×24 CSS-pixel hit
  target, without changing the visible glyph size — the inventory's own
  suggested acceptance criterion #6.
  **Corrected mechanism (Chief review, PR #136 round 1):** `web/css/style.css`
  sets `* { box-sizing: border-box; }` globally (`:56`), and both classes
  currently fix `width`/`height` directly with `padding:0`. Under
  `border-box`, adding padding *inside* an unchanged fixed width/height does
  **not** enlarge the outer box — the padding eats into the existing box
  instead of growing it, so "padding alone" is not a workable mechanism here
  and must not be recommended. The fix must instead increase the outer box
  itself, e.g. raising `.hjelp-knapp`'s `width`/`height` to `24px`
  (`1.3rem` ≈ 20.8px at the default 16px root, so this is a real increase,
  not a rounding no-op) and `.hjelp-knapp-liten`'s override to at least
  `24px` as well (its current `1.05rem` override is *smaller* than the
  base class, not larger), or applying `min-width:24px; min-height:24px`
  as an addition alongside the existing fixed values — either way, the
  glyph itself (`font-size`) stays unchanged; only the clickable box grows.
  Which of these two mechanisms (raise `width`/`height` directly vs. add
  `min-width`/`min-height`) is preferable is an implementation-time choice,
  not decided by this plan.
  **Recommendation on the open judgment call:** the inventory flags that
  WCAG 2.5.8's "inline" exception may technically apply here since every
  `.hjelp-knapp` sits inline within label text — rather than spending
  further analysis effort proving or disproving that exception, this plan
  recommends simply applying the hit-area fix regardless, since fixing it
  is cheap and removes the ambiguity outright rather than leaving a WCAG
  citation that depends on a case-by-case rendered-layout judgment; that
  recommendation itself is unaffected by the mechanism correction above.
- **NO/EN implications:** none — pure CSS, no text change.
- **Keyboard/focus cases:** none.
- **Mobile implications:** this batch **is** the mobile-relevant fix — real
  fat-finger tap success on a phone is exactly what's being addressed;
  the inventory's own "VERIFY IN BROWSER" item 5 (real-device tap success)
  still applies since CSS box size alone doesn't guarantee effective hit
  area on every device/browser combination.
- **Screen-reader verification needed vs. source-testable:** the *rule
  values* are source-testable (checking the CSS declares ≥24px one way or
  another needs no browser), but — unlike this plan's earlier draft —
  **do not claim "no layout risk" or "no visual change" categorically**:
  enlarging the outer box of an inline-flex button can shift inline
  spacing/alignment against adjacent label text, so a rendered
  desktop-and-mobile visual check is required before this batch can be
  considered done, not merely optional polish. That check can reasonably be
  folded into the existing `web-full-regression` sweep rather than needing
  a dedicated round, but it is not skippable.
- **Static test opportunities:** a static test could assert the CSS
  declares a ≥24px box (via `width`/`height` or `min-width`/`min-height`)
  for both classes, but this is CSS-in-a-stylesheet, not markup — a plain
  value-presence grep is possible but low-value versus just eyeballing the
  two rules in review; not recommended as a dedicated new test given how
  small and stable this surface is.
- **Regression risk:** Low, but not zero as previously stated — two CSS
  rules, with a real (if small) risk of inline-alignment shift now that the
  outer box genuinely grows; needs a before/after screenshot comparison on
  both desktop and mobile viewports rather than being assumed purely
  cosmetic-safe.
- **Dependencies on W5/B07/B08/B09-B11:** none.

**Future issue title:** *"WEB FIX — B06 batch 6: 24×24px minimum touch target for help buttons (#11 size half, #20)"*

---

## Batch 7 — First-visit Learner/Master dialog focus handling

**Findings:** #12 (MUST FIX — no focus management on the first-visit mode
dialog).

- **Files/functions/selectors:** `web/index.html` `#modus-forstegang`
  (`:92-105`); `web/js/app.js` `initModus` (`:355-381`), specifically
  wherever `_lukkModusForstegang` is defined/called.
- **Acceptance criteria:** on open, focus moves to the first mode button
  inside the dialog; a dedicated `Escape` key handler is added (currently
  only backdrop-click closes it); **and** an explicit product decision is
  made between (a) adding a real focus trap to justify the existing
  `aria-modal="true"`, or (b) dropping `aria-modal="true"` if a lighter,
  non-trapping treatment is intentionally preferred — the inventory
  explicitly declines to choose between these itself and calls it a
  product decision, and this plan does not resolve it either; it is
  listed here as a **precondition for this batch's acceptance criteria to
  be final**, not an implementation detail to improvise past.
- **Reference pattern already in this codebase:** `web/js/app.js:1095-1103`
  and `:1130` (the equipment modal) already has both an `Escape` listener
  and an explicit `.focus()` call on open — cited by the inventory itself
  as the proof this is a known, minimal-diff pattern in the same file, not
  a new one to invent.
- **NO/EN implications:** none — no new visible text, one dialog markup
  shared by both locales.
- **Keyboard/focus cases:** this batch is entirely about keyboard/focus —
  focus-on-open, Escape-to-close, and (pending the product decision above)
  a focus trap.
- **Mobile implications:** none beyond what already applies to the
  existing dialog.
- **Screen-reader verification needed vs. source-testable:** focus-on-open
  and Escape-handling are behaviorally verifiable live but structurally
  simple (mirrors the equipment-modal pattern, which already works); the
  inventory's own "VERIFY IN BROWSER" item 4 (whether background content
  is actually reachable despite `aria-modal="true"`) requires a live
  screen-reader check regardless of which side of the product decision is
  chosen.
- **Static test opportunities:** none meaningful beyond checking the
  Escape listener/`.focus()` call exist in source — the actual
  reachability of background content needs a live check per the item
  above.
- **Regression risk:** Low — this is a singular, first-visit-only dialog
  with no repeated/looped instances (unlike Batches 3/4), and a proven
  same-file reference implementation to copy.
- **Dependencies on W5/B07/B08/B09-B11:** none.

**Future issue title:** *"WEB FIX — B06 batch 7: focus management for first-visit Learner/Master dialog (#12) — needs a product decision on focus-trap vs. dropping aria-modal first"*

---

## Batch 8 — Side-drawer focus trap

**Findings:** #14 (SHOULD FIX — no focus trap in `#sidemeny`).

- **Files/functions/selectors:** `web/js/chrome.js`, `initSidemeny`
  (`:29-77`).
- **Acceptance criteria:** **not yet fully specifiable** — the inventory
  itself is explicit that this drawer already has *correct* focus-on-open
  (`:51`) and focus-restore-on-close (`:60`) plus a global Escape handler
  (`:73-75`); the only gap is the absence of a trap, and the inventory
  explicitly frames whether a trap is even worth the added complexity
  "for a drawer that isn't strictly modal" as an open question pending a
  live Tab-key walkthrough (its own "VERIFY IN BROWSER" item 3). This plan
  does not resolve that question — it is listed as a precondition:
  **do not open this as an implementation issue until that walkthrough has
  happened and a yes/no answer to "does Tab actually leak to background
  content in a way that matters" exists.**
- **NO/EN implications:** none anticipated.
- **Keyboard/focus cases:** entirely about whether `Tab`/`Shift+Tab` from
  the drawer's first/last focusable item should wrap back into the drawer
  instead of reaching the backdrop-covered page behind it.
- **Mobile implications:** the drawer is presumably a mobile-relevant
  pattern (side menu); no specific mobile-only gap beyond the general
  focus-trap question.
- **Screen-reader verification needed vs. source-testable:** live-only —
  this is precisely the kind of tab-order behavior that cannot be proven
  or refuted from source, per the inventory's own classification.
- **Static test opportunities:** none — this is runtime focus-order
  behavior.
- **Regression risk:** Low *if and only if* implemented — a focus trap
  touches an already-working focus-management implementation, so the risk
  is regressing the parts that already work (focus-on-open, focus-restore)
  while adding the trap, not introducing a wholly new hazard.
- **Dependencies on W5/B07/B08/B09-B11:** none.

**Future issue title:** *"WEB PREP — live Tab-walkthrough of #sidemeny to decide whether a focus trap is warranted (#14)"* (a **prep/decision** issue, not yet an implementation one — see acceptance criteria above).

---

## Batch 9 — Radar chart per-axis values

**Findings:** #15 (SHOULD FIX — 18-axis flavor radar exposes only one
whole-chart `aria-label`, no per-axis values to assistive tech).

- **Files/functions/selectors:** `web/js/radar.js` (`:53-57` chart-level
  `aria-label`; `:77-93` the SVG `<text>` labels that currently carry
  values only visually).
- **Acceptance criteria:** **not yet fully specifiable** — the inventory
  explicitly recommends "a product decision, not an assumed fix," since
  whether this matters depends on whether the chart is read as a
  decorative sensory summary or something a user needs exact numbers from.
  This plan does not make that call. Two candidate directions **if and
  when** the product decision favors adding one: (a) an `aria-describedby`
  pointing at a visually-hidden text summary listing all 18 category:value
  pairs, or (b) an adjacent accessible data table mirroring the chart —
  the inventory does not commit to either, and neither should this plan.
- **NO/EN implications:** if implemented, any new summary text needs both
  NO and EN i18n keys, following the same category-naming mechanism this
  document's Batch 3 already flags as being mid-fix via B09
  (`smaksKategoriVisning`) — worth checking B09's resolution before writing
  new category-name strings here, so the two don't diverge on how a
  category name is localized.
- **Keyboard/focus cases:** none anticipated — this is a
  non-interactive `<svg>`, not a focusable control.
- **Mobile implications:** none anticipated.
- **Screen-reader verification needed vs. source-testable:** live-only —
  the inventory's own "VERIFY IN BROWSER" item 6 asks what, if anything,
  is currently announced; that answer likely informs which of the two
  candidate directions above is actually worth building.
- **Static test opportunities:** none until a concrete design exists.
- **Regression risk:** Low technically (additive-only change to a
  rendering function), but genuinely **unscoped** until the product
  decision lands — do not estimate this batch's size before that decision
  exists.
- **Dependencies on W5/B07/B08/B09-B11:** soft dependency on B09 (see
  NO/EN implications above) if and only if this batch's eventual design
  needs to render per-axis category names as text.

**Future issue title:** *"WEB PREP — product decision: should the flavor radar expose per-axis values to assistive tech, and how (#15)"* (a **prep/decision** issue, not yet an implementation one).

---

## What should NOT be combined

- **Batch 3 (sliders) must not be merged into Batch 2**, despite living in
  the same file and even the same render branch as this batch's textareas/
  judgment-group items, because it is the only batch that generates `id`s
  in a loop rather than editing static template markup, and it carries the
  two named cross-issue coordination points (B09 same-line collision, W5
  same-branch overlap) that the rest of Batch 2 does not share. Bundling
  them would force the lower-risk static edits in Batch 2 to wait on the
  higher-risk, coordination-dependent slider fix.
- **Batch 4 (combobox) must not be bundled with anything else.** It is the
  single highest-regression-risk batch in this plan (a shared component
  with an arbitrary, user-controlled instance count on the malt/hop rows)
  and deserves its own isolated PR and its own dedicated manual regression
  pass, not a shared blast radius with an unrelated fix.
- **Batch 5 (help focus) and Batch 6 (touch-target sizing) must not be
  merged**, even though both fix parts of the same inventory finding
  (#11) in the same general subsystem, because they have fundamentally
  different risk profiles and verification methods: Batch 5 is JS
  behavioral change needing a live focus/keyboard walkthrough; Batch 6 is
  pure CSS, verified by a rendered screenshot check rather than a
  keyboard/focus walkthrough. Merging them would force a small,
  low-risk CSS fix to wait on a behavioral fix's full verification cycle.
- **Batches 8 and 9 must not be combined with each other or with anything
  else**, and must not be opened as *implementation* issues at all yet —
  both are explicitly blocked on a product/UX decision the inventory
  itself declines to make, and each decision is independent of the other
  (a Tab-walkthrough verdict for the drawer says nothing about whether the
  radar needs per-axis text). Treat each as its own **prep/decision**
  issue first; only draft an implementation issue once that decision
  exists.
- **#13 must not be combined with #14/#15** (see Batch 2's "why #13 is
  grouped here" note) even though all three are SHOULD FIX findings — #13
  has no open decision blocking it and should not share an issue with two
  items that do.

---

## Explicitly out of scope for this issue (per its own hard-scope list)

No `web/**` product file, i18n string, or ARIA attribute was edited to
produce this batching plan. No accessibility fix was implemented. No
deploy occurred. W5 was not started. `#116`/`#98`/`#100`, App/Core/
Bryggeskole, the roadmap, and `raw_data/unmatched_malt.json` were not
touched. The nine batches above, and the two prep/decision issues nested
inside Batches 8–9, are proposals for **future** bounded issues — none of
them is opened by this document.
