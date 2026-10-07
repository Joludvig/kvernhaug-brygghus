# V2.2 — Pakking Kompetent module contract (priming concept + short clarity / shelf-life reuse)

Status:
- Readiness contract (2026-10-05, offline), recorded on `offline/packing-kompetent-contract`.
- Built from the full-integration rehearsal `a736bd0`, which includes stage contract §F.1/§F.2.
- Docs only: no product code, registry or lesson JSON is changed.
- Not on GitHub/master.

**Verdict: IMPLEMENTATION READY** (§8). Every fact item rests on an already verified record (FACT-PACK-0001, FACT-BREW-0005,
FACT-OXY-0002). The trusted-tool guidance is labelled methodology. **No new fact is needed.**

**Status refresh 2026-10-05:**
- **Implemented locally/offline** on `offline/packing-kompetent-implementation` exactly as locked (CHUNK-PACK-F…I, Q-PACK-006…009, scoped basis rule in
  `pilot_package.py`), pending Chief review.
- Not merged into the integration rehearsal; not on GitHub/master.
- Foundation CHUNK-PACK-A…E / Q-PACK-001…005 are unchanged.
- Måling, Gjæring and Oppskriftsforståelse Kompetent and the Smak MUST content remain complete.
- Light-struck remains DEFERRED SHOULD.
- The remaining Kompetent MUST blocker is Mesking D18/D19 (fact pack M1/M2 awaiting the Chief spot-check).

## 1. Authority and scope

- Stage allocation contract:
  - §C.8;
  - §D.6 (locked: Kompetent understands that the priming amount controls carbonation and follows a trusted recipe,
    calculator or table; **no manual calculation is required**);
  - §F.1 (completion rule);
  - §F.2 (Chief rulings 2026-10-05):
    - the §D.6 priming concept is required;
    - D28/D58 get a **short reuse treatment** in this slice (settling/clearer beer from FACT-BREW-0005; the oxygen/shelf-life
      brief from FACT-OXY-0002);
    - finings, clarification techniques, cold-conditioning practice and shelf-life depth stay SHOULD, non-blocking.
- Package contract `v22_g3f_package_module_contract.md` (Foundation CHUNK-PACK-A…E, Q-PACK-001…005).
- Fact scope:
  - **FACT-PACK-0001**: priming sugar → renewed small fermentation in the sealed bottle → CO₂ dissolves; the amount needed
    depends on the beer (existing dissolved CO₂, temperature, style) and the carbonation wanted; no universal number.
  - **FACT-BREW-0005**: time after the most active fermentation; yeast and suspended material tend to settle; often clearer;
    strain-dependent; some beers are meant to stay hazy; no universal duration.
  - **FACT-OXY-0002**: once fermentation is underway, oxygen exposure is generally undesirable and can contribute to
    oxidative off-flavours (cardboard/stale), diminished hop aroma and reduced shelf stability. Minimise splashing and air
    contact during transfers. This is a direction, not a threshold, and one exposure does not inevitably ruin a batch.

## 2. Foundation (locked, not disturbed)

- CHUNK-PACK-A…E and Q-PACK-001…005 stay byte-identical.
- CHUNK-PACK-B already says the priming amount depends on the beer and the carbonation wanted, with no universal number.
  Kompetent adds the *how-to-decide* layer (§D.6) and does not restate the mechanism.
- CHUNK-PACK-D already says to minimise oxygen when packaging. Kompetent adds the *why* (shelf stability, hop aroma) within
  OXY-0002's scope.
- The Kompetent items are appended after CHUNK-PACK-E / Q-PACK-005 in the **same Pakking module and card** (still 11 cards).

## 3. Learning outcomes (Kompetent)

The learner can:
1. explain that the amount of priming sugar steers how carbonated the beer becomes, and that the right amount depends on the
   beer and the carbonation wanted (FACT-PACK-0001);
2. get the amount from a trusted recipe, priming calculator or carbonation table, give it the details it asks for, and record
   what they used. **No manual calculation** (§D.6; methodology);
3. explain that time lets yeast and other material settle so the beer often becomes clearer. This depends on the yeast, and
   some beers are meant to stay hazy (FACT-BREW-0005, reused);
4. explain why oxygen is avoided at packaging: it can contribute to stale/cardboard flavours, weaker hop aroma and reduced
   shelf stability (FACT-OXY-0002, reused).

## 4. Topic classification

| Topic | Class | Support |
|---|---|---|
| Priming amount steers carbonation; no universal amount | **READY** | FACT-PACK-0001 |
| Use a trusted recipe/calculator/table; record it; no manual maths | **METHODOLOGY** | §D.6 (locked decision) |
| Settling → often clearer; strain-dependent; some beers intentionally hazy | **READY (reuse)** | FACT-BREW-0005 |
| Oxygen after fermentation → stale flavours, weaker hop aroma, reduced shelf stability | **READY (reuse)** | FACT-OXY-0002 |

## 5. Concept IDs

| Concept | New / reused | Basis |
|---|---|---|
| `package.priming` | reused (Foundation Q-PACK-002) | fact (PACK-0001) |
| `package.priming_tool` | new | methodology (the closed `METHODOLOGY_CONCEPTS` in `pilot_package.py`) |
| `fermentation.conditioning` | reused (Gjæring; shared mastery, same fact) | fact (BREW-0005) |
| `oxygen.post_pitch` | reused (Kjøling/Pakking; shared mastery, same fact) | fact (OXY-0002) |

Only one new concept is introduced, and it is the only methodology concept. The panel needs a NO/EN label for
`package.priming_tool`.

## 6. Locked chunks (after CHUNK-PACK-E)

| Chunk | Basis | Content | source_claims |
|---|---|---|---|
| CHUNK-PACK-F | fact | Priming amount and carbonation:<br>- more or less priming sugar → more or less carbonation;<br>- the right amount depends on the beer and the carbonation you want;<br>- no single amount fits every batch. | FACT-PACK-0001 |
| CHUNK-PACK-G | methodology | Use a trusted tool:<br>- take the amount from your recipe, a priming calculator or a carbonation table you trust;<br>- give it the details it asks for;<br>- write down which tool and amount you used;<br>- no hand calculation needed. | none |
| CHUNK-PACK-H | fact | Clarity before packaging (short):<br>- yeast and other material tend to settle with time, so beer often becomes clearer;<br>- how much depends on the yeast;<br>- some beers are meant to stay hazy. | FACT-BREW-0005 |
| CHUNK-PACK-I | fact | Oxygen and shelf life (short):<br>- after fermentation has started, oxygen pick-up can contribute to stale/cardboard flavours, weaker hop aroma and shorter shelf stability;<br>- minimise splashing and air contact;<br>- it is a direction, not an instant ruin. | FACT-OXY-0002 |

## 7. Locked questions

All are `intermediate`, with three options and one correct answer.

| Question | Type | Basis | Concept | source_claims | Intent |
|---|---|---|---|---|---|
| Q-PACK-006 | scenario | fact | `package.priming` | FACT-PACK-0001 | A friend uses the same priming amount for every beer. The correct answer is that it depends on the beer and the carbonation wanted |
| Q-PACK-007 | scenario | methodology | `package.priming_tool` | none | How to decide the amount. The correct answer is a trusted recipe/calculator/table, recorded. Distractors: guess; "you must calculate it by hand" |
| Q-PACK-008 | scenario | fact | `fermentation.conditioning` | FACT-BREW-0005 | The beer is still hazy at packaging. The correct answer is that clarity depends on the yeast and some beers are meant to be hazy, so compare with what you intended. Not "add finings" or "always wait until bright" |
| Q-PACK-009 | scenario | fact | `oxygen.post_pitch` | FACT-OXY-0002 | Why careful filling matters. The correct answer is that oxygen can give stale flavours, weaker hop aroma and reduced shelf stability. Distractors: "oxygen doesn't matter once fermentation is done"; "any air instantly ruins the beer" |

**Implementation prerequisite** (not a fact gap): `bryggeskole/pilot_package.py` has no `basis` field. Add the scoped rule
used in `pilot_fermentation.py`:
- an absent basis means fact;
- a closed `METHODOLOGY_CONCEPTS = {package.priming_tool}`;
- CHUNK-PACK-A…E and Q-PACK-001…005 stay byte-identical;
- `test_pilot_sensory._NO_METHODOLOGY_PILOTS` drops `pilot_package`.

**NO/EN wording traps** (binding):
- No numbers at all: grams, g/L, volumes of CO₂, temperatures, days, pressures.
- No carbonation formula or table values.
- No "more sugar is always better" or "follow the label blindly". Bottle-bomb and over-pressure teaching stays with
  FACT-PACK-0003 in Foundation and is not re-claimed here.
- No finings, gelatin, isinglass or cold crash/cold conditioning. No "every beer must be bright".
- No oxidation chemistry. No shelf-life durations or "best before" claims. No "one exposure ruins the beer".
- No App field mapping. Completion stays with FACT-MEAS-0002 via the existing Foundation pointer.
- NO uses "flaskekondisjonering" for bottle conditioning, as in Foundation, and "modning" for maturation (FACT-BREW-0005
  notes).

**Bryggemester excluded:**
- quantitative priming and carbonation maths;
- residual-CO₂ estimation;
- kegging pressure tables, gauges and regulators;
- foam (D57);
- finings and clarification techniques (D28 depth);
- shelf-life depth and oxidation chemistry (D58/D62 depth).

## 8. Implementation-ready decision

**IMPLEMENTATION READY.** All four chunks and four questions are supported by verified records (PACK-0001, BREW-0005,
OXY-0002) or labelled methodology (§D.6). No fact gap and no new concept beyond `package.priming_tool`.

## 9. Explicitly not done

Not done in this document:
- no implementation;
- no registry, lesson JSON or product code change;
- no stage UI, Web, #471 or issue-477 change;
- no GitHub contact.

Sync note: mirror on #419 / the #343 roadmap when GitHub returns. No issue number is assigned.

v1.0 (2026-10-05, offline): readiness contract; IMPLEMENTATION READY; no new facts.
