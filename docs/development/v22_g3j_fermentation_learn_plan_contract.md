# V2.2 Goal 3J — Gjæringstemperatur Learn → Plan bridge contract

Version: 1.1
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#382](https://github.com/Joludvig/kvernhaug-brygghus/issues/382), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3),
accepted gap ordering [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358),
Mesking Learn→Plan precedent [#344](https://github.com/Joludvig/kvernhaug-brygghus/issues/344) /
[#352](https://github.com/Joludvig/kvernhaug-brygghus/issues/352),
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction)
Authoritative base at creation: `43d2b895f075939b6c4a6cb03cbcd06ee2611717`

This is a decision/prep document only. It contains **no product implementation** — see
[Hard non-goals](#hard-non-goals). Chief must review this contract before any implementation
child issue is opened.

---

## 1. Current-state audit

### 1.1 `bryggeskole/data/course_fact_registry.json` — Gjæringstemperatur-relevante verified records

| ID | Classification | Status | Claim (summarized) |
|---|---|---|---|
| `FACT-BREW-0001` | `documented_fact` | `verified` | Fermentation temperature affects yeast activity/speed; within a strain's workable range, warmer generally means more active yeast and can shorten fermentation. General direction, not a universal rule. |
| `FACT-BREW-0002` | `documented_fact` | `verified` | Temperature can change yeast-derived flavor/aroma, but size and direction are strain-dependent — a warmer fermentation does not produce the same flavor response in every strain. |
| `FACT-BREW-0003` | `professional_interpretation` | `verified` | Fermentation temperature targets should be chosen with strain-specific guidance, not a universal ale/lager rule. |

All three are consumed unmodified by `bryggeskole/data/pilot_fermentation_temperature.json` (`CHUNK-FERM-A/B/C`, `Q-FERM-001/002`) via `bryggeskole/pilot_fermentation.py`'s verified-only `source_claims` resolution (same `get_verified_record` boundary as Mesking, per
[BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) §18). The pilot chunk text is already hedged and strain-scoped — `CHUNK-FERM-C` states the exact instruction this bridge needs to reinforce: choose temperature "ut fra anbefalingen for akkurat den gjærstammen du bruker — ikke ut fra en generell tommelfingerregel om at 'ale skal gjæres varmt' eller 'lager skal gjæres kaldt'."

Unlike the Mesking precedent (which used only `CHUNK-MASH-B/C` of three available chunks), **all three fermentation chunks are directly load-bearing for this task** — A explains the mechanism (why temperature matters at all), B explains the strain-dependent flavor risk, and C is the direct behavioral instruction ("use strain-specific guidance, not a universal rule") that this bridge's persistence contract (§8) must not silently contradict with a guessed default.

### 1.2 `bryggeskole/pilot_fermentation.py`

Pure, stdlib-only, fail-closed pilot-content validator/renderer, architecturally identical to `bryggeskole/pilot_mashing.py`. Exposes `read_pilot_file()`, `render_chunk(chunk, language)`, `render_question(question, language)`, `evaluate_answer(question, selected_option_id, language)`. No Streamlit dependency, no persistent mastery state — safe to call from `ui/yeast_panel.py` exactly as `ui/process_panel.py` already calls `pilot_mashing` (§1.5).

### 1.3 `ui/bryggeskole_panel.py`

Already imports this exact module as `_pilot_gjaring` (`ui/bryggeskole_panel.py:95`) and renders a full "Gjæring" Bryggeskole module with its own mastery state (`st.session_state["bs_modul_sesjon"]["gjaering"]`, or whichever module id is registered). That flow is fully self-contained and disjoint from the App's recipe/yeast-selection session state — nothing there reads or writes the yeast panel today, and this bridge must not change that (§7.1's "no mastery interaction" rule, mirrored from Mesking, applies identically here).

### 1.4 `ui/yeast_panel.py` — exact current state

52 lines total. `render_yeast_panel(gjaer_database)` (line 3):

- Renders a header, a static intro `st.expander` (starter/health copy, hardcoded Norwegian — no i18n at all currently, see below),
- A yeast `st.selectbox` writing `st.session_state.valgt_gjaer_id` (lines 15–43),
- A caption showing flavor tags + attenuation for the selected strain (lines 44–52).

**No target fermentation-temperature field exists.** **No Learn→Plan bridge exists.** `ui/yeast_panel.py` has **zero `ui.i18n` usage** (`import streamlit as st` is its only import, line 1) — every string is a hardcoded Norwegian literal. This is a pre-existing gap this task does not fix wholesale (§10) — but any *new* copy this bridge adds must use `t()`/`ui.i18n`, matching the Mesking precedent (`ui/process_panel.py:11`), not extend the hardcoded-string pattern further.

Called from `app.py:149`, inside `tab_oppskrift`, immediately after `render_hop_panel` and immediately **before** `bygg_recipe_context()` is invoked (`app.py:152–160`) — i.e. before the recipe object for this render is built. This is exactly the "strong candidate" placement the issue names, and the audit confirms no better existing planning surface exists (§1.7 below rules out `recipe_card.py`/`sidebar.py` as the *editing* surface).

### 1.5 `ui/process_panel.py` — the exact, already-implemented Learn → Plan precedent

Issue #352 already shipped this pattern for Mesking, so this document reuses its mechanics verbatim rather than re-deriving them:

```python
from bryggeskole import pilot_mashing as _pilot_mesking
from ui.i18n import gjeldende_sprak, t
...
def _render_laer_bro(sprak):
    with st.expander(t("prosess.laer_bro.tittel"), expanded=False):
        try:
            pilot = _pilot_mesking.read_pilot_file()
        except _pilot_mesking.PilotContentError:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return
        chunker = {c["id"]: c for c in pilot["chunks"]}
        for chunk_id in _LAER_BRO_CHUNK_IDER:
            st.markdown(_pilot_mesking.render_chunk(chunker[chunk_id], sprak)["text"])
        st.caption(t("prosess.laer_bro.footer"))
```
(`ui/process_panel.py:134–150`, called as `_render_laer_bro(gjeldende_sprak())` at line 266.)

i18n keys live in `modules/i18n.py:214–215` (NO) and `:373–374` (EN) — `prosess.laer_bro.tittel` / `prosess.laer_bro.footer`.

### 1.6 `data/master_gjaer_v2.json`

Confirmed structure per entry (e.g. `lalbrew_house_ale`, `bohemian_lager_m84`): `display_name`, `produsent`, `kategori`, `gjaertype`, `smakstags`, `attenuation`, `aliases`, `butikk_match`, `verified`, `source`. **No temperature-range field of any kind exists on any of the 103 entries** — a targeted search for any key containing "temp" across the whole file returns zero matches. A verified per-strain temperature range would be a first-time schema addition here, not an extension of an existing field, and is explicitly not attempted by this document (§10/Hard non-goals — no yeast masterdata mutation, no scraping/import of manufacturer ranges).

### 1.7 Recipe object shape and the four persistence surfaces

`modules/recipe.py::bygg_recipe_object()` builds the App's internal Recipe Object as one flat dict (lines 81–102): `name`, `batch_size`, `efficiency`, `brygger_stil`, `malts`, `hops`, `yeast`, `stats`, `flavor_profile`, `process_profile`, `water_source_profile`, `water_target_profile`, `water_treatment`, `water_measurements`, plus conditionally `_kbh_passthrough`/`originRecipeId`. There is **no existing fermentation-temperature planning field anywhere** in this dict, in `ui/recipe_card.py`, in `ui/sidebar.py`'s load path, or in the `.kbhrecipe`/`.kbhbrew` schemas (all confirmed by direct audit below).

The four persistence surfaces named in the governing issue behave very differently, and the difference is load-bearing for §8's decision:

**(a) Local recipe save/load — `modules/recipe_storage.py`.** `lagre_oppskrift()` (`modules/recipe_storage.py:398–477`) writes the *entire* Recipe Object dict verbatim via `_skriv_json_atomisk(filsti, recipe)` (line 473) → plain `json.dump`, no field allow-list. Load (`_skann_oppskriftsfiler()`, lines 685–714) does `json.load` and returns the dict verbatim, requiring only `"name"` to be present. **This layer round-trips any new top-level key automatically, with zero code changes to `recipe_storage.py` itself** — it is a pure pass-through container, unlike (b)/(c) below.

**(b) `.kbhrecipe` export/import — `modules/kbh_contract.py` / `modules/kbh_import.py`.** This is an explicit, field-by-field whitelist, stated as a hard rule in [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §5–§6: "Both writers build the payload field by field, from an explicit known-field list — never by copying or spreading a whole source object into the file." `recipe_to_kbhrecipe_payload()` (`modules/kbh_contract.py:150–236`) only ever writes `navn`/`volum`/`effektivitet`/`malt`/`humle`/`gjaerId`/`bryggerStil`/`prosess`/`vann`/`originRecipeId` — a brand-new Recipe Object key it never explicitly reads is **silently dropped** on export. The `_kbh_passthrough` mechanism does **not** rescue this: it is populated only from unknown keys found in an *incoming imported* `.kbhrecipe` file (`modules/kbh_import.py::_bygg_passthrough()`, lines 442–469), never from the App's own local Recipe Object fields — `CORE_KBHRECIPE_V1.md` states this explicitly: "Passthrough exists for data that arrived from outside... it is not a channel for [the app's] own local metadata." Adding a new field to this layer requires an explicit, separately-justified schema addition on both `_KJENTE_PAYLOAD_FELT` sets (`kbh_contract.py:39–43`, mirrored in `kbh_import.py:65–69`) plus explicit read/write code — exactly the "Core/schema extension" the issue's guardrail says must not be assumed necessary.

**(c) `.kbhbrew` historical snapshot — `modules/kbhbrew.py`.** `bygg_ny_brew_snapshot()` (lines 310–350) builds its `recipe` sub-object by calling `recipe_to_kbhrecipe_payload(recipe)` directly (line 337) — i.e. it **inherits (b)'s exact whitelist**. A field not added to (b) cannot appear in (c) either, and no separate code change is needed to keep it out.

**(d) `ui/recipe_card.py` — the existing pattern for a new optional planning field.** `_bygg_recipe_fra_session()` (lines 147–183) is the concrete, repeated model:

```python
process_profile=st.session_state.get("aktiv_prosessprofil"),
water_source_profile=st.session_state.get("aktiv_vannkilde_snapshot"),
water_target_profile=st.session_state.get("aktiv_vannmaal_snapshot"),
water_treatment=st.session_state.get("aktiv_vannbehandling"),
water_measurements=st.session_state.get("aktiv_vannmaalinger"),
```
(`ui/recipe_card.py:163–167`) — read a dedicated session-state key, pass it straight through as a `bygg_recipe_object()` keyword argument, which stores it unconditionally (default `None`) on the Recipe Object dict. `modules/recipe_context.py:89–93` rebuilds the same fields for the *live calculation* object on every render. **Both call sites must be updated identically** for a new field to be visible in both the live UI and the saved/exported recipe — exactly as `water_treatment` needed both when it was added.

### 1.8 `ui/sidebar.py` — the "missing field → `None`, never guessed" load pattern

The exact proof the issue asks for, `ui/sidebar.py:172`:

```python
st.session_state["_aktiv_recipe_efficiency"] = resolve_recipe_efficiency(r_data.get("efficiency"))
```

`resolve_recipe_efficiency()` (`modules/recipe.py:13–34`) returns `None` for anything not a genuine positive, non-NaN number — a recipe missing the key, or an older recipe predating it, yields `None`, never a guessed value; `modules/recipe_context.py:21–26` treats `None` as "no override" and falls back to a live default. The same "set unconditionally on every load, `dict.get` default, never fabricate" pattern repeats for every other optional field at `ui/sidebar.py:172–222` (`_aktiv_kbh_passthrough`, `originRecipeId`, `process_profile` via `normaliser_prosessprofil()`, all four `water_*` snapshots). This is the exact template §6/§7 below reuse for the new field.

---

## 2. Exact selected user task

While a learner has selected a yeast strain in `ui/yeast_panel.py`, they can open a small, collapsed "why does fermentation temperature matter" bridge showing the existing, verified Gjæring fundamentals (`CHUNK-FERM-A/B/C`, unchanged), and — independently of whether they open it — deliberately type a planned target fermentation temperature (°C) into a new, optional numeric field on the same panel. An explicit, adjacent note states that Kvernhaug does not store verified per-strain temperature ranges, so the learner should follow the guidance for their specific selected strain/manufacturer rather than a generic ale/lager rule. That value is unset by default, is never derived from `gjaertype`/category/flavor tags, and saves and reopens with the rest of the recipe through the existing local save/load path.

This is deliberately the cheapest possible instance of Learn → Plan, mirroring §6 of the Mesking precedent: it does not gate, validate, or auto-set anything, and the mechanism of "type a number into a field" is unchanged — the bridge only adds an optional, in-context "why," and the field only adds an optional, deliberate "what."

---

## 3. Verified source/chunk reuse map

| Bridge element | Reuses |
|---|---|
| Mechanism explanation ("why does temperature matter") | `CHUNK-FERM-A` / `FACT-BREW-0001`, unchanged |
| Flavor/strain-dependence warning | `CHUNK-FERM-B` / `FACT-BREW-0002`, unchanged |
| "Use strain-specific guidance, not a universal ale/lager rule" instruction | `CHUNK-FERM-C` / `FACT-BREW-0003`, unchanged |

No new Course Fact Registry record is proposed. No new teaching copy is authored anywhere in `ui/yeast_panel.py` — every sentence the bridge shows already exists, verified, in `bryggeskole/pilot_fermentation.py`'s pilot content, rendered via its own unmodified `render_chunk()`. The one genuinely new piece of copy is the *guardrail note* next to the numeric field itself ("Kvernhaug does not know the correct range for your selected strain — follow your strain/manufacturer's guidance"), which is App UI copy, not a Course Fact Registry claim, exactly parallel to how `ui/process_panel.py`'s own subheader caption ("Prosessprofilen beskriver HVORDAN...") is App copy sitting alongside, not inside, the reused chunks.

---

## 4. UI placement decision

**Chosen: inside `render_yeast_panel()` in `ui/yeast_panel.py`, directly below the existing flavor/attenuation caption (after current line 52)** — the exact "strong candidate" the issue names, confirmed correct by §1.4/§1.7: this is the only surface where yeast selection, the recipe-build call, and the save/load path all meet before the recipe object for the render is constructed. No better existing planning surface was found in `ui/recipe_card.py` (pure plumbing/save-export UI, §1.7d) or `ui/sidebar.py` (load-time hydration only, never an editing surface, §1.8).

Two new elements, in this order:

1. **A collapsed `st.expander` Learn→Plan bridge**, placed first (immediately below the flavor/attenuation caption), showing `CHUNK-FERM-A`, `CHUNK-FERM-B`, `CHUNK-FERM-C` in that order — mirroring `_render_laer_bro()` (`ui/process_panel.py:134–150`) exactly: same `try`/`except PilotContentError` fallback (`st.error(t("bryggeskole.feil.innhold_ugyldig"))`, reusing the existing shared error key rather than minting a new one), same `read_pilot_file()`/`render_chunk(chunk, sprak)` calls, same "no mastery interaction" rule (§1.3), same footer caption pointing at the full Bryggeskole Gjæring module as plain text (no working cross-tab jump — same rationale as §7.0 of the Mesking contract: no reliable programmatic tab-switch exists for a bridge this small to justify building one).
2. **A new `st.number_input` for the planned target temperature**, placed directly below the bridge, with a `help=`/caption explicitly stating the guardrail from §2 — an unset value (see §6) renders as an empty field, never a pre-filled number, so a learner can never mistake a placeholder for a recommendation (issue's own "critical guardrail" requirement).

**Why the bridge is placed above the field, not below:** the learner should encounter *why* temperature matters and *why no universal number exists* immediately before being asked to commit to a number — the same "teaching immediately before the deliberate choice" placement principle used for the Mesking bridge (`ui/process_panel.py:134` sits directly above the mash-step editor), adapted to this panel's simpler, single-field control instead of a multi-step editor.

**i18n note (new, since this precedent differs from Mesking's):** `ui/yeast_panel.py` currently has zero `ui.i18n` usage (§1.4). This bridge's implementation child must add `from ui.i18n import gjeldende_sprak, t` to `ui/yeast_panel.py` and add exactly the new strings this bridge needs (bridge title/footer, field label/help, guardrail caption) to `modules/i18n.py`'s NO and EN blocks — following the `prosess.laer_bro.*` key-naming precedent (e.g. `gjaering.laer_bro.tittel`/`.footer`, `gjaering.temp_maal.label`/`.hjelp`). It must **not** attempt to retrofit i18n onto the panel's existing hardcoded strings (the starter/health intro, the yeast selectbox label) — that is a pre-existing gap out of this task's scope (§10).

---

## 5. Exact persistent data contract

**New Recipe Object field:** `fermentation_temp_target_c` — `float | None`.

- **Type/domain:** a finite real number of degrees Celsius, or `None`. **No brewing-semantic minimum or maximum is imposed in this slice.** The widget must stay unset by default and may use `step=0.5`, but must not display a min/max range that could be read as Kvernhaug-authorized yeast guidance. Persistence uses a small resolver (e.g. `resolve_fermentation_temp_target_c(value)`) that returns `None` for booleans, non-numeric values, NaN or ±infinity, and otherwise returns `float(value)`. This is type/finite-value hygiene only — it does not validate whether the number is suitable for any yeast strain.
- **Unset semantics:** `None` means "no target chosen yet." `None` is the field's default for every new/blank recipe, for every recipe saved before this field existed, and for any recipe whose stored value fails a basic type check — mirroring `resolve_recipe_efficiency()`'s "not a genuine positive real number → `None`, never guessed" pattern (§1.8). `None` is rendered as an empty `st.number_input` (Streamlit's pinned range, `streamlit>=1.59,<2.0`, per `requirements.txt`, supports `value=None` for an empty numeric widget) — never a pre-filled 18/20/any other placeholder number, satisfying the issue's "critical guardrail" against an ambiguous default.
- **Session-state ownership:** the visible widget uses one scalar key, `st.session_state["gjaering_temp_maal_c"]`. Because this key is recipe-scoped, it **does have cross-recipe/blank-state reset semantics** and must never be allowed to leak from the previously active recipe. A single coordination key, `_pending_gjaering_temp_maal_c`, is allowed for transitions that occur *after* the widget has already been instantiated in the current Streamlit run. `app.py` consumes that pending key by membership check (not by truthiness, because the intended value may be `None`) **before** `render_yeast_panel()` creates the number input, then assigns its value to `gjaering_temp_maal_c` and removes the pending key. This follows the repo's existing pending-before-widget pattern rather than inventing a new state model.
- **`bygg_recipe_object()` (`modules/recipe.py`):** add a new keyword parameter `fermentation_temp_target_c=None`, stored **unconditionally** on the returned dict (`recipe["fermentation_temp_target_c"] = fermentation_temp_target_c`) — always present, defaulting to `None`, exactly like the four `water_*` fields (never conditionally omitted the way `_kbh_passthrough`/`originRecipeId` are).
- **Both rebuild call sites updated identically** (§1.7d): `modules/recipe_context.py`'s live-calculation rebuild and `ui/recipe_card.py::_bygg_recipe_fra_session()`'s save/export rebuild both add `fermentation_temp_target_c=st.session_state.get("gjaering_temp_maal_c")`.

---

## 6. Save/load/export/history boundary

- **Local recipe save/load (`modules/recipe_storage.py`):** **included, automatically, with no code change to that module** (§1.7a) — the field round-trips as an ordinary top-level key on the saved JSON dict, exactly like every other Recipe Object field.
- **`.kbhrecipe` export/import (`modules/kbh_contract.py`/`modules/kbh_import.py`):** **explicitly deferred, not included, in this slice.** Per §1.7b, inclusion would require a genuine Core/schema addition — a new payload key (e.g. `gjaeringTemperaturMaal`), a new `_KJENTE_PAYLOAD_FELT` entry in *both* modules, and explicit validated read/write code — which is exactly the kind of Core/schema extension the issue's guardrail says must not be assumed justified for this bounded slice. **Concretely:** exporting a recipe that has a target set will silently omit it from the `.kbhrecipe` file today; this must be stated plainly in the implementation child's own report/changelog so it is a known, deliberate limitation, not a silent surprise discovered later. Promoting this to a Core V1 field is a separate, future, owner/Chief-authorized decision (see §11).
- **`.kbhbrew` historical snapshot (`modules/kbhbrew.py`):** **excluded automatically, with no separate code needed to keep it out** (§1.7c) — since the snapshot's `recipe` sub-object is built by calling the same `.kbhrecipe` payload writer, deferring (b) transitively defers (c). If a future round promotes the field into the `.kbhrecipe` schema, it will start appearing in new `.kbhbrew` snapshots automatically at that point (never retroactively in already-frozen historical snapshots, per `.kbhbrew`'s own frozen-snapshot contract).
- **Copy/"Lagre som ny kopi" behavior:** identical to every other scalar field read from `st.session_state` in `_bygg_recipe_fra_session()` — a copy inherits whatever the widget currently holds at the moment of copying, exactly like `brygger_stil`/`batch_volum_input` do today. No special copy-time reset logic is introduced (there is no "origin identity" style reason to zero it out on copy, unlike `originRecipeId`).
- **DEMO_MODE:** no new guard needed. `lagre_oppskrift()` already returns `None` without writing to disk whenever `DEMO_MODE` is set (`modules/recipe_storage.py:444–445`), and this field introduces no new disk write of its own — it flows through the exact same recipe-object/session-state/save path as every other optional field already covered by that central guard.

---

## 7. Backward compatibility and reset semantics

An older recipe file saved before this field existed simply lacks the `fermentation_temp_target_c` key. On saved-recipe load, `ui/sidebar.py` resolves `r_data.get("fermentation_temp_target_c")` through the finite-number resolver from §5 and writes the result **unconditionally** to `st.session_state["gjaering_temp_maal_c"]` before the yeast widget is created. Missing, null or invalid values therefore become `None`; the widget renders empty — never a guessed number and never a value derived from `gjaertype`, category or flavor tags.

The implementation child must cover **every transition into a new recipe context**, not only saved-recipe load:

1. **Brand-new app session:** `app.py` initializes `gjaering_temp_maal_c = None` when the key is absent.
2. **Recipe A → saved Recipe B:** `ui/sidebar.py`, which runs before the recipe tab widgets, directly assigns B's resolved stored value; if B lacks the field, it assigns `None`.
3. **Loaded recipe → sidebar “no recipe” placeholder / blank state:** before clearing `_last_loaded_recipe`, the sidebar directly sets `gjaering_temp_maal_c = None` because it still runs before `render_yeast_panel()`.
4. **Archive-success → blank recipe:** archive happens in `ui/recipe_card.py` after the yeast widget has already been instantiated in that run, so it must **not** write the widget-bound key directly. It sets `st.session_state["_pending_gjaering_temp_maal_c"] = None`; on the next rerun, `app.py` consumes that pending value before the widget exists.
5. **Import/new-draft/next-variant flows:** whenever a flow replaces the active recipe context, it must set the target from the incoming object if that object explicitly carries a valid App-internal `fermentation_temp_target_c`; otherwise it must set/reset to `None`. If the transition occurs before `render_yeast_panel()`, assign directly; if it is triggered after widget creation, use the same pending key. A newly imported `.kbhrecipe` cannot currently carry this field by contract (§6), so that flow necessarily resets to `None`. A next-variant seed only inherits the value if the seed contract explicitly includes this App-internal field; otherwise it resets to `None` — never implicitly reuses whatever happened to be in session state.

No migration script or schema-version bump is needed. The important invariant is stronger than “missing key loads as None”: **changing recipe context must deterministically hydrate or clear this recipe-scoped widget before it can be saved again.**

---

## 8. NO/EN wording contract

New `modules/i18n.py` keys (exact strings authored by the implementation child, not fixed verbatim here, but constrained as follows):

| Key | Constraint |
|---|---|
| `gjaering.laer_bro.tittel` | Short, inviting, collapsed-by-default label — same tone as `prosess.laer_bro.tittel` ("🎓 Why does mash temperature affect the beer?" precedent) adapted to fermentation/yeast. |
| `gjaering.laer_bro.footer` | Plain-text pointer to the Bryggeskole Gjæring module — same "Want to practice more? Open Brew School → X" shape as `prosess.laer_bro.footer`, not a working navigation control (§4). |
| `gjaering.temp_maal.label` | The number input's label — must not imply a recommendation (e.g. "Planned fermentation temperature (°C)" / "Planlagt gjæringstemperatur (°C)" — "planned/planlagt," never "recommended/anbefalt"). |
| `gjaering.temp_maal.hjelp` (or an inline caption) | Must state explicitly, in both languages, that Kvernhaug does not store a verified temperature range for the selected strain and the learner should follow their strain/manufacturer's own guidance — this is the direct UI expression of the issue's "critical guardrail" and of `CHUNK-FERM-C`'s own instruction; it must not soften into an implied universal ale/lager rule. |

`bryggeskole.feil.innhold_ugyldig` (the existing shared invalid-pilot-content error key, already used by `ui/process_panel.py` and `ui/bryggeskole_panel.py`) is reused unchanged — no new error string is minted for this bridge.

---

## 9. Transfer/application acceptance scenario

Mirroring §9.1 of the Mesking precedent — a human acceptance step, separate from and in addition to the automated tests in §10:

- **Setup:** the evaluator selects any yeast strain already available in `ui/yeast_panel.py` and supplies the **current manufacturer-published fermentation guidance for that exact strain from outside the app**. The contract deliberately hard-codes neither a strain name nor a numeric range, so this acceptance step cannot go stale or accidentally become Kvernhaug masterdata. The scenario must be different in framing from `Q-FERM-001`/`Q-FERM-002`'s authored questions.
- **Task:** after reading the bridge's three chunks in the running app, the learner selects a deliberate target temperature within the supplied manufacturer range and states, in their own words, (a) the chosen number, (b) a rationale invoking the activity/speed lever (`FACT-BREW-0001`) and/or the flavor lever (`FACT-BREW-0002`), and (c) an explicit acknowledgment that this choice is specific to the selected strain, not a generic "ale warm / lager cold" rule (`FACT-BREW-0003`).
- **Observable PASS criteria (all three required):** (1) the chosen number falls inside the supplied manufacturer range; (2) the rationale references the activity/speed and/or flavor relationship in the evaluator's own words, not a copied chunk sentence; (3) the strain-specificity acknowledgment is stated unprompted.
- **Observable FAIL criteria (any one):** a number outside the supplied range is asserted as correct anyway; the choice is justified purely by "ale vs. lager" or "the app's default"; or no rationale beyond "the app told me" can be produced.
- **Method and scope:** a human acceptance step (owner or QA reviewer) run once at the implementation child's final checkpoint, using the shipped app — no new schema, no new authored pilot/registry content, and no scoring UI or mastery-store change (consistent with §10/§11's non-goals).
- Per this project's existing governance, this is representative acceptance evidence — it does not gate roadmap progress on the owner personally acting as a mandatory learner (mirrors the Mesking precedent's own framing, §9.1).

---

## 10. Automated test plan for the implementation child

1. **New or extended `tests/test_yeast_panel.py`** (no such file exists today), using the same `AppTest`-driven pattern as `tests/test_process_panel.py`'s `TestLaerBroMeskingBridge` (`tests/test_process_panel.py:414–474`):
   - the bridge expander exists and is collapsed by default (mirrors `test_broen_finnes_og_er_kollapset_som_standard`);
   - it renders `CHUNK-FERM-A/B/C` unchanged, in that order, matching `pilot_fermentation.render_chunk(..., "no")`/`"en"` output exactly (mirrors `test_broen_viser_chunk_mash_b_og_c_uendret_paa_norsk`/`_engelsk`);
   - an invalid pilot file (mocked `PilotContentError`) shows the shared error string and never crashes `tab_oppskrift` (mirrors `test_ugyldig_pilotinnhold_krasjer_ikke_bryggdag_fanen`);
   - the number input exists, defaults to empty/`None` for a brand-new session, exposes no brewing-semantic min/max recommendation, and setting it updates `st.session_state["gjaering_temp_maal_c"]`;
   - the finite-value resolver accepts ordinary finite numeric values and rejects bool/non-numeric/NaN/±infinity to `None`, without applying a brewing-temperature range.
2. **`modules/recipe.py`'s existing test coverage** (wherever `bygg_recipe_object()` is exercised, e.g. via `tests/test_water_recipe_integration.py`'s pattern of calling it directly) extended to assert: the new parameter defaults to `None`; a supplied float is stored unconditionally under `fermentation_temp_target_c`.
3. **A new full-stack save/reload `AppTest` integration test**, following `tests/test_water_recipe_integration.py`'s exact shape (isolated `KVERNHAUG_RECIPES_DIR`, real `app.py` via `AppTest`): (a) an old recipe saved *without* the field opens with the widget empty/`None`; (b) setting a target, saving, and reopening in a brand-new session preserves the exact value; (c) Recipe A with a target → Recipe B without the field clears to `None`; (d) loaded Recipe A → sidebar blank/no-recipe state clears to `None`; (e) archive-success → blank state clears via the pending-before-widget path; (f) an imported `.kbhrecipe` lacking this deferred field resets it to `None`; (g) malt/hops/yeast/`process_profile`/`water_*` remain unchanged by this feature. These tests are specifically required to prove stale temperature cannot leak across recipe-context transitions.
4. **`tests/test_kbh_contract.py`** extended with an explicit negative assertion: a Recipe Object with `fermentation_temp_target_c` set produces a `.kbhrecipe` payload that does **not** contain that value under any key — proving §6's deferred-export decision holds and guards against silent future leakage through the passthrough mechanism.
5. **`tests/test_pilot_fermentation.py`** — unchanged; this issue and its implementation child make no edit to `bryggeskole/pilot_fermentation.py`, `pilot_fermentation_temperature.json`, or `course_fact_registry.json` (§3).
6. Full Python suite (`python3 -m unittest discover -s tests -b`) at the implementation child's final checkpoint, per [`.claude/rules/testing.md`](../../.claude/rules/testing.md).

This document itself only requires confirming every cited file:line still resolves against current master, done as part of writing it.

---

## 11. Explicit non-goals

Restated from the governing issue, since this document's own recommendations must not silently cross them:

- No App/UI implementation was made in this issue.
- No Course Fact Registry mutation was made in this issue (§3 recommends none).
- No pilot-content mutation was made in this issue.
- No yeast masterdata (`data/master_gjaer_v2.json`) mutation was made in this issue (§1.6).
- No `.kbhrecipe`/Core schema mutation was made or is recommended as required for this slice (§6 explicitly defers it).
- No `.kbhbrew` schema mutation.
- No scraping/import of manufacturer temperature ranges.
- No automatic temperature recommendation engine, pitch-rate work, pressure-fermentation curriculum, or fermentation schedule/ramp planner.
- No Web/public deploy, no Sóti/AI, no broader Learn→Plan bridges for boil/hop/package in this issue.
- No merge/deploy.

## Hard non-goals

(Restated verbatim from issue #382 for traceability — this document does not violate any of these.)

- no App/UI implementation;
- no Registry mutation unless this document only recommends it (it recommends none, §3);
- no yeast masterdata mutation;
- no scraping/import of manufacturer ranges;
- no broad yeast database enrichment;
- no automatic temperature recommendation engine;
- no pitch-rate work;
- no pressure-fermentation curriculum;
- no fermentation schedule/ramp planner;
- no Core/schema extension unless the audit proves it is necessary — the audit concludes it is **not** necessary for this bounded slice (§6), and this document does not implement one regardless;
- no Web/public deploy;
- no Sóti/AI;
- no broader Learn→Plan bridges for boil/hop/package in this issue;
- no merge/deploy.

---

## 12. Remaining owner/Chief decisions

1. **Whether to promote `fermentation_temp_target_c` into the `.kbhrecipe`/`.kbhbrew` Core schema at all, and when.** §6 defers this deliberately rather than deciding it — it is a genuine product/portability trade-off (a locally-useful plan field vs. widening the exported Core contract) that this document's own scope (docs-only, no Core/schema extension unless proven necessary) does not require it to resolve. If a future round wants export/history portability for this field, that is a separately authorized Core Contract change, not an automatic follow-on to this slice's implementation child.
2. **No owner decision is required for the implementation child's guardrail wording.** The semantic constraint in §8 is already fixed: it must state that Kvernhaug does not hold a verified range for the selected strain and that the brewer should follow current strain/manufacturer guidance; Claude may write concise NO/EN copy within that constraint.

No other genuine product choice in this slice requires an owner tie-break beyond Chief's review of this contract itself — every question in issue #382's "Required repo audit" and "UX decision required" sections was resolvable from existing, already-established repo precedent (the verified-only Course Fact Registry boundary, the already-shipped Mesking Learn→Plan bridge mechanics, the existing `water_*`/`process_profile` optional-field persistence pattern, and the explicit `.kbhrecipe` whitelist rule in `CORE_KBHRECIPE_V1.md`).
