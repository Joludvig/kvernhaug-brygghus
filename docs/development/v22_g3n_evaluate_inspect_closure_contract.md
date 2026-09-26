# V2.2 G3N — Evaluate/inspect closure contract from real Goal 2 evidence

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#390](https://github.com/Joludvig/kvernhaug-brygghus/issues/390), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3),
accepted gap map [#358](https://github.com/Joludvig/kvernhaug-brygghus/issues/358) (stages 8–9:
"evaluate/inspect teaching layer... deliberately last... use real Goal 2 evidence rather than
speculative scaffolding"), Goal 2 running case [#354](https://github.com/Joludvig/kvernhaug-brygghus/issues/354),
reflection/hypothesis implementation [#355](https://github.com/Joludvig/kvernhaug-brygghus/issues/355) /
merged [PR #356](https://github.com/Joludvig/kvernhaug-brygghus/pull/356), next-variant linkage
contract [#357](https://github.com/Joludvig/kvernhaug-brygghus/issues/357) / decision brief
`v22_g2c_next_variant_linkage_contract.md`, next-variant linkage implementation + owner-PC QA
[#363](https://github.com/Joludvig/kvernhaug-brygghus/issues/363) / merged
[PR #365](https://github.com/Joludvig/kvernhaug-brygghus/pull/365), product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65) (locked Bryggeskole direction).
Authoritative base at creation: `fc2a794371410f59c0eb644e38ca39c9cd1bf288`.

This is a decision/prep document only. It contains **no product implementation** — see
[Hard non-goals](#hard-non-goals). Chief must review this contract before any implementation
child issue is opened.

**Do not claim that the future Sommerglød v3 outcome has been brewed or evaluated. It has not
been proven by this task, and nothing in this document asserts otherwise.**

---

## 1. Audit — current source truth

### 1.1 `ui/kbhbrew_history_panel.py` — the six categories already exist as separate fields, with no scaffolding connecting them

Full read of the file (532 lines). It already renders, as **independently editable, separately
saved** groups:

- `_render_planlagt_sammendrag()` (line 131) — read-only frozen plan summary from
  `snapshot.predicted`/`snapshot.recipe` (never `actuals`/live data).
- `_render_actuals_skjema()` (line 148) — **instrument measurement**: `actuals.{og, fg,
  volumeL}` plus `actuals.notes` (measurement-adjacent free text) and `status`/`brewedAt`, its own
  "💾 Lagre målte verdier" save action.
- `_render_sammenligning()` (line 406) — read-only plan-vs-actual for `og`/`fg`/`volum`/`abv`
  only; **no `sensing.flavorProfile` comparison exists** (confirmed: `flavorProfile` is
  normalized/round-tripped by `modules/kbhbrew.py` — lines 70, 278–280, 417–419, 581–589 — but
  never rendered or edited anywhere in this panel; `_render_sensing_learning_skjema()`, line 238,
  exposes only `sensing.judgment`/`sensing.notes`).
- `_render_sensing_learning_skjema()` (line 238) — **sensory observation**
  (`sensing.judgment`/`sensing.notes`) and, in the same form but under its own subheading,
  **interpretation** (`learning.whatWorked`/`whatChanged`), **hypothesis**
  (`learning.hypothesis`, issue #355) and **decision** (`learning.nextTime`) — one shared "💾 Lagre
  sensorikk og læring" save action.
- `_render_neste_variant_seksjon()` (line 317, issue #363/#365, V2.2 G2D) — the **decision → next
  brew** step is already fully implemented and live: "🌱 Opprett neste variant" seeds an unsaved
  recipe draft from `snapshot.recipe` with a freshly minted `originRecipeId` (never inherited from
  the source), enabled only once `learning.nextTime` is non-empty; a second, separate action writes
  `learning.nextRecipeOriginId` to an already-saved recipe's `originRecipeId`, resolved by name in a
  selectbox, showing "not found" (never an error) for an unresolvable link.

**What is real and does not need to be built:** every one of the six categories the issue asks the
product to distinguish (measurement / process observation / sensory observation / interpretation /
hypothesis / decision-next-brew) already has its own field, its own widget, and — for the two
"write" actions — its own explicit save button. **What is genuinely missing:** nothing in this
panel currently explains *why* these are six separate boxes rather than one merged "how did it go"
text field, and nothing invites the brewer to explicitly record "still uncertain" rather than
forcing a premature single answer into one of the existing free-text fields.

### 1.2 `modules/kbhbrew_history_ui.py` — pure comparison/formatting helpers, no evaluate/inspect logic

`bygg_planlagt_sammendrag()` (line 83) and `bygg_planlagt_vs_faktisk()` (line 106): read-only,
`og`/`fg`/`volum`/`abv` only (never `flavorProfile`, never `sensing`/`learning`), returning `None`
for any missing value rather than fabricating one. `parse_actual_tallfelt()` is unrelated (input
validation for the actuals form). No helper here touches interpretation/hypothesis/decision at
all — that logic lives entirely in the UI layer's direct field access (§1.1).

### 1.3 Core `.kbhbrew` fields — already exactly the six categories, one already extended twice for this exact purpose

`docs/development/CORE_KBHBREW_V1.md`:

- **§5.5** (line 462) — the **immutable snapshot boundary**: `snapshot` (`recipe`, `ingredients`,
  `equipment`, `predicted`, `provenance`) is written once at brew creation and never modified
  afterward, "not even to fix a typo"; only layers 1/3/4/5 (`status`, `actuals`, `sensing`,
  `learning`, `brewedAt`) may ever be updated. A reader must reject/ignore any write attempt
  targeting an existing brew's `snapshot`.
- **§5.6** (line 473) — every field in layers 3–5 is optional and independently
  nullable/omittable; there is no minimum "complete" brew beyond layer 1 + a valid snapshot. This
  already permits "we still do not know" as a valid state for every one of the six categories —
  nothing in the wire contract requires a brewer to fill in every box.
- **§5.7** (line 483) — **measured actuals vs. derived values**: `actuals.{og, fg, volumeL}` are
  raw instrument readings stored as-entered; derived values (actual ABV, plan-vs-actual deviation)
  are always computed at read/use time, never carried as an authoritative wire field.
- **§5.8** (line 511) — **sensory/documented observation vs. instrument measurement**: `actuals`
  (layer 3) is instrument/measured; `sensing` (layer 4) is the brewer's subjective, documented
  experience; the two "must not be collapsed into one field." Cites `KBH_CORE_CONTRACT.md`'s
  Brew-Lab ownership of "observation/interpretation" as a distinct category from raw measurement
  (see §1.5 below).
- **§5.9** (line 541) — **learning/notes semantics**: `whatWorked`/`whatChanged`/`nextTime` (all
  free text, all optional, all independently editable at any time); `hypothesis` (issue #355,
  line 552) is explicitly *"not a measurement... not a sensory observation... not asserted causal
  truth... never auto-filled, never AI-generated, carries no confidence score or cause taxonomy"*;
  `nextRecipeOriginId` (issue #363, line 566) extends the same "next brew" framing to a *new,
  related* recipe, set only by an explicit brewer confirmation action, a **weak** reference that
  must never error on an unresolved target.

**Conclusion: the exact six-category separation this issue's "Product constraints" section
requires is already the ratified Core V1 wire shape.** No new `.kbhbrew` field, and no schema
version bump, is required to represent any of the six categories — they already exist,
independently, optionally, and are already correctly kept apart by two separate save actions in
the UI (§1.1).

### 1.4 `core/kbhbrew_v1.schema.json` — schema confirms the same six-way split

Lines 197–234: `actuals.{og, fg, volumeL, notes}` (measurement); `sensing.{judgment, flavorProfile,
notes}` (sensory observation — `judgment` enum `["yes","maybe","no"]`, no "unset" enum value at the
JSON level; the App-side "unset" tri-state is a UI convention, §1.1's tomstreng sentinel, not a
fourth schema enum value); `learning.{whatWorked, whatChanged, hypothesis, nextTime,
nextRecipeOriginId}` (interpretation / hypothesis / decision). `modules/kbhbrew.py` lines 69–71
(`_KJENTE_ACTUALS_FELT`/`_KJENTE_SENSING_FELT`/`_KJENTE_LEARNING_FELT`) and the
`_bygg_*_payload()`/`normaliser_*_lag()` pairs (lines 411/427/569/599) confirm this is the complete,
currently-implemented field set — matching §1.3 exactly, nothing newer exists on `master`.

### 1.5 `KBH_CORE_CONTRACT.md` — the "why six categories" answer already exists as ratified product principle, not a brewing-science claim

Section 1 (line 42) assigns "Brewing research, explanation, and pedagogy" to **Bryggeskole** and
"Actual brews, observations, and experiments" to **Brew Lab** as two distinct domains. Section 6
(line 165) states explicitly: *"Brew Lab owns the observation, experiment, and interpretation that
results when a user's batch data is used as hands-on brewing work."* This is the exact
already-ratified rationale for why Core V1 keeps `actuals`/`sensing`/`learning` apart (§1.3 cites
it directly at §5.8) — it is a **product-governance statement about domain ownership**, not a
brewing-chemistry claim, and therefore does not need Course Fact Registry sourcing to be taught
(§1.7 below draws the exact line between the two).

### 1.6 Immutable-history boundary already proven end-to-end by Goal 2 owner-PC acceptance

Per this issue's own "Owner-PC acceptance" list and `v22_g2c_next_variant_linkage_contract.md`
§6/§9's acceptance flow (issue #363, PR #365, owner-verified): a finished brew's
`snapshot.recipe`/`snapshot.predicted` stay byte-for-byte frozen; `learning.nextTime`/`hypothesis`
are freely editable at any later time; "🌱 Opprett neste variant" seeds a fresh draft with a
newly-minted `originRecipeId` that never collides with or mutates the source recipe's own ID; the
link survives an export/import round trip. **This is already-proven, already-shipped behavior**,
not something this contract needs to design or re-verify — it is cited here only as the "preserve
immutable historical source snapshot" evidence the issue's audit asks for.

### 1.7 Course Fact Registry — zero records relevant to "how to evaluate a finished beer," and this is correct, not a gap

`bryggeskole/data/course_fact_registry.json` currently has exactly these record-ID prefixes: `FACT-
BREW-*` (fermentation, 3), `FACT-MASH-*` (4), `FACT-BOIL-*` (4), `FACT-HOP-*` (3), `FACT-COOL-*`
(3), `FACT-OXY-*` (3), `FACT-TRANSFER-*` (1), `FACT-PACK-*` (4), `FACT-METHOD-*` (5) — 30 records
total, confirmed by direct grep, none about evaluation/interpretation/uncertainty as a general
skill. **This is not a gap requiring a new fact/source pack.** Per
`BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md` §0, the registry exists for **brewing-knowledge claims**
that need Tier A/B source provenance (hop chemistry, mash enzymology, sanitation windows, etc.).
"Measurement is not the same thing as your interpretation of it, and it's fine to not yet know
which of several possible explanations is right" is not a brewing-science claim — it is the same
kind of **product-methodology statement** `hypothesis` (issue #355) and the Core Contract's own
domain-ownership text (§1.5) already ship as UI copy without ever touching the Registry. Answer to
the issue's audit point 7: **no missing factual support — none is needed**, and this document does
not propose any new Course Fact Registry record.

### 1.8 Current Bryggeskole architecture — six topic-scoped modules, no "evaluate" module, and the accepted gap map already recommended against adding a seventh

`ui/bryggeskole_panel.py` (docstring, lines 1–60) wires exactly six self-contained, topic-scoped
pilot-clone modules (Forberedelse/metode, Mesking, Koking, Kjøling/overføring, Gjæring, Pakking),
each following the same non-shared-engine pattern (`bryggeskole/pilot_*.py`, each with its own
`PilotContentError`, its own fact-pack JSON, its own place in the shared six-stage
`_PROSESS_STADIER` grid). **There is no seventh "evaluate" module, and none of the six existing
ones covers stages 8–9.** The accepted gap map (#358,
[comment](https://github.com/Joludvig/kvernhaug-brygghus/issues/358#issuecomment-5771688004))
already reached this exact conclusion for these two stages: *"Evaluate/inspect teaching layer (stages 8–9) — deliberately
last, gated on real Goal 2 evidence, and likely the smallest slice overall (a few facts + concept
links surfaced inside the existing reflection UI, not a new module)."* This document's own
independent audit (§1.1–§1.7) reaches the same placement conclusion from first principles, and
additionally finds that even the parenthetical "a few facts" turns out not to be needed (§1.7).

### 1.9 Real Goal 2 evidence used

`docs/brew-lab/history/sommerglod-v1-v2.md` (the reconstructed, review-flagged record #354 already
established as this project's running case):

- **Sommerglød v1 → v2**: a real `whatChanged`/`nextTime`-shaped decision already exists in the
  record's own "Interpretation" section — v1's 7% Rauchmalz smoke was judged "too subtle/short-
  lived," v2 raised it to 10%, and v2's own "Sensory observations" section records the smoke was
  *still* judged too subtle. This is a real, already-recorded case of a *hypothesis-informed
  decision that did not fully resolve the underlying question* — exactly the kind of outcome the
  issue's "a valid outcome may be: 'we still do not know'" constraint must support, not something
  this document invents.
- **Sommerglød v2's own App-local evidence is explicitly, already-recorded as internally
  conflicting**: two legacy log entries dated `2026-07-13` disagree on FG (`1.0086588198424` vs.
  `1.010`) and ABV (`5.7%` vs. `5.5%`), and the reconstruction explicitly flags that entry A's FG is
  byte-identical to the recipe-computed FG, so "no silent reconciliation is made." **This is the
  single clearest piece of real evidence that the product must be able to represent "measured but
  conflicting/uncertain," not force one number to win.** Today's `.kbhbrew` model has exactly one
  `actuals.fg` value per brew — a genuine structural gap this document's recommendation (§4) must
  account for without inventing a new confidence/reconciliation field (§4.3, §5).

No Sommerglød data is created, renamed, or brewed by this document. The case remains illustrative
evidence for what the product must support, per this issue's own "Real evidence boundary."

---

## 2. Answers to the issue's required audit questions

1. **Can the six required categories already be distinguished in Brew History?** Yes — completely,
   already, since #355/#356 shipped `hypothesis` (§1.1, §1.3). The gap is not a missing category;
   it is missing *scaffolding* explaining why they're separate and inviting explicit uncertainty.
2. **Is the immutable-snapshot boundary already safe?** Yes, proven end-to-end (§1.6); this
   document adds no write path that could threaten it (§4.3).
3. **Does evaluating a finished beer need any new Core field?** No (§1.3, §1.4). The "conflicting
   evidence" case (§1.9) is real, but is already representable today as free text in
   `actuals.notes`/`sensing.notes`/`learning.whatChanged` — no structured "confidence" or
   "reconciliation" field is proposed (§4.3 explains why one would violate the issue's own hard
   non-goals).
4. **Does this need new verified facts?** No (§1.7) — this is a methodology/domain-ownership
   teaching point already ratified in `KBH_CORE_CONTRACT.md`, not a brewing-science claim.
5. **New Bryggeskole module, or contextual Brew History teaching?** Contextual Brew History
   teaching (§4) — matching both this document's own audit (§1.8) and the Chief-accepted #358 gap
   map's own prior conclusion for exactly these two stages.

---

## 3. Exact selected user task

While looking at one selected finished brew in Brew History (`ui/kbhbrew_history_panel.py`), before
filling in or editing the actuals/sensing/learning forms, the brewer can open one small, collapsed
"how to read this brew's evidence" bridge that:

1. Names the six already-existing, already-separate fields on this exact screen — measured values
   (`actuals.og/fg/volumeL`), process notes (`actuals.notes`/`brewedAt`), sensory observation
   (`sensing.judgment`/`sensing.notes`), interpretation (`learning.whatWorked`/`whatChanged`),
   hypothesis (`learning.hypothesis`), and decision/next brew (`learning.nextTime` +
   "🌱 Opprett neste variant" / `nextRecipeOriginId`) — and explains, in the product's own already-
   ratified terms (§1.5), why keeping them apart matters: a measurement is not your interpretation
   of it, and a hypothesis is not a decision.
2. Explicitly states that leaving any of these boxes blank, or writing that you don't yet know
   which of two explanations is right, is a valid, expected outcome — never a thing to be papered
   over with a fabricated single conclusion — directly informed by the real Sommerglød v2
   conflicting-FG evidence (§1.9), without naming Sommerglød in the shipped copy (§4.3).
3. Reminds the brewer, in one sentence, that the frozen plan above (`_render_planlagt_sammendrag`)
   can never change, and that `learning.nextTime` is the one field most worth filling in before
   starting the next brew (restating `CORE_KBHBREW_V1.md` §5.9's own existing "single most
   important value" framing, not inventing a new claim).

No new field, no new save action, no new module, no automatic reasoning, and no AI-authored
interpretation is added. This is the smallest possible teaching layer that closes Goal 3 stages 8–9
using only fields, actions, and ratified product text that already exist.

---

## 4. Recommendation

### 4.1 UI placement: one collapsed `st.expander` bridge inside `ui/kbhbrew_history_panel.py`

Placed directly after `_render_planlagt_sammendrag()` (line 131 today) and before
`_render_actuals_skjema()` (line 148) — teaching the "why six boxes" framing immediately before the
brewer starts filling any of them in, mirroring the established "teach immediately before the
deliberate choice" placement principle already used by every existing Learn→Plan bridge
(`ui/process_panel.py`, `ui/yeast_panel.py`, `ui/hop_panel.py`, per
`v22_g3l_boil_hop_learn_plan_contract.md` §4). This is the first bridge of this *shape* — Learn→
**Reflect**, not Learn→Plan — but reuses the identical collapsed-expander, read-only,
no-mastery-interaction convention unchanged.

Rendered exactly once per selected brew (not once per field, not once per category) — the same
"shared context shown once, not duplicated per row/field" principle the Koking bridge already
established for a repeating-row panel (`v22_g3l...md` §4's "why one shared bridge, not one per
row").

### 4.2 Content: existing ratified product text, not new Registry-sourced pilot chunks

Unlike every prior Learn→Plan bridge, this one does **not** call `read_pilot_file()`/
`render_chunk()` against any `bryggeskole/pilot_*.py` module or `course_fact_registry.json` record
— §1.7/§1.8 establish that no such content exists or is needed for this task. Instead, the bridge
is plain new i18n copy (like the existing `koking.laer_bro.guardrail` disclosure caption) that
restates, in learner-facing language, the already-ratified separation already cited in §1.3/§1.5:
`CORE_KBHBREW_V1.md` §5.5/§5.8/§5.9 and `KBH_CORE_CONTRACT.md` §1/§6. No new sentence introduces a
brewing-science claim; every sentence traces to an existing, already-reviewed governing document,
not to this document's own authority.

### 4.3 What this V1 contract deliberately does not do

- **No new `.kbhbrew`/Core field.** The real conflicting-evidence case (§1.9) is handled by
  inviting the brewer to write "still uncertain — two readings disagreed" into the *existing*
  `actuals.notes`/`sensing.notes`/`learning.whatChanged` free text, exactly as today's schema
  already allows (§1.3's §5.6 optionality). Adding a structured "confidence" or "reconciled value"
  field was considered and rejected: it would start building exactly the "confidence score system"
  the issue's hard non-goals forbid, for a case the existing free-text fields already cover.
- **No new Bryggeskole module, no new pilot file, no new fact pack.** §1.7/§1.8.
- **No AI diagnosis, no automatic causal explanation.** The bridge names categories; it never
  reads or summarizes what the brewer actually wrote into any field.
- **No generic troubleshooting encyclopedia.** The bridge teaches how to *read your own evidence*,
  not "what smoke-retention problems usually mean" or any other beer-fault content — it contains
  zero brewing-fault-specific claims.
- **No mutation of `snapshot`, and no new write path of any kind** — purely a read-only expander;
  the two existing save actions (`_render_actuals_skjema`, `_render_sensing_learning_skjema`) and
  the next-variant actions (`_render_neste_variant_seksjon`) are untouched.
- **No Sommerglød data created, renamed, or claimed brewed** (§1.9's own boundary, restated).
- **No Web/public deploy** — App-only, matching every other Bryggeskole/Learn→Plan precedent to
  date.
- **No Sóti integration.**

---

## 5. Alternatives considered

- **Build a seventh Bryggeskole "Evaluate" module**, structurally cloned from
  `pilot_mashing.py`/etc. Rejected — §1.7/§1.8 show there is no sourced factual corpus this module
  would teach that isn't already either (a) covered by the six existing category fields themselves,
  or (b) a domain-ownership statement already shipped in `KBH_CORE_CONTRACT.md`. A module with no
  Registry-backed content would be either empty scaffolding or, worse, pressure to invent
  unsourced "how to fix your beer" content — exactly the encyclopedia risk the issue forbids.
- **Add a structured "uncertainty"/confidence field to `learning` or `sensing`.** Rejected (§4.3) —
  the real evidence (§1.9) that motivates this is already representable in existing free text; a
  new structured field would start down the explicitly forbidden "confidence score system" path for
  no material gain over inviting the same statement in prose.
- **Teach this inside a new/expanded static `sensorikk.html` Web page instead of inside the App's
  Brew History panel.** Rejected — the gap map (#358, comment cited §1.8) already found
  `sensorikk.html` to be "generic troubleshooting," disconnected from any specific brew's actual
  recorded data; the whole point of this closure is to teach *at* the real, already-populated
  fields for *this* brew, which only the App's Brew History panel can do. Web is out of scope for
  this App/Core-focused closure, matching every prior Learn→Plan precedent's own scoping.
- **Reuse an existing Registry concept id (e.g. via `modules`/`concepts` cross-linking, the way
  Pakking/Forberedelse reuse Kjøling/Mesking facts).** Rejected — that mechanism exists to reuse an
  *already-verified brewing claim* across two topic modules; there is no such claim here to reuse
  (§1.7), so forcing a concept-id link would misrepresent a product-methodology statement as a
  sourced brewing fact.

---

## 6. NO/EN wording constraints

New `modules/i18n.py` keys, following the exact `<panel>.laer_bro.<element>` naming convention
already established by `prosess.laer_bro.*`/`gjaering.laer_bro.*`/`koking.laer_bro.*`, adapted to
this panel's own existing `brew_history.*` prefix:

| Key | Constraint |
|---|---|
| `brew_history.laer_bro.tittel` | Short, inviting, collapsed-by-default label, e.g. "🎓 Hvordan lese dette bryggets bevis?" / "🎓 How to read this brew's evidence?" — same tone as the three existing `*.laer_bro.tittel` keys. |
| `brew_history.laer_bro.forklaring` | Must name, in both languages, the six existing field groups on this screen by their plain-language role (measured value / process note / sensory observation / interpretation / hypothesis / decision) and state plainly that a measurement is not the same as your interpretation of it, citing no brewing-science claim — only the product's own field-separation principle (§4.2). Must not name `learning.hypothesis`'s field key verbatim to the learner; describe it in plain language, matching how `learning_hypothesis_caption` already does today. |
| `brew_history.laer_bro.usikkerhet_hint` | Must explicitly state that leaving a box blank, or writing that you don't yet know which explanation is right, is a valid, expected entry — never something to force into a false single conclusion. Must not introduce or imply any confidence score, percentage, or ranking. |
| `brew_history.laer_bro.neste_tid_hint` | One sentence restating that `learning.nextTime` (labelled via the existing `brew_history.learning_next_time_label` copy, not renamed) is the single most useful thing to fill in before the next brew — matching `CORE_KBHBREW_V1.md` §5.9's existing framing, not a new claim. |

No footer "practice more in Bryggeskole → X" line is added (unlike the three Learn→Plan
precedents) — there is deliberately no dedicated Bryggeskole module for this content to point to
(§1.8, §4.3), and inventing one only to have a footer target would be exactly the module this
document declines to build.

`bryggeskole.feil.innhold_ugyldig` is **not** reused here and no equivalent new error key is
needed — this bridge renders static i18n strings, never `PilotContentError`-raising pilot content
(§4.2), so there is no invalid-content failure mode to guard against (§8).

---

## 7. Persistence / session-state implications

None beyond what already exists. No new `.kbhbrew`/Core field (§4.3), no new session-state key
bound to persisted data, no change to any of the three existing save actions
(`_render_actuals_skjema`, `_render_sensing_learning_skjema`, `_render_neste_variant_seksjon`) or
their widget keys. The only new state is the `st.expander`'s own open/closed cosmetic flag, which
Streamlit manages implicitly — mirroring `v22_g3l...md` §6's identical conclusion for the Koking
bridge. **DEMO_MODE:** no new guard needed — the bridge reads no disk state of its own (its copy is
static i18n text, not a pilot JSON file); the existing `render_kbhbrew_history_panel()`
DEMO_MODE early-return (line 480) already hides the entire panel, including this bridge, in Demo
Mode exactly as it hides everything else in this file today.

---

## 8. Fail-closed behavior

- **No new failure mode is introduced.** The bridge is static, read-only display text; it never
  writes to `actuals`/`sensing`/`learning`/`snapshot`/any widget key.
- **No pilot-content parsing risk.** Because §4.2 deliberately does not call
  `read_pilot_file()`/`render_chunk()`, there is no `PilotContentError` path to catch — a
  meaningful difference from every prior Learn→Plan bridge, stated explicitly so the implementation
  child does not add an unnecessary `try`/`except` around plain `st.markdown()`/`t()` calls.
- **Unresolvable next-variant links remain unchanged.** This bridge does not touch
  `_render_neste_variant_seksjon()`'s existing "not found, never an error" behavior for an
  unresolvable `nextRecipeOriginId` (§1.1) — that guarantee is unaffected by this addition.

---

## 9. Representative human acceptance scenario

Mirroring the Learn→Plan precedents' own §9 structure — a human acceptance step, separate from and
in addition to the automated tests in §10:

- **Setup:** the evaluator is given one finished, non-Sommerglød brew record with a measured OG/FG
  already entered, and is told (out of band, not by the App) that two independent readings of one
  of those values actually disagreed during the real brew day.
- **Task:** the evaluator opens the new bridge, then fills in the actuals/sensing/learning forms
  for that brew, explicitly recording the disagreement as an uncertain note rather than picking one
  reading and discarding the other, and records one concrete `nextTime` decision.
- **Observable PASS criteria (all three required):** (1) the evaluator can state, in their own
  words, which of the six categories each of their own entries belongs to and why; (2) the
  disagreement is recorded as an explicit "not sure which reading is right" note, not silently
  resolved to one value; (3) the recorded `nextTime` decision is a decision, not a restatement of
  the measurement or the hypothesis.
- **Observable FAIL criteria (any one):** the evaluator collapses two categories into one
  paragraph with no ability to say which is which; the evaluator silently picks one of the two
  disagreeing readings without noting the conflict; the bridge is read as claiming to diagnose or
  explain the brew's outcome itself.
- **Method and scope:** representative human acceptance evidence only; no owner-as-student gate, no
  new schema, no new authored pilot/registry content, no scoring UI or mastery-store change (this
  bridge never touches `bryggeskole/mastery_store.py` — it lives entirely inside Brew History, not
  inside any Bryggeskole module's session state).

---

## 10. Automated test plan for the implementation child

1. **New test coverage for the bridge** (extending `tests/test_kbhbrew_history_ui_helpers.py` or a
   new `tests/test_kbhbrew_history_panel_evaluate_bridge.py`, using the same `AppTest`-driven
   pattern as `tests/test_process_panel.py`'s existing Learn→Plan bridge tests):
   - the bridge expander exists, is collapsed by default, and renders exactly once per selected
     brew, placed after `_render_planlagt_sammendrag` and before `_render_actuals_skjema`;
   - it renders the four new `brew_history.laer_bro.*` strings for both `no` and `en`;
   - it never calls `read_pilot_file()`/renders a `PilotContentError` path (confirms §4.2/§8);
   - selecting a different brew, or the existing sync-guard behavior (`_UKJENT_SENTINEL`, lines
     99–105, 497–516), is unaffected — the bridge introduces no new session-state key beyond its
     own cosmetic expander flag;
   - existing behavior is unchanged: `_render_actuals_skjema`, `_render_sensing_learning_skjema`,
     and `_render_neste_variant_seksjon` still save exactly the fields they save today, with the
     same two independent save actions.
2. **`tests/test_kbhbrew_engine_readerwriter.py`, `tests/test_kbhbrew_snapshot.py`,
   `tests/test_kbhbrew_roundtrip.py`** — unchanged, run as regression proof that no `.kbhbrew`
   field/shape changed (§4.3 adds none).
3. **`tests/test_kbhbrew_history_ui_helpers.py`** (existing) — unchanged, run as regression proof
   that `bygg_planlagt_sammendrag`/`bygg_planlagt_vs_faktisk` are untouched.
4. **`tests/test_course_fact_registry.py`** — unchanged; this issue and its implementation child
   make no edit to `course_fact_registry.json` (§1.7).
5. Full Python suite (`python3 -m unittest discover -s tests -b`) at the implementation child's
   final checkpoint, per [`.claude/rules/testing.md`](../../.claude/rules/testing.md).

This document itself only requires confirming every cited file:line still resolves against
current master, done as part of writing it (§1).

---

## 11. Explicit non-goals

Restated from the governing issue, since this document's own recommendation must not silently
cross them:

- No App/UI implementation was made in this issue.
- No Course Fact Registry mutation was made or proposed (§1.7, §5).
- No pilot-content mutation, no new Bryggeskole module (§1.8, §5).
- No `.kbhbrew`/Core schema mutation, and none is recommended (§1.3/§1.4/§4.3 explicitly find none
  needed).
- No AI diagnosis, no automatic causal explanation, no confidence score system (§4.3).
- No generic troubleshooting encyclopedia (§4.3, §5).
- No experiment/statistics platform, no automatic recipe optimization.
- No mutation of historical brew/snapshot truth (§1.6, §4.3, §7).
- No source-data normalization.
- No professional/certification depth, no generalized course framework rewrite.
- No Web/public deploy, no Sóti integration.
- No Sommerglød data created, renamed, or claimed brewed/evaluated (§1.9).
- No implementation in this issue.

## Hard non-goals

(Restated verbatim from issue #390 for traceability — this document does not violate any of
these.)

- No AI diagnosis.
- No automatic causal explanation.
- No generic troubleshooting encyclopedia.
- No experiment/statistics platform.
- No automatic recipe optimization.
- No mutation of historical brew/snapshot truth.
- No source-data normalization.
- No confidence score system.
- No professional/certification depth.
- No generalized course framework rewrite.
- No Web/public deploy.
- No Sóti integration.
- No implementation in this issue.

---

## 12. One bounded implementation recommendation

A single implementation child should add exactly one `st.expander` bridge (§4.1) to
`ui/kbhbrew_history_panel.py::render_kbhbrew_history_panel()`, placed between
`_render_planlagt_sammendrag()` and `_render_actuals_skjema()`; add the four `brew_history.laer_bro.*`
i18n keys (§6) to `modules/i18n.py`'s NO/EN blocks; add no new persisted field, session-state key,
Course Fact Registry record, or Bryggeskole module; and cover it with the test plan in §10. No
schema, calculation, mastery-store, or existing-save-action change belongs in this child.

---

## 13. Remaining owner/Chief decisions

None identified for this bounded slice. The six required categories, the immutable-snapshot
boundary, and the decision→next-recipe linkage are already fully implemented and owner-PC-verified
(§1.1, §1.3, §1.6); this document's only addition is a small, static, read-only teaching overlay
that requires no new sourced content and no new module.

A future, separately authorized round may decide whether the eventual *real* next-loop comparison
— "linked next recipe → brewed result → later evaluation," explicitly **not yet proven** by any
work to date (issue #390's own "Critical future-loop boundary") — deserves its own UI once a real
brew actually exists on the other end of a `nextRecipeOriginId` link. That is not a prerequisite
for this contract's recommendation and is not designed here.
