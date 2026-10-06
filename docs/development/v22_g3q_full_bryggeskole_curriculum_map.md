# V2.2 G3Q — Full Bryggeskole curriculum map from Kunze

Version: 1.3 (2026-10-03: §6.2 canonical course architecture added; 2026-10-04: §6.2.8 App course scope and canonical module order;
2026-10-04: §6.2.9 pointer to the course stage allocation contract)
Status: Curriculum audit — decision/prep document, reviewable, not actionable by itself. §6.1–§6.2 are locked owner
decisions and the canonical source for the Bryggeskole course architecture.
Governed by: [#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3), under the locked product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65). Related: [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358)
(process-oriented journey gap map), [#418](https://github.com/Joludvig/kvernhaug-brygghus/issues/418) (G3P raw-material learning),
[#420](https://github.com/Joludvig/kvernhaug-brygghus/issues/420) / merged PR #421 (current-product inventory).
Authoritative base at creation: `3cdb8f6bd6f8a14b488b7b838a84a35aa87c0862`.

This is a **curriculum audit, not course content**. It contains no teaching text, creates or changes no Course Fact
Registry record, and changes no product code — see [§19 Boundary statement](#193-boundary-statement).

**Kunze is used as the subject-domain / curriculum-index source only.** Nothing in this document promotes a Kunze
statement to verified Kvernhaug truth. Any exact fact needed later must go through visual page verification, the
existing Kvernhaug source hierarchy (#65: Tier A/B/C/D) and Course Fact Registry review.

---

## Contents

1. [Source and reference used](#1-source-and-reference-used)
2. [Kunze chapter/topic map (high level)](#2-kunze-chaptertopic-map-high-level)
3. [Current Bryggeskole coverage (reference to #420)](#3-current-bryggeskole-coverage-reference-to-420)
4. [Domain classification matrix (the full map)](#4-domain-classification-matrix-the-full-map)
5. [Missing-domain matrix](#5-missing-domain-matrix)
6. [Raw-material gap and the #418 relationship](#6-raw-material-gap-and-the-418-relationship)
   - 6.1 [Locked course progression model](#61-locked-course-progression-model)
   - 6.2 [Canonical course architecture and terminology axes](#62-canonical-course-architecture-and-terminology-axes)
7. [Hjemmebrygger — Trinn 1: Foundation](#7-hjemmebrygger--trinn-1-foundation)
8. [Hjemmebrygger — Trinn 2: Kompetent hjemmebrygger](#8-hjemmebrygger--trinn-2-kompetent-hjemmebrygger)
9. [Bryggemester — frivillig fordypning](#9-bryggemester--frivillig-fordypning)
10. [Bryggeri / profesjonell — senere spor](#10-bryggeri--profesjonell--senere-spor)
11. [Safety curriculum](#11-safety-curriculum)
12. [Science-foundation curriculum](#12-science-foundation-curriculum)
13. [Visual / interactive opportunities](#13-visual--interactive-opportunities)
14. [Source and Fact Registry gaps](#14-source-and-fact-registry-gaps)
15. [Recommended module architecture](#15-recommended-module-architecture)
16. [Ordered implementation roadmap](#16-ordered-implementation-roadmap)
17. [Natural homebrewer completion point](#17-natural-homebrewer-completion-point)
18. [One recommended next bounded child issue](#18-one-recommended-next-bounded-child-issue)
19. [Source limitations, unresolved gaps and boundary statement](#19-source-limitations-unresolved-gaps-and-boundary-statement)

---

## 1. Source and reference used

| Item | Value |
|---|---|
| Title | *Technology Brewing and Malting* |
| Author | Wolfgang Kunze (Chapter 11 co-written by Dr Hans-Jürgen Manger) |
| Edition / year | 3rd International Edition, 2004 (VLB Berlin, per owner's source note on #419) |
| File used | Owner's local OCR copy: `C:\Users\jolud\Downloads\793354499-Technology-Brewing-and-Malting-Wolfgang-Kunze OCR.pdf` (read-only; not copied into the repo) |
| Size | 946 PDF pages, all accessible; printed pagination runs to about 949 |
| OCR validation | **PASS WITH LIMITATIONS** (local validation, recorded on #419 on 2026-09-29) |
| Safe for curriculum mapping | **YES** |
| Safe for exact factual extraction without visual page verification | **NO** |

### 1.1 Known OCR and source limitations (locked input)

- Ordinary technical prose and numbered subsection headings are generally usable.
- Tables, formulas, figures, rotated pages and gutter-clipped text are **not** reliably represented by the OCR text.
- OCR can silently change exact values (for example `37%` → `3%`, `to` → `10`, `1` → `|`). Subscripts and superscripts can disappear.
- Several chapter-title banners (chapters 6, 8, 9, 11) exist only in the page image, not in the text layer.
- **SOURCE GAP — PRINTED PAGE NOT PRESENT IN PDF:** printed pages **257, 259, 260** (inside §3.3 Lautering) and
  **649** (inside §5.5.5 Filling of the cans). Nothing in this document infers, repairs or reconstructs their content.

### 1.2 How this document used the source

- **Chapter/section structure and page numbers** (§2) were read **visually** from the book's own table of contents
  page images (PDF pages 8–19, printed pages 7–18), not from OCR text. The OCR text layer of the TOC splits titles
  from page numbers and cannot be trusted for navigation.
- **Topic presence** in the body was confirmed from OCR prose plus keyword search. Where a scope statement below
  relies on body prose, the page was also checked visually. This applies to §8.3 *Hobby brewers*, printed pp. 793 and 796.
- **No numbers, tables or formulas from Kunze are reproduced.** Page references are navigation aids only.
- Page references are **printed/book page numbers**. To open them in the PDF: printed ≤ 256 → PDF = printed + 1;
  printed 258 → PDF 258; printed 261–648 → PDF = printed − 2; printed ≥ 650 → PDF = printed − 3.

---

## 2. Kunze chapter/topic map (high level)

Concise paraphrase of the book's structure. The Kunze numbering is kept so any topic can be found again.
"HB relevance" is this audit's judgement for a homebrewer curriculum. It is not a Kunze statement.

| Ch. | Kunze title (printed pp.) | Main sections (paraphrased, printed page) | HB relevance |
|---|---|---|---|
| — | Beer – the oldest drink for the common man (19–31) | History and development of beer and brewing | Context only |
| 1 | Raw materials (32–97) | 1.1 Barley: types, cultivation, kernel structure, composition, evaluation (32–49) · 1.2 Hops: regions, harvesting, cone structure, bitter substances/oil/polyphenols, evaluation, varieties, hop products (49–67) · 1.3 Water: water cycle, brewery use, sourcing, treatment, brewing-water ions, residual alkalinity (67–83) · 1.4 Yeast: cell structure, metabolism, multiplication, characterisation of brewing yeasts (83–90) · 1.5 Adjuncts: maize, rice, barley, sorghum, wheat, sugar, glucose syrup, colouring sugar (90–95) | **Core** (ingredient understanding); evaluation/agronomy → later |
| 2 | Malt production (97–194) | Intake/cleaning/transport of barley; drying/storage; steeping; germination; kilning incl. colour/flavour formation (Maillard), DMS precursor, enzyme inactivation (158–172); malt treatment; malt yield/evaluation (174–179); special malts: Pilsner, Munich, Vienna, melanoidin, caramel, acid, smoked, roasted, wheat, malt extract, other cereals, malt usage per beer type (179–186); safety in malting (187) | Special malts + "what kilning does" = **core**; malting technology = professional/optional |
| 3 | Wort production (195–367) | 3.1 Milling: dry/wet milling, grist evaluation (196–214) · 3.2 Mashing: enzymes, starch and β-glucan degradation, extract composition, acidification, mash vessels, mashing-in, infusion/decoction/special processes, control of mashing (214–255) · 3.3 Lautering: first/second wort, last runnings, lauter tun, mash filter, spent grains (255–281) · 3.4 Wort boiling: hop extraction/isomerisation, protein-phenol precipitation, evaporation, sterilisation, enzyme destruction, pH lowering, kettle design, performing boil incl. hop addition, monitoring wort (281–323) · 3.5 Brewhouse yield (323–331) · 3.6 Brewhouse equipment incl. pub/research brewhouses (331–336) · 3.7–3.8 Casting, coarse break removal, whirlpool (336–347) · 3.9 Cooling/clarifying wort, cold break, aeration (347–357) · 3.10 Control of wort production (357) · 3.11 Safety at work in wort production (359) | **Core** process spine; kettle/plant engineering → professional |
| 4 | Beer production — fermentation, maturation, filtration (367–532) | 4.1 Changes during fermentation/maturation: yeast metabolism, by-products (diacetyl, aldehydes, higher alcohols, esters, sulphur compounds, organic acids), pH/redox/colour/CO₂/colloidal changes, flocculation (367–386) · 4.2 Pure yeast culture propagation (386–395) · 4.3 Conventional fermentation/maturation: pitching, fermentation management, attenuation, transfer, maturation, CO₂ saturation, clarification, lagering (395–416) · 4.4 Cylindroconical vessels: fermentation schemes incl. pressure fermentation, yeast cropping, CO₂ recovery (416–453) · 4.5 Filtration (453–487) · 4.6 Stabilisation: microbiological, colloidal, flavour stability (487–507) · 4.7 Carbonation (507) · 4.8 Special methods: high gravity, ice beer, alcohol removal (509–523) · 4.9 Accident prevention: fermentation CO₂, pressure vessels, kieselguhr (523–532) | Fermentation management, by-products, maturation, carbonation, CO₂ safety = **core**; tank/filtration/propagation engineering → professional/advanced |
| 5 | Filling the beer (532–716) | Returnable glass bottles, bottle washing, filling, closing, pasteurising, labelling; non-returnable glass; PET; returnable plastic; cans (641–669; **SOURCE GAP p. 649**); casks/kegs incl. keg fittings and cleaning (669–679); transport/packaging/palletising; filling plant; beer losses (709–712) | Bottle/keg principles, oxygen pick-up and pressure concepts = **core**; filling lines = professional |
| 6 | Cleaning and disinfection (716–732) | Materials vs cleaning agents; cleaning agents; disinfection agents; CIP; cleaning procedure; mechanical cleaning; monitoring cleaning; protection at work | Cleaning vs disinfection, procedure, chemical protection = **core**; CIP = professional |
| 7 | Finished beer (732–786) | 7.1 Composition, beer and health (732–737) · 7.2 Taste and foam (737–742) · 7.3 Beer types: top/bottom fermentation types, trends outside the Reinheitsgebot (742–761) · 7.4 Quality examination: beer tasting, microbiological examination, beer analysis (original gravity, distillation/refraction analysis, colour, pH, oxygen, diacetyl, foam, CO₂, bitterness units, haze, filterability) (761–776) · 7.5 Process measurement technology: temperature, flow, level, density, haze, oxygen, pH, conductivity, pressure, optical (776–781) | Tasting, styles-as-context, measurement *concepts* = **core**; lab analysis, formal panels, inline instrumentation = professional |
| 8 | Small scale brewing (786–798) | 8.1 Pub breweries (786–792) · 8.2 Microbrewers (792) · 8.3 Hobby brewers: sourcing ingredients, making your own malt, a compact home brewing walkthrough (793–797) | **Directly relevant**; see §6 and §14 on scope/dating |
| 9 | Waste disposal and the environment (798–812) | Environmental legislation, waste water, residues (spent grains, break, yeast, kieselguhr, labels, glass, cans), emissions, PET recycling | Professional (homebrew: spent-grain disposal only) |
| 10 | Energy management in brewery and maltings (812–869) | Energy requirements, boilers/steam, refrigeration, electrical equipment/safety, pumps, fans, compressed air | Professional |
| 11 | Automation and plant planning (869–921) | Measurement/control requirements incl. measurement uncertainty; plant planning; plant design, piping, contamination-free design, CIP stations, chemical storage | Professional; the measurement-uncertainty idea is a Level 2 concept |
| — | Back matter (922–) | Abbreviations, unit conversion, advertisers, diagrams, literature references, index | Navigation only |

What the book is **not**: it is an industrial brewing and malting textbook. It has no dedicated treatment of recipe
formulation, flavour balance or homebrew equipment methods (BIAB, traditional all-grain in one's own kettle, all-in-one
machines). Where this map places those topics, that is a **Kvernhaug curriculum decision**, not something taken from Kunze.

---

## 3. Current Bryggeskole coverage (reference to #420)

The authoritative current-product truth is
[`v22_g3q_current_bryggeskole_coverage_inventory.md`](v22_g3q_current_bryggeskole_coverage_inventory.md) (#420, PR #421).
This document does not repeat its detail. In summary:

| Surface (per #420) | What exists |
|---|---|
| Structured modules | Six process modules: Forberedelse/metode, Mesking, Koking/humle, Kjøling/overføring, Gjæring, Pakking. 27 chunks, 29 questions, NO/EN, hidden mastery |
| Course Fact Registry | 30 records: 29 `verified`, 1 `draft` (`FACT-MASH-0003`, iodine test, unused) |
| Learn→Plan bridges | Mesking → process panel; Gjæring → yeast panel; Koking/humle → hop panel |
| Learn→Reflect | Static i18n bridge in Brew History (`_render_laer_bro`); not registry-backed by design (G3N) |
| App tools without teaching | Recipe engine (OG/IBU/EBC/ABV), BJCP match, water/salts, process profiles, brew-day plan, Brew History, ABV calculator |
| Static help | 12 Web hjelp pages × NO/EN, unlinked to registry ids |

This audit **re-labels coverage using the #419 vocabulary** (complete / partial / absent). It judges coverage
against what each domain needs at its *homebrewer level*, not against #420's descriptive labels. The judgement
rules are:

- **complete** — the domain's MUST/SHOULD scope for its level is taught in a structured module with verified facts;
- **partial** — some of that scope is taught, or it is taught only qualitatively where the level needs more;
- **absent** — not taught in Bryggeskole. An App tool, Web help page or passing mention does not count.

---

## 4. Domain classification matrix (the full map)

Legend:

- **Cov.** C complete · P partial · A absent.
- **Location** M module · B bridge · BH Brew History · SH static help · AT App tool · — nowhere.
- **HB level** MUST · SHOULD · OPT (optional/advanced). A level number (L1–L4) marks where the topic lands in §7–§10:
  L1 = Foundation, L2 = Kompetent hjemmebrygger, L3 = Bryggemester, L4 = Bryggeri / profesjonell (§6.2.2).
- **Pro** yes / no — whether the topic continues into a professional track.
- **Facts** S sufficient · P partial · M missing, judged against the recommended homebrewer scope.
- **Vis.** H high · M medium · L low visual/interactive value.
- **Kunze** printed page references from the TOC.

### 4.1 Raw materials

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D01 | Malt / grain: what malt is, base vs specialty, colour/flavour contribution, extract role | 1.1 (32–49); 2.5.1 (158–162); 2.8 (174–179); 2.9 (179–186) | A | AT (malt panel); M incidental (enzymes in Mesking) | MUST (L1 basic, L2 recipe use) | yes | M | H | — | #418 contract; then a malt fact pack |
| D02 | Hops: bitterness vs aroma roles, alpha acid concept, forms, variety choice, freshness | 1.2 (49–67); 3.4.3 (319–322) | P | M (Koking/humle), B (hop panel), SH | MUST | yes | P (HOP-0001…0003) | M | — | #418; add hop-as-ingredient facts |
| D03 | Yeast as organism: ale vs lager, attenuation/flavour role, forms (dry/liquid) | 1.4 (83–90); 4.1.1 (367) | P | M (Gjæring, temperature only), B, SH | MUST | yes | P (BREW-0001…0003) | M | — | #418 |
| D04 | Water as ingredient: majority ingredient, source water | 1.3.1–1.3.3 (67–72) | A | AT (water panel), SH (advanced) | MUST (L1) | yes | M | L | — | #418 |
| D05 | Adjuncts / other fermentables (sugars, unmalted cereals, adjunct mashing) | 1.5 (90–95); 3.2.4 special mashing (247–254) | A | — | SHOULD (L2 concept); cereal cooking OPT (L3) | yes | M | L | D01, D17 | L2 short unit after #418 |
| D06 | Malting process, incl. home malting | 2 (97–194); 8.3 "Making your own malt" (793–795) | A | — | OPT (L3); "what malting/kilning does" folded into D01 | yes | M | M | D01 | Only the D01 basics now; park the rest |

### 4.2 Recipe / brewing theory

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D07 | Extract / gravity (OG, what gravity measures) | 3.5.1 (323–330); 7.4.3 original gravity (767) | A | AT (OG calc; OG/FG in BH) | MUST (L1 concept, L2 use) | yes | M | H | D01 | Measurement & records module (§15) |
| D08 | Attenuation / fermentability | 4.3.3 attenuation (403); 3.2.1 (214–230) | A | AT (ABV) | MUST (L2) | yes | M (MASH-0001/0002 touch fermentability) | H | D07, D03, D17 | Fermentation expansion + recipe module |
| D09 | Alcohol formation and ABV concept | 4.1.2 (369–375); 7.4.3 distillation analysis (769) | A | AT (ABV calculator) | MUST (L2 concept) | yes | M | M | D07, D08 | Recipe module |
| D10 | Colour (EBC concept, where colour comes from) | 2.5.1 Maillard (159); 4.1.4 colour change (383); 7.4.3 colour (771) | A | AT (EBC) | SHOULD (L2) | yes | M | H | D01 | Recipe module |
| D11 | Bitterness (IBU concept, what drives it) | 1.2.4 (54); 3.4.1 (282); 7.4.3 bitterness units (774) | P (qualitative isomerisation only) | M, AT (IBU) | MUST (L2) | yes | P (HOP-0001) | M | D02, D21 | Recipe module |
| D12 | Balance (malt/bitterness/body/sweetness interplay) | No dedicated Kunze section found; nearest 7.2.1 beer flavour (737) | A | — | SHOULD (L2) | no | M | M | D07–D11 | Needs non-Kunze sources; recipe module |
| D13 | Beer styles as practical context | 7.3 (742–761) | A | AT (BJCP match) | SHOULD (L2, context not memorisation) | yes | M | L | D07–D11 | Recipe module; reuse BJCP data without teaching claims from it |
| D14 | Recipe formulation (turning a target into a grist/hop/yeast plan) | Not a Kunze chapter; nearest 2.9.16 malt usage per beer type (186) | A | AT (recipe engine) | MUST (L2) | yes | M | H | D01–D04, D07–D13 | Recipe module + Learn→Plan bridge to recipe editor |

### 4.3 Brewing process

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D15 | Preparation / method / equipment (BIAB, traditional, all-in-one) | 3.6 brewhouse equipment (331–336); 8.3 (793–797). Homebrew method framing is **not** from Kunze | C for method choice | M (Forberedelse/metode), AT (equipment), SH | MUST (L1) | yes | S (METHOD-0001…0005) | M | — | Keep; later bridge to equipment panel |
| D16 | Milling / crush | 3.1 (196–214) | A | — | SHOULD (L2) | yes | M | M | D01 | Fold into Mesking expansion |
| D17 | Mashing | 3.2 (214–255) | P | M, B (process panel), AT | MUST (L1 concept, L2 control) | yes | P (MASH-0001/0002/0004; MASH-0003 draft) | H | D01 | Mesking expansion; second source for MASH-0003 (§14) |
| D18 | Lautering / sparging / grain separation | 3.3 (255–281) — **SOURCE GAP pp. 257, 259–260** | A (layout only via METHOD-0001/0002) | M incidental, AT (sparge field) | MUST (L2, method-aware) | yes | P | M | D15, D17 | Mesking expansion ("mash & separate") |
| D19 | Wort collection (first wort, runnings, pre-boil check) | 3.3.1 (255); 3.3.2 (257 — **SOURCE GAP**); 3.4.4 monitoring wort (322) | A | — | SHOULD (L2) | yes | M | M | D18, D39, D40 | Mesking expansion |
| D20 | Boiling | 3.4 (281–323) | C (L1 qualitative) | M | MUST (L1) | yes | S (BOIL-0001…0004) | M | D17 | Keep; re-source BOIL-0001/0003 directly (§14) |
| D21 | Hop use / timing | 3.4.3 (319–322) | C (qualitative) | M, B (hop panel) | MUST (L1) | yes | S qualitative; M quantitative | H | D02, D20 | Keep; interactive timeline later (§13) |
| D22 | Whirlpool / hopstand | 3.8.3 whirlpool (337–341) — Kunze frames whirlpool as **trub separation** | P | M | SHOULD (L2) | yes | P (HOP-0002/0003) | M | D21 | Keep; note framing difference (§14.4) |
| D23 | Cooling (incl. hot/cold break) | 3.8 (336–347); 3.9.1–3.9.2 (347–352) | C (L1) | M | MUST (L1) | yes | S (COOL-0001…0003) | M | D20 | Keep; add bridge later |
| D24 | Transfer | 3.9.5 (356); 4.3.3 beer transfer (406); 4.3.7 (412) | C (L1) | M | MUST (L1) | yes | S (TRANSFER-0001, OXY-0002) | L | D23 | Keep |
| D25 | Oxygenation / aeration of wort | 3.9.3 (353–355) | C (L1, conditional) | M | MUST (L1) | yes | S (OXY-0001…0003) | M | D03 | Keep |
| D26 | Fermentation process: pitching, phases, monitoring | 4.1 (367–386); 4.3.3 (399–409) | P (temperature only) | M, B (yeast panel) | MUST (L1 basics, L2 management) | yes | P | H | D03, D07 | Fermentation expansion |
| D27 | Conditioning / maturation ("why wait") | 4.1.3 by-products incl. diacetyl (375–382); 4.3.5 (409–411); 4.4.3 (436–443) | A (PACK-0004 mentions time only) | SH | MUST (L2) | yes | M | M | D26 | Fermentation expansion |
| D28 | Clarification (break, cold conditioning, finings concept, haze) | 4.3.5 clarification (410); 4.6.2 colloidal stability (493–501); 4.5 filtration (453–487, professional) | A | SH only | SHOULD (L2 concept); filtration → L4 | yes | M (BOIL-0003/COOL-0002 cover break only) | L | D23, D27 | Short L2 unit (Pakking or fermentation expansion) |
| D29 | Carbonation | 4.3.5 CO₂ saturation (409); 4.7 (507); 7.4.3 CO₂ (774) | C (L1 qualitative) | M, SH | MUST (L1) | yes | S qualitative; M quantitative | M | D26 | Keep; quantitative priming = L2 candidate |
| D30 | Packaging (bottle/keg, pressure, oxygen pick-up) | 5.6 kegs (669–679); 5.1.7 oxygen in bottle neck (597); 8.3 bottling (796–797) — **SOURCE GAP p. 649** (cans; not homebrew-relevant) | C (L1) | M | MUST (L1) | yes | S (PACK-0001…0004) | L | D29 | Keep; add bridge later |

### 4.4 Cleaning, sanitation and safety

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D31 | Cleaning vs sanitation (disinfection): the difference, order, procedure | 6.1–6.7 (716–731) | P (boundary only: COOL-0003) | M (Kjøling/overføring) | MUST (L1) | yes | P | H | — | **Next child issue (§18)** |
| D32 | Contamination / infection concepts (spoilage organisms, why hot side vs cold side differ) | 4.6.1 (487–493); 7.4.2 (763–766); 8.3 (796) | P (COOL-0001/0003 concept) | M | MUST (L1 concept); detail L3 | yes | P | M | D31 | With D31 |
| D33 | Chemical handling (cleaners/sanitisers, caustic, storage, PPE) | 6.8 (731); 11.3.9 chemical warehouse (918) | A | — | MUST (L1) | yes | M | L | D31 | With D31; product labels/SDS are the Tier A sources, not Kunze |
| D34 | Heat / burn / boil-over hazards | 3.11 (359–367) | P (BOIL-0004 boil-over) | M | MUST (L1) | yes | P | L | — | Safety unit (§11) |
| D35 | Pressure and CO₂ safety (sealed containers, fermentation CO₂ in enclosed spaces) | 4.9.1 fermentation CO₂ (523); 4.9.2 pressure vessels (524); 11.3.4 (895–898) | P (PACK-0003) | M | MUST (L1) | yes | P (no CO₂-asphyxiation record) | L | D29 | Safety unit (§11) |
| D36 | Oxygen exposure after fermentation (oxidation, flavour stability) | 4.6.4 (504–507); 5.1.7 (597) | C (L1) | M | MUST (L1) | yes | S (OXY-0002/0003) | M | D24 | Keep |
| D37 | Electrical safety (electric kettles / all-in-one units) | 10.4.4 (846) — industrial only | A | — | SHOULD (L1) | no | M | L | D15 | Needs non-Kunze Tier A (manufacturer/standards) |

### 4.5 Measurement and control

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D38 | Temperature measurement (where and when to measure, instrument check) | 7.5.1 (776) | A (concept only) | AT (BH actuals) | MUST (L1) | yes | M | M | — | Measurement & records module |
| D39 | Gravity measurement: hydrometer/saccharometer, refractometer concept, alcohol effect on refractometer | 3.5.1 (323–330); 7.4.3 refraction analysis (769); 7.5.4 density meters (778) | A | AT (OG/FG entry, ABV calc) | MUST (L2) | yes | M | H | D07 | Measurement & records module |
| D40 | Volume measurement (hot vs cold volume, losses) | 3.5.1 volume conversion (329); 5.9 beer losses (709–712) | A | AT | SHOULD (L2) | yes | M (METHOD-0004 planning context) | M | D15 | Measurement & records module |
| D41 | pH (concept; measurement) | 3.2.1 acidification (214–230); 3.4.1 (286); 4.1.4 (382); 7.4.3 (771); 7.5.7 (779) | A | — | SHOULD (L2 concept); measurement OPT (L3) | yes | M | L | D51 | L2 concept with water; meter use L3 |
| D42 | Pressure measurement (gauges, regulators) | 4.3.7 pressure regulation (412); 7.5.10 (780) | A | — | OPT (L3: kegging / pressure fermentation) | yes | M | L | D35 | Later |
| D43 | Calibration / measurement error | 11.1.2 measurement uncertainty (869) | A | — | SHOULD (L2) | yes | M | L | D38, D39 | Measurement & records module |
| D44 | Record keeping (brew log, planned vs actual) | 3.10 (357); 8.3 notes (797 — gutter-clipped, **OCR UNCERTAIN** wording) | P | BH, AT, Learn→Reflect bridge | MUST (L2) | yes | n/a (methodology, G3N) | M | D38–D40 | Bridge measurement teaching into Brew History actuals |

### 4.6 Yeast and fermentation management

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D45 | Pitching and viability (enough healthy yeast; follow producer guidance) | 4.3.3 pitching (399); 4.4.4 yeast crop monitoring (443–447) | A | — | MUST (L2 concept) | yes | M (OXY-0001 touches yeast state) | L | D03 | Fermentation expansion |
| D46 | Temperature control | 4.3.3 (399–406); 4.4.3 (436–443) | C (L1) | M, B | MUST (L1) | yes | S (BREW-0001…0003) | M | D03 | Keep |
| D47 | Flavour development / by-products (esters, higher alcohols, diacetyl, sulphur, acetaldehyde) | 4.1.3 (375–382) | P (BREW-0002: temperature → flavour) | M | SHOULD (L2) | yes | P | M | D26 | Fermentation expansion; link to faults (D54) |
| D48 | Fermentation completion (stable gravity, not "bubbles stopped") | 4.3.3 attenuation (403–406) | A | — | MUST (L2) | yes | M | H | D39, D26 | Fermentation expansion |
| D49 | Yeast harvesting / reuse / propagation | 4.2 (386–395); 4.4.4 (443–447) | A | SH (gjærhøsting) | OPT (L3) | yes | M | L | D45 | Park (L3) |
| D50 | Pressure fermentation / advanced schemes | 4.4.3 (436–443) | A | SH (trykkgjæring) | OPT (L3) | yes | M | L | D35, D42 | Park (L3) |

### 4.7 Water

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D51 | Mash pH as a concept | 3.2.1 acidification of mash and wort (214–230) | A | — | SHOULD (L2) | yes | M | M | D04, D17 | #418 (concept only) |
| D52 | Chlorine / chloramine in source water | 1.3.4 treatment (72–76); 8.3 (793: chlorinated tap water flagged as a flavour risk — visually checked) | A | AT/SH | MUST (L1) | no | M | L | D04 | #418. **Chloramine was not found in the Kunze OCR** — needs another source |
| D53 | Ions / minerals / residual alkalinity / treatment | 1.3.5–1.3.6 (76–83) | A | AT (water panel), SH (vannkjemi) | OPT (L3) | yes | M | L | D51 | Park (L3); no mandatory advanced water chemistry (#418) |

### 4.8 Sensory and quality

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D54 | Common faults at beginner level (e.g. diacetyl, DMS, oxidation, light-struck, sour/infection) | 4.1.3 (375–382); 4.6.4 (504–507); 7.4.1 tasting (761–763) | P (DMS = BOIL-0002, oxidation = OXY-0002, as process facts, not as a fault curriculum) | M incidental, SH (sensorikk) | MUST (L2) | yes | P | M | D47, D55 | Sensory & evaluation module |
| D55 | Sensory basics: appearance, aroma, flavour, mouthfeel; observation vs interpretation | 7.2 taste and foam (737–742); 7.4.1 (761) | A | SH, BH (sensing form) | MUST (L2) | yes | M | H | — | Sensory & evaluation module |
| D56 | Outcome evaluation → deliberate next change | Kunze 7.4 is lab/QC-oriented; the homebrew loop is Kvernhaug methodology (G3N, #343 Goal 2) | P | BH, Learn→Reflect bridge | MUST (L2) | no | n/a (methodology) | M | D44, D55 | Tie to sensory module; no new facts needed |
| D57 | Foam / head retention | 7.2.2 (740); 7.4.3 foam stability (773) | A | — | OPT (L3); one L2 sentence in science | yes | M | L | D63 | Later |
| D58 | Shelf life / flavour stability | 4.6.4 (504–507) | P (OXY-0002) | M | SHOULD (L2 brief) | yes | P | L | D36 | Fold into Pakking |

### 4.9 Science foundations

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D59 | Enzymes / starch conversion | 2.4.1 enzyme formation (137); 3.2.1 (214–230) | P | M | MUST (L1 concept) | yes | P (MASH-0001) | H | D01 | Mesking expansion |
| D60 | Isomerisation | 1.2.4 (54); 3.4.1 (282) | C (L1) | M | MUST (L1) | yes | S (HOP-0001) | M | D02 | Keep |
| D61 | Yeast metabolism (sugar → alcohol + CO₂ + flavour compounds) | 1.4.2 (86–87); 4.1.2 (369–375) | A | — | SHOULD (L2 concept); detail L3 | yes | M | M | D03 | Fermentation expansion |
| D62 | Oxidation chemistry | 4.1.4 redox (383); 4.6.4 (504–507) | P | M | SHOULD (L2 concept) | yes | P | L | D36 | Fold into Pakking / faults |
| D63 | Protein / polyphenol / haze | 3.4.1 (283); 4.6.2 (493–501) | P (hot/cold break) | M | SHOULD (L2) | yes | P (BOIL-0003, COOL-0002) | L | D20, D23 | With D28 |
| D64 | Maillard reactions / colour and flavour formation | 2.5.1 (159) | A | — | SHOULD (L2, with D10) | yes | M | M | D01 | With D01/D10 |
| D65 | Carbonation / CO₂ science | 4.1.4 CO₂ content (384); 4.7 (507) | C (L1) | M | MUST (L1) | yes | S (PACK-0001/0002) | M | D29 | Keep |

(Microbiology science is covered by D32; foam science by D57.)

### 4.10 Additional domains revealed by Kunze

| ID | Domain | Kunze | Cov. | Location | HB level | Pro | Facts | Vis. | Dependencies | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|
| D66 | Brewhouse yield / efficiency and beer losses | 3.5 (323–331); 5.9 (709–712) | A | AT (efficiency inside recipe engine) | SHOULD (L2 concept); calculation L3 | yes | M | M | D07, D40 | Measurement & records or recipe module |
| D67 | Special methods: high gravity, ice beer, low/no alcohol | 4.8 (509–523) | A | SH (sterke øl) | OPT (L3) | yes | M | L | D26 | Park |
| D68 | Beer composition and health | 7.1 (732–737) | A | — | OPT (context) | no | M | L | — | Park. Any health statement needs Tier A sources |
| D69 | Brewing history / beer culture | Intro (19–31) | A | — | OPT (context) | no | M | L | — | Park |
| D70 | Pub / micro brewing | 8.1–8.2 (786–792) | A | "Bryggeri" environment = labels only (#420) | L4 | yes | M | M | — | Park (professional track) |
| D71 | Barley agronomy, hop growing regions, raw-material evaluation | 1.1.2, 1.1.5, 1.2.1–1.2.2, 1.2.5 | A | — | OPT (L3 context) | yes | M | L | D01, D02 | Park |

### 4.11 Professional / brewery domains (identified, outside homebrewer completion)

| ID | Domain | Kunze | Cov. | HB level | Pro | Note |
|---|---|---|---|---|---|---|
| D72 | Brewery process engineering (kettles, heating systems, lauter tun and mash filter engineering, CCV design, fermentation cellar layout) | 3.4.2 (289–319); 3.3.3–3.3.4 (257–278, SOURCE GAP 257/259–260); 4.3–4.4 (395–453) | A | L4 | yes | Professional track |
| D73 | Filtration and industrial stabilisation (kieselguhr, sheet, membrane, PVPP, pasteurisation) | 4.5–4.6 (453–507) | A | L4 | yes | Pasteurisation concept may be L3 context |
| D74 | Commercial packaging (bottle washing, filling lines, PET, cans, keg lines, palletising) | 5 (532–716) — SOURCE GAP 649 | A | L4 | yes | — |
| D75 | CIP systems and industrial cleaning design | 6.4 (721); 11.3.8 (917) | A | L4 | yes | — |
| D76 | Process measurement instrumentation (flow, level, conductivity, inline DO, optical) | 7.5 (776–781) | A | L4 | yes | DO instrumentation per #65 "later depth" |
| D77 | Professional QC / lab analysis (beer analysis methods, malt/barley/hop evaluation) | 7.4.2–7.4.3 (763–776); 2.8 (174–179); 1.1.5; 1.2.5 | A | L4 (some L3) | yes | — |
| D78 | Advanced yeast lab (pure-culture isolation, propagation plants) | 4.2 (386–395) | A | L4 (L3 for simple starters) | yes | — |
| D79 | Formal sensory panels | 7.4.1 (761) | A | L4 | yes | — |
| D80 | Environment / waste | 9 (798–812) | A | L4 (spent-grain disposal = L1 footnote) | yes | — |
| D81 | Energy / utilities (steam, refrigeration, electrical supply, pumps, compressed air) | 10 (812–869) | A | L4 | yes | — |
| D82 | Automation and plant planning | 11 (869–921) | A | L4 | yes | — |
| D83 | Recipe / statistical experiment design | Not a Kunze topic | A | L3/L4 | yes | #343 PARKs a statistics/experiment platform; the Goal 2 loop covers the homebrew need |

---

## 5. Missing-domain matrix

All domains classified **absent**, grouped by where they belong. Only the first two groups affect homebrewer completion.

| Group | Absent domains | Why it matters | Where it lands |
|---|---|---|---|
| **Blocks Level 1** (safe first brew) | D01 malt basics, D04 water basics, D52 chlorine, D33 chemical handling, D38 temperature measurement; plus the partial D31 cleaning vs sanitation, D34 heat, D35 CO₂/pressure | A learner cannot brew safely or understand the ingredients without them | Råvarer (#418) + Rengjøring & sikkerhet (§18) + Måling |
| **Blocks Level 2** (deliberate improvement) | D07 gravity, D08 attenuation, D09 alcohol, D10 colour, D12 balance, D13 styles, D14 recipe formulation, D16 milling, D18 lautering, D19 wort collection, D27 conditioning, D28 clarification, D39 gravity measurement, D40 volume, D43 calibration, D45 pitching, D48 fermentation completion, D51 mash pH, D55 sensory basics, D61 yeast metabolism, D64 Maillard, D66 efficiency; plus D05 adjuncts (short concept) | Without these a learner can follow a recipe but cannot formulate, measure, judge or improve one | Recipe, Measurement & records, Mesking/Gjæring expansion, Sensory |
| **Bryggemester / frivillig fordypning** | D06 malting, D41 pH measurement, D42 pressure measurement, D49 yeast reuse, D50 pressure fermentation, D53 water chemistry, D57 foam, D67 special methods, D71 agronomy/evaluation | Deeper control for motivated learners | Optional tracks |
| **Bryggeri / profesjonell / context** | D68–D70, D72–D83 | Professional or background | Park |

**Book-derived domains that the #419 checklist did not name:** malting process (D06), brewhouse yield and losses (D66),
flavour stability/shelf life (D58), special methods (D67), beer and health (D68), history (D69), pub/microbrewing (D70)
and raw-material evaluation (D71). Of these, only **D66 efficiency** (L2 concept) and **D58 shelf life** (L2 brief)
affect homebrewer completion.

---

## 6. Raw-material gap and the #418 relationship

- Kunze opens with raw materials. Chapter 1 covers barley, hops, water, yeast and adjuncts, and Chapter 2 covers malt
  (including special malts, 2.9). That confirms #418's premise: raw-material learning is a **foundational subject domain,
  not a side topic** of the process spine.
- The Kunze §8.3 *Hobby brewers* section (793–797) also starts from sourcing the four ingredients before any process
  step. A homebrew curriculum should therefore introduce the ingredients **before or alongside** the process spine.
  It should not come after it.
- **#418 scope is endorsed as is.** This map adds three boundary recommendations for the #418 contract:
  1. **Malt (D01):** include "what malting and kilning do" as a two-sentence concept (base vs specialty, and where colour
     and flavour come from, D64). Malting technology (D06) stays L3.
  2. **Water (D04, D51, D52):** L1 = majority ingredient + chlorine/chloramine risk. L2 = mash pH as a concept. Ions and
     residual alkalinity (D53) stay optional L3, consistent with #418's non-goals. Kunze mentions chlorinated water but the
     OCR showed no chloramine coverage, so the chloramine claim needs a non-Kunze source.
  3. **Adjuncts (D05):** not in #418's four-ingredient scope. Add a one-unit L2 concept later ("other fermentables and
     what they change"). Do not grow #418 for it.
- **Recommended structure:** one combined **Råvarer** module with four short ingredient sections. Four separate modules
  would add navigation cost without adding learning value. #418 decides the final structure.
- **Dependency:** D01–D04 feed D07–D14 (recipe theory). Recipe teaching should not start before Råvarer exists.

---

## 6.1 Locked course progression model

Owner decision, 2026-09-29:

The course should use a **progressive three-track model** with a deliberately low first threshold:

1. **Hjemmebrygger**
   - contains both the Foundation and Competent stages;
   - the first threshold must be easy enough that a beginner can get moving without facing the whole brewing discipline at once;
   - learning should build step by step from safe first-brew understanding toward independent recipe, measurement, evaluation and improvement skills;
   - completion of the Competent stage is the natural, satisfying homebrewer finish point.

2. **Bryggemester**
   - voluntary advanced-homebrewer depth after Hjemmebrygger completion;
   - for learners who want tighter process control, deeper science and more advanced methods;
   - not required to feel that the course is complete.

3. **Bryggeri / profesjonell**
   - separate later track for industrial/professional depth;
   - never required for homebrewer or Bryggemester completion.

The product principle is:

> **Low first threshold, gradual mastery, unlimited depth by choice.**

A learner should never be forced to absorb the entire subject before getting the satisfaction of successful progress, while a motivated learner must be able to continue all the way into advanced and professional depth.

"Bryggemester" is a **Kvernhaug curriculum track name**, not a claim of formal certification, professional licence or protected qualification.

---

## 6.2 Canonical course architecture and terminology axes

Owner decision, 2026-10-03, updated 2026-10-04 in §6.2.3, §6.2.4 and §6.2.8 (recorded offline during the GitHub outage; see the
sync note in §6.2.7).
This section is the **canonical home** for the Bryggeskole course architecture. Other documents point here instead of
restating it.

### 6.2.1 Scope

This decision concerns **only the Bryggeskole course**. The Kvernhaug App remains the brewing tool/product as it is;
nothing here redesigns the App, its tabs or its non-course features.

### 6.2.2 Course progression (unchanged from §6.1)

The 2026-09-29 progression in §6.1 stays canonical:

| Course track | Stage | Role |
|---|---|---|
| **Hjemmebrygger** | Trinn 1: **Foundation** | Deliberately low first threshold; safe first brew. Checkpoint, not completion |
| **Hjemmebrygger** | Trinn 2: **Kompetent hjemmebrygger** | The natural homebrewer completion point |
| **Bryggemester** | — | Voluntary advanced-depth track after Hjemmebrygger completion |
| **Bryggeri / profesjonell** | — | Separate later track; never required |

Principle: **Low first threshold. Gradual mastery. Unlimited depth by choice.**

There is **no five-level course model**. Where this document uses the shorthand L1–L4 (§4–§5), it means the four stages
above, in order: L1 = Foundation, L2 = Kompetent hjemmebrygger, L3 = Bryggemester, L4 = Bryggeri / profesjonell.

### 6.2.3 The course is its own learning product

- The Bryggeskole course is a **distinct learning product**, owned by the Bryggeskole domain
  ([KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md), Section 1).
- The full, completed course is intended to live later in its **own standalone app/program**.
- Some course material may also be exposed on the **website**.
- The current main Kvernhaug App's Bryggeskole tab is **not** the final home of the entire course.
- **Decided 2026-10-04 (§6.2.8):** the main App's Bryggeskole surface covers **Foundation → Kompetent hjemmebrygger**.
  The App itself stays the same brewing tool; only its Bryggeskole/course surface follows course progression.
- **Intended, not finalised:** the complete course, including Bryggemester depth and later deeper material, lives in a
  separate standalone course application/product. Its exact technical packaging is neither implemented nor finalised.
- **Still open:** which course content, if any, also appears on the website. That remains a separate product decision.
  (v1 of this section, 2026-10-03, left all of this undecided.)

### 6.2.4 Three different axes — never mix them

| Axis | Values | Where | What it is | What it is **not** |
|---|---|---|---|---|
| **Course progression** | Hjemmebrygger Foundation → Kompetent hjemmebrygger → Bryggemester → Bryggeri / profesjonell | Bryggeskole course (§6.1–§6.2) | How far the learner has come in the course | Not a UI display mode |
| **Web presentation mode** | **Bryggelærling / Bryggmester** (UI short form: Lærling / Mester) | Website recipe builder ([web/README.md](../../web/README.md)) | Support level in the **same** web application. Bryggelærling = more guidance, help popups and support ("støttehjul"). Bryggmester = same application and functionality with less guidance, for users who do not need the extra help | Not course levels and never renamed to Foundation / Kompetent / Bryggemester. Web "Bryggmester" is **not** the course track "Bryggemester" — the spelling difference is intentional |
| **App Bryggeskole environment chooser** | **Hjemmebrygger / Bryggeri** | Bryggeskole tab in the App (`ui/bryggeskole_panel.py`) | Legacy/pilot presentation axis from the #327-era design: changes labels/presentation only, with shared lesson content and shared mastery | Not the course progression, not two separate courses, not Foundation vs Kompetent, and not a hobby-vs-professional track progression. "Bryggeri" here is **not** the Bryggeri / profesjonell track |

Rules that follow:

- The App environment chooser's current behaviour (mostly labels, same lessons) is **intentional legacy behaviour**,
  not a defect and not evidence of two courses.
- The chooser **must not** be used as the architecture for future course content. New course content is placed by
  course stage (§7–§10), never by environment.
- The chooser stays as it is until a later, separately decided UI cleanup. This decision removes or renames nothing.

### 6.2.5 Web Hjelp & bryggehåndbok is not the course

The website's **Hjelp & bryggehåndbok** (`web/hjelp/`) is user and process guidance for using the website and the
brewing workflow. It is **not** the Bryggeskole course, even though its pages were historically built under a content
programme also labelled "Bryggeskole P0–P3B" (see [web/README.md](../../web/README.md)). Consolidating overlapping
help pages onto registry-backed course content remains a later, separate decision (§15).

### 6.2.6 Kunze / #419 and source rules (unchanged)

Kunze and #419 remain a **curriculum/domain mapping source** only. Nothing here changes Course Fact Registry governance,
the #65 source hierarchy or source-quality rules (§14.3).

### 6.2.7 Sync note

Recorded locally on branch `offline/course-architecture-decision` while GitHub was unavailable. When GitHub access
returns, this decision must be mirrored on the governing GitHub records (#419, the #343 roadmap and the #152 HO
pointer) before it is treated as synchronized. The 2026-10-04 update (§6.2.8) is recorded the same way. Its module
decisions must also be mirrored on #434 (Måling) and #436 (Oppskriftsforståelse).

### 6.2.8 Update 2026-10-04: App course scope and canonical module order

Owner/Chief decision, 2026-10-04, recorded offline.

**Course surfaces**

| Surface | Status |
|---|---|
| Main App Bryggeskole: **Foundation → Kompetent hjemmebrygger** | **Closed** (decided) |
| Bryggemester (voluntary advanced depth) and later deeper material in a standalone course product | Intended direction; packaging not implemented or finalised (partially open) |
| Bryggeri / profesjonell | Later professional/industrial depth; never required for the homebrewer course |
| Course content on the website | **Open**; separate product decision |
| Web Lærling/Mester support modes and the App Hjemmebrygger/Bryggeri chooser | Unchanged: separate from course progression (§6.2.4) |

**Canonical 11-module order** (1-based positions; this replaces the 0-based numbering in §15 for positions):

| # | Module | Stage |
|---|---|---|
| 1 | Råvarer | see its module contract / §7–§8 |
| 2 | Rengjøring og sikkerhet | see its module contract / §7–§8 |
| 3 | Forberedelse/metode | see its module contract / §7–§8 |
| 4 | Mesking | see its module contract / §7–§8 |
| 5 | Koking/humle | see its module contract / §7–§8 |
| 6 | Kjøling/overføring | see its module contract / §7–§8 |
| 7 | Gjæring | see its module contract / §7–§8 |
| 8 | Pakking | see its module contract / §7–§8 |
| 9 | Måling og bryggelogg | **Split:** Foundation first, Kompetent later (measurement contract) |
| 10 | Oppskriftsforståelse | **Entirely Kompetent**; intended for the main App Bryggeskole (recipe-understanding contract) |
| 11 | Smak og evaluering | see `v22_sensory_evaluation_module_contract.md` |

A stage is stated here only where a module contract locks it. Otherwise the owning module contract and §7–§8 govern.

The visible grid grows toward this order as modules land:
- Before Måling: Pakking (8) → Smak og evaluering (9).
- With Måling Foundation (status 2026-10-04: implemented in the offline/local integration, not yet on GitHub/master):
  Pakking (8) → Måling (9) → Smak (10).
- With Oppskriftsforståelse (status 2026-10-04: implemented locally/offline on `offline/recipe-understanding-implementation`, not yet
  on GitHub/master): Måling (9) → Oppskriftsforståelse (10) → Smak (11).

**Decision pointers** (closed locally, not yet on GitHub):
- **Måling og bryggelogg:** `v22_measurement_brewlog_module_contract.md`, closed on `offline/measurement-grid-position-correction` @
  `55eb93b4933d0f3109958410f40f696b4014dfa3`. Position 9; Foundation slice first.
- **Oppskriftsforståelse:** `v22_recipe_understanding_module_contract.md`, closed on `offline/recipe-understanding-contract` @
  `865d87d1413610643850909ec63f89a3aacff097`. Kompetent; main App; position 10; implementation waits for the Måling Foundation
  module. Status 2026-10-04: that prerequisite is satisfied in the offline integration (not yet on GitHub/master);
  Oppskriftsforståelse itself is now implemented locally/offline (`offline/recipe-understanding-implementation`; not yet on GitHub/master).

Implementation detail (ids, chunks, questions, tests) lives in those contracts, not here.

### 6.2.9 Stage allocation per module (2026-10-04)

Which stage (Foundation, Kompetent, Bryggemester, Bryggeri) each module's topics, chunks and questions belong to, the locked
content moves, the Foundation exit checkpoint, the Kompetent completion criteria and the Bryggemester/Bryggeri boundaries are
canonical in [v22_course_stage_allocation_contract.md](v22_course_stage_allocation_contract.md). Where §7–§10 and §4 level
labels in this audit differ from that contract on a stage question, the contract governs (for example: Smak og evaluering is
Kompetent; quantitative priming is Bryggemester, with the priming concept at Kompetent).

---

## 7. Hjemmebrygger — Trinn 1: Foundation

**Goal:** brew a first all-grain batch **safely** on the learner's own method (BIAB, traditional kettle, or all-in-one)
and understand *what is happening* at each stage.

| Area | Content (curriculum topics, not teaching text) | Current state |
|---|---|---|
| Safety & hygiene | Cleaning vs sanitation; hot side vs cold side; chemical handling; hot liquid/boil-over; sealed containers under pressure; CO₂ from fermentation in enclosed spaces; electrical equipment near liquids (D31–D35, D37) | Partial (COOL-0003, BOIL-0004, PACK-0003) |
| Ingredients | What malt, hops, yeast and water are and what each contributes; chlorine in tap water (D01–D04, D52) | Absent → #418 |
| Method | Choosing and understanding one's own method (D15) | Complete |
| Process spine | Mash (enzymes convert starch), boil (why), hops (bitterness vs aroma), cool/transfer, oxygen timing, ferment at the right temperature, carbonate and package (D17, D20–D25, D29, D30, D46, D59, D60, D65) | Largely complete (qualitative) |
| Basic measurement | Measure temperature where it matters; what OG/FG mean in one sentence (D38, D07 concept) | Absent |

**Level 1 finish line:** the learner can brew, ferment and package one batch safely and explain in plain words what each
stage does. This is a checkpoint, not the homebrewer completion point (§17).

## 8. Hjemmebrygger — Trinn 2: Kompetent hjemmebrygger

**Goal (#419):** formulate a sensible recipe, execute the process, measure, evaluate, and deliberately improve the next brew.

| Area | Content | Current state |
|---|---|---|
| Ingredients for decisions | Base vs specialty malt choice, hop roles and forms, yeast choice by attenuation and flavour, mash pH concept, adjuncts in brief (D01–D05, D51, D64) | Absent → #418 + follow-up |
| Recipe understanding | Gravity, attenuation, alcohol, colour, bitterness, balance, styles as context, formulation (D07–D14) | Absent (App tools only) |
| Process control | Milling/crush, grain separation for the learner's method, wort collection, efficiency concept (D16, D18, D19, D66) | Absent |
| Measurement & records | Hydrometer/refractometer, volume, simple instrument checks, recording planned vs actual (D39, D40, D43, D44) | Absent (App inputs only) |
| Fermentation management | Pitching/viability concept, phases, by-products, completion by stable gravity, conditioning (D26, D27, D45, D47, D48, D61) | Partial |
| Beer quality | Clarification concept, shelf life/oxidation, protein/polyphenol haze (D28, D58, D62, D63) | Absent/partial |
| Evaluate & improve | Sensory basics, observation vs interpretation, beginner fault set, one deliberate next change (D54–D56) | Partial (Brew History) |

**Level 2 finish line = homebrewer completion (§17).**

## 9. Bryggemester — frivillig fordypning

Offered as **voluntary tracks**, each finishable on its own. None is required to complete the course:

- **Water chemistry:** ions, residual alkalinity, treatment, pH measurement (D41, D53).
- **Yeast depth:** starters, harvesting and reuse, simple viability checks (D49, simple part of D78).
- **Pressure & kegging depth:** pressure fermentation, gauges and regulators, quantitative carbonation (D42, D50, D29 quantitative).
- **Mash depth:** step and decoction schedules, adjunct cereal cooking, quantitative fermentability (D05, D17 advanced).
- **Oxygen & stability:** oxidation control, flavour stability, foam (D57, D58, D62 depth).
- **Special beers:** high gravity, low/no alcohol (D67).
- **Make your own malt:** home malting (D06; Kunze 8.3 has a small-scale treatment).
- **Structured experimentation:** extends the Goal 2 loop. This is not a statistics platform (D83; PARKed in #343).

## 10. Bryggeri / profesjonell — senere spor

Clearly optional. PARKed per #343 ("broad professional Bryggeskole curriculum"):
D70 pub/microbrewing, D72 process engineering, D73 filtration/stabilisation, D74 commercial packaging, D75 CIP,
D76 instrumentation incl. dissolved-oxygen meters, D77 QC/lab analysis, D78 yeast lab, D79 formal sensory panels,
D80 environment/waste, D81 energy/utilities, D82 automation/plant planning.
Kunze Chapters 5, 9, 10, 11 and most of 4.4–4.6 are the natural source map for this track. The "Bryggeri" environment
in the current UI is navigation labels only (#420) and must not be presented as this track (see the three axes in §6.2.4).

---

## 11. Safety curriculum

Safety is **Level 1 MUST**. It is taught where the hazard occurs, plus one short consolidated unit, so the learner
has one place to review it.

| Topic | Kunze locator | Existing verified support | Needed | Level |
|---|---|---|---|---|
| Cleaning vs sanitation, order of operations | 6.1–6.7 (716–731) | COOL-0003 (boundary only) | Fact pack | L1 MUST |
| Chemical handling (cleaners, sanitisers, caustic), storage, eye/skin protection | 6.8 (731); 11.3.9 (918) | none | Fact pack. **Tier A = product labels/SDS and manufacturer guidance**, not Kunze | L1 MUST |
| Hot liquids, burns, boil-over | 3.11 (359–367) | BOIL-0004 (boil-over) | Burn/hot-liquid handling record | L1 MUST |
| Fermentation CO₂ in enclosed spaces | 4.9.1 (523) | none | Record (industrial source → needs homebrew-scale framing and a second source) | L1 SHOULD→MUST (owner decision) |
| Pressure: sealed bottles/kegs, rated equipment | 4.9.2 (524); 11.3.4 (895–898) | PACK-0003 | — (sufficient for L1) | L1 MUST |
| Electrical equipment (electric kettles/all-in-one near liquid) | 10.4.4 (846) — industrial only | none | Manufacturer/standards source | L1 SHOULD |
| Spoilage vs safety (infection spoils beer; framing without alarmism) | 4.6.1 (487–493); 7.4.2 (763) | COOL-0001/0003 | Record | L1 MUST |

**Owner decision flagged:** whether CO₂-in-enclosed-space is MUST or SHOULD at L1 (it depends on the typical Kvernhaug
learner fermenting indoors). This audit recommends MUST, framed as a short, proportionate caution.

## 12. Science-foundation curriculum

Rule (#419): science **only to the depth that explains a brewing decision**.

| Concept | Why the homebrewer needs it | Level | Existing support |
|---|---|---|---|
| Enzymes and starch conversion (D59) | Explains mash temperature and fermentability choices | L1 concept / L2 control | MASH-0001/0002/0004 |
| Maillard reactions (D64) | Explains specialty malt colour and flavour | L2 | none |
| Isomerisation (D60) | Explains why boil time drives bitterness | L1 | HOP-0001 |
| Yeast metabolism (D61) | Explains alcohol, CO₂, esters and diacetyl, and why completion matters | L2 | none (BREW-* cover temperature only) |
| Oxidation (D62) | Explains why oxygen is wanted before fermentation and unwanted after | L1 rule / L2 why | OXY-0001…0003 |
| Microbiology (D32) | Explains hot side vs cold side and infection | L1 concept | COOL-0001/0003 |
| Protein/polyphenol and haze (D63) | Explains break, clarity and chill haze | L2 | BOIL-0003, COOL-0002 |
| Carbonation / CO₂ (D65) | Explains priming vs forced carbonation | L1 | PACK-0001/0002 |
| Foam (D57) | Head retention | L3 (one L2 sentence) | none |

---

## 13. Visual / interactive opportunities

Only where interaction **materially improves understanding** (#343 Goal 3). Everything else stays text + questions.

| Opportunity | Domains | Why it helps | Value |
|---|---|---|---|
| **Hot side / cold side sanitation map**: a stage diagram marking where heat protects and where sanitation must take over | D31, D32, COOL-0003 | Spatial and temporal boundary. It is the single most misunderstood hygiene concept and is easy to show | High |
| **Gravity-over-time fermentation curve**: OG falling to a stable FG, marking attenuation and "done" | D07, D08, D48 | Makes completion and attenuation visible; connects directly to Brew History OG/FG | High |
| **Hydrometer / refractometer reading exercise** (read the scale, correct for temperature/alcohol at concept level) | D39, D43 | Reading an instrument is a spatial skill; the numbers must come from verified facts | High |
| **Mash temperature → fermentability explorer** (direction only, no universal numbers, per MASH-0002/0004 notes) | D17, D59 | Shows direction and trade-off without numeric claims | High |
| **Malt colour and role spectrum** (base → specialty → roast) | D01, D10, D64 | Makes colour and flavour contribution tangible | Medium |
| **Recipe consequence view** reusing the existing recipe engine (change malt/hop/yeast → see OG/IBU/EBC/ABV direction) | D07–D14 | Learn→Plan bridge. Must reuse the engine and **must not** create a second course truth | High |
| **Interactive hop timeline** (upgrade of the static `boil_timeline.py`) | D21, D22 | Timing trade-off is naturally interactive | Medium |
| **Tasting sheet linked to Brew History sensing** | D55, D56 | Trains observation vs interpretation on the learner's own beer | Medium |
| **Method-aware grain separation** (bag lift vs lauter vs basket) | D15, D18 | Equipment is spatial. Extends the existing method SVG | Medium |
| Water chemistry charts, CIP, plant diagrams | D53, L4 | Low value at homebrewer level | Low (skip) |

---

## 14. Source and Fact Registry gaps

### 14.1 Fact packs required before teaching (no registry change in this issue)

| Pack | Domains | Kunze locator (Tier B candidate) | Other source need |
|---|---|---|---|
| Cleaning, sanitation & chemical safety | D31–D33 | 6 (716–731) | Tier A: sanitiser/cleaner manufacturer documentation and SDS; homebrew-scale Tier B |
| Heat / CO₂ / electrical safety | D34, D35, D37 | 3.11 (359); 4.9 (523–532); 10.4.4 (846) | Manufacturer/standards for electrical; homebrew framing |
| Malt | D01, D10, D64 | 1.1; 2.5.1; 2.9 | Maltster technical data (Tier A) |
| Hops as ingredient | D02 | 1.2 | Hop supplier/producer technical data |
| Yeast as organism | D03, D45 | 1.4; 4.3.3 | Yeast producer technical data |
| Water basics + chlorine/chloramine + mash pH concept | D04, D51, D52 | 1.3; 3.2.1; 8.3 (793) | Chloramine: **not found in Kunze OCR** — needs another source; water utility / Tier A |
| Gravity, attenuation, alcohol | D07–D09, D48 | 3.5.1; 4.3.3; 4.1.2 | Instrument manufacturer documentation (Tier A) |
| Measurement & calibration | D38–D40, D43 | 3.5.1; 7.5; 11.1.2 | Instrument manufacturer documentation |
| Fermentation management & by-products | D26, D27, D47, D61 | 4.1–4.3 | Yeast producer + Tier B |
| Sensory & faults | D54, D55 | 7.2; 7.4.1; 4.1.3 | Tier A/B sensory references (for example flavour standards/references). To be identified; not assumed here |
| Recipe formulation, balance, styles | D12–D14 | Weak (no dedicated section) | **Kunze is not sufficient**; needs non-Kunze Tier B |
| Clarification / haze | D28, D63 | 4.3.5; 4.6.2 | Tier B |

### 14.2 Existing registry records that Kunze could strengthen (candidates only — separate, source-reviewed change)

| Record | Status | Kunze candidate locator | Required before any change |
|---|---|---|---|
| FACT-BOIL-0001 (enzyme inactivation, microbial reduction) | verified; Kunze cited **second-hand** via a BA-hosted VLB presentation (#420 §3) | 3.4.1 "wort sterilisation", "destruction of all enzymes" (285) | Visual page verification; replace or add a direct citation |
| FACT-BOIL-0003 (hot break) | verified; Kunze second-hand | 3.4.1 "formation and precipitation of protein-phenol compounds" (283) | Visual page verification |
| FACT-MASH-0003 (iodine test) | **draft**, needs a second source (#337) | 3.2.6 control of mashing (255); iodine appears in the OCR on printed pp. 215–220, 237, 255 | Visual page verification; registry review; could unlock the mash-conversion check |
| FACT-BOIL-0002 (DMS) | verified | 2.5.1 DMS formation (160); 3.4.1 evaporation of undesirable aroma substances (287) | Optional extra source |
| FACT-OXY-0001 (aeration timing) | verified | 3.9.3 time of yeast aeration (355) | Optional; see §14.4 |

### 14.3 Rules restated

- Kunze is a **Tier B** textbook in the #65 hierarchy. It is a strong source but not automatically sufficient, and not
  the only one for contested claims.
- **No OCR-only promotion.** Any Kunze-derived claim needs visual page verification of the exact page first. If the page
  is still unclear, it is recorded as **OCR UNCERTAIN** and not used.
- No numeric Kunze value (temperatures, dosages, quantities, bitterness arithmetic) becomes teaching content without
  unit/scope review. The registry's no-universal-numbers notes (MASH-0002/0004, PACK-0001, BREW-0003) stay in force.

### 14.4 Scope and dating conflicts to report (not resolve)

1. **Whirlpool framing.** Kunze 3.8.3 treats the whirlpool as **hot-trub separation**. The registry (HOP-0002/0003) also
   uses whirlpool/hop-stand as an **aroma-hopping** window. This is not a contradiction, but future teaching must not merge
   the two meanings.
2. **Hobby-brewer walkthrough is industry-framed and dated (2004).** Visually checked on printed pp. 793 and 796:
   - Kunze treats dried yeast as of uncertain quality and suggests obtaining yeast from a brewery. The registry's
     OXY-0001 treats fresh active dry yeast as a normal, well-characterised option.
   - The walkthrough assumes a cool, lager-type fermentation. That is narrower than the registry's strain-dependent
     framing (BREW-0003).

   Kunze should therefore **not** be used as the authority for homebrew *practice* claims where newer Tier A producer
   documentation exists.
3. **Chlorine handling.** Kunze 8.3 (793) suggests remedies for chlorinated tap water. The page was visually checked,
   but the remedies are not verified as Kvernhaug truth. Chloramine behaves differently, and Kunze was not found to
   cover it, so any water-treatment teaching needs other sources.

---

## 15. Recommended module architecture

Principle: **extend the six existing process modules and add five new ones.** The result is 11 modules at homebrewer
completion, with no per-topic module explosion. Optional L3 tracks are separate and visibly optional.

```
Level 1–2 core course (homebrewer completion)
 0  Råvarer                    NEW   malt · hops · yeast · water (+ adjuncts note)          ← #418
 1  Rengjøring og sikkerhet    NEW   cleaning vs sanitation · chemicals · heat · CO2/pressure ← §18
 2  Forberedelse/metode        KEEP  method choice (complete)
 3  Mesking                    EXTEND  + milling · grain separation (method-aware) · wort collection · conversion check
 4  Koking/humle               KEEP  (+ whirlpool framing note)
 5  Kjøling/overføring         KEEP  (sanitation boundary now links to module 1)
 6  Gjæring                    EXTEND  + pitching · phases · by-products · completion · conditioning
 7  Pakking                    EXTEND (small)  + clarification concept · shelf life
 8  Måling og bryggelogg       NEW   temperature · gravity · volume · checks · recording → Brew History actuals
 9  Oppskriftsforståelse       NEW   gravity · attenuation · alcohol · colour · bitterness · balance · style context → recipe editor
10  Smak og evaluering         NEW-ish  sensory basics · beginner faults · evaluate → next change (builds on G3N / Brew History)

Bryggemester (frivillig fordypning): Vannkjemi · Gjærhåndtering · Trykk og fat · Avansert mesking · Oksygen og holdbarhet · Spesialøl · Egen malt
Bryggeri / profesjonell (senere spor): parked
```

Design notes:

- **Sequence:** Råvarer and Rengjøring og sikkerhet come *before* the process spine in the recommended order. They do not
  lock it. A learner who wants to jump straight to Mesking may, consistent with the current open grid.
- **Module 8 is placed after the spine** because it is most useful once the learner has something to measure.
  (Numbering in this diagram is 0-based; the canonical 1-based positions are in §6.2.8 — Måling is position 9,
  Oppskriftsforståelse 10, Smak og evaluering 11.) Its
  temperature basics (D38) are referenced from L1 modules as a short inline note.
- **Module 10 reuses the G3N/Brew History methodology.** It adds sensory and fault *knowledge* (registry-backed), and
  keeps the evaluate/hypothesis *method* as non-registry product methodology.
- **Bridges:** 0 → recipe malt/hop/yeast choice; 8 → Brew History actuals; 9 → recipe editor; 10 → Brew History sensing.
  Every bridge reuses chunks read-only, following the existing bridge pattern (#420 §4).
- **One knowledge truth** (#343 principle 5). Web hjelp pages covering the same topics should later link to or be
  replaced by registry-backed content. That is a later consolidation, not part of this roadmap's slices.

---

## 16. Ordered implementation roadmap

Smallest sensible slices. Each has explicit dependencies, and each implementation slice is preceded by its
contract/fact pack, as in the existing G3 pattern (contract → facts → module → bridge → owner acceptance).

| # | Slice | Type | Depends on | Unlocks |
|---|---|---|---|---|
| 1 | **#418 G3P Råvarelære contract** (already open) | READ/PREP docs | — | 4 |
| 2 | **G3R Rengjøring og sikkerhet contract + fact-pack plan** (§18) | READ/PREP docs | — (can run in parallel with 1, as a second prep lane) | 5 |
| 3 | Registry re-sourcing pass: BOIL-0001/0003 direct Kunze citation; MASH-0003 second-source check (§14.2) | Registry change, source-reviewed, visual verification | — | Mesking conversion check (slice 8) |
| 4 | Råvarer fact pack(s) + module implementation | Registry + module | 1 | 9, 10 |
| 5 | Rengjøring og sikkerhet fact pack + module implementation | Registry + module | 2 | — |
| — | **Checkpoint: Level 1 complete** (owner-PC acceptance on one method) | Acceptance | 4, 5 | — |
| 6 | Måling og bryggelogg contract → facts → module → Brew History actuals bridge | Contract + module + bridge | 4 | 7, 9, 10 |
| 7 | Gjæring expansion (pitching, phases, completion, conditioning, by-products) | Contract + facts + module | 4, 6 | 10 |
| 8 | Mesking expansion (milling, method-aware grain separation, wort collection, conversion check). **Respects SOURCE GAP 257/259–260** | Contract + facts + module | 3, 4 | 9 |
| 9 | Oppskriftsforståelse contract → facts → module → recipe-editor bridge | Contract + module + bridge | 4, 6, 8 | 10 |
| 10 | Smak og evaluering (sensory, beginner faults, evaluate → next change) building on G3N | Contract + facts + module | 6, 7 | — |
| 11 | Pakking small extension (clarification concept, shelf life) | Facts + module | 7 | — |
| — | **Checkpoint: Level 2 = homebrewer completion** (acceptance with one real brew through the loop) | Acceptance | 4–11 | — |
| 12+ | Bryggemester-tracks, on demonstrated demand only | — | Level 2 | — |
| — | Bryggeri/profesjonell track | PARKED (#343) | — | — |

WIP rule (#343): one implementation lane, up to two prep lanes. Slices 1 and 2 are both prep, so they may run together.

---

## 17. Natural homebrewer completion point

**Hjemmebrygger completion = the Competent stage (former Level 2).** It is reached when the learner has completed modules 0–10 and used them on one real brew. The
course can then truthfully say, extending #65's own sentence:

> You can now plan, brew, ferment, package and evaluate a good all-grain homebrew safely and understandably — and
> deliberately improve the next one. You can stop here, or choose a deeper track.

Properties required of this finish point:

- It is **complete for the goal**. Neither Bryggemester nor Bryggeri/profesjonell content is a prerequisite, and nothing is presented as "the rest
  of the course".
- It is **method-inclusive**. It works for BIAB, traditional kettle all-grain and all-in-one (#65 §6) through the
  existing method-context framing.
- It is **evidence-based**, not a score. Mastery stays hidden, with no grades or rankings (#65 §3, #419).
- **Bryggemester** is shown **after** Hjemmebrygger completion as an optional next track. It is never shown as unfinished mandatory work.
- The Foundation stage is a deliberately low first threshold and recognised intermediate checkpoint ("you can brew safely"). It is not the final homebrewer completion claim.

---

## 18. One recommended next bounded child issue

**#418 is already open** and remains the first item on the roadmap. The single **new** child issue recommended by this audit is:

> **V2.2 G3R — Rengjøring og sikkerhet: Level 1 cleaning/sanitation + brewing-safety module contract**

- **Why this one:** cleaning vs sanitation (D31), chemical handling (D33), heat (D34) and CO₂/pressure (D35) are
  **Level 1 MUST** and are only partial or absent today. They are safety-relevant. They are the only L1 blocker not
  already covered by #418, and Kunze Chapter 6 plus 3.11/4.9 give a clear domain structure for them.
- **Deliverable:** exactly one docs-only contract, `docs/development/v22_g3r_cleaning_safety_module_contract.md`, defining:
  1. learner outcome at L1;
  2. MUST concepts (cleaning vs sanitation, order, hot/cold side, chemical handling, burns/boil-over, fermentation CO₂,
     pressure) and explicit LATER items (CIP, industrial cleaning, microbiological lab);
  3. reuse of COOL-0003, BOIL-0004, PACK-0003, COOL-0001;
  4. the missing fact pack, with Tier A sources named (sanitiser/cleaner manufacturer documentation and SDS for chemical
     claims, and Kunze Chapter 6 as Tier B structure only, after visual verification);
  5. placement as module 1 (§15) and the link from Kjøling/overføring;
  6. the hot side/cold side visual (§13);
  7. NO/EN, mastery concepts (for example `sikkerhet.rengjoring_vs_sanitering`, `sikkerhet.kjemikalier`, `sikkerhet.co2_trykk`);
  8. one acceptance scenario and the smallest implementation slices;
  9. the owner decision on CO₂-in-enclosed-space as MUST vs SHOULD (§11).
- **Non-goals:** no product code, no registry mutation, no CIP/professional depth, no Web deploy, no Sóti.
- **Size:** one prep PR. It can run in parallel with #418 as the second prep lane (#343 WIP rule).

---

## 19. Source limitations, unresolved gaps and boundary statement

### 19.1 Source limitations

- **SOURCE GAP — PRINTED PAGE NOT PRESENT IN PDF:** printed pp. **257, 259, 260**. These fall in §3.3.2 *Last runnings*,
  which starts and appears to end on p. 257, and in the opening of §3.3.3 *Mash separation with a lauter tun*, which
  resumes at p. 261. Printed p. 258 is figures only. Lautering (D18) and wort-collection (D19) teaching must use other
  sources for anything these pages would have covered.
- **SOURCE GAP — printed p. 649**, inside §5.5.5 *Filling of the cans*. This is a professional topic and affects no
  homebrewer domain.
- **OCR limits:** tables, formulas, figures, rotated pages and gutter-clipped columns are unreliable. All Kunze page
  references here come from the visually read TOC. No Kunze number, table or formula was used.
- **OCR UNCERTAIN:** the wording of the §8.3 closing advice on keeping notes (printed p. 797, gutter-clipped). It is used
  here only as topic presence for D44.
- **Chapter banners** (6, 8, 9, 11) are image-only in the OCR. Their titles were taken from the TOC images.
- **Not found in the Kunze OCR** (a keyword search, which is not proof of absence): chloramine; recipe formulation or
  balance as a topic; homebrew equipment methods (BIAB, all-in-one). Placing these in the curriculum is a Kvernhaug
  decision, and they need other sources.
- **Age of source:** Kunze is a 2004 industrial textbook. Homebrew-practice statements (yeast forms, fermentation
  practice, equipment) may be dated relative to current producer documentation (§14.4).

### 19.2 Unresolved / owner decisions

1. CO₂-in-enclosed-space as L1 MUST or SHOULD (§11).
2. Final Råvarer structure: one combined module or four (#418 decides; this audit recommends one).
3. Whether module 8 (Måling) should precede the spine for learners who own instruments (this audit recommends after).
   **Resolved 2026-10-04:** after the spine, position 9 (§6.2.8).
4. Whether Web hjelp pages overlapping new modules should be consolidated onto the registry (recommended later, out of scope).
5. Whether the Kunze PDF should be placed in the private Vault. Not done in this issue; see the PR description.

### 19.3 Boundary statement

Docs-only. Exactly one file added. No product code, Course Fact Registry, tests, Web, App, Sóti, `raw_data`, recipe or
deployment file was changed. No Kunze statement was promoted to verified truth. No long passages, whole tables or
formulas from Kunze were reproduced. General brewing knowledge was not used to repair missing or unclear source text.
The classifications above are curriculum judgements for owner/Chief review, not verified facts.
