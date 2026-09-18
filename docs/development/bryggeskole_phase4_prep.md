# Bryggeskole PREP — Phase 4 minimal usable-module slice after V2-3B (issue #325)

*PREP / source-audit document only. No product code, no UI implementation, no
V2-3C adaptive/spaced-repetition logic, no new course facts/topics, and no
Web/App/Core/Sóti/Brew Lab file changes were made to produce this document —
per issue #325's own hard gate. It defines the smallest coherent
post-novice-gate implementation slice and ends with an implementation-ready
issue template that is **not** created or armed.*

Read against current `master` at
`b22413a3cbde7a0efd3578083a13ea615677dd99`.

## 0. Naming/scope disambiguation (read this first)

Two things in this repo are easy to conflate with the "Phase 4" this
document is about. Neither is an error — both are intentional, separate
tracks — but citing either without this note risks confusion:

1. **Two unrelated "Bryggeskole" efforts.** (a) `web/hjelp/` — a set of
   already-shipped static help pages, referred to as "Bryggeskole P0–P3B" in
   `docs/PROJECT_STATUS_AUGUST_2026.md`. (b) The `bryggeskole/` Python
   package audited below (Course Fact Registry, fermentation pilot, mastery
   model — issues #65/#78/#89/#91/#93/#95/#97/#317). This document is about
   (b) only.
2. **"Phase 4" and the "Phase 3A novice gate" belong to the portfolio
   roadmap, not to the `bryggeskole/` package itself.** Roadmap V2.1
   ([#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101))
   sequences work across *all* product areas (Web, App, Bryggeskole, Brew
   Lab, Sóti) into Phases 0–5. Its **Phase 4 — "Complete learning loop"**
   text is:
   > After stabilization/acceptance: resume Bryggeskole pilot from the
   > already-built verified facts/content/mastery foundation; add only the
   > smallest UI/repetition layer needed to test one usable module; use
   > Learner findings to place verified teaching at actual decision points.
   > Do not expand course breadth first.

   This is a deliberate cross-domain sequencing decision (finish Web/App
   trust and prove Phase 3A Learner/Master novice-readiness *before*
   building more Bryggeskole surface), not a technical dependency between
   the `bryggeskole/` package and the Web Learner/Master mode code. The two
   remain architecturally separate domains
   (`docs/development/KBH_CORE_CONTRACT.md`'s domain-ownership table:
   *"Bryggeskole — Brewing research, explanation, and pedagogy"*, distinct
   from *App*/*Web*).
3. **The hard gate itself.** Phase 3A's protocol
   (`docs/development/phase3a_novice_acceptance_protocol.md`, issue #278,
   PR #280) is Chief-approved and awaiting an owner GO/NO-GO
   (`KBH_GO_READY_V1 issue=278`), but the actual *human* novice run — one
   real person completing the task in Learner mode without oral coaching —
   is the part no document or PR can satisfy. Per issue #325's own text,
   that run lives in "the owner-only acceptance issue created after #278";
   this audit did not locate that issue's number in any doc reachable from
   `master` (it is evidently tracked as a live, owner-run task rather than
   a written artifact) and does not invent one. Implementation of this
   Phase 4 slice remains blocked on that human result, whatever issue ends
   up recording it.

## 1. Current foundation on master

| Layer | File(s) | Status |
|---|---|---|
| Course Fact Registry V1 + verified-only API | `bryggeskole/course_fact_registry.py` (399 lines) | Done (#89, #91) |
| Fermentation fact pack | `bryggeskole/data/course_fact_registry.json` (3 verified facts, `FACT-BREW-0001..0003`) | Done (#93) |
| V2-3A fermentation pilot content/questions | `bryggeskole/pilot_fermentation.py` (409 lines) + `bryggeskole/data/pilot_fermentation_temperature.json` (3 chunks, mixed concept-check/scenario questions) | Done (#95) |
| V2-3B hidden mastery model + local persistence | `bryggeskole/mastery.py` (357 lines, pure) + `bryggeskole/mastery_store.py` (112 lines, I/O boundary) | Done (#97; current code on master landed via the #322 refresh/transplant `13ca793`, byte-identical to the originally approved `5b2545c`) |
| V2-3C adaptive scheduler/UI | — | **Does not exist.** Confirmed no reference anywhere except as an explicit non-goal in `mastery.py`'s own docstring. |

All four `bryggeskole/*.py` modules are stdlib-only, side-effect-free
(no network, **no Streamlit import**), and explicitly documented as "not
wired into any UI yet" (`mastery_store.py` docstring). Nothing in `app.py`,
`ui/**`, or `modules/**` currently imports `bryggeskole` at all — the only
consumer anywhere in the app is a separate CLI chat tool, `soti/tools.py`
(`hent_verifisert_fagfakta`), and it only calls the Course Fact Registry's
verified-only API — never the pilot or mastery layers.

Test coverage today (all green at HEAD, `python3 -m unittest
tests.test_course_fact_registry tests.test_pilot_fermentation
tests.test_bryggeskole_mastery tests.test_bryggeskole_mastery_store
tests.test_soti_course_fact_registry_tool` → 201 tests, OK):

| Test file | Tests | Covers |
|---|---|---|
| `tests/test_course_fact_registry.py` | 65 | Registry schema/validation + verified-only API |
| `tests/test_pilot_fermentation.py` | 42 | Pilot content validation + render/evaluate helpers |
| `tests/test_bryggeskole_mastery.py` | 48 | Pure mastery-update/label logic |
| `tests/test_bryggeskole_mastery_store.py` | 10 | Local JSON persistence, atomic writes |
| `tests/test_soti_course_fact_registry_tool.py` | 36 | Sóti chat-tool consumer (registry only) |

No dedicated markdown design doc exists yet for V2-3A/V2-3B — the design
record today is module docstrings + issues #95/#97. This document is the
first prose write-up of the reuse surface for those two layers.

## 2. Answers to the required audit questions

### Q1 — Which existing V2-3A/V2-3B APIs are ready to reuse as-is?

All of them, unmodified — this is precisely why the smallest slice (Q2) is
UI-only work:

- `bryggeskole.pilot_fermentation.read_pilot_file()` — loads and validates
  the shipped pilot content against the verified registry.
- `bryggeskole.pilot_fermentation.render_chunk(chunk, language)` /
  `render_question(question, language)` — pure view-models, already
  single-language, already omit the `correct` flag and feedback strings
  pre-answer.
- `bryggeskole.pilot_fermentation.evaluate_answer(question, selected_option_id, language)`
  — returns `{"question_id", "correct", "feedback"}`; never a numeric score.
- `bryggeskole.mastery.apply_answer(state_document, question, correct, now)`
  — pure orchestrator; updates every concept a question declares, derives
  `first_attempt` internally from `answered_questions`.
- `bryggeskole.mastery.mastery_label(concept_state, language)` — the only
  function that should ever reach the learner's screen for mastery state.
- `bryggeskole.mastery_store.read_mastery_state()` /
  `write_mastery_state(document)` — ready-made local JSON persistence,
  atomic writes, missing-file-safe, already env-var-isolatable
  (`KVERNHAUG_BRYGGESKOLE_STATE_DIR`) the same way `modules/pantry.py`'s
  `KVERNHAUG_PANTRY_DIR` is.

None of these four modules need a signature change, a new parameter, or a
behavior change to support the slice below.

### Q2 — Smallest UI surface for a genuinely usable end-to-end pilot

One new panel, `ui/bryggeskole_panel.py`, exporting
`render_bryggeskole_panel()`, following the repo's existing
`ui/<domain>_panel.py` → `render_<domain>_panel()` convention (see
`ui/pantry_panel.py`, `ui/equipment_panel.py`, etc.):

1. Load pilot content once via `read_pilot_file()`.
2. Render each chunk via `render_chunk(chunk, sprak)`, reusing the app's
   existing language state (`ui.i18n.gjeldende_sprak()` / `t()`) — no new
   language mechanism.
3. Render one question at a time via `render_question(question, sprak)`
   (radio/selectbox for options); on submit, call `evaluate_answer(...)`,
   show only its `feedback` string, then `apply_answer(...)` +
   `write_mastery_state(...)`.
4. After the question set is exhausted, show only `mastery_label(state,
   sprak)` per concept the pilot touches — never the raw `mastery`/
   `confidence` floats or `attempts` count.
5. Wire it into `app.py` as **one new entry inside the existing
   `tab_verktoy` tab** (alongside `render_equipment_panel()` etc.) rather
   than a fifth top-level tab — the pilot is one topic (fermentation
   temperature), not a course catalog, so it does not warrant new
   top-level navigation. (A 5th tab is the fallback if the owner later
   decides Bryggeskole deserves permanent top-level placement — that is a
   product decision for the implementation issue, not this PREP.)

No course browser, no topic picker, no multi-module navigation — there is
exactly one pilot topic today, so the smallest slice renders it directly.

### Q3 — Smallest repetition behavior to exercise mastery meaningfully

Do not build a scheduler. The existing `update_concept_state()` already
encodes the one distinction that makes repetition meaningful: a first
attempt gains mastery faster (`MASTERY_GAIN_FIRST_ATTEMPT`) than a
recovery attempt after a prior wrong answer
(`MASTERY_GAIN_RECOVERY`), and an incorrect answer only ever reduces
confidence, never mastery. The smallest UI behavior that actually exercises
this is:

- A **"Prøv igjen" / "Try again"** action that re-serves the *same*
  question set in place once the learner has completed it, re-running
  `evaluate_answer`/`apply_answer` against the *existing* (already
  persisted) mastery state rather than resetting it.
- No due-date, no interval, no "next review at" timestamp, no
  cross-session reminder/notification, no algorithmic selection of "what's
  due" — all of that is V2-3C by the roadmap's own wording and stays out of
  scope.

This is enough to observably move a concept's `mastery_label` upward across
two or three manual retakes in one sitting, which is what "exercise mastery
meaningfully" requires for a usability test — nothing more.

### Q4 — Which states/labels are learner-facing vs. must stay hidden

**Learner-facing:** chunk text (`render_chunk` output), question
prompt/options (`render_question` output), per-answer feedback text
(`evaluate_answer`'s `feedback`), and the four fixed `mastery_label` strings
("Sterkt område"/"Strong area", "God forståelse"/"Good understanding", "På
god vei"/"On the way", "Bør repeteres"/"Should repeat").

**Must stay hidden, always:** the raw `mastery`/`confidence` floats, the
`attempts` integer, `last_tested`, and the internal `answered_questions`
ledger. This is not a new rule the UI has to invent — the underlying layers
already enforce it structurally (`render_question` omits `correct`/feedback
pre-answer; `evaluate_answer` never returns a score;
`mastery_label`'s own test suite asserts no digit ever appears in a label
string). The UI slice's job is simply to never construct its own display
string from the raw state document fields — i.e., never read
`state["concepts"][c]["mastery"]` directly into a template; always go
through `mastery_label()`.

### Q5 — Exact files the later implementation would touch

**New:**
- `ui/bryggeskole_panel.py` — the panel itself.
- `tests/test_ui_bryggeskole_panel.py` — `AppTest`-based coverage (see Q6).

**Modified:**
- `app.py` — one new import + one new call inside the existing
  `tab_verktoy` block (`app.py:14-29` for the import, `app.py:196-201` for
  the call site pattern — see `ui/equipment_panel.py`'s
  `render_equipment_panel()` for the precedent).

**Deliberately NOT touched:**
- `bryggeskole/*.py` and `bryggeskole/data/*.json` — pure reuse, per Q1.
- `modules/**` — the `bryggeskole/` package is its own domain and does not
  need an App-side data-access shim; the panel calls it directly. The one
  open design question this raises (DEMO_MODE) is called out explicitly
  below rather than pre-answered.
- `web/**`, Core, Sóti, Brew Lab — no cross-domain change.

**One design question the implementation issue must decide explicitly**
(not decided by this PREP): where the `DEMO_MODE` write-guard lives.
Every existing persistence module the app has
(`modules/pantry.py`, `modules/kbhbrew_storage.py`, `modules/equipment.py`)
guards writes with `if DEMO_MODE: return` as the first line of the write
function, reading `DEMO_MODE` from `config.py`. `bryggeskole/mastery_store.py`
is deliberately config-agnostic (no Streamlit, no App-specific import) —
its own docstring states "not wired into any UI yet" precisely so this
choice hasn't been forced yet. Two options for the implementation issue to
pick between, not this document:
1. Guard at the `ui/bryggeskole_panel.py` call site (`if DEMO_MODE: return`
   before calling `write_mastery_state`, mirroring the panel-level
   `demo_state`-overlay pattern in `ui/pantry_panel.py:11` for reads), or
2. Add a thin `modules/bryggeskole_state.py` adapter that owns the
   DEMO_MODE guard the same way every other domain does, keeping
   `bryggeskole/` itself untouched either way.
Either keeps `bryggeskole/mastery_store.py` unmodified; the difference is
only which side of the App/`bryggeskole` boundary the guard lives on.

### Q6 — Focused tests that would prove the slice

- `AppTest`-based end-to-end render: chunk text appears, one question
  renders with its options, submitting an answer shows feedback text (not
  a score), and after finishing the set the rendered page shows a
  `mastery_label` string for each pilot concept.
- A regex/string-search assertion over the rendered `AppTest` output that
  **no** raw float (`0\.\d+`) or the literal words `mastery`/`confidence`/
  `attempts` ever appears in what's shown to the learner — the UI-level
  counterpart to the existing `test_no_raw_score_or_grade_in_any_label`
  guarantee already enforced one layer down.
- "Prøv igjen" path: answer once, retake, assert the concept's
  `mastery_label` output is monotonically non-decreasing (never re-tests
  the exact underlying float thresholds — those already have unit
  coverage in `tests/test_bryggeskole_mastery.py`).
- Persistence round-trip through the UI: submit an answer, assert
  `mastery_store.read_mastery_state()` reflects it on disk (using the
  existing `KVERNHAUG_BRYGGESKOLE_STATE_DIR` env-var isolation pattern
  `tests/test_bryggeskole_mastery_store.py` already established — no new
  isolation mechanism needed).
- Whichever DEMO_MODE guard location Q5 lands on: a test proving no file
  under `data/` is written when `DEMO_MODE=1`, following the existing
  `modules/pantry.py`/`modules/equipment.py` DEMO_MODE test pattern.
- `tests.test_course_fact_registry` / `tests.test_pilot_fermentation` /
  `tests.test_bryggeskole_mastery` / `tests.test_bryggeskole_mastery_store`
  stay green unmodified — this slice reuses, never edits, those layers.

### Q7 — What must remain explicitly out of scope

- Any V2-3C adaptive/spaced-repetition scheduler (due dates, intervals,
  "what's due today" selection, cross-session reminders).
- Any new course facts, concepts, or a second pilot topic — this slice
  serves the one existing fermentation-temperature pilot only.
- A course catalog / multi-topic navigation UI.
- Any change to `web/**`, Core, Sóti, or Brew Lab.
- Any change to the Course Fact Registry, the fermentation fact pack, the
  pilot content JSON, or the mastery model/store modules themselves —
  reuse only, per Q1/Q5.
- Starting implementation itself before the real human Phase 3A novice
  gate clears (see §0.3) — this document does not lift that gate.

### Q8 — Learner acceptance findings usable for placement/copy (without conflating domains)

The Web Learner/Master acceptance work
(`docs/development/phase3a_learner_master_acceptance.md`, issue #250, and
`docs/development/phase3a_novice_acceptance_protocol.md`, issue #278) is
about the **Web** app's Learner/Master mode UI and is architecturally
unrelated to `bryggeskole/` (§0.2). Two of its *findings*, however, are
transferable as UX **design principles**, not as shared code or state:

- **"Surface guidance at the actual decision point, not upfront."** Roadmap
  #101's Web backlog item B07 ("Learner guidance must not point at hidden
  content") and Phase 4's own text ("use Learner findings to place verified
  teaching at actual decision points") both point the same direction: the
  fermentation-temperature pilot should be reachable from *where a brewer
  is actually deciding about fermentation temperature* (e.g. near
  `render_process_panel()`'s fermentation step, if/when a later round adds
  that link) rather than only from a disconnected "Verktøy" tab entry. This
  PREP's Q2 recommendation (`tab_verktoy` placement) is the *minimum
  viable* placement for testing the module in isolation; the
  decision-point placement is a follow-up refinement the implementation
  issue may choose to include or defer.
- **"Automated tests cannot prove genuine understanding."** The same
  principle the Phase 3A protocol applies to Web Learner mode applies here:
  passing `AppTest` coverage proves the panel *behaves* correctly, not that
  a learner *understands* the material. No claim of pedagogical
  effectiveness should be made from Q6's tests alone.

No code, session-state key, or persistence mechanism should be shared
between the Web Learner/Master mode and this Bryggeskole panel — they stay
two separate domains per `KBH_CORE_CONTRACT.md`, connected only by these
transferable design principles.

## 3. Implementation-ready bounded issue template (NOT created/armed)

This template is provided for the owner to create and arm once the real
human Phase 3A novice gate (§0.3) clears. It is not created as a GitHub
issue by this PREP round.

```
Title: BRYGGESKOLE V2-3C-lite — minimal usable fermentation-pilot panel (Phase 4 slice)

Part of Roadmap V2.1 #101 Phase 4 ("Complete learning loop"). Prepared by
PREP audit #325 (docs/development/bryggeskole_phase4_prep.md).

## Hard gate
Do not start until the real human Phase 3A novice gate (owner-run, per the
protocol in docs/development/phase3a_novice_acceptance_protocol.md, issue
#278/PR #280) has actually been run and passed/conditionally passed. This
issue exists in draft form ahead of that so it is ready to arm immediately
once the gate clears — arming itself is a separate owner action.

## Scope
- Add ui/bryggeskole_panel.py (render_bryggeskole_panel()) rendering the
  existing V2-3A fermentation pilot end-to-end: chunks -> one question at a
  time -> feedback -> mastery_label per concept after the set is complete.
- Add a "Prøv igjen" / "Try again" retake action that re-serves the same
  question set against the existing persisted mastery state.
- Wire one call into app.py's existing tab_verktoy block.
- Decide and implement the DEMO_MODE write-guard boundary (see PREP §2 Q5:
  panel-level guard vs. a thin modules/bryggeskole_state.py adapter) —
  either is acceptable; state which was chosen and why.
- Reuse ui.i18n's existing NO/EN session state; do not add a new language
  mechanism.

## Explicit non-goals
- No V2-3C adaptive/spaced-repetition scheduler (due dates, intervals,
  cross-session reminders).
- No new course facts/topics/concepts.
- No course catalog/multi-topic navigation.
- No change to bryggeskole/*.py, bryggeskole/data/*.json, or their tests
  beyond what's needed to keep them green.
- No Web/Core/Sóti/Brew Lab file changes.

## Tests required
- AppTest-based render/flow coverage per PREP §2 Q6, including the
  no-raw-numeric-score-visible assertion and the retake/mastery-label
  monotonicity check.
- DEMO_MODE no-write-to-disk test for whichever guard location is chosen.
- Full Python suite green; `git diff --check` clean.

## Verification
- Closest relevant Bryggeskole/UI tests, then full suite at final
  checkpoint per .claude/rules/testing.md.

## Delivery
Open one bounded PR against master, Closes #<this issue>, stop at
status:review. No automatic merge.
```
