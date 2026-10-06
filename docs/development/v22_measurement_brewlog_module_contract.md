# V2.2 — Måling og bryggelogg (measurement and brew log) Foundation/Kompetent contract

Version: 1.1
Status: **Chief review completed 2026-10-03** (§21). The Foundation slice is approved for implementation-issue creation; the
issue draft is §22. Module code still requires that implementation issue, which is pending because GitHub is unavailable.
Not yet actionable as product work. (v1.0: decision/prep document — reviewable, not yet actionable.)
Status refresh 2026-10-04: the Foundation slice is implemented offline (§21.8); not yet on GitHub/master. Kompetent is not
implemented.
Governed by: [#434](https://github.com/Joludvig/kvernhaug-brygghus/issues/434), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3); product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65); curriculum owner
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (merged), whose map
(`v22_g3q_full_bryggeskole_curriculum_map.md`, §4.5 D38–D44, §4.6 D48, §13, §15) recommends this module as module 8 (the map's 0-based index; position 9 of 11 in the final order); Brew History
methodology from the G3N contract (`v22_g3n_evaluate_inspect_closure_contract.md`) and `CORE_KBHBREW_V1.md`; current-product
inventory `v22_g3q_current_bryggeskole_coverage_inventory.md`.
Authoritative base at creation: `40221da54e48bce86dda446fabd52786c276a1d1`.

This is a docs-only contract. It contains **no product code, no Course Fact Registry mutation, no new verified fact, no module,
no UI, no Core/schema change, no App/Web/Sóti change and no deploy**. Chief must review it before any implementation child issue is opened.

## 0. Source-status guard (read first)

The source reconnaissance behind this contract (delivered to the owner before #434 was implemented) is a **source map, not a verified
fact pack**. It is not stored in the repository, and **this run did not open any external source**. Therefore:

- Sources named in §6 are recorded with what the reconnaissance found. They are **directions for the later fact-pack round**, not citations.
  The fact-pack round must re-open and read every source it cites, record scope and tier, and have Chief review it. AI is never a source.
- Every candidate claim in §5 is **unverified** until that round has done so.
- Only the registry records in §4 are reusable now, and only within their existing `notes`/wording-trap scope.
- Numbers (temperatures, calibration temperatures, correction factors, percentages, day counts), formulas and product names are out of the
  Foundation layer unless a later source review checks them for scope and quality.
- Some reconnaissance sources were read directly and some through a summarising fetch tool. The fact-pack round must spot-check quotes against
  the live source before promoting any record.
- The Kunze pages named in §20 were visually verified during reconnaissance. They were not re-opened in this run.

**Level naming.** The #419 map uses L1/L2. In this contract **Foundation = L1** and **Kompetent = L2**.

## 1. Foundation learner outcome

After the Foundation part of Måling og bryggelogg, a homebrewer with no prior knowledge can, in their own words and without numbers to memorise:

1. say what **OG** and **FG** are: OG is the gravity of the wort before the yeast is added, FG is the gravity when fermentation has finished; gravity is a density reading that helps follow fermentation; OG and FG are **measurements, not targets**;
2. explain how to tell fermentation has plausibly **finished**: repeated gravity readings, taken some time apart, stop changing; an airlock that stops bubbling is not proof; one reading is not enough; a stable reading is not automatically the recipe's predicted FG;
3. **record the temperature of the fermenting beer and where or how it was measured**, and keep a measurement separate from a target
   (Chief 2026-10-03: the v1.0 clause "not assume room temperature equals beer temperature" is removed until a verified fact supports it;
   it is a factual claim, not methodology — §21.4);
4. record **how much beer went into the fermenter**;
5. write down **what they measured or saw** separately from **what they think caused it**;
6. compare the result with the recipe's plan and treat a difference as **evidence to look at**, not a grade and not a diagnosis;
7. keep a short brew log with the seven fields in §9, and not change a recorded reading afterwards.

Non-outcome: any ABV formula, efficiency or yield maths, calibration procedures, correction formulas, or memorised temperatures and day counts.
The learner should finish knowing what happened in the brew, not guessing why.

## 2. Kompetent learner outcome

After the Kompetent part, a homebrewer who already brews can, in their own words:

1. choose between a **hydrometer and a refractometer** for a task and say what each measures;
2. explain why a **refractometer reading taken after alcohol is present** is not the gravity directly, and what that requires (a hydrometer, or a correction that needs the original reading);
3. **check their instruments** (a simple habit, not lab calibration) and say what the check does and does not prove;
4. record, per gravity reading, the **date, the instrument and the sample temperature**;
5. record **pre-boil, post-boil and packaged volumes**, and explain why **hot and cold volumes differ**;
6. keep the **raw reading and any correction separately**, never overwriting the raw number;
7. record a **mash temperature** as a process measurement, distinct from the mash target;
8. write **one planned-vs-actual note, one hypothesis and one deliberate next change** for the next brew.

Non-outcome: laboratory technique, distillation or density-meter methods, statistical treatment, brewhouse yield accounting.

## 3. MUST / SHOULD / LATER concepts

Concept ids follow the registry style (`area.topic`). They are proposals for the fact-pack and module rounds, not existing registry concepts.
Mastery ids equal these concept ids (§11).

| Level | Concept | Proposed id | Source of truth |
|---|---|---|---|
| Foundation MUST | Gravity, OG and FG as measurements | `measurement.gravity` | M1 (§5) |
| Foundation MUST | Fermentation finished when repeated gravity readings stop changing | `measurement.fermentation_complete` | M2 (§5) |
| Foundation MUST | Fermentation temperature: record it and where it was measured; measurement is not a target | `measurement.temperature` | Methodology + FACT-BREW-0001/0002/0003; M5 only later |
| Foundation MUST | Volume into the fermenter | `measurement.volume` | Methodology (Foundation minimum) |
| Foundation MUST | Observation kept separate from interpretation | `sensory.observation_vs_interpretation` (reused; Chief 2026-10-03, §21.3 — v1.0 proposed `log.observation_vs_interpretation`, now not introduced) | G3N / Brew History methodology (no fact) |
| Foundation MUST | Planned vs actual without grading | `log.planned_vs_actual` | Existing Brew History comparison (no fact) |
| Foundation SHOULD | Hydrometer reading depends on the instrument's stated reference temperature | `measurement.hydrometer_temperature` | M4 (§5) |
| Kompetent | Hydrometer vs refractometer; refractometer after alcohol | `measurement.instrument_choice` | M3 (later) |
| Kompetent | Instrument checks | `measurement.instrument_check` | M7 (later) |
| Kompetent | Pre-boil, post-boil, packaged volumes; hot vs cold volume | `measurement.volume_stages` | M6 (later) |
| Kompetent | Raw reading vs correction; not fake precision | `measurement.uncertainty` | Methodology + Kunze p. 869 |
| Kompetent | Mash temperature as a process measurement | `measurement.mash_temperature` | Methodology + FACT-MASH-0004 context |
| Kompetent | One hypothesis and one deliberate next change | `log.hypothesis_next_change` | G3N / Brew History methodology (no fact) |
| LATER | see below | — | — |

**SHOULD note.** `measurement.hydrometer_temperature` is Foundation SHOULD, not MUST: the Foundation minimum can be met by "note the sample
temperature and what temperature your instrument is made for". The reference temperature is instrument-specific, so no universal number is ever taught.

**LATER (explicitly not in this module):**

- ABV formulas and derived-value teaching (Brew History recomputes derived values; they are not entries).
- Efficiency, yield and brewhouse accounting (#419 D66); pH measurement (D41).
- Hydrometer temperature-correction formulas and refractometer alcohol-correction formulas.
- Laboratory methods: distillation, density meters, pycnometers, forced-fermentation tests.
- Gravity-over-time logging schedules, telemetry, automated or electronic logging.
- Fermenter temperature controllers and setpoint tuning.
- Any change to the Brew History schema (see §15).

**Deviations from the #419 map, recorded so they are not silent:**

- #419 D48 (fermentation completion by stable gravity) is MUST at L2. #434 places one Foundation sentence for it (`measurement.fermentation_complete`), because it gates the packaging decision; the full depth stays Kompetent.
- #419 D38 (temperature measurement) is MUST L1 but partly about "instrument check". This contract keeps the Foundation part to "record it and where it was measured", and moves instrument checks to Kompetent.
- #419 D39 (gravity measurement) is MUST L2. Its OG/FG definitions move to Foundation; hydrometer/refractometer depth stays Kompetent.

## 4. Existing facts and methodology reused now

**Registry records** (`status: verified` in `bryggeskole/data/course_fact_registry.json` at the base SHA). Reuse only within each record's `notes`
scope. Do not duplicate them into new records.

| Record | What it carries here | Boundary |
|---|---|---|
| **FACT-YEAST-0002** (`yeast.attenuation`) | Attenuation is the proportion of wort sugars consumed; higher attenuation generally leaves a drier beer; it depends on the yeast and on conditions. Supports "the drop from OG to FG shows how much sugar was used". | Its notes forbid numeric attenuation bands, strain rankings and a universal ABV formula. |
| **FACT-BREW-0001/0002/0003** (`fermentation.temperature`) | Fermentation temperature influences activity and flavour, strain-dependently; targets come from strain guidance, not one universal number. Supports "a target is what you aim for; a reading is what you measured". | They say nothing about how or where to measure temperature. Do not use them for measurement claims. |
| **FACT-METHOD-0004** (`method.planning_variables`) | Water volumes, dead space and losses differ by method. Context for why volumes differ from plan. | Planning context, not a measurement fact. |

**Methodology already shipped (no Course Fact, per G3N §1.7):**

- the four Brew History layers: `snapshot` (frozen plan), `actuals`, `sensing`, `learning`;
- observation vs interpretation kept as separate fields with separate save actions;
- the immutable snapshot boundary and read-only plan-vs-actual comparison (`og`, `fg`, `volume`, `abv`);
- derived values (actual ABV, deviation, attenuation, efficiency) recomputed at read time and never stored as wire fields;
- `learning.hypothesis` as "not a measurement, not a sensory observation, not asserted causal truth", never auto-filled or AI-generated;
- "still uncertain" as a valid state (no field is required).

**No registry record exists** for OG/FG, gravity measurement, hydrometer, refractometer, temperature or volume measurement, logging, or planned vs
actual. The new records in §5 add only what is not covered above.

**Unsourced wording leads (read-only, never a source):** `web/hjelp/index.html` glosses for OG-måling, hydrometer temperature correction,
FG-måling and refractometer/Brix agree in direction with the reconnaissance sources but are not linked to registry ids and contain numbers
(week ranges, temperature ranges). They may be read as candidate wording leads and must not be copied into course content as verified truth.

## 5. Smallest later fact-pack plan

Each record is a future registry-mutating round (not this issue). Record shapes follow the registry (`id`, `claim`, `classification`, `status`,
`verified_at`, `sources[]`, `concepts[]`, `modules[]`, `notes`). This contract defines direction only; ids `FACT-…-NNNN` are assigned by the
fact-pack round.

### First slice (Foundation)

**M1 — OG/FG definitions; gravity is a density measurement.** Concept `measurement.gravity`. Classification `documented_fact`.
*Direction of claim:* Gravity is a density reading that shows how much sugar is dissolved. OG is the gravity of the wort before fermentation; FG
is the gravity at the end of fermentation.
*Source direction:* Tier A — refractometer manufacturer technical note defining OG and FG (commercial-interest caveat); Tier B — AHA hydrometer
guidance; Kunze p. 404 §4.3.3 for the "apparent" nature of a hydrometer reading of finished beer (Kompetent depth only).
*Traps:* no ABV formula; OG/FG are readings, not targets; no numbers.

**M2 — Fermentation completion from repeated stable gravity readings.** Concept `measurement.fermentation_complete`. Classification
`documented_fact` for the signal; any "next day" interval appears only as an example practice in `notes`.
*Direction of claim:* Repeated gravity readings taken some time apart that stop changing are the key signal that fermentation has finished.
*Source direction:* Tier A — the same manufacturer note ("readings can signal the end of fermentation when they stop moving"); Tier B — AHA
guidance (a second reading a day later); Kunze p. 405 §4.3.3 (attenuation limit reached when the extract stops decreasing).
*Traps:* one reading is not enough; airlock activity alone is not proof; stable is not automatically the predicted FG (a stalled fermentation
is also stable); no universal number of hours or days; stable readings do not by themselves mean the beer is ready to package.
*Gap:* no yeast-producer or other Tier A source states the rule (§6, G2).

**M4 — A hydrometer reading depends on the instrument's stated calibration/reference temperature.** Concept `measurement.hydrometer_temperature`.
Classification `documented_fact`.
*Direction of claim:* A hydrometer is accurate at the temperature it is made for, which is stated on the instrument; a sample at another
temperature reads differently.
*Source direction:* Tier A — the manufacturer note (scale valid at one temperature; note and compensate for variation); Tier B — AHA and BYO
guidance.
*Traps:* no universal calibration temperature; no correction formula; the reference temperature is whatever is printed on the learner's instrument.

### Later records

- **M3 — Refractometer after alcohol (Kompetent).** `measurement.instrument_choice`. Once alcohol is present a refractometer reading is not the
  gravity directly; use a hydrometer, or a correction that needs the original reading. Direction: manufacturer note (Tier A, commercial-interest
  caveat) and BYO (Tier B). Independent neutral source desired (G1). No correction formula in Foundation.
- **M5 — Fermenting beer vs room temperature (Foundation only after stronger source support).** `measurement.temperature`. Active fermentation
  warms the beer, so where you measure matters. Only Tier B/C support so far (G3). Until a stronger source exists, the Foundation temperature
  chunk teaches only "record it and where you measured it; measurement is not a target", drawing on FACT-BREW-0001/0002/0003 and methodology.
- **M6 — Hot vs cold wort volume (Kompetent).** `measurement.volume_stages`. Hot wort takes up more volume than cold wort. Direction: Kunze
  p. 329 §3.5.1.3 and BYO (Tier B). No shrinkage factor.
- **M7 — Thermometer accuracy check (Kompetent, only with brewing-relevant source).** `measurement.instrument_check`. The only source found is
  food-thermometer guidance (G4).

**No new Course Fact** is proposed for: observation vs interpretation, planned vs actual, hypothesis and next change, the minimum log, or the
"do not change a recorded reading" habit. They are product methodology (§12, §13).

## 6. Source requirements and source gaps

**Requirements for the fact-pack round:**

- Every cited source is re-opened and read. Record URL/DOI, tier, what it supports and does not support, and quote scope.
- Tier A: manufacturer technical documentation, recognised standards (ASBC/EBC), university/extension material, yeast/malt producer technical
  material where directly relevant. Tier B: Kunze, Palmer and established brewing texts, Brewers Association/AHA educational material.
  Retailers, forums, calculators and videos are never authority.
- Kunze is Tier B structural support. Any exact claim needs the printed page visually verified, with section and printed page recorded. OCR alone
  is not enough. Industrial-scale figures are not transferred to homebrew scale.
- A manufacturer with a commercial interest may be Tier A but must be flagged, and a second independent source is preferred.
- Source dates: record the publication or revision date. If the page does not show one, say so.

**Source map from reconnaissance (directions only; §0 applies):**

| Topic | Source | Tier | Notes |
|---|---|---|---|
| OG/FG definitions; end-of-fermentation signal; hydrometer temperature; refractometer and alcohol | MISCO, "How to Use a Refractometer to Brew Beer" (Rev 140407-1, 2014) | A (manufacturer; commercial interest) | Read directly. Contains many numbers and product claims; take none |
| Hydrometer, repeated readings | AHA, "How to Take an Accurate Hydrometer Reading" | B | Read via summarising fetch; date not shown |
| Refractometer after alcohol; distilled-water checking | BYO (Dave Green), "Hydrometers and Refractometers" | B | Read via summarising fetch; date not shown |
| Gravity at start and end of fermentation | Wyeast, "Yeast Fermentation" (29 Jul 2025) | A | Does not state the stable-readings rule |
| Fermenter temperature vs room | BYO, "Wort Temperature During Fermentation" (Mr. Wizard) | B/C | Undated; contains example temperatures to exclude |
| Volume, hot vs cold | BYO (Dave Green), "Hit Your Post-Boil Volume"; Kunze p. 329 | B | Numbers (shrinkage) excluded |
| Record keeping | BYO (Jason Simmons), "Recording Your Brew Day"; Kunze p. 797 | B | The BYO article is an exhaustive-log example, not a model |
| Thermometer checking | WSU Extension "Calibrating a Thermometer" (from USDA) | A (food scope) | No brewing content |
| Attenuation, hydrometer apparent reading, stable extract, accuracy principle | Kunze pp. 404, 405, 869 | B | Visually verified in reconnaissance |

**Explicit source gaps** (must stay visible; not to be filled from general knowledge or AI):

- **G1** No independent Tier A source (ASBC/EBC or a neutral instrument maker) opened for gravity or refractometer behaviour. The main Tier A source is a refractometer manufacturer.
- **G2** No yeast-producer or other Tier A source found for the "repeated stable readings mean finished" rule. The Wyeast and White Labs pages opened do not state it. The rule rests on Tier B AHA plus the manufacturer note plus Kunze.
- **G3** Fermenter vs room temperature has only Tier B/C support.
- **G4** Thermometer checking has only food-scope guidance; the FSIS page returned HTTP 403.
- **G5** No hydrometer temperature-correction formula is sourced. It must stay out of Foundation.
- **G6** There is no authoritative need for timestamp precision beyond "record when it was measured".
- **G7** The refractometer alcohol-correction formula is not sourced and stays out of Foundation.
- **G8** Some Kunze measurement pages remain unverified (p. 778 density meters, p. 406, and pp. 323–328 and 330 of §3.5.1).
- **G9** Some AHA/BYO publication dates are incomplete in the fetched text, so their currency is unknown.

## 7. Instrument traps

Foundation teaches the traps marked (F); the others are Kompetent.

- **Hydrometer:** valid at one reference temperature, printed on the instrument (F). Needs enough sample to float freely. Do not return the sample to the fermenter (F, hygiene). Cannot be reset; a consistent offset can only be noted or corrected afterwards. Fragile.
- **Refractometer:** reliable for unfermented wort. Once alcohol is present the reading is not the gravity directly (F: "check with a hydrometer"; the correction is Kompetent). The scale may be Brix rather than gravity. It needs temperature compensation. Disagreement with a hydrometer is usually a correction or method problem, not proof that one is broken.
- **Thermometer:** liquid, vessel wall and room air read differently, and active fermentation warms the beer (F: record where you measured;
  Chief 2026-10-03: Foundation teaches only "record where/how you measured" — the "warms the beer" and room-vs-beer statements stay out
  until M5 is verified, §21.4). Accuracy can be checked (Kompetent; source is food-scope).
- **Volume markings:** an unmarked or homemade scale is approximate; hot and cold volumes differ (Kompetent); Foundation records the fermenter volume as measured.
- **Precision:** teach "as accurate as necessary" (Kunze p. 869). Record what the instrument shows. No decimals of precision, no lab accuracy, no fake precision.

## 8. NO/EN terminology strategy

- Match the words already in the product. Do not introduce a second term for an existing concept. Norwegian help text already uses *tetthet*,
  *hydrometer*, *refraktometer*, *OG-måling*, *FG-måling*, *Brix*. Brew History already uses *planlagt*, *faktisk*, *målte verdier*, *sensorikk*,
  *læring*. English uses *gravity*, *OG/FG*, *hydrometer*, *refractometer*.
- Keep **measurement**, **target** and **interpretation** as distinct words in both languages. Do not use one word for two of them.
- Do not use "correct/actual/true gravity" for a hydrometer reading of finished beer without a qualifier. If depth is added later, call it the
  apparent reading (Kunze p. 404) and gloss it once.
- Every chunk, question, option and explanation exists in Norwegian and English with NO/EN key symmetry, as in the current modules. The registry
  claim is the single source for both languages; wording traps apply in both. No loose translation of measurement claims.
- No public Web page or generated `web/en/**` change in this line of work. If a later slice touches Web help, use
  `python3 scripts/generate_web_i18n_pages.py` only and never hand-edit `web/en/**`.
- Owner/Chief confirmation is needed only if a Norwegian term is not already in the product. The fact-pack round records any such term.

## 9. Minimum viable brew-log fields

**Foundation (seven items):**

1. brew date
2. OG (measured before pitching)
3. fermentation temperature, plus where or how it was measured
4. FG (measured after repeated stable readings)
5. volume into the fermenter
6. package date
7. observation notes (what was measured or seen), kept separate from interpretation

**Kompetent additions (each optional):** pre-boil volume; post-boil volume; packaged volume; reading date, instrument and sample temperature for each
gravity reading; mash temperature reading; one planned-vs-actual note; one hypothesis; one next change.

**Explicitly rejected (as mandatory content):** weather, propane or energy use, mandatory pH, mandatory efficiency, hour-by-hour logging, and
exhaustive telemetry. The reconnaissance found an example of an exhaustive enthusiast log; it is not a model for this module.

**Log habits (methodology, no fact):** record the raw reading; never silently overwrite it; if a correction is applied, record it separately;
note how and when each measurement was taken.

## 10. Module and chunk structure

**One module, "Måling og bryggelogg"**, module 8 in the #419 §15 sequence (0-based index; position 9 of 11 in the final order), placed **after** the process spine because it is most useful once the
learner has something to measure. It is not a hard gate; existing modules stay reachable. Indicative id `measurement.fundamentals`; the
implementation issue fixes the final id and file names.

- **Foundation part** (about 5 chunks, 5–6 questions): what to measure and why (know what happened); gravity, OG and FG; fermentation finished by
  repeated readings; temperature and where you measured it; the minimum log with observation kept apart from interpretation and plan-vs-actual as
  evidence.
- **Kompetent part** (about 4 chunks, 4–5 questions): instrument choice and the alcohol problem; checking your instruments; volumes, losses, hot vs
  cold; planned vs actual with one hypothesis and one next change.
- Pattern matches the existing modules (`bryggeskole/pilot_*.py` and `bryggeskole/data/pilot_*.json`): chunks with `source_claims`, `concept_check`
  and `scenario` questions, NO/EN text.
- A chunk enters the module only after its fact record is verified. Methodology chunks (log, observation vs interpretation, planned vs actual)
  enter without a fact record, because they teach product behaviour, and must say so rather than claim a brewing source.
- Visuals worth keeping (qualitative only): the gravity-over-time curve (OG falling to a stable FG) already recommended in #419, and a
  hydrometer/refractometer reading exercise for the Kompetent part. No calculator, no simulator.
- Learn→Reflect bridge: a later slice, consistent with the existing static bridge in Brew History (not registry-backed by design).
- Not recommended: separate modules for each measurement type, or a laboratory track.

## 11. Mastery concept IDs

In this codebase the mastery concept ids are the registry concept ids carried by question `concepts[]`. One hidden mastery concept per concept in §3;
no new mastery mechanics.

Foundation: `measurement.gravity`, `measurement.fermentation_complete`, `measurement.temperature`, `measurement.volume`,
`sensory.observation_vs_interpretation` (reused from the Smak og evaluering contract; Chief 2026-10-03, §21.3), `log.planned_vs_actual`,
and (SHOULD) `measurement.hydrometer_temperature`.

Kompetent: `measurement.instrument_choice`, `measurement.instrument_check`, `measurement.volume_stages`, `measurement.uncertainty`,
`measurement.mash_temperature`, `log.hypothesis_next_change`.

Question types: `concept_check` for definitions; `scenario` for decisions. Wrong-answer explanations reuse registry wording where a record exists.
No question may rest on an unverified claim, and no new scoring, badges or gating.

## 12. Planned-vs-actual governance

- Reuse the existing Brew History comparison. Do not build a second comparison engine or course truth.
- The plan is the frozen `snapshot` and never changes. The actual is read from `actuals`. The difference is computed at read time.
- A difference is **evidence to investigate**. It is not a grade, a score, a pass/fail or a diagnosis. The module never says a brew was "good" or
  "bad" on numbers alone, and never assigns a cause.
- Missing actuals are not errors; a brew is valid without them. The comparison shows "missing", not a fabricated value.
- Kompetent adds one written planned-vs-actual note. It is the brewer's own words, stored in the learning layer, not generated.
- No automatic blame, no "your efficiency is low" messages, no recommended fix.

## 13. Observation-vs-interpretation governance

- Reuse G3N/Brew History methodology. No new Course Fact.
- Keep separate: what was **measured** (`actuals`), what was **seen or tasted** (`sensing`), what the brewer **thinks caused it**
  (`learning.whatWorked`/`whatChanged`), a **hypothesis** (`learning.hypothesis`), and a **decision** for next time (`learning.nextTime`).
- A hypothesis is not asserted causal truth and is never auto-filled or AI-generated.
- "We still do not know" is a valid outcome and must be teachable. The module invites an explicit "uncertain", never forces a single answer.
- Teaching text must not present interpretation as measurement, must not present one measurement as proof of a cause, and must keep the raw reading
  intact when a correction is discussed.

## 14. Brew History mapping

Current actuals fields: `og`, `fg`, `volumeL`, `notes`, plus `brewedAt` and `status`. Derived values are recomputed and not stored. This contract
does not change any of this.

| Log item | Existing home | Note |
|---|---|---|
| brew date | `brewedAt` | |
| OG | `actuals.og` | one value |
| FG | `actuals.fg` | one value |
| volume into the fermenter | none today (notes) | **Not `actuals.volumeL`:** the App's Bryggedag panel writes post-boil volume there (§15 G-1, §21.4) |
| package date | no field | notes only today |
| fermentation temperature and where measured | no field | notes only today |
| observation notes (measured/seen) | `actuals.notes` | measurement/process-adjacent free text |
| sensory notes | `sensing.notes` / `sensing.judgment` | separate from measurement |
| interpretation | `learning.whatWorked` / `whatChanged` | |
| hypothesis | `learning.hypothesis` | |
| next change | `learning.nextTime` | |
| pre-boil / post-boil / packaged volume | no field | Kompetent; notes only today |
| reading date, instrument, sample temperature | no field | Kompetent; notes only today |
| mash temperature | no field | Kompetent; notes only today |
| plan vs actual | read-only comparison (`og`, `fg`, `volume`, `abv`) | |

Until a Core decision says otherwise, anything without a field is taught as a written note and is not stored structurally.

## 15. Explicit owner/Core gates

These are **product or Core decisions**. This contract records them and neither makes nor implements any of them. The schema is not changed.

- **G-1 `volumeL` stage.** The schema describes `actuals.volumeL` only as liters and does not say which brewing-stage volume it is. The
  Foundation minimum is "volume into the fermenter". Recommended interpretation, presented for later owner/Core review only:
  **`actuals.volumeL` = volume into the fermenter.** Not decided here. Until decided, teaching text says "volume into the fermenter" and does not
  claim that the App stores that specific stage.
  *Correction found at Chief review (2026-10-03):* the schema is silent, but the shipped App is not. `ui/brewday_panel.py` labels its input
  "Post-boil volum (L)" (`bd_post_boil_vol`) and writes it to `actuals.volumeL`, following the #155 preflight
  (`app_a1_active_brew_measurement_preflight.md` §6). The v1.0 recommendation above therefore conflicts with current App behaviour. Chief decision
  (§21.4): the Foundation lesson must **not** map "volume into the fermenter" onto `actuals.volumeL`. G-1 stays an open owner/Core decision; no
  schema or App change follows from this contract.
- **G-2 Fermentation temperature.** There is no field. Decide whether it becomes a field, stays in notes, or is deferred.
- **G-3 Reading date.** There is no per-reading date field.
- **G-4 Instrument/method.** There is no instrument or method field.
- **G-5 Multiple readings.** There is one `og` and one `fg` per brew. A repeat or conflicting reading cannot both be stored structurally. The G3N
  audit found a real brew with two conflicting FG values. Decide whether to store a series, keep one value plus notes, or leave it.
- **G-6 Package date.** No field; decide with G-2 to G-4.
- **G-7 Kompetent volumes.** Pre-boil and packaged volumes have no fields; post-boil volume is what the App's Bryggedag panel currently writes to
  `actuals.volumeL` (see G-1). Decide whether the others stay notes.

None of G-1 to G-7 blocks the Foundation fact pack (M1, M2, M4) or the methodology chunks. G-1 must be settled before any UI states which volume the
App stores. Any schema change needs its own Core issue and version handling.

## 16. Representative acceptance scenario

A new homebrewer finishes their first batch and wants to know whether it is ready to package.

1. Before adding the yeast they measure the wort and write down **OG**, noting that OG is a measurement, not the recipe's target.
2. They record the **volume that went into the fermenter**, and the **fermentation temperature with where they measured it** (in the liquid, on the
   vessel or in the room air). (Chief 2026-10-03: the v1.0 step "say why room temperature is not assumed to equal beer temperature" is removed
   until a verified fact supports it, §21.4.)
3. When the airlock quiets, they say that is **not proof** of anything. They take a gravity reading, then another some time later, and see whether
   the two are the same. One reading does not tell them; a stable pair is the key signal.
4. The readings stop changing, but the number is higher than the recipe's predicted FG. They say **stable does not mean the predicted FG**, and
   record it as it is rather than adjusting it.
5. They open the plan-vs-actual view, see the difference from the plan, and describe it as **evidence to look at**, not a grade.
6. In the notes they write what they measured and saw, separately from a guess about why. They mark the guess as a guess, and they may write
   "still uncertain".
7. Kompetent extension: they repeat the exercise with a refractometer, record that alcohol is now present, note the date, instrument and sample
   temperature, keep the raw reading, write one hypothesis and choose one deliberate change for the next brew.

Pass condition: an independent reader answers all steps correctly on a first read-through; no unverified claim is shown; no ABV formula,
universal number of days or calibration temperature appears; NO/EN show identical content. Owner-PC QA of the implementation remains a separate gate.

## 17. Smallest implementation slices

| # | Slice | Type | Depends on |
|---|---|---|---|
| 1 | **M1, M2, M4 fact pack**: open and read the sources, add verified records, tests | Registry + tests | this contract |
| 2 | Foundation module skeleton: methodology chunks plus the chunks whose records are verified; questions, NO/EN, mastery, module registration | Module + tests | 1 (each chunk ships when its record is done) |
| 3 | Owner/Core decision on G-1 (`volumeL` stage), then G-2 to G-7 | Decision | — (recommended before any UI states what the App stores) |
| 4 | Gravity-over-time visual | UI | 2 |
| 5 | Kompetent facts M3, M6 (and M7 or M5 only if source gaps close) | Registry + tests | source gaps G1, G3, G4 |
| 6 | Kompetent chunks and exercise | Module + tests | 5 |
| 7 | Learn→Reflect bridge into Brew History | UI | 2 |
| 8 | Owner-PC QA and Chief acceptance against §16 | QA | 2, 4–7 |

Slice 1 is independent of the module. The WIP rule of #343 still applies. This contract defines but does not implement any slice.

## 18. Hard non-goals

- No Course Fact Registry change and no new verified fact in this issue.
- No module, chunk, question, UI or bridge implementation.
- No Core or schema change, no `.kbhbrew` field, no schema-version change; no App, Web or Sóti change; no generated `web/en/**` change.
- No decision on any gate in §15, including `volumeL`.
- No ABV, attenuation, efficiency or yield formulas; no hydrometer or refractometer correction formulas.
- No universal calibration temperature, fermentation temperature, or number of hours or days.
- No laboratory training and no calibration procedures beyond a simple check.
- No mandatory weather, propane, pH, efficiency, hour-by-hour or telemetry logging.
- No automatic diagnosis, grading, scoring or blame; no AI-generated interpretation or hypothesis.
- No unsupported claims from general knowledge or AI; source gaps stay explicit.
- No deploy, no merge authority.

## 19. Wording traps (binding for the fact-pack round, questions and UI copy, in both languages)

- "The airlock stopped, so fermentation is finished."
- "One reading means it is finished."
- "A stable gravity is the predicted FG." (A stalled fermentation is also stable.)
- "A refractometer reads FG directly."
- "A hydrometer is always right."
- Any universal calibration temperature, correction factor or fermentation temperature.
- Any ABV formula.
- Efficiency or yield presented as Foundation content.
- Silently correcting a raw measurement, or recording only the corrected value.
- Interpretation presented as measurement, or one measurement presented as proof of a cause.
- Automatic diagnosis, grading, "good/bad brew" on numbers alone.
- OG or FG described as targets.
- Exhaustive logging treated as mandatory.
- A fixed number of hours or days for completion; "stable" without saying readings are taken some time apart with the same method.

## 20. Kunze anchors (Tier B, structural support only)

Visually verified during reconnaissance (rendered page images viewed; printed page and section recorded). Not re-opened in this run.

- **p. 404, §4.3.3 (attenuation):** a hydrometer reading of finished beer is "apparent" because alcohol changes the density; in practice apparent
  attenuation is used. Use qualitatively for Kompetent depth only.
- **p. 405, §4.3.3:** the attenuation limit is reached when the extract content no longer decreases; the decline is not steady in time. Use for
  M2 qualitatively; no day counts or percentages.
- **p. 329, §3.5.1.3:** hot wort volume is converted to cold volume at the temperature at which it is measured. Use qualitatively for M6; no factors.
- **p. 797, §8.3:** a hobby-brewer text advising notes on what was used and how much so a success can be repeated. Use for the log rationale.
- **p. 869, §11.1.1:** measure "as accurate as necessary" and "as often as necessary". Use for the accuracy framing.
- p. 776 §7.5.1, p. 769 §7.4.3 and p. 357 §3.10 were viewed and are industrial instrumentation or plant control. Do not use for homebrew claims.

Not verified: p. 778, p. 406, and pp. 323–328 and 330. Industrial figures and procedures are LATER. Printed-page offsets differ from PDF page
numbers by chapter, so a fact-pack round must view the rendered page and read the printed number, and must not rely on OCR text for any exact claim.

## 21. Chief review closure (2026-10-03)

Chief reviewed this contract on 2026-10-03. The decisions were relayed to Local Claude and recorded offline because GitHub was unavailable. They
must be mirrored on #434 when access returns. Where an earlier section disagrees with this section, this section wins. The earlier text is kept and
annotated so the change is visible.

### 21.1 Implementation slice

The first implementation slice is **Foundation only**. It does **not** decide whether Kompetent content may later appear in the main App. (Since decided, 2026-10-04: the main App Bryggeskole covers Foundation → Kompetent hjemmebrygger — curriculum map §6.2.3/§6.2.8 — so the later Kompetent Måling slice is in main-App scope. The first slice stays Foundation only.) Kompetent
is a later slice (§21.6).

### 21.2 Foundation shape (locked)

- Module/topic id: **`measurement.fundamentals`** (the value later used in registry `modules[]`, like `package.fundamentals`).
- **5 chunks:** `CHUNK-MEAS-A`, `CHUNK-MEAS-B`, `CHUNK-MEAS-C`, `CHUNK-MEAS-D`, `CHUNK-MEAS-E`.
- **6 questions:** `Q-MEAS-001` … `Q-MEAS-006`, all difficulty `beginner`.

| Chunk | Basis | Content | Allowed source claims |
|---|---|---|---|
| A | methodology | Why measure and log: know what happened before guessing why | none |
| B | fact | Gravity, OG and FG. OG and FG are measurements, not targets | FACT-MEAS-0001; FACT-YEAST-0002 only if the text genuinely needs it as supporting context |
| C | fact | Fermentation completion: repeated gravity readings taken some time apart stop changing; the airlock is not proof | FACT-MEAS-0002 |
| D | fact + methodology | Temperature: record the reading **and** where/how it was measured; for a hydrometer sample, note the sample temperature | FACT-MEAS-0003 where applicable |
| E | methodology | Minimum log; observation vs interpretation; plan vs actual is evidence, not a grade or diagnosis; never overwrite a raw recorded reading, record corrections separately | none |

Chunk C rules:
- No fixed number of hours or days.
- Predicted FG is a **plan** value, not a measurement.
- No factual claim beyond FACT-MEAS-0002 about what a particular stable reading proves or disproves.

### 21.3 Mastery concept

Reuse **`sensory.observation_vs_interpretation`**, defined in `v22_sensory_evaluation_module_contract.md` §4/§26, for observation vs
interpretation. `log.observation_vs_interpretation` is **not** introduced for the same underlying skill. The cross-module reuse follows the existing
precedent of `cool.sanitation_boundary` being taught in both Kjøling/overføring and Pakking. Other measurement/log concepts stay module-specific
where genuinely distinct.

### 21.4 App/course boundary, volume and temperature

Product scope:
- No Brew History schema change. No Core change.
- No calculator duplication: the ABV calculation, `modules/calculations.py` and recipe efficiency stay where they are and are not re-taught.

Volume:
- The lesson must **not** claim that App `actuals.volumeL` is "volume into the fermenter". The App stores post-boil volume there (§15 G-1).
- Foundation may teach recording the volume into the fermenter as a useful measurement. Integration stays generic: "record the measurement in
  your brew log/notes".

Temperature:
- "Room temperature is not beer temperature" is **removed** from Foundation until a verified fact supports it (M5, source gap G3). It is a factual
  claim and is not reclassified as methodology.
- Foundation teaches only "record the reading and where/how you measured it".

### 21.5 Grid placement

Måling og bryggelogg is **inserted after Pakking and before Smak og evaluering**: … → 8 Pakking → **9 Måling og bryggelogg** → 10 Smak og
evaluering (the current 9-card grid becomes 10 cards). Oppskriftsforståelse will later sit between Måling and Smak, following the 11-module order in
the #419 map §15: 8 Pakking → 9 Måling og bryggelogg → 10 Oppskriftsforståelse → 11 Smak og evaluering. (Corrected 2026-10-04: v1.1 called Måling
the "10th visible card"; it is position 9.) The grid is not changed by this
contract.

### 21.6 Kompetent (later slice, not implemented now)

Kept for later, unchanged: instrument choice (FACT-MEAS-0004), instrument checks, volume stages (FACT-MEAS-0005), correction vs raw reading, mash
temperature, and hypothesis + next change. The **fact gap for instrument checks remains open** (M7 / G4: only food-scope sources; no registry record).

### 21.7 Fact spot-check metadata

Chief live-checked public source material on 2026-10-03:
- AHA, "How to Take an Accurate Hydrometer Reading", https://homebrewersassociation.org/how-to-brew/how-to-take-an-accurate-hydrometer-reading/
- Wyeast FAQ, https://wyeastlab.com/faqs/
- MISCO, https://www.misco.com/beer-calculator/

These were matched only to existing source entries with the same publisher and title:

| Record | AHA hydrometer guidance | Wyeast FAQ on airlock activity | MISCO technical note REV140407-1 | Other |
|---|---|---|---|---|
| FACT-MEAS-0001 | URL + Chief spot-check note added | not cited | **not matched** (a different MISCO page was checked) | Wyeast "Yeast Fermentation" and BYO not re-checked |
| FACT-MEAS-0002 | URL + Chief spot-check note added | URL + Chief spot-check note added | **not matched** | — |
| FACT-MEAS-0003 | URL + Chief spot-check note added | not cited | **not matched** | BYO not re-checked |

Each record's `notes` gets a dated sentence saying which sources were spot-checked and which remain open. Claims, classification, status and
`verified_at` are unchanged. No source entry was added or removed.

**Status update 2026-10-04 (source spot-check follow-up; supersedes the "not matched" / "not re-checked" cells above):**

The cited MISCO REV140407-1 technical note was located and matched from the PDF itself, and the BYO (Dave Green) and Wyeast
"Yeast Fermentation" entries were matched to their pages. These checks were done by Local Claude on Chief instruction and are
recorded for Chief confirmation on the source entries.

Every source entry of FACT-MEAS-0001..0003 now carries a source-level check. The stored BYO publication/modified dates remain
unconfirmed. Claims, status and sources are unchanged.

### 21.8 Governance

- The Foundation slice is approved for **implementation-issue creation**. Module code still requires that implementation issue.
- The issue cannot be created while GitHub is unavailable. The paste-ready draft is §22.
- Status refresh (2026-10-04): the **Foundation** slice is implemented locally/offline on
  `offline/measurement-foundation-implementation` and merged into the offline integration rehearsal (10 cards; Måling at
  position 9, before Smak). It has **not yet landed on GitHub/master**: the §22 issue and a PR are still required.
- **Kompetent** (§21.6) is **not implemented**.

## 22. Foundation implementation issue — draft (create on GitHub when access returns)

Paste the block below as the issue body. Title: **V2.2 Måling og bryggelogg — Foundation module (`measurement.fundamentals`)**.

~~~markdown
## Goal

Implement the **Foundation** part of the Bryggeskole module **Måling og bryggelogg** (`measurement.fundamentals`), exactly as locked in
`docs/development/v22_measurement_brewlog_module_contract.md` §21 (Chief review 2026-10-03). Foundation only. Kompetent is a later issue.

Governed by #434 (contract, merged in #435), child of #343 (Roadmap V2.2 Goal 3). Facts: #444/#453 (FACT-MEAS-0001..0003).

## Prerequisites

- **Rengjøring og sikkerhet (#473)** and **Smak og evaluering (#472)** are merged first. The grid position below assumes their cards exist.
- This issue reuses #472's methodology pattern: a required `basis` field, the "Metode, ikke en faktapåstand" / "Method, not a fact claim"
  caption, and the `sensory.observation_vs_interpretation` concept.

## Scope (exact)

New, topic-scoped files following the existing pilot pattern (as `pilot_package.py` and `pilot_sensory.py` do; no shared generalisation):
- `bryggeskole/data/pilot_measurement_fundamentals.json`
  - `schema_version: 1`
  - `topic_id: PILOT-MEASUREMENT-FUNDAMENTALS`, following the existing `PILOT-<AREA>-FUNDAMENTALS` convention
- `bryggeskole/pilot_measurement.py`
  - loads the file and resolves every fact claim through the verified-only registry API (`get_verified_record`)
  - has its own wording guardrails
- registration in `ui/bryggeskole_panel.py`

### Chunks (exactly 5)

| id | basis | content | `source_claims` |
|---|---|---|---|
| CHUNK-MEAS-A | methodology | Why measure and log: know what happened before guessing why | `[]` |
| CHUNK-MEAS-B | fact | Gravity, OG, FG; OG and FG are measurements, not targets | `["FACT-MEAS-0001"]` (+ `FACT-YEAST-0002` only if the text genuinely needs it) |
| CHUNK-MEAS-C | fact | Fermentation completion: repeated readings taken some time apart stop changing; airlock is not proof | `["FACT-MEAS-0002"]` |
| CHUNK-MEAS-D | fact | Temperature: write down the reading **and** where/how it was measured; for a hydrometer sample note the sample temperature | `["FACT-MEAS-0003"]` |
| CHUNK-MEAS-E | methodology | Minimum log; observation vs interpretation; plan vs actual is evidence, not a grade/diagnosis; never overwrite a raw reading, record corrections separately | `[]` |

CHUNK-MEAS-D has `basis: "fact"` because it carries FACT-MEAS-0003. Its "write down where/how you measured" part is phrased as a recording
habit. It is never phrased as a factual claim about temperature differences between places.

### Questions (exactly 6, all `difficulty: "beginner"`)

| id | type | basis | concepts | `source_claims` | tests |
|---|---|---|---|---|---|
| Q-MEAS-001 | concept_check | fact | `measurement.gravity` | `["FACT-MEAS-0001"]` | OG/FG are measured values, not recipe targets |
| Q-MEAS-002 | scenario | fact | `measurement.fermentation_complete` | `["FACT-MEAS-0002"]` | Airlock has gone quiet: what tells you more? (repeated gravity readings, not the airlock) |
| Q-MEAS-003 | scenario | methodology | `log.planned_vs_actual` | `[]` | Measured FG differs from the recipe's predicted FG: record the reading as it is; predicted FG is a plan value; the difference is evidence to look at, not a grade |
| Q-MEAS-004 | scenario | methodology | `measurement.temperature` | `[]` | What to write down for fermentation temperature: the reading **and** where/how it was measured |
| Q-MEAS-005 | concept_check | fact | `measurement.hydrometer_temperature` | `["FACT-MEAS-0003"]` | Note the sample temperature; the reference temperature is the one stated on the instrument or in its instructions |
| Q-MEAS-006 | scenario | methodology | `sensory.observation_vs_interpretation` | `[]` | Separate what was measured/seen from what you think caused it |

Methodology concept allow-list for this module (closed): `log.planned_vs_actual`, `measurement.temperature`,
`sensory.observation_vs_interpretation`. Do **not** introduce `log.observation_vs_interpretation`. `measurement.volume` is taught in CHUNK-MEAS-E
without its own question in this slice.

### Basis rules

- Each fact claim used must be `status: verified` and resolve through the verified-only API.
- `methodology` requires `source_claims == []` and a concept from the allow-list. Methodology chunks and questions show the method caption and
  never claim a brewing source.
- Allowed facts, exactly: FACT-MEAS-0001, FACT-MEAS-0002, FACT-MEAS-0003, and FACT-YEAST-0002 (CHUNK-MEAS-B only, optional). No other record.
- `modules: ["measurement.fundamentals"]` may be added to the records the module actually uses. This is the only registry change allowed, and
  `tests/test_course_fact_registry.py`'s "documented facts without modules" assertion is updated accordingly. Claims, classification, status
  and sources stay unchanged.

### Content rules (binding wording traps, both languages; contract §19 and §21)

- No fixed number of hours or days. One reading is not enough. "Stable" always means readings taken some time apart.
- Predicted FG is a plan value, not a measurement. No claim beyond FACT-MEAS-0002 about what a stable reading proves or disproves.
- The airlock is not proof.
- No "room temperature is not beer temperature" and no "active fermentation warms the beer" (not verified; M5).
- No universal reference/calibration temperature, fermentation temperature or correction factor. No ABV, attenuation, efficiency, Plato or
  Brix formulas or numbers.
- Volume: teach "record the volume into the fermenter in your brew log/notes". **Never** say the App's volume field (`actuals.volumeL`) stores
  that volume. The App's Bryggedag panel stores post-boil volume there.
- Plan vs actual is evidence to look at, never a grade, score, pass/fail, diagnosis or blame.
- Never overwrite a raw reading. A correction is recorded separately.
- No hypothesis/next-change teaching (Kompetent).

### Placement

Insert after Pakking and before Smak og evaluering in both environments: … → 8 Pakking → **9 Måling og bryggelogg** → 10 Smak og evaluering
(the grid grows from 9 to 10 cards; Oppskriftsforståelse later goes between Måling and Smak). EN card title: "Measurement and brew
log". The Hjemmebrygger/Bryggeri chooser stays a presentation axis only. There is one shared lesson set, no per-environment content.

### NO/EN

Every chunk, prompt, option and feedback text exists in `no` and `en` with identical keys and structure. Terminology follows contract §8: *tetthet*,
*hydrometer*, *OG/FG*, *målt* / *measured*, *planlagt* / *faktisk*; keep measurement, target and interpretation as distinct words.

## Tests

- `tests/test_pilot_measurement.py` (new), mirroring `tests/test_pilot_package.py` / the #472 sensory tests:
  - exactly the 5 chunk ids and 6 question ids, in order
  - all questions `beginner`
  - exact basis, concepts and `source_claims` per the tables above
  - every fact claim verified
  - methodology rules: allow-list, empty claims
  - NO/EN key symmetry
  - wording-trap guards: no digits for hours/days; no `volumeL`/"into the fermenter" mapping to the App field; no room-vs-beer statement; no
    ABV/Plato/Brix formula; no `log.observation_vs_interpretation`
- `tests/test_course_fact_registry.py`: still exactly FACT-MEAS-0001..0005, and claims/status unchanged. Only the `modules` assertion is updated.
- `tests/test_ui_bryggeskole_panel.py`:
  - grid order with Måling at position 9, after Pakking and before Smak og evaluering (now position 10), in both environments
  - lesson renders NO/EN
  - methodology caption shown only on methodology items
- Mastery tests: answers are recorded under the concept ids above. `sensory.observation_vs_interpretation` is shared with Smak, not duplicated.
  Isolated state via `KVERNHAUG_BRYGGESKOLE_STATE_DIR`.
- `tests/playwright_streamlit/module-grid-responsive.spec.js`: card count updated from 9 to 10 cards and `MODUL_TEKST` (NO/EN) gets Måling at position 9, before Smak. The layout assertions stay
  as they are. Chromium + Firefox, desktop + mobile.
- Answer-order tests if the module uses `answer_order.py`.
- `git diff --check`.

## Owner QA (owner PC)

- NO and EN, both environment choices, desktop and narrow/mobile widths.
- Walk the contract §16 scenario, steps 1–6, as amended in §21.
- Check:
  - no unverified claim shown
  - no numbers or formulas
  - no claim about which volume the App stores
  - methodology captions present
  - mastery recorded
- Chief acceptance follows owner QA.

## Non-goals

- No Kompetent content: instrument choice, instrument checks, volume stages, raw-vs-correction depth, mash temperature, hypothesis/next change.
- No Brew History schema, `.kbhbrew` or Core change. No `actuals.volumeL` decision (G-1 stays open). No new Brew History fields.
- No Learn→Reflect bridge and no gravity-over-time visual (later slices).
- No calculator duplication. No App calculator, Web, `web/en/**` or Sóti change.
- No new Course Fact and no claim/status/source change.
- No #471 work.
- No scoring, badges, gating, grading or AI-generated interpretation.
~~~

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted in this run; no module, question, UI, bridge or visual implemented; no Core/schema
change; no gate in §15 decided; no Web/public or Sóti change; no deploy.

v1.1 (2026-10-03, Chief review closure): records the decisions in §21 and the issue draft in §22. The only registry change is spot-check
metadata on FACT-MEAS-0001..0003 source entries and notes (§21.7). No claim, classification, status or `verified_at` changed. Still no module,
UI, Core/schema, Web or Sóti change, no gate decided, and no deploy. No GitHub issue was created.
