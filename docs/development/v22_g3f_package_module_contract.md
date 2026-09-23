# V2.2 G3F — Package verified fact pack + module contract

Version: 1.0
Status: PREP/decision document — candidate fact pack proposed, sources are Claude's best-effort
candidates only (this Bridge run has no live network/source-fetch access — see §2); all proposed
records remain `draft` until a separately authorized citation-verification + registry-promotion pass
Governed by: [#372](https://github.com/Joludvig/kvernhaug-brygghus/issues/372), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3), the Goal 3
gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358), the merged Kjøling/
overføring module ([#370](https://github.com/Joludvig/kvernhaug-brygghus/issues/370) / PR #371,
prepared by [#368](https://github.com/Joludvig/kvernhaug-brygghus/issues/368) / PR #369), and
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction)
Authoritative base at creation: `f1dc9452dec51b0281357ba14065e3220b45cb46`

This is a **READ/PREP-only** document. It contains no module/UI implementation, no Course Fact
Registry mutation, and no App/Web/Core file changes — see [Hard non-goals](#hard-non-goals). It does
not authorize implementing a Package Bryggeskole module; it only prepares the fact pack and module
contract Chief would need to authorize that work.

---

## 0. Why Package, and what already exists

Per #358's gap map, Package was flagged as the other weakest MUST stage after cool/transfer, and
cool/transfer is now merged and live (#370 / PR #371 — "V2.2 G3E"). With Mesking, Koking/humle,
Kjøling/overføring and Gjæring all implemented, Package is the next missing physical-process stage
before Bryggeskole can honestly claim a coherent path from finished fermentation to a packaged,
drinkable beer.

**Current repo state relevant to this prep, confirmed by inspection:**

- `bryggeskole/data/course_fact_registry.json` currently has **21** verified/draft records:
  `FACT-BREW-0001..0003` (fermentation), `FACT-MASH-0001..0004` (mashing, one still `draft`),
  `FACT-BOIL-0001..0004`/`FACT-HOP-0001..0003` (boil/hop), and `FACT-COOL-0001..0003`/
  `FACT-OXY-0001..0003`/`FACT-TRANSFER-0001` (cool/transfer, all `verified`). **Zero** are about
  packaging, priming, carbonation, or container/pressure safety. §2 identifies two of these existing
  **verified** records that already cover part of this issue's beginner scope and proposes reusing
  them rather than duplicating — the rest of the gap needs new candidate records.
- Four topic-scoped pilot modules exist: `bryggeskole/pilot_mashing.py`,
  `bryggeskole/pilot_boil_hop.py`, `bryggeskole/pilot_cool_transfer.py`,
  `bryggeskole/pilot_fermentation.py` — each its own copy with the identical function-name contract
  (`pilot_cool_transfer.py`'s own docstring: "this module is deliberately its own topic-scoped copy,
  not a generalization of those modules, since none of the four pilots [is] a shared engine"). No
  `bryggeskole/pilot_package.py` or equivalent exists. This contract's §3 mirrors that same
  structural pattern for a fifth pilot rather than proposing a shared engine.
- `ui/bryggeskole_panel.py` (four real, clickable modules today: Mesking/Koking/Kjøling/Gjæring) is
  the productionized multi-module Bryggeskole UI (#338, extended by #366 for Koking and #370 for
  Kjøling/overføring). Its own six-stage process grid (`_PROSESS_STADIER`, lines 137–153, per issue
  #327's "malt/milling → mash → boil → cooling → fermentation → packaging" requirement) **already
  includes a sixth stage** — `{"no": "Tapping/flasking", "en": "Kegging/bottling"}` in the
  hjemmebrygger environment, `{"no": "Pakking/CIP", "en": "Packaging/CIP"}` in the bryggeri
  environment — that is currently orientation-only ("Kommer senere"): `_STADIUM_TIL_MODUL` (lines
  158–160) maps only stage indices 1–4 to the four live modules, leaving index 5 unmapped. This is
  concrete, already-built evidence that a fifth Package module was anticipated and has an exact,
  ready integration slot — see §5.9.
- The App has no dedicated packaging/carbonation calculation surface, and (confirmed by inspection of
  `ui/brewday_panel.py`) the brew-day checklist (`_SJEKKLISTE`, lines 24–27) and its six expanders end
  at **"5. Gjæring"** (`bd_pitch_temp`, `bd_inkbird_temp`, `bd_ferm_pressure`, `bd_transfer_note`) —
  there is currently no bottling/kegging/priming field anywhere in the brew-day plan. This is a
  materially different situation from cool/transfer, mashing and boil/hop, each of which found an
  *existing* UI field to anchor a future Learn→Plan bridge to (§6 below has no such field to point at
  yet).
- No static Web prose on bottling/kegging/priming/force-carbonation was found under `web/hjelp/`
  during this prep pass (`web/hjelp/klaring.html` covers clarification/cold-side terms only,
  `web/hjelp/trykkgjaering.html` covers pressure *fermentation*, a different and explicitly
  out-of-scope topic — see [Hard non-goals](#hard-non-goals)). Per the governing issue, this document
  does not reuse or depend on Web prose regardless; every claim in §2 is independently stated and
  sourced here.

---

## 1. Minimum learner outcome

A learner who completes this module should be able to explain, in their own words, without needing a
specific bottle/keg brand or a universal numeric carbonation schedule:

1. **Packaging continues the same sanitized-handling boundary already taught in cool/transfer** —
   from `FACT-COOL-0003`: any surface that will touch the finished beer from cooling onward needs to
   be clean and sanitized, and that boundary does not end at the fermenter — it extends through every
   piece of packaging equipment (bottling wand/siphon, bottles and caps, keg and its fittings/tap)
   that will subsequently contact the beer.
2. **Bottle conditioning / priming, as a concept** — adding a small, measured amount of fermentable
   ("priming") sugar to beer before sealing it into bottles restarts a small, renewed fermentation
   inside the sealed bottle; because the resulting CO₂ has nowhere to escape, it dissolves into the
   beer and carbonates it. The right amount depends on the specific beer and the carbonation level
   wanted — there is no single universal number that fits every batch.
3. **Keg / force-carbonation, as a concept** — beer can also be carbonated without any renewed
   fermentation, by connecting a sealed keg to an external CO₂ source under pressure; how much CO₂
   ends up dissolved in the beer depends on the applied pressure, the beer's temperature, and time —
   this module teaches the concept and the variables involved, not a specific numeric
   pressure/temperature/time schedule.
4. **Oxygen after fermentation still matters at packaging** — reusing the already-verified
   `FACT-OXY-0002` rather than re-teaching it: once fermentation is actively underway (which it
   already is by the time a beer is being packaged), unnecessary splashing/air pickup should still be
   minimized during whichever transfer packaging requires, for the same oxidation-risk reasons
   already taught in cool/transfer — this is continuity, not a new claim.
5. **Packaging into a sealed container creates internal pressure, and that has safety implications** —
   whichever path is chosen, the container ends up sealed and carbonated/conditioned, which means it
   holds pressure; using containers/equipment not actually intended or rated for that pressure (e.g. a
   non-beer glass bottle, a damaged or already-stressed bottle, an incompatible cap or fitting) risks
   unsafe overpressure or container failure. The learner should come away knowing *that* this risk
   exists and *why* container/equipment suitability matters — not a pressure-vessel engineering
   lesson.
6. **Packaging method is a practical choice, not a quality hierarchy, and both paths reach the same
   natural completion point** — bottling and kegging are both legitimate, commonly used homebrewing
   paths; the right choice for a given brewer depends on equipment, budget, storage space and how the
   beer will be served, not on one method producing objectively better beer. Either path, once
   properly sanitized, primed/carbonated and given time to condition, arrives at the same natural end
   point of the finishable homebrewer journey: beer that is carbonated, conditioned and ready to
   serve or store.

**Explicitly not an outcome:** a numeric priming-sugar calculation, a numeric keg
pressure/temperature/time carbonation schedule, naming or comparing specific bottle/keg/CO₂-system
brands or models, a pressure-vessel engineering explanation, or draft-system/dispense balancing.
None of these have a source attached in §2, and the governing issue's own non-goals exclude them.

---

## 2. Proposed verified fact pack

**None of the four new records below exist in `bryggeskole/data/course_fact_registry.json` yet, and
this issue does not add them.** They are proposed candidates, in the exact record shape
[`BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md`](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) defines, for a
future, separately authorized editorial pass to review and (if it concurs) actually commit to the
registry — mirroring how `v22_g3d_cool_transfer_module_contract.md` §2 (and, before that,
`v22_g3b_boil_hop_module_contract.md` §2 and `V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` §4) flagged
uncommitted candidate sources without registering them itself.

**Source-verification note (read before §2.2):** this Bridge run has no live network/source-fetch
access, so — unlike `v22_g3d_cool_transfer_module_contract.md`'s *final* state (which already
reflects Chief's subsequent live citation pass) — the source refs below are Claude's best-effort
candidates only: real organizations and publications, named by type and topic per the governing
issue's own "Source rules" priority list, but **not** live-verified exact URLs. Where an exact URL is
given below, it is a plausible candidate only, not a confirmed live source. Every one of these needs
Chief's separate live citation-verification pass — the same process cool/transfer's own first round
(#368) went through — before any record could be promoted past `draft`.

**Reuse-first: two existing verified records already cover part of this scope.** Per the governing
issue's own instruction ("reuse existing verified Kvernhaug facts/sources where semantically
sufficient" for sanitation/oxygen claims), this pack does **not** propose new records for beginner
scope items 1 and 4 — it proposes reusing:

- **`FACT-COOL-0003`** (verified, `cool.sanitation_boundary`) for beginner scope item 1 (packaging
  sanitation boundary). Its claim already generalizes to "any tool used from this point forward" and
  explicitly lists "fermenter" among covered surfaces — packaging equipment (bottling wand/siphon,
  bottles/caps, keg/fittings/tap) is a direct, unmodified extension of the same already-verified
  claim, not a new fact. No wording change to the registry record is proposed.
- **`FACT-OXY-0002`** (verified, `oxygen.post_pitch`) for beginner scope item 4 (oxygen after
  fermentation). Its claim already covers "any transfer performed after active fermentation has
  begun" — packaging transfer (racking to a bottling bucket, or to a keg) is exactly such a transfer,
  not a new fact.

This reuse is also the concrete instance of `ui/bryggeskole_panel.py`'s own documented cross-module
design goal — "delt verifisert kunnskap + delt mastery på tvers av moduler" ("shared verified
knowledge + shared mastery across modules") — the same concept ids (`cool.sanitation_boundary`,
`oxygen.post_pitch`) and their existing bilingual UI labels (`_KONSEPT_LABELS`, lines 185/187) would
be surfaced again by the Package module's own chunks, not duplicated under new ids.

### 2.1 Candidate new records

| Proposed ID | Classification | Recommended status | Claim (summarized) |
|---|---|---|---|
| `FACT-PACK-0001` | `documented_fact` | `draft` | A measured amount of fermentable priming sugar added to beer before sealing it in bottles restarts a small, renewed fermentation inside the sealed bottle; the resulting CO₂ has no escape path and dissolves into the beer, carbonating it. No single universal priming amount fits every batch. |
| `FACT-PACK-0002` | `documented_fact` | `draft` | Beer can be carbonated in a sealed keg by connecting it to an external CO₂ source under pressure, with no renewed fermentation involved; the amount of CO₂ that dissolves depends on pressure, beer temperature, and time/contact method. |
| `FACT-PACK-0003` | `documented_fact` | `draft` | Packaging beer into a sealed, carbonating/conditioning container creates internal pressure; containers/fittings not intended or rated for that pressure (e.g. non-beer glass, damaged bottles, incompatible caps/fittings) risk unsafe overpressure or container failure. |
| `FACT-PACK-0004` | `professional_interpretation` | `draft` | Bottling and kegging are both legitimate, commonly used packaging paths, not a quality hierarchy; the appropriate choice depends on equipment/budget/storage/serving context, and either path — once sanitized and properly primed/carbonated — reaches the same natural completion point (conditioned, ready to serve or store). |

### 2.2 Full entries

**`FACT-PACK-0001`** — *documented_fact*, draft
- **Claim:** Adding a small, measured amount of fermentable ("priming") sugar to beer immediately
  before sealing it into bottles triggers a renewed, small-scale fermentation inside each sealed
  bottle. Because the CO₂ produced by that renewed fermentation has no other escape path, it
  dissolves into the beer under the pressure that builds inside the sealed bottle, carbonating it.
  The amount of priming sugar needed depends on the specific beer (its existing dissolved CO₂,
  temperature, style) and the carbonation level wanted — there is no single universal number that
  applies to every batch.
- **Scope/limits:** States the mechanism and the "no universal number" boundary only; does not
  provide or endorse a specific priming-sugar dosage, formula, or table (explicit hard non-goal — "no
  numeric carbonation calculator lesson"). Does not name a specific priming-sugar type/product.
- **Sources (candidate — Chief verification required, see note above):**
  - Palmer, *How to Brew* — bottling/priming chapter (organization: howtobrew.com; exact
    chapter/section path not confirmed by this Bridge run).
  - An established manufacturer or brewing-science source on bottle conditioning fundamentals (e.g.
    a Fermentis/Lallemand/White Labs knowledge-base article on conditioning, mirroring the
    manufacturer-source tier already used for `FACT-BREW-0001..0003`/`FACT-OXY-0001` — exact article
    not confirmed by this Bridge run).
- **Wording traps to avoid:** do not state a specific priming-sugar amount/table as correct or
  required; do not imply any fermentable sugar type works identically; do not imply this is the same
  mechanism as the original fermentation rather than a distinct, smaller, sealed-container renewal of
  it.

**`FACT-PACK-0002`** — *documented_fact*, draft
- **Claim:** Beer can also be carbonated in a sealed keg by connecting it to an external CO₂ supply
  under pressure, with no renewed/secondary fermentation involved. The amount of CO₂ that ends up
  dissolved in the beer depends on the pressure applied, the beer's temperature, and the time/contact
  method used (e.g. a slower "set and forget" equilibrium approach versus a faster agitation-based
  approach) — carbonation level is directly adjustable by the brewer rather than fixed by however
  much priming sugar was added.
- **Scope/limits:** Describes the concept and the governing variables (pressure, temperature, time)
  only; does not provide a specific pressure/temperature/time schedule or carbonation-level target
  (explicit hard non-goal — "no numeric carbonation calculator lesson"), and does not compare or
  recommend specific CO₂ regulator/keg equipment brands or models.
- **Sources (candidate — Chief verification required, see note above):**
  - An established homebrewing technical source on kegging/force carbonation (e.g. a Brew Your Own
    article on kegging or carbonation; exact article not confirmed by this Bridge run).
  - Reputable, non-brand-specific equipment/gas guidance on the pressure–temperature relationship
    used for force carbonation (the widely cross-referenced "carbonation chart" concept used across
    homebrewing technical literature; a specific chart/source is a Chief-verification decision, not
    asserted here).
- **Wording traps to avoid:** do not present one specific pressure/temperature/time combination as
  "the" carbonation schedule; do not name or favor a specific keg/regulator brand; do not imply force
  carbonation is strictly faster or better than bottle conditioning — it is a different mechanism
  with different trade-offs, not a superior one (see `FACT-PACK-0004`).

**`FACT-PACK-0003`** — *documented_fact*, draft
- **Claim:** Whichever packaging path is used, the beer ends up sealed inside a container that is
  actively carbonating (bottle conditioning) or being force-carbonated (keg) — meaning that container
  holds internal pressure. Using a container or fitting not actually intended or rated for that
  pressure — a standard non-beer glass bottle, a bottle that is damaged, chipped, or has already been
  stressed by repeated reuse, or an incompatible cap/fitting — creates a risk of unsafe overpressure
  or container failure. Brewers should use bottles/kegs and capping/sealing equipment specifically
  intended for carbonated beer, and follow safe handling practice around any pressurized container.
- **Scope/limits:** States the existence of this safety boundary and its general cause (unsuitable
  container/fitting under pressure), not a specific pressure rating, a specific safe/unsafe product
  list, or a full pressure-vessel engineering treatment (explicit hard non-goal — "no pressure-vessel
  engineering course", "no detailed beer-serving system design").
- **Sources (candidate — Chief verification required, see note above):**
  - Palmer, *How to Brew* — the widely repeated safety guidance against reusing non-beer glass
    bottles/reusing damaged bottles for bottle conditioning (organization: howtobrew.com; exact
    chapter/section path not confirmed by this Bridge run).
  - Established homebrewing/safety guidance on safe handling of pressurized kegs/CO₂ systems (e.g.
    an American Homebrewers Association or equivalent established safety resource, or reputable
    CO₂/gas-supplier safety guidance; exact source not confirmed by this Bridge run, and any resulting
    citation must stay non-brand-specific per the governing issue's own source-rule for this claim
    category).
- **Wording traps to avoid:** do not name a specific unsafe or safe product/brand; do not turn this
  into pressure numbers, burst-pressure ratings, or a design/engineering lesson; do not imply every
  packaging attempt is dangerous — the point is container/equipment *suitability*, not that pressure
  itself is inherently hazardous when suitable equipment is used correctly.

**`FACT-PACK-0004`** — *professional_interpretation*, draft
- **Claim:** Bottling and kegging are both legitimate, widely used homebrewing packaging methods —
  neither is a marker of a "better" or more serious brewer, and the appropriate choice for a given
  brewer depends on practical factors (equipment cost/availability, storage space, how quickly the
  beer will be served, personal preference), not on any inherent quality difference in the resulting
  beer. Once the sanitation boundary (`FACT-COOL-0003`, reused) has been respected and the beer has
  been properly primed/conditioned or force-carbonated (`FACT-PACK-0001`/`FACT-PACK-0002`) and given
  appropriate time, either path reaches the same natural completion point: a carbonated, conditioned
  beer ready to serve or store.
- **Scope/limits:** A synthesis/interpretation drawing on `FACT-PACK-0001`/`FACT-PACK-0002`/
  `FACT-PACK-0003` and reused `FACT-COOL-0003`/`FACT-OXY-0002`, not a new independently measured
  result — mirrors the precedent set by `FACT-BOIL-0004`/`FACT-COOL-0003`-style synthesis records
  already in the registry (`FACT-MASH-0004`, `FACT-HOP-0003`, `FACT-OXY-0003`). Does not claim every
  homebrewer's context makes both methods equally convenient in practice — only that neither is
  inherently a "better beer" marker.
- **Sources:** the same candidate sources underlying `FACT-PACK-0001`/`FACT-PACK-0002`/
  `FACT-PACK-0003` above, combined with the already-verified `FACT-COOL-0003`/`FACT-OXY-0002`.
- **Wording traps to avoid:** never present bottling as "the beginner method" and kegging as "the
  real/serious brewer method," or vice versa; never imply a brewer must eventually "graduate" from one
  to the other; keep the "natural completion point" framing as an end to the *process*, not a claim
  that packaging is the end of the brewer's learning journey.

---

## 3. Module contract

### 3.1 Proposed topic id

`PILOT-PACKAGE-FUNDAMENTALS` — mirrors the existing `PILOT-MASHING-FUNDAMENTALS` /
`PILOT-BOIL-HOP-FUNDAMENTALS` / `PILOT-COOL-TRANSFER-FUNDAMENTALS` naming convention already used by
`bryggeskole/pilot_mashing.py` / `bryggeskole/pilot_boil_hop.py` / `bryggeskole/pilot_cool_transfer.py`.

### 3.2 Learning chunks (5 — within the required 3–6, matching the issue's own "about five chunks")

Each chunk below is a **structural proposal** (id, source claim(s), teaching intent) — not finished
bilingual copy, mirroring both prior contracts' own precedent of leaving final NO/EN teaching prose to
a later implementation child, once the underlying facts are actually reviewed/promoted. Chunk order
follows the governing issue's own proposed pedagogical order A–E exactly; no evidence surfaced during
this prep pass to justify changing it.

| Chunk ID | `source_claims` | Teaching intent (one sentence) |
|---|---|---|
| `CHUNK-PACK-A` | `FACT-COOL-0003` (reused) | Packaging continues the same clean/sanitized handling boundary already taught in cool/transfer — it now covers bottling/kegging equipment too. |
| `CHUNK-PACK-B` | `FACT-PACK-0001` | Bottle conditioning/priming: a measured amount of priming sugar restarts a small, sealed-bottle fermentation whose CO₂ carbonates the beer. |
| `CHUNK-PACK-C` | `FACT-PACK-0002` | Keg/force carbonation: external CO₂ under pressure carbonates beer directly, with carbonation level set by pressure/temperature/time — no renewed fermentation. |
| `CHUNK-PACK-D` | `FACT-OXY-0002` (reused), `FACT-PACK-0003` | Oxygen still matters at packaging (reused, not re-taught from scratch) and packaging creates pressure — use suitable, rated containers/equipment. |
| `CHUNK-PACK-E` | `FACT-PACK-0004` | Choosing bottling vs. kegging is a practical choice, not a quality hierarchy; both reach the same "ready to serve/store" completion point. |

### 3.3 Scenarios/questions

Mirroring `pilot_cool_transfer.py`'s existing `concept_check`/`scenario` question types and
`evaluate_answer()` contract (never a raw numeric score), one substantive question per chunk is
proposed, each declaring `source_claims` that must resolve against the **verified-only** registry API
(`get_verified_record`) exactly as the four existing pilots already require — meaning none of these
questions could actually ship until at least their underlying fact(s) are promoted past `draft`. Two
of the five chunks (`CHUNK-PACK-A`, part of `CHUNK-PACK-D`) already resolve today, since
`FACT-COOL-0003` and `FACT-OXY-0002` are already `verified` — only their *new* companion facts in
`CHUNK-PACK-B`/`C`/`D`/`E` need promotion.

Representative scenario shapes (final wording is implementation-child work, same reasoning as §3.2):

- **Scenario** on `CHUNK-PACK-A`: a learner has just finished cooling/transferring into the fermenter
  and, weeks later, reaches for a bottling wand that was left sitting unrinsed since the last brew day
  — tests whether the learner recognizes the sanitation boundary from cool/transfer explicitly
  extends to packaging equipment, not just cooling/transfer equipment.
- **Concept check** on `CHUNK-PACK-B`: distinguishing "priming sugar restarts a small fermentation in
  the sealed bottle" from an overclaim like "any amount of extra sugar is fine, more sugar just means
  more carbonation with no downside" — tests whether the learner grasps the "no universal number, and
  it matters" boundary without needing an actual formula.
- **Concept check** on `CHUNK-PACK-C`: distinguishing keg/force carbonation (external CO₂, no
  renewed fermentation, pressure/temperature/time-driven) from bottle conditioning (`CHUNK-PACK-B`) —
  tests that the learner does not conflate the two mechanisms as "the same thing, different container."
- **Scenario** on `CHUNK-PACK-D`: a learner asks whether splashing while racking into a bottling
  bucket, three weeks after pitching, matters "since fermentation is basically done anyway," and
  separately, whether any glass bottle they have on hand is fine for bottle conditioning — tests both
  the reused post-pitch oxygen-minimization point and the new pressure/container-suitability point in
  the same scenario, since the issue pairs them in pedagogical order D.
- **Scenario** on `CHUNK-PACK-E`: a learner who successfully bottled their first batch asks whether
  they should "upgrade" to kegging to make better beer — tests whether the learner treats packaging
  method choice as a practical/contextual decision rather than a quality ladder.

### 3.4 Feedback intent

Same pattern as the existing four pilots: `feedback_correct`/`feedback_incorrect` strings giving a
short, plain-language explanation of *why*, hedged consistently with each fact's own scope/limits
(§2) — never a bare "right"/"wrong," and never asserting more certainty than the underlying fact
supports (e.g. never implying kegging is "better," per `FACT-PACK-0004`'s own wording-trap note; never
implying oxygen exposure instantly ruins a beer, per the reused `FACT-OXY-0002`'s own existing
wording-trap note). No aggregate score is ever shown to the learner, consistent with `#65`'s "hidden
mastery, not a raw score" principle and the existing `evaluate_answer()` contract.

### 3.5 Hidden mastery/repetition implications

No new mastery engine or scheduling logic — this module would reuse `bryggeskole/mastery.py`'s
existing `apply_answer()`/`mastery_label()` exactly as the four existing pilots already do. Proposed
concept ids, following the existing English `domain.concept` convention already used by the shipped
pilots (`mashing.temperature`, `hop.isomerization_time`, `cool.speed`, …):

- `cool.sanitation_boundary` (`CHUNK-PACK-A`, `FACT-COOL-0003` — **reused id, not a new one**, so a
  learner's existing mastery on this concept from the cool/transfer module carries straight over,
  which is the concrete mechanism behind `ui/bryggeskole_panel.py`'s own "shared mastery across
  modules" design goal noted in §0.)
- `package.priming` (`CHUNK-PACK-B`, `FACT-PACK-0001`)
- `package.force_carbonation` (`CHUNK-PACK-C`, `FACT-PACK-0002`)
- `oxygen.post_pitch` (`CHUNK-PACK-D`, `FACT-OXY-0002` — **reused id**, same rationale as above)
- `package.pressure_safety` (`CHUNK-PACK-D`, `FACT-PACK-0003`)
- `package.path_choice` (`CHUNK-PACK-E`, `FACT-PACK-0004`)

`CHUNK-PACK-D` intentionally maps to two concept ids (one reused, one new) rather than a merged single
id, mirroring how the cool/transfer contract's own `CHUNK-COOLXFER-D` mapped to three concept ids
(`oxygen.pre_pitch`, `oxygen.post_pitch`, `oxygen.timing_distinction`) under one chunk — a chunk can
teach more than one trackable concept without needing a 1:1 chunk-to-concept ratio.

No V2-3C adaptive/spaced-repetition scheduler exists yet (unchanged since both prior contracts' own
check) — this module would surface hidden mastery labels exactly the way the existing four modules
already do, with no new repetition mechanism invented for packaging specifically.

### 3.6 NO/EN requirements

Same bilingual shape already enforced by the existing pilots' `_validate_bilingual_text()` — every
chunk `text`, question `prompt`, option `text`, and `feedback_correct`/`feedback_incorrect` must carry
both a `no` and an `en` value, validated fail-closed exactly like the existing four pilots. No new
i18n mechanism is proposed; this is a direct reuse of the existing pilot content contract.

**Terminology guidance for the later NO/EN authoring pass** (not authored here — flagging the exact
Norwegian brewing terms an author would need, since packaging introduces several new domain terms none
of the four prior modules needed):

| Concept | Norwegian | English |
|---|---|---|
| Priming sugar / bottle conditioning | Primesukker / flaskekonditionering (flaskegjæring) | Priming sugar / bottle conditioning |
| Force carbonation | Tvangskarbonering | Force carbonation |
| Keg | Fat (kegg brukes også, spesielt muntlig) | Keg |
| Bottling wand | Tappestav | Bottling wand |
| Sealed container / pressure | Trykksatt/lukket beholder | Sealed/pressurized container |
| Conditioning (post-packaging) | Modning/lagring (kondisjonering forekommer også) | Conditioning |
| Ready to serve/store | Klar til servering/lagring | Ready to serve/store |

`ui/bryggeskole_panel.py`'s existing `_MODULER["pakking"]["tittel_nokkel"]` (proposed,
`"bryggeskole.modul.pakking.tittel"`) and `_KONSEPT_LABELS` entries for the new concept ids above are
implementation-child work, not authored here — listed to keep this contract's terminology consistent
with what that later step will need.

---

## 4. Visual requirement

**Recommendation: a static, responsive fermenter → split-path → serve/store process-flow diagram —
exactly the concept the governing issue itself prefers, and the smallest meaningful visual, not a
decorative illustration.**

A single flow, starting from one shared node and branching into two parallel paths that reconverge:

- **Gjæringskar (fermenter)** — the shared starting point, beer has finished active fermentation;
- **splits into two parallel paths**, each inside the same shaded "sanitized handling zone" already
  established by the cool/transfer visual (mirrors `bryggeskole/cool_transfer_flow.py`'s own zone
  technique, extended forward through packaging — supports `CHUNK-PACK-A`):
  - **Flaske-sti (bottle path):** Tappestav/overføring → Flaske + primesukker → sealed bottle
    (supports `CHUNK-PACK-B`);
  - **Fat-sti (keg path):** Overføring → Fat + ekstern CO₂ (supports `CHUNK-PACK-C`);
- **both paths reconverge** at a single shared end node: **Klar til servering/lagring (ready to
  serve/store)** (supports `CHUNK-PACK-E`'s "same natural completion point" framing) — deliberately
  drawn as equal-weight, side-by-side paths of the same visual size/prominence, so neither path reads
  as the "main" or "upgraded" route (directly supports `CHUNK-PACK-E`'s "not a quality hierarchy"
  point and the visual requirement's own "no brand/model hierarchy" constraint).

Two small, non-numeric labels/icons carry the remaining two teaching points without adding a numeric
axis or scale:

- one near the fermenter → split point: "unngå unødvendig oksygen ved overføring" / "avoid
  unnecessary oxygen during transfer" (`CHUNK-PACK-D`'s reused oxygen point);
- one shared label spanning both sealed-container nodes (bottle and keg): "bruk trykkegnet
  utstyr — flaske og fat er under trykk" / "use pressure-suitable equipment — bottle and keg are
  under pressure" (`CHUNK-PACK-D`'s new pressure/container-safety point).

This is deliberately **not** proposed as fully interactive in V1, for the same reasoning
`v22_g3d_cool_transfer_module_contract.md` §4 and `v22_g3b_boil_hop_module_contract.md` §4 both already
applied to their own visuals: a static, well-labeled diagram already carries the process/spatial and
"two equal legitimate paths" understanding this topic needs. An optional future enhancement —
clicking a stage/path to open its matching chunk — mirrors the same low-complexity, context-preserving
judgment made for all three prior Bryggeskole visuals, but is not required for a first usable slice.
No 3D/game-engine visual is proposed (explicit hard non-goal). No equipment catalogue — the diagram
shows the generic process shape (fermenter → bottle/keg → serve/store), not a comparison of specific
bottle cap styles, keg types, or CO₂ regulator brands/models.

A future implementation would mirror `bryggeskole/cool_transfer_flow.py`'s own pattern — its own,
standalone, pure SVG-generating module (e.g. `bryggeskole/package_flow.py`), not a shared/generalized
flow-diagram engine, consistent with every other Bryggeskole visual module to date.

---

## 5. Future Learn→Plan bridge

**No existing App/UI field to anchor to — genuinely different from all three prior contracts.**
Unlike mashing (`ui/process_panel.py`'s mash-step `temperatur` field), boil/hop (`ui/hop_panel.py`'s
per-addition `tid` field), and cool/transfer (`ui/brewday_panel.py`'s "4. Overføring & OG" expander,
`bd_pitch_temp`/`bd_transfer_note`), this prep pass found **no packaging/bottling/kegging field
anywhere in the App**. `ui/brewday_panel.py`'s brew-day checklist (`_SJEKKLISTE`, §0) and its six
expanders (`147`–`504`) end at **"5. Gjæring"**; there is no "6. Pakking" (or equivalent) expander, and
`_BD_DEFAULTS` has no `bd_priming_*`/`bd_keg_*`/`bd_bottling_*` session key. A real future bridge would
therefore need its own new brew-day step/field to attach to — not just a contextual expander next to
something that already exists — which is meaningfully more implementation work than the two prior
bridges needed, and is explicitly **not** undertaken here.

The governing issue itself asks only whether "any later Learn→Plan bridge is actually useful" (do not
implement it here) — given the above, this contract's answer is: **plausibly useful eventually, but
not yet actionable**, since it would require first deciding whether/how to add a packaging step to the
brew-day plan at all (a separate, App-side product decision outside this docs-only issue's scope), not
merely where to attach a bridge to an existing field. This is flagged as a remaining decision in §7,
not resolved here.

---

## 6. Non-goals

Restated from the governing issue, since this document's own recommendations must not silently cross
them:

- No Bryggeskole module/UI code was written or changed.
- No Course Fact Registry mutation was made — §2's records are proposals only, all at `draft`, none
  committed to `bryggeskole/data/course_fact_registry.json`.
- No pilot-content file (`bryggeskole/data/pilot_package_fundamentals.json` or similar) was created.
- No Learn→Plan bridge implementation was made (§5 is identification-and-honest-gap-reporting only,
  since no existing field was found to bridge to).
- No advanced/professional packaging curriculum was authored (no numeric priming/force-carbonation
  calculator, no draft-system/dispense-balancing content, no pressure-fermentation content — that
  remains `web/hjelp/trykkgjaering.html`'s separate, advanced-only territory, and is a different topic
  from this module's packaging-pressure-safety awareness point).
- No broad bottle/keg/CO₂-equipment encyclopedia or supplier/product recommendations were authored —
  §2's fact pack is bounded to exactly what §1's learner outcomes need.
- No recipe changes, framework/engine, Web/public productization, or deployment.

## Hard non-goals

(Restated verbatim from issue #372 for traceability — this document does not violate any of these.)

- no module/UI implementation;
- no Course Fact Registry mutation/promotion;
- no recipe changes;
- no public Web/standalone work;
- no supplier/product recommendations;
- no specific keg/bottle brand;
- no numeric carbonation calculator lesson;
- no detailed beer-serving system design;
- no draft-system balancing course;
- no pressure-fermentation course;
- no advanced cellar/packaging science;
- no Sóti/AI;
- no deploy.

---

## 7. Remaining owner/Chief decision

1. **Citation check is outstanding.** Unlike this document's cool/transfer precedent (which already
   reflects Chief's completed live citation pass), this Bridge run had no live network/source-fetch
   access at all — every source ref in §2.2 is a named-candidate-organization-and-topic only, not a
   verified URL. A live citation pass (mirroring #368's own follow-up) is needed before any of
   `FACT-PACK-0001..0004` could be promoted past `draft`.
2. **Whether/how to add a packaging step to the brew-day plan (`ui/brewday_panel.py`) is unresolved**
   and is a prerequisite for §5's Learn→Plan bridge ever becoming actionable — this is a separate,
   App-side product decision this docs-only prep issue does not make.
3. **Terminology choice between "flaskegjæring" and "flaskekonditionering"** (§3.6) for the later
   NO/EN authoring pass — both are in real homebrewing use in Norwegian; picking one (or explaining
   both) is left to that authoring step.
4. **Which chunk absorbs `FACT-COOL-0003`'s reuse most naturally** — this contract places it alone in
   `CHUNK-PACK-A` as the module's opening chunk (continuity from cool/transfer); an alternative would
   fold it into `CHUNK-PACK-D` alongside the other reused fact (`FACT-OXY-0002`) and `FACT-PACK-0003`,
   mirroring how cool/transfer's own `CHUNK-COOLXFER-D` bundled three oxygen facts together. This
   contract's own judgment favors keeping sanitation as its own opening chunk since it is the module's
   first teaching point and the issue's own pedagogical order A–E lists it separately from D — but this
   remains open to Chief's review.
