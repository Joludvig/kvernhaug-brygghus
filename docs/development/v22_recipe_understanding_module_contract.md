# V2.2 — Oppskriftsforståelse (recipe understanding) Kompetent contract

Version: 1.1
Status: **Chief review completed 2026-10-03** (§27). The module is approved for implementation-issue creation; the issue draft is §28.
Implementation depends on the Måling og bryggelogg Foundation module landing first, and the issue is pending because GitHub is unavailable.
Not yet actionable as product work. (v1.0: decision/prep document — reviewable, not yet actionable.)
Status refresh 2026-10-04: the Måling Foundation dependency is satisfied in the offline/local integration (not yet on
GitHub/master). This module itself is not implemented.
Governed by: [#436](https://github.com/Joludvig/kvernhaug-brygghus/issues/436), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3); product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65); curriculum owner
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (merged), whose map
(`v22_g3q_full_bryggeskole_curriculum_map.md`, topics D07–D14, module 9 "Oppskriftsforståelse") recommends this module. Sibling contracts:
`v22_measurement_brewlog_module_contract.md` (#434/#435, Måling og bryggelogg), `v22_g3n_evaluate_inspect_closure_contract.md`
(Brew History methodology), `v22_g3p_raw_material_learning_contract.md` (Råvarer).
Authoritative base at creation: `3b1df6ed827bad5aea974867bc28b042f9ea1c99`.

This is a docs-only contract. It contains **no product code, no Course Fact Registry mutation, no new verified fact, no module, no UI, no
recipe-engine change, no Core/schema change, no App/Web/Sóti change and no deploy**. Chief must review it before any implementation child
issue is opened.

## 0. Source-status guard (read first)

The source reconnaissance behind this contract (delivered to the owner before #436) is a **source map, not a verified fact pack**. It is not
stored in the repository, and **this run did not open any external source**. Therefore:

- Sources named in §16 are recorded as the reconnaissance found them. They are **directions for the later fact-pack round**, not citations. The
  fact-pack round must re-open and read every source it cites, record scope, tier, date and access method, and have Chief review it. AI is
  never a source.
- Every candidate claim in §5 is **unverified** until that round has done so.
- Only the registry records in §4 are reusable now, and only within their existing `notes` and wording-trap scope.
- Some reconnaissance sources were read directly and some through a summarising fetch tool. The fact-pack round must spot-check every quote
  against the live source before promoting a record.
- The Kunze pages named in §16 (pp. 403, 405, 406) were visually verified during reconnaissance. They were not re-opened in this run.
- The recipe-engine description in §14 was read from origin/master `3b1df6e` during reconnaissance and is repeated here as documented
  implementation truth. It is not a teaching source.

**Level naming.** The #419 map uses L1/L2. In this contract **Foundation = L1** and **Kompetent = L2**.

**Chief decisions recorded as fixed inputs** (not re-opened here): BU:GU is an App/Master-view heuristic only; new recipe facts use
`FACT-RECIPE-000n`; style context is methodology and needs no style Course Fact; future R-4 is `professional_interpretation`; the existing recipe
engine is the only calculation truth; no directional claim about alcohol and perceived bitterness; no numeric teaching bands or formulas.

## 1. Foundation prerequisite checkpoint

There is **no new Foundation teaching** in this module. Foundation already covers (elsewhere): what malt, hops, yeast and water do (Råvarer), the
attenuation sentence (FACT-YEAST-0002), and OG/FG as measurements (Måling, #435).

This module opens with one short checkpoint, at the start of the Kompetent module:

> **The OG/FG/ABV/IBU/EBC values shown for a recipe are predictions/estimates. Measured values are what actually happened.**

This is methodology (G3N §1.7, #435), **not a Course Fact**. It has no registry record and needs none.

Foundation outcome: "I can follow a recipe and understand the basic consequence." That is already reachable with existing facts. Balance, BU:GU,
style ranges and formulation are **not** pulled down into Foundation.

## 2. Kompetent learner outcomes

After Oppskriftsforståelse, a homebrewer can, in their own words and without numbers to memorise:

1. read a recipe as a **plan**: say what each major ingredient row is doing (base malt, specialty malt, bittering and late hops, yeast);
2. explain the chain **OG (extract) → fermentability → attenuation → FG → alcohol / body / dryness tendencies**, and say that a high OG is not
   automatically sweet and not automatically strong;
3. say that **attenuation is not decided by the yeast alone**: the wort's fermentability (malt and mash) and the fermentation conditions matter;
4. say in one sentence what the alcohol concept is: yeast turns fermentable sugar into alcohol and CO2, and what is left is residual extract;
5. explain where **colour** comes from (malt, kilning, roasting), that EBC is a darkness scale, and that colour is not flavour;
6. explain that a calculated **IBU** is a standard index and an estimate, that it is **one axis** and not a taste verdict, and that two beers with the
   same IBU can taste different because the rest of the beer matters;
7. describe **balance** as how strongly the parts of the beer are perceived relative to each other, and say that a deliberately unbalanced beer can
   be valid;
8. use a **style range** as a comparison frame for what is typical, and say that being outside it does not make a recipe wrong;
9. follow the **formulation workflow** (§13) and use the existing App to check predicted consequences;
10. make **one deliberate change** to a recipe, write it down as a hypothesis, and after the next brew compare planned with actual without
    claiming proof.

The learner finishes able to say: "I understand why this recipe looks like this, what the important choices are, and what will probably happen if I
deliberately change one of them."

## 3. MUST / SHOULD / LATER concepts

Concept ids equal the registry concept ids that question `concepts[]` will carry (§20). The `Basis` column says what supports a chunk today.

| Level | Concept | Proposed id | Basis |
|---|---|---|---|
| Kompetent MUST | Gravity / recipe consequence: OG is extract, not all of it ferments | `recipe.gravity_vs_fermentability` | FACT-YEAST-0002, FACT-MASH-0001/0004, M1 (Måling) |
| Kompetent MUST | Attenuation / fermentability: recipe + yeast + conditions | `recipe.attenuation_chain` | FACT-YEAST-0002/0005, FACT-MASH-0001/0004 |
| Kompetent MUST | Alcohol concept (no formula) | `recipe.alcohol_concept` | FACT-YEAST-0001/0002, M1 |
| Kompetent MUST | Bitterness / IBU as one axis | `recipe.ibu_vs_perceived_bitterness` | FACT-RECIPE-0001 (R-2, landed) + FACT-HOP-0001/0002 |
| Kompetent MUST | Recipe formulation workflow | `recipe.formulation_workflow` | Methodology + FACT-METHOD-0004 |
| Kompetent SHOULD | Colour | `recipe.colour_origin` | FACT-MALT-0002/0003/0004 |
| Kompetent SHOULD | Balance | `recipe.balance` | FACT-RECIPE-0003 (R-4, landed) |
| Kompetent SHOULD | Style as reference frame | `recipe.style_context` | Methodology (no fact) |
| Kompetent SHOULD | Change one thing on purpose | ~~`recipe.one_change`~~ → taught under `recipe.formulation_workflow` (Chief 2026-10-03, §27.5) | Methodology; G3N/#435 |
| Kompetent SHOULD | Specialty malt fermentability tendency | `recipe.specialty_fermentability` | FACT-RECIPE-0002 (R-1, landed) |
| LATER / Bryggemester (course track) | Yeast biochemistry (glycolysis) | — | Kunze §4.1.2 (not for Kompetent) |
| LATER / Bryggemester (course track) | Apparent vs real attenuation detail | — | One gloss at most |
| LATER / Bryggemester (course track) | Utilisation and Tinseth maths, EBC/SRM/Lovibond conversion, efficiency maths | — | Explicit non-goals (§26) |
| LATER | Water minerals and perceived bitterness | — | Tier B only; gap |
| LATER | Brewhouse yield, mash pH detail, cohumulone claims | — | Other modules / contested |

Deviations from the #419 map: D07 (gravity) is MUST L1 concept, L2 use; here the L1 definitions live in Måling and only the recipe consequence lives
here. D08–D09 stay L2. D10, D12 and D13 stay SHOULD. D11 and D14 stay MUST. No map row is dropped.

## 4. Existing facts reused

Verified registry records on origin/master `3b1df6e` (39 records). Reuse is limited to each record's own `notes` and wording traps.

| Record | Used for |
|---|---|
| FACT-YEAST-0001 | Yeast consumes fermentable sugar and produces alcohol and CO2 (alcohol concept) |
| FACT-YEAST-0002 | Attenuation is the share of wort sugars consumed; depends on yeast, fermentation and wort conditions; no numbers |
| FACT-YEAST-0005 | Choose yeast against the intended beer, using producer attenuation information |
| FACT-MASH-0001 | Enzymes; some starch becomes dextrins that ordinary yeast does not ferment |
| FACT-MASH-0004 | Mash temperature is one of several factors; no single correct temperature |
| FACT-MASH-0002 | Abstract-level only (65–80 C study). Prefer MASH-0004; do not lean on it |
| FACT-MALT-0002 | Base versus specialty malt |
| FACT-MALT-0003 | Colour and flavour from thermal processing; colour is not a one-to-one flavour predictor; no EBC numbers |
| FACT-MALT-0004 | Grist proportion affects malt character; specialty-malt scope, not universal |
| FACT-HOP-0001 | Isomerisation is time-dependent, with a ceiling; no utilisation numbers |
| FACT-HOP-0002 / 0003 | Late/whirlpool additions retain more aroma and generally give lower utilisation; multiple additions |
| FACT-BREW-0001/0002/0003 | Fermentation temperature: activity, strain-dependent flavour, strain-specific targets |
| FACT-METHOD-0004 | Planning variables |

**Methodology already shipped (no Course Fact, per G3N §1.7):** predicted versus actual; the read-only plan-versus-actual comparison in Brew History;
Learn → Reflect → improve next brew; `log.hypothesis_next_change` from #435.

**Planned at v1.0, now landed (refreshed 2026-10-03):** #435 measurement M1, M2, M4 are FACT-MEAS-0001/0002/0003 (#444/#453); P4 FACT-HOP-0004
and **FACT-HOP-0005** (alpha % versus IBU, #440); R-2, R-1 and R-4 are FACT-RECIPE-0001/0002/0003 (#441/#450, #442/#451, #443/#452). All are
`verified`. FACT-RECIPE-0001/0002 still carry an open Chief live spot-check note (§27.10).

**Checked and not needed:** FACT-BOIL-*, FACT-COOL-*, FACT-OXY-*, FACT-PACK-*, FACT-TRANSFER-*.

**No registry record exists** for the recipe consequence of gravity, IBU-versus-perceived-bitterness, balance, colour scale, style or formulation.

## 5. Smallest future fact-pack plan

**No registry mutation happens in #436.** Everything below is a plan for later child issues. Ids use `FACT-RECIPE-000n`; exact numbers are assigned at
implementation time.

| Id (proposed) | Classification | Concept | Direction of claim (unverified) |
|---|---|---|---|
| **R-2** | `documented_fact` | `recipe.ibu_vs_perceived_bitterness` | IBU is a standard index; a calculated recipe IBU is an estimate; perceived bitterness also depends on the beer matrix. **No directional claim** for alcohol, residual sugar, roast, water or hop character |
| **R-1** | `documented_fact` | `recipe.specialty_fermentability` | Caramel/crystal malt extract is less fermentable than base-malt extract and adds body and residual extract; the effect depends on type and usage rate and is normally small at ordinary usage |
| **R-4** | `professional_interpretation` | `recipe.balance` | Balance describes how strongly the parts of the beer are perceived relative to each other; no universal numeric ratio; deliberate imbalance can be valid |

- **R-3 (a style Course Fact) is NOT required.** Style context is methodology (§12).
- **Status 2026-10-03:** all of the records below have landed (§4). Historical plan:
- **Order:** prerequisites first — #435 measurement M1 and P4 FACT-HOP-0005 — then **R-2, R-1, R-4**. R-4 last because it synthesises R-2 with the
  other sources and mirrors the FACT-MASH-0004 / FACT-HOP-0003 synthesis precedent.
- **Dependencies:** R-2 must not be implemented until FACT-HOP-0005 has landed. R-4 depends on R-2.
- **Each future record** needs: sources opened and read live, scope, tier, date, wording traps, and Chief review. Numbers stay out.
- Not registry facts (methodology, §15): the mental model, BU:GU, style stance, the formulation workflow, one-change, predicted-versus-actual.

## 6. Recipe mental model

```
INGREDIENTS  →  WORT                          →  FERMENTATION                 →  FINISHED BEER
malt bill        extract / OG                     yeast + wort + conditions        FG + alcohol + residual extract
+ mash choices   + fermentability                 → attenuation                    + body / dryness tendencies

hops             alpha acids + timing             calculated IBU                   perceived bitterness depends on
                                                                                   the rest of the beer
```

Every arrow is a **tendency the brewer steers**, not a lookup. **The App calculates predictions.** Numbers on the recipe are estimates.

## 7. Gravity / attenuation / alcohol model

```
OG / extract → fermentability → yeast + fermentation conditions → attenuation → FG → alcohol / body / dryness tendencies
```

Teach:

- OG is the extract dissolved in the wort before fermentation; not all of it is fermentable. FG is what is left after fermentation. The definitions
  and readings stay in **#435 / Måling**; this module teaches only the recipe consequence.
- **High OG does not automatically mean a sweet beer**, and does not automatically mean a strong one (OG sets the potential; what ferments decides the
  rest).
- **Yeast alone does not determine attenuation.** Mash choices and malt choices set how fermentable the wort is; yeast and conditions then act on it
  (FACT-YEAST-0002, FACT-MASH-0001/0004).
- Alcohol concept: yeast ferments available sugar into alcohol and CO2; more fermentable extract generally allows more alcohol; residual extract remains.

Link types, for the fact-pack round to keep straight:

- **Definitional or documented:** attenuation is the share of extract fermented; the wort's fermentability sets a ceiling; more fermented extract
  gives more alcohol.
- **Tendencies only:** mash temperature and fermentability; specialty malt and fermentability; FG and body/dryness/sweetness; OG and sweetness.

Do not teach: numeric attenuation bands, an ABV formula, a strain ranking, an attenuation calculator, apparent-versus-real detail beyond one gloss.

## 8. Colour model

Teach:

- malt is the main colour source in most beers; kilning and roasting affect colour (FACT-MALT-0002/0003);
- **EBC is a darkness scale; a higher EBC is darker**;
- **colour is not flavour**: similar colours can come from different malts or sugars with quite different flavours (FACT-MALT-0003);
- the recipe's **predicted colour is an estimate**;
- proportion matters (FACT-MALT-0004, specialty-malt scope only).

A learner should be able to see why a recipe is pale, amber, brown or black without memorising colour equations. **No colour-conversion maths** (EBC,
SRM, Lovibond). Boil/Maillard process colour pick-up is **not sourced** and is not taught (gap G-4 in §17).

## 9. Bitterness / perceived-bitterness model

```
hop alpha acid %  →  isomerised by boiling (FACT-HOP-0001)  →  calculated IBU (index, estimate)
                                                          →  perceived bitterness = IBU + the rest of the beer
```

Teach:

- **IBU is a standard index.** A calculated recipe IBU is an **estimate**.
- Perceived bitterness also depends on the beer matrix.
- **IBU is ONE axis, not a taste verdict.** Two beers with the same IBU can taste different.
- Hop timing is taught at direction level only (FACT-HOP-0001/0002/0003): earlier = more bitterness, later = more aroma; no minutes as rules.

**Teach no directional claim** for alcohol, residual sugar, roast, water or hop character. The reconnaissance sources **conflict** on alcohol (one
peer-reviewed source reports that ethanol increases perceived bitterness; a trade source treats alcohol as sweetness to be balanced), and no
Tier A source states a direction for the others. The only Tier A-supported statement is that the matrix changes perception.

Do not teach: IBU formula, Tinseth, utilisation percentages, IBU bands as universal truth, alpha acid % as IBU. P4 FACT-HOP-0005 covers alpha % versus IBU
and must land before R-2. (Both have landed: FACT-HOP-0005 and FACT-RECIPE-0001, §4.)

## 10. Balance model

**Balance describes how strongly the different parts of the beer are perceived relative to each other.**

Possible components: malt sweetness and body; bitterness; dryness; alcohol; roast; hop flavour and aroma.

- There is **no correct universal numerical ratio**.
- **A deliberately unbalanced beer can be intentional and valid.**
- Bitterness commonly works against malt sweetness, but a brewer may push either forward on purpose.
- Any lever named for changing balance (more extract calls for more bittering hops, less late hopping keeps malt more prominent) is shown as a
  **tendency**, and the learner is told to check the result by tasting.

Balance is a professional interpretation (future R-4), not a measurement. Kunze has no balance section; source strength is mainly Tier B (§16–§17).
Not taught: water minerals and bitterness, cohumulone claims, any numeric target.

## 11. BU:GU governance

BU:GU is **not** part of the learner curriculum. The contract is explicit:

- BU:GU stays an **App/Master-view rough heuristic**.
- It is **not a Course Fact** and has **no registry record**.
- It is **not a learning objective**. There is **no quiz** on it.
- **No BU:GU thresholds or bands** appear in teaching text, questions or visuals.
- It uses **OG, not FG**, so it ignores residual extract.
- It uses a **calculated IBU**, which is an estimate.
- It **ignores several perceptual variables** (alcohol, roast, water, hop character, carbonation, the rest of the matrix).
- **The same ratio does not mean the same beer, and the same BU:GU must never imply the same balance.**
- ~~If the course mentions it at all, it is at most **one sentence in the Master view** saying it is a rough App indicator and not a verdict.~~
  **Superseded (Chief 2026-10-03, §27.6): BU:GU is omitted entirely from the module** — no sentence, no Master-view exception.
- Learn text must never quote a value or a band as "balanced".

**Separate future issue (not #436):** softening the App's labels. The current style panel uses unsourced product thresholds and wording such as
"Humledominert", "Maltdominert" and "Harmonisk balansert … oppleves veldig balansert", the last of which asserts a perception. Changing them is an App
change outside this contract; it is recorded in §25 only so it is not lost.

## 12. Style-context governance

- **Style is a reference frame, not a rulebook.** This is **methodology**, and **no style Course Fact is required**.
- A style range is a **comparison frame for what is typical**. **Outside the range does not make a recipe wrong.**
- The style-match percentage is **context only, not a quality score**. The course never presents it as a grade.
- **BJCP is a context source only, not a brewing-chemistry authority.** It describes where most competition examples cluster and is meant for judging.
- The App already labels non-BJCP Kvernhaug/historical categories as "not an official BJCP style"; the course keeps that distinction.
- **Direct BJCP ranges shown in Learn text require a later licence/attribution check** (gap G-7). Until then, Learn text may describe the idea of a
  range without quoting BJCP numbers.
- No style memorisation: no "learn the ranges for style X" objectives or questions.

## 13. Recipe-formulation workflow

Kvernhaug **methodology** (not a Course Fact, and **not a rigid universal brewing algorithm**; a learner may enter at any step):

1. Decide what you want the beer to be.
2. Choose strength direction.
3. Choose malt structure.
4. Choose bitterness and hop expression.
5. Choose yeast / attenuation direction.
6. Choose process choices supporting the goal.
7. Check predicted consequences in the existing App.
8. Brew, measure and evaluate.
9. Change one deliberate thing next time.

Steps 3–6 rest on existing facts (FACT-MALT-0002/0004, FACT-HOP-0001/0002/0003, FACT-YEAST-0002/0005, FACT-MASH-0004, FACT-BREW-0003). Step 7 is
the §14 mapping. Step 8 is #435 (Måling). Step 9 is one-change methodology below.

**One-change methodology.** Change as few things as practical, ideally one, so the result is easier to interpret. But:

- this **does not prove causation**;
- a homebrew batch is **not a controlled experiment**;
- ingredient lots, process, measurement and tasting all vary;
- treat each deliberate change as a **hypothesis**.

Reuse G3N / #435 methodology: **Learn → Reflect → improve next brew**. (Chief 2026-10-03, §27.5: this module carries it as
`recipe.formulation_workflow`; it does not reuse `log.hypothesis_next_change`, whose consolidation is deferred to the Kompetent Måling slice.) No Course Fact and no statistical experiment design.

## 14. Existing engine Learn→Plan mapping

**THE COURSE EXPLAINS. THE EXISTING ENGINE CALCULATES. No second truth.** The engine is the only calculation truth. Bryggeskole builds **no**
calculator, and does **not** compensate for engine limits with course calculations. The engine is implementation truth, **not** a teaching source.

**Current implementation truth (read from origin/master `3b1df6e`):**

| Value | How the engine gets it |
|---|---|
| OG | Existing recipe calculation (malt potential × amount × the recipe's efficiency setting ÷ volume) |
| EBC | Existing Morey-based calculation |
| FG / ABV | Based on the yeast's **stored attenuation**. **The mash profile does not affect the FG calculation** |
| IBU | Existing Tinseth implementation (a 0-minute addition gives 0 IBU; late/whirlpool additions are treated by minutes, not temperature) |
| BU:GU | App heuristic (§11) |
| Style | Existing BJCP ranges plus non-BJCP labelled categories |

**Safe engine consequence view — numeric or predicted direction is okay** (always labelled as estimate):

| Change | Show |
|---|---|
| more base malt | OG direction; predicted ABV direction |
| more or darker malt | EBC direction |
| more or earlier bittering hops | calculated IBU direction |
| different stored yeast attenuation | predicted FG / ABV direction — **must be labelled estimate** |

**Qualitative only — never show an engine number as if it were the effect:**

| Change | Why |
|---|---|
| mash temperature → fermentability | not modelled |
| specialty malt → body / FG tendency | the engine raises FG only through OG, not through unfermentable extract |
| late / whirlpool hop effects beyond the current model | engine treats minutes as boil-equivalent time |
| fermentation-temperature flavour consequences | not in the calculation (existing Gjæring bridge stays qualitative) |
| perceived bitterness | IBU is an index |
| sweetness / body / balance | not modelled |

The contract states plainly that **the engine does not model the mash-temperature effect on FG and does not model body, sweetness or balance**. Any
future change to the engine is a separate App/Core issue and not part of this contract. Efficiency is out of scope apart from one sentence:
"the OG you get depends on your setup".

## 15. Methodology versus Course Facts

**Not Course Facts (keep out of the registry):**

- predicted numbers are estimates and measured values are what happened (§1);
- the mental model (§6) and the gravity/attenuation chain as a teaching sequence (§7);
- BU:GU as a Master-view heuristic (§11);
- style as a reference frame; the style-match percentage as context (§12);
- the nine-step workflow and one-change methodology (§13);
- Learn → Reflect → improve next brew.

**Future Course Facts:** R-2, R-1, R-4 only (§5). Everything else reuses §4 records.

## 16. Source requirements

Every future record must be read live and recorded with tier, scope, date and access method. Reconnaissance directions (not citations):

| Need | Direction | Tier | Note |
|---|---|---|---|
| R-2 IBU vs perceived | Oxford Companion to Beer "IBUs" entry; BrewingScience 2007 taste-sensing paper (Gastl, Hanke, Back); a trade balance article | B / A (narrow) / B | The peer-reviewed paper is a taste-sensor study with simplified solutions. Do not derive directional claims |
| R-1 specialty fermentability | Briess caramel-malt manual (maltster, Tier A); Oxford Companion "caramel malts" (B) | A / B | Effect is normally small at ordinary usage; no percentages in teaching |
| R-4 balance | Palmer *How to Brew* hops and recipe chapters; a trade balance article; the R-2 sources | B | Synthesis; mirrors MASH-0004 |
| Gravity/attenuation chain | Palmer yeast and mash chapters; Kunze pp. 403, 405 (visually verified); existing facts | B | Kunze is industrial lager context; use qualitatively; no lager figures |
| Colour | Oxford Companion colour/SRM entries; Briess malt-analysis article | B / A | Predicted colour is an estimate |
| Formulation | Palmer "Developing Your Own Recipes"; AHA recipe-design article | B | Methodology; not a fact |
| Style context | BJCP introduction and FAQ | context only | Describes BJCP itself; not chemistry |

Reading marks for the later round: `[DIRECT]` raw text read; `[WF]` fetched summary (spot-check needed); `[KZ-V]` visually verified Kunze page (record
section and printed page; printed = PDF + 2 for chapters 3/4); OCR-only text is a pointer, never an exact-claim source. Retailers, forums, YouTube and
AI are never provenance.

## 17. Source gaps

- **G-1** No Tier A directional evidence for every component of perceived bitterness (alcohol, residual sugar, roast, water, hop character).
- **G-2** **Alcohol direction conflicts between sources.** Teach no direction.
- **G-3** BU:GU evidence is weak (trade and blog level; the origin book was not opened).
- **G-4** Process colour pick-up (boil, Maillard in the kettle) is not sourced.
- **G-5** Balance and formulation rest mainly on Tier B. **Kunze is insufficient for balance and formulation** (no balance section; the map's malt-usage
  pointer at p. 186 does not match its content).
- **G-6** FACT-MASH-0002 is abstract-level only.
- **G-7** BJCP licence/attribution for reusing ranges in Learn text is unresolved.
- **G-8** The Palmer web source needs a later live check and an edition, date and access record (the site's certificate was expired during
  reconnaissance).
- **G-9** Some reconnaissance sources were read through a summarising fetch tool and need a live spot-check; some pages were not accessible (a
  homebrewing-association article and a magazine article could not be read directly).
- **G-10** Some source dates are not shown on the page or are old; each fact-pack round must record them.

## 18. Wording traps

Never teach:

- "high OG = sweet"; "high OG automatically = strong";
- "yeast alone sets attenuation"; "mash temperature X gives attenuation Y";
- "crystal malt simply makes beer sweet or heavy" (the effect depends on type and usage and is normally small);
- "the only way to raise FG is unfermentable sugars" (mash also matters);
- "IBU = perceived bitterness"; "same IBU = same bitterness";
- any direction for alcohol, residual sugar, roast, water or hop character as a fact about perceived bitterness;
- "same BU:GU = same balance"; "BU:GU X = balanced"; any BU:GU band;
- "colour = flavour"; EBC as an exact prediction ("the beer will be 22 EBC");
- "style match % = beer quality"; "outside the style range = wrong"; "BJCP tells you how to brew";
- "the engine models the mash-temperature effect on FG"; "the engine models body, sweetness or balance";
- "change exactly one thing" as proof of causation;
- "harmonisk / veldig balansert" as scientific truth;
- Palmer's or Kunze's attenuation percentages, or example grist percentages, as teaching rules.

## 19. NO/EN terminology strategy

Norwegian is the source language; English follows. Match existing App words rather than inventing new ones.

| NO | EN | Note |
|---|---|---|
| oppskrift | recipe | |
| kornblanding / malt | grist / malt | grist = the whole malt bill |
| vørter / OG (opprinnelig tetthet) | wort / OG | OG-måling wording lives in Måling |
| ferdiggjæret tetthet / FG | final gravity / FG | |
| utgjæring | attenuation | not "utgjæringsprosent" as a number |
| forgjærbarhet | fermentability | |
| restekstrakt | residual extract | |
| alkohol (ABV) | alcohol (ABV) | concept only |
| farge / EBC | colour / EBC | "mørkere = høyere EBC" |
| bitterhet / IBU | bitterness / IBU | "beregnet IBU", never "opplevd IBU" |
| opplevd bitterhet | perceived bitterness | |
| balanse | balance | never "riktig balanse" |
| stil / stilområde | style / style range | "referanseramme", not "regel" |
| forventet / beregnet | predicted / calculated | always for App values |
| målt | measured | Måling wording |
| hypotese, én bevisst endring | hypothesis, one deliberate change | |

Terms not to use in teaching: "harmonisk", "ideell", "riktig", "perfekt" for balance; "kvalitetsscore" for style match; "fasit" for a workflow or
range. Bitterness and colour terms follow the Råvarer and Kjøling/Koking modules.

## 20. Mastery concept IDs

Mastery ids equal the registry concept ids carried by question `concepts[]` in `bryggeskole/data/pilot_*.json` (existing convention; no new mastery
system). Proposed ids (see §3):

- `recipe.gravity_vs_fermentability`, `recipe.attenuation_chain`, `recipe.alcohol_concept`
- `recipe.ibu_vs_perceived_bitterness` (FACT-RECIPE-0001)
- `recipe.formulation_workflow`, ~~`recipe.one_change`~~ (not created, §27.5)
- `recipe.colour_origin`, `recipe.balance` (FACT-RECIPE-0003), `recipe.style_context`, `recipe.specialty_fermentability` (FACT-RECIPE-0002)

**Superseded for the first implementation by §27.4–§27.5:** questions reuse existing ids where they apply an already-mastered concept; the
proposed `recipe.gravity_vs_fermentability`, `recipe.attenuation_chain`, `recipe.alcohol_concept` and `recipe.colour_origin` are not introduced.

Existing ids reused in questions: `yeast.attenuation`, `yeast.organism_role`, `yeast.choice_principle`, `mashing.fermentability`,
`mashing.dextrins`, `malt.base_vs_specialty`, `malt.colour_flavour`, `malt.grist_percentage`, `hop.isomerization_time`, `hop.addition_strategy`,
`method.planning_variables`. Questions that assert a fact must carry the id of a verified record; questions on methodology carry the methodology
concept id and no `FACT-*` claim.

## 21. Recommended module structure

Module 9, after Måling og bryggelogg (module 8). About seven Kompetent chunks (locked at exactly seven, CHUNK-REC-A..G, in §27.2–§27.3):

1. **Read a recipe as a plan** — what each row does; the §1 checkpoint.
2. **From OG to FG** — §7 chain; alcohol concept; body/dryness as tendencies.
3. **Colour** — §8.
4. **Bitterness** — §9; IBU as one axis.
5. **Balance** — §10. (v1.0 allowed a one-sentence BU:GU Master note; superseded — BU:GU omitted, §27.6.)
6. **Style as reference frame** — §12.
7. **Change one thing on purpose** — §13 workflow and one-change; bridge to the recipe editor (§14).

Chunks 2 and 7 need no new facts and can be built first. Chunks 4 and 5 wait for R-2 and R-4 (or ship as clearly limited to the existing facts).
(2026-10-03: R-2 and R-4 have landed, so all seven chunks ship in one implementation issue, §28.)
Each chunk: short text, one visual or interaction, a few questions; no wall of text. Dependencies from the #419 map: Råvarer before recipe theory.

## 22. Recommended visuals / interactions

Contract only; none are implemented here.

- **Qualitative extract bar:** one bar for the wort's extract, split into "fermented → alcohol + CO2" and "left in the beer", with a
  fermentability control. No numbers. Complements the planned gravity-over-time curve in Måling.
- **Malt colour strip:** pale to black with base / caramel / roasted roles, and a "colour is not flavour" prompt. No EBC maths.
- **Recipe consequence view using the existing engine:** change one input and see direction arrows on OG, FG, ABV, IBU and EBC, each tagged
  "calculated direction (estimate)" or "qualitative only" per §14. It states that the engine does not model mash temperature.
- **Neutral style-range strip:** the recipe's value against a range with neutral wording ("typical for this style" / "outside the usual range"); no
  percentage score; no BJCP numbers until the licence check.
- **"Two beers, same IBU" comparison:** two recipes with the same calculated IBU but different FG, roast or OG, asking "what else changes how each
  tastes?" (no directional answer key).

Reuse the existing Learn→Plan bridge pattern (verified chunk ids, no new teaching text authored in the panel).

## 23. One representative acceptance scenario

A homebrewer opens a pale-ale recipe in the App. The module's first screen tells them the OG/FG/ABV/IBU/EBC values are predictions. They read the
recipe rows and say what the base malt, the small caramel-malt share, the bittering and late hops and the yeast are doing.

They raise the base malt in the existing recipe view and see OG and predicted ABV move; they raise a darker malt and see EBC move; they lengthen the
bittering addition and see calculated IBU move. Each is labelled an estimate. They then try "mash temperature" in the consequence view and are told
it is **qualitative only** and that the engine does not model it.

They explain in their own words why a high OG does not automatically mean a sweet beer and why the yeast alone does not fix attenuation. They say why
two beers with the same IBU can taste different and describe what "balance" means to them without a target number. They compare the recipe with a
style range and say that being outside it does not make it wrong.

They write one hypothesis ("less late hopping should let the malt stand out more"), make **one deliberate change**, brew, measure (Måling), and after
tasting record what happened as a hypothesis result, not proof.

Pass criteria: no number learned, no threshold, no formula, no style memorised; every App value read as an estimate; the engine used only as the
calculator; the hypothesis written before the brew.

## 24. Smallest implementation slices

Each slice is a separate child issue after Chief review; none is part of #436.

1. **Docs contract (this document).** No registry, code or UI change.
2. **Prerequisites** (other issues): #435 measurement M1 and P4 FACT-HOP-0005. — **landed**
3. **Fact pack R-2** (`recipe.ibu_vs_perceived_bitterness`), sources read live, Chief review. — **landed** (FACT-RECIPE-0001)
4. **Fact pack R-1** (`recipe.specialty_fermentability`). — **landed** (FACT-RECIPE-0002)
5. **Fact pack R-4** (`recipe.balance`). — **landed** (FACT-RECIPE-0003)
6. **Module chunks 2 and 7** on existing facts only.
7. **Chunks 1, 3 (colour) and 6** on existing facts and methodology.
8. **Chunks 4 and 5** after R-2 and R-4 land.

**2026-10-03:** slices 6–8 are merged into one module issue (§28, all seven chunks). Slice 9 (recipe-editor bridge) stays a
separate, later UI slice (§27.9).
9. **Recipe-editor bridge** (consequence view using the existing engine; verified chunk ids only; no second calculation).

Do not build UI before this contract is reviewed.

## 25. Dependencies / later gates

- **#435 / Måling:** measurement M1 (OG/FG definitions) before this module teaches OG/FG. — M1 landed (FACT-MEAS-0001); additionally the **Måling
  og bryggelogg Foundation module must land before this module is implemented** (§27.8).
- **P4:** FACT-HOP-0005 before R-2 implementation. — landed
- **R-4 depends on R-2.** — both landed
- **BJCP licence/attribution check** before any BJCP numbers appear in Learn text (G-7).
- **Palmer live check** and edition/date/access record before any Palmer-sourced record (G-8).
- **Source spot-checks** of every summarised-fetch quote (G-9).
- **Separate future App issue:** softening the App's balance/BU:GU label wording (§11). Not part of #436.
- **Registry id assignment** for `FACT-RECIPE-000n` at implementation time.
- **Engine limits** (FG/ABV ignore the mash profile and specialty-malt fermentability): accepted as "estimate" labelling. Changing the engine is a separate
  App/Core issue; the course must not compensate.
- **Mash pH, efficiency, water:** other modules; only one-sentence boundaries here.

## 26. Hard non-goals

This contract and its later slices must **not** include:

- registry changes in #436, or any new verified fact in this PR;
- module code, UI, or visual implementation;
- recipe-engine modifications, or any App/Web/Core/Sóti change;
- a Bryggeskole calculator, or a second calculation truth;
- formula teaching: ABV formula, Tinseth or utilisation formula, EBC/SRM/Lovibond conversion maths, attenuation formula as a calculator;
- numeric attenuation bands, numeric BU:GU bands or thresholds, IBU bands as universal truth;
- BU:GU as a learning objective, quiz item, fact or threshold-bearing visual;
- style memorisation, or style-match percentage as a quality score;
- an ingredient encyclopaedia, malt or hop catalogue, or a strain encyclopaedia;
- efficiency maths, water chemistry or detailed water profiles;
- statistical experiment design;
- a brewing chemistry degree, or an optimisation engine;
- deploy.

## 27. Chief review closure (2026-10-03)

Chief reviewed this contract on 2026-10-03. The decisions were relayed to Local Claude and recorded offline because GitHub was unavailable. They
must be mirrored on #436 when access returns. Where an earlier section disagrees with this section, this section wins. Earlier text is kept and
annotated.

### 27.1 Course and App scope

- Oppskriftsforståelse is **entirely Kompetent**.
- The main App's Bryggeskole course scope includes **Foundation → Kompetent hjemmebrygger**, so this module **is** intended for the main App
  Bryggeskole.
- This does not change the later standalone full-course product.
- Sync note: this App-scope decision should also be reflected in the curriculum map's course-architecture section when that local, offline
  architecture record is synchronised. It is recorded here first because this module is the first Kompetent-only module.

### 27.2 Module shape (locked)

- Topic **`recipe.fundamentals`**; JSON `topic_id` **`PILOT-RECIPE-FUNDAMENTALS`**.
- **7 chunks** `CHUNK-REC-A` … `CHUNK-REC-G`; **7 questions** `Q-REC-001` … `Q-REC-007`, exactly one per chunk.
- Every question uses `difficulty: "beginner"`. This field is **item difficulty under the current schema convention, not the course-stage label**.
  The module is Kompetent regardless. No new difficulty taxonomy is introduced.

### 27.3 Chunk scope and allowed facts

| Chunk | Basis | Scope | Allowed source claims |
|---|---|---|---|
| A | fact (application) | Read a recipe as a plan; apply already-taught ingredient roles without re-teaching Råvarer; includes the §1 methodology checkpoint (recipe numbers are predictions/estimates; measurements describe what actually happened) | as needed from FACT-MALT-0002, FACT-MALT-0004, FACT-HOP-0003, FACT-YEAST-0005 |
| B | fact | OG → fermentability → attenuation → FG → alcohol/body/dryness tendencies | FACT-YEAST-0001, FACT-YEAST-0002, FACT-MASH-0001, FACT-MASH-0004, FACT-RECIPE-0002; FACT-MEAS-0001 only as a referenced prerequisite (OG/FG definitions are not re-taught) |
| C | fact | Colour: malt/process origin; EBC as darkness context; colour is not flavour | FACT-MALT-0002, FACT-MALT-0003, FACT-MALT-0004 |
| D | fact | Bitterness: IBU is an index and an estimate, one axis; similar IBU can be perceived differently | FACT-RECIPE-0001, FACT-HOP-0001, FACT-HOP-0002; FACT-HOP-0005 as prerequisite/reference where needed |
| E | fact (professional interpretation) | Balance is relative to brewer intent, not a universal score; deliberate emphasis can be valid | FACT-RECIPE-0003 |
| F | methodology | Style as a comparison frame; outside a range is not automatically wrong | `[]` |
| G | methodology | Formulation workflow: one deliberate change based on an explicit hypothesis/intent; measurement and evaluation are deferred to Måling and Smak | `[]` |

Chunk-specific bans:
- **B:** no "high OG = automatically sweet", no "high OG = automatically strong", no "FG = sweetness score".
- **D:** no directional claim for alcohol, residual sugar, roast, water or hop character on perceived bitterness.
- **F:** no BJCP numbers, no style memorisation, no style-match percentage as a quality score.

### 27.4 Question shape

| Question | Type | Tests |
|---|---|---|
| Q-REC-001 | scenario | Recipe plan / ingredient roles |
| Q-REC-002 | scenario | OG / fermentability / attenuation consequence |
| Q-REC-003 | concept_check or scenario | Colour is not flavour |
| Q-REC-004 | scenario | Same/similar IBU can taste different |
| Q-REC-005 | scenario | Balance against intent |
| Q-REC-006 | scenario | Style frame ≠ right/wrong |
| Q-REC-007 | scenario | One deliberate recipe change |

Questions reuse existing Råvarer concept ids where they apply an already-mastered ingredient concept. No duplicate mastery concept is created
merely because the same fact is applied at recipe level. The exact per-question mapping is in §28.

### 27.5 Concept consolidation

- G uses **`recipe.formulation_workflow`**: planning and changing the recipe deliberately.
- **`recipe.one_change` is not created.**
- **`log.hypothesis_next_change` is not reused here.** Any consolidation of that concept is deferred to the Kompetent Måling slice.
- Evaluating the result afterwards belongs to **`sensory.evaluate_against_intent`** (Smak og evaluering).

### 27.6 BU:GU

**Omitted entirely** from this module: no learning objective, sentence, question, threshold, visual or Master-view exception. The App may keep
displaying its existing heuristic, but this course module does not teach it. (Supersedes §11's one-sentence allowance and §21 item 5's Master note.)

### 27.7 Boundaries

**Måling** owns OG/FG definitions, measured readings, the planned-vs-actual method and the brew log. **Oppskriftsforståelse** owns the consequences
of planned recipe values, recipe intent, and predicted/calculated values as estimates.

Wording:
- Use *forventet / beregnet* and *predicted / calculated*.
- **Never call App recipe values measured values.**

**Smak og evaluering** owns the observed sensory result and evaluation against intent. Oppskrift is the intended/predicted side. It does **not** teach
the tasting sequence, faults, or observation vs interpretation again.

### 27.8 Grid and dependency

Final order: … Pakking → Måling og bryggelogg → **Oppskriftsforståelse** → Smak og evaluering.

Implementation **must wait until the Måling og bryggelogg Foundation module has landed**. The issue draft may be created before then, and it declares
the dependency.

Status refresh (2026-10-04): the Måling Foundation module is implemented in the offline/local integration, so the
dependency is satisfied there. It has not yet landed on GitHub/master. Oppskriftsforståelse is not implemented.

### 27.9 Recipe-editor bridge

The recipe-editor consequence view / visual bridge (§14, §22, §24 slice 9) is a **separate, later UI slice**. It is not part of the first module
implementation issue.

### 27.10 Fact source spot-check (FACT-RECIPE-0001, FACT-RECIPE-0002)

**No registry source entry was marked spot-checked.** Claims, classification, status, `verified_at` and sources are unchanged.

| Record | Stored source entry | Result |
|---|---|---|
| FACT-RECIPE-0001 | Oladokun et al., Food Research International 2016, `10.1016/j.foodres.2016.05.018` | DOI metadata (Crossref) resolves to "Modification of perceived beer bitterness intensity, character and temporal profile by hop aroma extract", Food Res. Int. 86, 104–111 (2016). This is a reference-integrity check only, not a claim spot-check. **Open** |
| FACT-RECIPE-0001 | Oladokun et al., Food Chemistry 2017, `10.1016/j.foodchem.2017.03.031` | Resolves to "Perceived bitterness character of beer in relation to hop variety and the impact of hop aroma", Food Chem. 230, 215–224 (2017). Reference-integrity only. **Open** |
| FACT-RECIPE-0001 | Gastl, Hanke & Back, BrewingScience 2007 | Not matched; volume/page still unrecorded. **Open** |
| FACT-RECIPE-0001 | Oxford Companion to Beer; Palmer *How to Brew* ch. 5 | Not checked. **Open** |
| FACT-RECIPE-0002 | Briess, "Introducing Crystal Red(R) and a Caramel Malt User's Manual" | Chief's evidence ("Briess public material on crystal/caramel malt") names no matching title or URL. **Open** |
| FACT-RECIPE-0002 | Crisp Malt, "Dark Crystal Malt / Crystal 400" | Chief's evidence is the Crisp public malt **handbook**, a different document from this product entry. **Open** |
| FACT-RECIPE-0002 | Castro et al. 2021; Oxford Companion; Palmer ch. 21 | Not checked. **Open** |

The Chief-supplied paper, Oladokun et al., "The impact of hop bitter acid and polyphenol profiles on the perceived bitterness of beer", Food
Chemistry 205 (2016) 212–220, `10.1016/j.foodchem.2016.03.023`, is a **third, different paper**. It is not one of the stored entries, so it was not
matched and not added.

Leads for the next Chief spot-check (search results only, not opened, not recorded in the registry):
- a Briess "Introducing Crystal Red® Malt" page, https://www.brewingwithbriess.com/?p=20059
- a Crisp "Dark Crystal 400" product page, https://crispmalt.com/?p=725

The open spot-check notes on both records remain. The module may use both records because they are `verified`. Closing the spot-check is a
separate Chief action.

**Status update 2026-10-04 (source spot-check follow-up; supersedes the "Open" cells above for the sources named here):**

These source entries were matched to their exact public records and now carry source notes (Local Claude on Chief instruction,
for Chief confirmation):
- FACT-RECIPE-0001: Gastl, Hanke & Back (BrewingScience 60(3/4):48–54, DOI 10.23763/BRSC07-01GASTL), Oladokun 2016 (Food Res.
  Int. 86) and Oladokun 2017 (Food Chem. 230), at abstract level.
- FACT-RECIPE-0002: the Briess "Introducing Crystal Red® and a Caramel Malt User's Manual" page, the Crisp "Dark Crystal Malt |
  Crystal 400" page, and Castro et al. 2021.

**Still open:** the Oxford Companion entries for both records (no edition or medium stored); Palmer *How to Brew* ch. 5
(FACT-RECIPE-0001) and ch. 21 (FACT-RECIPE-0002) (howtobrew.com certificate expired; ch. 21 has no stored URL).

The search leads listed above were not used as evidence. The Briess `?p=20059` lead turned out to be a different post.

### 27.11 Governance

- The module is approved for **implementation-issue creation**. Implementation depends on Måling landing first (§27.8).
- The issue cannot be created while GitHub is unavailable. The paste-ready draft is §28.
- Nothing here marks product implementation as started or complete.
- Status refresh (2026-10-04): the Måling Foundation dependency (§27.8) is satisfied offline; not yet on GitHub/master.

## 28. Implementation issue — draft (create on GitHub when access returns)

Paste the block below as the issue body. Title: **V2.2 Oppskriftsforståelse — Kompetent module (`recipe.fundamentals`)**.

~~~markdown
## Goal

Implement the Bryggeskole module **Oppskriftsforståelse** (`recipe.fundamentals`), exactly as locked in
`docs/development/v22_recipe_understanding_module_contract.md` §27 (Chief review 2026-10-03).

- The module is **entirely Kompetent**, intended for the main App Bryggeskole (scope: Foundation → Kompetent hjemmebrygger).
- Governed by #436 (contract, merged in #437), child of #343 (Roadmap V2.2 Goal 3).
- Facts: #440 (FACT-HOP-0005), #441/#450 (FACT-RECIPE-0001), #442/#451 (FACT-RECIPE-0002), #443/#452 (FACT-RECIPE-0003).

## Dependency (blocking)

- **The Måling og bryggelogg Foundation module (`measurement.fundamentals`) must be merged first.** Do not start implementation before that.
- Smak og evaluering (#472) and Rengjøring og sikkerhet (#473) are also expected merged; the grid order and the `basis` pattern come from them.

## Scope (exact)

New, topic-scoped files following the existing pilot pattern (no shared generalisation):
- `bryggeskole/data/pilot_recipe_fundamentals.json` (`schema_version: 1`, `topic_id: PILOT-RECIPE-FUNDAMENTALS`)
- `bryggeskole/pilot_recipe.py`: verified-only claim resolution via `get_verified_record`, a required `basis` ("fact" | "methodology") per the
  #472 pattern, and its own wording guardrails
- registration in `ui/bryggeskole_panel.py`

**7 chunks, 7 questions, exactly one question per chunk. Every question `difficulty: "beginner"`.** This is item difficulty under the current
schema convention, not the course stage; the module is Kompetent. Do not add a difficulty taxonomy.

### Chunks

| id | basis | content | allowed `source_claims` (only these) |
|---|---|---|---|
| CHUNK-REC-A | fact | Read a recipe as a plan: what base malt, specialty malt, bittering/late hops and yeast are doing, applied without re-teaching Råvarer. Includes the method checkpoint: recipe numbers are predictions/estimates; measurements describe what actually happened | subset of FACT-MALT-0002, FACT-MALT-0004, FACT-HOP-0003, FACT-YEAST-0005 |
| CHUNK-REC-B | fact | OG → fermentability → attenuation → FG → alcohol/body/dryness **tendencies** | subset of FACT-YEAST-0001, FACT-YEAST-0002, FACT-MASH-0001, FACT-MASH-0004, FACT-RECIPE-0002 |
| CHUNK-REC-C | fact | Colour: malt/process origin; EBC as darkness context; colour is not flavour | subset of FACT-MALT-0002, FACT-MALT-0003, FACT-MALT-0004 |
| CHUNK-REC-D | fact | IBU is an index and an estimate, one axis; similar IBU can be perceived differently | FACT-RECIPE-0001 + subset of FACT-HOP-0001, FACT-HOP-0002, FACT-HOP-0005 |
| CHUNK-REC-E | fact | Balance relative to brewer intent; not a universal score; deliberate emphasis can be valid | FACT-RECIPE-0003 |
| CHUNK-REC-F | methodology | Style as a comparison frame; outside a range is not automatically wrong | `[]` |
| CHUNK-REC-G | methodology | Formulation workflow; one deliberate change from an explicit hypothesis/intent; measuring and evaluating are deferred to Måling and Smak | `[]` |

Chunk-specific rules:
- **CHUNK-REC-B:** FACT-MEAS-0001 may only be referenced as a prerequisite ("see Måling og bryggelogg"). It is not cited in `source_claims` and
  OG/FG are not re-defined.
- **CHUNK-REC-A:** the checkpoint sentence is phrased as method, not as a sourced fact.

### Questions

| id | type | basis | concepts | `source_claims` |
|---|---|---|---|---|
| Q-REC-001 | scenario | fact | `malt.base_vs_specialty` (reused from Råvarer) | `["FACT-MALT-0002"]` |
| Q-REC-002 | scenario | fact | `yeast.attenuation` (reused from Råvarer) | `["FACT-YEAST-0002"]` |
| Q-REC-003 | concept_check | fact | `malt.colour_flavour` (reused from Råvarer) | `["FACT-MALT-0003"]` |
| Q-REC-004 | scenario | fact | `recipe.ibu_vs_perceived_bitterness` | `["FACT-RECIPE-0001"]` |
| Q-REC-005 | scenario | fact | `recipe.balance` | `["FACT-RECIPE-0003"]` |
| Q-REC-006 | scenario | methodology | `recipe.style_context` | `[]` |
| Q-REC-007 | scenario | methodology | `recipe.formulation_workflow` | `[]` |

Concept rules:
- Methodology concept allow-list (closed): `recipe.style_context`, `recipe.formulation_workflow`.
- Do **not** create `recipe.one_change`, `recipe.gravity_vs_fermentability`, `recipe.attenuation_chain`, `recipe.alcohol_concept` or
  `recipe.colour_origin`.
- Do **not** use `log.hypothesis_next_change`.
- Reused Råvarer concepts share mastery with Råvarer; they are not duplicated.

### Basis rules

- Each fact claim must be `status: verified` and resolve through the verified-only API.
- `methodology` requires `source_claims == []` and an allow-listed concept. It shows the #472 method caption ("Metode, ikke en faktapåstand" /
  "Method, not a fact claim") and never claims a brewing source.
- No claims outside the per-chunk lists above.
- `modules: ["recipe.fundamentals"]` may be added to the records the module actually cites. This is the only registry change allowed; claims,
  classification, status and sources are unchanged, and registry tests are updated accordingly.

### Content rules (both languages; contract §18 and §27)

- **No re-teaching of Råvarer:** apply ingredient roles to a recipe; do not repeat the ingredient chunks.
- **Måling boundary:**
  - Måling owns OG/FG definitions, measured readings, the planned-vs-actual method and the brew log.
  - Use *forventet / beregnet* and *predicted / calculated* for App values.
  - **Never call App recipe values measured values.**
- **Smak boundary:** no tasting sequence, no faults, no observation-vs-interpretation teaching. Evaluating the result belongs to Smak
  (`sensory.evaluate_against_intent`).
- **BU:GU omitted entirely:** no objective, sentence, question, threshold, visual or Master-view note.
- **Banned claims:**
  - "high OG = automatically sweet", "high OG = automatically strong", "FG = sweetness score"
  - "IBU = perceived bitterness", "same IBU = same bitterness"
  - any direction for alcohol, residual sugar, roast, water or hop character on perceived bitterness
  - "crystal malt makes beer sweet/adds body", or "all specialty malt is less fermentable"
  - "colour = flavour", or an exact EBC prediction
- **Balance:** never "harmonisk", "ideell", "riktig", "perfekt"; balance is not a quality score.
- **Style:** no BJCP numbers, no style memorisation, no style-match % as a quality score; "outside the range" is not wrong.
- **No numbers or formulas:** no ABV, Tinseth/utilisation, EBC/SRM/Lovibond, attenuation, efficiency or BU:GU maths; no numeric bands; no minute
  schedules as rules.
- **Engine limits:** do not claim the engine models mash temperature → FG, specialty-malt fermentability, body, sweetness or balance.

### Placement

Grid order in both environments: … Pakking → Måling og bryggelogg → **Oppskriftsforståelse** → Smak og evaluering. EN card title: "Recipe
understanding". The Hjemmebrygger/Bryggeri chooser stays presentation-only, with one shared lesson set.

### NO/EN

Every chunk, prompt, option and feedback text exists in `no` and `en` with identical keys and structure. Terminology follows contract §19.
Norwegian is the source language.

## Tests

- `tests/test_pilot_recipe.py` (new), mirroring the existing pilot tests and the #472 sensory tests:
  - exactly CHUNK-REC-A..G and Q-REC-001..007, in order; one question per chunk
  - all `beginner`
  - exact basis, concepts and `source_claims` per the tables, with per-chunk claim subsets enforced
  - every fact claim verified; methodology rules (allow-list, empty claims)
  - NO/EN key symmetry
  - wording-trap guards: no BU:GU or "BU:GU" text; no BJCP numbers; no digits as bands or minutes; no "målt"/"measured" applied to App recipe
    values; no forbidden balance words; no `recipe.one_change` or `log.hypothesis_next_change`
- `tests/test_course_fact_registry.py`: record set, claims and status unchanged; only `modules` assertions updated if `modules` is set.
- `tests/test_ui_bryggeskole_panel.py`:
  - grid order with Oppskriftsforståelse between Måling and Smak in both environments
  - NO/EN rendering
  - method caption only on methodology items
- Mastery tests: reused Råvarer concepts record into the same mastery ids, with no duplicates. State isolated via
  `KVERNHAUG_BRYGGESKOLE_STATE_DIR`.
- `tests/playwright_streamlit/module-grid-responsive.spec.js`: card count and `MODUL_TEKST` (NO/EN) updated for the new card. Layout assertions
  unchanged. Chromium + Firefox, desktop + mobile.
- Answer-order tests if `answer_order.py` is used.
- `git diff --check`.

## Owner QA (owner PC)

- NO and EN, both environment choices, desktop and narrow/mobile widths.
- Walk the contract §23 scenario up to the recipe reading and explanations. The recipe-editor steps of §23 belong to the later bridge slice.
- Check:
  - every App value is described as predicted/calculated
  - no BU:GU
  - no numbers or formulas
  - no tasting-method or OG/FG-definition re-teaching
  - methodology captions present
  - mastery recorded
- Chief acceptance follows owner QA.

## Non-goals

- No recipe-editor consequence view or visual bridge (separate later UI slice).
- No recipe-engine, style-engine or style-label change (the BU:GU/"Harmonisk balansert" wording stays a separate App issue). No App calculator,
  Core, schema, Web, `web/en/**` or Sóti change.
- No new Course Fact and no claim/status/source change.
- No BU:GU in any form.
- No Kompetent Måling content and no `log.hypothesis_next_change` consolidation.
- No tasting-method or fault teaching.
- No ingredient, hop or strain encyclopaedia, efficiency or water chemistry, or statistical experiment design.
- No #471 work.
- No scoring, badges, gating or AI-generated interpretation.
~~~

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted in this run; no module, question, UI, bridge or visual implemented; no recipe-engine,
Core or schema change; no gate in §25 decided beyond the Chief decisions listed in §0; no Web/public or Sóti change; no deploy.

v1.1 (2026-10-03, Chief review closure):
- Records the decisions in §27 and the issue draft in §28.
- Refreshes the sections that listed already-merged facts as pending (§3, §4, §5, §20, §21, §24, §25).
- Supersedes the BU:GU one-sentence allowance (§11).
- Course Fact Registry still unchanged: the §27.10 source checks found no matching entry to mark.
- Still no module, UI, engine, Core/schema, Web or Sóti change, and no deploy. No GitHub issue was created.
