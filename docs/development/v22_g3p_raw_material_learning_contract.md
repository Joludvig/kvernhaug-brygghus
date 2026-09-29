# V2.2 G3P — Råvarelære (raw-material learning) contract

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#418](https://github.com/Joludvig/kvernhaug-brygghus/issues/418), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3); product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65); curriculum owner
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (merged, `af078d8661bae0aecc247d89ba5520a91fbce1d0`), whose map
(`v22_g3q_full_bryggeskole_curriculum_map.md`, §6) endorses #418 as is and recommends one combined Råvarer module; current-product
inventory `v22_g3q_current_bryggeskole_coverage_inventory.md`.
Authoritative base at creation: `af078d8661bae0aecc247d89ba5520a91fbce1d0`.

This is a docs-only contract. It contains **no product code, no Course Fact Registry mutation, no new verified fact, no UI, no Web/App/Core/Sóti change and no deploy**.
Chief must review it before any implementation child issue is opened.

## 0. Source-status guard (read first)

The owner-supplied source reconnaissance accepted on #418 is a **source map, not a verified fact pack**. That reconnaissance is not stored in the
repository, and **this run did not open any external source**. Therefore:

- Nothing below is cited as *supported by* an external source. Where a source *kind* is named, it is a direction for the later fact-pack round.
- Every candidate claim in §5 is **unverified** until the fact-pack round opens and reads the named source, records scope and tier, and Chief reviews it.
- Only the registry records listed in §4 are reusable now, and only within their existing `notes`/wording-trap scope.
- Exact numbers, ranges, dosing and shelf-life durations are out of the Foundation layer unless a later source review checks them for scope and quality.

## 1. Learner outcome

After Råvarer, a homebrewer with no prior knowledge can, in their own words and without numbers to memorise:

1. say what each of the four ingredients contributes to the beer (malt: sugars/extract, enzymes, colour and flavour; hops: bitterness, flavour, aroma; yeast: turns sugar into alcohol and CO₂ and adds flavour; water: the majority ingredient, whose quality matters);
2. make a sensible **first-recipe choice** for each ingredient and say why (base vs specialty malt, which hop role a hop addition serves, which yeast type fits the intended beer and temperature, whether tap water needs checking first);
3. recognise the **common beginner mistakes** the process spine otherwise assumes are known (old/oxidised hops, ignoring producer yeast guidance, chlorine/chloramine in tap water, treating specialty malt as a base);
4. connect an ingredient choice to a concrete App surface (malt list, hop panel, yeast panel, water panel) and to the process stage where it matters.

Non-outcome: memorising ion targets, strain names, hop-variety sensory catalogues or malt-analysis values.

## 2. MUST concepts (Foundation)

Concept ids follow the registry style (`area.topic`). They are proposals for the fact-pack round, not existing registry concepts.

| Ingredient | MUST concept | Proposed id |
|---|---|---|
| Malt | What malt is; why barley is malted (starch access + enzymes) | `malt.what_is_malt` |
| Malt | Base vs specialty malt: base supplies most extract and enzymes; specialty is used in smaller amounts for colour/flavour | `malt.base_vs_specialty` |
| Malt | Colour and flavour come from kilning/roasting; EBC as "how dark", beginner level, no colour-prediction maths | `malt.colour_flavour` |
| Malt | Extract and fermentability contribution (reuse MASH facts) | `malt.extract_fermentability` |
| Malt | Why percentages of the grist matter: the mix, not one malt, sets the beer | `malt.grist_percentage` |
| Hops | Three roles: bitterness, flavour, aroma | `hop.roles` |
| Hops | Alpha-acid % is a property of the hop pack; IBU is a beer-level result of alpha acid, amount, time and boil | `hop.alpha_acid_vs_ibu` |
| Hops | Timing during active boil (reuse HOP-0001/0002/0003) | `hop.timing_link` |
| Hops | Late/flameout vs whirlpool/hop-stand named as distinct, without App timing semantics | `hop.late_vs_whirlpool_naming` |
| Hops | Common forms (pellets, whole cones) and that hops age; store cool/dark/airtight (conditions, not durations) | `hop.forms_storage` |
| Hops | Old hops can bring stale/unpleasant flavour | `hop.old_hop_risk` |
| Yeast | Yeast is the organism that ferments sugar into alcohol and CO₂ | `yeast.organism_role` |
| Yeast | Attenuation: how much of the sugar a yeast ferments; affects dryness/ABV | `yeast.attenuation` |
| Yeast | Ale vs lager at beginner level (types differ in usual working temperature and character) | `yeast.ale_vs_lager` |
| Yeast | Temperature matters and is strain-specific (reuse BREW-0001/0002/0003) | `yeast.temperature_link` |
| Yeast | Safe pitch principle: enough healthy yeast, follow the producer's guidance; no generic cell-count arithmetic | `yeast.pitch_principle` |
| Yeast | Yeast choice by intended beer and producer datasheet, not strain memorisation | `yeast.choice_principle` |
| Water | Water is the majority ingredient and its quality carries into the beer | `water.majority_ingredient` |
| Water | Chlorine vs chloramine as an off-flavour risk; check the local waterworks/municipality information | `water.chlorine_chloramine` |
| Water | Source water vs "what I want to brew": awareness only, no targets | `water.source_awareness` |

## 3. LATER / advanced (explicitly not Foundation)

- Mash pH as a concept (candidate L2 SHOULD, own exact scope), and any pH numbers.
- Ions, residual alkalinity, target profiles, salt dosing (stays in the App water panel and `web/hjelp/vannkjemi.html`; not mandatory for course completion).
- Boiling/standing as a chlorine/chloramine fix; home-scale chloramine removal methods (only with a Tier A brewing-specific source).
- Malt storage/freshness nuance, crushed-vs-whole malt freshness, malt-analysis sheet reading, malt catalogue depth.
- Liquid-vs-dry yeast detail, yeast starters, pitch-rate calculators, viability maths, harvesting/repitching, pressure fermentation.
- Hop-variety sensory framing beyond catalogue data, hop oils/chemistry, hop storage index, dry-hop technique.
- Adjuncts/other fermentables (curriculum map D05: a later one-unit L2 concept, not in #418).
- Strain, hop-variety or malt encyclopedias of any kind.

## 4. Existing verified facts reusable now

All are `status: verified` in `bryggeskole/data/course_fact_registry.json` at the base SHA. Reuse only within each record's `notes` scope; wording traps remain binding.

| Ingredient | Records | What they can carry |
|---|---|---|
| Malt | FACT-MASH-0001, FACT-MASH-0004 | Malt enzymes convert starch; some becomes unfermentable dextrins; fermentability depends on several variables including malt enzyme content. Supports `malt.extract_fermentability` only. |
| Malt | FACT-BOIL-0002 (background only) | DMS precursor exists in malt. Not a Foundation malt concept. |
| Hops | FACT-HOP-0001, -0002, -0003 | Isomerisation and its time dependence; aroma volatility; multi-addition strategy. Cover `hop.roles` (bitter vs aroma) and `hop.timing_link`. Do not assert numbers; late additions are "generally lower", never "zero". |
| Yeast | FACT-BREW-0001, -0002, -0003 | Temperature drives activity; flavour effect is strain-dependent; choose temperature per strain guidance. Cover `yeast.temperature_link`. |
| Yeast | FACT-OXY-0001 | Yeast uses oxygen for membrane growth; aeration conditional on yeast form/state. Supports `yeast.pitch_principle` context only; must not become "always aerate". |
| Water | none | No water record exists. |

FACT-MASH-0003 (iodine test) is `draft` and out of scope. No record covers malt as a raw material, hop forms/storage, yeast attenuation/ale-vs-lager, or any water claim.

**Duplication/unsourced-claim hazards found in the audit (do not promote automatically):** `web/hjelp/humle.html`, `web/hjelp/gjaervalg.html`, `web/hjelp/gjaerhosting.html`, `web/hjelp/vannkjemi.html`, and captions in `ui/malt_panel.py`, `ui/water_panel.py`, `ui/hop_panel.py`, `ui/yeast_panel.py` and the malt/hop/yeast masterdata make ingredient claims that are not linked to registry ids. They may be *read* as candidate wording leads in the fact-pack round; they are never a source and must not be copied into course content as verified truth.

## 5. Missing fact/source packs

Each pack is a future registry-mutating round (not this issue). Source *kinds* below are directions from the accepted reconnaissance; every source must be opened and read before citation.

| Pack | Content | Direction for sources | Open red flags |
|---|---|---|---|
| **P1 Malt core** | `malt.what_is_malt`, `base_vs_specialty`, `colour_flavour`, `grist_percentage`; reuse MASH-0001/0004 | Malt producer technical material; established brewing texts/encyclopedia as Tier B; the owner-held reference book (Kunze) may inform structure but is not cited second-hand as in BOIL-0001/0003 | Colour numbers stay out; no "specialty malt never converts" absolutes |
| **P2 Yeast core** | `organism_role`, `attenuation`, `ale_vs_lager`, `pitch_principle`, `choice_principle` | Yeast manufacturer technical/knowledge-centre material (Tier A) | Do not teach dated dry-yeast framing where current producer documentation supersedes it; no generic cells/mL/°P arithmetic as dry-yeast truth; source gap: one strong beginner source for sugar → alcohol + CO₂ |
| **P3 Water foundation** | `majority_ingredient`, `chlorine_chloramine`, `source_awareness` | Municipal/waterworks information and brewing-specific water guidance | Never teach boiling/standing as a universal fix; Norway-specific chloramine prevalence and home-scale removal guidance at Tier A are open gaps; no mash-pH numbers |
| **P4 Hops delta** | `alpha_acid_vs_ibu`, `forms_storage`, `old_hop_risk`; naming of late vs whirlpool | Hop supplier/producer datasheets (already used by HOP-0002) and brewing texts | Teach storage *conditions*, not universal shelf-life numbers; keep whirlpool-as-trub-separation distinct from whirlpool/hop-stand aroma usage; general hop-variety selection beyond catalogue data is an open gap |

Pack order follows §12. Unfilled gaps stay explicit; they are not filled from general knowledge or AI.

## 6. Recommended module structure

**One combined "Råvarer" module with four short ingredient sections** (Malt, Humle, Gjær, Vann), aligned with the curriculum map's recommendation. Reasons: four separate modules add navigation cost without learning value at Foundation depth; the ingredients are compared in one decision ("what goes in my first recipe"); the existing module system (`ui/bryggeskole_panel.py` `_MODULER`) already handles topic modules of this size.

Proposed shape (indicative; the implementation issue fixes it):

- Module id `raw_materials.fundamentals`; concepts as in §2.
- About 10–12 chunks (roughly 3 malt, 3 hops incl. reuse, 3 yeast incl. reuse, 2 water) and about 10–14 questions, mix of `concept_check` and `scenario`, matching the current chunk/question pattern (`bryggeskole/pilot_*.py` + `bryggeskole/data/*.json`).
- Hops and yeast chunks that only restate existing facts link to the existing Koking/humle and Gjæring chunks rather than duplicate them.
- Placement: **before** the process spine (curriculum map §15 module architecture: Råvarer and Rengjøring og sikkerhet precede the process spine). Not a hard gate: existing modules stay reachable.
- Four separate modules or a deeper water/malt track are explicitly **not** recommended now. Revisit only if learner evidence shows the combined module is too long.

## 7. Connection to the process spine and Learn→Plan

- Forward links (one line each, text only): Malt → Mesking (enzymes, fermentability); Humle → Koking/humle (timing, IBU); Gjær → Gjæring (temperature, pitch) and Kjøling/overføring (oxygen); Vann → Forberedelse/metode (source water checked before brew day; chlorine before mash/boil water is used).
- Learn→Plan bridges follow the existing pattern (collapsed expander, read-only reuse of chunks, no questions, no mastery call). Candidate bridge surfaces: `ui/malt_panel.py` (malt), `ui/hop_panel.py` (hops; already bridges Koking/humle), `ui/yeast_panel.py` (yeast; already bridges Gjæring), `ui/water_panel.py` (water, chlorine/awareness only). Bridges are a **later slice**, not part of the first implementation issue, and the existing bridges' hard-coded chunk ids must not be broken.
- No recipe-engine, masterdata or timing-semantics change. Whirlpool teaching stays separate from App boil-time semantics, as in the G3L contract.

## 8. Visual and interactive opportunities

Value-ranked, all optional beyond one:

1. **Malt roles strip (recommended for slice 1):** a static, qualitative diagram sorting example malt types along "supplies extract/enzymes" to "adds colour/flavour", no numbers. Same technique as `boil_timeline.py` (static SVG).
2. Hop roles vs time: reuse `boil_timeline.py`; add no new diagram.
3. Yeast: "sugar → alcohol + CO₂ + flavour" three-step static diagram; no interactive model.
4. Water: a short "check your tap water" decision card (utility information → chlorine or chloramine → what to look up), no calculator.
5. Later: live link from the recipe builder showing grist percentage split (base vs specialty) using existing App data only.

No new simulator, no numeric yeast/pH/ion calculator in Foundation.

## 9. NO/EN requirements

- Every chunk, question, option and explanation exists in Norwegian and English, with NO/EN key symmetry, as in the current modules.
- Terminology follows established App/Web wording: humle, gjær, malt, vann, IBU, EBC, ABV, klorin/kloramin; English "hops", "yeast", "malt", "water", "chlorine/chloramine". Do not introduce a second term for an existing concept.
- No public Web page or generated `web/en/**` change in this line of work; if a later slice touches Web help, use `python3 scripts/generate_web_i18n_pages.py` only and never hand-edit `web/en/**`.
- Claims are not translated loosely: the fact registry claim is the single source for both languages, and wording traps apply in both.

## 10. Mastery and question concepts

- One hidden mastery concept per MUST concept in §2 (mirrors existing mastery use in `bryggeskole/mastery.py`); no new mastery mechanics.
- Question types: `concept_check` for definitions/roles; `scenario` for decisions. Scenario examples (not final text):
  - Malt: a recipe is 100 % roasted malt — what is wrong, and which malt should carry most of the grist?
  - Hops: same hop, added at 60 minutes vs at flameout — which serves bitterness and which aroma, and why is neither "zero" of the other?
  - Yeast: two yeasts, one for ale, one for lager — what does that change about how you plan fermentation temperature, and where do you look for exact guidance?
  - Water: tap water smells of chlorine — what do you check before brew day? (No "boil it" answer; no numbers.)
- Wrong-answer explanations reuse registry wording; no question may rest on an unverified claim, so a concept enters the module only after its pack is verified.
- No new scoring, badges or gating.

## 11. Representative acceptance scenario

A new homebrewer plans their first all-grain Pale Ale. Before any process module:

1. They open Råvarer and read Malt: they can say the base malt provides the bulk and a small share of specialty malt gives colour/flavour, and answer the roasted-malt scenario correctly.
2. In Humle they explain what an early vs late addition is for and that the pack's alpha % is not the beer's IBU.
3. In Gjær they pick an ale yeast, state that temperature guidance comes from the producer's datasheet, and explain why "more yeast" is not the same as "healthy, enough yeast".
4. In Vann they explain what to look up in local waterworks information about chlorine/chloramine before brew day, and do not answer "just boil it".
5. In the App the same learner opens the malt, hop, yeast and water panels and can relate each choice to what they just learned; nothing in the App computes differently.

Pass condition: all four sections answered correctly on a first read-through by an independent reader, no unverified claim is shown, and NO/EN show identical content. Owner-PC QA of the implementation remains a separate gate.

## 12. Smallest ordered implementation slices

| # | Slice | Type | Depends on |
|---|---|---|---|
| 1 | **P1 Malt fact pack**: open sources, add verified malt records, no UI | Registry + tests | this contract |
| 2 | **P4 Hops delta fact pack** | Registry + tests | 1 (pattern only) |
| 3 | **P2 Yeast core fact pack** | Registry + tests | — |
| 4 | **P3 Water foundation fact pack** | Registry + tests | — |
| 5 | Råvarer module skeleton with only the sections whose packs are verified; questions, NO/EN, mastery, module registration | Module + tests | 1–4 (each section may ship when its pack is done) |
| 6 | Malt roles strip visual | UI | 5 |
| 7 | Learn→Plan bridges (malt/water; extend hop/yeast if needed) | UI | 5 |
| 8 | Owner-PC QA + Chief acceptance against §11 | QA | 5–7 |

Packs 1–4 are independent of each other and may be separate bounded issues; the WIP rule of #343 still applies.

## 13. Recommended first bounded implementation issue

**"V2.2 G3P-1 — Råvarer fact pack P1: Malt core"**

- Scope: open and read the malt sources; add verified registry records for `malt.what_is_malt`, `malt.base_vs_specialty`, `malt.colour_flavour`, `malt.grist_percentage` (reusing MASH-0001/0004 rather than duplicating); add or extend registry tests in `tests/test_course_fact_registry.py`; document each record's scope and wording traps in `notes`.
- Why first: malt has the widest gap (no records, "incidental" coverage in the inventory), feeds Mesking and recipe theory (curriculum map D07–D14), and its sources and red flags are the least entangled with the open gaps that hold back water and yeast (chloramine prevalence, beginner CO₂ source).
- Non-goals: no module, no questions, no UI, no App masterdata change, no Web change, no water/hop/yeast records, no numbers or EBC tables, no Sóti work, no deploy.
- Done when: every new record is `verified` only with opened sources, source tier and scope recorded, and Chief has reviewed the exact head.

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted; no module, question, UI or bridge implemented; no masterdata, recipe-engine, supplier/catalog, advanced-water, yeast-strain, hop-variety or malt-catalogue work; no Web/public change; no Sóti work; no deploy.
