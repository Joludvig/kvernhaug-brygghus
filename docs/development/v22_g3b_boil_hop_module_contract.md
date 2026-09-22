# V2.2 G3B — Boil/hop verified fact pack + module contract

Version: 1.0
Status: PREP/decision document — reviewable, not yet actionable
Governed by: [#362](https://github.com/Joludvig/kvernhaug-brygghus/issues/362), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3), the Goal 3
gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358), and
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole product direction)
Authoritative base at creation: `f2d425456da4f6449b66738cfa970c8948449802`

This is a **READ/PREP-only** document. It contains no module/UI implementation, no Course Fact
Registry mutation, and no App/Web/Core file changes — see [Hard non-goals](#hard-non-goals). It
does not authorize implementing a Koking/humle Bryggeskole module; it only prepares the fact pack
and module contract Chief would need to authorize that work.

---

## 0. Why boil/hop, and what already exists

Per #358's gap map, boil/hop was identified as the strongest first Goal-3 slice: it sits directly
after Mesking in the brew-day flow, no interactive Bryggeskole module exists for it today, and the
App already has hop/IBU planning surfaces a future Learn→Plan bridge could attach to (§5).

**Current repo state relevant to this prep, confirmed by inspection:**

- `bryggeskole/data/course_fact_registry.json` currently has **zero** boil- or hop-related
  records — only `FACT-BREW-0001..0003` (fermentation) and `FACT-MASH-0001..0004` (mashing)
  exist. This document proposes the first candidate boil/hop facts (§2); none are added to the
  registry file by this issue.
- No `bryggeskole/pilot_boil*.py` or equivalent module exists. `bryggeskole/pilot_mashing.py` and
  `bryggeskole/pilot_fermentation.py` are the two existing topic-scoped pilots this contract
  mirrors structurally (schema, chunk/question shape, verified-only `source_claims` resolution).
- The App already computes hop bitterness using Glenn Tinseth's published boil-time/gravity-based
  utilization model (`modules/calculations.py:beregn_total_ibu`, `beregn_gram_fra_ibu`) — a
  genuine, already-implemented, source-backed hop-timing/IBU relationship this module's teaching
  content should stay consistent with (not re-derive or contradict), without becoming a math
  lesson about it (§1).
- The App's hop-addition editor is `ui/hop_panel.py:render_hop_panel()`, where each addition has
  an explicit `tid` (timing, minutes) field per line item — the concrete future Learn→Plan
  attachment point identified in §5.
- Static prose already exists at `web/hjelp/humle.html` (+ `web/en/hjelp/humle.html`). Per the
  governing issue, none of that prose is reused here — every claim in §2 is independently stated
  and sourced by this document, not lifted from that page.

---

## 1. Minimum learner outcome

A learner who completes this module should be able to explain, in their own words, without doing
any IBU arithmetic:

1. **What boiling does** in the brewing process — it stops mashing (enzymes are inactivated by
   heat), reduces the wort's microbial load, drives off certain unwanted volatile compounds, and
   causes proteins/polyphenols to coagulate and drop out ("hot break").
2. **Why hop timing changes contribution** — a hop addition's bitterness contribution depends on
   how long it spends at boiling temperature (isomerization takes time), while its aroma/flavor
   contribution depends on volatile oils that boil off the longer the addition is boiled — the two
   effects move in opposite directions with boil time.
3. **Bitterness vs. later/aroma-oriented additions**, at a practical conceptual level — an early
   ("bittering") addition contributes mostly bitterness and little aroma; a late/near-flameout
   addition contributes mostly aroma/flavor and little bitterness; brewers commonly combine both
   rather than relying on one single addition.
4. **What whirlpool/hop-stand means at a basic level** — hops added after active boiling has
   stopped, held at a still-hot (below-boiling) temperature for a period, aiming to extract more
   aroma/flavor with less isomerization/bitterness and less volatile-oil loss than a boil
   addition — a distinct technique from a timed boil addition, not merely "a very late boil
   addition."
5. **What to observe during boil and hop additions** — watching for the rolling boil and its
   early foam ("hot break"), which can cause a boil-over if unwatched in a fairly full kettle; and
   tracking hop-addition timing against the remaining boil time (or, for a whirlpool addition,
   against the post-boil hold time) rather than by feel.

**Explicitly not an outcome:** deriving or reciting the Tinseth utilization formula, computing an
exact IBU number, or comparing utilization models numerically. `modules/calculations.py` already
owns that calculation; this module teaches *why* timing matters, not *how to calculate* it (per
the governing issue's own instruction).

---

## 2. Proposed verified fact pack

**None of the records below exist in `bryggeskole/data/course_fact_registry.json` yet, and this
issue does not add them.** They are proposed candidates, in the exact record shape
[`BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md`](BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md) defines, for a
future, separately authorized editorial pass to review and (if it concurs) actually commit to the
registry — mirroring how `V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` §4 flagged uncommitted candidate
sources without registering them itself.

**Honesty note on sourcing, stated plainly:** this PREP round has no live network/source-fetch
access (no browsing tool was available in this run), so no claim below can be marked `verified`
per §9 of the registry contract — `verified` requires a concrete, checkable `ref` (specific
document/edition/URL) plus a review pass confirming it, neither of which this round can perform.
Every claim below is well-established, textbook-level brewing science/technique (the kind already
reflected, uncited, in this repo's own `beregn_total_ibu` docstring, which names Tinseth's model
directly) — but "well-established to the author" is not the same as "sourced per §9," so every
proposed record is recommended at `status: draft`, `sources` entries with `tier`/`type` filled in
but often *without* a concrete `ref` yet (§7's explicit "legitimate for draft, not sufficient for
verified" case). Promotion to `verified` is an explicit future owner/Chief-reviewed step requiring
an actual citation check (exact book/edition/page or URL), not performed here.

### 2.1 Candidate records

| Proposed ID | Classification | Recommended status | Claim (summarized) |
|---|---|---|---|
| `FACT-BOIL-0001` | `documented_fact` | `draft` | Boiling wort inactivates the mash enzymes and reduces microbial load carried over from mashing/lautering. |
| `FACT-BOIL-0002` | `documented_fact` | `draft` | A sustained, vigorous, open boil drives off volatile compounds (e.g. DMS precursor) that would otherwise carry into the beer. |
| `FACT-BOIL-0003` | `documented_fact` | `draft` | Boiling coagulates wort proteins and polyphenols ("hot break"); removing this material reduces haze/off-flavor risk, but this is distinct from chill haze, which forms on cooling. |
| `FACT-BOIL-0004` | `practical_experience` | `draft` | The onset of a rolling boil commonly produces a rising foam that can boil over in a fairly full kettle if unwatched; brewers commonly reduce heat briefly or watch closely during this window. |
| `FACT-HOP-0001` | `documented_fact` | `draft` | Hop alpha acids require time at boiling temperature to isomerize into soluble, bitter iso-alpha-acids; a longer boil time increases bitterness contribution from a given addition, approaching a practical ceiling rather than increasing without bound. |
| `FACT-HOP-0002` | `documented_fact` | `draft` | Hop aroma/flavor compounds (volatile essential oils) are lost the longer an addition is boiled; additions made late in the boil, at flameout, or during a post-boil whirlpool/hop-stand retain more of the original aroma/flavor character than an equivalent full-boil addition, while contributing comparatively little isomerized bitterness. |
| `FACT-HOP-0003` | `professional_interpretation` | `draft` | Because bitterness contribution and aroma/flavor retention move in opposite directions with boil time, brewers commonly combine hop additions at different times (e.g. an early "bittering" addition plus a late/whirlpool "aroma" addition) to target both independently, rather than relying on a single addition. |

### 2.2 Full entries

**`FACT-BOIL-0001`** — *documented_fact*, draft
- **Claim:** Boiling wort to an active, sustained boil inactivates the malt enzymes that were
  active during mashing (stopping further starch conversion) and reduces the wort's microbial
  load carried over from the mash/lauter.
- **Scope/limits:** "Reduces microbial load at the time of boiling" — this is not a claim that
  the wort, kettle, or any downstream equipment remains sterile afterward; post-boil handling
  (chilling, transfer, fermenter sanitation) can still introduce contamination. No specific
  minimum time/temperature threshold is asserted here.
- **Source (proposed, tier/type only, no concrete ref yet):** `{"tier": "B", "type": "established
  homebrewing/brewing-science technical text"}` — the standard "boiling stops mashing and reduces
  microbial load" statement appears across established brewing texts; an exact edition/page
  citation is owed before promotion to `verified`.
- **Wording traps to avoid:** do not say "sterilizes" (implies complete, permanent freedom from
  microorganisms); do not attach a specific minute count as a universal rule.

**`FACT-BOIL-0002`** — *documented_fact*, draft
- **Claim:** A sustained, vigorous, uncovered boil drives off volatile compounds formed from malt
  (notably a DMS precursor) that would otherwise remain in the wort and carry an off-flavor into
  the finished beer; a covered or insufficiently vigorous boil traps these compounds instead of
  venting them.
- **Scope/limits:** No specific minimum boil duration or malt-type threshold is asserted as
  universal — DMS precursor levels vary by malt (this is more relevant for base malts like
  pilsner malt than for well-modified, kilned malts), which this claim does not quantify.
- **Source (proposed):** `{"tier": "B", "type": "established brewing-science technical text
  covering DMS/wort boiling"}` — concrete ref owed before promotion.
- **Wording traps to avoid:** do not state a fixed "X minutes removes all DMS risk" rule; do not
  imply every beer style is equally sensitive to this compound.

**`FACT-BOIL-0003`** — *documented_fact*, draft
- **Claim:** Boiling causes wort proteins and polyphenols to coagulate and precipitate out (the
  "hot break"); removing this material (e.g. via a whirlpool or kettle strainer) reduces haze and
  certain off-flavor/staling risks in the finished beer.
- **Scope/limits:** Explicitly distinct from **chill haze**, which forms later, on cooling, from a
  different (colder-temperature) protein-polyphenol interaction — this claim does not cover or
  resolve chill haze.
- **Source (proposed):** `{"tier": "B", "type": "established brewing-science technical text
  covering hot break/wort clarification"}` — concrete ref owed before promotion.
- **Wording traps to avoid:** never conflate "hot break" and "chill haze" as the same phenomenon
  or imply removing hot break also prevents chill haze.

**`FACT-BOIL-0004`** — *practical_experience*, draft
- **Claim:** In the first minutes after a wort reaches a rolling boil, a rising foam ("hot break"
  foam, distinct from the coagulated hot-break material in `FACT-BOIL-0003` that later
  precipitates) commonly forms and can rise fast enough to boil over the kettle if the kettle is
  fairly full and the brewer is not watching; briefly reducing heat, using an anti-foam aid, or
  simply staying attentive during this window is common homebrewing practice to prevent it.
- **Scope/limits:** This is an established, widely observed brewing practice, not a controlled
  study result — it does not claim a boil-over always happens, nor quantify a fill-level
  threshold.
- **Source (proposed):** `{"tier": "C", "type": "established homebrewing practice/technique
  guidance"}` — no single primary citation is expected for common kettle-management practice;
  multiple independent homebrewing references describing this behavior would support promotion.
- **Wording traps to avoid:** do not present this as a guaranteed event ("will boil over"); do not
  imply a single fixed fill percentage is safe for every kettle geometry.

**`FACT-HOP-0001`** — *documented_fact*, draft
- **Claim:** Hop alpha acids are not bitter in their native form; they must isomerize at boiling
  temperature to become the soluble, bitter iso-alpha-acids that contribute perceived bitterness.
  Isomerization is time-dependent: a longer boil time for a given addition increases its
  bitterness contribution, but utilization approaches a practical ceiling rather than increasing
  without bound as boil time grows.
- **Scope/limits:** This claim describes the direction and the general isomerization/utilization
  relationship only — it does not assert or reproduce any specific numeric utilization curve or
  percentage (that remains `modules/calculations.py`'s own implemented Tinseth model, out of
  scope for this teaching claim per §1's explicit non-goal).
- **Source (proposed):** `{"tier": "A", "type": "published hop-utilization model (e.g. Tinseth's
  own published boil-time/gravity utilization work, already the basis of
  modules/calculations.py's beregn_total_ibu)"}` — a concrete ref to the specific published
  source is owed before promotion; note this differs from most other candidates here in citing a
  named, already-implemented model rather than general textbook consensus.
- **Wording traps to avoid:** do not state a specific utilization percentage or claim any one
  utilization model (Tinseth, Rager, Garetz, etc.) is the single, universally accepted number —
  models are established approximations that differ numerically from one another.

**`FACT-HOP-0002`** — *documented_fact*, draft
- **Claim:** Hop aroma and flavor come largely from volatile essential oils, which boil off the
  longer a hop addition remains in an active boil. An addition made late in the boil, at
  flameout, or during a post-boil whirlpool/hop-stand therefore retains more of its original
  aroma/flavor character than an equivalent addition boiled for the full boil time, while
  contributing comparatively little isomerized bitterness (per `FACT-HOP-0001`, isomerization
  needs boil time the addition no longer has).
- **Scope/limits:** "Comparatively little" bitterness, not "zero" — very short boil times still
  contribute some small utilization under standard models; this claim does not assert an exact
  cutoff, and it does not specify any particular whirlpool temperature/duration as optimal (those
  vary by process and hop variety, and no single source is cited here for a specific number).
- **Source (proposed):** `{"tier": "B", "type": "established brewing-science technical text
  covering hop essential-oil volatility and late-addition/whirlpool practice"}` — concrete ref
  owed before promotion.
- **Wording traps to avoid:** do not say a late/whirlpool addition contributes "zero" bitterness;
  do not assert one specific "correct" whirlpool temperature or hold time as a universal rule.

**`FACT-HOP-0003`** — *professional_interpretation*, draft
- **Claim:** Because bitterness contribution (favored by longer boil time, `FACT-HOP-0001`) and
  aroma/flavor retention (favored by shorter boil time, `FACT-HOP-0002`) move in opposite
  directions with boil time, brewers commonly use hop additions at more than one point in the
  process — e.g. an early "bittering" addition plus a late or whirlpool "aroma/flavor" addition —
  to pursue both independently in the same beer, rather than relying on a single addition.
- **Scope/limits:** This is a synthesis/interpretation of `FACT-HOP-0001`/`FACT-HOP-0002`, not a
  new independently measured result — it describes a common brewing strategy, not a fixed
  numeric schedule (e.g. it does not assert "60/20/5 minutes" as a required recipe).
- **Source (proposed):** `{"tier": "B", "type": "professional interpretation drawing on the same
  sources underlying FACT-HOP-0001/FACT-HOP-0002"}` — no independent citation beyond those two
  is expected, consistent with how `FACT-MASH-0004` (also `professional_interpretation`) is
  sourced in the existing registry.
- **Wording traps to avoid:** do not present any specific minute schedule as *the* correct or
  only pattern; do not imply single-addition recipes are wrong.

---

## 3. Module contract

### 3.1 Proposed topic id

`PILOT-BOIL-HOP-FUNDAMENTALS` — mirrors the existing `PILOT-MASHING-FUNDAMENTALS` /
`PILOT-FERMENTATION-TEMPERATURE` naming convention in `bryggeskole/pilot_mashing.py` /
`bryggeskole/pilot_fermentation.py`.

### 3.2 Learning chunks (6 — within the required 3–6)

Each chunk below is a **structural proposal** (id, source claim(s), teaching intent) — not
finished bilingual copy. Per §2's own honesty note and the precedent set by
`V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` (which authored no new teaching prose either), writing
final NO/EN chunk text is implementation-child work, done only once the underlying facts are
actually reviewed/promoted, so that chunk wording never gets ahead of what the registry has
actually verified.

| Chunk ID | `source_claims` | Teaching intent (one sentence) |
|---|---|---|
| `CHUNK-BOILHOP-A` | `FACT-BOIL-0001` | What boiling does: stops mashing, reduces microbial load. |
| `CHUNK-BOILHOP-B` | `FACT-BOIL-0002`, `FACT-BOIL-0003` | What a vigorous, open boil removes/coagulates (volatile off-flavor precursors; hot break), and what to watch for (folds in `FACT-BOIL-0004`'s foam/boil-over observation as practical context, not a separate chunk). |
| `CHUNK-BOILHOP-C` | `FACT-HOP-0001` | Why hop timing changes bitterness: isomerization takes boil time. |
| `CHUNK-BOILHOP-D` | `FACT-HOP-0002` | Why late/whirlpool additions favor aroma over bitterness: volatile oils boil off. |
| `CHUNK-BOILHOP-E` | `FACT-HOP-0003` | Why brewers combine early and late additions to get both bitterness and aroma. |
| `CHUNK-BOILHOP-F` | `FACT-HOP-0001`, `FACT-HOP-0002` | What whirlpool/hop-stand means at a basic level, as a distinct technique from a timed boil addition. |

### 3.3 Scenarios/questions

Mirroring `pilot_mashing.py`'s existing `concept_check`/`scenario` question types and
`evaluate_answer()` contract (never a raw numeric score), one question per chunk is proposed,
each declaring `source_claims` that must resolve against the **verified-only** registry API
(`get_verified_record`) exactly as the existing pilots already require — meaning none of these
questions could actually ship until at least their underlying fact(s) are promoted past `draft`.

Representative scenario shapes (final wording is implementation-child work, same reasoning as
§3.2):

- **Concept check** on `CHUNK-BOILHOP-A`: distinguishing "boiling stops mashing/reduces microbial
  load" from an overclaim like "boiling sterilizes everything downstream."
- **Scenario** on `CHUNK-BOILHOP-C`/`D`: a learner planning a very aromatic, low-bitterness pale
  ale asks whether to add all their hops at the start of the boil — tests whether the learner can
  reason from the opposite-direction relationship (`FACT-HOP-0003`) to recommend a late/whirlpool
  addition instead, without requiring an IBU calculation.
- **Concept check** on `CHUNK-BOILHOP-F`: distinguishing a whirlpool/hop-stand addition from "a
  very late boil addition" — tests that the learner understands the temperature/timing distinction
  (post-boil, still hot, not actively boiling), not just "added near the end."
- **Scenario** on `CHUNK-BOILHOP-B` (folding in `FACT-BOIL-0004`): a learner describes a kettle
  that's nearly full right as the boil starts rolling and foam is rising — tests recognition of
  the boil-over risk window and a reasonable practical response, not a specific fixed rule.

### 3.4 Feedback intent

Same pattern as the existing pilots: `feedback_correct`/`feedback_incorrect` strings giving a
short, plain-language explanation of *why*, hedged consistently with each fact's own scope/limits
(§2) — never a bare "right"/"wrong," and never asserting more certainty than the underlying fact
supports (e.g. never implying one universal whirlpool duration, per `FACT-HOP-0002`'s own
wording-trap note). No aggregate score is ever shown to the learner, consistent with `#65`'s
"hidden mastery, not a raw score" principle and the existing `evaluate_answer()` contract.

### 3.5 Hidden mastery/repetition implications

No new mastery engine or scheduling logic — this module would reuse `bryggeskole/mastery.py`'s
existing `apply_answer()`/`mastery_label()` exactly as the mash/fermentation pilots already do
(`bryggeskole_phase4_prep.md` §2 confirms these are topic-agnostic today). Proposed concept ids,
following the existing English `domain.concept` convention already used by the shipped pilots
(`mashing.temperature`, `fermentation.*`), not the earlier Norwegian examples from #65's original
sketch:

- `boil.enzyme_inactivation` (`CHUNK-BOILHOP-A`)
- `boil.volatile_removal` (`CHUNK-BOILHOP-B`, `FACT-BOIL-0002`)
- `boil.hot_break` (`CHUNK-BOILHOP-B`, `FACT-BOIL-0003`)
- `boil.observation` (`CHUNK-BOILHOP-B`, `FACT-BOIL-0004`)
- `hop.isomerization_time` (`CHUNK-BOILHOP-C`)
- `hop.aroma_volatility` (`CHUNK-BOILHOP-D`)
- `hop.addition_strategy` (`CHUNK-BOILHOP-E`)
- `hop.whirlpool_technique` (`CHUNK-BOILHOP-F`)

No V2-3C adaptive/spaced-repetition scheduler exists yet (confirmed absent per
`bryggeskole_phase4_prep.md` §1) — this module would surface hidden mastery labels exactly the
way the existing two modules already do, with no new repetition mechanism invented for boil/hop
specifically.

### 3.6 NO/EN requirements

Same bilingual shape already enforced by `bryggeskole/pilot_mashing.py`'s
`_validate_bilingual_text()` — every chunk `text`, question `prompt`, option `text`, and
`feedback_correct`/`feedback_incorrect` must carry both a `no` and an `en` value, validated
fail-closed exactly like the existing two pilots. No new i18n mechanism is proposed; this is a
direct reuse of the existing pilot content contract.

### 3.7 Future App planning hook

See §5 for the full bridge identification — restated briefly here as the module contract's own
forward pointer: `CHUNK-BOILHOP-C`/`D`/`E` are the chunks a future Learn→Plan bridge would surface
next to `ui/hop_panel.py`'s per-addition `tid` field, mirroring exactly how
`V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` surfaced `CHUNK-MASH-B`/`C` next to the mash-step
`temperatur` field. Not implemented by this issue.

---

## 4. Visual requirement

**Recommendation: a static boil/hop timeline diagram — the smallest meaningful visual, not a
decorative illustration.**

A single horizontal timeline representing the boil, left (boil start) to right (boil end), with:

- a labeled zone near the start for the hot-break/foam window (supports `CHUNK-BOILHOP-B`,
  `boil.observation`);
- addition-time markers a learner can place conceptually along the timeline (e.g. "60 min
  remaining" near the left, "5 min remaining" and "flameout" near the right);
- a **whirlpool/hop-stand zone extending past the boil-end marker**, visually distinct from the
  boil itself (different shading/pattern), directly supporting `CHUNK-BOILHOP-F`'s "whirlpool is
  not just a very late boil addition" distinction;
- two small opposing directional cues along the same timeline — bitterness contribution
  increasing toward the left (longer boil time remaining), aroma/flavor retention increasing
  toward the right — visualizing `FACT-HOP-0003`'s trade-off without any numeric axis or IBU
  scale, consistent with §1's "not an IBU math lesson" boundary.

This is deliberately **not** proposed as fully interactive in V1 — a static, well-labeled diagram
already carries the process/spatial understanding this topic needs (per Roadmap V2.2's own "not
everything must be visual... use visual interaction where it improves process, equipment or
spatial understanding" principle). An optional enhancement — clicking a marker to open its
matching chunk — mirrors the same low-complexity, context-preserving judgment
`V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` §7.0 made for its own bridge, but is not required for a
first usable slice. No 3D/game-engine visual is proposed (explicit hard non-goal, both for this
issue and for Roadmap V2.2's Bryggeri-environment work, which is explicitly later/optional).

---

## 5. Future Learn→Plan bridge

**Identified candidate, not implemented here:** `ui/hop_panel.py:render_hop_panel()` already
renders one editable row per hop addition, each with its own `tid` (timing, minutes) field. This
is the exact same shape as the Learn→Plan bridge already contracted for Mesking
(`V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md`, attaching to `ui/process_panel.py`'s mash-step
`temperatur` field) — a contextual, collapsed-by-default explanation (an `st.expander`, following
the same complexity/state-preservation reasoning as §7 of that document, not a tab jump) placed
near the hop-addition editor, surfacing `CHUNK-BOILHOP-C`/`D`/`E` so a learner editing a hop
addition's timing can see *why* that number matters — hop timing/IBU/aroma tradeoff, exactly the
connection #358's gap map named as boil/hop's likely bridge.

This is **identification only**. A real bridge needs its own bounded audit/contract document,
exactly like `V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` was for Mesking — confirming exact line
numbers, session-state keys, and a factual mismatch check against `ui/hop_panel.py`'s own copy (if
any exists) before any implementation child is authorized. No such audit is performed here, and no
App/UI code is touched by this issue.

---

## 6. Non-goals

Restated from the governing issue, since this document's own recommendations must not silently
cross them:

- No Bryggeskole module/UI code was written or changed.
- No Course Fact Registry mutation was made — §2's records are proposals only, all at `draft`,
  none committed to `bryggeskole/data/course_fact_registry.json`.
- No pilot-content file (`bryggeskole/data/pilot_boil_hop*.json` or similar) was created.
- No Learn→Plan bridge implementation was made (§5 is identification only).
- No IBU mathematics lesson content was authored (§1's explicit boundary).
- No broad hop encyclopedia, advanced/professional hopping curriculum, or chemistry deep-dive
  beyond learner need was authored — §2's fact pack is bounded to exactly what §1's five learner
  outcomes need.
- No supplier/product recommendations, recipe changes, framework/engine, Web/public
  productization, or deployment.

## Hard non-goals

(Restated verbatim from issue #362 for traceability — this document does not violate any of
these.)

- no module code;
- no broad hop encyclopedia;
- no advanced professional hopping curriculum;
- no chemistry deep-dive beyond learner need;
- no supplier/product recommendations;
- no recipe changes;
- no framework/engine;
- no Web/public productization;
- no deployment.

---

## 7. Remaining owner/Chief decision

1. **Citation check on the 7 proposed `draft` facts (§2).** This round could not fetch/verify
   exact source references (no live network access in this run) — every proposed fact needs a
   human or Chief-led pass to attach a concrete, checkable `ref` (specific book edition/page, or
   URL) before any promotion to `verified` per the registry contract's own §9 requirement. Until
   then, none of §3's chunks/questions can actually ship, since the existing pilots' own
   `source_claims` resolution requires a *verified* record (§18 of the registry contract), not
   merely a draft one.
2. **Whether `FACT-BOIL-0004`'s foam/boil-over observation stays folded into `CHUNK-BOILHOP-B`
   or becomes its own seventh chunk** — this document recommends folding it in to stay within the
   3–6 chunk range and avoid diluting the core boil/hop-timing narrative, but a future
   implementation child could reasonably split it out if it proves pedagogically awkward combined.
3. **Whether the optional clickable-marker enhancement to the §4 timeline is worth its added
   complexity** for a first usable slice, versus shipping the static diagram alone first — no
   strong preference is expressed here; this mirrors the same open-ended judgment
   `V2_2_G1A_MASH_LEARN_PLAN_CONTRACT.md` left to its own implementation child for UI polish.

No other genuine product choice in this slice required an owner tie-break beyond Chief's review of
this contract itself, per the governing issue's "Done when" criterion.
