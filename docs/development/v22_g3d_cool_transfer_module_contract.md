# V2.2 G3D — Cool/transfer verified fact pack + module contract

Version: 1.1
Status: PREP/decision document — Chief source-verification completed for the candidate fact pack;
all proposed records remain `draft` until a separately authorized registry-promotion pass
Governed by: [#368](https://github.com/Joludvig/kvernhaug-brygghus/issues/368), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3), the Goal 3
gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358), the merged boil/hop
module ([#366](https://github.com/Joludvig/kvernhaug-brygghus/issues/366) / PR #367), and
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction)
Authoritative base at creation: `7f5aeb1377a27fef778347f3088f4f4ce3216665`

This is a **READ/PREP-only** document. It contains no module/UI implementation, no Course Fact
Registry mutation, and no App/Web/Core file changes — see [Hard non-goals](#hard-non-goals). It
does not authorize implementing a Kjøling/overføring Bryggeskole module; it only prepares the fact
pack and module contract Chief would need to authorize that work.

---

## 0. Why cool/transfer, and what already exists

Per #358's gap map, cool/transfer sits immediately after boil/hop in the brew-day flow, is a MUST
gap for a finishable homebrewer journey, and was flagged with strong visual/equipment value
(chiller/transfer path is equipment-dependent). #358's own recommended ordering places it directly
after the now-merged boil/hop module.

**Current repo state relevant to this prep, confirmed by inspection:**

- `bryggeskole/data/course_fact_registry.json` currently has **zero** cooling-, oxygen-, or
  transfer-related records — 14 records exist across `FACT-BREW-0001..0003` (fermentation),
  `FACT-MASH-0001..0004` (mashing), and `FACT-BOIL-0001..0004`/`FACT-HOP-0001..0003` (boil/hop,
  #366). This document proposes the first candidate cool/transfer facts (§2); none are added to
  the registry file by this issue.
- No `bryggeskole/pilot_cool*.py` or equivalent module exists. `bryggeskole/pilot_mashing.py`,
  `bryggeskole/pilot_fermentation.py`, and `bryggeskole/pilot_boil_hop.py` are the three existing
  topic-scoped pilots this contract mirrors structurally (schema, chunk/question shape,
  verified-only `source_claims` resolution) — each its own topic-scoped copy, never a shared
  engine (`bryggeskole/pilot_boil_hop.py`'s own docstring states this explicitly).
- The App has no dedicated cooling/transfer calculation surface (unlike boil/hop, which could
  anchor onto the already-implemented Tinseth IBU model). The relevant App touchpoints are UI-only:
  `ui/brewday_panel.py`'s brew-day checklist includes a `"Nedkjøling ferdig"` ("cooling complete")
  item (`_SJEKKLISTE`, line 26), and its **"4. Overføring & OG"** expander (lines 336–353) collects
  `bd_pitch_temp` (pitching temperature) and `bd_transfer_note` (free-text transfer note) — the
  concrete future Learn→Plan attachment candidates identified in §5.
- Static prose already exists at `web/hjelp/klaring.html` (+ `web/en/hjelp/klaring.html`, hot
  break/cold break/trub/whirlpool/cold crash/finings) and glossary entries in `web/hjelp/index.html`
  (`#def-kjoling`, `#def-oksidasjon`, `#def-cold-crash`). Per the governing issue, **none of that
  prose is reused here** — every claim in §2 is independently stated and sourced by this document,
  not lifted from those pages. `web/hjelp/trykkgjaering.html` covers pressure fermentation, which
  is explicitly advanced/out of scope for this beginner module (§6).

---

## 1. Minimum learner outcome

A learner who completes this module should be able to explain, in their own words, without needing
any specific chiller brand/model or a fixed numeric cooling-rate target:

1. **What happens between end of boil and pitching/fermentation** — the wort is cooled from
   boiling temperature down toward the yeast's intended pitching temperature, then moved
   ("transferred") into the fermenter, where cold break continues to form and fermentation begins
   once yeast is added.
2. **Why cooling matters and what to control** — cooling reduces the time the wort spends in a
   temperature range where unwanted microorganisms can grow before pitching, and (distinct from
   `FACT-BOIL-0003`'s hot break) drives the formation of cold break as the wort passes through
   cooler temperatures.
3. **The clean/sanitized handling boundary after the boil** — boiling only protects the wort by
   heat while it is actively hot; from the moment cooling begins, every surface that will touch the
   wort/beer (chiller, hose/tubing, fermenter, tools) needs to be clean and sanitized, because that
   heat-based protection is gone.
4. **Basic transfer choices and their practical trade-offs** — gravity transfer (no pump, needs an
   elevation difference) versus pump-assisted transfer (works regardless of relative vessel height,
   at the cost of more equipment/cleaning); a closed/sealed transfer path reduces splashing and
   air/oxygen exposure compared with an open pour, at the cost of added setup complexity.
5. **Where cold-side oxygen exposure can help, and when active aeration is actually needed** —
   oxygen availability before/at pitching can support yeast sterol/UFA synthesis and healthy
   growth, but the brewer does **not** always need to add oxygen deliberately. Need depends on yeast
   form/state, pitch rate, wort gravity and manufacturer/process guidance; fresh active dry yeast
   at normal first-pitch rates is a common case where added wort aeration may be unnecessary.
   Once fermentation is actively underway, unnecessary oxygen exposure is generally undesirable
   (oxidation risk). This is a **timing-and-need distinction**, not a blanket "oxygen is bad" or
   "always aerate before pitching" rule.
6. **How immersion-chiller / common homebrew transfer paths fit the process** — at a conceptual
   level only: a chiller cools the wort before transfer, and the transfer step moves it into the
   fermenter; this module does not catalogue chiller types, brands, or equipment features beyond
   what §1.4/§1.5 need.

**Explicitly not an outcome:** naming/comparing specific chiller types (immersion vs. plate vs.
counterflow) beyond the general trade-off in §1.4, a numeric cooling-rate/temperature-band target,
a specific sanitizer product/contact-time, or a dissolved-oxygen target value. None of these have a
source attached in §2, and the governing issue's own "no broad equipment encyclopedia" boundary
excludes them.

---

## 2. Proposed verified fact pack

**None of the records below exist in `bryggeskole/data/course_fact_registry.json` yet, and this
issue does not add them.** They are proposed candidates, in the exact record shape
[`BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md`](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) defines, for a
future, separately authorized editorial pass to review and (if it concurs) actually commit to the
registry — mirroring how `v22_g3b_boil_hop_module_contract.md` §2 (and, before that,
`V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` §4) flagged uncommitted candidate sources without
registering them itself.

**Source-verification note:** the Bridge run itself had no live network/source-fetch access, but
Chief subsequently performed the live citation pass and supplied concrete, checkable references
from Wyeast, Fermentis, Lallemand, Palmer/How to Brew and Brew Your Own. Those references are now
attached below. The seven proposed records still remain `status: draft` because this PR is a
READ/PREP contract only and does not mutate the Course Fact Registry. Promotion to `verified`
requires its own separately authorized registry/editorial pass; this document now has the evidence
needed for that later decision.

### 2.1 Candidate records

| Proposed ID | Classification | Recommended status | Claim (summarized) |
|---|---|---|---|
| `FACT-COOL-0001` | `documented_fact` | `draft` | Rapid post-boil cooling toward pitching temperature reduces the time wort spends in a temperature range favorable to unwanted microorganisms before pitching. |
| `FACT-COOL-0002` | `documented_fact` | `draft` | As wort cools, proteins/polyphenols coagulate again ("cold break"), a temperature-driven phenomenon distinct from hot break (`FACT-BOIL-0003`). |
| `FACT-COOL-0003` | `documented_fact` | `draft` | Boiling's heat-based protection ends once cooling begins; every surface touching the wort/beer from that point on needs to be clean and sanitized. |
| `FACT-OXY-0001` | `documented_fact` | `draft` | Yeast can use oxygen before/at pitching for sterol/UFA synthesis, but deliberate brewer aeration is conditional; fresh active dry yeast at normal first pitch may not need added wort aeration. |
| `FACT-OXY-0002` | `documented_fact` | `draft` | Once fermentation is actively underway, unnecessary oxygen exposure is generally undesirable — oxidative off-flavors, diminished hop aroma, reduced shelf stability. |
| `FACT-OXY-0003` | `professional_interpretation` | `draft` | Practical oxygen guidance is timing- and yeast-dependent: pre-pitch oxygen can be beneficial where needed, while unnecessary oxygen after active fermentation begins should be minimized. |
| `FACT-TRANSFER-0001` | `practical_experience` | `draft` | Gravity vs. pump transfer, and closed/sealed vs. open transfer paths, involve different practical trade-offs (equipment/cleaning vs. splashing/air exposure). |

### 2.2 Full entries

**`FACT-COOL-0001`** — *documented_fact*, draft
- **Claim:** Cooling wort rapidly from boiling temperature down toward the yeast's intended
  pitching temperature reduces the time the wort spends in a temperature range where unwanted/
  spoilage microorganisms can grow, and is standard homebrewing practice for reducing infection
  risk before pitching.
- **Scope/limits:** Does not claim rapid cooling guarantees zero infection risk, nor that slow
  cooling always causes infection — this describes a risk-reduction direction, not a guarantee.
  Does not assert a specific numeric cooling-rate threshold or a fixed "danger zone" temperature
  band as a universal rule (equipment and ambient conditions vary). Distinct from `FACT-BOIL-0001`
  (boiling reduces microbial load *at the time of boiling*) — cooling is a separate, later exposure
  window, not a continuation of the same protection.
- **Sources (Chief-verified):**
  - Palmer, *How to Brew*, Ch. 7 "Cooling the Wort": https://howtobrew.com/section-1/chapter-7/
  - Palmer, *How to Brew*, Ch. 2: https://howtobrew.com/section-1/chapter-2/
  - Brew Your Own, "Wort Chilling": https://byo.com/articles/wort-chilling/
  These support rapid cooling as a risk-reduction practice while still allowing qualified
  no-chill/slow-chill process language rather than an absolute rule.
- **Wording traps to avoid:** do not imply cooling slowly always causes an infection; do not state
  a specific "danger zone" temperature range as a universal fixed rule; do not imply this claim
  extends or repeats `FACT-BOIL-0001`'s own microbial-load scope.

**`FACT-COOL-0002`** — *documented_fact*, draft
- **Claim:** As wort cools from boiling toward pitching temperature, proteins and polyphenols that
  were still soluble in hot wort coagulate again and precipitate — "cold break" — a temperature-
  driven phenomenon distinct from the "hot break" that forms during the boil itself
  (`FACT-BOIL-0003`).
- **Scope/limits:** Does not assert a specific quantity of cold break, nor a specific benefit or
  detriment from how much of it is carried into the fermenter — homebrewers vary in how much they
  choose to leave behind in the kettle, and this claim does not take a side on that practice.
- **Sources (Chief-verified):**
  - Palmer, *How to Brew*, Ch. 7 "Cooling the Wort": https://howtobrew.com/section-1/chapter-7/
  - Brew Your Own, "Wort Chilling": https://byo.com/articles/wort-chilling/
  - Brew Your Own, "Hows and Whys of the Wort Chiller":
    https://byo.com/articles/hows-and-whys-of-the-wort-chiller/
  These support cold-break formation during cooling and its distinction from hot break.
- **Wording traps to avoid:** never conflate cold break with hot break as the same phenomenon or
  the same temperature stage; never conflate cold break with chill haze (chill haze is a colder,
  later, different-mechanism phenomenon, already explicitly excluded from `FACT-BOIL-0003`'s own
  scope).

**`FACT-COOL-0003`** — *documented_fact*, draft
- **Claim:** Boiling protects the wort by heat only while it is actively at or near boiling
  temperature (`FACT-BOIL-0001`); once cooling begins, any surface that will subsequently contact
  the wort or beer — chiller, transfer hose/tubing, fermenter, airlock, and any tool used from this
  point forward — is no longer protected by that heat, and needs to be clean and sanitized before
  and during use to avoid introducing spoilage organisms.
- **Scope/limits:** Describes the existence and starting point of this handling boundary, not a
  specific sanitizer product, contact time, or procedure — those vary by product and are explicitly
  out of scope (mirrors `FACT-BOIL-0004`'s own "no single fixed rule" boundary).
- **Sources (Chief-verified):**
  - Palmer, *How to Brew*, Ch. 2: https://howtobrew.com/section-1/chapter-2/
  - Brew Your Own, "Hows and Whys of the Wort Chiller":
    https://byo.com/articles/hows-and-whys-of-the-wort-chiller/
  These support the post-boil sanitation boundary and sanitation of wort-contact cooling/transfer
  equipment without prescribing one sanitizer product or contact time.
- **Wording traps to avoid:** do not imply one single specific sanitizer or contact time is
  required; do not imply the boil "immunizes" downstream equipment or that this boundary is optional.

**`FACT-OXY-0001`** — *documented_fact*, draft
- **Claim:** Brewing yeast can use oxygen before or around pitching to synthesize sterols and
  unsaturated fatty acids needed for healthy membrane growth. Whether the brewer needs to
  deliberately aerate/oxygenate the wort is conditional: it depends on yeast form/state, pitch
  rate, wort gravity and manufacturer/process guidance. Fresh active dry yeast at normal first-pitch
  rates is a common explicit case where added wort aeration may be unnecessary because the dried
  cells are produced with sterol/UFA reserves.
- **Scope/limits:** Describes both the biological role of oxygen and the operator-action exception.
  It does not prescribe a dissolved-oxygen target, aeration method or duration, and it must not be
  taught as "all wort must be aerated before pitching."
- **Sources (Chief-verified, manufacturer/primary technical guidance):**
  - Wyeast, "Oxygenation & Aeration":
    https://wyeastlab.com/resource/home-enthusiast-oxygenation-aeration/
  - Fermentis FAQ: https://fermentis.com/en/knowledge-center/faq/
  - Fermentis, "What are the best 5 ways to improve fermentation?":
    https://fermentis.com/en/news/fermentation/what-are-the-best-5-ways-to-improve-fermentation/
  - Lallemand, "Premium Dry Yeast for Quality, Consistent Fermentations":
    https://www.lallemandbrewing.com/en/asia/resources/lallemand-premium-dry-yeast-for-quality-consistent-fermentations/
  - Lallemand, *Yeast Nutrition* booklet:
    https://connect.lallemandbrewing.com/wp-content/uploads/2022/11/Nutrition-Booklet-ENG-Digital-AB-Vickers.pdf
- **Wording traps to avoid:** do not turn "oxygen can support growth" into "the brewer must always
  add oxygen"; do not imply oxygen is wanted throughout fermentation; keep fresh first-pitch dry
  yeast as an explicit common exception to mandatory aeration.

**`FACT-OXY-0002`** — *documented_fact*, draft
- **Claim:** Once fermentation is actively underway, oxygen exposure to the wort/beer is generally
  undesirable: it can contribute to oxidative off-flavors (e.g. cardboard/"stale" notes), diminished
  hop aroma, and reduced shelf stability. Minimizing splashing and unnecessary air contact during
  any transfer performed after active fermentation has begun is standard homebrewing practice.
- **Scope/limits:** Does not claim a single stray oxygen exposure inevitably ruins a batch —
  describes a risk/quality direction, not an absolute threshold or guaranteed outcome.
- **Sources (Chief-verified):**
  - Brew Your Own, "Racking and Transferring":
    https://byo.com/articles/racking-and-transferring/
  - Brew Your Own, "Transferring Beer":
    https://byo.com/articles/transferring-beer-techniques/
  These support minimizing splashing/unnecessary air exposure during post-fermentation transfer.
- **Wording traps to avoid:** do not imply any oxygen contact after pitching instantly spoils the
  beer; do not conflate this with the pre-pitch requirement in `FACT-OXY-0001` — same molecule,
  opposite-timing effect, not a contradiction.

**`FACT-OXY-0003`** — *professional_interpretation*, draft
- **Claim:** Practical oxygen guidance is both timing- and yeast-dependent. Before/at pitching,
  oxygen availability can be beneficial where the yeast/process requires it, but deliberate
  aeration is not universally required (fresh active dry yeast at normal first pitch is a common
  exception). Once fermentation is actively underway, unnecessary oxygen exposure should generally
  be minimized.
- **Scope/limits:** A synthesis/interpretation of `FACT-OXY-0001`/`FACT-OXY-0002`, not a new
  independently measured result; does not define one universal oxygen target or one exact temporal
  cutoff for every fermentation.
- **Sources:** same Chief-verified manufacturer sources underlying `FACT-OXY-0001`, combined with
  the transfer/oxidation sources underlying `FACT-OXY-0002`.
- **Wording traps to avoid:** never state this as simply "oxygen is bad", "oxygen is always wanted
  before pitching", or "always aerate wort"; the teaching point is conditional need before pitch
  and minimized unnecessary oxygen once active fermentation is underway.

**`FACT-TRANSFER-0001`** — *practical_experience*, draft
- **Claim:** Homebrewers commonly move wort/beer between vessels either by gravity (relying on an
  elevation difference between vessels, requiring no pump) or with a pump (works regardless of
  relative vessel height, at the cost of added equipment and cleaning); a closed/sealed transfer
  path (e.g. a hose run vessel-to-vessel with minimal open-air contact) reduces splashing and
  airborne contamination/oxygen exposure compared with an open pour or open racking, at the cost of
  added setup complexity.
- **Scope/limits:** Describes the trade-off directions only — does not claim one method is
  universally "correct," does not recommend a specific pump/hose product, and does not assert a
  numeric contamination-rate difference between methods.
- **Sources (Chief-verified):**
  - Brew Your Own, "Transferring Beer":
    https://byo.com/articles/transferring-beer-techniques/
  - Palmer, *How to Brew*, Ch. 9 "Transferring Your Wort":
    https://howtobrew.com/section-1/chapter-9/
  These support gravity/pump transfer mechanics, splash control and sanitation trade-offs. Palmer's
  historical blanket aeration advice must **not** override the modern yeast-manufacturer guidance
  in `FACT-OXY-0001`.
- **Wording traps to avoid:** do not present gravity or pump transfer as inherently superior; do not
  imply an open transfer always causes contamination, or that a closed transfer eliminates the risk.

---

## 3. Module contract

### 3.1 Proposed topic id

`PILOT-COOL-TRANSFER-FUNDAMENTALS` — mirrors the existing `PILOT-MASHING-FUNDAMENTALS` /
`PILOT-BOIL-HOP-FUNDAMENTALS` naming convention in `bryggeskole/pilot_mashing.py` /
`bryggeskole/pilot_boil_hop.py`.

### 3.2 Learning chunks (5 — within the required 3–6)

Each chunk below is a **structural proposal** (id, source claim(s), teaching intent) — not
finished bilingual copy. Per §2's own honesty note and the precedent set by both prior contracts
(neither authored final teaching prose), writing final NO/EN chunk text is implementation-child
work, done only once the underlying facts are actually reviewed/promoted, so chunk wording never
gets ahead of what the registry has actually verified.

| Chunk ID | `source_claims` | Teaching intent (one sentence) |
|---|---|---|
| `CHUNK-COOLXFER-A` | `FACT-COOL-0001` | Why cooling matters: shrinks the time window where unwanted microorganisms can grow before pitching. |
| `CHUNK-COOLXFER-B` | `FACT-COOL-0002` | What cold break is, and why it's a different stage/phenomenon from hot break. |
| `CHUNK-COOLXFER-C` | `FACT-COOL-0003` | The post-boil clean/sanitized handling boundary: heat-based protection ends when cooling starts. |
| `CHUNK-COOLXFER-D` | `FACT-OXY-0001`, `FACT-OXY-0002`, `FACT-OXY-0003` | Cold-side oxygen: can be beneficial before/at pitching when the yeast/process needs it; deliberate aeration is conditional, while unnecessary oxygen should be minimized once fermentation is active. |
| `CHUNK-COOLXFER-E` | `FACT-TRANSFER-0001` | Basic transfer choices (gravity vs. pump; closed vs. open path) and their practical trade-offs. |

### 3.3 Scenarios/questions

Mirroring `pilot_boil_hop.py`'s existing `concept_check`/`scenario` question types and
`evaluate_answer()` contract (never a raw numeric score), one question per chunk is proposed, each
declaring `source_claims` that must resolve against the **verified-only** registry API
(`get_verified_record`) exactly as the existing pilots already require — meaning none of these
questions could actually ship until at least their underlying fact(s) are promoted past `draft`.

Representative scenario shapes (final wording is implementation-child work, same reasoning as
§3.2):

- **Concept check** on `CHUNK-COOLXFER-A`: distinguishing "cooling quickly reduces infection risk"
  from an overclaim like "cooling is optional since boiling already sterilized everything" —
  deliberately tests the same wording trap `FACT-BOIL-0001` already guards against, now applied to
  the next stage.
- **Concept check** on `CHUNK-COOLXFER-B`: distinguishing cold break from hot break — tests whether
  the learner understands these are different phenomena at different temperature stages, not the
  same event described twice.
- **Scenario** on `CHUNK-COOLXFER-C`: a learner has just finished the boil and reaches for a hose
  that was used (unrinsed) on a previous brew day, to run wort into the fermenter — tests whether
  the learner recognizes the sanitized-handling boundary starts at cooling, not only at pitching.
- **Scenario** on `CHUNK-COOLXFER-D`: a learner asks whether wort should **always** be deliberately
  aerated before pitching, and whether that is equivalent to splashing during a transfer three days
  into active fermentation. The correct concept is that pre-pitch oxygen can be beneficial when the
  yeast/process needs it, fresh active dry yeast may not require added aeration, and unnecessary
  oxygen after active fermentation begins should be minimized.
- **Concept check** on `CHUNK-COOLXFER-E`: distinguishing gravity vs. pump transfer trade-offs —
  tests that the learner treats this as a situational trade-off (equipment/cleaning vs. no pump
  needed), not a "one is correct, one is wrong" choice.

### 3.4 Feedback intent

Same pattern as the existing three pilots: `feedback_correct`/`feedback_incorrect` strings giving a
short, plain-language explanation of *why*, hedged consistently with each fact's own scope/limits
(§2) — never a bare "right"/"wrong," and never asserting more certainty than the underlying fact
supports (e.g. never implying oxygen is simply "bad," per `FACT-OXY-0003`'s own wording-trap note).
No aggregate score is ever shown to the learner, consistent with `#65`'s "hidden mastery, not a raw
score" principle and the existing `evaluate_answer()` contract.

### 3.5 Hidden mastery/repetition implications

No new mastery engine or scheduling logic — this module would reuse `bryggeskole/mastery.py`'s
existing `apply_answer()`/`mastery_label()` exactly as the three existing pilots already do.
Proposed concept ids, following the existing English `domain.concept` convention already used by
the shipped pilots (`mashing.temperature`, `hop.isomerization_time`, …):

- `cool.speed` (`CHUNK-COOLXFER-A`, `FACT-COOL-0001`)
- `cool.cold_break` (`CHUNK-COOLXFER-B`, `FACT-COOL-0002`)
- `cool.sanitation_boundary` (`CHUNK-COOLXFER-C`, `FACT-COOL-0003`)
- `oxygen.pre_pitch` (`CHUNK-COOLXFER-D`, `FACT-OXY-0001`)
- `oxygen.post_pitch` (`CHUNK-COOLXFER-D`, `FACT-OXY-0002`)
- `oxygen.timing_distinction` (`CHUNK-COOLXFER-D`, `FACT-OXY-0003`)
- `transfer.method_tradeoffs` (`CHUNK-COOLXFER-E`, `FACT-TRANSFER-0001`)

No V2-3C adaptive/spaced-repetition scheduler exists yet (unchanged since the boil/hop contract's
own check) — this module would surface hidden mastery labels exactly the way the existing three
modules already do, with no new repetition mechanism invented for cool/transfer specifically.

### 3.6 NO/EN requirements

Same bilingual shape already enforced by the existing pilots' `_validate_bilingual_text()` — every
chunk `text`, question `prompt`, option `text`, and `feedback_correct`/`feedback_incorrect` must
carry both a `no` and an `en` value, validated fail-closed exactly like the existing three pilots.
No new i18n mechanism is proposed; this is a direct reuse of the existing pilot content contract.

### 3.7 Future App planning hook

See §5 for the full bridge identification — restated briefly here as the module contract's own
forward pointer: `CHUNK-COOLXFER-C`/`D`/`E` are the chunks a future Learn→Plan bridge would surface
next to `ui/brewday_panel.py`'s **"4. Overføring & OG"** expander (`bd_pitch_temp`,
`bd_transfer_note`), mirroring how `V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` surfaced its chunks next
to the mash-step `temperatur` field and the boil/hop contract surfaced its chunks next to
`ui/hop_panel.py`'s `tid` field. Not implemented by this issue.

---

## 4. Visual requirement

**Recommendation: a static cool/transfer process-flow diagram — the smallest meaningful visual,
not a decorative illustration.** This follows the issue's own preferred direction exactly.

A single horizontal flow, left (post-boil kettle) to right (fermenter), with four stages:

- **Kjele (post-boil)** — the wort just after the boil ends, still hot;
- **Kjøling** — the cooling step, supporting `CHUNK-COOLXFER-A`/`B` (cooling speed, cold break);
- **Overføring** — the transfer step, supporting `CHUNK-COOLXFER-E` (gravity vs. pump, closed vs.
  open path), shown as two small alternative path variants (not a full equipment catalogue —
  no specific chiller/pump brand or model);
- **Gjæringskar** — the fermenter, where fermentation begins;

with a **shaded "sanitized handling zone"** starting at the Kjøling stage and extending through
Overføring to Gjæringskar — a clear, visually distinct boundary directly supporting
`CHUNK-COOLXFER-C`'s "heat-based protection ends here" claim, mirroring the visual-boundary shading
technique `bryggeskole/boil_timeline.py` already used for its own whirlpool/hop-stand zone.

Two small, non-numeric labels/icons mark the oxygen-timing/need distinction from
`CHUNK-COOLXFER-D`: one near the Kjøling→Overføring transition ("oksygenering kan være nyttig før
pitching — behov avhenger av gjær" / "aeration can help before pitching — need depends on the yeast")
and one at the Gjæringskar stage ("unngå unødvendig oksygen etter aktiv gjæring" / "avoid unnecessary
oxygen once fermentation is active"). No dissolved-oxygen scale or numeric axis is introduced.

This is deliberately **not** proposed as fully interactive in V1 — a static, well-labeled diagram
already carries the process/spatial understanding this topic needs (same reasoning
`v22_g3b_boil_hop_module_contract.md` §4 and Roadmap V2.2's own "not everything must be visual"
principle already applied to boil/hop). An optional enhancement — clicking a stage to open its
matching chunk — mirrors the same low-complexity, context-preserving judgment made for both prior
Bryggeskole visuals, but is not required for a first usable slice. No 3D/game-engine visual is
proposed (explicit hard non-goal). No broad equipment encyclopedia — the diagram shows the generic
process shape (kettle → cooling → transfer → fermenter), not a comparison of specific chiller
types, brands, or models.

---

## 5. Future Learn→Plan bridge

**Identified candidate, not implemented here:** `ui/brewday_panel.py`'s **"4. Overføring & OG"**
expander (lines 336–353) already renders `bd_pitch_temp` (pitching temperature, °C) and
`bd_transfer_note` (free-text transfer note) fields on the brew-day checklist, immediately after
the boil/post-boil-volume step and immediately before the "5. Gjæring" section. This is a genuinely
different UI location/pattern than the two prior bridges (`ui/process_panel.py`'s mash-step field,
`ui/hop_panel.py`'s per-addition `tid` field — both recipe-builder fields), since it lives on the
brew-day execution checklist instead — a contextual, collapsed-by-default explanation (an
`st.expander`, same complexity/state-preservation reasoning as the two prior bridges, not a tab
jump) placed near this step would surface `CHUNK-COOLXFER-C`/`D`/`E` so a learner filling in
pitching temperature or a transfer note can see *why* the sanitation boundary and oxygen timing
matter right at that moment. `_SJEKKLISTE`'s own `"Nedkjøling ferdig"` checklist item (line 26) is
a second, simpler candidate anchor point, noted here for the future audit to weigh against the
"4. Overføring & OG" expander.

This is **identification only**. A real bridge needs its own bounded audit/contract document,
exactly like the two prior bridges each got — confirming exact line numbers, session-state keys,
and a factual mismatch check against `web/hjelp/klaring.html`/`web/hjelp/index.html`'s own prose (if
any exists) before any implementation child is authorized. No such audit is performed here, and no
App/UI code is touched by this issue.

---

## 6. Non-goals

Restated from the governing issue, since this document's own recommendations must not silently
cross them:

- No Bryggeskole module/UI code was written or changed.
- No Course Fact Registry mutation was made — §2's records are proposals only, all at `draft`,
  none committed to `bryggeskole/data/course_fact_registry.json`.
- No pilot-content file (`bryggeskole/data/pilot_cool_transfer*.json` or similar) was created.
- No Learn→Plan bridge implementation was made (§5 is identification only).
- No advanced/professional cold-side process curriculum was authored (e.g. no dissolved-oxygen
  targets, no closed-transfer/CO₂-purge system design, no pressure-fermentation content — that
  remains `web/hjelp/trykkgjaering.html`'s separate, advanced-only territory).
- No broad chiller/pump/equipment encyclopedia or supplier/product recommendations were authored —
  §2's fact pack is bounded to exactly what §1's learner outcomes need.
- No recipe changes, framework/engine, Web/public productization, or deployment.

## Hard non-goals

(Restated verbatim from issue #368 for traceability — this document does not violate any of
these.)

- no module/UI code;
- no recipe changes;
- no Web/public deployment;
- no Sóti/AI;
- no new mastery engine;
- no generalized course-framework rewrite;
- no advanced/professional cold-side process curriculum;
- no broad equipment encyclopedia;
- no supplier/product recommendations.

---

## 7. Remaining owner/Chief decision

1. **Citation check is complete.** Chief has attached concrete, checkable references for all seven
   proposed `draft` facts. They intentionally remain `draft` because this PR is prep-only; a
   later implementation/editorial child must promote only those records that satisfy the production
   registry evidence contract.
2. **Keep `FACT-OXY-0001..0003` folded into one `CHUNK-COOLXFER-D` for the first implementation.**
   The pedagogical point is precisely the contrast between conditional pre-pitch need and
   post-fermentation oxygen avoidance; splitting it would make that relationship harder to see.
3. **Which brew-day UI field anchors the future Learn→Plan bridge (§5)** — the "4. Overføring & OG"
   expander's `bd_pitch_temp`/`bd_transfer_note` fields, or the simpler `"Nedkjøling ferdig"`
   checklist item — remains for that bridge's own bounded audit to resolve, not this prep PR.
