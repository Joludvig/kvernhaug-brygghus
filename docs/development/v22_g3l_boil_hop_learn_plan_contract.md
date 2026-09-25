# V2.2 Goal 3L — Koking/humle Learn → Plan bridge contract

Version: 1.1
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#386](https://github.com/Joludvig/kvernhaug-brygghus/issues/386), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3),
accepted gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358),
Koking/humle module implementation [#366](https://github.com/Joludvig/kvernhaug-brygghus/issues/366) /
merged [PR #367](https://github.com/Joludvig/kvernhaug-brygghus/pull/367),
Mesking Learn→Plan precedent [#344](https://github.com/Joludvig/kvernhaug-brygghus/issues/344) /
[#352](https://github.com/Joludvig/kvernhaug-brygghus/issues/352),
Gjæringstemperatur Learn→Plan precedent [#382](https://github.com/Joludvig/kvernhaug-brygghus/issues/382) /
merged [PR #385](https://github.com/Joludvig/kvernhaug-brygghus/pull/385),
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction)
Authoritative base at creation: `72399a4156a1640512495207f5c8cc7bb4a264de`

This is a decision/prep document only. It contains **no product implementation** — see
[Hard non-goals](#hard-non-goals). Chief must review this contract before any implementation
child issue is opened.

---

## 1. Current-state audit

### 1.1 `bryggeskole/data/course_fact_registry.json` — Koking/humle-relevant verified records

All 7 records are `status: "verified"` (`verified_at: "2026-09-22T14:00:00Z"`), each with an
explicit `notes` hedge/scope boundary:

| ID | Line | Classification | Claim (summarized) | Explicit hedge (`notes`) |
|---|---|---|---|---|
| `FACT-BOIL-0001` | 153 | `documented_fact` | Boiling inactivates mash enzymes and reduces microbial load carried from mash/lauter. | "reduces microbial load at the time of boiling," not a sterility claim afterward; never say "sterilizes." |
| `FACT-BOIL-0002` | 170 | `documented_fact` | A malt precursor forms DMS on heating; **DMS itself** is volatile (not the precursor); vigorous/long boil helps drive it off. | Wording trap: never call the precursor "volatile" — DMS is what's volatile. No fixed minute-count rule. |
| `FACT-BOIL-0003` | 187 | `documented_fact` | Boiling coagulates/precipitates proteins+polyphenols ("hot break"). | Explicitly distinct from chill haze, which forms later during cooling. |
| `FACT-BOIL-0004` | 204 | `practical_experience` | Rising foam in the first minutes of a rolling boil can cause boil-over. | Not a guaranteed event; no fixed fill-level threshold. |
| `FACT-HOP-0001` | 221 | `documented_fact` | Boiling isomerizes hop alpha acids → iso-alpha-acids (bitterness); time-dependent; utilization approaches a practical ceiling. | Does not assert or reproduce any specific numeric utilization curve/percentage — that remains `modules/calculations.py`'s own implemented Tinseth model. |
| `FACT-HOP-0002` | 238 | `documented_fact` | Aroma/flavor oils boil off over time; a late/flameout/whirlpool addition retains more aroma and reaches lower utilization — **not zero**. | "'Generally lower' utilization, not 'zero' or 'negligible'"; no specific whirlpool temperature/duration asserted as optimal. |
| `FACT-HOP-0003` | 260 | `professional_interpretation` | Because bitterness and aroma move opposite ways with time, brewers commonly combine an early "bittering" addition with a late/whirlpool "aroma" addition. | Synthesis of `FACT-HOP-0001`/`FACT-HOP-0002`, not a new measurement; does not assert a fixed numeric schedule (no "60/20/5 minutes" rule). |

### 1.2 `bryggeskole/pilot_boil_hop.py` and `bryggeskole/data/pilot_boil_hop_fundamentals.json`

Pure, stdlib-only, fail-closed pilot-content validator/renderer — architecturally identical to
`pilot_mashing.py`/`pilot_fermentation.py` (same `read_pilot_file()`/`render_chunk(chunk, language)`/
`render_question(question, language)`/`evaluate_answer(...)` API, same `PilotContentError`,
same verified-only `source_claims` resolution boundary, per
[BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) §18). It
explicitly states it is "deliberately not an IBU math lesson," deferring all numeric Tinseth
math to `modules/calculations.py`.

`pilot_boil_hop_fundamentals.json` has exactly six chunks, already lettered in a pedagogical
order this document reuses unchanged (§3):

| Chunk | `source_claims` | Teaches |
|---|---|---|
| `CHUNK-BOILHOP-A` | `FACT-BOIL-0001` | Boiling stops mashing; reduces microbial load; not sterile afterward. |
| `CHUNK-BOILHOP-B` | `FACT-BOIL-0002/3/4` | DMS driven off; hot break vs. chill haze; boil-over foam risk. |
| `CHUNK-BOILHOP-C` | `FACT-HOP-0001` | Alpha-acid isomerization is time-dependent; utilization has a practical ceiling. |
| `CHUNK-BOILHOP-D` | `FACT-HOP-0002` | Aroma oils boil off with time; late/flameout/whirlpool retains more aroma, reaches lower (not zero) utilization. |
| `CHUNK-BOILHOP-E` | `FACT-HOP-0003` | Bitterness vs. aroma trade off with time → brewers combine early "bittering" + late/whirlpool "aroma" additions. |
| `CHUNK-BOILHOP-F` | `FACT-HOP-0001`, `FACT-HOP-0002` | Whirlpool/hop-stand is a **distinct technique** (added after active boiling stops, held hot-not-boiling) — not just "a very late boil addition." |

`CHUNK-BOILHOP-A`/`B` teach general boil chemistry/safety (enzyme inactivation, DMS, hot break,
boil-over) — not hop-timing-specific, and not reused by this bridge (§3). `CHUNK-BOILHOP-C`
through `F` are the exact hop-timing-role content this task needs, already hedged and
technique-scoped by the pilot content itself — e.g. `CHUNK-BOILHOP-D` (NO, verbatim): *"...men
en varm, lang whirlpool kan likevel bidra med merkbar bitterhet, ikke null"* ("...but a hot,
long whirlpool can still contribute material bitterness, not zero"), and `CHUNK-BOILHOP-F` (NO,
verbatim): *"Whirlpool/hop-stand er en egen teknikk, ikke bare «en veldig sen
koketilsetning»..."* ("Whirlpool/hop-stand is a distinct technique, not just 'a very late boil
addition'...").

### 1.3 `ui/bryggeskole_panel.py` — Koking module wiring

Koking is wired in as the third self-contained Bryggeskole module (`_MODUL_KOKING`,
`_MODULER["koking"]`, `_MODUL_REKKEFOLGE`, `_STADIUM_TIL_MODUL` index 2, `_KONSEPT_LABELS` for
8 concept ids including `hop.isomerization_time`/`hop.aroma_volatility`/
`hop.addition_strategy`/`hop.whirlpool_technique`) — the same per-module mastery session-state
pattern as Mesking/Gjæring (`st.session_state["bs_modul_sesjon"]["koking"]`, persisted via
`bryggeskole/mastery_store.py`). This flow is fully self-contained and disjoint from the App's
recipe/hop-planning session state (`bs_*` keys never overlap with `valgt_humle`/`humle_*` keys,
§1.7) — nothing there reads or writes the hop panel today, and this bridge must not change that
(mirrors both precedents' "no mastery interaction" rule, §7.1 below).

`bryggeskole/boil_timeline.py` (a pure, stdlib-only, non-interactive SVG generator with
qualitative early/late/flameout/whirlpool markers and **no numeric IBU axis**) is rendered only
inside this Bryggeskole lesson flow (`ui/bryggeskole_panel.py`, import + one `st.markdown(...,
unsafe_allow_html=True)` call). A repo-wide search finds no reuse of it from `ui/hop_panel.py`
or any other recipe-planning file — it is not, and this document does not propose making it,
part of the bridge (§4's placement decision explains why not).

### 1.4 `ui/hop_panel.py` — exact current state

127 lines total. `render_hop_panel(humle_database)` (line 9):

- Renders a header (`st.header("🌿 Humle-tilsetninger")`, line 10),
- An "➕ Legg til humle" add-row button (line 16) that appends a new
  `{"id": ..., "gram": 20, "tid": 5}` dict,
- A per-row loop (lines 57–126) rendering, for each hop row: a hop `st.selectbox` (line 71), a
  `st.number_input("Gram", ...)` (line 76), and **`st.number_input("Tid (Min)", min_value=0,
  max_value=120, ..., step=5, key=f"humle_tid_{j}_v{_v}")`** (line 78) — the row's boil-timing
  field, purely numeric minutes,
- A read-only, **disabled**, non-persisted display caption computed at line 93:
  `bruk_type = "Bitter" if ny_tid >= 60 else ("Smak" if ny_tid >= 15 else ("Aroma" if ny_tid > 0
  else "Tørrhumle"))`, shown via `st.text_input("Bruk", value=f"{bruk_type} ({h_alfa}%
  Alfa)", disabled=True, ...)` (line 94) — a UI caption *derived from* `tid`, never written back
  into the row dict, never round-tripped anywhere, and never consumed by the IBU calculator
  (§1.6). This is the closest thing to an existing qualitative timing label in the App today, and
  it already proves the direction this bridge needs (lower `tid` reads more toward
  aroma/dry-hop, higher `tid` toward bitter) — but it has **no whirlpool category at all**: a
  whirlpool addition entered at, say, `tid=15` renders identically to an in-boil addition at 15
  minutes ("Smak"/flavor), with no way to distinguish the two.
- A per-row "Mål-IBU"/"Beregn gram" reverse-calculator (lines 104–123), only shown when
  `ny_tid > 0`.

**`ui/hop_panel.py` has zero `ui.i18n` usage** — no `from ui.i18n import` line anywhere in the
file (confirmed by grep); every string is hardcoded Norwegian, matching the pre-bridge state
`yeast_panel.py` was found to be in before the Gjæring bridge. This is a pre-existing gap this
task does not fix wholesale (§11) — but any *new* copy this bridge adds must use `t()`/`ui.i18n`
(§7).

Called from `app.py:163`, inside `tab_oppskrift`/`with col1:`, immediately after
`render_malt_panel` (line 161) and immediately before `render_yeast_panel` (line 165) — and, as
with the Gjæring precedent, before `bygg_recipe_context()` is invoked (`app.py:169–177`). This
is the exact "strong candidate" placement the issue names: the only surface where hop selection,
the recipe-build call, and the save/load path all meet before the recipe object for the render
is constructed.

**Note for the implementation child:** `ui/ingrediens_paneler.py:56` contains a second,
differently-shaped `render_hop_panel(humle_database, humle_meny_valg, humle_id_kart)` with its
own copy of the row-mutation logic. A repo-wide search finds **zero importers** of
`ingrediens_paneler` anywhere — it is dead/orphaned code, not the live panel. The implementation
child must edit `ui/hop_panel.py` only, and should not be misled by this second file.

### 1.5 Hop row shape and the Recipe Object

`modules/recipe.py::bygg_recipe_object()` takes `hops` as a plain positional parameter and
stores it verbatim (`recipe["hops"] = hops`) — no reshaping, no validation inside that function.
The actual row dicts are built upstream, directly by `ui/hop_panel.py`'s own per-row loop (line
126: `oppdatert_humle_liste.append({"id": ny_h_id, "gram": nytt_gram, "tid": ny_tid})`), and
`modules/recipe_context.py::bygg_recipe_context()` passes `st.session_state.valgt_humle`
straight through as the `hops` keyword. **Exactly three fields exist on every hop row today:
`id`, `gram`, `tid`.** `recipe_context.py` separately builds a *derived* `humle_calc` list
(`{"navn": ..., "gram": ..., "tid": ...}`) purely as internal IBU/flavor-wheel calculation
input — this is not what's stored on the Recipe Object.

### 1.6 IBU calculation and downstream brewday reporting — both purely `tid`-driven, no whirlpool concept

`modules/calculations.py::beregn_total_ibu()` (line 215) implements Tinseth: for each hop, line
240 `times_faktor = (1 - math.exp(-0.04 * tid)) / 4.15`, combined with a gravity "bigness"
factor into `utnyttelse` (utilization); line 246 special-cases `if tid == 0: utnyttelse = 0.0`
(pure dry-hop, zero boil bitterness). `beregn_gram_fra_ibu()` (line 189, the inverse formula
`ui/hop_panel.py`'s "Beregn gram" button calls at line 118) uses the identical time-factor curve.
**Neither function reads or is aware of any timing *category* — only the raw minute value.** A
whirlpool addition entered as `tid=15` is scored by the exact same curve as an in-boil addition
at 15 minutes; the calculator has no concept of "this addition was not at active boiling
temperature."

This same blind spot propagates one layer further, into brew-day reporting:
`modules/brewday_calc.py::_bygg_humle_entry()` (line 110) derives `tilsatt_etter_min = max(0,
total_koketid_min - tid)` (line 147, "added after N minutes [from boil start]") and
`tid_over_koketid` (line 139, an impossible-timing warning when a hop's own boil time exceeds
the process's total boil duration), both consumed by `ui/brewday_panel.py`'s brewday-plan table
(lines 205–230, columns "Tid igjen" / "Tilsatt etter"). This table is a **read-only report**
derived from the same `tid` field, not an editing surface, and it likewise has no whirlpool
category — it is flagged here as relevant context (the same qualitative gap exists one screen
further into the brewer's actual brew day), not as a surface this bridge touches (§11 — out of
scope).

**Conclusion for §5 below:** hop timing is, end to end, purely numeric minutes. No qualitative
role/category field exists anywhere in the schema, the editing UI, the IBU math, or the brewday
report — matching the issue's framing that "a deliberate hop-timing role/direction choice" must
be *represented by*, not added on top of, the existing `tid` field.

### 1.7 The four persistence surfaces — hop rows already round-trip unchanged

Mirrors the Gjæring contract's §1.7 generic architecture; confirmed here specifically for hop
rows:

- **Local recipe save/load (`modules/recipe_storage.py`).** Verbatim pass-through — the `hops`
  list round-trips as an ordinary key on the saved JSON dict, with no code specific to hop rows.
- **`.kbhrecipe` export (`modules/kbh_contract.py`).** `_valider_humle(hops)` (line 105) validates
  `id`/`gram ≥ 0`/`tid ≥ 0`; `_bygg_humle_rader(hops)` (line 127) is an explicit whitelist:
  `[{"id": rad["id"], "gram": rad["gram"], "tid": rad["tid"]} for rad in hops]` — exactly the
  three existing fields, nothing more.
- **`.kbhrecipe` import (`modules/kbh_import.py`).** `_valider_og_bygg_humle()` (line 258) reads
  `id`/`gram`/`tid`, explicitly **rejects** a present `custom` dict or `alfaOverride` key (lines
  266–279, unsupported-by-import categories) and builds the same three-field row (line 286).
- **`.kbhbrew` (`modules/kbhbrew.py`).** Calls `recipe_to_kbhrecipe_payload()` directly — inherits
  (b)'s exact whitelist, no separate hop-row handling.

**Because this task adds no new field (§5), none of these four surfaces need any code change,**
and no new export/import test is required to prove a new field is excluded (contrast the Gjæring
precedent, whose new `fermentation_temp_target_c` field needed an explicit non-leak test — there
is no equivalent new field here to leak).

### 1.8 Session-state keys

The live hop-row list is `st.session_state.valgt_humle` (initialized `app.py:72–74` as
`[{"id": ..., "gram": 20, "tid": 60}]`), read/written by `ui/hop_panel.py`, `app.py:171`
(`bygg_recipe_context`), `ui/recipe_card.py`, `ui/brewday_panel.py`, `ui/sidebar.py` (load),
`modules/kbh_import_apply.py` (import apply), and others — all under the `valgt_humle`/`humle_*`
naming convention, fully disjoint from Bryggeskole's `bs_*` keys (§1.3). Per-row widget keys
follow the resident "widget-reset version key" pattern (`f"humle_tid_{j}_v{_v}"`, etc.), and a
`"_pending_humle_gram"` pending-key is already used for the reverse-IBU-calculator flow (lines
52–55, 120) — the resident "pending key" pattern this bridge does not need, since it introduces
no widget-bound value that must survive a rerun before its own widget exists (§6).

---


## 2. Exact selected user task

While editing a recipe's hop rows in `ui/hop_panel.py`, the learner can open one small, collapsed
"why does hop timing matter" bridge showing the existing, verified Koking/humle timing content
(`CHUNK-BOILHOP-C/D/E/F`, unchanged) — and, independently of whether they open it, continue
making one concrete planning decision already represented correctly by the App: choosing the
**boil duration for an in-boil hop addition** in the existing "Tid (Min)" field.

No new field, selectbox, or category is added. For additions that are actually in the active
boil, a higher `tid` value represents an earlier/longer-boiled addition and a lower positive
`tid` value represents a later/shorter-boiled addition. That is the bounded Learn → Plan task.

**A true flameout/whirlpool/hop-stand addition is explicitly NOT represented by this field in the
current App.** The planner has no technique/phase dimension: a positive `tid` is consumed by the
Tinseth calculation and brewday timing as active-boil minutes, while `tid == 0` is currently
treated as zero boil utilization and the UI labels it as dry hop. The bridge must therefore
never tell the learner to encode a true whirlpool by "just entering a low minute value."
`CHUNK-BOILHOP-F` is reused specifically to teach that whirlpool is a distinct technique and
to disclose that the current recipe planner cannot represent it faithfully yet.

This is deliberately the cheapest safe instance of Learn → Plan: it does not gate, validate,
auto-set, or add new persisted state. The existing numeric field remains the planning mechanism
for **in-boil timing only**; the bridge adds an in-context "why" plus an explicit boundary around
techniques the current data model does not represent.

---

## 3. Verified source/chunk reuse map

| Bridge element | Reuses |
|---|---|
| "Why does boil time change bitterness?" (higher `tid` → more bitterness, up to a ceiling) | `CHUNK-BOILHOP-C` / `FACT-HOP-0001`, unchanged |
| "Why does a later/whirlpool addition taste/smell different?" (lower `tid` → more aroma, lower — not zero — bitterness) | `CHUNK-BOILHOP-D` / `FACT-HOP-0002`, unchanged |
| "Why brewers use more than one addition" (early bittering + late/whirlpool aroma) | `CHUNK-BOILHOP-E` / `FACT-HOP-0003`, unchanged |
| "Whirlpool is a distinct technique, not just a very-late boil addition" — direct source for the boundary that the current numeric boil-time field must **not** be used as a fake whirlpool representation | `CHUNK-BOILHOP-F` / `FACT-HOP-0001`+`FACT-HOP-0002`, unchanged |

`CHUNK-BOILHOP-A`/`B` (general boil chemistry/safety — enzyme inactivation, DMS, hot break,
boil-over) are **not reused** — they answer "why do we boil at all," not "why does *when* I add
hops matter," and including them would duplicate/widen scope beyond the one hop-timing task
selected in §2 (the issue's own "smallest task" instruction). No new Course Fact Registry record
is proposed, and no new teaching copy is authored anywhere in `ui/hop_panel.py` beyond the
guardrail disclosure itself (§8) — every taught sentence already exists, verified, in
`bryggeskole/pilot_boil_hop.py`'s pilot content, rendered via its own unmodified
`render_chunk()`. The guardrail text is App UI copy about what the *calculator* does, not a
Course Fact Registry claim — exactly parallel to how the Gjæring contract's "Kvernhaug does not
store a verified range for your strain" caption sits alongside, not inside, its reused chunks.

---

## 4. UI placement decision

**Chosen: one collapsed `st.expander` inside `render_hop_panel()` (`ui/hop_panel.py`), placed
directly below the header (`st.header("🌿 Humle-tilsetninger")`, line 10) and above the "➕ Legg
til humle" button (line 16)** — before any row exists to look at, mirroring both precedents'
"teach immediately before the deliberate choice" placement principle, adapted to a
repeating-row panel where a per-row bridge would either duplicate itself N times or attach
arbitrarily to only one row.

**Why one shared bridge, not one per row:** `ui/hop_panel.py` can hold any number of hop rows
(the panel supports adding/removing rows freely, §1.4). Rendering the same `st.expander` inside
the per-row loop (lines 57–126) would repeat identical content once per row — noisy for a
multi-hop recipe and inconsistent with the panel's own existing pattern of showing shared
context once (e.g. the add-row button) rather than per row. A single bridge at the top, always
visible regardless of row count (including the zero-row edge case, since the panel always starts
with one default row per `app.py:72-74` but a learner can delete it), is the only placement that
scales correctly with the row list.

**Contents, in order:**

1. `CHUNK-BOILHOP-C`, `D`, `E`, `F` rendered via `pilot_boil_hop.read_pilot_file()` /
   `render_chunk(chunk, sprak)`, in that order — same `try`/`except PilotContentError` fallback
   as both precedents (`st.error(t("bryggeskole.feil.innhold_ugyldig"))`, reusing the existing
   shared error key rather than minting a new one), same "no mastery interaction" rule (§1.3).
2. **The guardrail disclosure** (§8), placed inside the same expander, directly after the four
   chunks and visually distinguished (e.g. `st.warning`/`st.caption` rather than plain
   `st.markdown`, so it reads as a tool-limitation notice, not more lesson content) — placed
   once here rather than duplicated as `help=` text on every row's "Tid (Min)" widget, for the
   same row-count-scaling reason as point 1.
3. A footer caption pointing at the full Bryggeskole Koking module as plain text (e.g. "Vil du
   øve mer? Åpne Bryggeskole → Koking." / "Want to practice more? Open Brew School → Boil.") —
   not a working cross-tab jump, mirroring both precedents' `_render_laer_bro()`-style footer
   (no reliable programmatic tab-switch exists for a bridge this small to justify building one,
   per the Mesking contract's §7.0 analysis, unchanged since then).

**i18n note (same gap as the Gjæring precedent found for `yeast_panel.py`):** `ui/hop_panel.py`
currently has zero `ui.i18n` usage (§1.4). This bridge's implementation child must add `from
ui.i18n import gjeldende_sprak, t` to `ui/hop_panel.py` and add exactly the new strings this
bridge needs (§7) to `modules/i18n.py`'s NO and EN blocks, following the `prosess.laer_bro.*`
(`ui/process_panel.py:214-215`) / `gjaering.laer_bro.*` (`modules/i18n.py:216-217`) key-naming
precedent — i.e. `koking.laer_bro.*`. It must **not** attempt to retrofit i18n onto the panel's
other existing hardcoded strings (header, row labels, the disabled "Bruk" caption, the IBU
reverse-calculator) — that is a pre-existing gap out of this task's scope (§11), exactly as the
Gjæring contract ruled for `yeast_panel.py`'s starter/health intro and selectbox label.

---


## 5. Whether a persistent-data change is needed

**No persistent-data change is needed for the bounded task selected in §2: choosing earlier vs.
later timing for additions that are actually in the active boil.** The existing `tid` field
already persists exactly that quantity through local recipe storage, `.kbhrecipe`, `.kbhbrew`,
IBU calculation and brewday reporting.

The audit does, however, prove a separate product gap: **flameout/whirlpool/hop-stand cannot be
represented faithfully by the current three-field hop row**. Adding a technique/phase field
would be a real recipe/Core design decision because calculation and brewday semantics would also
need to understand it; merely adding a cosmetic enum while leaving downstream consumers
`tid`-only would create contradictory state. That broader change is not required to ship this
small Learn → Plan bridge and is therefore deferred rather than smuggled into this slice.

Accordingly, the implementation child must not add a role/category field and must not teach the
learner to encode whirlpool using a low `tid` value. The bridge may explain the early↔late
**in-boil** direction and must clearly state that true post-boil whirlpool/hop-stand planning is
not yet represented by this App surface.

---

## 6. Session-state/save/reopen implications

None beyond what already exists. This task introduces no new session-state key bound to
persisted recipe data — the only new optional state is the bridge `st.expander`'s own
open/closed cosmetic flag, which Streamlit manages implicitly (no explicit session-state
variable is required unless the implementation child wants it to remember its state across
reruns, which is optional polish, not a requirement — mirrors the Mesking contract's §8). No
change to `valgt_humle`, any `humle_*_{j}_v{_v}` widget key, or `_pending_humle_gram`. Because
§5 introduces no new field, save/load/export/import (§1.7) are entirely unaffected — there is
nothing new to hydrate on load, clear on a blank/new-recipe transition, or reset on copy, unlike
the Gjæring precedent's §5–§7 (which needed a five-transition reset contract specifically
*because* it added a new recipe-scoped field). **DEMO_MODE:** no new guard needed, for the same
reason as both precedents — this bridge introduces no new disk write of its own; it only reads
two static, shipped JSON files via `read_pilot_file()`, in both demo and normal mode.

---

## 7. NO/EN wording contract

New `modules/i18n.py` keys (exact strings authored by the implementation child, not fixed
verbatim here, but constrained as follows), following the `<panel>.laer_bro.<element>` naming
convention already established by `prosess.laer_bro.*`/`gjaering.laer_bro.*`:

| Key | Constraint |
|---|---|
| `koking.laer_bro.tittel` | Short, inviting, collapsed-by-default label — same tone as `prosess.laer_bro.tittel`/`gjaering.laer_bro.tittel`, adapted to hop timing (e.g. "🎓 Hvorfor påvirker humle-tidspunkt ølet?" / "🎓 Why does hop timing affect the beer?"). |
| `koking.laer_bro.guardrail` | Must state, in both languages: (a) for **in-boil additions**, a shorter positive boil time generally moves the plan toward the late/aroma direction and lower — **not zero** — utilization than a longer boil time, without promising a fixed sensory outcome; (b) the current "Tid (Min)" field, IBU/gram calculator and brewday timing model active-boil minutes only and do **not** represent flameout/whirlpool/hop-stand as a separate technique; (c) therefore the learner must not encode a true whirlpool simply by entering an arbitrary low minute value and treating the resulting IBU/brewday timing as whirlpool-aware. Do not invent a corrective minute offset, temperature, utilization percentage or compensation formula. |
| `koking.laer_bro.footer` | Plain-text pointer to the Bryggeskole Koking module — same "Want to practice more? Open Brew School → X" shape as the two precedent footers, not a working navigation control (§4). |

`bryggeskole.feil.innhold_ugyldig` (the existing shared invalid-pilot-content error key, already
used by `ui/process_panel.py`, `ui/yeast_panel.py`, and `ui/bryggeskole_panel.py`) is reused
unchanged — no new error string is minted for this bridge.

---


## 8. Fail-closed behavior

- **Invalid pilot content:** identical to both precedents — a caught `PilotContentError` renders
  the existing shared error string and returns early, never raising past `render_hop_panel()`
  into a crashed `tab_oppskrift`.
- **The planner's whirlpool blind spot is disclosed, not silently left implicit, and not
  "fixed."** This task does not change `modules/calculations.py`'s Tinseth implementation,
  `modules/brewday_calc.py`'s derived reporting, or add a whirlpool-aware branch to either.
  The `koking.laer_bro.guardrail` string must state that the current field is an
  active-boil-time planner and that a true flameout/whirlpool/hop-stand is **not representable
  here yet**. This is safer than accepting a fake numeric encoding and merely warning that its
  IBU may be wrong.
- **No new failure mode is introduced.** The bridge is read-only display; it never writes to
  `valgt_humle`, any hop-row widget key, or any persisted field.

---


## 9. Transfer/application acceptance scenario

Mirroring both precedents' §9 — a human acceptance step, separate from and in addition to the
automated tests in §10:

- **Setup:** the evaluator is given a recipe with one hop addition boiled for a long duration and
  a goal that also calls for more late-hop aroma character. The exact style and numbers must be
  different from the authored Koking/humle questions.
- **Task:** after reading the bridge's four chunks, the evaluator proposes a concrete **in-boil**
  timing change (for example adding a second shorter-boiled addition while retaining an early
  bittering addition) and explains, in their own words, (a) why the shorter-boiled addition moves
  in the late/aroma direction, (b) why it can still contribute bitterness rather than "zero,"
  and (c) that a true flameout/whirlpool/hop-stand is a different technique which this current
  `Tid (Min)` planning field cannot represent faithfully.
- **Observable PASS criteria (all three required):** (1) the proposed change is a coherent
  application of the bitterness/aroma trade-off without claiming one fixed correct schedule;
  (2) the rationale uses the verified time/utilization/aroma direction in the evaluator's own
  words; (3) the evaluator does **not** fake a whirlpool by entering an arbitrary low boil-time
  number and explicitly recognizes the current planner boundary.
- **Observable FAIL criteria (any one):** the learner claims late/whirlpool means zero bitterness;
  treats a low `Tid (Min)` value as a faithful whirlpool representation; treats the resulting
  IBU as whirlpool-aware; or gives no rationale beyond "the app told me."
- **Method and scope:** representative human acceptance evidence only; no owner-as-student gate,
  no new schema, no new authored pilot/registry content, no scoring UI or mastery-store change.

---

## 10. Automated test plan for the implementation child

1. **New `tests/test_hop_panel.py`** (no such file exists today — confirmed by directory
   listing), using the same `AppTest`-driven pattern as `tests/test_process_panel.py`'s
   `TestLaerBroMeskingBridge` (`ui/process_panel.py:134-150`'s test counterpart):
   - the bridge expander exists and is collapsed by default, rendered exactly once regardless of
     how many hop rows are present (including after adding a second/third row via the "➕ Legg
     til humle" button and after deleting the default row);
   - it renders `CHUNK-BOILHOP-C/D/E/F` unchanged, in that order, matching
     `pilot_boil_hop.render_chunk(..., "no")`/`"en"` output exactly, and does **not** render
     `CHUNK-BOILHOP-A`/`B`;
   - the `koking.laer_bro.guardrail` string renders inside the same expander, visually
     distinguished from the chunk text, for both `no` and `en`, and explicitly says the
     current field models active-boil timing rather than whirlpool/flameout/hop-stand;
   - an invalid pilot file (mocked `PilotContentError`) shows the shared error string and never
     crashes `tab_oppskrift`;
   - existing row behavior is unchanged: the hop-row dict shape remains exactly
     `{"id", "gram", "tid"}`, adding/removing/editing a row still works identically to before
     this bridge existed, and no new session-state key beyond the cosmetic expander state is
     created.
2. **`tests/test_kbh_contract.py` / `tests/test_kbh_import.py`** — unchanged, run as regression
   only (no new assertion required, unlike the Gjæring precedent's explicit non-leak test —
   there is no new field here to leak, per §5/§6).
3. **`tests/test_hop_boil_time_validation.py` / `tests/test_hop_boil_time_ui_integration.py`** —
   unchanged, run as regression proof that `_bygg_humle_entry`'s `tid_over_koketid`/
   `tilsatt_etter_min` derivation and the brewday-plan warning flow are untouched by this task.
4. **`tests/test_pilot_boil_hop.py`** — unchanged; this issue and its implementation child make
   no edit to `bryggeskole/pilot_boil_hop.py`, `pilot_boil_hop_fundamentals.json`, or
   `course_fact_registry.json` (§3).
5. Full Python suite (`python3 -m unittest discover -s tests -b`) at the implementation child's
   final checkpoint, per [`.claude/rules/testing.md`](../../.claude/rules/testing.md).

This document itself only requires confirming every cited file:line still resolves against
current master, done as part of writing it.

---

## 11. Explicit non-goals

Restated from the governing issue, since this document's own recommendations must not silently
cross them:

- No App/UI implementation was made in this issue.
- No Course Fact Registry mutation was made in this issue (§3 recommends none).
- No pilot-content mutation was made in this issue (`bryggeskole/pilot_boil_hop.py`,
  `pilot_boil_hop_fundamentals.json`, `boil_timeline.py` all untouched).
- No `modules/calculations.py` (Tinseth IBU math) or `modules/brewday_calc.py` mutation — the
  calculator's whirlpool blind spot is disclosed (§8), never patched, corrected, or given a
  compensation formula.
- No `.kbhrecipe`/Core schema mutation, and none is recommended (§5 explicitly finds none
  needed).
- No `.kbhbrew` schema mutation.
- No broad hop encyclopedia, no IBU math lesson, no supplier/product recommendations, no
  automatic recipe optimization, no generalized course framework.
- No retrofit of i18n onto `ui/hop_panel.py`'s pre-existing hardcoded strings beyond this
  bridge's own new copy (§4).
- No Web/public deploy, no Sóti/AI, no broader Learn→Plan bridges for cool/transfer or package
  in this issue.
- No merge/deploy.

## Hard non-goals

(Restated verbatim from issue #386 for traceability — this document does not violate any of
these.)

- AI is not the source; only existing verified Registry claims may drive instructional
  statements.
- No new fact may be marked verified without concrete source/provenance review.
- No broad hop encyclopedia.
- No IBU math lesson.
- No supplier/product recommendations.
- No automatic recipe optimization.
- No generalized course framework.
- No Web/public deploy.
- No Sóti/AI integration.
- No recipe/Core schema extension unless the audit proves it is strictly required — the audit
  concludes it is **not** required for this bounded slice (§5), and this document does not
  implement one regardless; prefer reusing existing hop recipe fields (done — §2/§5 reuse the
  existing `tid` field unchanged).
- No implementation in this issue.

---


## 12. One bounded implementation recommendation

A single implementation child should add the `st.expander` bridge described in §4 to
`ui/hop_panel.py::render_hop_panel()`, importing `bryggeskole.pilot_boil_hop` and `ui.i18n`
exactly as `ui/process_panel.py`/`ui/yeast_panel.py` already do for their own bridges; add the
three `koking.laer_bro.*` i18n keys (§7) to `modules/i18n.py`'s NO/EN blocks; add no new
persisted field, session-state key, or calculation change; explicitly scope the existing
`Tid (Min)` control to **in-boil additions** and disclose that true
flameout/whirlpool/hop-stand is not representable by that field; and cover it with the test plan
in §10. No calculation, brewday, schema or hop-row-shape change belongs in this child.

---


## 13. Remaining owner/Chief decisions

None identified for this bounded implementation. The existing numeric field is sufficient for
the selected **early↔late in-boil** timing decision, while the audit also proves that
whirlpool/flameout/hop-stand is a distinct unsupported planning dimension. That unsupported
dimension is explicitly deferred rather than misrepresented, so this slice needs no schema
change or owner tie-break.

A future product round may decide whether explicit post-boil hop techniques deserve a
recipe/Core representation that is understood consistently by planning, IBU estimation and
brewday reporting. That future decision is not a prerequisite for this bridge.

---

