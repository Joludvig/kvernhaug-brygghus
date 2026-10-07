# V2.2 — Mesking Kompetent module contract (grain separation + wort collection)

Status:
- Readiness contract (2026-10-05, offline), recorded on `offline/mesking-kompetent-contract`.
- Built from the full-integration rehearsal `a736bd0`, which includes stage contract §F.1/§F.2.
- Docs only: no product code, registry or lesson JSON is changed.
- Not on GitHub/master.

**Verdict: NOT IMPLEMENTATION READY** (§8). The method-aware *layout* of grain separation is already verified and taught
(FACT-METHOD-0001…0005, Forberedelse/metode CHUNK-METHOD-B…E). What is missing is the Kompetent *practice* behind it, for
which no verified record exists:
- the grain bed as a filter, and recirculating cloudy first runnings;
- wort held back in the grain, sparging versus full-volume mashing, and later runnings being weaker.

The smallest unblocking fact round is two records (§9). The rest of the slice is READY or METHODOLOGY and is shape-locked here.

## 1. Authority and scope

- Stage allocation contract:
  - §C.3 and §C.4;
  - §D.1 (Kompetent owns grain separation and wort collection "once sourced");
  - §F.1 (completion rule);
  - §F.2 (Chief rulings 2026-10-05):
    - **D18 method-aware grain separation = MUST**;
    - **D19 wort collection travels with D18 in this slice** (not a separate MUST);
    - D16 milling, the conversion check (FACT-MASH-0003), D51 mash pH and D66 efficiency are SHOULD, non-blocking.
- Curriculum map:
  - D18 "MUST (L2, method-aware)" and D19 "SHOULD (L2)";
  - §19.1 SOURCE GAP: Kunze printed pp. 257, 259–260 (§3.3.2 *Last runnings*, start of §3.3.3), so D18/D19 teaching must
    use other sources.
- Existing verified support:
  - FACT-METHOD-0001 (BIAB: separation by lifting the bag, draining, sometimes a dunk);
  - FACT-METHOD-0002 (traditional: a grain bed over a false bottom/manifold, drained to the kettle, typically sparged to
    recover further sugar);
  - FACT-METHOD-0003 (all-in-one: basket/malt pipe holds the grain bed; separation in the same vessel; often recirculation);
  - FACT-METHOD-0004 (volumes, dead space, absorption/retention differ by equipment; plan for your own);
  - FACT-METHOD-0005 (no method hierarchy);
  - FACT-MEAS-0001 (gravity; OG);
  - FACT-MEAS-0005 (hot vs cooled volume; losses).

**Required in this slice:** method-aware grain separation and wort collection.

**Not in this slice** (non-blocking, not smuggled in):
- milling/crush (D16);
- conversion check / iodine (FACT-MASH-0003, draft);
- mash pH (D51);
- efficiency concept or maths (D66);
- step/decoction mashing;
- lauter-tun engineering;
- set/stuck-mash troubleshooting depth;
- run-off rates;
- sparge water temperature or pH;
- bag-squeezing claims.

## 2. Foundation and existing Kompetent content (not disturbed)

- Mesking:
  - CHUNK-MASH-A (Foundation concept);
  - CHUNK-MASH-B/C and Q-MASH-002/003 (Kompetent by stage, §D.1; the presentation move is not part of this slice).
  - All unchanged.
- Forberedelse/metode CHUNK-METHOD-A…E and their questions are unchanged. This slice applies them and does not restate the
  layouts.
- The Kompetent items are appended after CHUNK-MASH-C / Q-MASH-003 in the **same Mesking module and card** (still 11 cards).

## 3. Learning outcomes (Kompetent)

The learner can:
1. explain, for their own method (BIAB, traditional mash/lauter, all-in-one), how wort is separated from the grain, and what
   the grain bed does where there is one. No method is "proper" or better (FACT-METHOD-0005);
2. explain why sugar-rich wort stays in the wet grain, and the two common ways of handling it: rinsing (sparging) or using
   more of the water in the mash. Also that later runnings are weaker;
3. collect the wort and record the pre-boil volume (noting hot or cooled) and gravity, then compare them with the plan and
   their own equipment's numbers. This is methodology; no efficiency maths.

## 4. Topic classification

| Topic | Class | Support | Narrowing |
|---|---|---|---|
| Separation layout per method | **READY** | FACT-METHOD-0001/0002/0003, 0005 | Applied, not restated; no hierarchy |
| Grain bed as a filter; recirculate the first cloudy runnings until clearer | **FACT GAP — M1** | METHOD-0002/0003 say "filter medium", "grain bed" and "recirculation (where present)", but not *why*, nor that the first runnings are recirculated until clearer | No run-off rate, no recirculation time, no clarity standard |
| Wort retained in the grain; sparge vs full-volume; later runnings weaker | **FACT GAP — M2** | METHOD-0002 says only that sparging recovers further sugar; METHOD-0004 says absorption/retention differs by equipment | No sparge temperature or pH, no efficiency numbers, no fly/batch sparge technique depth |
| Plan for your own equipment's absorption/dead space | **READY** | FACT-METHOD-0004 | No universal numbers |
| Pre-boil volume (hot vs cooled) and gravity | **READY** | FACT-MEAS-0005, FACT-MEAS-0001 | Measurement truth stays in Måling; no correction maths |
| Pre-boil check and log, one deliberate change | **METHODOLOGY** | Måling J / Smak pattern | No efficiency calculation; hypothesis ≠ proof |

## 5. Concept IDs

| Concept | New / reused | Basis |
|---|---|---|
| `mashing.grain_separation` | new | fact (**M1** + METHOD-0001…0003) |
| `mashing.wort_collection` | new | fact (**M2**) |
| `method.planning_variables` | reused (Forberedelse/metode; shared mastery) | fact (METHOD-0004) |
| `mashing.preboil_check` | new | methodology — the closed `METHODOLOGY_CONCEPTS` in `pilot_mashing.py` |

## 6. Proposed chunks (after CHUNK-MASH-C)

| Chunk | Basis | Content | source_claims |
|---|---|---|---|
| CHUNK-MASH-D | fact | Separating wort from grain, by method:<br>- bag lifted out (BIAB);<br>- drained through a grain bed (traditional);<br>- basket or malt pipe in the same vessel (all-in-one).<br>Where wort runs through a grain bed, the bed helps filter it, and the first cloudy runnings are recirculated until clearer. No method is better. | FACT-METHOD-0001, FACT-METHOD-0002, FACT-METHOD-0003, FACT-METHOD-0005, **M1** |
| CHUNK-MASH-E | fact | Collecting the wort:<br>- the wet grain holds sugar-rich wort;<br>- rinsing (sparging) recovers more, or more of the water goes into the mash;<br>- later runnings are weaker;<br>- the grain keeps back some liquid, so plan with your own equipment's numbers. | **M2**, FACT-METHOD-0004 |
| CHUNK-MASH-F | methodology | Pre-boil check:<br>- note the collected volume (hot or cooled, see Måling) and the gravity;<br>- compare with the plan;<br>- if they differ, write one hypothesis and choose one deliberate change.<br>No efficiency maths. | none |

## 7. Proposed questions

All are `intermediate`, with three options and one correct answer.

| Question | Type | Basis | Concept | source_claims |
|---|---|---|---|---|
| Q-MASH-004 | concept_check | fact | `mashing.grain_separation` | FACT-METHOD-0001, FACT-METHOD-0002, FACT-METHOD-0003 |
| Q-MASH-005 | scenario | fact | `mashing.grain_separation` | **M1** |
| Q-MASH-006 | scenario | fact | `mashing.wort_collection` | **M2** |
| Q-MASH-007 | scenario | fact | `method.planning_variables` | FACT-METHOD-0004 |
| Q-MASH-008 | scenario | methodology | `mashing.preboil_check` | none |

Question intents:
- Q-004: the same job is done by different hardware in each method; no method is "proper".
- Q-005: the first runnings are cloudy with grain bits; the correct answer is to recirculate until clearer.
- Q-006: after the first drain, the wet grain still holds sugar; the correct answer is to rinse/sparge, or to plan the water
  for a full-volume mash.
- Q-007: the volumes were copied from someone else's different system; the correct answer is to plan with your own
  equipment's absorption/dead space.
- Q-008: the pre-boil volume or gravity differs from the plan; the correct answer is to record it (hot or cooled), compare,
  form one hypothesis and make one change.

**Implementation prerequisite** (not a fact gap): `bryggeskole/pilot_mashing.py` has no `basis` field. Add the scoped rule
used in `pilot_fermentation.py`:
- an absent basis means fact;
- a closed `METHODOLOGY_CONCEPTS = {mashing.preboil_check}`;
- CHUNK-MASH-A…C and Q-MASH-001…003 stay byte-identical;
- `test_pilot_sensory._NO_METHODOLOGY_PILOTS` drops `pilot_mashing`.

**NO/EN wording traps** (binding):
- No numbers, temperatures, ratios, run-off rates or times. No efficiency or yield maths.
- No method hierarchy ("proper", "real", "advanced").
- No bag-squeezing claim either way.
- No stuck-sparge troubleshooting depth.
- No sparge-water pH or temperature.
- No milling/crush, iodine/conversion check or mash pH.
- No App field mapping. Measurement truth is a cross-link to Måling, not restated.

**Bryggemester / Bryggeri excluded:**
- lauter-tun design and engineering;
- fly-vs-batch sparge optimisation;
- efficiency calculation;
- last-runnings gravity cut-offs;
- mash filters;
- step/decoction mashing;
- pH measurement.

## 8. Implementation-ready decision

**NOT IMPLEMENTATION READY.**
- CHUNK-MASH-D and Q-MASH-005 need M1.
- CHUNK-MASH-E and Q-MASH-006 need M2.
- Everything else (Q-MASH-004, Q-MASH-007, CHUNK-MASH-F, Q-MASH-008) is READY or METHODOLOGY.
- The slice is not split (Measurement/Gjæring precedent).

## 9. Smallest blocking fact pack (one bounded round)

| Proposed id | Concept | Candidate claim (to be confirmed against sources; NOT verified) | Suggested class |
|---|---|---|---|
| FACT-MASH-0005 (M1) | `mashing.grain_separation` | After the mash, the wort is separated from the spent grain. Where wort is drained through a bed of grain (a lauter tun with a false bottom or manifold, or a basket or malt pipe), the grain bed itself helps filter the wort, and brewers commonly recirculate the first, cloudy runnings back over the bed until the wort runs clearer. In BIAB, the bag holds the grain and separation happens as the bag is lifted out. | documented_fact |
| FACT-MASH-0006 (M2) | `mashing.wort_collection` | After the first draining, the wet grain still holds sugar-rich wort. Rinsing the grain with more hot water (sparging) recovers more of it; some brewers instead put more of the total water into the mash and sparge little or not at all. Later runnings are weaker than the first, and the grain keeps back some liquid, so not all of the wort is recovered. | documented_fact |

Source requirements (same standard as M7 and G1/G2):
- At least two independent, brewing-relevant sources per record, read in full.
- At least one strong technical or producer source where available (for example, an all-in-one system maker's manual for
  recirculation through the malt pipe; commercial interest flagged).
- At least one independent brewing text, association or magazine.
- Kunze may support only pages outside the §19.1 gap.
- Snippets and AI summaries are not evidence.
- Unsupported clauses are dropped. Possible drops:
  - "later runnings are weaker";
  - "commonly recirculate until clearer";
  - the full-volume/no-sparge alternative.

Leads only (not opened in this task; no content is claimed):
- John Palmer, *How to Brew* (lautering/sparging chapters);
- Oxford Companion to Beer entries ("lautering", "vorlauf", "sparging", "first runnings");
- BYO/AHA lautering articles;
- all-in-one system manuals.

## 10. Explicitly not done

Not done in this document:
- no implementation;
- no registry, lesson JSON or product code change;
- no stage UI, Web, #471 or issue-477 change;
- no GitHub contact.

Sync note: mirror on #419 / the #343 roadmap when GitHub returns. No issue number is assigned.

v1.0 (2026-10-05, offline): readiness contract; NOT IMPLEMENTATION READY; fact pack M1 + M2.
