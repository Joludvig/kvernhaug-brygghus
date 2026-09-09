# App A1 — Active Brew / Measurement Binding: Source Preflight

Status: Analysis / preflight only — no App product behavior changed by
this document.
Scope: App (`app.py`, `ui/**`, `modules/**`) only. Web/Bryggeskole/Sóti
untouched.
Authoritative master audited against: `b722811a7e04def9ae98baa95acaa78e6d0cbac4`
(the commit named in issue #155 at creation time; this repo's `master`
was unchanged at that SHA when this audit was written).
Written for: issue #155 (Roadmap V2.1 #101 Phase 2, CoS day queue #153).

## 0. Executive summary

The Roadmap A1 contract assumes a single ownership question — "does a
measurement land on the right brew" — but the actual source shows a
**more fundamental gap**: there are **two structurally independent
measurement-entry surfaces** in the Brewday tab, and only one of them
is wired to any `.kbhbrew` brew at all.

1. **Brewday-sheet fields** (`ui/brewday_panel.py`, Steg 4/5:
   `bd_og`, `bd_fg`, `bd_abv`, `bd_pre_boil_sg`, `bd_pre_boil_vol`,
   `bd_post_boil_vol`, `bd_pitch_temp`, `bd_transfer_note`, …) are
   **plain Streamlit widget session-state** with **no `.kbhbrew`
   persistence path at all**. They feed only the in-memory `plan`/
   `eff` calculations and the downloadable brewday-sheet HTML
   (`render_brewday_html`). They are never read or written by
   `modules/kbhbrew_storage.py`.
2. **Brew History actuals fields** (`ui/kbhbrew_history_panel.py`,
   widget keys `kbhbrew_hist_og::{brew_id}` etc.) **are** wired to
   `.kbhbrew` — via an explicit "💾 Lagre målte verdier" button that
   calls `modules/kbhbrew_storage.py::oppdater_brew_lag()`. This is a
   second, separate form, further down the same Brewday tab, with its
   **own independent brew selector** (`kbhbrew_historikk_valgt_id`)
   that is **not** pre-bound to whichever brew the "▶️ Start nytt
   brygg" button most recently created.

So the roadmap's "does OG go to the right brew" question is downstream
of a prior, unaddressed question: **today, OG entered on the brewday
sheet does not go to *any* brew** — the user must retype it a second
time, in a second form, after manually re-selecting the brew from an
unrelated dropdown. This is not a data-corruption bug (nothing is
silently misfiled) — it is a **missing binding + a duplicate,
disconnected UI**, which is the correct framing for the "smallest safe
implementation boundary" in Section 8.

No code in this audit was changed; all line references are read-only
citations of current master.

## 1. Current source truth — prose data-flow

### 1.1 What "active brew" means today, concretely

There is **no App-wide "active brew" concept**. There are three
independent, weakly-related notions that could each be mistaken for
it:

- **`_aktiv_kbhbrew_brew_id`** (`ui/kbhbrew_panel.py:52`,
  `_AKTIV_BREW_ID_NOKKEL`) — session-only (never persisted to disk),
  set only inside the `st.button("▶️ Start nytt brygg")` handler
  (`ui/kbhbrew_panel.py:110`) right after
  `opprett_og_lagre_ny_brew()` succeeds. It exists **solely to render
  a "✅ Aktivt brygg denne økten" confirmation caption**
  (`ui/kbhbrew_panel.py:118-122`) — the docstring is explicit that it
  is "KUN for å vise en vedvarende bekreftelse … IKKE for å hindre et
  NYTT … klikk" (`ui/kbhbrew_panel.py:66-69`). **Nothing else in the
  codebase reads this key** (confirmed by repo-wide grep — the only
  other references are in
  `tests/test_kbhbrew_create_panel_apptest.py`, asserting exactly this
  confirmation-caption behavior).
- **`kbhbrew_historikk_valgt_id`** (`ui/kbhbrew_history_panel.py:338`)
  — the Streamlit `selectbox` widget key backing the *separate* Brew
  History picker. Defaults to whatever `st.selectbox` defaults to
  (first item in `sorter_brews_for_eksport(brews)`'s newest-first
  order, `modules/kbhbrew_ui.py:117-128`) — **not** derived from
  `_aktiv_kbhbrew_brew_id` in any way.
- **`_last_loaded_recipe_file`** (`ui/sidebar.py:134`) — the *recipe*
  identity used only as `recipe_id` when minting a **new** brew
  (`ui/kbhbrew_panel.py:105`). It is a recipe-file pointer, not a
  brew pointer, and has no relationship to which existing brew is
  "active" for measurement entry.

None of these three keys is cleared, reconciled, or cross-checked
against either of the others anywhere in the source.

### 1.2 Brewday-sheet fields never reach `.kbhbrew`

`ui/brewday_panel.py:17-31` seeds `_BD_DEFAULTS` — including
`bd_pre_boil_vol`, `bd_pre_boil_sg`, `bd_post_boil_vol`,
`bd_pitch_temp`, `bd_transfer_note` — as ordinary
`st.session_state` defaults, each bound 1:1 to a plain
`st.text_input`/`st.number_input` widget (`bd_og`: line 291, `bd_fg`:
line 333, `bd_abv`: line 337, no default in `_BD_DEFAULTS` for these
three — they're created lazily by the widgets themselves). These
values are read in exactly two places:

1. `beregn_effektivitet(...)` (Steg 6, `ui/brewday_panel.py:357-364`)
   — an in-memory, per-rerun display calculation only.
2. The `log` dict built in the `st.button("🖨️ Generer
   Bryggedagsark")` handler (`ui/brewday_panel.py:419-430`), passed to
   `render_brewday_html(ctx, plan, log, water=...)` and offered as a
   **downloadable HTML file** — never written to
   `recipes/_kbhbrew/` or `recipes/_logs/`.

`modules/kbhbrew_storage.py::oppdater_brew_lag()` is **not imported,
called, or referenced anywhere in `ui/brewday_panel.py`**
(confirmed by grep: `oppdater_brew_lag` appears only in
`ui/kbhbrew_history_panel.py`, `modules/kbhbrew_history_ui.py`,
`modules/kbhbrew.py`'s docstrings, `modules/kbhbrew_storage.py`
itself, and its unit tests). There is **no code path, direct or
indirect, by which `bd_og`/`bd_fg`/`bd_post_boil_vol`/
`bd_transfer_note` ever reach a `.kbhbrew` brew's `actuals` layer.**

### 1.3 The *separate* path that does reach `.kbhbrew`

`ui/kbhbrew_history_panel.py::render_kbhbrew_history_panel()` is
rendered directly below `render_brewday_panel`'s own internals — it is
actually invoked *from inside* `render_brewday_panel`, at
`ui/brewday_panel.py:92` (`render_kbhbrew_history_panel()`, called
right after `render_kbhbrew_create_panel()` at line 91, both **before**
the "🗒️ 1. Bryggeplan" expander). So the create panel, the history
panel, and Steg 1-6 (including the Steg 4 OG field) all render in the
same tab, in this order:

1. Header + batch metadata inputs.
2. `render_kbhbrew_create_panel()` — "▶️ Start nytt brygg".
3. `render_kbhbrew_history_panel()` — brew picker + actuals form +
   sensing/learning form (**writes to `.kbhbrew`**).
4. Steg 1-6 expanders, including Steg 4 "⚗️ Overføring & OG"
   (`bd_og` — **does not write to `.kbhbrew`**) and Steg 6
   "📊 Effektivitet" (reads `bd_og`/`bd_pre_boil_sg`/
   `bd_pre_boil_vol` for a **display-only** efficiency estimate).
5. Checklist + print-sheet button (reads `bd_og`/`bd_fg` again, for
   the downloadable HTML only).

A user who wants to permanently record OG must therefore scroll *past*
Steg 4's own OG field, find the History panel's picker higher up the
page, re-select the same brew there (nothing pre-selects it), and type
the OG a second time in `kbhbrew_hist_og::{brew_id}`
(`ui/kbhbrew_history_panel.py:132-136`), then click "💾 Lagre målte
verdier" (`ui/kbhbrew_history_panel.py:173`). Only *that* click reaches
`oppdater_brew_lag()` (`ui/kbhbrew_history_panel.py:189-199`), which
merges into the stored brew's `actuals` layer via
`normaliser_actuals_lag({**gjeldende, **actuals})`
(`modules/kbhbrew_storage.py:230-231`) and writes atomically
(`_skriv_json_atomisk`, `modules/kbhbrew_storage.py:240`).

### 1.4 Snapshot vs. actuals separation (already sound)

`modules/kbhbrew_storage.py::oppdater_brew_lag()` (lines 206-241)
**never accepts a `snapshot` argument at all** — there is no code path
in this function, or anywhere else, that can overwrite
`brew["snapshot"]` after creation. `opprett_og_lagre_ny_brew()`
(lines 177-203) builds the snapshot exactly once, via
`modules/kbhbrew.py::bygg_ny_brew()` → `bygg_ny_brew_snapshot()`
(`modules/kbhbrew.py:308-347`), which is a pure function with no
disk/session access. This half of the roadmap contract — "frozen
historical plan/snapshot never changes" — is **already correctly
enforced by construction**, independent of anything A1 needs to add.

## 2. Answers to the required source-audit questions

**Q1 — What object/id currently represents an active/in-progress brew,
if any?**
None, canonically. `_aktiv_kbhbrew_brew_id` is the closest candidate
but is explicitly scoped (by its own docstring and by every actual
read site) to "last brew created this session, for display only" — it
is never used to route a measurement write. See Section 1.1.

**Q2 — When a new `.kbhbrew` is created, where is its local identity
stored for subsequent reruns?**
`st.session_state[_AKTIV_BREW_ID_NOKKEL]`
(`"_aktiv_kbhbrew_brew_id"`), set at `ui/kbhbrew_panel.py:110`,
session-only (not written to any file — the brew *record* itself is
persisted via `opprett_og_lagre_ny_brew()`, but the pointer to "which
brew is active" is not). It is read back once, at
`ui/kbhbrew_panel.py:113-122`, purely to re-render the confirmation
caption and self-heal (`st.session_state.pop(...)`) if the brew was
deleted from disk out-of-band.

**Q3 — Does `bd_og`, `bd_fg`, post-boil/actual volume, or related
transfer data currently write into `.kbhbrew` actuals at all? If yes,
exact call path. If no, prove the gap.**
No. Proof: `oppdater_brew_lag` is not imported by
`ui/brewday_panel.py` (verified by `grep -rn "oppdater_brew_lag"
--include=*.py .` — every hit is in `kbhbrew_history_panel.py`,
`kbhbrew_history_ui.py`, `kbhbrew.py`/`kbhbrew_storage.py` internals,
or tests of those files). `bd_og`/`bd_fg`/`bd_post_boil_vol`/
`bd_pre_boil_vol`/`bd_pre_boil_sg`/`bd_pitch_temp`/
`bd_transfer_note` are read only at `ui/brewday_panel.py:341-364`
(effektivitet display) and `:420-430` (HTML export `log` dict) — see
Section 1.2. Neither call path touches `recipes/_kbhbrew/`.

**Q4 — What happens to brewday widget state when the user changes
active recipe, selects another saved recipe, imports a recipe, creates
a new brew, or reopens history?**
- **Changing/loading another saved recipe** (`ui/sidebar.py:68-139`):
  overwrites `valgt_malt`/`valgt_humle`/`valgt_gjaer_id`/
  `gjeldende_navn`/efficiency/passthrough/process-profile/water
  session-state keys, then `st.rerun()`. It **never touches any
  `bd_*` key or `_aktiv_kbhbrew_brew_id`** — confirmed by grep across
  `ui/sidebar.py`. So `bd_og`, `bd_fg`, etc. silently **survive** a
  recipe switch, still showing whatever was typed for the *previous*
  recipe, now displayed underneath a different recipe's header/target
  values (`ctx['og']`/`ctx['fg']` in the field labels update, but the
  typed actual value does not clear).
- **Importing a recipe** (text import `apply_import_to_session_state`,
  or `.kbhrecipe` import `apply_kbhrecipe_import_to_session_state`):
  same story — neither touches `bd_*` (not read in this audit's grep
  of those two modules' session-state writes beyond recipe/ingredient
  fields).
- **Creating a new brew** (`ui/kbhbrew_panel.py:83-111`): does not
  touch any `bd_*` key either. `bd_og` typed *before* clicking "▶️
  Start nytt brygg" is simply not part of what gets frozen (correctly
  — `bygg_predicted_fra_ctx(ctx)` only reads `ctx["og"]`, the
  *planned* OG, never `bd_og`; see `modules/kbhbrew_ui.py:71-77`).
- **Reopening history** (`ui/kbhbrew_history_panel.py`): re-renders
  the actuals form pre-filled from **the stored brew's own
  `actuals`**, not from `bd_*` (`ui/kbhbrew_history_panel.py:134-146`)
  — this path is internally self-consistent, it simply never receives
  anything from Steg 4.

**Q5 — Is there any path where measurements can be visually associated
with recipe A while persisted to brew B, or simply remain
unpersisted?**
Both, and confirmed:
- **Simply remain unpersisted**: any value entered in Steg 4/5
  (`bd_og`, `bd_fg`, `bd_pitch_temp`, `bd_transfer_note`, …) — proven
  in Q3.
- **Visually associated with the wrong brew is also possible**, in the
  *History* form specifically: `kbhbrew_historikk_valgt_id`
  (`ui/kbhbrew_history_panel.py:334-339`) is a free-standing selectbox
  with no relationship to the currently loaded recipe (`ctx`) or to
  `_aktiv_kbhbrew_brew_id`. A user mid-way through recipe A's brewday
  tab can select an *older* brew (e.g. from recipe C, brewed weeks
  ago) in that dropdown and save actuals there, while the rest of the
  tab (Steg 1-6, header) still visually displays recipe A's plan. The
  widget keys are correctly brew-scoped (`f"...::{brew_id}"`,
  `ui/kbhbrew_history_panel.py:24` docstring + line 135 etc.) so no
  *typed text* leaks between brews — but the *selection itself* is
  never validated against "the brew the rest of this tab is about".

**Q6 — How are snapshot immutability and actuals mutation separated
today?**
Cleanly, by function signature: `oppdater_brew_lag()` has no
`snapshot` parameter at all (Section 1.4). This is a proven-safe path,
not a trust break, and A1 must preserve it exactly as-is.

**Q7 — What current UI feedback tells the user whether a measurement
was persisted?**
Only `st.success(t("brew_history.lagret_ok"))`
(`ui/kbhbrew_history_panel.py:200`) after the History form's own
"💾 Lagre målte verdier" click, and the equivalent
`brew_history.sensing_learning_lagret_ok` toast for the sensing/
learning form (`ui/kbhbrew_history_panel.py:264`). **Steg 4/5 of the
brewday sheet give no save-state feedback at all**, because they have
no save action — there's no error either, which is the trust break:
a user can reasonably believe typing OG into the field literally
labelled "OG (mål: …)" under the Brewday tab has "saved" it, with
nothing telling them otherwise until/unless they separately understand
the History panel is a different, second entry surface.

**Q8 — Which fields belong in A1: OG, FG, actual volume(s), brewedAt,
transfer note, or a smaller set? Distinguish MUST from later polish.**
See Section 6.

**Q9 — What is the smallest safe implementation boundary?**
See Section 7 (recommendation).

## 3. Exact files/functions/session-state keys involved

| Concern | File | Symbol / key |
|---|---|---|
| Brewday transfer widgets (unbound) | `ui/brewday_panel.py` | `bd_og`, `bd_fg`, `bd_abv`, `bd_pitch_temp`, `bd_transfer_note`, `bd_pre_boil_vol`, `bd_pre_boil_sg`, `bd_post_boil_vol` (session-state keys, `_BD_DEFAULTS` at lines 17-31 + ad-hoc widget defaults) |
| Brewday tab composition | `ui/brewday_panel.py` | `render_brewday_panel()` (line 34), calls `render_kbhbrew_create_panel()` (line 91), `render_kbhbrew_history_panel()` (line 92) |
| New-brew creation + session pointer | `ui/kbhbrew_panel.py` | `render_kbhbrew_create_panel()`, `_AKTIV_BREW_ID_NOKKEL = "_aktiv_kbhbrew_brew_id"` (line 52), set at line 110 |
| Ingredient-preflight helper | `modules/kbhbrew_ui.py` | `manglende_ingrediens_ider()`, `bygg_predicted_fra_ctx()` |
| Brew engine (pure) | `modules/kbhbrew.py` | `bygg_ny_brew()`, `bygg_ny_brew_snapshot()` (never mutated after creation), `normaliser_actuals_lag()` |
| Local storage/identity | `modules/kbhbrew_storage.py` | `opprett_og_lagre_ny_brew()` (mints `brewId`), `oppdater_brew_lag()` (actuals/sensing/learning/status/brewedAt only, never snapshot), `hent_brew()`, `hent_alle_brews()` |
| Actuals-entry UI (wired, but disconnected from Steg 4) | `ui/kbhbrew_history_panel.py` | `render_kbhbrew_history_panel()`, brew picker `kbhbrew_historikk_valgt_id` (line 338), actuals widgets `kbhbrew_hist_{og,fg,volum,brygget_dato,status,notes}::{brew_id}`, save click `kbhbrew_hist_lagre_btn::{brew_id}` (line 173) → `oppdater_brew_lag()` (line 189) |
| Strict numeric validation for manual actuals typing | `modules/kbhbrew_history_ui.py` | `parse_actual_tallfelt()` |
| Recipe selection/switch (does not touch `bd_*`/brew pointer) | `ui/sidebar.py` | `render_sidebar()`, writes `valgt_malt`/`valgt_humle`/`valgt_gjaer_id`/`gjeldende_navn`/`_last_loaded_recipe_file`/etc. (lines 68-139) |
| Recipe→recipe_id link for new brews | `ui/kbhbrew_panel.py:105` | `recipe_id=st.session_state.get("_last_loaded_recipe_file")` |
| Central recipe context (rebuilt every rerun, every tab) | `app.py` | `bygg_recipe_context()` call at line 143, before `tab_bryggdag` renders (line 175-180) |

## 4. Recommended active-brew identity contract for the App

The roadmap contract requires "one active brew / measurement binding".
Given Section 1-3, the recommendation is to **promote
`_aktiv_kbhbrew_brew_id` from a display-only session pointer to the
single source of truth for "which brew Steg 4/5/History write to"**,
rather than inventing a second, parallel concept:

1. Rename its role (not necessarily its literal key, to minimize
   blast radius) to mean: *the brew that Steg 4 OG/FG/volume/transfer
   fields and the History actuals form both target, for this
   session*.
2. Set it in exactly the two places that should define "active":
   - "▶️ Start nytt brygg" (already sets it today — keep).
   - An explicit user action in the History panel equivalent to
     "make this the active brew" (new — see Section 5) OR, more
     conservatively for A1, simply **remove the independent History
     picker's own default and instead pre-select/lock it to
     `_aktiv_kbhbrew_brew_id` whenever one exists**, while still
     allowing the user to explicitly pick a different (e.g. older)
     brew if they intentionally want to record a late measurement —
     that explicit pick should then *update*
     `_aktiv_kbhbrew_brew_id`, not silently diverge from it.
3. Never infer "active" from the loaded *recipe* — a recipe can have
   many brews (explicitly supported, `ui/kbhbrew_panel.py:80-81`:
   "Hvert klikk oppretter et NYTT batch"), so recipe identity must
   never be conflated with brew identity, and switching recipes (Q4)
   must not silently retarget an in-progress brew's measurements.
4. `_aktiv_kbhbrew_brew_id` should **not** survive a recipe switch
   silently associated with the new recipe's context — it should
   either (a) be explicitly cleared when the loaded recipe's
   `recipeId` no longer matches the active brew's own `recipeId`
   (matches "switching active recipe never moves measurements to
   another brew"), or (b) remain associated with its own brew but the
   UI must clearly show "active brew: <recipe X, batch date>" so it's
   never mistaken for belonging to the recipe currently on screen.
   Recommendation: **(a)**, since (b) 's ambiguity is exactly what Q5
   already proves is confusing today.

## 5. Exact persistence/readback contract

For any field A1 wires (see Section 6 for which):

- **Write**: only via `modules/kbhbrew_storage.py::oppdater_brew_lag()`
  — no new write path. An explicit, single Streamlit `st.button(...)`
  click remains the only trigger (established, tested pattern — see
  `ui/kbhbrew_history_panel.py:173`/`258` and the existing
  "rendering/typing writes nothing" guarantee already covered by
  `tests/test_kbhbrew_history_panel_apptest.py`). Steg 4 must **not**
  gain an auto-save-on-rerun behavior — that would be a new, untested
  state pattern and contradicts the repo's established
  "explicit-click-only" convention (`ui/kbhbrew_panel.py:70-72`,
  `ui/kbhbrew_history_panel.py:15-17`).
- **Read/prefill**: Steg 4/5 widgets, if merged with the History
  actuals form (Section 7 option A) or kept separate but bound
  (option B), must prefill from `hent_brew(brew_id)["actuals"]`
  exactly like `ui/kbhbrew_history_panel.py:132-148` already does —
  never fabricate a default (same "aldri en gjettet default"
  principle already documented at
  `ui/kbhbrew_history_panel.py:26-30`).
- **Validation**: reuse `modules/kbhbrew_history_ui.py::
  parse_actual_tallfelt()` unchanged for any numeric actual typed
  directly by a human (not the JS-parseFloat-tolerant
  `normaliser_actuals_lag()`, which is for import/legacy tolerance
  only — this distinction is already deliberate, see
  `modules/kbhbrew_history_ui.py:32-45`).
- **No new `.kbhbrew` schema fields.** Every field A1 needs (`og`,
  `fg`, `volumeL`, `notes`) already exists in `_KJENTE_ACTUALS_FELT`
  (`modules/kbhbrew.py:67`). `transferNote`/`pitchTemp` are **not**
  currently modeled in the Core `.kbhbrew` V1 actuals schema
  (`core/kbhbrew_v1.schema.json` — only `og`/`fg`/`volumeL`/`notes`
  are known actuals fields); mapping `bd_transfer_note` would need to
  go into the existing free-text `notes` field, not a new wire field
  (a genuinely new Core-contract field is out of scope for an App-only
  A1 change — Core is governed separately, see
  `docs/development/KBH_CORE_CONTRACT.md`).

## 6. Field scope — MUST vs. later polish

Per the roadmap contract text ("OG entered during transfer is stored
on the selected/active brew; … FG and actual volume follow the same
ownership rule where applicable"):

**MUST (A1 core):**
- `og` (Steg 4) — the contract's own headline example.
- `fg` (Steg 5) — explicitly named in the roadmap contract.
- Actual volume — the contract says "actual volume(s) … where
  applicable"; the existing `.kbhbrew` schema only has one actual
  volume field (`volumeL`), post-boil is the more meaningful single
  value to bind (pre-boil is a process-control reading feeding the
  *plan*, not a batch-level actual worth freezing per brew). Recommend
  binding **post-boil volume only** (`bd_post_boil_vol`) to
  `actuals.volumeL`, and leaving pre-boil volume/SG as brewday-sheet-
  only process data (they already have no `.kbhbrew` actuals
  equivalent field at all).
- `brewedAt` — already a first-class `.kbhbrew` field
  (`brew["brewedAt"]`, settable via `oppdater_brew_lag(...,
  brewed_at=...)`) and already surfaced in the History form
  (`ui/kbhbrew_history_panel.py:152-156`); A1 should make sure Steg 4/
  5's own date inputs (`bd_dato`, batch date) don't *also* silently
  duplicate this without binding it, to avoid recreating the same
  problem for a fourth field.

**Later polish (explicitly NOT A1, per issue's own MUST/polish
split):**
- `bd_transfer_note` → would require overloading the single `notes`
  actuals field or a Core contract change — defer.
- `bd_pitch_temp`, mash/boil-observation temps
  (`bd_mash_temp_1/2/3`), Inkbird temp, fermentation pressure — none
  have any `.kbhbrew` actuals-schema equivalent today; adding them is
  a Core-contract-scope decision, not an App-wiring fix.
- Reconciling/merging the *sensing/learning* form (already fully
  wired, Section 1.3) with Steg 5's gjæring fields — out of scope,
  already functions correctly as its own flow.

## 7. Bounded implementation options + recommendation

**Option A — Merge Steg 4/5 measurement fields into the existing
History actuals form's data path** (bind Steg 4/5 widgets' values to
write through the *same* `oppdater_brew_lag()` call, gated on
`_aktiv_kbhbrew_brew_id` being set, with its own explicit save action
near Steg 4/5 rather than requiring the user to scroll back up to the
History panel). Removes the duplicate-entry UX entirely. Larger diff:
touches widget layout/flow in `ui/brewday_panel.py` non-trivially.

**Option B — Keep the two forms visually separate but bind identity**:
leave Steg 4/5 exactly as free-typed fields for *live, in-session*
display/effektivitet/print-sheet purposes (their current, working
role), and make the *History* panel default/lock its selector to
`_aktiv_kbhbrew_brew_id` (Section 4, point 2) plus add a clear
one-line UI hint at Steg 4 ("target brew: <label>, edit/save actuals
below ↓") linking down to the History form. Smaller diff, but the
duplicate-typing UX papercut remains (softened, not eliminated).

**Option C — Do nothing to Steg 4/5; only fix the History picker's
default binding** (Section 4 point 2 alone). Smallest possible diff,
fixes Q5's "wrong brew" risk, but does not address Q3's "no path at
all" gap, which is the more serious of the two findings.

**Recommendation: Option A**, because the roadmap contract's own
language ("OG entered **during transfer**") specifically describes
Steg 4's real-time entry moment, not a separate after-the-fact form —
Option B/C leave that moment un-persisted, which is the actual trust
break this preflight found. Option A is bounded: it reuses the
existing `oppdater_brew_lag()` write path, the existing
`parse_actual_tallfelt()` validation, and the existing brew-scoped
widget-key suffixing pattern (`::{brew_id}`) verbatim — no new
persistence mechanism, no Core contract change, no new state pattern
beyond what Section 4 already establishes.

## 8. Recipe-switch / reopen / import edge cases (acceptance-relevant)

| Scenario | Current behavior | Required A1 behavior |
|---|---|---|
| User types OG in Steg 4, never clicks any save | Nothing persisted (today, always) | Nothing persisted (must remain non-destructive; only an explicit click writes) |
| User types OG in Steg 4, clicks new Steg 4/5 save (Option A) | N/A | Writes to `_aktiv_kbhbrew_brew_id`'s `actuals.og` only if that id is set and resolves via `hent_brew()`; if unset, block with a clear error (mirrors the existing equipment/ingredient preflight pattern at `ui/kbhbrew_panel.py:87-99`) — never silently no-op |
| User switches active recipe mid-brewday (sidebar) | `bd_*` values persist unchanged, now shown under a different recipe's header (Q4/Q5) | `_aktiv_kbhbrew_brew_id` must be cleared/invalidated when the newly loaded recipe's identity no longer matches the active brew's `recipeId` (Section 4 point 4); Steg 4/5 fields should not misleadingly imply they still target the old brew |
| User imports a new recipe (text or `.kbhrecipe`) | Same as above | Same rule as recipe switch |
| User creates a second new brew from the same recipe (explicitly supported) | `_aktiv_kbhbrew_brew_id` updates to the new brew; any *unsaved* Steg 4 text remains, now implicitly retargeted | Unsaved Steg 4 text must be clearly re-scoped or cleared per the widget-reset-version-key pattern (`PROJECT_MAP.md` "Etablerte state-mønstre") keyed on `_aktiv_kbhbrew_brew_id`, so a stale typed value can never be silently attributed to the new brew |
| User reopens History and manually picks an older brew | Actuals form correctly shows that older brew's own stored actuals (already correct) | If Option A is adopted, an explicit pick here should also update `_aktiv_kbhbrew_brew_id` so Steg 4/5 and History never disagree about the target brew afterward |
| Frozen snapshot vs. actuals | Already correctly separated (Section 1.4/Q6) | Must remain unchanged — A1 adds no new snapshot-mutation path |

## 9. Snapshot/actuals invariants (must hold after A1)

- `oppdater_brew_lag()` must continue to never accept/write a
  `snapshot` argument.
- Every actuals write remains a **merge**, not a replace
  (`{**gjeldende, **endringer}`, `modules/kbhbrew_storage.py:231`) —
  A1's new Steg 4/5 write path must reuse `oppdater_brew_lag()`
  directly rather than re-implementing merge semantics.
- `FORBUDTE_ACTUALS_EKSPORTFELT` (`abv`/`actual_abv`/`actualAbv`,
  `modules/kbhbrew.py:87`) remains enforced at export — A1 must not
  attempt to persist `bd_abv` as a wire field (it's a derived display
  value only, consistent with existing Core policy #3).
- DEMO_MODE must remain a hard no-op for any new write path, exactly
  like every existing `.kbhbrew` write
  (`opprett_og_lagre_ny_brew`/`oppdater_brew_lag`/`importer_kbhbrew`
  all check `DEMO_MODE` first).

## 10. UI save-state feedback requirement

Whichever option is chosen, A1 must close the Q7 gap: the moment a
user leaves Steg 4/5 without having triggered any write, the UI must
make that state legible — either (a) a persistent "not yet saved to
`<brew>`" indicator distinct from the History form's existing
`st.success`, or (b) Option A's merged save button co-located with the
fields themselves, removing the ambiguity structurally rather than
via a warning label. Recommendation: (b), as a natural consequence of
Option A (Section 7) — no separate "unsaved" state machine needs to be
invented if the save action is right where the field is.

## 11. Focused test plan (unit/AppTest/browser-equivalent)

No browser/E2E harness exists in `tests/` (testing.md) — everything
below is `AppTest`/unit-level, following the exact existing patterns:

- **Unit** (pure, no Streamlit): if any new helper is added (e.g. "is
  this recipe's `recipeId` the active brew's own `recipeId`"), it
  belongs in a `modules/*_ui.py`-style pure module and gets its own
  `tests/test_*_helpers.py`, mirroring
  `modules/kbhbrew_history_ui.py` / `tests/test_kbhbrew_history_ui_helpers.py`.
- **AppTest — new/extended, mirroring
  `tests/test_kbhbrew_history_panel_apptest.py`'s existing "dangerous
  state boundaries" list**:
  1. Typing into Steg 4 OG without any save click writes nothing to
     disk (rerun-only assertion, `hent_alle_brews()` unchanged).
  2. One explicit Steg 4/5 save click updates exactly the active
     brew's `actuals`, preserves `brewId`/`originBrewId`/`recipeId`/
     the entire frozen `snapshot` (mirrors the History AppTest's own
     assertion #5).
  3. No operation in Steg 4/5 or the create panel creates a second,
     unintended brew.
  4. Switching the loaded recipe (via the sidebar harness pattern) is
     asserted to clear/invalidate `_aktiv_kbhbrew_brew_id` when
     `recipeId` no longer matches (Section 8 row 2/3) — extend
     `tests/_brewday_panel_app.py`-style harness or add a new fixture
     under `tests/fixtures/streamlit_harness/`.
  5. Creating a second brew from the same recipe re-targets
     `_aktiv_kbhbrew_brew_id` and any stale unsaved Steg 4 text is
     provably not attributable to the new brew (widget-reset-version
     assertion).
  6. DEMO_MODE: new write path is a no-op, exactly like
     `test_oppdater_brew_lag_is_a_noop_in_demo_mode`
     (`tests/test_kbhbrew_storage_identity.py:282`).
  7. Legacy `recipes/_logs/` remains untouched (mirrors existing
     assertion #9 in `test_kbhbrew_history_panel_apptest.py`).
- **Existing regression suites that must stay green through A1**:
  `tests/test_kbhbrew_storage_identity.py`,
  `tests/test_kbhbrew_history_panel_apptest.py`,
  `tests/test_kbhbrew_create_panel_apptest.py`,
  `tests/test_brewday_tab_ux_cleanup.py`,
  `tests/test_brewday_export_hop_mismatch.py`,
  `tests/test_brewday_print_pagination.py` — none of these are
  expected to need behavior changes from this preflight alone, but any
  A1 implementation PR must run the full suite per `testing.md`.

## 12. Non-goals (explicit)

- No new Core `.kbhbrew` V1 wire fields (transfer note, pitch temp,
  mash observations) — Core-contract scope, separate authorization.
- No Web/Bryggeskole/Sóti changes.
- No change to the already-correct snapshot-immutability mechanism.
- No auto-save-on-rerun behavior anywhere (violates the repo's
  established explicit-click-only write pattern).
- No redesign of the sensing/learning form (`_render_sensing_learning_skjema`) — already correctly scoped and wired.
- No migration of existing stored `.kbhbrew` brews or historical
  brewday-sheet exports.
- No decision here on whether `_aktiv_kbhbrew_brew_id` should also
  survive a full app restart (persisted, not just session-state) —
  flagged as an open question for the implementation issue, not
  resolved by this preflight.

## 13. One implementation issue, or split?

**Recommend one implementation issue**, scoped to Option A (Section 7)
plus the recipe-switch invalidation rule (Section 4 point 4 / Section
8), because:

- The core fix (wiring Steg 4/5 to `oppdater_brew_lag()`) and the
  identity-invalidation rule are **not independently shippable** —
  wiring the write path without the invalidation rule would actively
  make Q5's "wrong brew" risk *worse* (a newly-reachable write path
  with no recipe-switch guard), and the invalidation rule alone
  (Section 4 point 4) without the write path leaves Q3's core gap
  unaddressed.
- Both changes touch the same files (`ui/brewday_panel.py`,
  `ui/kbhbrew_panel.py`, possibly `ui/kbhbrew_history_panel.py`'s
  selector default) and the same session-state contract
  (`_aktiv_kbhbrew_brew_id`), so splitting them would mean two PRs
  each partially reviewing the other's precondition.
- The *later-polish* fields (Section 6) are already cleanly separable
  and should be their own, subsequent issue(s) if/when prioritized —
  but that split is about field scope, not about splitting A1's core
  binding fix itself.

## 14. STOP

Per issue #155's Delivery section: this is a docs-only analysis PR.
No `app.py`/`ui/**`/`modules/**` product behavior was modified. A1
implementation does not start automatically from this preflight.
