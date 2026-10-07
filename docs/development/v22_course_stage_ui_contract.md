# V2.2 — Bryggeskole course stage UI contract (Foundation → Kompetent hjemmebrygger)

Version: 1.0 (2026-10-05, offline); 1.1 (2026-10-05): Chief review GREEN, defaults approved, explicit-stage-choice refinement (§3, §7.3, §17), S1 status (§15); 1.2 (2026-10-05): S1 merged, S2 status (§15); 1.3 (2026-10-05): S2 Chief GREEN, S3 status (§15)

Status:
- **Contract for review.** Docs only. It implements nothing: no app behaviour, UI, mastery store, lesson JSON, registry or
  module content is changed.
- Built on the offline integration rehearsal `f316cb22beae0ff11dc9228f5dba65fc8a21c58d` (tree `0cebb31…`), where
  **Foundation required content** and **Kompetent hjemmebrygger required content** are COMPLETE LOCALLY/OFFLINE (stage
  allocation contract §E.1, §F.3).
- Recorded offline during the GitHub outage on `offline/course-stage-ui-contract`. Not on GitHub/master.

**Verdict: IMPLEMENTATION READY** (§18) for slices S1–S5 (§15), with the defaults in §17 confirmed at Chief review.

**Status 2026-10-05:**
- Chief review GREEN. All seven §17 defaults are approved, plus the explicit-stage-choice refinement (§7.3).
- The contract is merged into the offline integration rehearsal (`0bd8397`).
- **S1 (stage metadata) is MERGED LOCALLY/OFFLINE** into the integration rehearsal (`f003bc4`).
- **S2 (lesson rendering by stage) is IMPLEMENTED LOCALLY/OFFLINE** (Chief GREEN). It is combined with S3 on
  `offline/course-stage-ui-s3-selector` and **NOT YET MERGED**.
- **S3 (stage selector + cards) is IMPLEMENTED LOCALLY/OFFLINE** on `offline/course-stage-ui-s3-selector`, on top of
  S2. It is pending Chief review and not merged. S2 + S3 merge together; a clean full-suite run on the combined tree
  is required first.
- **S4 and S5 are NOT IMPLEMENTED.** The stage UI is not complete, and nothing is on GitHub/master.

Governed by (never restated or changed here):
- [curriculum map §6.2](v22_g3q_full_bryggeskole_curriculum_map.md#62-canonical-course-architecture-and-terminology-axes):
  - the three axes (§6.2.4);
  - the main App covers Foundation → Kompetent hjemmebrygger (§6.2.8);
  - the canonical 11-module order (§6.2.8).
- [stage allocation contract](v22_course_stage_allocation_contract.md):
  - which stage each chunk and question belongs to (§C, §D);
  - Foundation exit (§E);
  - Kompetent completion rule and status (§F.1–§F.3);
  - "no stage field exists today" (§J.2).
- This contract decides only **how** stages are presented, and the metadata mechanism that carries them.

---

## 0. What the code does today (read before designing)

Read on `f316cb2`:

| Area | Today | Source |
|---|---|---|
| Entry | `render_bryggeskole_panel()`: environment chooser (Hjemmebrygger / Bryggeri) → overview → one module | `ui/bryggeskole_panel.py` |
| Overview | One 11-card grid in canonical order (`_MODUL_REKKEFOLGE`; `_PROSESS_STADIER[miljo]` gives environment-specific card titles at the same indices; `_STADIUM_TIL_MODUL` maps index → module). Responsive via the scoped `.st-key-bs_skoleoversikt_grid` 220 px rule | same |
| Card status | Session-only badges: "Øvd på tidligere" (session baseline from persisted concept attempts), "Påbegynt", "Gjennomført denne økten". Button: Start / Fortsett / Se resultat | `_modul_status`, `_ovd_tidligere_baseline` |
| Guidance | `_anbefalt_modul()`: first module in canonical order not completed this session. Never a lock | same |
| Module flow | Per module, session-only `bs_modul_sesjon[modul_id]`: lesson (one chunk at a time, **all** chunks) → questions (**all** questions) → summary per concept. Widget keys `bs_valg_{modul}_r{runde}_q{idx}` etc. | `_render_leksjon`, `_render_sporsmal`, `_render_oppsummering` |
| Methodology label | Caption "Metode, ikke en faktapåstand" when a chunk or question has `basis: methodology` | same |
| Mastery | `data/bryggeskole_mastery_state.json`, schema v1: `concepts{id: mastery, confidence, attempts, last_tested}` + `answered_questions{question_id: attempts, last_correct, last_tested}`. Isolated by `KVERNHAUG_BRYGGESKOLE_STATE_DIR`; DEMO_MODE keeps it in session_state | `bryggeskole/mastery*.py` |
| Stage | **No stage field anywhere.** `difficulty` is item difficulty, not stage (recipe contract §27.2: the Kompetent Recipe questions are `beginner`) | pilot JSON |
| Learn bridges | Koking C–F (Humle panel), Mesking B/C (Bryggdag), Gjæring A–C (Gjær panel), Learn → Reflect (history). They render chunks by id, without regard to stage | `ui/hop_panel.py`, `ui/process_panel.py`, `ui/yeast_panel.py`, `ui/kbhbrew_history_panel.py` |

Facts from the content that constrain the design:
- Concepts **cross stages**. For example:
  - `measurement.fermentation_complete`: Q-MEAS-002 and Q-FERM-003 are Foundation, Q-FERM-007 is Kompetent;
  - `package.priming`: Q-PACK-002 Foundation, Q-PACK-006 Kompetent;
  - `oxygen.post_pitch`: Q-PACK-004 Foundation, Q-COOLXFER-005 and Q-PACK-009 Kompetent;
  - `sensory.observation_vs_interpretation`: Q-MEAS-006 Foundation, Q-SENS-003/004 Kompetent.

  So **stage progress cannot be derived from concept mastery**, and concepts must stay shared.
- **Question ids are stable and are already persisted per question** (`answered_questions`). Stage progress can therefore
  be derived from data that already exists.
- Some stage moves sit **inside one chunk**:
  - CHUNK-BOILHOP-B mixes boil-over safety (Foundation) with DMS/hot-break depth (Kompetent, §D.2);
  - CHUNK-COOLXFER-D mixes the oxygen timing **rule** (Foundation) with its mechanism (Kompetent, §D.3).

  Chunk-level metadata cannot split them; see §6.3.

## 1. User mental model

> "Bryggeskolen har to trinn. **Trinn 1 – Foundation** er der jeg starter: nok til å brygge trygt og forstå hva som skjer.
> **Trinn 2 – Kompetent hjemmebrygger** er neste trinn: å forstå og styre prosessen så jeg kan gjenta og forbedre.
> De samme 11 temaene går gjennom begge trinnene. Jeg kan se alt, men skolen foreslår hvor jeg bør begynne."

- One course, two stages, **one set of 11 topics**. A topic (module) is a place; a stage is a **depth** within that place.
- The stage is a **lens** over the same school, not a second school. Nothing is locked.
- The legacy environment (Hjemmebrygger / Bryggeri) is how the school is **dressed** (card names); it is never the stage.

## 2. Terminology

| Term | Meaning | Learner-facing? |
|---|---|---|
| **Trinn / stage** | Course progression axis: `foundation`, `kompetent` (later `bryggemester`, outside the main App) | yes |
| **Foundation** | Trinn 1. Canonical name in NO and EN | yes |
| **Kompetent hjemmebrygger** | Trinn 2. Always written in full or as "Kompetent", **never** as bare "Hjemmebrygger" | yes |
| **Miljø / environment** | Legacy presentation axis Hjemmebrygger / Bryggeri (§6.2.4). Unchanged | yes (as today) |
| **Modul / module** | One of the 11 canonical topics | yes |
| **Stage content** | The chunks and questions of one module that belong to one stage | no (internal) |
| **Development completeness** | Whether the *content* for a stage exists (§E.1, §F.3). A project status | **never shown** to learners |
| **Learner progress** | What this learner has worked through (§7) | yes |

Ambiguity rule:
- The UI never shows "Hjemmebrygger" as a stage label.
- Stage labels always carry the "Trinn 1/2" (Stage 1/2) prefix.
- The environment stays labelled with its icon ("🏠 Hjemmebrygger" / "🏭 Bryggeri") as today.

## 3. Chosen top-level interaction

**Model: a stage lens over the single 11-card grid** (a variant of option A, explicit stage selection).

Flow:
- environment chooser (unchanged);
- overview, with a compact stage selector above the grid;
- the grid, 11 cards in canonical order;
- a module opened **in the selected stage**.

Stage selector:
- One horizontal `st.radio` with key `bs_trinn` and two options: "Trinn 1 · Foundation" and "Trinn 2 · Kompetent
  hjemmebrygger".
- Radio is chosen over newer button-group widgets because:
  - AppTest already supports it and the suite already drives radios;
  - it wraps naturally on narrow screens;
  - it is not a giant tab/button.
- A one-line caption under it explains the selected stage (§9).
- Default: Foundation. Exception: Kompetent once the learner's Foundation progress is "gjennomgått" (§7.3), and only
  when the learner has made no explicit stage choice in this session (Chief refinement, §7.3).
- The choice lives in `st.session_state` only (like `bs_miljo`). **No storage change.**

Why not the alternatives:
- **B, two sections on one page:** either duplicates the 11 cards (22 cards) or turns each card into two stacked
  sub-cards. That is too long at 390 px and too noisy at 1280 px.
- **C, progressive unlock:** contradicts the Chief intent (a low threshold; guidance, not locks) and the existing product
  convention ("Kun anbefalt rekkefølge … aldri en lås", issues #458/#473).
- **D, stage chosen inside each module:** the learner would lose the course-level picture of where they are.

## 4. Module-card behaviour

- Always **11 cards, same positions, same environment titles, same open-button keys** (`bs_apne_modul_{id}_btn`).
  Mesking stays 4th, Pakking 8th.
- Each card shows, for the **selected stage** only:
  1. **Stage content line.** One caption, chosen from:
     - "Innhold i dette trinnet": the module has stage content;
     - "Bygger på Foundation": Kompetent view of a module with no Kompetent content;
     - "Hører til Trinn 2": Foundation view of a Kompetent-only module.
  2. **Learner status for that stage** (§7):
     - "Ikke startet" is shown implicitly (no badge);
     - "📚 Øvd på tidligere", "🕒 Påbegynt", "✅ Gjennomgått".
  3. **One button.**
- The module kind decides the line and the button:

| Module kind (from the map, §6) | Foundation view | Kompetent view |
|---|---|---|
| Both stages (Råvarer, Mesking, Koking, Kjøling, Gjæring, Pakking, Måling) | content line + status; Start/Fortsett/Se resultat opens Foundation content | content line + status; opens Kompetent content |
| Foundation only (Rengjøring og sikkerhet, Forberedelse/metode) | as above | "Bygger på Foundation – ingen egen Trinn 2-del"; button **"Repeter"** opens the Foundation content (and switches the lens to Foundation, visibly) |
| Kompetent only (Oppskriftsforståelse, Smak og evaluering) | "Hører til Trinn 2 – Kompetent hjemmebrygger"; button **"Se Trinn 2-innholdet"** switches the lens to Kompetent and opens it. Not disabled, not greyed out | content line + status |

- No card is ever empty, disabled or marked "Kommer senere". `bryggeskole.prosess.kommer_badge` stays unused.
- The existing "✅ Leksjon tilgjengelig" caption is replaced by the stage content line.

## 5. Lesson-flow behaviour

- A module session is keyed by **(module, stage)**. The three steps are unchanged — lesson (one chunk at a time) →
  questions → summary — but each step contains **only that stage's chunks and questions**, in their existing JSON order.
- Breadcrumb: `Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Trinn 2 · Kompetent ▸ Mesking`. Environment and stage are both visible
  and never merged.
- Block counter: "Læringsbolk n av N" counts within the stage (Mesking Kompetent: 5 blocks B–F; Foundation: 1 block A).
- **Stage with questions but no chunks** (Kompetent view of Råvarer and Kjøling/overføring): the lesson step shows one
  short intro caption — "Trinn 2 i denne modulen er dypere spørsmål om det du lærte i Foundation." — plus a "Repeter
  Foundation-leksjonen" link, then "Start spørsmål". No fake chunk is created.
- A Kompetent session offers a quiet "Repeter Foundation-delen" link in the lesson step. It never forces a Foundation
  re-run.
- Summary: unchanged structure (one card per concept, "Denne runden" + "Over tid"), limited to the concepts of that stage's
  questions. "Over tid" stays the **shared** concept mastery, so a concept practised in both stages shows one cumulative
  value.
- Methodology captions, answer-order freezing, no preselection and the disabled "Sjekk svar" until a choice are all
  unchanged.
- Widget/session keys:
  - **Foundation keeps today's keys exactly** (`bs_valg_{modul}_r{runde}_q{idx}`, `bs_bolk_neste_{modul}_btn`, …);
  - **Kompetent adds a stage infix** `_k` (`bs_valg_{modul}_k_r{runde}_q{idx}`, `bs_bolk_neste_{modul}_k_btn`, …);
  - so the two stages of one module can never share a radio value. A future stage gets its own infix from the stage
    table.

## 6. Stage metadata model

### 6.1 Mechanism

One canonical, data-driven stage map, **not** stage fields scattered in eleven lesson files and **not** chunk-letter lists
in UI code:
- `bryggeskole/data/course_stage_map.json`: a stage per chunk id and per question id, grouped by pilot `topic_id`;
- `bryggeskole/course_stage.py`: a pure, stdlib-only reader/validator in the style of the pilots, with
  `STAGES = ("foundation", "kompetent")`, `read_stage_map()`, `stage_of_chunk()`, `stage_of_question()`,
  `stage_content(pilot, stage)` and `module_stage_kinds()`.

Validation (fail-closed, all errors collected):
- `schema_version` must be 1;
- every chunk and question id of every pilot appears **exactly once**;
- no unknown ids;
- stage ∈ the closed `STAGES` set;
- each topic_id matches a pilot.

UI fallback:
- If the map is invalid or missing, the panel logs nothing to disk and **falls back to today's single flow** (every chunk
  and question, no stage selector).
- The school never breaks because of stage metadata.

Why a separate map rather than a `stage` field in the pilot JSON:
- No lesson JSON or eleven validator copies change. Content and contracts stay byte-identical, as do the
  `test_pilot_*` and stage-contract checks that read them.
- One file can be checked against the stage allocation contract in one test.
- A future stage is one more value plus map entries.

Cost: the map must follow content changes. The validator makes drift a failing test, never a silent mis-tag.

### 6.2 The map (S1 data, derived only from stage allocation contract §C/§D)

| Module (topic) | Foundation chunks | Foundation questions | Kompetent chunks | Kompetent questions |
|---|---|---|---|---|
| Råvarer | RAW-A…K | Q-RAW-001, 002, 003, 005, 007, 008, 013, 014 | — | Q-RAW-004, 006, 009, 010, 011, 012 (§D.4) |
| Rengjøring og sikkerhet | SAFE-A…G | Q-SAFE-001…008 | — | — |
| Forberedelse/metode | METHOD-A…E | Q-METHOD-001…005 | — | — |
| Mesking | MASH-A | Q-MASH-001 | MASH-B…F | Q-MASH-002…008 (§D.1, §F.2) |
| Koking/humle | BOILHOP-A, **B (interim, §6.3)**, C, D, E | Q-BOILHOP-001, 003, 004, 005, 006 | BOILHOP-F | Q-BOILHOP-002, 007, 008 (§D.2) |
| Kjøling/overføring | COOLXFER-A, B, C, **D (interim, §6.3)**, E | Q-COOLXFER-001, 002, 003, 006 | — | Q-COOLXFER-004, 005 (§D.3) |
| Gjæring | FERM-A…D | Q-FERM-001…003 | FERM-E…K | Q-FERM-004…011 |
| Pakking | PACK-A…E | Q-PACK-001…005 | PACK-F…I | Q-PACK-006…009 |
| Måling og bryggelogg | MEAS-A…E | Q-MEAS-001…006 | MEAS-F…J | Q-MEAS-007…013 |
| Oppskriftsforståelse | — | — | REC-A…G | Q-REC-001…007 (§C.10) |
| Smak og evaluering | — | — | SENS-A…G | Q-SENS-001…010 (§C.11, §D.5) |

Totals:
- Foundation: 45 questions over 9 modules, and 48 chunks.
- Kompetent: 54 questions over 9 modules, and 36 chunks.
- Together: 99 questions; every one of the 84 chunks is mapped exactly once.

Koking review items (§D.2 "review at implementation"):
- Q-BOILHOP-004 and 005 stay with their Foundation concepts (early/late timing);
- Q-BOILHOP-008 (hot break) goes with hot-break depth to Kompetent (§C.5 lists hot-break depth only under Kompetent).

### 6.3 Mixed chunks — interim rule

**A chunk that contains Foundation-required content is tagged Foundation until its content is split.** Foundation must
never lose required material because of a presentation tag.
- **CHUNK-BOILHOP-B → Foundation (interim).**
  - It carries boil-over safety; Q-BOILHOP-003 (Foundation) depends on it.
  - Its DMS/hot-break depth is tested only by the Kompetent questions Q-002/Q-008.
- **CHUNK-COOLXFER-D → Foundation (interim).** It carries the oxygen timing rule (§C.6 Foundation). Q-COOLXFER-004/005
  stay Kompetent.

The real fix is a separate **content** slice:
- split each chunk into a Foundation part and a Kompetent part, with no new facts;
- then retag;
- it is listed as optional slice C1 (§15), outside this UI work.

Optional Foundation taster CHUNK-SENS-A (§D.5, "may"): **not exposed** in this contract (non-goal, §14). The map keeps
SENS-A Kompetent.

## 7. Mastery and progress behaviour

### 7.1 What stays exactly as it is
- The mastery file, schema v1, `apply_answer()`, `mastery_label()`, concept ids and `answered_questions`.
  **No migration, no new field, no rewrite on read.**
- Concepts stay shared across modules and stages. A Kompetent answer on `package.priming` still moves the same concept a
  Foundation answer moved.

### 7.2 Stage progress, derived only from existing data
For a module *m* and stage *s*, let Q(m, s) be that stage's questions in the map. Using `answered_questions[qid]`:

| Status | Rule |
|---|---|
| ikke startet / not started | no q ∈ Q(m, s) has attempts > 0 |
| påbegynt / in progress | some, but not all, q ∈ Q(m, s) have attempts > 0 |
| gjennomgått / worked through | every q ∈ Q(m, s) has attempts > 0 **and** `last_correct` is true |

- A module with Q(m, s) = ∅ has **no status** for that stage; it shows the §4 line instead.
- "Øvd på tidligere" becomes per (module, stage), read from the same session baseline snapshot, now question-based. This
  keeps PR #340's rule that this session's answers never create the badge.
- "Gjennomført denne økten" stays session-only per (module, stage).

Existing learners: their stored `answered_questions` count immediately under the new stages, because question ids are
unchanged. For example, a stored Q-MASH-001 shows as Mesking Foundation progress.

### 7.3 Stage-level progress (learner-facing)
- "Trinn 1 · Foundation: 4 av 9 moduler gjennomgått".
- "Trinn 2 · Kompetent: 1 av 9 moduler gjennomgått".
- These are counts of modules, **never a percentage, score or grade** (mastery contract: no raw-score UX).
- When every Foundation module is "gjennomgått", the overview shows:
  - "Du har gått gjennom Trinn 1. Klar for Trinn 2 – Kompetent hjemmebrygger?";
  - the default lens becomes Kompetent.
- **Chief refinement (2026-10-05): automatic defaulting never overrides an explicit choice.**
  - With no explicit stage choice in the current session, the lens is Foundation by default.
  - With Foundation worked through and still no explicit choice, Kompetent may become the recommended/default lens.
  - Once the learner has explicitly chosen a stage in the session (the `bs_trinn` selector, or a card button that
    switches the lens), that choice is preserved for the rest of the session. No progress change, recommendation or
    rerun may switch it back.
  - Implemented in S3/S4; S1 has no UI and is unaffected.
- It never says "Foundation complete" or "Kompetent complete" as a qualification.

### 7.4 Development completeness ≠ learner completion
- §E.1/§F.3 milestone states are project facts and appear **only in docs**.
- No UI text, badge or default is driven by development completeness.
- A learner with no answers sees "ikke startet" everywhere, even though all content exists.

## 8. Unlock and guidance behaviour

- **Hard locking: NO.** Every module and both stages are always openable.
- Guidance:
  - the default lens is Foundation;
  - the recommendation line ("💡 Anbefalt neste: …") becomes stage-aware: the first module in canonical order whose
    selected-stage content is not "gjennomgått" and not completed this session;
  - in the Kompetent lens, a Kompetent learner with Foundation gaps also gets one quiet line: "Tips: Trinn 2 bygger på
    Trinn 1 – du har Foundation-moduler du ikke har gått gjennom ennå." It names no lock, and it is dismissable by simply
    ignoring it.
- Foundation completion is **not** a prerequisite for viewing or answering Kompetent content. The pedagogical order is
  communicated, not enforced.

## 9. NO/EN labels (new i18n keys, `modules/i18n.py`)

| Key | NO | EN |
|---|---|---|
| `bryggeskole.trinn.velg` | Trinn | Stage |
| `bryggeskole.trinn.foundation` | Trinn 1 · Foundation | Stage 1 · Foundation |
| `bryggeskole.trinn.kompetent` | Trinn 2 · Kompetent hjemmebrygger | Stage 2 · Competent homebrewer |
| `bryggeskole.trinn.kompetent_kort` | Trinn 2 · Kompetent | Stage 2 · Competent |
| `bryggeskole.trinn.foundation_forklaring` | Start her: nok til å brygge trygt og forstå hva som skjer. | Start here: enough to brew safely and understand what is happening. |
| `bryggeskole.trinn.kompetent_forklaring` | Neste trinn: forstå og styr prosessen, så du kan gjenta og forbedre. | Next stage: understand and steer the process, so you can repeat and improve. |
| `bryggeskole.trinn.innhold` | Innhold i dette trinnet | Content at this stage |
| `bryggeskole.trinn.bygger_pa_foundation` | Bygger på Foundation – ingen egen Trinn 2-del | Builds on Foundation – no separate Stage 2 part |
| `bryggeskole.trinn.horer_til_kompetent` | Hører til Trinn 2 – Kompetent hjemmebrygger | Belongs to Stage 2 – Competent homebrewer |
| `bryggeskole.trinn.se_kompetent` | Se Trinn 2-innholdet | View Stage 2 content |
| `bryggeskole.trinn.repeter` | Repeter | Review |
| `bryggeskole.trinn.repeter_foundation` | Repeter Foundation-delen | Review the Foundation part |
| `bryggeskole.trinn.kun_sporsmal` | Trinn 2 i denne modulen er dypere spørsmål om det du lærte i Foundation. | Stage 2 in this module is deeper questions about what you learned in Foundation. |
| `bryggeskole.trinn.fremdrift` | {trinn}: {n} av {totalt} moduler gjennomgått | {trinn}: {n} of {totalt} modules worked through |
| `bryggeskole.trinn.klar_for_kompetent` | Du har gått gjennom Trinn 1. Klar for Trinn 2 – Kompetent hjemmebrygger? | You have worked through Stage 1. Ready for Stage 2 – Competent homebrewer? |
| `bryggeskole.trinn.tips_foundation` | Tips: Trinn 2 bygger på Trinn 1 – du har Foundation-moduler du ikke har gått gjennom ennå. | Tip: Stage 2 builds on Stage 1 – you have Foundation modules you have not worked through yet. |
| `bryggeskole.status.gjennomgatt` | ✅ Gjennomgått | ✅ Worked through |

Rules:
- "Foundation" is not translated.
- EN uses "Competent homebrewer" for the stage. The environment stays "🏠 Homebrewer", so the two are never the same
  string.
- The i18n coherence tests (`test_i18n_sprakbytte_koherens_apptest`) must cover every new key in both languages.

## 10. Responsive behaviour

Targets: 1280 / 900 / 750 / 390 px, sidebar expanded and collapsed, NO and EN, both environments.
- Stage selector:
  - a horizontal radio that wraps to two lines below about 420 px;
  - labels ≤ 34 characters;
  - `kompetent_kort` is used inside card captions and the breadcrumb.
- Cards: the existing scoped 220 px rule is unchanged. Each new caption is one short line that may wrap; there are no new
  columns.
- Lesson/summary nav keeps `.st-key-bs_nav_actions`. The new "Repeter Foundation-delen" link is a `width="content"`
  button in that row, never `stretch`.
- Acceptance:
  - 0 horizontal overflow on grid and lesson at all widths;
  - no letter-stacked buttons (`nav-buttons-responsive.spec.js` pattern);
  - no duplicated labels.

## 11. Backward compatibility

- **Mastery data:** no migration (§7.1). The real mastery file is untouched by every slice.
- **Content:** lesson JSON, registry and pilot validators are unchanged.
- **Keys:** Foundation keeps every existing widget key; card keys are unchanged; Kompetent keys are new.
- **Tests:** tests that assume "all questions of a module in one flow" (for example TestMeskingKompetent,
  TestPakkingKompetent, the Gjæring/Måling Kompetent classes and the DEMO_MODE subprocess) must move to stage-aware
  helpers in S2. This is an intended, listed test migration (§17), not a regression.
- **Fallback:** an invalid or missing stage map gives exactly today's behaviour (§6.1).
- **Learn bridges** (Humle, Bryggdag, Gjær, history) stay stage-agnostic and unchanged.

## 12. Legacy presentation-mode interaction

- The environment chooser stays first and unchanged (§6.2.4: "stays as it is until a later, separately decided UI
  cleanup").
- Stage and environment are **independent**. All 4 combinations show the same stage content. Only card titles differ by
  environment, exactly as today.
- Switching environment ("🔁 Velg annet miljø") keeps the selected stage and all session progress per (module, stage).
- The stage selector is never placed on the environment screen, and the environment is never inferred from the stage.

## 13. Future Bryggemester extension

- The stage set is data (`STAGES`, the map values, the i18n table).
- Adding Bryggemester later means:
  - a new stage value with its own key infix;
  - map entries;
  - labels.

  The selector, cards, session keys and progress rules iterate over `STAGES` and need no structural change.
- **Not now:** the main App scope stays Foundation → Kompetent (§6.2.8). Bryggemester belongs to the later standalone
  course product, which can reuse `course_stage.py`.
- **Bryggeri / profesjonell** is a different axis (stage contract §B, §H). It is never a value in this selector.

## 14. Explicit non-goals

- No Bryggemester or Bryggeri content, stage values or UI.
- No new course content, chunk split, fact or registry change. C1 is separate (§6.3).
- No change to the legacy environment chooser, its labels or behaviour (a rename is an open decision, §17).
- No optional Foundation taster (CHUNK-SENS-A).
- No persistent stage preference, account, certificate, score or percentage.
- No change to the Learn bridges, Web, #471 (light-struck) or the issue-477 stack.
- No hard locks or gamification (streaks, points, medals).

## 15. Implementation slices

| Slice | Scope | Changes stored mastery? | Changes visible UI? |
|---|---|---|---|
| **S1 — stage metadata only** | `course_stage_map.json` + `course_stage.py` + tests: every id exactly once; closed stage set; the §6.2 table asserted against the stage allocation contract; counts 45/54 questions, 48/36 chunks; mixed-chunk interim rule documented in the map | NO | NO |
| **S2 — lesson rendering by stage** | (module, stage) sessions; stage-filtered lesson/questions/summary; `_k` key infix; questions-only Kompetent intro; "Repeter Foundation-delen"; breadcrumb; fallback to the single flow; migration of stage-assuming tests | NO | yes (inside modules) |
| **S3 — stage navigation + cards** | `bs_trinn` selector; card stage lines and buttons (§4); stage-aware recommendation; new i18n keys | NO | yes (overview) |
| **S4 — progress presentation** | Question-based per-stage status (§7.2); per-(module, stage) "Øvd på tidligere" baseline; module counts per stage; "klar for Trinn 2" line and default-lens rule | NO (read-only use of `answered_questions`) | yes |
| **S5 — responsive / i18n / browser QA** | Chromium + Firefox, NO/EN × both environments × 1280/900/750/390, sidebar open/closed; i18n coherence; overflow 0; final test cleanup | NO | no new behaviour |
| C1 (optional, content; separate decision) | Split CHUNK-BOILHOP-B and CHUNK-COOLXFER-D into Foundation and Kompetent parts (no new facts), then retag in the map | NO | content |

Order and merging:
- S1 first; it can merge alone because it changes no behaviour.
- **S2 and S3 merge into the integration together.** S2 alone would show only Foundation content with no way to reach
  Kompetent.
- Then S4, then S5.
- **None of S1–S5 changes stored mastery data or the mastery schema.**

**Slice status (2026-10-05):**

| Slice | Status |
|---|---|
| S1 | **MERGED LOCALLY/OFFLINE** (Chief GREEN; integration `f003bc4`). Files: `bryggeskole/course_stage.py`, `bryggeskole/data/course_stage_map.json`, `tests/test_course_stage_map.py`. Foundation 48 chunks / 45 questions / 9 modules; Kompetent 36 / 54 / 9; 84 / 99 total. Interim locks as approved. Fail-closed validator |
| S2 | **IMPLEMENTED LOCALLY/OFFLINE** (Chief GREEN; `offline/course-stage-ui-s2-rendering`), combined with S3 on `offline/course-stage-ui-s3-selector`; **NOT YET MERGED**. It must not merge alone. Details below the table |
| S3 | **IMPLEMENTED LOCALLY/OFFLINE** on `offline/course-stage-ui-s3-selector` (on top of S2); **pending Chief review; NOT merged**. Details below the table |
| S4 | NOT IMPLEMENTED |
| S5 | NOT IMPLEMENTED |
| C1 | Not started (optional; separate content decision) |

S2 as implemented (`ui/bryggeskole_panel.py`):
- **Lesson context.**
  - The stage of the lesson context is the internal session key `bs_aktiv_trinn`.
  - S2 gives the learner no way to set it; that is S3. So the normal entry keeps today's single flow, today's keys
    and today's breadcrumb, and does not read the stage map at all.
- **Stage content.**
  - Content comes only from `course_stage.items_for_stage()`.
  - The existing lesson, question and summary renderers run on a stage view of the pilot, in the same order.
- **Sessions and keys.**
  - Sessions are keyed `module`, `module@foundation` and `module@kompetent`.
  - The single flow and Foundation keep today's widget keys. Kompetent uses the `_k` infix
    (`bs_valg_mesking_k_r1_q0`, …).
- **Questions-only stage** (Råvarer and Kjøling Kompetent): a neutral intro, "Repeter Foundation-delen", then the
  questions.
- **Single-stage modules:** an explicit "no separate Trinn 2 part" / "belongs to Trinn 2" state with a stage
  switch. No session is created for it.
- **Breadcrumb:** the environment and stage axes stay separate.
  - NO: "Trinn 1 · Foundation" / "Trinn 2 · Kompetent".
  - EN: "Stage 1 · Foundation" / "Stage 2 · Competent homebrewer".
  - The keys are `bryggeskole.trinn.sti.*`. The breadcrumb uses the full EN stage name, per the Chief S2 brief, rather
    than the §9 short form.
- **Invalid or missing map:** logged once per session, no crash, no guessing, today's single flow.
- **Mastery:** apply_answer, concept ids and the schema are unchanged. Summaries show only the stage's concepts.
- **Since S3:** the normal entry is stage-aware. `bs_aktiv_trinn` is only the lesson context, set by a card action
  and cleared on leaving the module; the single flow remains only as the invalid/missing-map fallback.

S3 as implemented (`ui/bryggeskole_panel.py`, `bryggeskole/course_stage.py`, `modules/i18n.py`):
- **One authoritative stage.**
  - The lens is the selector's own key `bs_trinn` (`foundation`/`kompetent`; never an environment value).
  - It is written back at the start of every run, so it survives runs where the radio is not drawn (open module,
    environment screen).
  - `bs_trinn_valgt_eksplisitt` records an explicit choice: the selector's `on_change`, or a card action that
    switches the lens. A widget value Streamlit only materialised never sets it.
- **Default (§7.3, Chief refinement).**
  - Without an explicit choice the lens is Foundation, or Kompetent once every Foundation module is worked through.
  - After an explicit choice nothing changes the lens for the rest of the session: no progress change, environment
    switch, language switch or rerun.
- **Selector:** one horizontal `st.radio` above the grid, NO "Trinn 1 · Foundation" / "Trinn 2 · Kompetent
  hjemmebrygger", EN "Stage 1 · Foundation" / "Stage 2 · Competent homebrewer", with a help text and a one-line
  caption. The environment chooser stays first and unchanged.
- **Cards:** the same 11 cards, order and `bs_apne_modul_{id}_btn` keys in both lenses. Titles stay tied to the
  environment. Each card has one stage line and one button; nothing is disabled or greyed.
  - Both-stage module: "Innhold i dette trinnet"; today's session badges for that (module, stage); the button opens
    the selected stage.
  - Foundation-only module (Rengjøring og sikkerhet, Forberedelse/metode) in the Kompetent lens: "Bygger på
    Foundation – ingen egen Trinn 2-del" + "Repeter". It opens the Foundation lesson; the lens stays Kompetent.
  - Kompetent-only module (Oppskriftsforståelse, Smak og evaluering) in the Foundation lens: "Hører til Trinn 2" +
    "Se Trinn 2-innholdet". It switches the lens to Kompetent (an explicit choice) and opens the module there.
- **Guidance (no lock, §8):**
  - "Anbefalt neste" names the first module in canonical order with content at the selected stage that is neither
    worked through there nor completed at that stage this session.
  - Kompetent lens with Foundation gaps: one quiet tip line.
  - Foundation worked through: "Du har gått gjennom Trinn 1. Klar for Trinn 2?" (not after an explicit Kompetent
    choice). No completion, certification or mastery wording.
- **Readiness helper:** pure `course_stage.module_stage_status()` / `stage_worked_through()`, read-only over
  `answered_questions` (§7.2), reusable by S4. No S4 counts or per-card status are shown.
- **Fallback:** with an invalid or missing map there is no selector, no stage line and no stage guidance: today's
  overview and single flow.
- **Tests:**
  - The legacy panel suite pins the single-flow engine (the fallback).
  - The stage-split normal path is covered by the S2 and S3 suites, including a card-driven full walk of all 18
    (module, stage) pairs.
  - Chromium smoke: `tests/playwright_streamlit/stage-selector-smoke.spec.js`.

## 16. Acceptance tests

S1 (unit, no UI):
- the map validates;
- each of the 84 chunk ids and 99 question ids is mapped exactly once;
- unknown id, duplicate id, unknown stage and wrong schema_version each fail closed;
- per-module Foundation/Kompetent sets equal §6.2;
- Oppskriftsforståelse and Smak have no Foundation items;
- Rengjøring and Forberedelse/metode have no Kompetent items;
- BOILHOP-B and COOLXFER-D are Foundation, with a note in the map;
- no pilot JSON or registry byte changes.

S2 (AppTest, both environments, NO/EN):
- Mesking:
  - Foundation shows 1 block and 1 question;
  - Kompetent shows 5 blocks (B–F) and 7 questions, with Foundation keys unchanged and `_k` keys in Kompetent;
- Råvarer and Kjøling Kompetent show the questions-only intro, then 6 and 2 questions;
- the methodology caption appears exactly on methodology items;
- no preselection; disabled submit; correct and wrong feedback;
- retry empty;
- summary shows readable labels only, limited to stage concepts;
- shared mastery: a Kompetent answer on `package.priming` changes the same concept as Q-PACK-002;
- an invalid map gives today's single flow;
- DEMO_MODE writes no file.

S3:
- 11 cards in both lenses and environments; Mesking 4th, Pakking 8th;
- the selector defaults to Foundation;
- Kompetent-only cards in the Foundation lens are clickable and switch the lens;
- Foundation-only cards in the Kompetent lens show "Bygger på Foundation" and "Repeter";
- switching environment keeps the stage;
- no "Hjemmebrygger" string is used as a stage label.

S4:
- a seeded `answered_questions` (isolated state dir) gives the expected status per (module, stage);
- the real mastery file is unchanged (size/mtime check);
- no percentage or score strings appear;
- "klar for Trinn 2" appears only when every Foundation module is worked through;
- a fresh learner sees "ikke startet" everywhere.

S5:
- browser smoke 8/8 per engine pair: grid, lens switch, a mixed module in both stages, a questions-only Kompetent
  module, overflow 0/0 at all four widths with the sidebar open and collapsed;
- i18n coherence;
- full suite green.

## 17. Migration risk and open decisions

Risks:

| Risk | Mitigation |
|---|---|
| Large test migration in S2: many panel tests assume one flow per module | Planned; stage-aware helpers (`_apne_modul(at, id, trinn=…)`); Foundation keys unchanged to keep most older tests valid |
| Map drift when content changes | S1 validator: every id exactly once, fail-closed test |
| Learners confused by two "Hjemmebrygger" words | "Trinn n ·" prefix rule; EN "Competent homebrewer"; breadcrumb shows both axes separately |
| Mixed chunks show some Kompetent depth in Foundation | Interim rule (§6.3); optional C1 content split |
| Existing learners see Kompetent modules as "ikke startet" although they practised concepts in other modules | Correct by design: progress is per question, mastery per concept; summary "Over tid" still shows the shared mastery |
| Session keys collide across stages | `_k` infix for Kompetent |

Defaults for Chief confirmation (the contract locks them unless overridden). **Status 2026-10-05: all seven APPROVED by
the Chief** (with the §7.3 explicit-choice refinement; "gjennomgått" = every stage question tried and its latest
recorded answer correct):
1. Stage lens over one grid, with an `st.radio` selector (§3).
2. Separate stage map file rather than per-item `stage` fields (§6.1).
3. Interim tagging of CHUNK-BOILHOP-B and CHUNK-COOLXFER-D as Foundation (§6.3); C1 optional.
4. Q-BOILHOP-008 (hot break) is Kompetent (§6.2).
5. "Gjennomgått" = every stage question attempted and last answer correct (§7.2); module counts allowed, no percentages.
6. EN stage name "Competent homebrewer" (§9).
7. No rename of the legacy environment labels now. A later cleanup may add a "Miljø" prefix, as a separate decision.

## 18. Verdict

**IMPLEMENTATION READY.**
- Every design question has a decision grounded in the current code and contracts.
- The metadata mechanism is bounded (one map, one pure module).
- No slice needs a storage migration.
- The only interpretive calls are listed as Chief-confirmable defaults (§17), and none of them blocks S1.

Next safe step: Chief review, then implement **S1** (metadata only) on its own branch.
Status 2026-10-05: S1 is implemented (§15). Next: Chief review of S1; if GREEN, merge S1 and start S2 together with S3.
Status 2026-10-05 (2): S1 merged; S2 implemented and pending Chief review. Next: if S2 is GREEN, keep it unmerged and
implement S3 on top of it; after S3 is GREEN, merge S2 + S3 together.
Status 2026-10-05 (3): S2 Chief GREEN; S3 implemented on top of it, pending Chief review. Next: if GREEN, merge the
combined S2+S3 state into the integration (after a clean full suite), then implement S4.

Sync note: mirror on #419 / the #343 roadmap when GitHub returns. No issue number is assigned.
