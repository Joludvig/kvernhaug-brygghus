# V2.2 — Bryggeskole course stage allocation contract

Version: 1.0 (2026-10-04)
Status: **Canonical, locked owner/Chief decisions** for *where* course content belongs by stage. Decision/architecture
document only: it implements nothing and changes no lesson, registry, UI or Web file.
Recorded offline during the GitHub outage; see the sync note in §K.
Builds on: the Course Stage Allocation Audit (Local Claude, 2026-10-04, read-only) and the owner/Chief decisions on it, the
same day.
Course architecture (progression, App scope, terminology axes, canonical module order) stays canonical in
[v22_g3q_full_bryggeskole_curriculum_map.md §6.1–§6.2](v22_g3q_full_bryggeskole_curriculum_map.md#62-canonical-course-architecture-and-terminology-axes).
This contract does not restate or change it. It allocates content to stages inside that architecture.

Module contracts stay authoritative for their own scope. Where they lock a stage, this contract repeats only the pointer:
[Råvarer #418](v22_g3p_raw_material_learning_contract.md),
[Rengjøring og sikkerhet](v22_g3r_cleaning_safety_module_contract.md),
[Måling og bryggelogg](v22_measurement_brewlog_module_contract.md),
[Oppskriftsforståelse](v22_recipe_understanding_module_contract.md),
[Smak og evaluering](v22_sensory_evaluation_module_contract.md).
Where this contract moves content that an older process-module contract placed without a stage, **this contract wins**
for the stage question only.

---

## Contents

- A. [Status and authority](#a-status-and-authority)
- B. [Four-stage model](#b-four-stage-model)
- C. [11-module stage matrix](#c-11-module-stage-matrix)
- D. [Locked content moves](#d-locked-content-moves)
- E. [Foundation exit checkpoint](#e-foundation-exit-checkpoint)
- F. [Kompetent completion criteria](#f-kompetent-completion-criteria)
- G. [Bryggemester entry boundary](#g-bryggemester-entry-boundary)
- H. [Bryggeri exclusion boundary](#h-bryggeri-exclusion-boundary)
- I. [Known gaps and source blockers](#i-known-gaps-and-source-blockers)
- J. [Implementation implications](#j-implementation-implications)
- K. [Sync note and boundary statement](#k-sync-note-and-boundary-statement)

---

## A. Status and authority

- **Owner/Chief decisions, 2026-10-04.** The decisions in §B–§H are locked. Changing them needs a new owner/Chief decision
  recorded here.
- **What this contract decides:** the stage each topic, chunk and question *belongs to*.
- **What it does not decide:** teaching text, facts, sources, question wording, UI presentation, or the technical
  mechanism for showing stages (§J). A chunk tagged here for a move is **not** edited by this contract.
- **Facts:** no Course Fact Registry record is created, changed or promoted. Fact ids are cited only as they exist.
  Registry governance, the #65 source hierarchy and the source-quality rules are unchanged.
- **Kunze / #419** remains a curriculum-mapping input only (curriculum map §6.2.6, §14.3). Industrial topics do not enter
  the homebrew course merely because Kunze covers them (§H).

### A.1 Reference implementation state

Status labels in §C describe the **green integration rehearsal** `offline/full-integration-rehearsal` @
`68e146b7b67ebb8f292ae5bd29a2ce873cc0668d` (local, not on GitHub). Verified there on 2026-10-04:

| Check | State |
|---|---|
| Visible module cards | **9**: Råvarer, Rengjøring og sikkerhet, Forberedelse/metode, Mesking, Koking/humle, Kjøling/overføring, Gjæring, Pakking, Smak og evaluering (`_MODUL_REKKEFOLGE`, `ui/bryggeskole_panel.py`) |
| Måling og bryggelogg | **Not implemented.** Foundation contracted and locked (measurement contract §21.2); no pilot file, no card |
| Oppskriftsforståelse | **Not implemented.** Kompetent contracted (recipe contract §27); **blocked by the Måling Foundation module** (§27.8) |
| Smak og evaluering | **Visible**, but contractually **Kompetent** (sensory contract §1–§3). Implemented chunks are methodology only (SENS-A, B, F, G) |
| `FACT-MASH-0003` (iodine test) | **draft**; every other registry record is `verified` (58 records) |
| Stage labels in the UI | None. All visible cards are one open grid |

**On GitHub master `e48deb5`** only 7 cards are visible: Rengjøring og sikkerhet (#473) and Smak og evaluering (#472)
exist only in the offline product stack until it lands. "IMPLEMENTED" for those two modules therefore means "implemented
in the offline stack, not yet on master". This contract does not change either state.

## B. Four-stage model

| Stage | Where | Guiding question | Character |
|---|---|---|---|
| **Foundation** (Hjemmebrygger, Trinn 1) | Main App Bryggeskole | *What do I need to understand to brew safely and know what I am doing?* | Deliberately **low threshold**. A checkpoint, not completion |
| **Kompetent hjemmebrygger** (Trinn 2) | Main App Bryggeskole | *How do I make consistently good beer, understand my process and correct it?* | Course **completion** |
| **Bryggemester** | **Out of App**: voluntary advanced depth / later standalone course product | *How do I reason deeply about brewing science, formulation and process?* | Optional, never required |
| **Bryggeri / profesjonell** | **Out of App**: later professional track | *What belongs mainly to professional/industrial operation and should not burden the homebrewer course?* | Separate; **not** "even harder Bryggemester" |

**Operational heuristic (locked):**

- **Kompetent** generally explains **direction** and enables sound practical decisions.
- **Bryggemester** generally **quantifies or controls**, using maths, instruments, advanced techniques or deeper chemistry.
- **Bryggeri** is industrial operation (§H). It is a different axis from Bryggemester depth, not its next level.

**Not these axes:** the Web support modes **Bryggelærling / Bryggmester** (Lærling / Mester) and the App environment chooser
**Hjemmebrygger / Bryggeri** are presentation axes, not course stages (curriculum map §6.2.4). Course-stage "Bryggemester"
≠ Web mode "Bryggmester"; the spelling difference is intentional.

Status labels used in §C:

| Label | Meaning |
|---|---|
| IMPLEMENTED | Exists as module content at the reference state (§A.1) |
| CONTRACTED | Locked in a module contract; not implemented |
| MAPPED | Named in the curriculum map / roadmap; no module contract yet |
| GAP | Needed, but neither contracted nor sourced |
| OUT OF APP | Belongs to Bryggemester or Bryggeri, outside the main App course |

## C. 11-module stage matrix

Ids are cited as they exist today. "Moves" refers to §D. A chunk listed under Kompetent because of a move still sits in
its current module file until a later implementation slice (§J).

### C.1 Råvarer

| Stage | Content | Status |
|---|---|---|
| Foundation | What malt, hops, yeast and water each do: malt basics, base vs specialty, colour/flavour origin, grist share; hop roles, alpha % ≠ IBU, ageing; yeast role, attenuation idea, ale vs lager pattern, choice and pitch principle; water majority ingredient, chlorine/chloramine, source awareness. **All #418 Foundation MUST concepts stay Foundation** (CHUNK-RAW-A…K; FACT-MALT-0001…0004, FACT-HOP-0001…0005, FACT-YEAST-0001…0005, FACT-WATER-0001…0003) | IMPLEMENTED |
| Kompetent | The **deeper questioning** of those concepts (Q-RAW-004, 006, 009, 010, 011, 012; §D.4). Applying ingredients to recipe decisions via Oppskriftsforståelse (incl. FACT-RECIPE-0002). Adjuncts in brief (D05), mash pH as a concept (D51), colour/flavour formation in depth (D64) | Questions IMPLEMENTED (to move); recipe use CONTRACTED; D05/D51/D64 MAPPED |
| Bryggemester | Water chemistry (ions, residual alkalinity, treatment, pH measurement: D53, D41), home malting (D06), hop oils/chemistry, yeast form detail, starters, harvesting (D49), agronomy/variety context (D71) | OUT OF APP |
| Bryggeri | Raw-material evaluation and lab analysis (D77), malting technology | OUT OF APP |

Not below Foundation-exit: numbers, pH, ions, target profiles, strain/hop/malt encyclopedias, pitch-rate arithmetic (#418 §3).

### C.2 Rengjøring og sikkerhet

| Stage | Content | Status |
|---|---|---|
| Foundation | Cleaning ≠ sanitising; clean first; hot/cold-side boundary; chemical handling by label/SDS; boil-over; fermentation CO₂ in enclosed spaces (MUST by owner decision); pressure in sealed containers (CHUNK-SAFE-A…G; FACT-SAFE-0001…0003, FACT-COOL-0001/0003, FACT-BOIL-0004, FACT-PACK-0003) | IMPLEMENTED (offline stack, #473) |
| Foundation (deferred) | Spoilage vs safety framing; electrical equipment near liquids (SHOULD); scald first aid (optional) | GAP (source gaps, cleaning contract §3/§6) |
| Kompetent | No separate unit required. Intended sourness vs spoilage is taught in Smak (FACT-SENSORY-0003) | CONTRACTED (in Smak) |
| Bryggemester | Contamination/microbiology detail (D32 detail) | OUT OF APP |
| Bryggeri | CIP (D75), industrial safety systems, gas monitoring, confined spaces, chemical warehouses, pressure engineering, electrical installation | OUT OF APP |

### C.3 Forberedelse/metode

| Stage | Content | Status |
|---|---|---|
| Foundation | Own method (BIAB, traditional, all-in-one); same fundamental steps; no method hierarchy; equipment-specific planning without universal numbers (CHUNK-METHOD-A…E; FACT-METHOD-0001…0005, FACT-MASH-0001, FACT-BOIL-0001) | IMPLEMENTED |
| Kompetent | Method-aware grain separation and wort collection (in Mesking, §C.4); efficiency as a concept (D66) | MAPPED |
| Bryggemester | None mapped | — |
| Bryggeri | Brewhouse design (D72), pub/micro operation (D70) | OUT OF APP |

### C.4 Mesking

| Stage | Content | Status |
|---|---|---|
| Foundation | **Concept only:** enzymes in malt turn starch into sugars, and some into dextrins that give body (CHUNK-MASH-A, Q-MASH-001; FACT-MASH-0001) | IMPLEMENTED |
| Kompetent | Mash temperature **direction**, fermentability control, process variables (CHUNK-MASH-B, CHUNK-MASH-C, Q-MASH-002, Q-MASH-003; FACT-MASH-0002/0004; §D.1). Milling (D16), grain separation (D18) and wort collection (D19) **when sourced**; conversion check (needs FACT-MASH-0003, still draft); mash temperature as a measurement (Måling Kompetent) | MASH-B/C IMPLEMENTED (to move); D16/D18/D19 MAPPED; conversion check GAP; mash-temperature measurement CONTRACTED |
| Bryggemester | Step/decoction schedules, adjunct cereal cooking, quantitative fermentability, pH measurement | OUT OF APP |
| Bryggeri | Lauter tun / mash filter engineering (D72), brewhouse yield accounting | OUT OF APP |

### C.5 Koking/humle

| Stage | Content | Status |
|---|---|---|
| Foundation | Why we boil (enzymes stop, microbes reduced); early vs late hop timing; bitterness vs aroma; combining additions; boil-over safety (CHUNK-BOILHOP-A, C, D, E; FACT-BOIL-0001, FACT-HOP-0001…0003; boil-over in §C.2). A **simple** statement that a vigorous open boil also drives off unwanted volatiles may stay | IMPLEMENTED |
| Kompetent | DMS mechanism/detail and hot-break depth (from CHUNK-BOILHOP-B; FACT-BOIL-0002/0003); whirlpool / hop-stand technique (CHUNK-BOILHOP-F; Kunze trub-separation framing kept distinct, map §14.4); Q-BOILHOP-002, Q-BOILHOP-007 (§D.2); IBU as an estimate/index via Oppskriftsforståelse (FACT-RECIPE-0001); DMS recognition in Smak | Moved items IMPLEMENTED (to move); IBU/DMS recognition CONTRACTED |
| Bryggemester | Utilisation / Tinseth maths, hop chemistry, contested hop-compound claims | OUT OF APP |
| Bryggeri | Kettle design and heating systems (D72) | OUT OF APP |

### C.6 Kjøling/overføring

| Stage | Content | Status |
|---|---|---|
| Foundation | Cool quickly; cold-side sanitation boundary; transfer basics; cold break at one-line level; the **oxygen timing rule**: oxygen can help before fermentation, unnecessary oxygen after fermentation starts is harmful, follow yeast/manufacturer guidance (CHUNK-COOLXFER-A, B, C, E; rule part of D; FACT-COOL-0001…0003, FACT-TRANSFER-0001, FACT-OXY-0001…0003) | IMPLEMENTED |
| Kompetent | **Why** oxygen matters: sterols, unsaturated fatty acids, dry-yeast reserves (mechanism part of CHUNK-COOLXFER-D; Q-COOLXFER-004, Q-COOLXFER-005; §D.3); protein/polyphenol haze (D63) | Mechanism IMPLEMENTED (to move); D63 MAPPED |
| Bryggemester | Oxygen and flavour-stability depth (D57/D58/D62 depth) | OUT OF APP |
| Bryggeri | Heat exchangers, aeration systems, dissolved-oxygen instrumentation (D76) | OUT OF APP |

### C.7 Gjæring

| Stage | Content | Status |
|---|---|---|
| Foundation | Temperature affects activity and flavour; follow the strain's guidance (CHUNK-FERM-A…C; FACT-BREW-0001…0003). Pitch principle is in Råvarer (FACT-YEAST-0004) | IMPLEMENTED |
| Foundation (locked gap) | What happens after pitching at a simple level; knowing fermentation is active **without treating airlock activity as proof**; **finished = repeated stable gravity readings**; semantic links to Måling and Pakking (§D.9) | GAP (partly sourced, §I) |
| Kompetent | Pitching/viability concept (D45), phases (D26), by-products limited to the sourced diacetyl example plus strain/temperature flavour (D47; FACT-SENSORY-0001, FACT-BREW-0002), completion in depth (D48), conditioning/maturation (D27), yeast metabolism concept (D61) | MAPPED (roadmap slice 7, no contract) |
| Bryggemester | Starters, harvesting/reuse (D49), pressure fermentation (D50), yeast biochemistry, special methods (D67), simple viability checks | OUT OF APP |
| Bryggeri | Propagation plants / yeast lab (D78), cylindroconical schemes, CO₂ recovery (D72) | OUT OF APP |

### C.8 Pakking

| Stage | Content | Status |
|---|---|---|
| Foundation | Sanitation continues; priming is a small new fermentation in the bottle; force carbonation as a concept; minimise oxygen; pressure safety; both paths legitimate (CHUNK-PACK-A…E; FACT-COOL-0003, FACT-PACK-0001…0004, FACT-OXY-0002). Link: package only when fermentation is finished (§D.9) | IMPLEMENTED; link GAP |
| Kompetent | **Priming concept:** the priming amount controls carbonation; follow a trusted recipe, calculator or table; **no manual calculation** required (§D.6). Clarification (D28), shelf life brief (D58) | Priming concept GAP (no contract); D28/D58 MAPPED (roadmap slice 11) |
| Bryggemester | Quantitative priming and carbonation maths, pressure/kegging depth, gauges and regulators (D42, D50), foam (D57) | OUT OF APP |
| Bryggeri | Commercial packaging lines (D74), filtration/stabilisation/pasteurisation (D73) | OUT OF APP |

### C.9 Måling og bryggelogg

| Stage | Content | Status |
|---|---|---|
| Foundation | **Locked, preserved exactly** (measurement contract §1, §21.2): OG/FG as measurements, not targets; finished fermentation = repeated stable readings; temperature + where/how measured; volume into the fermenter; observation vs interpretation; plan vs actual; minimum useful brew log. **No formulas, no manual maths.** CHUNK-MEAS-A…E, Q-MEAS-001…006; FACT-MEAS-0001…0003 (verified) | CONTRACTED, not implemented |
| Kompetent | Instrument choice (FACT-MEAS-0004), refractometer after alcohol, instrument checks, volume stages (FACT-MEAS-0005), raw reading vs correction, mash temperature, hypothesis + next change (measurement §21.6) | CONTRACTED (later slice); instrument-check fact GAP |
| Bryggemester | Correction formulas, pH measurement (D41), pressure gauges (D42), efficiency maths (D66) | OUT OF APP |
| Bryggeri | Laboratory methods, inline instrumentation (D76), QC (D77) | OUT OF APP |

### C.10 Oppskriftsforståelse

| Stage | Content | Status |
|---|---|---|
| Foundation | **None. No Foundation recipe module.** Prerequisites only (Råvarer and Måling Foundation) | — |
| Kompetent | **Entire module** (recipe contract §27): recipe as a plan; OG → fermentability → attenuation → FG; colour is not flavour; IBU as one axis; balance against intent; style as a frame; one deliberate change. CHUNK-REC-A…G, Q-REC-001…007; FACT-RECIPE-0001…0003 plus reused ingredient facts | CONTRACTED; blocked by Måling Foundation |
| Bryggemester | Utilisation/Tinseth, colour-unit conversion, efficiency maths, apparent vs real attenuation detail, yeast biochemistry, structured experimentation beyond one change (D83) | OUT OF APP |
| Bryggeri | Statistical experiment design (D83) | OUT OF APP |

### C.11 Smak og evaluering

| Stage | Content | Status |
|---|---|---|
| Foundation | **No Foundation teaching and not part of Foundation completion.** The observation-vs-interpretation checkpoint is taught in Måling Foundation. CHUNK-SENS-A (simple tasting order) **may** be offered as an **optional Foundation taster** (§D.5) | Taster: not presented today |
| Kompetent | **The module is Kompetent.** Methodology: tasting sequence, describe ≠ diagnose, fault vs character, evaluate against intent + one change (CHUNK-SENS-A, B, F, G; Q-SENS-001…006). Beginner fault set: diacetyl (with acetaldehyde/sulphur as observation only), DMS + oxidation, light-struck (SHOULD) + intended sourness vs spoilage (sensory §27 chunks 3–5; FACT-SENSORY-0001…0003, FACT-BOIL-0002, FACT-OXY-0002) | Methodology IMPLEMENTED (offline stack, #472); fault chunks CONTRACTED; light-struck record GAP |
| Bryggemester | Wider off-flavour catalogue, causes of acetaldehyde/sulphur, staling depth | OUT OF APP |
| Bryggeri | Formal sensory panels, scoresheets, thresholds, statistics, lab analysis (D79) | OUT OF APP |

## D. Locked content moves

Each move says **where content belongs**. It is not an edit instruction for this contract; see §J.

### D.1 Mesking

- **Foundation:** concept only (enzymes; starch → sugars and dextrins at a simple level).
- **Move up to Kompetent:** `CHUNK-MASH-B`, `CHUNK-MASH-C`, `Q-MASH-002`, `Q-MASH-003`.
- Kompetent also owns grain separation and wort collection **once sourced** (§I).

### D.2 Koking/humle

- **Foundation:** why we boil; early vs late timing; bitterness vs aroma; boil-over safety. A simple Foundation-level
  statement may remain where the process needs it.
- **Move depth up to Kompetent:** the DMS mechanism/detail and hot-break depth in `CHUNK-BOILHOP-B`; `CHUNK-BOILHOP-F`
  (whirlpool / hop-stand technique); `Q-BOILHOP-002` (DMS volatile removal) and `Q-BOILHOP-007` (whirlpool technique).
- **Review at implementation (not locked as moves):** `Q-BOILHOP-004` and `Q-BOILHOP-005` test Foundation concepts at
  intermediate difficulty, and `Q-BOILHOP-008` tests hot break at beginner level. Each stays with its concept's stage; only
  its depth may be simplified.

### D.3 Kjøling/overføring

- **Foundation:** cool quickly; cold-side boundary; transfer basics; the oxygen timing **rule** (§C.6).
- **Move up to Kompetent:** the mechanism and depth in `CHUNK-COOLXFER-D` (sterols, unsaturated fatty acids, dry-yeast
  reserves) and its intermediate questions `Q-COOLXFER-004` and `Q-COOLXFER-005`.
- Foundation needs the rule stated simply. Whether that needs a beginner-level question is an implementation decision.

### D.4 Råvarer depth (resolves the audit's #418 conflict with option (a))

- **Keep at Foundation:** every #418 Foundation MUST concept, in simple form.
- **Move question depth up to Kompetent:** `Q-RAW-004` (grist %), `Q-RAW-006` (alpha ≠ IBU), `Q-RAW-009` (attenuation),
  `Q-RAW-010` (ale/lager vs strain), `Q-RAW-011` (yeast choice), `Q-RAW-012` (pitch principle).
- Kompetent and Oppskriftsforståelse may reuse the deeper reasoning under the existing concept ids (recipe contract §27.4).
  No duplicate mastery concept is created.
- `Q-RAW-014` (chlorine/chloramine, source awareness) is not moved: water source awareness is a Foundation MUST.

### D.5 Smak og evaluering

- **The module is Kompetent** and is no longer presented, conceptually, as mandatory Foundation work.
- `CHUNK-SENS-A` (simple tasting order) **may** be exposed as an **optional Foundation taster**. It is **not** part of
  Foundation completion.
- Fault vocabulary and causes stay Kompetent or above.

### D.6 Quantitative priming (resolves the curriculum-map D29 vs §9 conflict)

- **Kompetent:** understand that the priming amount controls carbonation; follow a trusted recipe, calculator or table.
- **Bryggemester:** quantitative calculation, carbonation maths and pressure depth.
- **No manual calculation is required for Kompetent completion.**

### D.7 Måling Foundation

Already locked in the measurement contract (§1, §21.2) and **preserved exactly**: OG/FG as measurements; finished
fermentation = repeated stable readings; temperature + where/how measured; volume into the fermenter; observation vs
interpretation; plan vs actual; minimum useful brew log. No formulas, no manual maths.

### D.8 Oppskriftsforståelse

The **entire module stays Kompetent**. There is **no Foundation recipe module**.

### D.9 Foundation fermentation gap

Foundation must eventually include:

1. what happens after pitching, at a simple level;
2. knowing fermentation is active **without treating airlock activity as proof**;
3. **finished fermentation = repeated stable gravity readings**;
4. semantic links from Gjæring and Pakking to Måling.

No unsupported detail is added now. Fact/source status is in §I.

## E. Foundation exit checkpoint

> **"I can brew, ferment and package one batch safely and explain what each stage does."**

Foundation is a **checkpoint, not course completion**. At it, the learner can, in their own words and without numbers to
memorise:

1. clean, then sanitise, and handle the basic safety points (chemicals, boil-over, fermentation CO₂, pressure);
2. explain the four raw-material roles (malt, hops, yeast, water);
3. describe their own brew-day sequence for their method;
4. explain the basics of mashing, boiling, cooling and fermentation temperature;
5. use hop timing at concept level (early for bitterness, late for aroma);
6. know that fermentation completion requires repeated stable readings;
7. package safely;
8. keep the minimum brew log.

Today items 6 and 8 are not yet taught: Måling Foundation is not implemented, and the Gjæring Foundation gap (§D.9) is open.

## F. Kompetent completion criteria

**Course completion = kompetent hjemmebrygger.** This is a Kvernhaug course stage, not a certification, licence or
professional qualification.

The learner can:

1. understand and adjust a recipe as a plan;
2. measure and record properly;
3. control their own brewing method at practical, qualitative depth;
4. understand fermentation and conditioning;
5. taste systematically;
6. compare planned with actual;
7. make one evidence-based, deliberate change for the next brew.

## G. Bryggemester entry boundary

Content becomes optional Bryggemester depth (outside the main App) when it needs any of:

- **maths or formulas:** correction formulas, utilisation/Tinseth, colour-unit conversion, efficiency/yield maths,
  quantitative priming and carbonation, pitch-rate arithmetic;
- **instruments beyond the homebrew basics:** pH meters, pressure gauges and regulators as a topic of their own;
- **advanced techniques:** step/decoction mashing, cereal cooking, starters, harvesting/repitching, pressure fermentation,
  kegging pressure systems, special beers (high gravity, low/no alcohol), home malting;
- **deeper chemistry:** water ions and residual alkalinity, yeast biochemistry, by-product causes beyond the sourced
  diacetyl example, hop-oil chemistry, Maillard detail;
- **structured experimentation** beyond one deliberate change.

Bryggemester is never shown as unfinished mandatory work (curriculum map §17).

## H. Bryggeri exclusion boundary

Bryggeri / profesjonell is **industrial operation**, kept separate from both the homebrew course and Bryggemester:

- CIP systems and industrial cleaning design;
- production plant design and process engineering;
- commercial packaging lines (washing, filling, cans, PET, kegs at scale);
- formal QC and laboratory analysis;
- yeast propagation plants;
- inline process instrumentation;
- formal sensory panels and statistics;
- utilities, energy, environment/waste and industrial automation.

Kunze chapters 5, 9, 10 and 11 and most of 4.4–4.6 are mapped to this track (curriculum map §10). Coverage in Kunze is not
a reason to teach a topic in the homebrew course.

## I. Known gaps and source blockers

| Gap | Stage | State |
|---|---|---|
| Måling og bryggelogg Foundation module | F | CONTRACTED, facts verified (FACT-MEAS-0001…0003); not implemented |
| Fermentation after pitching (simple) | F | GAP. FACT-YEAST-0001 supports "yeast consumes sugar and makes alcohol and CO₂". **No record for signs of active fermentation or phases** |
| Airlock not proof; finished = stable readings | F | Sourced by FACT-MEAS-0002; taught in Måling F once implemented; Gjæring/Pakking links not yet present |
| Any safety consequence of packaging too early | F | GAP. FACT-PACK-0003 covers damaged or unrated containers only; no record for early packaging |
| Spoilage vs safety; electrical near liquids; scald first aid | F | GAP (cleaning contract §3/§6) |
| Priming concept (amount controls carbonation; use a trusted tool) | K | GAP: no contract; FACT-PACK-0001 covers priming as a process only |
| Instrument checks | K | GAP (measurement M7 / G4) |
| Conversion check | K | `FACT-MASH-0003` **draft**; needs a second source |
| Grain separation / wort collection | K | MAPPED; Kunze SOURCE GAP printed pp. 257, 259–260 (curriculum map §19.1) |
| Light-struck | K (SHOULD) | No record of its own; S-3 not landed; FACT-SENSORY-0002 names the descriptor only |
| Adjuncts, mash pH concept, colour/flavour formation depth | K | MAPPED; no facts |
| Gjæring Kompetent expansion, Pakking extension | K | MAPPED (roadmap slices 7 and 11), no contracts |
| Stage presentation in the UI | F/K | GAP: no mechanism exists (§J) |

## J. Implementation implications

1. **Nothing moves by this contract.** Lesson JSON, questions, registry and UI are unchanged. Each move in §D is executed
   only by a later, separately scoped implementation slice with its own tests and owner QA.
2. **No stage field exists today.** Pilot JSON has no stage attribute, and question `difficulty` is **item difficulty, not
   the course stage** (recipe contract §27.2). How stages are expressed (a data field, module grouping, presentation in the
   grid) is a later product/UI decision. It must not reuse the App environment chooser (curriculum map §6.2.4).
3. **Mastery stays concept-based.** Moving a chunk or question between stages does not create or rename a mastery concept.
   Reuse follows the existing precedent (`cool.sanitation_boundary`, `sensory.observation_vs_interpretation`).
4. **Smak placement.** Presenting Smak og evaluering as Kompetent is a presentation change for the stage-presentation slice.
   The current visible card is not removed by this contract.
5. **Order of work** (unchanged dependencies):
   - Måling Foundation → Oppskriftsforståelse;
   - Gjæring Foundation basics after or with Måling Foundation, because they share the completion criterion;
   - the moves in §D.1–§D.4 together with the stage-presentation slice, so content is never hidden without a home.
6. **Grid order** stays as in curriculum map §6.2.8. This contract changes no position.

## K. Sync note and boundary statement

**Sync note.** Recorded locally on branch `offline/course-stage-allocation-contract` while GitHub was unavailable. When
access returns, mirror it on #419 and the #343 roadmap (with the module-specific parts on #418, #434, #436 and the sensory
issue) before treating it as synchronized.

**Boundary.** Docs only. This contract adds one document and pointer lines. It changes no lesson/pilot JSON, Course Fact
Registry record, UI, Web, requirements or test behaviour, does not touch #471, and promotes no Kunze statement to
verified truth.
