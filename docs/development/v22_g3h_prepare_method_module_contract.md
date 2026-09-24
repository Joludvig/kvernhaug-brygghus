# V2.2 G3H — Prepare/metodevalg verified fact pack + module contract

Version: 1.2
Status: PREP/decision document — Chief live citation pass completed 2026-09-24; implementation
decisions below are resolved for the bounded next slice; candidate new records remain `draft` until
a separately authorized Registry-promotion / implementation pass
Governed by: [#376](https://github.com/Joludvig/kvernhaug-brygghus/issues/376), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3), the
accepted Goal 3 gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358), the
completed Package module ([#374](https://github.com/Joludvig/kvernhaug-brygghus/issues/374) / PR
#375, "V2.2 G3G" — now merged, all five physical brew-day stages implemented), and
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product
direction)
Authoritative base at creation: `c5498ebc15f2b728ee1d52179b7fb3ce38caa047`

This is a **READ/PREP-only** document. It contains no module/UI implementation, no Course Fact
Registry mutation, and no App/Web/Core file changes — see [Hard non-goals](#hard-non-goals). It
does not authorize implementing a Prepare/metodevalg Bryggeskole module; it only prepares the fact
pack and module contract Chief would need to authorize that work.

---

## 0. Why prepare/metodevalg, and what already exists

Per #358's gap map, "1. Prepare" was already flagged as a MUST gap: "No interactive/verified
prepare module; method-choice orientation (BIAB vs. AG vs. AIO) exists only as disconnected static
prose." With Mesking, Koking, Kjøling/overføring, Gjæring and Pakking all now implemented (#374 /
PR #375, merged), this is the last clearly identified MUST content gap before Goal 3 can move from
the physical brew-process spine into bridge/evaluate closure — exactly the framing the governing
issue itself states.

**Current repo state relevant to this prep, confirmed by inspection:**

- `bryggeskole/data/course_fact_registry.json` currently has **25** records (24 `verified`, one —
  `FACT-MASH-0003` — still `draft`): `FACT-BREW-0001..0003` (fermentation), `FACT-MASH-0001..0004`
  (mashing), `FACT-BOIL-0001..0004`/`FACT-HOP-0001..0003` (boil/hop), `FACT-COOL-0001..0003`/
  `FACT-OXY-0001..0003`/`FACT-TRANSFER-0001` (cool/transfer), and `FACT-PACK-0001..0004`
  (packaging, all `verified` — confirming #374's own registry-promotion pass landed). **Zero**
  existing records are about brewing methods, equipment layout, or method context. §6 identifies
  no existing record semantically sufficient to reuse for this issue's core method-identity claims
  (unlike Package's reuse of `FACT-COOL-0003`/`FACT-OXY-0002`) — every method-specific claim below
  is a new candidate. §2's opening chunk does reuse two existing records to ground its "same
  process" framing (see §2.0).
- Five topic-scoped pilot modules exist: `bryggeskole/pilot_mashing.py`,
  `bryggeskole/pilot_boil_hop.py`, `bryggeskole/pilot_cool_transfer.py`,
  `bryggeskole/pilot_fermentation.py`, `bryggeskole/pilot_package.py` — each its own copy with the
  identical function-name contract, explicitly "not a generalization... since none of the five
  pilots hardcodes anything beyond its own default file paths" (`pilot_package.py`'s own
  docstring). No `bryggeskole/pilot_prepare.py`/`pilot_method_context.py` or equivalent exists.
  This contract's §3 proposes a sixth topic-scoped pilot mirroring that same structural pattern,
  not a shared engine.
- `ui/bryggeskole_panel.py` (five real, clickable modules today: Mesking/Koking/Kjøling/Gjæring/
  Pakking, per its own current docstring — "fem reelle, åpne moduler... resten av brygge-reisen
  vist som 'Kommer senere'") is the productionized multi-module Bryggeskole UI. Its own six-stage
  process grid (`_PROSESS_STADIER`, lines 153–169) is **now fully mapped except its first stage**:
  `_STADIUM_TIL_MODUL` (lines 175–178) maps indices 1–5 (Mesking → Koking → Kjøling → Gjæring →
  Pakking) to the five live modules; **index 0** — `{"no": "Maling av malt", "en": "Milling the
  malt"}` in the hjemmebrygger environment, `{"no": "Mølle", "en": "Mill"}` in the bryggeri
  environment — remains the sole unmapped "Kommer senere" grid cell. This is concrete, already-
  built evidence of exactly one remaining pre-Mesking slot in the existing grid — see §5.
- `ui/bryggeskole_panel.py`'s own docstring states the Hjemmebrygger/Bryggeri environment chooser is
  "bevisst uendret fra issue #327: kun navigasjon/presentasjon, ingen nye kursfakta oppstår her"
  ("deliberately unchanged from issue #327: navigation/presentation only, no new course facts
  originate here") — a materially different axis (home vs. professional-scale context) from this
  issue's BIAB/traditional/all-in-one method axis, and one this contract does not propose
  repurposing (see §5).
- No existing App field anchors a BIAB/all-grain/all-in-one method choice anywhere: inspection of
  `ui/bryggeskole_panel.py`, `ui/process_panel.py`, `modules/i18n.py` and `config.py` found only one
  loose mention — `modules/i18n.py`'s own Hjemmebrygger environment description text, "Kjele/BIAB,
  bøtte/FermZilla, keg eller flaske" ("Kettle/BIAB, bucket/FermZilla, keg or bottle") — a single
  descriptive phrase, not a method selector, calculation surface, or process-profile field. This
  mirrors Package's own finding in `v22_g3f_package_module_contract.md` §5 ("no existing App/UI
  field to anchor to").
- `web/hjelp/bryggemetoder.html` (+ `web/en/hjelp/bryggemetoder.html`) already contains descriptive
  prose on BIAB, "vanlig all-grain (separat meskekar)" and "alt-i-ett bryggemaskin", plus
  batch/fly sparge and the App's own advanced mesh-profile methods (Hochkurz, dekoksjon, reiterated
  mash). Per the governing issue, this page is usable **only as a discovery aid** — it is not
  authoritative source truth, and no claim in §2 below is sourced from it. It did, however, help
  confirm the three method names/framing this contract uses and that the page's own scope already
  matches this issue's beginner boundary (its own closing note: "Flere metoder... kan legges til
  som egne kort her senere, uten å endre resten av siden" — the static page explicitly expects to
  stay separate from any future course module).
- `web/hjelp/utstyr-brewzilla.html` is brand/model-specific (BrewZilla) and is explicitly excluded
  as a source here per the governing issue's "no equipment-brand-specific assumptions" /
  "no brand/model dependence" constraints (§4, [Hard non-goals](#hard-non-goals)).

---

## 1. Minimum learner outcome

A learner who completes this module should be able to explain, in their own words, without naming
a specific bag/vessel/machine brand or a fixed numeric water/dead-space figure:

1. **All three supported method contexts still perform the same core brewing functions** — mash
   grain in controlled water/temperature, separate wort from grain in some form, boil the wort,
   then cool/ferment/package it — the method context changes *how* those functions are physically
   carried out, not *what* they fundamentally are.
2. **BIAB, as a concept** — the whole grain bill is mashed while contained in a bag placed directly
   in the same kettle/mash vessel already used elsewhere in the brew day; wort/grain separation
   happens by lifting the bag out (rather than draining through a separate lauter tun), which
   combines mashing and separation into fewer vessels than the traditional layout.
3. **Traditional separate-vessel all-grain, as a concept** — mashing happens in a dedicated
   mash/lauter vessel (often with a false bottom or similar filter medium), the wort is drained
   into a separate kettle, and the grain bed is typically sparged/rinsed separately to recover more
   sugar — a different equipment layout, not a different underlying mash chemistry from BIAB.
4. **All-in-one brewing machines, as a concept** — mashing and boiling (and often recirculation
   and/or built-in temperature control) are integrated into a single vessel, commonly using an
   internal basket/malt-pipe-style filter element to hold the grain and enable separation within
   that same vessel — the integration changes handling, not the underlying brewing principles.
5. **Method context affects practical planning, not brewing chemistry** — water volumes, dead
   space, grain handling, and the recirculation/sparging approach a brewer plans around can differ
   meaningfully by equipment/method, so a recipe's practical water/time planning should account for
   the brewer's own equipment rather than assuming one universal set of numbers applies to all
   three contexts.
6. **No method is inherently the "real" or "better" brewing path** — BIAB, traditional separate-
   vessel all-grain, and all-in-one machines are all legitimate, widely used all-grain approaches;
   the right choice for a given brewer is contextual (equipment, space, budget, batch size,
   workflow preference), not a quality ladder to climb.

**Explicitly not an outcome:** a specific bag/vessel/machine brand or model recommendation, a
numeric water-volume/dead-space/efficiency table or calculator, a claim that any one method is more
efficient/produces better beer than another, a full equipment buying guide, or coverage of
batch/fly sparge technique choice (already covered by `web/hjelp/bryggemetoder.html`'s own separate
"skyllemetoder" section, out of this module's scope per the governing issue's own beginner
boundary). None of these have a source attached in §2, and the governing issue's own non-goals
exclude them.

---

## 2. Proposed verified fact pack

**None of the records below exist in `bryggeskole/data/course_fact_registry.json` yet, and this
issue does not add them.** They are proposed candidates, in the exact record shape
[`BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md`](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) defines, for a
future, separately authorized editorial pass to review and (if it concurs) actually commit to the
registry — mirroring how `v22_g3f_package_module_contract.md` §2 and
`v22_g3d_cool_transfer_module_contract.md` §2 both flagged uncommitted candidate sources without
registering them itself.

**Source-verification note:** Chief completed a live citation pass on 2026-09-24.
Concrete claim-matched refs are now attached to each proposed record in §2.2. This resolves the prep
source gate only; `FACT-METHOD-0001..0005` still remain `draft` until a later authorized
Registry-promotion / implementation pass.

### 2.0 Shared process truth (chunk A) — reuse, no new record

Per the governing issue's own "reuse existing verified Kvernhaug facts/sources where semantically
sufficient" instruction (already applied by Package's contract for its sanitation/oxygen claims),
this pack does **not** propose a new record for beginner scope item 1 ("shared process truth"). It
proposes anchoring that framing on two already-verified records that describe the mash/boil
functions themselves independent of equipment:

- **`FACT-MASH-0001`** (verified, `mashing.starch_conversion`) — malt enzymes convert starch to
  fermentable sugar/dextrins during mashing, regardless of which vessel/method contains that mash.
- **`FACT-BOIL-0001`** (verified, `boil.enzyme_inactivation`) — boiling inactivates mash enzymes
  and reduces microbial load, regardless of which vessel produced the wort being boiled.

Both claims are already stated in equipment-neutral terms, so extending them to "this happens the
same way whichever of the three method contexts produced the mash/wort" is a direct, unmodified
application, not a new fact. No wording change to either registry record is proposed.

### 2.1 Candidate new records

| Proposed ID | Classification | Recommended status | Claim (summarized) |
|---|---|---|---|
| `FACT-METHOD-0001` | `documented_fact` | `draft` | BIAB: the full grain bill mashes in a bag inside the same kettle; separation happens by lifting the bag rather than draining through a separate lauter tun. |
| `FACT-METHOD-0002` | `documented_fact` | `draft` | Traditional all-grain: mashing and lautering happen in dedicated vessel(s), typically with a separate sparge step; a different equipment layout, not a different mash chemistry from BIAB. |
| `FACT-METHOD-0003` | `documented_fact` | `draft` | All-in-one machines integrate mash/boil (often plus recirculation/heating control) in one vessel, commonly via an internal basket/malt-pipe filter element; handling changes, not underlying chemistry. |
| `FACT-METHOD-0004` | `professional_interpretation` | `draft` | Water volumes, dead space, grain handling and recirculation/sparging approach can differ meaningfully by method/equipment; there is no single universal planning figure across all three contexts. |
| `FACT-METHOD-0005` | `professional_interpretation` | `draft` | BIAB, traditional all-grain and all-in-one machines are all legitimate approaches; method choice is contextual (equipment/space/budget/batch size/workflow), not a quality hierarchy. |

Five new candidate records — within the governing issue's own "roughly 5–8 records" guidance, plus
the two reused records in §2.0.

### 2.2 Full entries

**`FACT-METHOD-0001`** — *documented_fact*, draft
- **Claim:** In Brew In A Bag (BIAB), the full grain bill is mashed while contained inside a
  porous bag placed directly in the same kettle/mash vessel used for the rest of the brew day.
  Instead of draining wort through a separate lauter tun or false bottom, wort/grain separation
  happens by lifting the bag out of the kettle (commonly allowing it to drain, and sometimes
  followed by a simple dunk in additional hot water) — functionally combining the mash and
  separation steps into fewer vessels than the traditional layout in `FACT-METHOD-0002`.
- **Scope/limits:** Describes the mechanism only — does not assert BIAB always omits a separate
  sparge/rinse step (some BIAB brewers do dunk-sparge the bag), and does not assert BIAB is more or
  less efficient than traditional all-grain (no numeric efficiency claim, per the governing issue's
  hard non-goals). Does not name a specific bag material, size or brand.
- **Sources (Chief live-verified 2026-09-23):**
  - American Homebrewers Association, *Brew in a Bag (BIAB)*:
    https://www.homebrewersassociation.org/wp-content/uploads/How-To-Brew-in-a-Bag.pdf
    — describes BIAB as all-grain brewing in one kettle, grain contained in a bag and wort/grain
    separation by lifting/removing the bag; it also notes sparge variants.
  - American Homebrewers Association, *Homebrew Equipment*:
    https://www.homebrewersassociation.org/how-to-brew/homebrew-equipment/
    — independently describes BIAB bags and contrasts them with mash-tun/sparge equipment.
- **Wording traps to avoid:** never call BIAB "not real all-grain brewing" — the same whole-grain
  mash/conversion chemistry applies (see `FACT-MASH-0001`, reused in §2.0); never imply BIAB
  requires specialized equipment beyond a bag and a kettle; never state BIAB is universally more or
  less efficient than the other two methods.

**`FACT-METHOD-0002`** — *documented_fact*, draft
- **Claim:** In traditional separate-vessel all-grain brewing, mashing takes place in a dedicated
  mash/lauter vessel — often using a false bottom, braided-hose manifold, or similar filter medium
  to form a "grain bed" — and the resulting wort is drained into a separate brewing kettle,
  typically with an additional sparge step rinsing the grain bed with more hot water to recover
  further sugar. Using a dedicated mash/lauter vessel is a matter of equipment/process layout, not
  a separate underlying brewing chemistry from BIAB (`FACT-METHOD-0001`) or an all-in-one system
  (`FACT-METHOD-0003`).
- **Scope/limits:** Describes the vessel/separation layout only — does not compare traditional
  all-grain's efficiency or output quality against the other two methods, and does not describe or
  favor a specific sparge technique (batch vs. fly sparge remains `web/hjelp/bryggemetoder.html`'s
  own separate, unsourced-here discovery-aid content, explicitly out of this module's beginner
  scope).
- **Sources (Chief live-verified 2026-09-24):**
  - American Homebrewers Association, *Homebrew Equipment*:
    https://www.homebrewersassociation.org/how-to-brew/homebrew-equipment/
    — describes the mash tun as the vessel that holds the mash and separates wort from grain, plus
    separate sparge-water handling and grain-bed recirculation/vorlauf.
  - MoreBeer, *All Grain Brewing Instructions*:
    https://morebeer.com/collections/all-grain-brewing-instructions
    — explicitly contrasts BIAB/single-vessel brewing with a three-vessel mash-tun setup and
    describes the designated mash-tun / false-bottom workflow.
- **Wording traps to avoid:** never imply the mash chemistry itself differs from BIAB's — same
  starch-conversion process (`FACT-MASH-0001`, reused); never present traditional all-grain as the
  "proper" or "real" method relative to the other two.

**`FACT-METHOD-0003`** — *documented_fact*, draft
- **Claim:** An all-in-one brewing system integrates mashing and boiling — and often wort
  recirculation and/or built-in heating/temperature control — into a single vessel, commonly using
  an internal perforated basket, malt pipe, or similar filter element to hold the grain bed for
  mashing and enable wort/grain separation within that same vessel, rather than requiring the
  brewer to physically move wort between separate mash and boil vessels. Recirculating the wort
  through the grain bed (where present) and electric heating/temperature control change how a
  brewer manages the process without changing the underlying mash/boil chemistry already described
  in `FACT-MASH-0001`/`FACT-BOIL-0001`.
- **Scope/limits:** Describes the category-level mechanism only — does not name, recommend, or
  compare a specific all-in-one brand/model (`web/hjelp/utstyr-brewzilla.html`'s brand-specific
  content is explicitly excluded here), and does not assert all-in-one systems are more efficient,
  easier, or otherwise "better" than the other two methods.
- **Sources (Chief live-verified 2026-09-23):**
  - Grainfather, *G30 Brewing System Showcase*:
    https://us.grainfather.com/pages/g30-showcase
    — current manufacturer example of an all-in-one all-grain system combining electric temperature
    control, mashing/sparging functions and a grain basket in one integrated system.
  - Grainfather, *Compare the Grainfather Brewing Systems*:
    https://us.grainfather.com/pages/compare-the-grainfather-brewing-systems
    — documents all-in-one functionality and perforated grain-basket designs across multiple systems.
  - American Homebrewers Association, *Team Homebrewing Ups Your Game*:
    https://www.homebrewersassociation.org/homebrew-community-culture/team-homebrewing-ups-your-game/
    — independently identifies all-in-one electric systems as a distinct homebrewing equipment
    approach alongside three-vessel and gravity-fed mash/kettle setups.
- **Wording traps to avoid:** never name a specific brand/model as defining "all-in-one"; never
  imply built-in recirculation/heating changes the underlying starch-conversion or
  enzyme-inactivation chemistry (`FACT-MASH-0001`/`FACT-BOIL-0001`, reused); never present
  all-in-one as the most "advanced" or objectively best method.

**`FACT-METHOD-0004`** — *professional_interpretation*, draft
- **Claim:** Regardless of which method context is used, the water volumes, dead space, grain
  handling, and recirculation/sparging approach a brewer needs to plan for can differ meaningfully
  by equipment/method — for example, a bag-based system's absorption/retention characteristics and
  a false-bottom or malt-pipe system's dead space are not identical — so a recipe's practical
  water/time planning should account for the brewer's own equipment rather than assuming one
  universal set of numbers works identically across BIAB, traditional all-grain, and all-in-one
  systems.
- **Scope/limits:** States the *existence and direction* of this planning difference only — does
  not provide or endorse a specific liter figure, dead-space table, or equipment-specific formula
  (explicit hard non-goal: "no numeric water-profile/equipment calculator lesson"), and does not
  claim one method always requires strictly more or less water/time than another as a universal
  rule.
- **Sources (Chief live-verified 2026-09-23):**
  - American Homebrewers Association, *Brew in a Bag (BIAB)*:
    https://www.homebrewersassociation.org/wp-content/uploads/How-To-Brew-in-a-Bag.pdf
    — shows BIAB strike-water planning depends on grain absorption, target pre-boil volume and the
    brewer's own boil-off behavior.
  - MoreBeer, *All Grain Brewing Instructions*:
    https://morebeer.com/collections/all-grain-brewing-instructions
    — explicitly distinguishes single-vessel/BIAB water planning from three-vessel mash-tun planning
    and calls out equipment dead space as a planning input.
  - The documented method/equipment sources for `FACT-METHOD-0001..0003` above complete the basis
    for this synthesis; no fixed liters, percentages or universal equipment values are promoted here.
- **Wording traps to avoid:** never state a specific liter/percentage dead-space number as a fixed
  rule; never imply one method's planning is strictly "harder" or "easier" than another's; never
  turn this into an equipment calculator lesson.

**`FACT-METHOD-0005`** — *professional_interpretation*, draft
- **Claim:** BIAB, traditional separate-vessel all-grain, and all-in-one brewing machines are all
  legitimate, widely used all-grain homebrewing approaches that share the same underlying mash/
  boil/cool/ferment/package process (`FACT-MASH-0001`, `FACT-BOIL-0001`, reused in §2.0). The
  appropriate choice for a given brewer depends on contextual factors — available equipment, space,
  budget, batch size, and workflow preference — not on any one method being inherently a "better,"
  more advanced, or more "real" brewing method than the others.
- **Scope/limits:** A synthesis/interpretation drawing on `FACT-METHOD-0001`/`FACT-METHOD-0002`/
  `FACT-METHOD-0003`/`FACT-METHOD-0004` and reused `FACT-MASH-0001`/`FACT-BOIL-0001`, not a new
  independently measured result — mirrors the precedent already set by `FACT-PACK-0004` and
  `FACT-MASH-0004`. Does not claim every homebrewer's context makes all three methods equally
  convenient in practice — only that none is inherently a "better beer" marker.
- **Sources (Chief live-verified 2026-09-24):**
  - American Homebrewers Association, *Brew in a Bag (BIAB)*:
    https://www.homebrewersassociation.org/wp-content/uploads/How-To-Brew-in-a-Bag.pdf
    — establishes BIAB as a legitimate all-grain method using the same downstream boil/post-boil
    process.
  - American Homebrewers Association, *Team Homebrewing Ups Your Game*:
    https://www.homebrewersassociation.org/homebrew-community-culture/team-homebrewing-ups-your-game/
    — documents three-vessel, all-in-one electric and gravity-fed mash/kettle approaches being used
    side by side in real homebrewing practice.
  - MoreBeer, *All Grain Brewing Instructions*:
    https://morebeer.com/collections/all-grain-brewing-instructions
    — states that BIAB/single-vessel and three-vessel methods are similar in underlying theory and
    can be adapted across all-in-one systems.
  - Grainfather, *G30 Brewing System Showcase*:
    https://us.grainfather.com/pages/g30-showcase
    — establishes an integrated all-in-one all-grain method context.
  - This record remains a `professional_interpretation`: “not a quality hierarchy” is a bounded
    pedagogy/product synthesis and does not claim equal convenience, cost or efficiency.
- **Wording traps to avoid:** never present BIAB as "the beginner method," traditional all-grain as
  "proper brewing," or all-in-one as automatically producing better/worse beer, in any direction;
  never imply a brewer must eventually "graduate" from one method to another; keep "same underlying
  process" as the framing, never "same convenience/cost," which this claim does not assert.

---

## 3. Module contract

### 3.1 Proposed topic id

`PILOT-METHOD-CONTEXT-FUNDAMENTALS` — mirrors the existing `PILOT-MASHING-FUNDAMENTALS` /
`PILOT-BOIL-HOP-FUNDAMENTALS` / `PILOT-COOL-TRANSFER-FUNDAMENTALS` / `PILOT-PACKAGE-FUNDAMENTALS`
naming convention already used by the five existing pilot files. Proposed module reference for
`sources[].modules` / registry `concepts` grouping: `method_context.fundamentals`.

### 3.2 Learning chunks (5 — within the governing issue's own "about five chunks" target)

Each chunk below is a **structural proposal** (id, source claim(s), teaching intent) — not finished
bilingual copy, mirroring every prior contract's own precedent of leaving final NO/EN teaching
prose to a later implementation child, once the underlying facts are actually reviewed/promoted.
Chunk order follows the governing issue's own proposed pedagogical order A–E exactly; no evidence
surfaced during this prep pass to justify changing it.

| Chunk ID | `source_claims` | Teaching intent (one sentence) |
|---|---|---|
| `CHUNK-METHOD-A` | `FACT-MASH-0001` (reused), `FACT-BOIL-0001` (reused) | Same brewing goal/process across all three method contexts — mash, separate, boil, cool/ferment/package happen every time, only the equipment layout differs. |
| `CHUNK-METHOD-B` | `FACT-METHOD-0001` | BIAB: whole grain bill mashed in a bag inside the kettle; separation by lifting the bag, not a separate lauter tun. |
| `CHUNK-METHOD-C` | `FACT-METHOD-0002` | Traditional all-grain: dedicated mash/lauter vessel(s) plus a separate sparge step — same mash chemistry as BIAB, different equipment layout. |
| `CHUNK-METHOD-D` | `FACT-METHOD-0003` | All-in-one machines: mash and boil integrated in one vessel, often with recirculation/heating control — handling changes, not underlying chemistry. |
| `CHUNK-METHOD-E` | `FACT-METHOD-0004`, `FACT-METHOD-0005` | Choosing a method context is practical/contextual, not a quality hierarchy; planning details (water, dead space, handling) do change by method even though the beer chemistry doesn't. |

### 3.3 Scenarios/questions

Mirroring the five existing pilots' `concept_check`/`scenario` question types and
`evaluate_answer()` contract (never a raw numeric score), one substantive question per chunk is
proposed, each declaring `source_claims` that must resolve against the **verified-only** registry
API (`get_verified_record`), exactly as the five existing pilots already require. This means none
of these questions could actually ship until `FACT-METHOD-0001..0005` are promoted past `draft` —
`CHUNK-METHOD-A` is the one exception, since both of its reused facts (`FACT-MASH-0001`,
`FACT-BOIL-0001`) are already `verified` today.

Representative scenario shapes (final wording is implementation-child work, same reasoning as
§3.2):

- **Scenario** on `CHUNK-METHOD-A`: a learner is told that one friend brews with BIAB and another
  uses a separate mash/lauter vessel, and asks whether their two batches undergo fundamentally
  different brewing chemistry — tests whether the learner recognizes the shared mash/boil process
  underneath the different equipment.
- **Concept check** on `CHUNK-METHOD-B`: distinguishing "BIAB mashes and separates using a bag in
  the same kettle" from an overclaim like "BIAB isn't really all-grain brewing" — tests that the
  learner understands BIAB as a layout variant of all-grain, not a different/lesser process.
- **Concept check** on `CHUNK-METHOD-C`: distinguishing traditional separate-vessel all-grain
  (dedicated mash/lauter vessel plus sparge) from BIAB (`CHUNK-METHOD-B`) — tests that the learner
  identifies the equipment/layout difference without concluding the underlying chemistry differs.
- **Scenario** on `CHUNK-METHOD-D`: a learner sees an all-in-one system actively recirculating wort
  through a malt pipe during mashing and asks whether that recirculation is "a different kind of
  brewing chemistry" than a kettle-and-bag setup — tests that the learner attributes the difference
  to handling/equipment, not to a different underlying process.
- **Scenario** on `CHUNK-METHOD-E`: a learner who has been brewing BIAB successfully asks whether
  they should "upgrade" to an all-in-one machine to make better beer, or whether their water/dead-
  space numbers from a BIAB recipe will transfer unchanged to a traditional separate-vessel setup —
  tests both the "no hierarchy" point and the "planning details do change by method" point in the
  same scenario, mirroring how the governing issue itself pairs beginner scope items 5 and 6.

### 3.4 Feedback intent

Same pattern as the five existing pilots: `feedback_correct`/`feedback_incorrect` strings giving a
short, plain-language explanation of *why*, hedged consistently with each fact's own scope/limits
(§2.2) — never a bare "right"/"wrong," and never asserting more certainty than the underlying fact
supports (e.g. never implying one method is objectively better, per `FACT-METHOD-0005`'s own
wording-trap note; never implying BIAB skips real all-grain chemistry, per `FACT-METHOD-0001`'s own
wording-trap note). No aggregate score is ever shown to the learner, consistent with `#65`'s
"hidden mastery, not a raw score" principle and the existing `evaluate_answer()` contract.

### 3.5 Hidden mastery/repetition implications

No new mastery engine or scheduling logic — this module would reuse `bryggeskole/mastery.py`'s
existing `apply_answer()`/`mastery_label()` exactly as the five existing pilots already do.
Proposed concept ids, following the existing English `domain.concept` convention already used by
the shipped pilots (`mashing.temperature`, `hop.isomerization_time`, `cool.speed`,
`package.priming`, …):

- `method.shared_process` (`CHUNK-METHOD-A`, `FACT-MASH-0001`/`FACT-BOIL-0001` — both **reused
  ids**, not new ones, so a learner's existing mastery on these two concepts from the Mesking/Koking
  modules carries straight over — the same "shared mastery across modules" mechanism §0 and
  `v22_g3f_package_module_contract.md` §3.5 already documented for `cool.sanitation_boundary`/
  `oxygen.post_pitch`).
- `method.biab` (`CHUNK-METHOD-B`, `FACT-METHOD-0001`)
- `method.traditional_allgrain` (`CHUNK-METHOD-C`, `FACT-METHOD-0002`)
- `method.all_in_one` (`CHUNK-METHOD-D`, `FACT-METHOD-0003`)
- `method.planning_variables` (`CHUNK-METHOD-E`, `FACT-METHOD-0004`)
- `method.no_hierarchy` (`CHUNK-METHOD-E`, `FACT-METHOD-0005`)

`CHUNK-METHOD-A` intentionally maps to two reused concept ids under one chunk, and `CHUNK-METHOD-E`
intentionally maps to two new concept ids under one chunk — both mirror the precedent already set
by cool/transfer's `CHUNK-COOLXFER-D` (three concept ids under one chunk) and Package's
`CHUNK-PACK-D` (two concept ids under one chunk): a chunk can teach more than one trackable concept
without needing a strict 1:1 chunk-to-concept ratio.

No V2-3C adaptive/spaced-repetition scheduler exists yet (unchanged since every prior contract's
own check) — this module would surface hidden mastery labels exactly the way the existing five
modules already do, with no new repetition mechanism invented for method context specifically.

### 3.6 NO/EN requirements

Same bilingual shape already enforced by the five existing pilots' `_validate_bilingual_text()` —
every chunk `text`, question `prompt`, option `text`, and `feedback_correct`/`feedback_incorrect`
must carry both a `no` and an `en` value, validated fail-closed exactly like the existing modules.
No new i18n mechanism is proposed; this is a direct reuse of the existing pilot content contract.

**Terminology guidance for the later NO/EN authoring pass** (not authored here — flagging the exact
Norwegian brewing terms an author would need):

| Concept | Norwegian | English |
|---|---|---|
| BIAB / mash bag | Kornpose / meskepose (BIAB brukes også direkte på norsk) | BIAB / mash bag |
| Mash/lauter tun | Meskekar / lauterkar | Mash tun / lauter tun |
| False bottom | Falskbunn | False bottom |
| Sparge / rinse the grain bed | Skylle kornresten / skylling | Sparge / rinse the grain bed |
| All-in-one brewing system | Alt-i-ett bryggemaskin | All-in-one brewing system |
| Malt pipe / basket | Malt-rør / kurv | Malt pipe / basket |
| Recirculation | Resirkulering | Recirculation |
| Dead space | Dødvolum | Dead space |
| Method / equipment context | Bryggemetode / utstyrskontekst | Brewing method / equipment context |

`ui/bryggeskole_panel.py`'s existing `_MODULER[...]["tittel_nokkel"]` pattern (proposed,
`"bryggeskole.modul.metodevalg.tittel"`) and new `_KONSEPT_LABELS` entries for the concept ids in
§3.5 are implementation-child work, not authored here — listed to keep this contract's terminology
consistent with what that later step will need.

---

## 4. Visual requirement

**Recommendation: "same process spine → three equipment layouts" — exactly the concept the
governing issue itself prefers, and the smallest meaningful visual, not a decorative
illustration.**

Three parallel, equal-weight horizontal rows, each showing the identical downstream process spine
(Mesk → Skille vørt fra korn → Kok → Kjøl → Gjær → Pakk / Mash → Separate wort from grain → Boil →
Cool → Ferment → Package), but with a different equipment icon/label at the "Mesk → Skille"
segment only:

- **BIAB-rad:** Kjele + pose (kettle + bag) — one shared vessel, separation by lifting the bag
  (supports `CHUNK-METHOD-B`);
- **Tradisjonell-rad:** Meskekar/lauterkar → Kjele (mash/lauter vessel → kettle) — two vessels, a
  drain/sparge step between them (supports `CHUNK-METHOD-C`);
- **Alt-i-ett-rad:** Ett integrert kar + kurv/malt-rør (one integrated vessel + basket/malt pipe) —
  one vessel handling both functions (supports `CHUNK-METHOD-D`);

All three rows visually reconverge onto the exact same "Kok → Kjøl → Gjær → Pakk" icon sequence,
drawn identically across all three rows — the single strongest visual reinforcement of §1's "same
process, different layout" outcome and `CHUNK-METHOD-A`'s teaching point, and directly supports the
"no quality hierarchy" requirement by drawing all three rows with identical box sizes, stroke
weights and vertical prominence (mirrors `bryggeskole/package_flow.py`'s own "deliberately equal
visual weight" technique for its two packaging paths).

This is deliberately **not** proposed as fully interactive in V1, for the same reasoning every
prior Bryggeskole visual contract already applied: a static, well-labeled diagram already carries
the "same spine, different layout, no hierarchy" understanding this topic needs. An optional future
enhancement — clicking a row to open its matching chunk — mirrors the same low-complexity,
context-preserving judgment made for all four prior Bryggeskole visuals, but is not required for a
first usable slice. No 3D/game-engine visual is proposed (explicit hard non-goal). No equipment
catalogue and no brand/model icon — each row shows the generic layout shape (bag / two vessels /
integrated vessel+basket), never a specific bag material, false-bottom design, or machine
brand/model.

A future implementation would mirror `bryggeskole/cool_transfer_flow.py`/`bryggeskole/
package_flow.py`'s own pattern — its own, standalone, pure SVG-generating module (e.g.
`bryggeskole/method_context_flow.py`), not a shared/generalized flow-diagram engine, consistent
with every other Bryggeskole visual module to date.

---

## 5. Recommended UI/integration surface

**Recommendation: reuse the existing, already-unmapped first grid slot — no new "stage 0", no
course-navigation-framework rewrite.**

`ui/bryggeskole_panel.py`'s own six-stage `_PROSESS_STADIER` grid (§0) already has exactly one
unmapped cell: index 0 (`"Maling av malt"`/`"Milling the malt"` in the hjemmebrygger environment,
`"Mølle"`/`"Mill"` in the bryggeri environment), still `"Kommer senere"` since `_STADIUM_TIL_MODUL`
only maps indices 1–5. This is the smallest possible integration surface: the grid cell already
sits immediately before Mesking, already exists as a distinct clickable-in-the-future slot, and
needs no restructuring — only extending `_STADIUM_TIL_MODUL` with one new `0: _MODUL_METODEVALG`
entry once an actual module exists, exactly the same mechanical step each of the five prior modules
already went through for their own index.

This satisfies the governing issue's own "least disruptive integration surface" requirement more
directly than either alternative it lists:

- **A short orientation module/card before Mesking** — this recommendation **is** that option,
  concretely anchored to the one slot the grid already reserves for exactly this position, rather
  than a newly invented one.
- **Contextual environment chooser content** — assessed and **not** recommended: the existing
  Hjemmebrygger/Bryggeri chooser is a different axis entirely (home vs. professional-scale
  brewing context, not BIAB/traditional/all-in-one method), and its own docstring explicitly states
  it is "navigation/presentation only, no new course facts" (issue #327) — repurposing it to carry
  new verified-fact-backed teaching content would conflict with that already-stated design
  constraint, not extend it cleanly.

Chief decision for the bounded implementation slice: reuse this existing first grid position, but
rename its learner-facing stage label so it does not misleadingly say only “Maling av malt/Mill”.
Use **“Forberedelse/metode” / “Preparation/method”** (with equivalent brewery-context wording if
needed) and implement the content as the same kind of compact topic-scoped pilot as the five existing
modules. This preserves the process spine, avoids a navigation rewrite and still satisfies the
required chunks/questions/mastery contract.

No App-side (non-Bryggeskole) integration surface was found to anchor a future Learn→Plan-style
bridge onto: unlike Mesking/Boil-hop/Cool-transfer (each anchored to an existing App field), and
matching Package's own finding in `v22_g3f_package_module_contract.md` §5, no BIAB/all-grain/
all-in-one method selector exists anywhere in the App today (§0). A future bridge, if ever wanted,
would first need its own new field/decision — not attempted here, and not required by this issue.

---

## 6. Registry reuse/new-record map

| Fact | Status now | Reused or new | Concept id(s) | Chunk |
|---|---|---|---|---|
| `FACT-MASH-0001` | `verified` | Reused, unmodified | `method.shared_process` (new alias concept alongside its existing `mashing.starch_conversion`) | `CHUNK-METHOD-A` |
| `FACT-BOIL-0001` | `verified` | Reused, unmodified | `method.shared_process` (new alias concept alongside its existing `boil.enzyme_inactivation`) | `CHUNK-METHOD-A` |
| `FACT-METHOD-0001` | Does not exist | New candidate | `method.biab` | `CHUNK-METHOD-B` |
| `FACT-METHOD-0002` | Does not exist | New candidate | `method.traditional_allgrain` | `CHUNK-METHOD-C` |
| `FACT-METHOD-0003` | Does not exist | New candidate | `method.all_in_one` | `CHUNK-METHOD-D` |
| `FACT-METHOD-0004` | Does not exist | New candidate | `method.planning_variables` | `CHUNK-METHOD-E` |
| `FACT-METHOD-0005` | Does not exist | New candidate | `method.no_hierarchy` | `CHUNK-METHOD-E` |

Chief decision on `method.shared_process`: use it as a **module-local mastery concept** for the
shared-process question/chunk, while keeping the existing Registry `concepts` on
`FACT-MASH-0001` and `FACT-BOIL-0001` unchanged. The implementation may add the method module to
those records' `modules` lists to record genuine cross-module reuse, but it must not invent a second
Registry truth or rewrite their existing concept semantics.
---

## 7. Non-goals

Restated from the governing issue, since this document's own recommendations must not silently
cross them:

- No Bryggeskole module/UI code was written or changed.
- No Course Fact Registry mutation was made — §2's records are proposals only, all at `draft`, none
  committed to `bryggeskole/data/course_fact_registry.json`.
- No pilot-content file (`bryggeskole/data/pilot_method_context_fundamentals.json` or similar) was
  created.
- No `ui/bryggeskole_panel.py` change was made — §5's `_STADIUM_TIL_MODUL` extension is described,
  not implemented.
- No visual module (`bryggeskole/method_context_flow.py` or similar) was created — §4 is a contract
  only.
- No numeric water-volume/dead-space/equipment calculator was authored (no numbers appear in §2's
  claims beyond describing that a difference exists).
- No equipment purchase recommendation, supplier comparison, or brand/model-specific teaching was
  authored — `web/hjelp/utstyr-brewzilla.html`'s brand-specific content was explicitly not reused.
- No recipe changes, framework/engine, Web/public productization, or deployment.

## Hard non-goals

(Restated verbatim from issue #376 for traceability — this document does not violate any of
these.)

- no module/UI implementation;
- no Course Fact Registry mutation/promotion;
- no equipment purchase recommendations;
- no supplier comparison;
- no brand/model-specific teaching;
- no numeric water-profile/equipment calculator lesson;
- no recipe changes;
- no Web/public deployment;
- no professional brewery curriculum;
- no Sóti/AI;
- no new mastery engine;
- no generalized course-framework rewrite.

---

## 8. Chief decisions / implementation-ready state

The prep blockers are resolved for the bounded implementation child:

1. **Citation gate — RESOLVED.** Chief completed the live source pass on 2026-09-24; concrete refs
   are attached in §2.2. New records remain `draft` until the implementation/editorial pass.
2. **Grid placement/copy — RESOLVED.** Reuse the existing first process-grid position and rename its
   learner-facing label to **Forberedelse/metode / Preparation/method** rather than presenting the
   broader module under a misleading “Maling av malt/Mill” label.
3. **Presentation weight — RESOLVED.** Implement as a compact sixth topic-scoped pilot using the
   existing chunks/questions/mastery machinery; do not create a new course engine.
4. **Shared-process mastery — RESOLVED.** `method.shared_process` is module-local mastery wiring;
   do not add it as a second Registry concept on `FACT-MASH-0001`/`FACT-BOIL-0001`.
5. **NO terminology — RESOLVED for first implementation.** Use **“meskepose (BIAB)”** on first
   introduction, then “meskepose”/“BIAB” naturally thereafter.

No owner product decision remains before the bounded implementation slice. Fresh owner GO is still
required for merging this prep PR, per normal governance.
