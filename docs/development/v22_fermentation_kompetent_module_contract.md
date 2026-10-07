# V2.2 — Gjæring Kompetent module contract

Status:
- Readiness contract (2026-10-05, offline), recorded on `offline/fermentation-kompetent-contract`.
- Built from the full-integration rehearsal at `bca2601`, which includes the merged Måling Kompetent.
- Docs only: no product code, registry or lesson JSON is changed.
- Not on GitHub/master.

**Status refresh 2026-10-05 (§12): IMPLEMENTATION READY.**
- G1 = FACT-BREW-0004 and G2 = FACT-BREW-0005 are verified after the Chief live source spot-check PASS.
- The shape below is locked.
- The §9 verdict that follows is kept for the record and is superseded.
- Status refresh 2026-10-05: **implemented locally/offline** on `offline/fermentation-kompetent-implementation` (CHUNK-FERM-E…K, Q-FERM-004…011), pending Chief
  review. It is not yet merged into the integration rehearsal and not on GitHub/master.
  - Foundation remains complete and unchanged.
  - Måling Kompetent and the Smak MUST content remain complete.
  - Light-struck remains a deferred SHOULD item (S-3 / #471).

**Verdict (superseded 2026-10-05 by §12): NOT IMPLEMENTATION READY** (§9). Two Kompetent MUST topics have no verified fact:
- fermentation phases (curriculum map D26);
- conditioning/maturation in general (D27).

The smallest unblocking fact round is two records (§10). Everything else in the slice is READY or METHODOLOGY and is shape-locked
here (§6–§7), so implementation can start as soon as those two records are verified.

## 1. Authority and inputs read

- Course stage allocation contract §C.7 (Gjæring), §F (Kompetent criteria), §G (Bryggemester boundary), §I (gaps).
- Curriculum map (#419 material), `v22_g3q_full_bryggeskole_curriculum_map.md`:
  - rows D26, D27, D45, D47, D48, D61 (the Gjæring Kompetent scope) and D49, D50, D67 (Bryggemester);
  - line 298 lists D27 conditioning, D45 pitching, D48 completion and D61 metabolism as items that "block Level 2";
  - the source plan (fermentation management: "Yeast producer + Tier B").
- Current Gjæring pilot:
  - `bryggeskole/pilot_fermentation.py` and `bryggeskole/data/pilot_fermentation_temperature.json`;
  - CHUNK-FERM-A…D and Q-FERM-001…003.
- Råvarer yeast content: CHUNK-RAW-G…I and Q-RAW-008…012 (FACT-YEAST-0001…0005).
- Måling (CHUNK-MEAS-A…J, FACT-MEAS-0001…0006); measurement contract §21–§24.
- Smak og evaluering (CHUNK-SENS-C, FACT-SENSORY-0001/0002); sensory contract §10, §27, §30–§31.
- Pakking (CHUNK-PACK-B…E, FACT-PACK-0001…0004) and the `kondisjonering` terminology fix.
- Kjøling/overføring oxygen rule (FACT-OXY-0001…0003).
- The Learn→Plan bridge contract `v22_g3j_fermentation_learn_plan_contract.md`:
  - `ui/yeast_panel.py` shows exactly CHUNK-FERM-A/B/C (`_LAER_BRO_CHUNK_IDER`);
  - the optional `fermentation_temp_target_c` plan field.
- The Course Fact Registry: 59 records, all verified except the draft FACT-MASH-0003.

## 2. Foundation (locked, not disturbed)

| Item | Content | Basis |
|---|---|---|
| CHUNK-FERM-A | Temperature → yeast activity and speed | FACT-BREW-0001 |
| CHUNK-FERM-B | Temperature → flavour, strain-dependent | FACT-BREW-0002 |
| CHUNK-FERM-C | Strain-specific guidance, no universal ale/lager rule | FACT-BREW-0003 |
| CHUNK-FERM-D | After pitching: fermentable sugar → alcohol + CO₂; gravity generally falls; airlock not reliable; finished = repeated stable readings; Måling cross-link | FACT-YEAST-0001, FACT-MEAS-0001, FACT-MEAS-0002 |
| Q-FERM-001…003 | Temperature/activity, strain-dependence, completion | as above |

Rules for Foundation:
- Kompetent is appended after Foundation in the **same module and card**: `gjaring`, grid position 7, still 11 cards.
- CHUNK-FERM-A…D and Q-FERM-001…003 must stay byte-identical.
- The Learn→Plan bridge keeps showing exactly CHUNK-FERM-A/B/C.
- Kompetent adds no bridge content, no plan field and no App mapping.

## 3. Topic classification

Key:
- READY = a verified record supports the wording.
- METHODOLOGY = a safe, non-factual teaching pattern.
- FACT GAP = no verified record.

| # | Topic (stage model) | Class | Support | Narrowing / reason |
|---|---|---|---|---|
| A | Fermentation phases (D26) | **FACT GAP** | Only "gravity generally falls" (MEAS-0001), "stable readings = plausibly finished" (MEAS-0002) and "warmer → faster" (BREW-0001) | Foundation CHUNK-FERM-D already teaches all of this. No record names or describes any phase, its order or what happens in it. Chief decision 2026-10-04 (§D.9) deferred phases as optional at Foundation; at Kompetent, D26 "L2 management" is MUST |
| B | Conditioning/maturation, "why wait" (D27) | **PARTIAL → FACT GAP for the general concept** | SENSORY-0001: diacetyl uptake depends on the beer staying in contact with enough yeast during fermentation **and maturation**. PACK-0001: bottle conditioning is a renewed small fermentation. PACK-0004: "given appropriate time" | The diacetyl clause is the **only** verified maturation claim (sensory contract §30). Nothing verified says what conditioning/maturation is in general, that beer clears as yeast settles, that flavour "rounds", or that cold conditioning or lagering is used. D27 is MUST and listed as blocking Level 2 |
| C | Pitching / viability (D45) | **READY, narrowed** | YEAST-0004: enough healthy yeast, producer guidance, no universal cell count. OXY-0001/0003: oxygen need is conditional, with the fresh dry-yeast exception. BREW-0003: strain-specific temperature | D45's own wording ("enough healthy yeast; follow producer guidance") is exactly YEAST-0004. **"Viability" as a defined term is narrowed out**: no record defines it or links it to age or storage. Kompetent says "healthy yeast" only. Viability checks stay Bryggemester (§C.7) |
| D | Yeast metabolism concept (D61) | **READY** | YEAST-0001 (sugar → alcohol + CO₂ + flavour/aroma compounds); MASH-0001 (dextrins ordinary brewing yeast does not ferment); YEAST-0002 (attenuation depends on yeast + wort + fermentation conditions); OXY-0001 (early oxygen supports membrane growth, conditionally) | Concept level only. No pathways, glycolysis, sugar spectrum, mass balance or "every sugar is fermentable by every strain" |
| E | By-products beyond diacetyl (D47) | **READY only as the stage contract already limits it**; beyond that FACT GAP (non-blocking) | READY: diacetyl (SENSORY-0001) and "yeast-derived flavour/aroma depends on strain and temperature" (YEAST-0001, BREW-0002) | Esters, higher/fusel alcohols, acetaldehyde production or clean-up, sulphur/H₂S formation, and any temperature → by-product mapping: **FACT GAP**. They are Bryggemester "by-product causes beyond the sourced diacetyl example" (stage contract §G), so they do **not** block Kompetent. Acetaldehyde and sulphur stay Smak vocabulary/observation only (FACT-SENSORY-0002) |
| F | Completion in more depth (D48) | **READY** | MEAS-0002, MEAS-0001; YEAST-0002 (how far gravity falls depends on yeast and conditions, so FG is a measurement, not a fixed number); MASH-0001 (some wort content is not fermented); MEAS-0004 (after alcohol: hydrometer, or a correction that also uses the original reading) | No FG numbers, attenuation percentages or ABV. "Stable gravity" answers *has fermentation finished*; it does not answer *is the beer ready to drink* (methodology, row G). No claim that diacetyl remains after stable gravity |
| G | Practical process reasoning (no Bryggemester maths) | **METHODOLOGY** | Pattern from Måling J and Smak (G3N): plan vs actual, observation ≠ interpretation, one hypothesis, one deliberate change | Record yeast product, pitching per producer guidance, fermentation temperature with where/how measured, and dated gravity readings. Keep "measured" separate from "tasted". Never diagnose a fermentation from one smell. A hypothesis is not proof |

## 4. Learning outcomes (Kompetent)

The learner can:

1. **(D61, READY)** Explain at concept level that yeast ferments the fermentable sugars and makes alcohol, CO₂ and flavour/aroma compounds:
   - part of the wort (dextrins) is not fermented by ordinary brewing yeast;
   - how far fermentation goes depends on the yeast and on wort and fermentation conditions.
2. **(D45, READY narrowed)** Plan pitching as "enough healthy yeast, following the producer's guidance for that yeast":
   - no universal cell count;
   - oxygen before or at pitching is conditional (fresh dry yeast is a common exception), and unnecessary oxygen after fermentation
     starts is avoided (cross-link to Kjøling, not restated).
3. **(D26, FACT GAP — G1)** Describe the course of a fermentation over time in qualitative phases, with no durations.
4. **(D48, READY)** Judge completion from repeated stable readings rather than one reading, the airlock or a planned FG:
   - FG differs with yeast and conditions;
   - after alcohol, use a hydrometer or a corrected refractometer reading (cross-link to Måling, not restated).
5. **(D47, READY narrowed)** Explain diacetyl as the sourced example of a fermentation by-product that healthy yeast can take back up
   with enough yeast contact:
   - yeast-derived flavour depends on strain and temperature;
   - a buttery smell is not proof of diacetyl (cross-link to Smak).
6. **(D27, FACT GAP — G2; diacetyl part READY)** Explain why beer is given time after the main fermentation, and that there is no
   universal duration.
7. **(METHODOLOGY)** Keep a fermentation log, make plan-vs-actual notes, form one hypothesis and make one deliberate change, without
   maths and without treating a hypothesis or a single sense as proof.

## 5. Concept IDs

| Concept | New / reused | Basis | Owner |
|---|---|---|---|
| `fermentation.yeast_metabolism` | new | fact | Gjæring |
| `yeast.pitch_principle` | reused (shared mastery, as `sensory.observation_vs_interpretation`) | fact | Råvarer |
| `fermentation.phases` | new | fact (**G1**) | Gjæring |
| `measurement.fermentation_complete` | reused (already shared by Q-FERM-003) | fact | Måling |
| `yeast.attenuation` | reused | fact | Råvarer |
| `fermentation.byproducts` | new | fact | Gjæring |
| `fermentation.conditioning` | new | fact (**G2** + SENSORY-0001) | Gjæring |
| `fermentation.process_reasoning` | new | methodology (Gjæring `METHODOLOGY_CONCEPTS`) | Gjæring |

The panel needs NO/EN labels for the five new concepts.

## 6. Proposed chunks

Chunks are appended after CHUNK-FERM-D.

| Chunk | Basis | Content | source_claims | Class |
|---|---|---|---|---|
| CHUNK-FERM-E | fact | What yeast does with the wort: fermentable sugar → alcohol + CO₂ + flavour/aroma; dextrins not fermented by ordinary yeast; attenuation depends on yeast + conditions | FACT-YEAST-0001, FACT-MASH-0001, FACT-YEAST-0002 | READY |
| CHUNK-FERM-F | fact | Pitching with healthy yeast: producer guidance, no universal count; conditional oxygen and the dry-yeast exception; strain-specific temperature | FACT-YEAST-0004, FACT-OXY-0001, FACT-OXY-0003, FACT-BREW-0003 | READY |
| CHUNK-FERM-G | fact | Fermentation over time: qualitative phases, no durations | **G1** (+ FACT-MEAS-0001) | FACT GAP |
| CHUNK-FERM-H | fact | Completion in depth: repeated stable readings; FG is a measurement, not a target; hydrometer after alcohol | FACT-MEAS-0002, FACT-MEAS-0001, FACT-YEAST-0002, FACT-MEAS-0004 | READY |
| CHUNK-FERM-I | fact | By-products: diacetyl as the sourced example; strain/temperature flavour; butter smell ≠ proof | FACT-SENSORY-0001, FACT-BREW-0002, FACT-YEAST-0001 | READY |
| CHUNK-FERM-J | fact | Conditioning/maturation, "why wait": general concept + diacetyl yeast contact; no universal duration | **G2**, FACT-SENSORY-0001 | FACT GAP (diacetyl part READY) |
| CHUNK-FERM-K | methodology | Fermentation log and process reasoning; measured ≠ tasted; one hypothesis, one change | none | METHODOLOGY |

## 7. Proposed questions

All are `intermediate`, with three options and one correct answer.

| Question | Type | Basis | Concept | source_claims | Class |
|---|---|---|---|---|---|
| Q-FERM-004 | concept_check | fact | `fermentation.yeast_metabolism` | FACT-YEAST-0001, FACT-MASH-0001 | READY |
| Q-FERM-005 | scenario | fact | `yeast.pitch_principle` | FACT-YEAST-0004, FACT-OXY-0001 | READY |
| Q-FERM-006 | scenario | fact | `fermentation.phases` | **G1** | FACT GAP |
| Q-FERM-007 | scenario | fact | `measurement.fermentation_complete` | FACT-MEAS-0002, FACT-MEAS-0001 | READY |
| Q-FERM-008 | scenario | fact | `yeast.attenuation` | FACT-YEAST-0002 | READY |
| Q-FERM-009 | scenario | fact | `fermentation.byproducts` | FACT-SENSORY-0001 | READY |
| Q-FERM-010 | scenario | fact | `fermentation.conditioning` | **G2**, FACT-SENSORY-0001 | FACT GAP |
| Q-FERM-011 | scenario | methodology | `fermentation.process_reasoning` | none | METHODOLOGY |

Notes:
- Q-FERM-007: the airlock has stopped and one reading looks "low enough". The correct answer is to repeat readings some time apart.
- Q-FERM-008: two yeasts give different FGs. The correct answer is that attenuation depends on the yeast and the conditions, so a
  different FG alone does not show a mistake.
- Q-FERM-009: the beer smells buttery. The correct answer is that this may be diacetyl and is linked to yeast contact through
  fermentation and maturation; the smell is not proof. Distractors include "it is certainly an infection".

Without G1/G2, the READY subset is:
- CHUNK-FERM-E, F, H, I, K;
- Q-FERM-004, 005, 007, 008, 009, 011.

## 8. Dependencies, wording boundaries and exclusions

**Dependencies** (cross-links as plain text; no gating, no stage UI):
- Råvarer yeast (FACT-YEAST-0001…0005) is the vocabulary base; Gjæring applies it and does not restate it.
- Måling owns measurement truth: completion (MEAS-0002), instruments (MEAS-0004/0006).
- Smak owns recognition (diacetyl descriptor, "descriptor ≠ diagnosis").
- Kjøling owns the oxygen timing rule.
- Pakking owns priming and bottle conditioning (PACK-0001); CHUNK-FERM-J links to it and does not restate the mechanism.

**Implementation prerequisite** (not a fact gap): `bryggeskole/pilot_fermentation.py` has no `basis` field, and it requires non-empty
`source_claims` on every chunk and question. The implementation must add the scoped basis rule from `pilot_sensory.py` /
`pilot_measurement.py`:
- a closed `METHODOLOGY_CONCEPTS = {fermentation.process_reasoning}`;
- for the Foundation items only, an absent `basis` is treated as `fact` and still needs non-empty `source_claims`. This keeps
  CHUNK-FERM-A…D byte-identical.
- `test_exactly_four_chunks` becomes a Foundation/Kompetent split.

**NO/EN wording traps** (binding; to be enforced by implementation tests):
- No numbers at all: temperatures, durations, cell counts, pitch rates, FG/attenuation values, ABV.
- No pathway or biochemistry words (glycolysis, pyruvate, enzymes inside the yeast) and no "every sugar is fermentable".
- No "viability" definition, percentage, age/storage rule or test.
- No universal "always aerate" or "oxygen is bad".
- No airlock, krausen or bubbles as evidence of phase or completion. Visible/audible signs need G1-level support.
- No esters, higher/fusel alcohols, acetaldehyde production or clean-up, sulphur/H₂S formation, or diacetyl rest temperature/time.
- No "acetaldehyde/sulphur means unfinished beer".
- No "more time always fixes it"; no infection diagnosis from taste; no "stable gravity means the beer is ready to drink".
- No hypothesis presented as proof. No auto-filled explanation and no App field mapping.
- NO uses `kondisjonering`, consistent with Pakking.

**Bryggemester content excluded:**
- starters;
- harvesting/repitching/propagation (D49);
- pressure fermentation (D50);
- pitch-rate or cell-count arithmetic;
- yeast biochemistry/glycolysis;
- high-gravity, ice and low/no-alcohol methods (D67);
- viability/vitality testing and counting;
- diacetyl-rest schedules;
- by-product causes beyond diacetyl;
- fermentation schedules/ramps;
- clarification/finings depth (D28).

## 9. Implementation-ready decision

**NOT IMPLEMENTATION READY.**
- Topics A (phases) and B (conditioning/maturation, general concept) are Kompetent MUST content without verified support.
- Building them from the existing records would invent facts.
- Topics C–G are READY or METHODOLOGY and are shape-locked above.
- Following the Measurement precedent (Chief §23.4: do not split; keep Kompetent closed until the gap closes), the slice is not
  split by default.

Alternative for the Chief (not recommended by this contract): approve the READY subset (§7) now as a narrowed Kompetent, with phases
and general conditioning deferred.

## 10. Smallest blocking fact pack (one bounded round)

| Id | Concept | Candidate claim (to be confirmed against sources, not verified) | Suggested class |
|---|---|---|---|
| G1 | `fermentation.phases` | After pitching, fermentation commonly runs through an initial period in which the yeast adapts and grows with little change in gravity, a period of active fermentation in which most fermentable sugar is consumed and gravity falls fastest, and a slower final period as fermentation finishes. How long each period lasts depends on the yeast, the wort and conditions such as temperature. | documented_fact |
| G2 | `fermentation.conditioning` | After the main fermentation, beer is commonly given further time (conditioning or maturation) before packaging or serving. During this time yeast can continue to reduce some fermentation by-products, and yeast and other particles can settle so the beer becomes clearer. The time needed depends on the beer, the yeast and the conditions; there is no single universal duration. | documented_fact or professional_interpretation |

Source rules for the round:
- Each record needs at least two independent sources, read in full. Prefer a yeast producer (Tier A) plus Tier B, per the curriculum
  map source plan.
- Kunze §4.1 and §4.3.5 (printed pp. 367–386 and 409–411) are structural Tier B leads only.
- No source has been opened for G1/G2 in this task; no source content is claimed here.

Wording traps for both records:
- G1: no durations; no visible or audible sign as proof.
- G2: must not restate SENSORY-0001's diacetyl mechanism (ownership stays there); no duration; no cold-conditioning/lagering
  temperature.

Stop rule: if a clause is not supported, it is dropped and the record narrowed, not filled in.

Not in the pack, because it is narrowed out and non-blocking:
- viability definition;
- by-products beyond diacetyl;
- visible/audible fermentation signs.

## 12. G1/G2 closure and shape lock (2026-10-05, offline)

**G1 and G2 are verified.** The Chief live source spot-check of
`v22_fermentation_g1_g2_source_pack.md` passed on 2026-10-05.
- Both records use the bounded source-pack claims, with BREW numbering (no `FACT-FERM-*`).
- Both are `documented_fact`, with `verified_at` 2026-10-05T09:10:01+02:00 (the local receipt of the PASS; provenance is in the notes).
- Both were added on `offline/fermentation-kompetent-implementation`.

| Record | Concept | Bounded content |
|---|---|---|
| FACT-BREW-0004 | `fermentation.phases` | Fermentation does not run at one steady rate:<br>- an early period while the yeast adapts;<br>- a main, more active period where most fermentable sugar is consumed;<br>- a later, slower period.<br>The stages overlap; sources name and divide them differently; length and vigour depend on yeast, wort and conditions. |
| FACT-BREW-0005 | `fermentation.conditioning` | Beer is commonly given further time after the most active fermentation (maturation/conditioning, overlapping the end of fermentation):<br>- active yeast can reduce **some** earlier by-products;<br>- yeast and suspended material tend to settle, so the beer often becomes clearer — strain-dependent, and some beers are meant to stay hazy;<br>- there is no universal duration. |

**Chief refinement (binding):**
- The sentence "not everything can be fixed by waiting" / "ikke alt kan rettes opp ved å vente" is dropped entirely, from the claim
  and from all learner wording.
- G2 names no by-product: no acetaldehyde, no sulphur.
- Diacetyl stays governed by FACT-SENSORY-0001 and is used only in CHUNK-FERM-I/J within that record's scope.

**Gjæring Kompetent is IMPLEMENTATION READY.** The §6 and §7 shape is locked as approved:
- G1/G2 rows are filled with the new records;
- the Chief decision "do not split" is honoured.

| Chunk | Basis | source_claims |
|---|---|---|
| CHUNK-FERM-E | fact | FACT-YEAST-0001, FACT-MASH-0001, FACT-YEAST-0002 |
| CHUNK-FERM-F | fact | FACT-YEAST-0004, FACT-OXY-0001, FACT-OXY-0003, FACT-BREW-0003 |
| CHUNK-FERM-G | fact | FACT-BREW-0004, FACT-MEAS-0001 |
| CHUNK-FERM-H | fact | FACT-MEAS-0002, FACT-MEAS-0001, FACT-YEAST-0002, FACT-MEAS-0004 |
| CHUNK-FERM-I | fact | FACT-SENSORY-0001, FACT-BREW-0002, FACT-YEAST-0001 |
| CHUNK-FERM-J | fact | FACT-BREW-0005, FACT-SENSORY-0001 |
| CHUNK-FERM-K | methodology | none |

| Question | Type | Basis | Concept | source_claims |
|---|---|---|---|---|
| Q-FERM-004 | concept_check | fact | `fermentation.yeast_metabolism` | FACT-YEAST-0001, FACT-MASH-0001 |
| Q-FERM-005 | scenario | fact | `yeast.pitch_principle` | FACT-YEAST-0004, FACT-OXY-0001 |
| Q-FERM-006 | scenario | fact | `fermentation.phases` | FACT-BREW-0004 |
| Q-FERM-007 | scenario | fact | `measurement.fermentation_complete` | FACT-MEAS-0002, FACT-MEAS-0001 |
| Q-FERM-008 | scenario | fact | `yeast.attenuation` | FACT-YEAST-0002 |
| Q-FERM-009 | scenario | fact | `fermentation.byproducts` | FACT-SENSORY-0001 |
| Q-FERM-010 | scenario | fact | `fermentation.conditioning` | FACT-BREW-0005, FACT-SENSORY-0001 |
| Q-FERM-011 | scenario | methodology | `fermentation.process_reasoning` | none |

All Kompetent questions are `intermediate`, with three options and one correct answer. The Foundation questions keep their existing
difficulty.

Implementation notes (no shape change):
- **Terminology.** §8 says "NO uses `kondisjonering`". The FACT-BREW-0005 notes ask for "modning" as the main Norwegian word, so it
  does not collide with Pakking's "flaskekondisjonering". The two are reconciled, not contradictory: the NO text says "modning", with
  "kondisjonering" as the gloss the sources and Pakking use.
- **Methodology.** The closed `METHODOLOGY_CONCEPTS` in `bryggeskole/pilot_fermentation.py` is exactly `{fermentation.process_reasoning}`.
- **Absent basis.** An absent `basis` means `fact` and still requires verified, non-empty `source_claims`. CHUNK-FERM-A…D and
  Q-FERM-001…003 stay byte-identical.
- **Mastery.** No new concept beyond the five approved in §5.
- **Out of scope.** No App field, no Learn→Plan bridge change (still CHUNK-FERM-A/B/C), no stage UI.

## 11. Explicitly not done in this document

Not done here:
- no Gjæring Kompetent implementation;
- no change to Foundation, Measurement, Recipe or Sensory;
- no registry, lesson JSON or product code change;
- no stage UI, Web, #471 or issue-477 change;
- no GitHub contact.

Sync note: when GitHub access returns, mirror this on #419 / the #343 roadmap before treating it as synchronized. No new issue number
is assigned here.

v1.0 (2026-10-05, offline): readiness contract; verdict NOT IMPLEMENTATION READY; fact pack G1 + G2.

v1.1 (2026-10-05, offline G1/G2 closure): adds §12 (FACT-BREW-0004/0005 verified after the Chief live source spot-check; IMPLEMENTATION READY; shape locked as CHUNK-FERM-E…K and Q-FERM-004…011) and a status pointer. Not on GitHub/master.
