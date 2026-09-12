# App A3 — State Orientation Contract: Source Preflight

Status: Analysis / preflight only — no App product behavior changed by
this document.
Scope: App (`app.py`, `ui/**`, `modules/**`) only. Web/Bryggeskole/Sóti
untouched. No Core schema/contract change. No `.kbhbrew` field added.
Authoritative master audited against: `66cad513a44a25a59b197e1ee7ada4dcc3830568`
(confirmed current `origin/master` at the time this preflight was
written; `origin` was re-fetched immediately before starting and had
not advanced beyond this SHA).
Written for: issue #235 (Roadmap V2.1 #101 Phase 2, App Brewday
Stabilization V1). Risk class: DECISION per Production Workflow V2
(#199) — this document is the "bounded prep" step; the actual product
decision/implementation follows in a later, separate issue after Chief
review.

## 1. Scope / governing roadmap

Roadmap V2.1 #101, Phase 2 (App Brewday Stabilization V1), A3: clearly
distinguish, in the Streamlit App, (a) active recipe, (b) active/
in-progress brew, (c) historical brew, (d) plan vs actual — these may
appear together, but the user must not reasonably mistake one for
another.

- **A1** (active-brew measurement binding) is already implemented and
  merged via issue #170 — NOT redone here. Its own preflight is
  [`app_a1_active_brew_measurement_preflight.md`](app_a1_active_brew_measurement_preflight.md);
  its "before" state (no binding at all) is now historical — current
  master already has the binding this preflight builds on top of.
- **A2** (calculation consistency) is already implemented via #160/
  #161 — not redone, not touched.
- Production Workflow V2 (#199, still LOCKED as of this preflight,
  `updated_at` 2026-09-12T18:10:31Z) classifies this work as
  **DECISION**: "schema/ownership/UX contract/data-state semantics or
  multiple legitimate solutions" → `bounded prep → explicit decision →
  implementation → gates → Chief PASS → owner-policy → release`. This
  document is exactly that bounded-prep artifact; it recommends but
  does not perform an implementation.
- Governing HO/CLAUDE.md/AGENT_WORKFLOW.md sources were re-read on
  current master and are unchanged from the versions this session
  already verified byte-for-byte in the immediately preceding Shared
  HO Policy smoke test (same branch point, `66cad51...`).

## 2. Current master/source baseline

Branch `docs/app-a3-state-orientation`, created from fresh
`origin/master` (`66cad513a44a25a59b197e1ee7ada4dcc3830568`) after
confirming `git fetch origin` showed zero drift (`0	0` ahead/behind)
and after preserving the known local file
(`raw_data/unmatched_malt.json`, unchanged) and stash (`KBH pre-sync
20260911-214508`, unchanged).

Files read in full for this audit: `app.py`; `ui/brewday_panel.py`;
`ui/kbhbrew_panel.py`; `ui/kbhbrew_history_panel.py`; `ui/sidebar.py`;
`ui/recipe_card.py`; `modules/kbhbrew.py` (status/actuals sections);
`modules/kbhbrew_storage.py` (`oppdater_brew_lag`); `modules/
kbhbrew_ui.py`; `modules/kbhbrew_history_ui.py`; `modules/
recipe_importer.py::apply_import_to_session_state`; `modules/
kbh_import_apply.py` (identity-pop line); `modules/recipe_storage.py::
lagre_oppskrift` (rename semantics); relevant i18n strings in
`modules/i18n.py` (`brew_history.*` keys, NO+EN); test method names in
`tests/test_brewday_a1_measurement_apptest.py`,
`tests/test_kbhbrew_history_panel_apptest.py`.

All line references below are read-only citations of this exact
master; nothing was changed.

## 3. Current state/identity map

Four session-state layers exist today, and A1 already unifies two of
them on purpose:

| Concept | Representation | Owner file |
|---|---|---|
| Active **recipe content** | `valgt_malt`, `valgt_humle`, `valgt_gjaer_id`, `gjeldende_navn`, `brygger_stil`, `batch_volum_input`, etc. — rebuilt into `ctx` every rerun by `bygg_recipe_context()` | `app.py:145-153`, `modules/recipe_context.py` |
| Active **recipe identity** (which file, if any, it was loaded from) | `_last_loaded_recipe_file` (+ display twin `_last_loaded_recipe`) | `ui/sidebar.py:128/134/141-142`, `ui/recipe_card.py:174-175/249` |
| Active/in-progress **brew** (session write-target) | `_aktiv_kbhbrew_brew_id`, read/written ONLY via `aktiv_brew_id()`/`sett_aktiv_brew_id()` | `ui/kbhbrew_panel.py:62-85` |
| Historical **brew selection** (Brew History picker) | `kbhbrew_historikk_valgt_id` (Streamlit selectbox key) | `ui/kbhbrew_history_panel.py:372-377` |

**Key fact, by deliberate A1 design (issue #170 "Identity safety"):**
the third and fourth rows are the *same identity*, kept in sync both
directions:

- `_sinkroniser_aktiv_brew_mot_oppskrift()` (`ui/kbhbrew_panel.py:88-111`)
  invalidates `_aktiv_kbhbrew_brew_id` (sets it to `None`) if the brew
  no longer exists locally, **or** if the current `_last_loaded_
  recipe_file` no longer equals the brew's own frozen `recipeId`
  (`modules/kbhbrew_ui.py::aktiv_brew_matcher_recipe()`).
- Whenever the active target changes (new brew created, or just
  invalidated), `render_kbhbrew_history_panel()` force-repositions its
  own selectbox to match, on the next render where they differ
  (`ui/kbhbrew_history_panel.py:363-370`).
- Conversely, an explicit user pick in the History selectbox updates
  the shared active target (`ui/kbhbrew_history_panel.py:379-382`),
  which then also retargets Steg 4/5's own OG/FG/post-boil-volume
  fields via a prefill-resync block that runs before those widgets are
  instantiated (`ui/brewday_panel.py:105-141`).
- This exact coupling is covered by an existing, passing test
  (`tests/test_brewday_a1_measurement_apptest.py::
  test_7_historikkens_eksplisitte_utvalg_retargetterer_steg45`) — it
  is intentional, not a bug, and exists specifically to prevent the
  ORIGINAL A1 gap (Steg 4/5 and History silently disagreeing about
  which `.kbhbrew` a write goes to).

The practical consequence for A3: **"historical brew" and "active/
in-progress brew" are not two independent states in current source —
they are one shared pointer**, and the roadmap's own question ("does
selecting history retarget Brewday, or vice versa?") is answered
**YES, both ways, by design**. A3's job is therefore not to invent a
second identity, but to make the *meaning* of that single, shared
pointer legible when the selected brew is not "today's session brew"
in the intuitive sense (see Section 8).

## 4. Active recipe contract (current, as-proven)

- **Canonical identity**: `_last_loaded_recipe_file` — the literal
  filename the current recipe content came from, or `None` for an
  unsaved/blank/imported-but-not-yet-saved recipe. `_last_loaded_
  recipe` is a display-name twin, always set/cleared alongside it.
- **What changes it, proven by source**:
  - Selecting a saved recipe in the sidebar → sets both keys
    (`ui/sidebar.py:128,134`), plus `st.rerun()` (line 139) — visible
    immediately.
  - Selecting the placeholder "(none selected)" → clears both
    (`ui/sidebar.py:141-142`).
  - `.kbhrecipe` file import → explicitly clears `_last_loaded_
    recipe_file` (`modules/kbh_import_apply.py:102`) — always treated
    as a brand-new, unsaved recipe (matches its own docstring
    "KBHR-010").
  - "💾 Lagre endringer" (save changes to the loaded recipe) → keeps
    the identity if the name is unchanged, or **updates it to the new
    filename** if the recipe was renamed before saving (`ui/
    recipe_card.py:174-175`, backed by `modules/recipe_storage.py::
    lagre_oppskrift()`'s `navn_endret` branch, lines 449-452).
  - "💾 Lagre som ny kopi" (save-as-variant) → does **not** touch
    `_last_loaded_recipe_file` at all — the on-screen "current" recipe
    identity is unchanged; only a new file is written on disk.
  - "🗑️ Slett gjeldende" (archive current) → clears `_last_loaded_
    recipe_file` and resets recipe content to the blank defaults
    (`ui/recipe_card.py:224-249`).
  - **Text-paste import** ("🔍 Analyser" → "✅ Importer oppskrift" in
    the sidebar, `modules/recipe_importer.py::
    apply_import_to_session_state()`) → does **NOT** touch
    `_last_loaded_recipe_file` at all (confirmed by full read + repo
    grep: the function only writes `gjeldende_navn`, `batch_volum_
    input`, `valgt_malt`, `valgt_humle`, `valgt_gjaer_id`, `import_
    versjon`). This is the one identity-changing recipe action that
    behaves differently from every other one — see Section 8, finding
    A3-1.
- **Save/import/new/variant summary**: every path that produces a
  *genuinely new* recipe identity clears/sets `_last_loaded_recipe_
  file` correctly **except** text-paste import.

## 5. Active brew contract (current, as-proven)

- **Canonical identity**: `_aktiv_kbhbrew_brew_id`, accessed only via
  `aktiv_brew_id()` / `sett_aktiv_brew_id()` (`ui/kbhbrew_panel.py:
  66-85`) — no other module reads the raw key.
- **Created by**: "▶️ Start nytt brygg" (`ui/kbhbrew_panel.py:145-173`),
  which freezes `ctx["recipe"]` + equipment + predicted values as a
  new `.kbhbrew`'s immutable `snapshot`, mints `brewId`, and stamps
  `recipeId = st.session_state.get("_last_loaded_recipe_file")` at
  that exact moment (line 167).
- **Retargeted by**: an explicit History selection (Section 3), or a
  fresh "▶️ Start nytt brygg" click (always updates to the new brew,
  never blocked by an existing active brew — multiple real brews per
  recipe are explicitly supported).
- **Invalidated by**: `_sinkroniser_aktiv_brew_mot_oppskrift()`
  whenever the brew no longer exists locally, or its frozen `recipeId`
  no longer matches the live `_last_loaded_recipe_file` — run at the
  top of `render_kbhbrew_create_panel()`, i.e. before Steg 4/5's own
  prefill-resync and before History's default-selection logic read the
  pointer in the same rerun.
- **A1 measurement-write protection** (unchanged, still correctly
  enforced on current master):
  - The ONLY write path for Steg 4/5 is the explicit "💾 Lagre målinger
    til aktivt brygg" button (`ui/brewday_panel.py:424-450`); it
    resolves `aktiv_brew_id()` fresh at click time, is **disabled
    entirely** when there is no active brew (`disabled=_lagre_mal_
    brew is None`, line 427), validates OG/FG via the same strict
    `parse_actual_tallfelt()` History uses, and writes through the
    same `oppdater_brew_lag()` — no parallel/new write mechanism.
  - Typing into Steg 4/5 without clicking never persists anything
    (rerun-only; proven by `test_1_typing_uten_lagre_klikk_
    skriver_ingenting`).
  - A recipe switch that invalidates the active brew also empties
    `bd_og`/`bd_fg`/`bd_post_boil_vol` before the widgets render again
    (`ui/brewday_panel.py:123-141`, proven by `test_4`).
  - A second new brew from the same recipe never inherits unsaved
    Steg 4/5 text from the first (proven by `test_5`).

## 6. Historical brew contract (current, as-proven)

- **Representation**: `render_kbhbrew_history_panel()`'s own
  selectbox, sourced from `hent_alle_brews()` — every locally stored
  `.kbhbrew`, of **any** `status` (`active`/`done`/`discarded`),
  sorted newest-`createdAt`-first (`modules/kbhbrew_ui.py::
  sorter_brews_for_eksport`).
- **Independent of the active Brewday brew?** **No** — by design, it
  is the *same* identity (Section 3). This directly answers the
  roadmap's own question 5 ("does selecting history silently retarget
  Brewday, or vice versa?") with a proven **yes, both directions,
  intentionally, and covered by an existing test** — not a bug, but
  the central fact A3 must design its orientation contract around.
- **`status` field**: purely a persisted, manually-set lifecycle label
  (`active`/`done`/`discarded`), changed **only** via History's own
  actuals-form status dropdown + explicit "💾 Lagre målte verdier"
  click (`ui/kbhbrew_history_panel.py:167-174,198-208`). Nothing in
  source ever auto-transitions it — a brew stays `status: active`
  forever unless a human explicitly flips it in History. This means
  the word "active" is used for two structurally unrelated things at
  once (see Section 8, finding A3-2).
- **Where the two states can legitimately differ**: any time the user
  has never clicked "▶️ Start nytt brygg" this session and has never
  picked anything in History either (`aktiv_brew_id()` is `None` while
  History still lists brews to browse) — this is the one case where
  "browsing history" and "having an active brew" are cleanly separate,
  and current source already handles it correctly (History renders its
  own picker regardless; the Steg 4/5 save section shows a clear "no
  active brew" caption, `ui/brewday_panel.py:416-420`).

## 7. Plan vs actual contract (current, as-proven)

Already clean and unambiguous — no ambiguity found here:

- **Frozen plan**: `brew["snapshot"]`, built once at creation by
  `modules/kbhbrew.py::bygg_ny_brew_snapshot()`, and — verified again
  on this master — `oppdater_brew_lag()` (`modules/kbhbrew_storage.py:
  206-241`) has **no `snapshot` parameter at all**, so nothing can ever
  mutate it after creation.
- **Mutable actuals**: `brew["actuals"]`, written only through
  `oppdater_brew_lag()`'s explicit-click paths.
- **Presentation**: `_render_planlagt_sammendrag()` (`ui/kbhbrew_
  history_panel.py:112-126`) reads exclusively from `snapshot`, under
  the heading `brew_history.planlagt_tittel` = "📋 Planlagt (frosset
  ved opprettelse)" / "📋 Planned (frozen at creation)". `_render_
  actuals_skjema()` reads/writes exclusively `actuals`, under `brew_
  history.actuals_tittel` = "🧪 Målte verdier (faktisk)" / "🧪 Measured
  values (actual)". Every individual field label is distinctly
  prefixed "Planlagt …"/"Planned …" vs "Faktisk …"/"Actual …" in both
  languages (`modules/i18n.py:77-91,144-156`). `_render_sammenligning()`
  shows both side by side under "⚖️ Planlagt vs. faktisk"/"Planned vs.
  actual".
- **OG (target/planned) label on Steg 4 itself** already includes the
  planned value inline: `f"OG (mål: {fmt_og(ctx['og'])})"` (`ui/
  brewday_panel.py:340`) — the widget label already tells the user
  what the *planned* value is while they type the *actual* one.

No source evidence of a real "plan mistaken for actual" trust break —
this is the one of the four roadmap dimensions that is already
correctly contracted and should not be touched by A3's implementation.

## 8. Proven ambiguity/trust-break inventory

Ordered by severity. Every item below is demonstrated from the exact
current-master source cited, not inferred.

### A3-1 (highest severity) — Text-paste import does not invalidate the active-brew pointer

`modules/recipe_importer.py::apply_import_to_session_state()` (lines
240-269) never reads or writes `_last_loaded_recipe_file`. Every other
recipe-identity-changing action does (Section 4). Consequence: a user
with an active brew from recipe A can use "📥 Importer oppskrift fra
tekst" → "✅ Importer oppskrift" to completely replace the on-screen
malt/humle/gjær/name with an unrelated recipe B's content, while
`_last_loaded_recipe_file` silently keeps pointing at recipe A's file.
`_sinkroniser_aktiv_brew_mot_oppskrift()` then sees no identity
mismatch (it only ever compares filenames) and leaves the active brew
untouched. The Steg 4/5 "💾 Lagre målinger til aktivt brygg" caption
(`ui/brewday_panel.py:422-423`) still shows recipe A's brew's own
frozen name/id, but a user who just pasted recipe B and is now looking
at recipe B's numbers on screen can easily read that caption as "yes,
this is my current recipe's brew" and save recipe-B-context
measurements onto recipe A's historical brew. **Untested**: `test_4`
(the existing recipe-switch invalidation test) uses a synthetic
`KVERNHAUG_TEST_RECIPE_ID` test harness that simulates a `_last_
loaded_recipe_file` change directly — it does not exercise the real
text-import code path, so this gap has no regression coverage today.

### A3-2 — "Active" is overloaded between brew lifecycle status and session write-target

`brew["status"] == "active"` (a persisted lifecycle field, changed only
via History's own dropdown) and "✅ Aktivt brygg denne økten" (`ui/
kbhbrew_panel.py:176-180`, the ephemeral session write-target caption)
are two unrelated concepts sharing the word "aktiv"/"active" with no
UI distinction. Because History selection sets the session target
regardless of the selected brew's own status (Section 6), simply
clicking an old, already-`Ferdig`/`Done` brew in History produces a
caption reading "✅ Aktivt brygg denne økten: `xyz` · opprettet … ·
status **Ferdig**" — "active" and "done" describing the exact same
object in the same sentence. Nothing in source prevents or flags this.

### A3-3 — Selecting an old/finished brew in History silently makes it the live measurement-save target, with no distinguishing warning

A direct consequence of the by-design coupling in Section 6: there is
no difference in the Steg 4/5 "💾 Lagre målinger" UI between "this is
today's brew I just started" and "this is a brew from months ago I
opened in History purely to look at it." The caption at `ui/brewday_
panel.py:422-423` shows only the target brew's frozen recipe name and
its `brewId` — never its `status`, never how old it is, never an
explicit "you are about to write into an already-finished brew"
signal. A user who opens History to review an old batch, then
absent-mindedly types a value into Steg 4's OG field and clicks the
still-enabled save button, will silently overwrite that old, finished
brew's `actuals` — an explicit click occurred (not a silent write in
the strict A1 sense), but the *orientation* that this brew is
historical rather than "the one I'm brewing right now" is not
communicated anywhere in that flow.

### A3-4 (lowest severity) — Renaming-and-saving the active recipe invalidates the active brew silently, one rerun late

`lagre_oppskrift()` only changes the returned filename when the
recipe's name actually changed (`modules/recipe_storage.py:449-452`).
When it does, "💾 Lagre endringer" updates `_last_loaded_recipe_file`
immediately (`ui/recipe_card.py:174-175`) but issues no `st.rerun()`
afterward. `_sinkroniser_aktiv_brew_mot_oppskrift()` therefore does not
re-evaluate (and clear `_aktiv_kbhbrew_brew_id` + the bound Steg 4/5
fields) until the *next*, unrelated rerun — so a user who renames and
saves mid-brewday sees no immediate feedback that their active-brew
target and typed-but-unsaved Steg 4/5 values are about to disappear;
they simply vanish the next time any widget triggers a rerun. This is
arguably the *correct* identity outcome (a rename is a new filename,
hence a new `recipeId` match), but the timing/silence is exactly the
kind of "is this intentional and visible" gap the roadmap goal calls
out.

No other ambiguity was found in the required source trace — in
particular, plan-vs-actual (Section 7) and the core A1 write-binding
itself (Section 5) are already sound.

## 9. Proven-safe existing behavior (do not touch)

- Frozen-snapshot immutability (`oppdater_brew_lag()` has no `snapshot`
  parameter) — unchanged since A1, still enforced by construction.
- Explicit-click-only writes everywhere: create brew, Steg 4/5 save,
  History actuals save, History sensing/learning save — no
  auto-save-on-rerun anywhere in this whole surface.
- Sidebar-driven recipe switch correctly invalidates the active brew
  and clears bound fields (`test_4`, a real production code path, not
  synthetic — the synthetic harness in `test_4` simulates the
  *outcome* of a `_last_loaded_recipe_file` change, which is exactly
  what the real sidebar path also produces).
- A second new brew from the same recipe never inherits unsaved Steg
  4/5 text (`test_5`).
- Legacy `recipes/_logs/` is untouched by any of this (`test_6`).
- Numeric validation (`parse_actual_tallfelt()`) is shared, identical,
  and strict across both write surfaces (Steg 4/5 and History) — no
  divergent parsing behavior.
- `.kbhrecipe` file import correctly clears the active-recipe identity
  (`modules/kbh_import_apply.py:102`).
- Archiving the current recipe correctly clears identity and resets to
  blank defaults (`ui/recipe_card.py:249`).
- Plan vs actual labeling is already clear, consistent, and fully
  i18n'd in both languages (Section 7).
- DEMO_MODE hides every persistent-write UI path consistently
  (create panel, import/export panels, History panel, Steg 4/5 save
  section).

## 10. Transition matrix

| Transition | Current behavior | Orientation gap? |
|---|---|---|
| Select another saved recipe (sidebar) | `_last_loaded_recipe_file` updates, active brew invalidated + fields cleared, `st.rerun()` — immediate | None (proven-safe) |
| Import `.kbhrecipe` file | Identity explicitly cleared, treated as brand-new unsaved recipe | None (proven-safe) |
| **Text-paste import** | Recipe content fully replaced; identity **not** cleared; old active brew (if any) silently remains the write target | **A3-1** |
| New recipe / blank (via "🗑️ Slett gjeldende") | Identity cleared, content reset, active brew invalidated on next render | None (proven-safe) |
| "💾 Lagre som ny kopi" (save as variant) | Identity unchanged (correct — on-screen recipe is still the same one); new file written on disk only | None |
| "💾 Lagre endringer", name unchanged | Identity unchanged; active brew untouched | None |
| "💾 Lagre endringer", name changed | Identity updated immediately; active-brew invalidation deferred to next unrelated rerun | **A3-4** |
| Start a new brew ("▶️ Start nytt brygg") | New `.kbhbrew` frozen, becomes new active target, History selectbox force-syncs to it | None (proven-safe) |
| Reopen existing active brew (revisit Bryggdag tab) | Session-persisted `_aktiv_kbhbrew_brew_id` still resolves via `hent_brew()`; self-heals if deleted out-of-band | None (proven-safe) |
| Select another (older/finished) brew in History | Becomes the new shared active target; Steg 4/5 fields resync to its own actuals; no distinction shown for its status/age | **A3-2**, **A3-3** |
| Return from History to a brand-new/no-target state | Steg 4/5 save section shows explicit "no active brew" caption, save button disabled | None (proven-safe) |

## 11. Recommended smallest A3 implementation

All four findings are small, label/warning-level fixes to the
**existing** shared identity — no new state engine, no second brew
pointer, no new session-state key beyond what is already listed below.

- **Fix A3-1**: add the same identity-clearing call `.kbhrecipe` import
  already uses — `st.session_state.pop("_last_loaded_recipe_file",
  None)` — inside `apply_import_to_session_state()` (`modules/
  recipe_importer.py`), mirroring `modules/kbh_import_apply.py:102`
  exactly. One line, same precedent, no new mechanism.
- **Fix A3-2**: reword the existing caption at `ui/kbhbrew_panel.py:
  176-180` to separate "this session writes to…" from the brew's own
  persisted `status`, e.g. "🎯 Bryggdag skriver til: `<navn>` ·
  `<brewId>` (lagret status: **Ferdig**)" instead of prefixing the
  whole line with "Aktivt". Wording-only change to an existing
  `st.success()` call; no new state.
- **Fix A3-3**: in the existing "💾 Lagre målinger til aktivt brygg"
  block (`ui/brewday_panel.py:411-423`), add a conditional `st.warning`
  when `_lagre_mal_brew.get("status") != "active"`, e.g. "⚠️ Dette
  bryggets status er **Ferdig** — lagring her oppdaterer et allerede
  avsluttet brygg, ikke et nytt." Reuses the exact same `_lagre_mal_
  brew` variable already resolved on that line; no new lookup, no new
  state.
- **Fix A3-4**: add `st.rerun()` after a successful "💾 Lagre endringer"
  that changed the recipe's identity (i.e., `nytt_filnavn !=
  st.session_state.get("_last_loaded_recipe_file")` before the
  assignment) — mirrors the `st.rerun()` pattern already used
  elsewhere in the same file (archive/import flows) so the resulting
  active-brew invalidation is visible in the same interaction.

None of these four changes touch `.kbhbrew` schema, Core contracts,
calculation logic, or introduce any new identity concept — all four
reuse an existing variable, an existing invalidation rule, or an
existing UI call site, changed only in wording or in one conditional
branch/one `st.rerun()` placement.

## 12. Exact files/functions/session keys likely touched

| Fix | File | Function/site | Session keys involved (all pre-existing) |
|---|---|---|---|
| A3-1 | `modules/recipe_importer.py` | `apply_import_to_session_state()` | `_last_loaded_recipe_file` |
| A3-2 | `ui/kbhbrew_panel.py` | `render_kbhbrew_create_panel()`, the `st.success(...)` at lines 176-180 | `_aktiv_kbhbrew_brew_id` (read via `aktiv_brew_id()`) |
| A3-3 | `ui/brewday_panel.py` | the "💾 Lagre målinger til aktivt brygg" block, lines 411-423 | `_aktiv_kbhbrew_brew_id` (via `aktiv_brew_id()`), `_lagre_mal_brew` (local var, already resolved) |
| A3-4 | `ui/recipe_card.py` | the "💾 Lagre endringer" `st.button(...)` handler, lines 164-177 | `_last_loaded_recipe_file`, `_last_loaded_recipe` |

No new files, no new i18n keys strictly required (A3-2/A3-3 strings
can be added as new `brew_history.*`/`kbhbrew.*` i18n entries following
the exact existing pattern in `modules/i18n.py`, in both languages —
this is a content addition to an existing table, not a new mechanism).

## 13. Acceptance matrix

| # | Given | When | Then |
|---|---|---|---|
| 1 | Active brew exists for recipe A | User text-imports a different recipe B | Active brew is invalidated; Steg 4/5 save section shows "no active brew"; History selectbox shows no forced selection |
| 2 | A brew with `status: done` is selected in History | Steg 4/5 create-panel caption renders | Caption text no longer reads as "Aktivt …" without qualification; it clearly separates "this session's write target" from the brew's own stored status |
| 3 | A brew with `status` != `active` is the current write target | The "💾 Lagre målinger" section renders | A visible warning states the target brew is not in `active` status, before any save click |
| 4 | User renames the loaded recipe and clicks "💾 Lagre endringer" | Save succeeds and the filename changed | The active-brew invalidation (and any resulting Steg 4/5 field clear) is visible in the same interaction, not one rerun later |
| 5 | Any of the above | — | Frozen `snapshot` is never mutated; no new `.kbhbrew` field is written; DEMO_MODE still hides all of this UI; existing `test_1`–`test_7` in `test_brewday_a1_measurement_apptest.py` still pass unmodified |

## 14. Focused AppTest/unit test plan

No browser/E2E harness exists in this repo (`testing.md`) — everything
below is `AppTest`/unit-level, extending the existing patterns:

- **New AppTest cases**, most naturally added to `tests/
  test_brewday_a1_measurement_apptest.py` (same harness, same fixtures)
  or a new sibling `tests/test_app_a3_state_orientation_apptest.py` if
  the implementation issue prefers a clean separation from A1's own
  suite:
  1. Text-paste import while an active brew exists invalidates it
     (closes the A3-1 coverage gap `test_4` does not reach) — exercise
     the real sidebar "🔍 Analyser" → "✅ Importer oppskrift" flow, not
     the synthetic `KVERNHAUG_TEST_RECIPE_ID` harness.
  2. Selecting a `status: done` brew in History surfaces the new A3-3
     warning in the Steg 4/5 save section; selecting a `status: active`
     brew does not.
  3. The A3-2 reworded caption text is asserted directly (exact string
     or absence of the ambiguous old phrasing) for a `done`-status
     active target.
  4. Renaming and saving the loaded recipe mid-brewday is followed
     (within the same AppTest `.run()`) by the active-brew invalidation
     and field-clear being observable immediately.
  5. Regression: `test_1`–`test_9` in `test_brewday_a1_measurement_
     apptest.py` and all of `test_kbhbrew_history_panel_apptest.py`
     still pass unmodified.
- **Unit tests**: only if a small pure helper is extracted (e.g. a
  `skal_advare_om_avsluttet_status(brew)` predicate for A3-3) — belongs
  in `modules/kbhbrew_ui.py` with its own test in `tests/
  test_kbhbrew_ui_helpers.py`, mirroring the existing pure-function
  pattern; not required if the condition stays a one-line inline check.
- **Existing suites that must stay green**: `tests/
  test_brewday_a1_measurement_apptest.py`, `tests/
  test_kbhbrew_history_panel_apptest.py`, `tests/
  test_kbhbrew_create_panel_apptest.py`, `tests/
  test_kbhbrew_storage_identity.py`, `tests/
  test_brewday_tab_ux_cleanup.py`, `tests/test_app_i18n_foundation.py`
  (if new i18n keys are added).

## 15. Non-goals (explicit)

- No redo of A1 (#170) persistence/binding logic — it is correct and
  is the foundation this preflight builds on.
- No redo of A2 (#160/#161) calculation consistency.
- No Core `.kbhbrew`/`.kbhrecipe` schema change, no new wire field.
- No new session-state identity concept, second brew pointer, or state
  machine — every recommended fix reuses the existing shared
  `_aktiv_kbhbrew_brew_id`/`_last_loaded_recipe_file` pair.
- No automatic `status` transition (e.g. auto-marking a brew "done") —
  status remains a manual, explicit History-form choice.
- No redesign of the Brew History form, the sensing/learning form, or
  the plan-vs-actual comparison — Section 7 found them already correct.
- No Web/Bryggeskole/Sóti change, no deployment.
- No touching #97/#98, #99/#100, or owner-local/private data
  (`raw_data/unmatched_malt.json` untouched by this audit).
- No A4 workflow-polish scope creep.

## 16. Implementation split recommendation

**One bounded implementation issue, not a split.** All four findings
(A3-1 through A3-4) are label/warning/timing fixes to the *same* shared
identity contract (Section 3) rather than independent features:

- A3-2 and A3-3 are two sides of the same "browsing an old brew in
  History looks the same as brewing today" problem — shipping one
  without the other leaves the caption fixed but the save-button risk
  unaddressed, or vice versa.
- A3-1 and A3-4 both close the two remaining gaps in the single
  invalidation rule `_sinkroniser_aktiv_brew_mot_oppskrift()` already
  encodes — splitting them would mean two PRs each touching the same
  identity-comparison logic's edge cases.
- None of the four changes conflict on files enough to justify separate
  review lanes (`modules/recipe_importer.py`, `ui/kbhbrew_panel.py`,
  `ui/brewday_panel.py`, `ui/recipe_card.py` — four small, independent
  edits, reviewable together as one coherent "state orientation" pass).
- This mirrors the A1 preflight's own bundling reasoning (Section 13
  there): the fixes are not independently shippable in a way that
  reduces risk, only in a way that fragments review.

## 17. STOP

Per issue #235's guardrails: this is a docs-only preflight. No
`app.py`/`ui/**`/`modules/**` product behavior was modified. A3
implementation does not start automatically from this preflight — it
waits for Chief exact-head review per Production Workflow V2's
DECISION flow.
