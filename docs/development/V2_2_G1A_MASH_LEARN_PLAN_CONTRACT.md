# V2.2 Goal 1A — Learn → Plan Mesking: practical guidance + UX contract

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#344](https://github.com/Joludvig/kvernhaug-brygghus/issues/344), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 1: Learn → Plan),
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction),
[#199](https://github.com/Joludvig/kvernhaug-brygghus/issues/199) (Production Workflow V2)
Authoritative base at creation: `e250eaebdda646c9797e53539b226bbb5b06b706`

This is a decision/prep document only. It contains **no product implementation** — see
[Hard non-goals](#hard-non-goals). Chief must review this contract before any implementation
child issue is opened.

---

## 1. Current-state audit

### 1.1 `bryggeskole/data/course_fact_registry.json` — Mesking-relevant verified records

| ID | Classification | Status | Claim (summarized) |
|---|---|---|---|
| `FACT-MASH-0001` | `documented_fact` | `verified` | Alpha-/beta-amylase break down starch during mashing; not all of it converts to fermentable sugar — some becomes unfermentable dextrins. |
| `FACT-MASH-0002` | `documented_fact` | `verified` | In a study varying mash temperature 65–80°C, increasing mash temperature *within that exact range* reduced wort fermentability; mash thickness also mattered. Explicitly scoped: must not be read as generic beginner mash-temperature guidance without a separate source supporting that broader claim. |
| `FACT-MASH-0003` | `documented_fact` | `draft` | Iodine test explanation. Not promoted (issue #337 — needs a second independent source). Not referenced by any shipped pilot content. |
| `FACT-MASH-0004` | `professional_interpretation` | `verified` | Mash temperature is one of several factors (also mash thickness/water-to-grist ratio, malt enzyme content) affecting fermentability; no single mash temperature is universally correct for every recipe. |

Both `FACT-MASH-0002` and `FACT-MASH-0004` are consumed, unmodified, by
`bryggeskole/data/pilot_mashing_fundamentals.json` (`CHUNK-MASH-B`, `CHUNK-MASH-C`,
`Q-MASH-002`, `Q-MASH-003`) via `bryggeskole/pilot_mashing.py`'s verified-only
`source_claims` resolution (`get_verified_record`, §18 of
[BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md)). The pilot
chunk text is already careful, hedged and range-scoped — it explicitly says "this shows a
direction from one specific study, not a fixed answer for exactly how much it matters in your
own brewing" (`CHUNK-MASH-B`) and "there is no single, universal mash temperature that is
correct for every recipe" (`CHUNK-MASH-C`).

**Two of the three sources cited in issue #344's body (Evans et al. 2005, and the constant-72°C
isothermal study) are not yet Course Fact Registry records at all.** Only Muller 1991 is
registered, as `FACT-MASH-0002`. This is a scope note carried into §3 and §4 below — it does not
block this decision, but no claim in this document treats Evans 2005 or the 72°C study as
verified Bryggeskole knowledge, since neither is.

### 1.2 `bryggeskole/pilot_mashing.py`

Pure, stdlib-only, fail-closed pilot-content validator/renderer (topic-scoped copy, mirroring
`pilot_fermentation.py`'s architecture, per issue #337). Exposes `read_pilot_file()`,
`render_chunk(chunk, language)`, `render_question(question, language)`,
`evaluate_answer(question, selected_option_id, language)`. `render_chunk()` returns a plain
dict with `id`, `text` (already resolved to one language), `source_claims`. No Streamlit
dependency — safe to call from `ui/process_panel.py` exactly as `ui/bryggeskole_panel.py`
already calls it.

### 1.3 `ui/bryggeskole_panel.py`

Fully self-contained two-module (Mesking/Gjæring) learning UI, rendered as its own top-level
Streamlit tab (`tab_bryggeskole` in `app.py`). Session state is **per-module**
(`st.session_state["bs_modul_sesjon"][modul_id]`), never global, and mastery persists via
`bryggeskole/mastery_store.py` (or a `DEMO_MODE` session overlay). Nothing here currently
reads or writes anything on the App's recipe/process-profile side — Bryggeskole and the
planning surfaces are two disjoint session-state trees today.

### 1.4 `ui/process_panel.py`

Renders as part of `tab_bryggdag` (`app.py` line ~178), immediately above `render_water_panel`
and `render_brewday_panel`. Owns the "🌡️ Meskesteg (redigerbare)" expander
(`ui/process_panel.py:243`), where the learner edits each mash step's `temperatur`/`varighet`/
`stegtype`/`kommentar` via per-step widgets. The currently selected standard profile's static
`forventet_paavirkning` text (see §1.5) is shown as a caption just above that expander
(`ui/process_panel.py:234-235`), already in the right visual position for a Learn → Plan bridge
to attach to.

### 1.5 `modules/process_profiles.py` — the factual mismatch

`STANDARDPROFILER["hochkurz"]` (lines 75–111) contains stronger practical wording than the
registry currently supports:

```python
"beskrivelse": (
    "Klassisk tysk to-trinns stegmesk: en beta-amylase-hvile "
    "(mer gjærbart sukker, tørrere øl) etterfulgt av en "
    "alfa-amylase-hvile (mer kropp/uforgjærbart sukker) og mashout. ..."
),
...
"forventet_paavirkning": (
    "To separate hviler gir brygger bedre kontroll over "
    "gjærbarhet/kropp enn én enkelt temperatur — vanligvis noe "
    "tørrere og renere enn en tilsvarende enkel infusjon ved samme "
    "gjennomsnittstemperatur."
),
```

mash_steps: `63°C` beta rest, `70°C` alpha rest (`_steg(63, 40, ...)`, `_steg(70, 30, ...)`).

This is App copy (module docstring text shown in the UI), not a Course Fact Registry record —
it carries no `source_claims` and is not validated against the registry at all. It is exactly
the mismatch issue #344 asks this document to resolve *before* connecting Bryggeskole to the
planning controls.

### 1.6 Recipe save/load path for `process_profile`

`process_profile` is already a first-class, independently persisted recipe field, fully
separate from the malt/hop/yeast ingredient lists:

- `modules/recipe_context.py:31` reads `st.session_state["aktiv_prosessprofil"]` into `ctx`.
- `modules/recipe.py:97` stores it on the recipe dict as `process_profile`.
- `modules/kbh_contract.py:215-217` and `modules/kbh_import.py:485,563` round-trip it through
  the KBH export/import contract (`payload["prosess"]`).
- `ui/sidebar.py:173-174` and `modules/kbh_import_apply.py:84-85` restore it on load, **always**
  through `modules/process_profiles.normaliser_prosessprofil()` — the one common
  repair/normalization boundary (§1.7) — never the raw stored dict directly.
- `ui/process_panel.py:88-121` (`_bygg_aktiv_profil`) rebuilds the full active profile from live
  widget state on every render and writes it back to
  `st.session_state["aktiv_prosessprofil"]` (line 404), which is what gets persisted.

### 1.7 `normaliser_prosessprofil()` — already the single normalization boundary

`modules/process_profiles.py:229-271`. For a known standard `process_id` (e.g. `hochkurz`), it
**always** returns a fresh deep copy of the canonical standard profile's own `mash_steps` —
never whatever was stored/edited before — except `brukernotater`, which passes through
unchanged. For `process_id == "egendefinert"`, the user's own edited steps are the entire point
and pass through unchanged. `ui/process_panel.py` calls this on every "new recipe loaded or
inconsistent state detected" branch (lines 176–197) and shows a toast if a repair happened. This
means editing a mash step's temperature already persists and reopens safely today — no new
schema or persistence work is needed for a Learn → Plan task that targets this field (see §4).

---

## 2. Exact factual mismatch(es)

1. **Hochkurz's `forventet_paavirkning` comparative claim is unsupported by any cited source.**
   No source in the registry, nor any of the three sources in issue #344's body, compares a
   stepped mash against a single-infusion mash *at the same average temperature*. All three
   sources are single-vessel, single (or varied) temperature studies of fermentability as a
   function of mash temperature — none tests mashing *methodology* (stepped vs. infusion) as
   the independent variable. "vanligvis noe tørrere og renere enn en tilsvarende enkel infusjon
   ved samme gjennomsnittstemperatur" is a claim about a comparison nobody in scope actually ran.

2. **Hochkurz's 63°C beta rest sits outside `FACT-MASH-0002`'s own explicitly stated scope.**
   `FACT-MASH-0002`'s `notes` field says exactly: "the claim is deliberately scoped to the exact
   65–80°C range... it must not be read as generic beginner mash-temperature guidance... without
   a separate source that supports that broader, practical-brewing claim." 63°C is below that
   range's floor. The directional claim itself (lower temperature region → more fermentable
   wort) is well-established enzyme biochemistry and is *not* being disputed here — but citing
   it as if `FACT-MASH-0002` directly covers a 63°C decision overstates what that specific
   registry record actually verified.

3. **The 70°C alpha rest is directionally inside `FACT-MASH-0002`'s scope** (65–80°C) and its
   directional claim (higher temp in that range → less fermentable, more unfermented
   carbohydrate = more body) is consistent with the study direction. This one is *not* a
   mismatch on direction — only §2.1's comparative overclaim and §2.2's out-of-range citation
   are.

No mismatch exists on the Bryggeskole/pilot-content side itself (§1.1): `CHUNK-MASH-B`/
`CHUNK-MASH-C` and their questions are already correctly hedged and range-scoped. The mismatch
is entirely in `modules/process_profiles.py`'s App-side copy, which predates and was never
checked against the registry.

---

## 3. Source-to-claim mapping

| Process-profile claim | Supported by | Verdict |
|---|---|---|
| Beta rest (~63°C) → more fermentable sugar / drier beer (directional only) | General enzyme biochemistry (beta-amylase more heat-labile, favored at lower mash temps); *directionally* consistent with `FACT-MASH-0002`'s 65–80°C finding extrapolated downward, but 63°C itself is outside that study's tested range | **Directionally supportable, but must not cite `FACT-MASH-0002` as if it covers 63°C specifically** — needs hedging language, not a precise-sounding rule |
| Alpha rest (~70°C) → more body / more unfermentable sugar | `FACT-MASH-0002` (65–80°C range, Muller 1991) | **Supportable**, 70°C is inside the tested range and the direction matches |
| "Two rests typically give a drier/cleaner result than a single infusion at the same average temperature" | *No source* — none of the registry's or issue #344's cited sources compare mashing methodology at matched average temperature | **Not supportable — must be weakened or removed** |
| "No single mash temperature is universally correct for every recipe" (general framing, already used correctly in Bryggeskole) | `FACT-MASH-0004` | Supportable, already correctly scoped in the pilot content |

Evans et al. 2005 and the 72°C isothermal study (sources B and C in issue #344's body) are
**not yet registry records** (§1.1) — they are not used to support any claim in this table,
and no recommendation in §4 below treats them as verified Bryggeskole knowledge. Whether to
promote either of them to a new `FACT-MASH-00xx` record is a separate, future editorial
decision (registry mutation is out of scope for this issue — see [Hard non-goals](#hard-non-goals)).

---

## 4. Recommended fact-registry change(s)

**None, for the Learn → Plan bridge itself.** The safe practical contract sketched in issue
#344's body —

> Mash temperature is a directional lever on wort fermentability, not a precise FG/body dial...
> a target around the mid-60s can favor higher fermentability than a substantially warmer mash
> around ~70–72°C, but actual results also depend on malt/enzyme properties, mash thickness,
> time, pH and the wider process.

— is already assemblable, near-verbatim, from the **existing** `CHUNK-MASH-B` (`FACT-MASH-0002`)
+ `CHUNK-MASH-C` (`FACT-MASH-0004`) pair, without a new record. The Learn → Plan bridge (§6)
should point at these two existing verified chunks directly rather than author new teaching
copy or register a new fact for this task. This satisfies §344's own instruction #7 ("reuse
existing pilot/registry truth rather than duplicating teaching copy").

A future, separately authorized round *could* register Evans 2005 and/or the 72°C isothermal
study as new `FACT-MASH-00xx` records to broaden the evidence base for `FACT-MASH-0002`'s
65–80°C claim (e.g. Evans 2005's wider tested range would let a future record state the
direction more generally). That is explicitly **not** required to unblock the Learn → Plan
bridge and is not recommended as part of this issue's implementation child — flagged here only
so it isn't silently forgotten.

---

## 5. Process-profile copy corrections required (for the implementation child — not made here)

`modules/process_profiles.py`, `STANDARDPROFILER["hochkurz"]`:

1. **Remove or hedge the single-infusion comparison** in `forventet_paavirkning`. Replace the
   unsupported "vanligvis noe tørrere og renere enn en tilsvarende enkel infusjon ved samme
   gjennomsnittstemperatur" with language that states only what the sources support: that the
   two rests let the brewer aim more deliberately at a fermentability/body trade-off than a
   single temperature choice does — without claiming a predictable outcome relative to any
   specific single-infusion baseline.
2. **Hedge the 63°C beta-rest claim** in `beskrivelse` so it reads as directional guidance
   (consistent with general enzyme behavior and the *direction* `FACT-MASH-0002` reports) rather
   than as if a specific verified study measured exactly that temperature.
3. **Leave the 70°C alpha-rest claim's direction as-is** — it is the one directional claim in
   this profile that sits inside `FACT-MASH-0002`'s own tested range.
4. No other `STANDARDPROFILER` entry (`enkel_infusjon`, `enkel_dekoksjon`, `reiterated_mash`,
   `egendefinert`) makes a mash-*temperature*-to-fermentability claim that needs correction.
   `enkel_dekoksjon`'s `forventet_paavirkning` claim (melanoidin/Maillard flavor development
   from boiling a mash portion) is a different topic (decoction technique, not mash
   *temperature*) and is out of this issue's audit scope.

This issue makes **no edit** to `modules/process_profiles.py` (hard non-goal, per §344 and
[§ below](#hard-non-goals)) — the implementation child issue must make exactly the three edits
above, nothing broader, and must not otherwise touch `mash_steps` values, other profiles, or
UI copy.

---

## 6. Exact selected Learn → Plan user task

**Task:** while a learner is choosing or editing a mash step's temperature in the existing
"🌡️ Meskesteg (redigerbare)" expander (`ui/process_panel.py:243`), they can open a small,
contextual explanation of *why* mash temperature matters for their beer — grounded in the same
verified Mesking content already taught in the Bryggeskole Mesking module — without leaving the
Bryggdag tab or losing their in-progress recipe/process-profile edits.

This is deliberately the **cheapest possible instance** of Learn → Plan: it does not gate,
validate, or auto-set anything. The learner's actual planning decision — what temperature to
put in the `temperatur` field — is unchanged in mechanism; the bridge only adds an optional,
in-context "why" alongside the existing editable field.

---

## 7. Exact UX bridge contract

**No tab jump.** `app.py` renders `tab_oppskrift`/`tab_innkjop`/`tab_bryggdag`/`tab_verktoy`/
`tab_bryggeskole` as sibling `st.tabs()` panes (§1.4); Streamlit has no supported API to
programmatically activate a different tab and no reliable way to scroll back to a prior
in-tab position afterward. A "jump to Bryggeskole tab, then jump back" design would be
exactly the brittle architecture issue #344 itself warns against forcing.

**Chosen bridge: an `st.expander` rendered directly inside `render_process_panel()`**, placed
immediately below the existing `forventet_paavirkning` caption (`ui/process_panel.py:234-235`)
and above the "🌡️ Meskesteg (redigerbare)" expander, so it sits exactly where the learner is
already looking when they're about to edit a temperature.

- Label: a short, inviting string (e.g. "🎓 Hvorfor påvirker mesketemperatur ølet?" /
  "🎓 Why does mash temperature affect the beer?"), collapsed by default — it must never push
  the existing editable mash-step fields further down by default, since those are the primary
  controls on this panel.
- Content: rendered by calling `bryggeskole.pilot_mashing.read_pilot_file()` once per panel
  render (same pattern `ui/bryggeskole_panel.py:692-696` already uses, including catching
  `PilotContentError` and showing a graceful fallback instead of crashing the whole Bryggdag
  tab if the pilot content is ever invalid) and `render_chunk()`-ing exactly `CHUNK-MASH-B` and
  `CHUNK-MASH-C`, in that order, in the learner's current language (`ui.i18n.gjeldende_sprak()`,
  same as `ui/bryggeskole_panel.py`). No new teaching copy is authored in `ui/process_panel.py`
  itself — every sentence shown here already exists, verified, in the pilot content.
- A one-line footer link/caption pointing at the full Bryggeskole Mesking module
  ("Vil du øve mer? Åpne Bryggeskole → Mesking" / "Want to practice more? Open Bryggeskole →
  Mesking") — plain text, not a working in-app navigation control, since no reliable
  cross-tab jump exists (see above). This sets learner expectations correctly instead of
  promising a jump the UI can't deliver.
- **No mastery interaction here.** `evaluate_answer()`/`apply_answer()`/mastery persistence are
  never called from this bridge — mastery state remains owned exclusively by
  `ui/bryggeskole_panel.py`'s own module flow (§1.3). This keeps the bridge read-only and avoids
  a second, competing entry point into the mastery store.

**Reuse boundary, stated plainly:** the bridge imports `bryggeskole.pilot_mashing` directly,
exactly the same cross-module import pattern `ui/bryggeskole_panel.py` already uses for its own
two pilot modules (§1.3) — no new shared "engine" module, no duplicated chunk text, no new
Course Fact Registry record (§4).

---

## 8. State/persistence contract

- **No new session-state keys beyond one, purely cosmetic, expander-open/closed key** (Streamlit
  manages `st.expander`'s own open/closed state implicitly when given a stable key — no explicit
  session-state variable is required unless the implementation child wants the expander to
  remember its open/closed state across reruns, which is optional polish, not a requirement).
- **No change to `aktiv_prosessprofil`, `process_profile`, or any existing recipe-persistence
  path** (§1.6–§1.7). The bridge is read-only display; it never writes to
  `st.session_state["prosess_mash_steps"]` or any other widget-bound key the existing mash-step
  editor owns.
- **No change to Bryggeskole mastery state** (`bryggeskole/mastery_store.py`,
  `st.session_state["bs_modul_sesjon"]`) — the bridge reads `read_pilot_file()`/`render_chunk()`
  only, both pure and side-effect-free (§1.2).
- **DEMO_MODE:** the bridge introduces no new disk write, so it needs no new `DEMO_MODE` guard
  beyond what already exists — `read_pilot_file()` only ever reads two static JSON files
  (`pilot_mashing_fundamentals.json`, `course_fact_registry.json`), which are shipped content,
  not per-user data, in both demo and normal mode.

---

## 9. Acceptance/test plan for the implementation child

1. `tests/test_process_panel.py` — extend with a new AppTest-style case asserting the new
   expander renders, is collapsed by default, and its resolved chunk text matches
   `pilot_mashing.render_chunk(CHUNK-MASH-B/C, language)` for both `no` and `en` (mirroring the
   existing pattern already used for i18n assertions elsewhere in this suite).
2. `tests/test_process_profiles.py` — extend with assertions on the corrected `hochkurz`
   `beskrivelse`/`forventet_paavirkning` text: (a) it no longer contains an unsupported
   single-infusion comparison string, (b) the 63°C/70°C `mash_steps` values themselves are
   unchanged (§5 is a copy-only correction, never a `mash_steps` value change).
3. `tests/test_pilot_mashing.py` — unchanged; this issue and its implementation child make no
   edit to `bryggeskole/pilot_mashing.py`, `pilot_mashing_fundamentals.json`, or
   `course_fact_registry.json` (§4).
4. Manual verification (implementation child, not this issue): open the Bryggdag tab, confirm
   the new expander appears above the mesk-step editor for every process profile (not just
   Hochkurz — the bridge is temperature-education, not Hochkurz-specific), confirm it never
   auto-expands, and confirm editing a mash-step temperature afterward still saves/reloads
   correctly through a full recipe save → reload cycle (exercising §1.6/§1.7's existing path,
   unchanged by this feature).
5. Full Python suite (`python3 -m unittest discover -s tests -b`) at the implementation child's
   final checkpoint, per [`.claude/rules/testing.md`](../../.claude/rules/testing.md).

This document itself only requires: `git diff --check` (below) and confirming every repo path
cited above still resolves against current master, both done as part of writing it.

---

## 10. Explicit non-goals

Restated from the governing issue, since this document's own recommendations must not silently
cross them:

- No App/UI product code changes were made in this issue.
- No Course Fact Registry mutation was made in this issue (§4 recommends none for the bridge
  itself; a possible future registry expansion is flagged, not performed).
- No pilot-content mutation was made in this issue.
- No process-profile copy mutation was made in this issue (§5 specifies the corrections; the
  implementation child performs them).
- No new schema was introduced (§6–§8 confirm the existing `process_profile`/`mash_steps` shape
  is sufficient).
- No Web Bryggeskole, standalone app work, Goal 2/3/4 work, Sóti work, or broader course
  expansion is in scope here.
- No merge/deploy.

## Hard non-goals

(Restated verbatim from issue #344 for traceability — this document does not violate any of
these.)

- no App/UI product code changes;
- no Course Fact Registry mutation in this issue;
- no pilot-content mutation in this issue;
- no process-profile copy mutation in this issue;
- no new schema;
- no Web Bryggeskole;
- no standalone app work;
- no Goal 2/3/4 work;
- no Sóti work;
- no broad course expansion;
- no merge/deploy.

---

## 11. Remaining owner decision

None identified. Every question in issue #344's "Required repo audit" and "Required UX
decision" sections was resolvable from existing principles/precedent already established in
this codebase (the verified-only Course Fact Registry boundary, `normaliser_prosessprofil()`'s
existing persistence guarantee, and `st.tabs()`'s documented lack of programmatic switching).
No genuine product choice in this slice required an owner tie-break beyond Chief's review of
this contract itself.
