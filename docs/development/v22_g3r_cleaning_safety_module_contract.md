# V2.2 G3R — Rengjøring og sikkerhet (cleaning and safety) Foundation contract

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#432](https://github.com/Joludvig/kvernhaug-brygghus/issues/432), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3); product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65); curriculum owner
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (merged), whose map
(`v22_g3q_full_bryggeskole_curriculum_map.md`, §4.4, §11, §13, §15, §18) recommends this module; current-product inventory
`v22_g3q_current_bryggeskole_coverage_inventory.md`; sibling contract `v22_g3p_raw_material_learning_contract.md` (Råvarer).
Authoritative base at creation: `40221da54e48bce86dda446fabd52786c276a1d1`.

This is a docs-only contract. It contains **no product code, no Course Fact Registry mutation, no new verified fact, no module, no UI,
no App/Web/Core/Sóti change and no deploy**. Chief must review it before any implementation child issue is opened.

## 0. Source-status guard (read first)

The source reconnaissance behind this contract (delivered to the owner before #432 was implemented) is a **source map, not a verified fact
pack**. It is not stored in the repository, and **this run did not open any external source**. Therefore:

- Sources named in §6 are recorded with what the reconnaissance found. They are **directions for the later fact-pack round**, not citations.
  The fact-pack round must re-open and read every source it cites, record scope and tier, and have Chief review it.
- Every candidate claim in §5 is **unverified** until that round has done so.
- Only the four registry records listed in §4 are reusable now, and only within their existing `notes`/wording-trap scope.
- Exact numbers (concentrations, contact times, temperatures, exposure limits, ppm, first-aid minutes), product names and shelf-life durations
  are out of the Foundation layer unless a later source review checks them for scope and quality.
- The reconnaissance read some sources directly and some through a summarising fetch tool. The fact-pack round must spot-check quotes against
  the live source before promoting any record.

## 1. Learner outcome

After Rengjøring og sikkerhet, a homebrewer with no prior knowledge can, in their own words and without numbers to memorise:

1. say the difference between **cleaning** (removing dirt and residue) and **sanitising** (reducing microorganisms on a clean surface), and that sanitising does not replace cleaning;
2. state the order: **clean first, sanitise second**, and say why a dirty surface cannot be properly sanitised;
3. say **where sanitation starts to matter** in the brew day (once the wort is cooling, everything that touches it must be clean and sanitised), and that a hot boil does not make the rest of the brew day safe;
4. handle **cleaners and sanitisers** safely: follow the product label and safety data sheet, protect eyes and hands where they say so, use them ventilated where they say so, keep them in the original container and out of children's reach, and never mix cleaning products;
5. explain that **fermentation produces CO₂**, that CO₂ has no smell or colour and can collect in small, closed or low spaces, and what the simple precaution is (ferment in a ventilated space);
6. explain that a **sealed bottle or keg is under pressure** and that only suitable, undamaged, rated equipment should hold it.

Non-outcome: memorising concentrations, contact times, product names, exposure limits, chemical reaction lists or safety-system procedures; passing a
professional safety or microbiology course. The learner should feel calmly informed, not alarmed.

## 2. MUST concepts (Foundation)

Concept ids follow the registry style (`area.topic`). Ids marked *existing* are already used by registry records. Ids marked *new* are proposals
for the fact-pack round, not existing registry concepts.

| # | MUST concept | Proposed id | Source of truth |
|---|---|---|---|
| 1 | Cleaning vs sanitising | `hygiene.clean_vs_sanitize` (new) | N1 (§5) |
| 2 | Clean first, sanitise second | `hygiene.clean_first` (new) | N1 (§5) |
| 3 | Hot-side / cold-side sanitation boundary | `cool.sanitation_boundary` (*existing*) | FACT-COOL-0003 (reuse) |
| 4 | Chemical handling: label/SDS, eye/hand protection, ventilation, original-container storage, do not mix cleaning products | `safety.chem_handling` (new) | N2 (§5) |
| 5 | Fermentation CO₂ in enclosed / poorly ventilated spaces | `safety.fermentation_co2` (new) | N3 (§5); L1 MUST = owner decision (§13, resolved) |
| 6 | Pressure safety for sealed bottles, kegs and rated equipment | `package.pressure_safety` (*existing*) | FACT-PACK-0003 (reuse) |

Concept 5 is an unconditional Foundation MUST by owner decision (2026-09-30, §13). Concepts 1–4 and 6 are MUST unconditionally.

## 3. SHOULD, optional and LATER

**SHOULD / optional (second slice; each needs its own source review):**

| Candidate | Proposed id | Status |
|---|---|---|
| Scald first aid (cool with running water; when to seek medical help). Boil-over itself is already covered by FACT-BOIL-0004 | `safety.scald_first_aid` (new) | Optional. First-aid support exists from a Norwegian public health source; homebrew-specific **prevention** evidence is incomplete. |
| Electrical equipment near liquids | `safety.electric_near_liquids` (new) | SHOULD/LATER. Generic wet-environment shock-risk support exists from a Norwegian electrical-safety source; **no brewing-specific authoritative source was found**. |
| Spoilage vs safety (quality vs health framing) | `safety.spoilage_vs_safety` (new) | Deferred. The blanket claim "beer cannot make you sick" is **not supported**. The desired quality-vs-health framing remains a source gap (§6). |

**LATER (explicitly not Foundation):**

- Clean-in-place (CIP) and industrial cleaning systems, caustic cleaning regimes, chemical warehouses.
- Microbiological laboratory technique, culture plating, pathogen testing, detailed contamination taxonomy.
- Professional brewery safety systems: gas monitors and alarms, confined-space entry procedures, permits, lock-out/tag-out, compliance training.
- Quantitative pressure engineering: burst ratings, relief-valve sizing, keg and regulator specifications.
- Electric brewery wiring, circuit sizing, element and controller guidance.
- Dosing tables for cleaners and sanitisers; product comparisons; brand recommendations.
- Milling-area mechanical hazards and other industrial plant safety.

**Deviations from the #419 map, recorded so they are not silent:**

- #419 §11 lists *Hot liquids, burns, boil-over* as L1 MUST with a "burn/hot-liquid handling record" needed. This contract keeps boil-over covered by FACT-BOIL-0004 and makes scald first aid optional, because no homebrew-specific prevention source has been found. A new fact is not created from general knowledge.
- #419 §11 lists *Spoilage vs safety* as L1 MUST. This contract defers it, because the evidence does not support the blanket claim and the wording-critical half has no opened source. Revisit when the gap in §6 is closed.
- #419 §18 suggests one combined `sikkerhet.co2_trykk` mastery id. This contract separates CO₂ and pressure (§11), because pressure is an existing fact and CO₂ is a new one.

## 4. Existing verified facts reused now

All four are `status: verified` in `bryggeskole/data/course_fact_registry.json` at the base SHA. Reuse only within each record's `notes` scope; the
wording traps in those notes remain binding. Do not duplicate them into new records.

| Record | What it carries in this module | Boundary |
|---|---|---|
| **FACT-COOL-0003** (documented_fact) | Concept 3 and the hot/cold visual: heat protects only while the wort is at or near boiling; once cooling begins, everything that touches wort or beer must be clean and sanitised. | Does not name a sanitiser, contact time or procedure. Notes forbid implying the boil "immunises" downstream equipment. It does not explain the *difference* between cleaning and sanitising or their order, which is why N1 is needed. |
| **FACT-COOL-0001** (documented_fact) | Context only: rapid cooling reduces the time the wort spends in a range where spoilage organisms can grow. Used to explain *why the cold side is the risk window*. | Not a hygiene-procedure fact. Not a "danger zone" temperature claim. Do not use it as a source for cleaning or sanitising. |
| **FACT-BOIL-0004** (practical_experience) | Boil-over: foam can rise fast in the first minutes of a rolling boil; reduce heat or stay attentive. Used for the hot-liquid unit. | Covers the process event, not injury or first aid. Does not claim a boil-over always happens or quantify a fill level. |
| **FACT-PACK-0003** (documented_fact) | Concept 6: packages hold pressure; damaged or unrated containers risk failure; use suitable rated equipment. | States the boundary, not pressure numbers, ratings, product lists or engineering. Its own notes forbid brand/product naming. |

**Source-quality note (flag only, no change proposed):** FACT-PACK-0003 lists a Lallemand thiol-preservation guide among its sources. Its relevance
to pressure safety was not obvious during reconnaissance, and that source was not re-opened. If a later source-quality review finds FACT-PACK-0003
insufficient, it is a separate issue. This contract does not create a new pressure fact.

## 5. Missing fact pack — the smallest expected future fact pack

Each record is a future registry-mutating round (not this issue). Record shapes follow the existing registry: `id`, `claim`, `classification`,
`status`, `verified_at`, `sources[]` (tier/type/ref), `concepts[]`, `modules[]`, `notes` (scope + wording traps). This contract defines
direction only; it does not implement records, and ids `FACT-…-NNNN` are assigned by the fact-pack round.

### N1 — Cleaning vs sanitising + clean-first order

- Concepts: `hygiene.clean_vs_sanitize`, `hygiene.clean_first`.
- Direction of claim: *Cleaning removes dirt and residue. Sanitising reduces microorganisms on a clean surface and does not replace cleaning. A dirty surface cannot be properly sanitised, so clean first and sanitise second.*
- Classification: `documented_fact`.
- Source direction: Tier A — public-health authority guidance on cleaning/sanitising/disinfecting (CDC handout) and manufacturer technical material stating that surfaces are cleaned before the sanitiser is used (Star San product tech sheet). Tier B — Palmer, *How to Brew*, Ch. 2 (definitions of clean/sanitise/sterilise; "sterilization is not necessary"); university extension guidance for corroboration.
- Scope: general home/small-scale equipment. Not product-specific, not a procedure.
- Traps: "sanitised = sterile"; product names, concentrations, contact times or "no-rinse" claims; treating "clean" as sufficient for surfaces that touch cooled wort.
- Reuse note: FACT-COOL-0003 already carries "clean and sanitised" at the boundary. N1 adds the *difference* and the *order*, and must not restate the boundary.

### N2 — Generic chemical handling

- Concept: `safety.chem_handling`.
- Direction of claim: *Cleaners and sanitisers can harm skin and eyes. Follow the product label and its safety data sheet; wear the eye and hand protection they call for; use them ventilated where they say so; keep them tightly closed, in the original container, and out of children's reach. Do not mix different cleaning products.*
- Classification: `documented_fact`.
- Source direction: Tier A — manufacturer safety data sheets for one acid-based sanitiser and one alkaline/percarbonate cleaner (hazard classification, PPE, ventilation, storage, listed incompatibilities); Norwegian poisons-information service guidance on keeping chemicals in the original container and on first response. Tier A/B — extension guidance for "do not mix".
- Scope: generic, product-neutral. The claim teaches the *habit* of reading the label and SDS, not any product's chemistry.
- Traps:
  - No dosing, concentrations, contact times or classification codes.
  - Do **not** claim that PBW-type cleaner plus an acid sanitiser creates gas or heat: neither product's SDS says so. Each SDS lists incompatibilities (strong bases/oxidisers for the sanitiser; strong oxidisers/acids for the cleaner) but neither describes the outcome of mixing them.
  - Keep product-specific chemistry out of the generic claim, including the Star San tech-sheet warning against chlorinated cleaners. That warning belongs to one product's documentation, not the Foundation fact.
  - Do not present a US SDS as a Norwegian label. Products sold in Norway carry their own EU-format label and SDS, so the claim is "read *your* product's label and SDS".
  - Kunze p. 718, §6.1.2 (hypochlorite mixed with acidic cleaners) is **corrosion context for chrome-nickel steel, not a human-safety source**. It must not be cited for chemical-mixing safety.

### N3 — Fermentation CO₂, qualitative hazard

- Concept: `safety.fermentation_co2`.
- Direction of claim: *Fermentation produces carbon dioxide. CO₂ is colourless and odourless, is heavier than air, and can collect in small, closed or low spaces and displace oxygen. Ferment in a ventilated space.*
- Classification: `documented_fact` (hazard mechanism); the "ferment in a ventilated space" precaution is a proportionate interpretation and must be marked as such in `notes`.
- Source direction: Tier A — a regulator alert that explicitly covers fermentation in carboys and buckets (Ontario workplace guidance; nearest small-vessel analogue, but still commercial/workplace scale); generic asphyxiant and oxygen-displacement guidance from public safety bodies. Tier B — Brewers Association CO₂ hazards material; Kunze §4.9.1, printed p. 523 (visually verified in reconnaissance).
- Scope: qualitative mechanism and a simple precaution. **Homebrew-scale probability is not quantified by any authoritative source found.**
- Traps:
  - No ppm, percentage thresholds, workplace exposure limits, gas monitors, buddy systems or confined-space entry procedures (industrial).
  - Do not say home fermentation is dangerous in ordinary use, and do not say it is harmless.
  - Do not say "you will smell it" (it is odourless).
  - Do not merge dispensing/cylinder CO₂ with fermentation CO₂; they are different sources.
  - Do not transfer Kunze's percentages, workplace limits or fermenter-entry procedures to a home fermenter.

### Optional records (second slice only)

- **O1 scald first aid** (`safety.scald_first_aid`): Norwegian public health guidance on cooling a burn with running water and when to seek help. Numbers (minutes, temperature) go in the record only if a decision is made to teach first aid; a homebrew prevention claim has no source.
- **O2 electricity near liquids** (`safety.electric_near_liquids`): generic Norwegian electrical-safety guidance that shock risk is greatest where things are wet and that earth-fault protection exists to protect people. No wiring, circuit or element advice.
- **O3 spoilage vs safety** (`safety.spoilage_vs_safety`): peer-reviewed research shows pathogens tested could not grow in standard-strength beers but could survive for weeks, and grew in alcohol-free beer. It does not support "safe". The quality-vs-health half has no opened source, so the record waits for one.

## 6. Source map from reconnaissance, and explicit source gaps

**Source map** (directions only; §0 applies). Tier A = manufacturer documentation/SDS, regulators/public-health bodies; Tier B = established brewing
technical material, Kunze as structured support.

| Topic | Sources the reconnaissance found | Tier | Notes |
|---|---|---|---|
| Clean vs sanitise, order | CDC "The Difference Between Cleaning, Sanitizing, & Disinfecting" (2022 handout); Five Star Star San product tech sheet (Rev. 6/03); Palmer *How to Brew* Ch. 2; Penn State Extension | A / A / B / A-B | Palmer read directly; CDC and tech sheet read from extracted PDF text |
| Chemical handling | Five Star Star San SDS (rev. 11/17/2020); Five Star PBW SDS (3/9/2022); Helsenorge/Giftinformasjonen "Farlige produkter i hjemmet" (13 May 2024) | A | SDSs are US-format; Norwegian page read via summarising fetch |
| Fermentation CO₂ | Ontario Ministry of Labour alert on brew-on-premise/wine-making establishments (2022, updated 2025); Brewers Association "CO2 Hazards" (2026); Kunze §4.9.1, p. 523 | A / B / B | Ontario and BA read via summarising fetch; Kunze page viewed visually |
| Generic asphyxiant background | HSE carbon dioxide page; WorkSafe Victoria cellar gas page; NIOSH pocket guide; OSHA oxygen-deficient atmospheres page; Arbeidstilsynet tank-work page | A | None of these mention fermentation as a source (verified on opening). Arbeidstilsynet does not name CO₂. Background only. |
| Scald first aid | Helsenorge "Førstehjelp ved brannskader" (8 May 2026) | A | First aid only, not prevention |
| Electrical | Elsikkerhetsportalen "Alt om jordfeil" | A/B | Generic; not brewing-specific |
| Spoilage vs safety | Menz, Aldred & Vriesekoop, *J. Food Prot.* 2011 (abstract) | A | Laboratory inoculation study; abstract only |

**Explicit source gaps** (must stay visible in the fact-pack round; not to be filled from general knowledge or AI):

- **G1** Norwegian authoritative terminology for cleaning/sanitising/disinfecting in the homebrew context is not confirmed. The Mattilsynet pages found concern aquaculture and organic farming and were not opened. Do not silently equate *sanitering*, *desinfeksjon* and *sterilisering* (§8).
- **G2** No authoritative source quantifies home-fermenter CO₂ risk or names a room size or batch size. No Norwegian source on fermentation CO₂ was found. The nearest regulator analogue (Ontario) is workplace scale.
- **G3** No authoritative homebrew-specific source on preventing scalds when handling hot wort. Only first aid is sourced.
- **G4** No brewing-specific authoritative source on electrical safety.
- **G5** "Spoilage from infection usually affects flavour rather than health" has no opened source.
- **G6** No source states what happens when a PBW-type cleaner and an acid sanitiser are mixed.
- **G7** FACT-PACK-0003's Lallemand source looks off-topic for pressure safety (§4). Not re-opened; flag only.
- **G8** The Menz paper was read as an abstract only.
- **G9** Kunze pages not visually verified in reconnaissance: pp. 716, 720, 722–732 and 524–532. Anything drawn from them needs a visual check first (§16).

## 7. Wording traps (binding for the fact-pack round, questions and UI copy, in both languages)

- "Sanitised = sterile." Sterilisation is neither needed nor achieved by homebrew sanitisers.
- "Beer cannot make you sick" or "nothing survives in beer." Not supported. Do not write it, imply it, or accept it as a correct answer.
- "Everything on the hot side is automatically sterile", or any suggestion that the boil immunises later equipment.
- Any dosing, concentration, ppm, contact time, shelf-life or product/brand name in a Foundation claim.
- "PBW plus Star San produces gas or heat." Not supported.
- A chlorine-gas warning presented as a general rule. It is one product's documented warning about chlorinated cleaners.
- Kunze p. 718 mixing warning used as a human-safety source (it is a steel-corrosion note).
- A US SDS classification presented as the Norwegian label or as the learner's product.
- CO₂: "you will smell it"; "home fermenting is dangerous"; "home fermenting is harmless"; ppm or percentage thresholds; monitors, buddy systems or entry procedures; merging dispensing CO₂ with fermentation CO₂.
- Pressure: pressure numbers, brand/product lists, rating tables (per FACT-PACK-0003 notes).
- Burns: no prevention claims without a source; if first aid is taught, no ice and no wet cloth as the source states.
- Tone: proportionate. Do not write scare copy; severity is stated once and the precaution is simple and specific.

## 8. NO/EN terminology strategy

- Match the words already in the product, and do not introduce a second term for an existing concept. The current cool/transfer module uses Norwegian *rent og sanitert* / *rengjøring* / *sanitert håndteringssone* and English *clean and sanitized* / *sanitized handling zone*.
- **Norwegian:** *rengjøring* (rengjøre) for cleaning; *sanitering* (sanitere / sanitert) for sanitising, matching current App wording. Use *desinfeksjon* only where a fact-pack source uses it, and gloss it in the same sentence rather than treating it as a synonym. Do not use *sterilisering* as a synonym for sanitising; introduce it only to say it is not required.
- **English:** *clean* / *sanitize*, matching current App spelling (*sanitized*). Prose in docs may use *sanitise*; UI and course copy follow the App spelling. This is a spelling variant only and does not need a decision.
- **Owner/Chief confirmation needed (G1):** confirm which Norwegian term is authoritative for the homebrew context before the fact-pack round finalises Norwegian claim text. Until then, the Norwegian claim text keeps the current App wording and flags G1.
- Every chunk, question, option and explanation exists in Norwegian and English with NO/EN key symmetry, as in the current modules. The registry claim is the single source for both languages; wording traps apply in both. No loose translation of safety claims.
- No public Web page or generated `web/en/**` change in this line of work. If a later slice touches Web help, use `python3 scripts/generate_web_i18n_pages.py` only and never hand-edit `web/en/**`.

## 9. Hot-side / cold-side visual concept

Recommended as the module's one visual (#419 §13 ranks it High value: "the single most misunderstood hygiene concept and is easy to show").

- Extend, do not replace, the existing static stage diagram in `bryggeskole/cool_transfer_flow.py`, which already shades a "sanitized handling zone" from cooling onward. This contract does not touch that file. The implementation slice decides whether to reuse the SVG helper or add a sibling.
- Content: a horizontal brew-day strip (mash → boil → cooling → transfer → fermentation → packaging). Heat-protected region marked only around the boil; sanitised-handling region from the start of cooling; a small "clean first, then sanitise" callout. No temperatures, no minutes.
- Constraints: qualitative only; static SVG (the same technique as `boil_timeline.py`); identical NO/EN labels; must not suggest the hot side is sterile or that the boundary is a fixed temperature; the shading marks a boundary, not a guarantee (as in FACT-COOL-0003's notes).
- No interactive simulator, calculator or animation.

## 10. Recommended short module/chunk structure

**One short module, "Rengjøring og sikkerhet"** (module 1 in the #419 §15 sequence: Råvarer first, then this module, then the process spine).
Indicative id `safety.fundamentals`; the implementation issue fixes the final id and file names.

- About **6–7 chunks** and **6–8 questions**, mixing `concept_check` and `scenario`, matching the current chunk/question pattern (`bryggeskole/pilot_*.py` and `bryggeskole/data/pilot_*.json`).
- Indicative chunks:
  1. Clean vs sanitise (N1)
  2. Clean first, sanitise second (N1)
  3. Where the boundary is — hot side / cold side, with the visual (FACT-COOL-0003, FACT-COOL-0001 context)
  4. Handling cleaners and sanitisers (N2)
  5. Hot liquids and boil-over (FACT-BOIL-0004; scald first aid only if O1 ships)
  6. CO₂ from fermentation (N3, required; owner decision §13)
  7. Pressure in sealed bottles and kegs (FACT-PACK-0003)
- Chunks that only restate an existing fact link to the existing Kjøling/overføring, Koking/humle and Pakking chunks rather than duplicate them.
- Placement: before the process spine as a recommended order, **not a hard gate**; existing modules stay reachable. Kjøling/overføring's sanitation-boundary chunk gets a text link to this module; that link is a later slice.
- A chunk enters the module only after its fact record is verified. If N1–N3 are not all ready, ship only the sections whose records are verified.
- Not recommended: several separate safety modules, an industrial-safety track, or a CIP/microbiology track.

## 11. Mastery concept IDs

In this codebase the mastery concept ids are the registry concept ids carried by question `concepts[]` (for example `cool.sanitation_boundary`,
`package.pressure_safety`). This contract therefore uses registry-style ids rather than the illustrative `sikkerhet.*` ids in #419 §18. One hidden
mastery concept per MUST concept; no new mastery mechanics.

| Concept id | Origin | Owns |
|---|---|---|
| `hygiene.clean_vs_sanitize` | new (N1) | difference between cleaning and sanitising |
| `hygiene.clean_first` | new (N1) | order; why a dirty surface cannot be sanitised |
| `cool.sanitation_boundary` | existing | hot-side/cold-side boundary (reuse; already used by the cool-transfer and package modules) |
| `safety.chem_handling` | new (N2) | label/SDS, PPE, ventilation, storage, do not mix |
| `safety.fermentation_co2` | new (N3) | fermentation CO₂ hazard and simple precaution |
| `package.pressure_safety` | existing | pressure in sealed containers (reuse; already used by the package module) |

Optional/later ids, only if their records ship: `safety.scald_first_aid`, `safety.electric_near_liquids`, `safety.spoilage_vs_safety`.

Question types: `concept_check` for definitions; `scenario` for decisions. Wrong-answer explanations reuse registry wording. No question may rest on an
unverified claim. No new scoring, badges or gating.

## 12. Representative acceptance scenario

A new homebrewer is about to make a first batch with a used fermenter and a bottle of sanitiser.

1. They notice the fermenter has visible residue. They **clean it first** and say why sanitiser alone would not work on a dirty surface, in their own words (N1).
2. They explain what sanitising adds: it reduces microorganisms on a clean surface but does not make anything sterile.
3. On the brew-day strip they point to where heat stops protecting the wort and say the fermenter, hose, airlock and every tool used from then on must be clean and sanitised (FACT-COOL-0003).
4. Before opening the sanitiser they check the **label and safety data sheet**, put on eye and hand protection as directed, use it ventilated as directed, and afterwards close it and return it to its original container out of reach of children. When offered a "stronger" mix of two cleaners they decline (N2).
5. They plan to ferment in a ventilated room rather than a small closed cupboard, and can say why in one sentence (N3, required; owner decision §13).
6. They say a sealed bottle or keg is under pressure and that only suitable, undamaged, rated equipment should hold it (FACT-PACK-0003).

Pass condition: an independent reader answers all steps correctly on a first read-through; no unverified claim is shown; no dose, contact time or
product name appears; NO/EN show identical content. Owner-PC QA of the implementation remains a separate gate.

## 13. Owner decision: fermentation CO₂ at Level 1 — resolved as MUST

**OWNER DECISION (2026-09-30): CO₂ at L1 = MUST.** This gate is resolved. The decision is recorded here as given by the owner; the research below is the rationale and evidence limit behind it.

**Rationale (from the research recommendation that preceded the decision):** MUST is supported as a cautious recommendation, with calm qualitative framing,
because:

- severity is high (asphyxiation is possible and can be fatal);
- the hazard is invisible and odourless, so a beginner cannot detect it;
- mitigation is simple (ferment in a ventilated space);
- both the nearest regulator analogue (Ontario, carboys and buckets) and the visually verified Kunze §4.9.1 describe the mechanism.

**Limit of the evidence:** homebrew-scale probability is not quantified by any authoritative source found (G2). The regulator analogue is
workplace scale. What makes MUST defensible is severity and cheap mitigation, not measured likelihood.

**Consequences of the decision:**

- N3 is in the smallest fact pack, the CO₂ learner outcome (§1 item 5) is required, the acceptance-scenario step (§12 step 5) is required, and the module's CO₂ chunk is required, not optional. Framing stays one short, proportionate caution, never an industrial safety unit.

Nothing else in this contract depended on the answer, so resolving the gate re-opens no other decision.

## 14. Smallest implementation slices

| # | Slice | Type | Depends on |
|---|---|---|---|
| 1 | **N1 fact pack**: cleaning vs sanitising + clean-first (sources opened and read; registry records; tests) | Registry + tests | this contract |
| 2 | **N2 fact pack**: generic chemical handling (SDS-based) | Registry + tests | this contract |
| 3 | **N3 fact pack**: fermentation CO₂ qualitative hazard | Registry + tests | this contract + §13 owner decision (**RESOLVED: MUST**) |
| 4 | Module skeleton with only the sections whose records are verified; questions, NO/EN, mastery, module registration | Module + tests | 1–3 (each section may ship when its record is done) |
| 5 | Hot-side/cold-side visual | UI | 4 |
| 6 | Kjøling/overføring link to this module and other Learn→Plan links | UI | 4 |
| 7 | Optional records O1–O3, each with its own source review | Registry (+ module) | gaps G3–G5 closed |
| 8 | Owner-PC QA + Chief acceptance against §12 | QA | 4–6 |

Slices 1–3 are independent of each other and may be separate bounded issues or one combined issue (the smallest fact pack); the WIP rule of #343
still applies. This contract defines but does not implement them.

## 15. Hard non-goals

- No Course Fact Registry change and no new verified fact in this issue.
- No module, chunk, question or UI implementation; no bridge changes.
- No App, Web, Core or Sóti change; no masterdata or recipe-engine change; no generated `web/en/**` change.
- No CIP or industrial cleaning depth.
- No chemical dosing tables, concentrations, contact times or product/brand recommendations.
- No wiring, circuit, element or controller advice.
- No quantitative pressure engineering or pressure numbers.
- No microbiology laboratory content.
- No professional brewery safety systems, confined-space procedures or compliance training.
- No unsupported claims drawn from general knowledge or AI; source gaps stay explicit.
- No deploy, no merge authority.

## 16. Kunze anchors (Tier B, structural support only)

Kunze, *Technology Brewing and Malting*, is used only as structure for safety topics unless an exact claim is visually page-verified.

Visually verified in reconnaissance (rendered page images viewed; printed page and section recorded):

- **p. 523, §4.9.1** — fermentation CO₂: odourless and tasteless, about 1.5 times heavier than air, collects in the bottom of vessels and spaces, accident history. **Use** qualitatively only for N3; no percentages or workplace limits.
- **p. 721, §6.3** — disinfecting agents: a disinfectant needs a powerful disinfecting effect where a cleaning agent needs good cleaning power; residues must be rinsed out; use the supplier's documents. **Use** for terminology and "follow supplier documentation" only, not for chemistry.
- **p. 718, §6.1.2** — hypochlorite and acidic cleaning solutions: **corrosion context for chrome-nickel steel, not a human-safety source. Do not use it for chemical-mixing safety.**
- p. 717, §6.1.2 — stainless-steel types. Not relevant.
- p. 359, §3.11.1 — milling-area accident prevention (industrial roller mills). Not needed for Foundation; LATER.

Not visually verified: pp. 716, 720, 722–732 (chemical agents, CIP and cleaning procedure, monitoring) and 524–532 (rest of §4.9). CIP and
industrial procedure content is LATER regardless. Printed-page offsets differ from PDF page numbers by section, so a fact-pack round must view the
rendered page and read the printed number, and must not rely on OCR text for any exact claim.

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted in this run; no module, question, UI, bridge or visual implemented; no masterdata,
recipe-engine, Web/public or Sóti change; the owner decision that fermentation CO₂ at L1 is MUST (2026-09-30) is recorded in §13; no deploy.
