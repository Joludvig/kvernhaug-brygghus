# V2.2 — Oppskriftsforståelse (recipe understanding) Kompetent contract

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
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
| Kompetent MUST | Bitterness / IBU as one axis | `recipe.ibu_vs_perceived_bitterness` | FACT-HOP-0001/0003 now; R-2 later |
| Kompetent MUST | Recipe formulation workflow | `recipe.formulation_workflow` | Methodology + FACT-METHOD-0004 |
| Kompetent SHOULD | Colour | `recipe.colour_origin` | FACT-MALT-0002/0003/0004 |
| Kompetent SHOULD | Balance | `recipe.balance` | Methodology now; R-4 later |
| Kompetent SHOULD | Style as reference frame | `recipe.style_context` | Methodology (no fact) |
| Kompetent SHOULD | Change one thing on purpose | `recipe.one_change` | Methodology; G3N/#435 |
| Kompetent SHOULD | Specialty malt fermentability tendency | `recipe.specialty_fermentability` | R-1 later; qualitative until then |
| LATER / Bryggmester | Yeast biochemistry (glycolysis) | — | Kunze §4.1.2 (not for Kompetent) |
| LATER / Bryggmester | Apparent vs real attenuation detail | — | One gloss at most |
| LATER / Bryggmester | Utilisation and Tinseth maths, EBC/SRM/Lovibond conversion, efficiency maths | — | Explicit non-goals (§26) |
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

**Planned, not yet in the registry (dependencies, not reuse today):** #435 measurement M1 (OG/FG definitions), M2, M4; P4 FACT-HOP-0004 and
**FACT-HOP-0005** (alpha % versus IBU).

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
and must land before R-2.

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
- If the course mentions it at all, it is at most **one sentence in the Master view** saying it is a rough App indicator and not a verdict.
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

Reuse G3N / #435 (`log.hypothesis_next_change`): **Learn → Reflect → improve next brew**. No Course Fact and no statistical experiment design.

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
- `recipe.ibu_vs_perceived_bitterness` (R-2 later)
- `recipe.formulation_workflow`, `recipe.one_change`
- `recipe.colour_origin`, `recipe.balance` (R-4 later), `recipe.style_context`, `recipe.specialty_fermentability` (R-1 later)

Existing ids reused in questions: `yeast.attenuation`, `yeast.organism_role`, `yeast.choice_principle`, `mashing.fermentability`,
`mashing.dextrins`, `malt.base_vs_specialty`, `malt.colour_flavour`, `malt.grist_percentage`, `hop.isomerization_time`, `hop.addition_strategy`,
`method.planning_variables`. Questions that assert a fact must carry the id of a verified record; questions on methodology carry the methodology
concept id and no `FACT-*` claim.

## 21. Recommended module structure

Module 9, after Måling og bryggelogg (module 8). About seven Kompetent chunks:

1. **Read a recipe as a plan** — what each row does; the §1 checkpoint.
2. **From OG to FG** — §7 chain; alcohol concept; body/dryness as tendencies.
3. **Colour** — §8.
4. **Bitterness** — §9; IBU as one axis.
5. **Balance** — §10; BU:GU only as the one-sentence Master note (§11).
6. **Style as reference frame** — §12.
7. **Change one thing on purpose** — §13 workflow and one-change; bridge to the recipe editor (§14).

Chunks 2 and 7 need no new facts and can be built first. Chunks 4 and 5 wait for R-2 and R-4 (or ship as clearly limited to the existing facts).
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
2. **Prerequisites** (other issues): #435 measurement M1 and P4 FACT-HOP-0005.
3. **Fact pack R-2** (`recipe.ibu_vs_perceived_bitterness`), sources read live, Chief review.
4. **Fact pack R-1** (`recipe.specialty_fermentability`).
5. **Fact pack R-4** (`recipe.balance`).
6. **Module chunks 2 and 7** on existing facts only.
7. **Chunks 1, 3 (colour) and 6** on existing facts and methodology.
8. **Chunks 4 and 5** after R-2 and R-4 land.
9. **Recipe-editor bridge** (consequence view using the existing engine; verified chunk ids only; no second calculation).

Do not build UI before this contract is reviewed.

## 25. Dependencies / later gates

- **#435 / Måling:** measurement M1 (OG/FG definitions) before this module teaches OG/FG.
- **P4:** FACT-HOP-0005 before R-2 implementation.
- **R-4 depends on R-2.**
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

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted in this run; no module, question, UI, bridge or visual implemented; no recipe-engine,
Core or schema change; no gate in §25 decided beyond the Chief decisions listed in §0; no Web/public or Sóti change; no deploy.
