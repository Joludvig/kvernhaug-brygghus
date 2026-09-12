# App A4 — Workflow Polish Source Audit (issue #239)

Status: **DECISION preflight, source audit only — no product code changed.**
Governing: Roadmap V2.1 #101 Phase 2 "App Brewday Stabilization V1", item A4.
Risk class: DECISION (Production Workflow V2 #199) — several legitimate
implementation choices exist per finding; this document narrows them but
does not choose silently on the owner's behalf where a real choice remains.

A1 (issue #170), A2, and A3 (issue #237, preflight in
`docs/development/app_a3_state_orientation_preflight.md`, PR #238) are
completed on master and are **not** reopened here except where this
audit's own required trace (A4-3, "sidebar recipe selector population")
surfaced a real interaction this document is obligated to report (Section
8, Finding F0).

---

## 1. Scope / governing roadmap

Roadmap #101 Phase 2, item A4, exactly four bullets (issue #239 body,
verified against the live GitHub issue and against #101 directly):

1. preserve batch/brewer metadata if presented as start-brew fields;
2. move/shortcut first equipment confirmation earlier;
3. refresh recipe selector immediately after save;
4. reduce unnecessary internal terminology without removing power-user
   depth.

This document is the bounded DECISION/preflight step. It does not
implement, does not redo A1–A3, does not touch Web/Bryggeskole/Brew
Lab/Sóti, does not open Phase 3, and does not touch parked #97/#98/#99/
#100 or owner-local data (`raw_data/unmatched_malt.json` untouched, see
Section 16).

## 2. Current master/source baseline

- Branch: `docs/app-a4-workflow-polish`, created from `origin/master` at
  `a6cb5757c2a698391f48d9e43cd5ca79e1bd95de` (confirmed via `git fetch
  origin` + `git rev-parse origin/master`, matching the SHA issue #239
  itself records at creation).
- That commit is `a6cb575` = "Merge pull request #238 from
  Joludvig/app/a3-state-orientation" — i.e. A3 (fix `4da5bba`,
  `fix(app): clarify A3 brew state orientation (#237)`) is the last
  App-relevant change on master before this audit.
- All findings below are traced against this exact commit, using direct
  source reading (`Read`/`Grep`) and, where a claim needed empirical
  proof rather than static reading, short-lived, read-only
  `streamlit.testing.v1.AppTest` probe scripts run against isolated
  temp directories (`KVERNHAUG_RECIPES_DIR`/`KVERNHAUG_EQUIPMENT_FILE`),
  never against real user data, and deleted after use. No product file
  was modified to produce this evidence.

## 3. A4-1 — batch/brewer metadata — current contract

**Traced:** `ui/kbhbrew_panel.py::render_kbhbrew_create_panel()` (the
"▶️ Start nytt brygg" button, lines 115–191),
`modules/kbhbrew_storage.py::opprett_og_lagre_ny_brew()` (lines
177–203), `modules/kbhbrew.py::bygg_ny_brew()`/`bygg_ny_brew_snapshot()`
(lines 308–382, the full Core V1 `.kbhbrew` field list).

**Finding: the premise does not currently hold.** "Start nytt brygg" is
a single bare button with **no input fields at all** before the click —
no batch number, no brewer name, nothing. The function signature of
`opprett_og_lagre_ny_brew()` and `bygg_ny_brew()` confirms this: no
`batch`/`brewer` parameter exists anywhere in the call chain. The
resulting `.kbhbrew` object's own field set (`brewId`, `originBrewId`,
`parentBrewId`, `recipeId`, `status`, `createdAt`, `brewedAt`,
`snapshot`, `actuals`, `sensing`, `learning`) has no batch-number or
brewer-name field either — confirmed via `grep -n "brewer\|batch"` on
`modules/kbhbrew.py` (zero hits).

The one adjacent, genuinely existing field is `brygger_stil` — a
free-text **style tag** shown on the recipe card ("Bryggerstil (vises
på kortet...)", `ui/recipe_card.py:121-125`, placeholder example
"Imperial Nordisk Røykstaut"). This is a recipe-level field, not a
start-brew field, and it is **already correctly preserved**: it flows
through `modules/recipe_context.py` → `modules/kbh_contract.py`
(`brygger_stil` → `bryggerStil`) → `recipe_to_kbhrecipe_payload()` →
frozen into every new `.kbhbrew` snapshot's `recipe` payload
unconditionally. Nothing here is discarded. This is NOT "brewer
metadata" in the roadmap's likely sense (a person's name or a batch
identifier) and does not satisfy A4-1 by itself.

**Conclusion:** there is currently nothing to "preserve" for A4-1,
because no batch-number/brewer-name capture point exists in the App at
start-brew time. The roadmap bullet's own "if presented" condition is
false on current master.

**`CORE/SCHEMA DECISION REQUIRED`** — if the product actually wants a
human-meaningful batch label and/or brewer name captured at start-brew
time (distinct from the opaque `brewId` UUID and from the unrelated
`brygger_stil` style tag), that is a **new** `.kbhbrew` Core field (most
likely on the mutable `learning`/top-level layer, since it is
brew-specific operator metadata, not part of the frozen recipe
`snapshot`) and/or a new session field feeding it. This audit does not
choose that field name, layer, or whether it is even wanted — it only
establishes that no such capability exists today and that adding it is
a Core contract decision, not a wording/UI fix.

**Classification: `DECISION`** (only if the product actually wants this
capability — see Section 15) — otherwise **`ALREADY CORRECT` /
`OUT OF A4`** if the roadmap bullet is considered satisfied by
confirming nothing is currently lost.

## 4. A4-2 — first equipment confirmation — current contract

**Traced:** `app.py` tab layout (lines 125–195),
`ui/equipment_panel.py::render_equipment_panel()` (full file, 92
lines), `modules/equipment.py` (full file — `DEFAULTS`,
`last_equipment()`, `equipment_kilde_er_lagret()`, `lagre_equipment()`),
`ui/kbhbrew_panel.py:150-156` (the gate on "Start nytt brygg").

**Current flow:** Equipment confirmation lives exclusively in
`render_equipment_panel()`, called once, from `tab_verktoy` (the 4th/
last tab, `app.py:195`), inside a collapsed `st.expander("⚙️
Utstyrsprofil")`. `render_kbhbrew_create_panel()` (called from
`ui/brewday_panel.py:103`, inside `tab_bryggdag`, the 3rd tab) gates
brew creation on `equipment_kilde_er_lagret()` — a deliberate,
Chief-reviewed guard (PR #30 blocker 3: an unconfirmed default profile
must never be silently frozen into a `.kbhbrew` as if it were the
user's real equipment). If unconfirmed, the user gets only a text error
(`ui/kbhbrew_panel.py:151-156`) telling them to go to "🔧 Verktøy" →
"⚙️ Utstyrsprofil" and click "💾 Lagre utstyrsprofil" — no link, no
inline shortcut. This is real, source-proven friction: a first-time
user's natural first action (Bryggdag tab → Start nytt brygg) dead-ends
with a message pointing at a different, not-yet-visited tab and a
collapsed expander.

**Why a naive fix doesn't work:** `render_equipment_panel()` uses fixed
widget keys (`eq_efficiency`, `eq_boil_off`, `eq_mash_ratio`,
`eq_grain_abs`, `eq_dead_space`, `eq_kettle_cap`, `eq_boil_time`,
`eq_save_btn`). `app.py` renders **all** tab bodies on every run
regardless of which tab is active (confirmed comment at `app.py:133`
and by design elsewhere in this codebase). Calling
`render_equipment_panel()` a second time from inside `tab_bryggdag`
would render the same widget keys twice in the same script run →
Streamlit `DuplicateWidgetID`. So "just call the same function again"
is not the smallest fix; it would require either lifting the whole form
into a shared, key-parameterized helper (real work, not a shortcut), or
moving the panel back to `tab_bryggdag` (undoing a previous, deliberate
"Brewday Tab UX Cleanup V1" decision documented at `app.py:190-194` to
reduce planning/config noise in the Bryggdag tab — a DECISION-level
reversal, not a FAST fix).

**Smallest useful improvement (source-supported):** the defaults shown
in `render_equipment_panel()`'s own caption ("Standardverdier er
BrewZilla 35L Gen 4.1") are already loaded by `last_equipment()`
whenever nothing is saved yet (`modules/equipment.py:33-40`, falls back
to `DEFAULTS`). The gate only checks whether *any* file was ever
explicitly saved (`equipment_kilde_er_lagret()`), not whether the
current values differ from the shown defaults. A single new button in
the existing error branch — "confirm these defaults now" — that calls
the already-existing `lagre_equipment(last_equipment())` directly would
let a first-time user clear the gate in one click, from where they
already are, without a second equipment system, without duplicating
any widget key, and without touching the existing full-form panel or
its Verktøy-tab placement at all.

**Classification: `FAST`** for the one-click "confirm defaults and
retry" button (small, bounded, single existing function call, no new
storage/ownership). Any bigger navigational change (moving the whole
panel, adding tab-switch machinery) is **`DECISION`**, not needed to
satisfy "smallest useful improvement."

## 5. A4-3 — recipe selector refresh — current contract

**Traced:** `ui/sidebar.py` (selector build/reload logic, lines 40–115,
and the text-import section, lines 140–219), `ui/recipe_card.py`
(save/rename/save-as-copy, lines 114–220), `modules/recipe_importer.py`
(`apply_import_to_session_state`), `modules/kbh_import_apply.py`
(`apply_kbhrecipe_import_to_session_state`). Verified with three
isolated, read-only `AppTest` probes against `app.py` (temp recipe
dirs, deleted after use) covering: unchanged-name save, rename+save,
and text-import-over-a-loaded-recipe.

**The options list is never stale.** `hent_alle_oppskrifter()` is
called fresh at the top of every `render_sidebar()` execution
(`ui/sidebar.py:48`) — there is no caching layer. Any rerun (including
A3-4's own `st.rerun()` after an identity-changing rename) always shows
the current on-disk recipe set. "Selector refresh" is therefore never a
*list-population* problem on current master.

**It is a *selected-value* problem, and it is real:**

- **Unchanged-name save (`lagre_endringer_btn`, name not changed):**
  correct. Probed: selector value stays exactly the saved recipe name,
  matching the one surviving option. No stale/orphaned state. **Already
  correct.**
- **Rename + save (`lagre_endringer_btn`, name changed):** A3-4 already
  makes `_last_loaded_recipe`/`_last_loaded_recipe_file` update
  immediately and triggers `st.rerun()`. But the `sidebar_recipe_selector`
  **widget's own bound value is never explicitly updated** — it still
  holds the *old* name string. On the immediate rerun, the old name no
  longer exists in the freshly-rebuilt options list (the old dict key is
  gone, replaced by the new name), so Streamlit's selectbox falls back
  to the placeholder index. Probed and confirmed: after a rename+save,
  `sidebar_recipe_selector` reads `"__ingen_oppskrift_valgt__"`
  ("-- Velg oppskrift --") even though `gjeldende_navn` and
  `_last_loaded_recipe_file` correctly show the *new* name/file. The
  sidebar visibly claims "no recipe selected" while the editor is
  actively showing (and has just saved) one. This is exactly the class
  of orientation problem A1/A3 were about, just on a control A3 never
  touched.
- **Save as new copy (`lagre_ny_kopi_btn`):** does not touch
  `_last_loaded_recipe`/`_last_loaded_recipe_file`/the selector at all
  (`ui/recipe_card.py:194-205`) — by design, the user keeps editing the
  *original*. The new copy appears in the selector's option list on the
  next render (list is always fresh) but is never auto-selected. This
  is self-consistent (no orphaning), but it is a genuine, unresolved
  product question the roadmap itself raises ("should save-as-copy
  select the new copy?") — not a bug, a **choice**.
- **Real text-paste import over an already-loaded recipe — most severe
  finding of this audit (F0, see Section 8).** Probed on full `app.py`
  with a recipe previously loaded via the real sidebar selector: after
  a successful "✅ Importer oppskrift" click, the imported ingredients
  are visibly applied for one instant and then **silently reverted**
  back to the previously-loaded recipe's data (`valgt_malt` ends the
  interaction as `weyermann_pilsner`, the ORIGINAL saved recipe's malt,
  not the imported "Bohemian Pilsner Floor" ingredient) — with no error
  shown. Root cause traced precisely: `apply_import_to_session_state()`
  pops `_last_loaded_recipe`/`_last_loaded_recipe_file` (A3-1's fix,
  correct in isolation) and the import button handler then calls
  `st.rerun()` (`ui/sidebar.py:219`, pre-existing, not part of A3). On
  that rerun, `render_sidebar()` runs again from the top: the
  `sidebar_recipe_selector` widget's own bound value is still the old
  recipe name (untouched by the pop), so the sidebar's own
  reload-on-mismatch check (`ui/sidebar.py:68-69`:
  `valgt_lagret_navn != st.session_state.get("_last_loaded_recipe")`)
  now reads `"<old name>" != None` → **true** → it reloads the old
  recipe from disk, overwriting the just-imported content. The exact
  same mechanism (`st.rerun()` in the confirm handler,
  `apply_kbhrecipe_import_to_session_state()` clearing identity the
  same way, `ui/sidebar.py:315`) is used by the pre-existing
  `.kbhrecipe` file-import path; it was not independently re-confirmed
  to reproduce this run (the constructed test payload did not pass the
  contract validator in the time available for this audit — see
  Section 14), but the mechanism is identical and this should be
  treated as *likely shared*, not assumed absent.
  **Why untested:** both existing regression suites for these import
  paths (`tests/test_app_a3_state_orientation_apptest.py`'s
  `_IMPORT_HARNESS`, `tests/test_kbh_import_ui_apptest.py`'s sidebar-
  only harness) set `_last_loaded_recipe`/`_last_loaded_recipe_file`
  directly via `session_state[...] =`, bypassing the real
  `sidebar_recipe_selector` widget entirely — neither suite exercises a
  genuinely-selected recipe through the real selector before importing,
  so neither could have caught this. It is not a new regression from
  A3-1 specifically (the `.kbhrecipe` path has had the identical
  `st.rerun()` + identity-clear shape since PRI 2C3, well before A3);
  it is a pre-existing sidebar-selector defect that A3-1 faithfully
  inherited by correctly mirroring the established pattern, as
  instructed.
- **"New recipe":** the App has **no dedicated "new recipe" affordance**
  at all (confirmed: no button/flow found matching this in
  `ui/sidebar.py`, `app.py`, or `ui/recipe_card.py`; this exists only on
  Web, out of scope). Selecting the sidebar placeholder is a no-op by
  design (`ui/sidebar.py:68`, the reload condition excludes
  `_INGEN_OPPSKRIFT_VALGT`) — it deliberately does not clear the
  in-progress draft. **Not applicable to this repo; no finding.**

**Classification:**
- Rename+save selector-value orphaning: **`FAST`** — the smallest fix
  is to explicitly set
  `st.session_state["sidebar_recipe_selector"] = <new name>` alongside
  the existing identity update in `ui/recipe_card.py`'s
  `lagre_endringer_btn` handler, before the existing `st.rerun()`. Small,
  bounded, single existing control, no ownership change.
  Note: this is genuinely on the *App* side of the codebase this audit
  is scoped to, but the responsible line lives inside the same handler
  A3-4 just touched (`ui/recipe_card.py:164-189`) — flag for Chief to
  decide whether it rides with the eventual A4-3 FAST PR or is folded
  back as a small A3 follow-up, since it is really "finish what A3-4
  started," not new A4 scope.
- F0 (import-over-loaded-recipe silent revert): **`OUT OF A4`** by strict
  roadmap-bullet mapping (it is not one of the four bullets), but
  **high severity** (silent data loss, not cosmetic) and directly
  surfaced by the A4-3 trace this issue required. Recommend it become
  its own immediate, separate `FAST` issue — see Section 15.
- Save-as-copy selection semantics: **`DECISION`** (legitimate choice
  either way; not a defect).

## 6. A4-4 — terminology inventory

Scope: only the create/import/export Brewday-adjacent surface
(`ui/kbhbrew_panel.py`), which is the one place jargon actually leaks
to users — checked and ruled out elsewhere (Section 7).

### Keep (legitimate brewing/power-user terms — unchanged)
OG/FG/ABV/IBU/EBC, mash ratio, boil-off, attenuation, efficiency
("Brygghuseffektivitet"), dead space/kettle capacity (equipment
vocabulary a power user needs), `.kbhbrew`/`.kbhrecipe` as literal file
extensions the user actually sees on disk/in a file picker.

### Candidate simplification

| # | Current NO text | Current EN | Surface / file / key | Why it's implementation jargon | Smallest replacement | i18n key |
|---|---|---|---|---|---|---|
| 1 | "🍺 Start nytt brygg (**lagre historisk snapshot**)" | none (hardcoded NO only) | `ui/kbhbrew_panel.py:139`, `st.markdown` | "Snapshot" is a software-engineering metaphor for frozen state, not a brewing term; a brewer needs to know this *records today's brew*, not the storage mechanism | "🍺 Start nytt brygg (fryser dagens oppskrift og utstyr)" | new `kbhbrew.start_ny_brew_tittel` |
| 2 | "Fryser gjeldende oppskrift, utstyrsprofil og spådde verdier som ET NYTT, historisk **Core V1**-brygg (`.kbhbrew`). ... påvirker ALDRI dette **snapshotet** igjen." | none | `ui/kbhbrew_panel.py:140-144`, `st.caption` | "Core V1" is an internal architecture/versioning label with zero brewing meaning; "snapshotet" repeats #1's issue | "Fryser gjeldende oppskrift, utstyrsprofil og spådde verdier som et NYTT, historisk brygg. Senere endringer i oppskrift/utstyr/masterdata påvirker ALDRI dette brygget igjen." | new `kbhbrew.start_ny_brew_beskrivelse` |
| 3 | "...ville blitt hoppet stille over i **snapshotet**" | none | `ui/kbhbrew_panel.py:158-161`, `st.error` | same "snapshot" issue, in an error message a confused first-time user is most likely to actually read | "...ville blitt hoppet stille over i det lagrede brygget" | new `kbhbrew.manglende_ingrediens_feil` |
| 4 | Toast: "Nytt brygg startet: `{brew['brewId']}`" | none | `ui/kbhbrew_panel.py:174` | raw UUID-shaped internal id (`brew-<uuid4>`) has no brewing meaning; nothing a user can act on | "Nytt brygg startet: {oppskriftsnavn}" (use the recipe name already in `ctx`/`brew["snapshot"]["recipe"]["navn"]`, not the id) | new `kbhbrew.nytt_brygg_toast` |
| 5 | "🎯 Bryggdag skriver til: `` `{brew_id}` `` · opprettet {opprettet}" | "🎯 Brewday writes to: `` `{brew_id}` `` · created {opprettet}" | `modules/i18n.py:88,157`, key `kbhbrew.skriver_til` (added by A3-2, PR #238) | same raw-id issue as #4, now freshly introduced; a brewer orients by recipe name + date, not an internal id | swap `{brew_id}` for the brew's own recipe name (already available as `aktiv_brew["snapshot"]["recipe"]["navn"]` at the call site) | same key, value change only |
| 6 | "📦 Importer `.kbhbrew`-fil" caption: "Åpne en `.kbhbrew`-fil (**Core V1** — et historisk brygg, IKKE en oppskrift)." | none | `ui/kbhbrew_panel.py:206-211` | "Core V1" jargon again; the useful part of the sentence ("historisk brygg, ikke en oppskrift") already carries the meaning without it | "Åpne en `.kbhbrew`-fil (et historisk brygg, IKKE en oppskrift)." | new `kbhbrew.import_beskrivelse` |
| 7 | "✅ Importert som nytt lokalt brygg: `` `{resultat['brewId']}` ``" | none | `ui/kbhbrew_panel.py:272` | same raw-id issue as #4/#5 | use the imported brew's recipe name instead of its id | new `kbhbrew.import_bekreftet` |
| 8 | "Ingen **Core V1**-brygg lagret lokalt ennå." | none | `ui/kbhbrew_panel.py:295` | "Core V1" jargon in an empty-state message | "Ingen brygg lagret lokalt ennå." | new `kbhbrew.export_tomt` |

All eight are wording-only; none change what data exists or how it is
stored. Items 4/5/7 additionally require picking the display source
(recipe name from the already-frozen snapshot) — no new field, purely
reading an already-present value instead of an already-present id.

**Scope note, not itself a finding:** this whole section of
`ui/kbhbrew_panel.py` currently has **no English strings at all** (it
never went through the app-wide i18n pass the rest of the App has —
contrast with `ui/kbhbrew_history_panel.py`, which is fully `t()`-based
NO/EN). Translating all of it is a larger, separate lift than "the
smallest wording change" this section is scoped to; recommending it be
tracked separately rather than folded silently into the A4-4 wording
fix (see Section 12).

## 7. Already-correct behavior — DO NOT TOUCH

- `hent_alle_oppskrifter()` is read fresh every render — the selector's
  option list is never a caching problem (Section 5).
- Unchanged-name "Lagre endringer" already keeps the selector correctly
  pointed at the right recipe (Section 5).
- `brygger_stil` (the recipe-level style tag) is already correctly
  captured and frozen into every new `.kbhbrew` snapshot — not lost,
  not "brewer metadata" that needs preserving (Section 3).
- `equipment_kilde_er_lagret()`'s hard confirmation gate itself
  (refusing to freeze an unconfirmed default profile) is correct and
  Chief-reviewed (PR #30) — A4-2's fix must not weaken or bypass it,
  only add a faster confirm path (Section 4).
- `ui/kbhbrew_history_panel.py` already fully uses `t()`-based NO/EN
  i18n, and already translates the Core V1 internal layer names
  (`actuals`/`sensing`/`learning`) into brewer-facing labels ("Målte
  verdier (faktisk)" / "Sensorikk/smaksinntrykk" / "Læring/refleksjon",
  `modules/i18n.py:90,105,112` + EN at `159,174,181`) instead of
  showing the raw layer names. Same for both the History-panel brew
  picker and the export panel's brew picker — both use
  `format_func=lambda bid: etiketter[bid]` friendly labels, never a raw
  `brewId`, in the selection control itself (only the confirmation
  messages flagged in Section 6 leak the raw id).
- Save-as-new-copy's non-selection of the new copy is a coherent,
  deliberate-looking choice, not a bug (Section 5).
- The App has no "new recipe" affordance and none is implied to be
  missing by current source — out of scope, not a finding (Section 5).

## 8. Source-proven friction/trust findings ranked by severity

1. **F0 — HIGH, `OUT OF A4` (see Section 15 for recommended handling).**
   Pasting/importing over an already-selector-loaded recipe silently
   reverts to the old recipe's content after the import's own
   `st.rerun()`, with no error shown. Actual data loss risk (a user
   could paste a new recipe, see it apply, then have it silently
   replaced by the old one), not merely cosmetic. Root-caused precisely
   in Section 5. Confirmed on the real text-import path; the
   `.kbhrecipe` path shares the identical code shape but was not
   independently re-confirmed this session (Section 5, Section 14).
2. **MEDIUM — A4-3.** Rename+save leaves the sidebar selector showing
   "-- Velg oppskrift --" (looks like nothing is selected) immediately
   after a successful, identity-changing save — directly undercuts
   trust in "is my change saved," the exact class of problem A1/A3
   exist to prevent.
3. **MEDIUM — A4-2.** First-time equipment confirmation is discovered
   only via a dead-end error on a different tab, with no shortcut back.
   Not data-unsafe (the gate itself is correct), but a real first-run
   trust/friction cost.
4. **LOW — A4-4 items 4/5/7.** Raw internal `brewId` UUIDs surface in
   otherwise-friendly toasts/captions. Confusing, not harmful — the
   underlying data is correct either way.
5. **LOW — A4-4 items 1/2/3/6/8.** "Snapshot"/"Core V1" wording in
   static captions/headers. Cosmetic.
6. **LOW/DECISION — A4-1.** No batch/brewer-name capture exists to lose
   data from; only relevant if the product actually wants the
   capability (Section 3).
7. **INFORMATIONAL — A4-3 save-as-copy.** Not a defect, a pending
   product choice (Section 5).

## 9. Smallest recommended fix for each valid finding

- **F0:** make the sidebar's reload-on-mismatch check
  (`ui/sidebar.py:68-69`) distinguish "user picked a different option in
  the dropdown" from "something else cleared the identity flags
  underneath the still-selected dropdown value" — e.g. only reload when
  `valgt_lagret_navn` differs from what the widget itself held on the
  *previous* render, not merely from `_last_loaded_recipe`. Needs a
  DECISION on the exact comparison (see Section 15) — not silently
  implementable within a FAST fix without picking that semantics.
- **A4-3 rename-orphaning:** explicitly set
  `st.session_state["sidebar_recipe_selector"] = ny_recipe["name"]` in
  `ui/recipe_card.py`'s `lagre_endringer_btn` success branch, before the
  existing `st.rerun()`.
- **A4-2:** add one button next to the existing error in
  `ui/kbhbrew_panel.py:150-156` that calls
  `lagre_equipment(last_equipment())` directly and reruns, reusing
  `modules/equipment.py`'s existing functions unchanged.
- **A4-4:** the eight wording/id-display swaps in Section 6's table,
  each a one-line change plus (where noted) a new i18n key pair.
- **A4-1:** no fix without a prior DECISION (Section 3); nothing to
  implement blind.

## 10. Exact files/functions/session keys/data fields likely touched

- `ui/sidebar.py` — the reload-on-mismatch condition (line ~68), for F0.
- `ui/recipe_card.py` — `lagre_endringer_btn` handler (lines 164–189),
  for the A4-3 selector-value fix; possibly also `_bygg_recipe_fra_session`
  if A4-1's decision adds new fields.
- `ui/kbhbrew_panel.py` — `render_kbhbrew_create_panel()` (equipment
  shortcut button + wording, lines 139–191),
  `render_kbhbrew_import_panel()` (wording, lines 205–272),
  `render_kbhbrew_export_panel()` (wording, line 295).
- `modules/i18n.py` — new keys per Section 6's table, NO+EN.
- `modules/equipment.py` — no change expected; only its existing
  `last_equipment()`/`lagre_equipment()` are called from a new site.
- Session keys read/touched: `sidebar_recipe_selector` (widget key),
  `_last_loaded_recipe`, `_last_loaded_recipe_file`, `gjeldende_navn`.
- No `.kbhbrew`/`.kbhrecipe` data field is touched by any FAST item.
  A4-1, if authorized, would touch the `.kbhbrew` schema (Section 11).

## 11. Core/schema impact assessment

**No schema change required** for F0, A4-2, A4-3, or A4-4 — all are
UI/session-state/wording fixes on existing fields and existing storage
functions.

**A4-1 is the only potential schema-impacting item, and only if
authorized.** A new human-meaningful batch-label/brewer-name field
would be a new key on the `.kbhbrew` object (most naturally alongside
`brewedAt` at the top level, or inside `learning`, since it is
brew-instance metadata, not part of the frozen recipe `snapshot`, and
not part of `actuals`/`sensing` either). This document does not choose
the field name or layer — that is the explicit `CORE/SCHEMA DECISION
REQUIRED` from Section 3.

## 12. NO/EN + i18n impact

- All eight A4-4 wording fixes need matching NO+EN keys added to
  `modules/i18n.py`, following the file's existing two-dict convention
  (already used correctly by A3-2/A3-3's `kbhbrew.*` keys added in PR
  #238).
- The pre-existing, structural gap that `ui/kbhbrew_panel.py` has *no*
  English text at all (unlike `ui/kbhbrew_history_panel.py`) is bigger
  than "smallest wording fix" and should not be silently absorbed into
  the A4-4 issue; flagged as a separate, explicit scope choice for
  Chief (fold in now vs. track separately later).
- A4-2's new button needs one new NO+EN string pair for its label.
- A4-3's fixes (both F0 and the rename-orphaning fix) are pure
  state/logic changes with no new user-facing text.

## 13. Acceptance matrix

| Area | Given | When | Then |
|---|---|---|---|
| A4-2 | equipment never saved, on Bryggdag tab | click "Start nytt brygg" | existing error still shows; a new one-click "confirm defaults" option appears and, when clicked, saves defaults and the next "Start nytt brygg" click succeeds without visiting Verktøy |
| A4-3 (rename) | a recipe loaded via sidebar, active brew in progress | rename + "Lagre endringer" | selector shows the NEW name selected (not the placeholder) in the same interaction A3-4 already reruns |
| A4-3 (unchanged) | a recipe loaded via sidebar | "Lagre endringer" with no name change | selector still shows the same recipe selected (regression guard — must not change) |
| F0 | a recipe loaded via sidebar | paste-import a different recipe and confirm | imported content persists after the import's own rerun; does NOT silently revert to the old recipe |
| A4-4 | "Start nytt brygg" clicked successfully | toast/caption shown | shows the recipe's name, not a raw `brewId`; no "Core V1"/"snapshot" wording remains in the touched strings |
| A4-4 (regression) | any existing kbhbrew create/import/export flow | any action | behavior/data unchanged — only display text/id-vs-name swapped |

## 14. Focused AppTest/unit test plan

For the eventual implementation PR(s), reusing existing harness
patterns already proven in this codebase:

- A4-2: extend `tests/fixtures/streamlit_harness/kbhbrew_create_harness.py`
  (or reuse `_A1_HARNESS`) with an unconfirmed-equipment case; assert
  the new button appears only when `equipment_kilde_er_lagret()` is
  False, calls `lagre_equipment`, and that "Start nytt brygg" then
  succeeds on a subsequent click — mirroring
  `tests/test_kbhbrew_create_panel_apptest.py`'s existing structure.
- A4-3 (rename-orphaning): extend
  `tests/test_app_a3_state_orientation_apptest.py`'s
  `TestA34UmiddelbarOrienteringEtterNavneendring` (full `app.py`
  harness, already proven to reach `lagre_endringer_btn` via the real
  sidebar) with an assertion on
  `at.sidebar.selectbox(key="sidebar_recipe_selector").value` after
  rename+save — this exact gap (no selector-value assertion) is why
  A3-4's own tests did not catch it.
- F0: a **new** full-`app.py` test — select a saved recipe via the real
  sidebar selector first, THEN paste-import a different recipe, and
  assert the imported ingredients survive (do not revert) after the
  import handler's own `st.rerun()`. Neither existing import test suite
  can be reused directly for this, precisely because both use harnesses
  that never populate a real selector-bound identity first (Section 5)
  — this is the reproduction case for whichever issue F0 becomes.
- A4-4: string-content assertions (`assertIn`/`assertNotIn` on rendered
  caption/toast text) in a small extension of
  `tests/test_kbhbrew_create_panel_apptest.py` and
  `tests/test_kbhbrew_import_export_apptest.py`, asserting the new
  wording appears and "snapshot"/"Core V1"/raw `brewId` no longer do,
  in both NO and EN session-language states.
- Full suite: not required for this docs-only preflight (no product
  code changed); would be required at implementation time per Workflow
  V2's FAST/DECISION test-responsibility rule.

## 15. Implementation split recommendation

Do **not** bundle all four A4 bullets plus F0 into one PR — ownership
and risk genuinely differ:

1. **`app/a4-equipment-shortcut` (FAST)** — A4-2 only. One new button,
   one existing function call, isolated to
   `ui/kbhbrew_panel.py::render_kbhbrew_create_panel()`.
2. **`app/a4-selector-orientation` (FAST, but needs one explicit
   decision first)** — A4-3's rename-orphaning fix. Small and bounded
   once the exact selector-update line is agreed; can ship with #1 or
   alone.
3. **`app/a4-terminology` (FAST)** — A4-4's eight wording/id-display
   swaps, as one small, self-contained, NO+EN copy-and-display PR.
   Chief should explicitly decide at kickoff whether the "no English at
   all in this panel" gap (Section 12) is folded into this same PR or
   tracked as its own follow-up — recommend follow-up, to keep this PR
   small.
4. **A separate, urgent issue for F0** — recommend opening it
   immediately (not bundled with any A4 PR), since it is a silent
   data-loss-shaped defect discovered during this audit, not a
   roadmap-A4 item. Risk class is likely `DECISION` at the "which
   comparison replaces the reload check" step (Section 9), then `FAST`
   to implement once that's chosen — Chief should confirm severity and
   sequencing; this document does not have authority to reclassify it
   above what #239 asked for.
5. **A4-1 stays a pure `DECISION`, no issue opened yet** — nothing to
   implement until the product decides whether batch/brewer-name
   capture is wanted at all, and if so, its field/layer (Section 3,
   Section 11). Recommend folding this into a future roadmap discussion
   rather than a standalone prep issue, since there is no current
   behavior to audit further — the answer is already "does not exist."

Preference for several small issues over one large one here is
deliberate: #1–#3 have no shared risk surface (different files/
functions), and F0 is severity- and root-cause-distinct enough from all
four A4 bullets that bundling it would blur its own review.

## 16. Explicit non-goals

- No product code, Core/schema, or `.kbhbrew` format change in this
  document or its branch.
- No redo of A1 (#170), A2, or A3 (#237/PR #238) — F0 is reported, not
  fixed, and does not alter any A1/A3 contract already in place.
- No Phase 3 acceptance work.
- No Web, Bryggeskole, Brew Lab, or Sóti change.
- No touching #97/#98/#99/#100.
- No touching owner-local/private data — `raw_data/unmatched_malt.json`
  remains modified-but-untouched-by-this-session throughout (verified
  via `git status --short` before and after this audit), and the
  pre-existing stash `KBH pre-sync 20260911-214508` is untouched.
- No merge, no deploy, no A4 implementation PR opened from this branch.
