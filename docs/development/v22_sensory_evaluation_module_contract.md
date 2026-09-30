# V2.2 — Smak og evaluering (sensory evaluation) Kompetent contract

Version: 1.0
Status: Decision/prep document — reviewable, not yet actionable
Governed by: [#438](https://github.com/Joludvig/kvernhaug-brygghus/issues/438), bounded child of
[#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) (Roadmap V2.2, Goal 3); product direction
[#65](https://github.com/Joludvig/kvernhaug-brygghus/issues/65); curriculum owner
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (merged), whose map
(`v22_g3q_full_bryggeskole_curriculum_map.md`, topics D54–D56, module 10) recommends this module. Sibling contracts:
`v22_recipe_understanding_module_contract.md` (#436), `v22_measurement_brewlog_module_contract.md` (#434), and the Brew History methodology in
`v22_g3n_evaluate_inspect_closure_contract.md` (§1.7) and `CORE_KBHBREW_V1.md`.
Authoritative base at creation: `d291cdd2b13c2636df3ddfa8dfb983b7db8962a1`.

This is a docs-only contract. It contains **no product code, no Course Fact Registry mutation, no new verified fact, no module, no UI, no Brew
History/Core/schema change, no App/Web/Sóti change and no deploy**. Chief must review it before any implementation child issue is opened.

## 1. Source-status guard (read first)

The source reconnaissance behind this contract (delivered to the owner before #438) is a **source map, not a verified fact pack**. It is not stored
in the repository, and **this run did not open any external source**. Therefore:

- Sources named in §22 are recorded as the reconnaissance found them. They are **directions for the later fact-pack round**, not citations. The
  fact-pack round must re-open and read every source it cites, record tier, date, scope and access method, mark commercial interest, and have Chief
  review it. AI is never a source.
- Every candidate claim in §6 is **unverified** until that round has done so.
- Only the registry records in §5 are reusable now, and only within their existing `notes` and wording-trap scope.
- Some reconnaissance material was read directly, some through a summarising fetch tool, and some only as search-result text. The fact-pack round
  must spot-check every such item against the live source before promoting any record.
- The Kunze pages named in §22 (printed pp. 376, 377, 505, 762, 763) were visually verified during reconnaissance. They were not re-opened in this run.
- No numeric thresholds, concentrations, temperatures, times or scores appear in this contract or may appear in teaching.

**Level naming.** The #419 map uses L1/L2. In this contract **Foundation = L1** and **Kompetent = L2**.

**Chief decisions recorded as fixed inputs** (not re-opened here): the fault set in §9; `FACT-SENSORY-000n` as the sensory fact family; one
consolidated descriptor record; light-struck taught here as SHOULD; no health claim about spoilage; no Brew History schema change; bias note as a short
methodology note only; BJCP as context only; no numeric serving temperature; no new detailed staling fact.

## 2. Foundation prerequisites

There is **no new Foundation teaching** in this module. Reuse only the existing checkpoint from #435:

> **Write what you observed separately from your guess about why.**

Observation-versus-interpretation is **methodology, not a new Course Fact** (G3N §1.7). Foundation already covers, elsewhere: the process facts in §5
(boil, cooling, oxygen, sanitation boundary, yeast and fermentation temperature), and OG/FG as measurements (#435).

## 3. Kompetent learner outcomes

After Smak og evaluering, a homebrewer can, in their own words and without numbers or compound names to memorise:

1. taste their own beer on purpose with a simple structure (LOOK · SMELL · TASTE · FEEL · NOTE) and write down what they actually perceive;
2. keep an **observation** apart from an **interpretation**, a **hypothesis** and a **decision**, and accept "I don't know yet" as a complete answer;
3. compare the finished beer with the beer they intended, describing the difference in words and not with a grade;
4. recognise a **small** set of common faults (§9) and say, for each, what it may point to without claiming it is proven;
5. say that a descriptor becomes a "fault" only relative to what they intended, how strong it is and the context;
6. recognise **green (immature) beer** character and understand, qualitatively, that time with healthy yeast changes it;
7. say the difference between intended sourness and unwanted microbial contamination or spoilage, and that taste alone does not establish which;
8. use a few practical tasting habits (§18) and know that expectations can influence perception (§19);
9. record the result in the existing Brew History fields (§20) and choose **one deliberate next change** as a hypothesis test, not as proof.

The learner finishes able to say: "I can taste my beer systematically, describe what I actually perceive, compare it with what I intended, stay honest
about what I don't know, and choose one sensible next change."

## 4. MUST / SHOULD / LATER concepts

Concept ids equal the registry concept ids that question `concepts[]` will carry (§26).

| Level | Concept | Proposed id | Basis |
|---|---|---|---|
| Kompetent MUST | Taste on purpose (LOOK · SMELL · TASTE · FEEL · NOTE) | `sensory.tasting_sequence` | Methodology |
| Kompetent MUST | Observation is not diagnosis | `sensory.observation_vs_interpretation` | Methodology (G3N §1.7, #435) |
| Kompetent MUST | Evaluate against intent; one deliberate change | `sensory.evaluate_against_intent` | Methodology (G3N, #436) |
| Kompetent MUST | Fault versus intended character | `sensory.fault_vs_character` | Methodology, plus future descriptor context |
| Kompetent MUST | Diacetyl | `sensory.diacetyl` | Future S-1 |
| Kompetent MUST | DMS | `sensory.dms_recognition` | Future S-4 descriptor; process = FACT-BOIL-0002 |
| Kompetent MUST | Oxidation / stale character | `sensory.oxidation_recognition` | Future S-4 descriptor; process = FACT-OXY-0002 |
| Kompetent MUST | Sourness versus unwanted microbial contamination / spoilage | `sensory.sourness_intent_vs_spoilage` | Future S-2 |
| Kompetent SHOULD | Light-struck | `sensory.lightstruck` | Future S-3 |
| Kompetent SHOULD | Acetaldehyde / green-beer character | `sensory.green_beer` | Future S-1 and S-4 (no standalone fact) |
| Kompetent SHOULD | Temporary / strain-dependent sulphur | `sensory.green_beer` | No standalone fact |
| Kompetent SHOULD | Tasting habits | `sensory.tasting_habits` | Methodology |
| Kompetent SHOULD | Expectation and comparison note | `sensory.expectation_note` | Methodology |
| Kompetent SHOULD | Typical descriptors as vocabulary | `sensory.typical_descriptors` | Future S-4 |
| LATER / examples only | Phenolic, astringency, metallic, fusel/solvent, ester faults, the wider off-flavour-wheel catalogue | — | Not in the beginner set |
| LATER | Detailed staling, time and warmth, shelf life | — | Pakking / D58 |
| LATER | Formal panels, scoresheets, thresholds, statistics, lab analysis | — | Non-goals (§33) |

Deviation from the #419 map: D54 is MUST L2 with five example faults. Here the fault set is **narrowed and deepened** (§9) and taught as "recognise and
interpret carefully", not as a catalogue. D55 and D56 are unchanged in level.

## 5. Existing facts reused

Verified registry records on origin/master `d291cdd` (39 records). Reuse is limited to each record's own `notes` and wording traps.

| Record | Used for |
|---|---|
| **FACT-BOIL-0002** | DMS **process truth**: precursor, DMS is the volatile material, a vigorous sufficiently long boil is one control. Trap kept: never call the precursor volatile |
| **FACT-OXY-0002** | Oxidation **process truth**: oxygen after fermentation starts is generally undesirable; cardboard/stale notes, diminished hop aroma, reduced shelf stability |
| FACT-OXY-0001, FACT-OXY-0003 | Oxygen timing; no target number |
| FACT-YEAST-0001 | Yeast metabolism contributes flavour and aroma compounds |
| FACT-BREW-0001, -0002, -0003 | Fermentation temperature and yeast flavour are strain-dependent; no universal temperature |
| FACT-COOL-0001, FACT-COOL-0003 | Fast cooling and the sanitation boundary (spoilage organisms; **not** a health claim) |
| FACT-HOP-0002 | Hop aroma is volatile |
| FACT-MALT-0003 | Colour is not a one-to-one flavour predictor |
| FACT-BOIL-0003, FACT-COOL-0002 | Hot and cold break, for the clarity/haze observation |
| FACT-PACK-*, FACT-TRANSFER-0001 | Only within their existing scope, as process links |

**Do not duplicate** the DMS process truth or the oxidation process truth. A sensory chunk links to FACT-BOIL-0002 and FACT-OXY-0002; it does not
restate their mechanisms in a new record.

**Planned, not yet in the registry (dependencies, not reuse today):** #435 M2 (stable gravity), and #436 R-2 / R-4 (perceived bitterness and balance).

**No registry record exists** for sensory basics, diacetyl, acetaldehyde, light-struck, sourness or spoilage, or typical descriptors.

## 6. Smallest future sensory fact pack

**No registry mutation happens in #438.** Ids use `FACT-SENSORY-000n`; numbers are assigned at implementation time. Later order: **S-1, S-4, S-2, S-3.**

**S-1 — `sensory.diacetyl` — `documented_fact`.** Direction (unverified):

- a butter / butterscotch descriptor;
- generated during normal yeast fermentation through a precursor;
- healthy yeast can reduce it during maturation or contact;
- bacteria may also produce it;
- low levels may be accepted in some beer contexts;
- generally undesirable when unintentionally prominent.

Must not contain: thresholds; a fixed rest temperature or time; "butter proves diacetyl"; "more time always fixes it"; any commercial enzyme
treatment. **Note:** a "slick / oily mouthfeel" sentence that appeared in the reconnaissance was garbled and is **not** supported by the Brewers
Association evidence in hand; it is **not** carried into this contract or any future record as sourced truth.

**S-4 — `sensory.typical_descriptors` — `documented_fact`.** **One** tightly scoped, consolidated descriptor record (not one per fault):

- DMS: sweetcorn / cooked-vegetable family;
- oxidation / stale: cardboard / paper family, possibly sherry-like in an appropriate aged-beer context;
- acetaldehyde: green-apple family;
- light-struck: skunky family.

Critical rule: **descriptor ≠ diagnosis.** The record must not restate the BOIL-0002 or OXY-0002 mechanisms.

**S-2 — `sensory.sourness_intent_vs_spoilage` — `documented_fact`.** Direction: acidity can be intentional in sour beer; unexpected sourness in a beer
not intended to be sour can be associated with microbial spoilage; taste alone does not establish cause. Quality and sensory scope only.
**No health claim** (§14).

**S-3 — `sensory.lightstruck` — `documented_fact`.** Direction: light plus hop-derived bitter compounds plus photosensitiser chemistry can produce a
skunky character; brown or amber glass protects much better than clear or green glass. Must not contain: wavelength teaching, thresholds, minute
rules, or "brown glass makes beer immune". Pakking may reuse this record later; no duplicate process truth.

**Every future fact round must:** reopen sources live; record tier, date, scope and access method; mark commercial interest; re-view the relevant
Kunze pages; and spot-check any earlier fetch-summary or snippet material. Sources and gaps: §22, §23.

## 7. Sensory mental model

```
OBSERVE → DESCRIBE → COMPARE → INTERPRET CAREFULLY → HYPOTHESIS → NEXT CHANGE
```

- **Observe:** what is actually there, with no cause.
- **Describe:** in the brewer's own words first, then optional vocabulary; intensity as well as descriptor.
- **Compare:** with the intended beer and, where useful, a reference beer or the last batch.
- **Interpret carefully:** "may", "could", "one possibility"; several causes can give a similar perception.
- **Hypothesis:** a possible explanation, not asserted truth.
- **Next change:** one deliberate change.

**"Still uncertain" is a valid endpoint** at interpretation or hypothesis.

Classification:

- **Documented facts:** typical descriptors; supported mechanisms and origins (§6).
- **Professional interpretation:** diagnose cautiously; several causes may produce similar perceptions.
- **Kvernhaug methodology:** the sequence itself; uncertainty is valid; one deliberate next change.

Only the first belongs in the registry.

## 8. LOOK · SMELL · TASTE · FEEL · NOTE framework

**This framework is Kvernhaug methodology, not sensory-science truth.** It is a structured way to notice, not a formal scoring instrument, and **there
is no scoring sheet.**

| Step | What the brewer does |
|---|---|
| **LOOK** | Colour; clarity or haze; head or foam only at a simple observation level. Reuse FACT-MALT-0003 (colour is not flavour) and the break facts for haze; no foam science |
| **SMELL** | Notice intensity; use own words first; **no causal conclusion from aroma alone** |
| **TASTE** | Sweetness, bitterness, sourness, malt / hop / yeast character; aftertaste may live here |
| **FEEL** | Body, carbonation, warmth, and dry or puckering as **plain description** (not a cause, not bitterness) |
| **NOTE** | Write the observations and **keep them separate from interpretation** |

The existing Web page's five steps (see, smell, taste, mouthfeel, aftertaste) are compatible; the reconciliation gate is §32.

## 9. Beginner fault set

**Do not expand this set.**

| Level | Fault | Teaching depth |
|---|---|---|
| Kompetent MUST | 1. Diacetyl | recognise + cautious fermentation/maturation connection (future S-1) |
| Kompetent MUST | 2. DMS | recognise (S-4 descriptor) + link to FACT-BOIL-0002 |
| Kompetent MUST | 3. Oxidation / stale character | recognise (S-4 descriptor) + link to FACT-OXY-0002 |
| Kompetent MUST | 4. Sourness vs unwanted microbial contamination / spoilage | recognise + limits (future S-2) |
| Kompetent SHOULD | 5. Light-struck | recognise + cause only (future S-3) |
| Kompetent SHOULD | 6. Acetaldehyde / green-beer character | inside the green-beer concept (S-1/S-4) |
| Kompetent SHOULD | 7. Temporary / strain-dependent sulphur | short note inside the green-beer concept |

**Phenolic, astringency, metallic, fusel/solvent, ester faults and the larger off-flavour-wheel catalogue stay LATER or examples only.** Phenolic and
ester character may appear as examples inside §16 without a fact and without being taught as faults. Astringency must never be taught as bitterness.

For each item the module teaches "recognise, and hold several possible causes open"; a fault name is **not** vocabulary to memorise.

## 10. Diacetyl governance

- **Level:** MUST. Recognise, and make a **cautious** fermentation/maturation connection. Uses future S-1.
- The learner may say "this smells buttery." They must **not** conclude "this is diacetyl" or "the yeast failed" from butter alone.
- The safe direction (S-1): a butter / butterscotch descriptor; produced through normal yeast fermentation; healthy yeast can reduce it during
  maturation or contact; bacteria may also produce it; low levels can be accepted in some contexts; generally undesirable when unintentionally prominent.
- Process-side homebrew guidance stays qualitative: healthy yeast, enough maturation, and a sanitary process. **No fixed rest temperature or time**, no
  thresholds, no commercial enzyme treatment, and no claim that more time always fixes it.
- Reuse FACT-YEAST-0001 and FACT-BREW-0002 for the general yeast and temperature link. Do not restate them.
- The unsupported "slick / oily mouthfeel" sentence is **not** part of this governance (§6).

## 11. DMS governance

- **Level:** MUST. Descriptor via future S-4 (sweetcorn / cooked-vegetable family). **Process explanation MUST reuse FACT-BOIL-0002**; there is no second
  DMS process fact.
- Preserve the FACT-BOIL-0002 trap: **the precursor is not the volatile material; DMS itself is volatile.**
- Context: the perception can be part of some beers' character, and it is not, by itself, proof of a process problem. Other causes can give a similar
  perception.
- **Never teach** "cooked corn means the boil was too short", or any fixed boil time.

## 12. Oxidation governance

- **Level:** MUST. Descriptor via S-4 (cardboard / paper family; possibly sherry-like in an appropriate aged-beer context). **Process explanation MUST reuse
  FACT-OXY-0002** (and, for timing, FACT-OXY-0001 and FACT-OXY-0003).
- Limits of diagnosis by taste: a stale or cardboard impression may point to oxygen, to age, or to storage, and taste alone does not say which.
  Deeper time / warmth / shelf-life material is **Pakking / D58**, not here; **no new detailed staling fact.**
- **Never teach** "cardboard proves splashing during transfer."
- Oxidation character can present differently by beer, and is rarely intended.

## 13. Light-struck governance

- **Level:** SHOULD. Recognise, and give the simple cause. Uses future S-3. May be reused by Pakking later; **no duplicate process truth.**
- Descriptor: skunky family (via S-4).
- Cause, simply: light acting on hop-derived bitter compounds; brown or amber glass protects much better than clear or green glass.
- **No** wavelength teaching, thresholds or minute rules; **never** "brown glass makes beer immune."
- Light-struck is **rarely intentional** (§16).

## 14. Sourness / spoilage governance

- **Level:** MUST (recognise + limits). Uses future S-2.
- **Preferred learner-facing terms:** *unwanted microbial contamination* and *spoilage*. Avoid "infection" as the default word.
- Separate, in plain language: intended sourness (sour styles); acidity that is normal in a beer; unexpected sourness in a beer not meant to be sour;
  and unwanted microbial contamination.
- What the learner may responsibly infer from taste alone: that the beer is more sour than intended, and that microbial contamination is **one possible**
  explanation. Taste alone does not establish the cause.
- **Never teach** "sour = infected."
- **No health or safety claim in either direction.** The learner-facing text must not say spoiled beer is dangerous and must not say it is safe. The
  reconnaissance did not establish evidence for a health claim either way. The text **"if unsure, do not drink it"** is **not** to be added as a sourced
  teaching fact. FACT-COOL-0001 and FACT-COOL-0003 are quality/spoilage-organism facts and are not health claims either.
- Any precautionary wording, if ever wanted, is a separate owner decision and never a Course Fact.

## 15. Acetaldehyde / sulphur green-beer concept

One simple **green (immature) beer** concept covers three things that time with healthy yeast can change, taught qualitatively:

- **Diacetyl** (butter / butterscotch), via S-1.
- **Acetaldehyde** (green-apple family, via S-4), as a **SHOULD** inside this concept. **No standalone fact.** Do not teach "green apple definitely
  means it just needs more time": other causes exist.
- **Temporary / strain-dependent sulphur** (rotten-egg family) as a short note. **No standalone fact.** Some sulphur character can be normal in some
  fermentations and may fade. **Never** "sulphur = infection."

The maturation idea is shown qualitatively (a visual, §28), with no numbers. Kunze's green-beer / mature-beer grouping (p. 376) is structural
support only.

## 16. Fault vs intentional-character governance

Teach:

> **A descriptor is an observation. Whether it is a fault depends on what you intended, how strong it is, and the context.**

Do **not** over-relativise.

Can be intended or normal in some contexts (examples only): acidity in a sour beer; sulphur in some fermentations; phenolic character in some yeast
styles; low diacetyl in some contexts.

But:

- **light-struck is rarely intentional**;
- **cardboard / stale character is rarely intentional**;
- **unintended, prominent diacetyl is generally undesirable.**

Medicinal or chlorophenolic character is distinct from an intended phenolic character; that contrast may be mentioned once as an example, with no
fault-catalogue depth. Style is optional context only, and BJCP is a context source only (§18, §31). **No score.**

## 17. Observation vs interpretation governance

Wording ladder:

| Step | Example |
|---|---|
| OBSERVATION | "I smell butter." |
| INTERPRETATION | "This could be diacetyl." |
| HYPOTHESIS | "Maybe the yeast did not finish maturation." |
| DECISION | "Next time I will let fermentation/maturation finish and verify the process." |

Governance:

- an observation is **what was perceived**;
- an interpretation uses **"may", "could", "one possibility"**;
- **one observation never becomes a proven cause**;
- a hypothesis is **not asserted truth** (the schema already says `learning.hypothesis` is not asserted causal truth);
- **the App and the course never auto-generate a diagnosis**, and no AI-written causal conclusion is shown;
- **"I don't know yet" is valid.**

Reuse the G3N / Brew History methodology unchanged. Several causes can produce similar perceptions; that is professional interpretation and stays
methodology, not a per-fault registry claim.

## 18. Tasting habits

Four practical habits, all methodology:

1. a **clean, odour-free glass** and a neutral place;
2. **smell soon after pouring**;
3. use **consistent serving conditions** for comparisons;
4. a **side-by-side comparison** when useful (a reference beer or the last batch).

**No numeric serving-temperature recommendation** (no temperatures in any unit). Teach only that comparisons should use the same conditions. Water or a
plain cracker between samples may be included **only if a live source review supports it**. **No professional panel procedure**, no controlled booths,
no scoring scheme, no statistics. BJCP is context only: **no BJCP scoresheet, no competition scoring, no judging training** (§31).

## 19. Bias / blind-comparison note

Include **only as a short Kompetent SHOULD methodology note.**

Safe direction:

> Expectations can influence perception. Side-by-side comparison, or having another person pour samples without telling which is which, can reduce some
> expectation effects.

**Do not say blind tasting removes bias.** No statistics, no effect sizes, and no psychology training. The evidence basis is limited in scope
(§23), so the note is framed as a habit and not as a proven cure.

## 20. Brew History mapping

**No schema change.** No new fields, and no Core change. The module teaches how to use the existing fields well:

| Existing field | Role in this module |
|---|---|
| `sensing.notes` | LOOK / SMELL / TASTE / FEEL **observations**, kept as observations |
| `sensing.judgment` | yes / maybe / no; "maybe" already supports uncertainty |
| `sensing.flavorProfile` | **Existing heuristic only.** Not a measurement, not an objective sensory value, not a score, not diagnostic truth |
| `learning.whatWorked`, `learning.whatChanged` | **Interpretation** |
| `learning.hypothesis` | A possible explanation; **not causal truth** |
| `learning.nextTime` | The deliberate next change |
| `learning.nextRecipeOriginId` | Next-variant linkage |

**Important:** `sensing.flavorProfile` (numeric sliders on the recipe flavour-wheel axes) is existing product behaviour. The course **must not** teach its
numeric sliders as measurements, objective sensory values, scores or diagnostic truth. **Any future change to those sliders is a separate App/Core
issue** and is not part of #438.

Recorded, not decided: the schema has no separate aroma/appearance/mouthfeel fields, no confidence field and no structured fault descriptors; none is
proposed here.

## 21. Oppskriftsforståelse / intent mapping

| Step | Source in the product / other contracts |
|---|---|
| **INTENDED** | The recipe snapshot, the brewer's intent, and the predicted values (which #436 treats as estimates) |
| **OBSERVED** | Sensory notes (§8) plus measured actuals (#435) |
| **DIFFERENCE** | Described in words; **no grade** |
| **HYPOTHESIS** | One possible explanation, from the reused facts (fermentation, boil, oxygen, hop timing, and #436 R-2 / R-4 when they land) |
| **NEXT CHANGE** | One deliberate change (#436 one-change methodology: as few changes as practical; a hypothesis, not proof) |

Style is **optional context only** (#436 §12). The **predicted flavour wheel is not intended sensory truth**; it is an existing product heuristic and
must not be presented as what the beer "should" taste like. Wording about bitterness and balance follows #436 (IBU is one axis; balance is relative
perception; no directional claim about alcohol; no "harmonisk / veldig balansert" as scientific truth).

## 22. Source requirements

Every future record must be read live and recorded with tier, date, scope and access method. Reconnaissance directions (not citations):

| Need | Direction | Tier / note |
|---|---|---|
| S-1 diacetyl | A yeast-producer technical article (commercial interest); Oxford Companion entry; Kunze printed pp. 376–377 (visually verified); a peer-reviewed off-flavour review; a homebrewing text | A (commercial) / B / B / A / B |
| S-4 descriptors | Brewers Association off-flavour series (page summaries only in recon); the peer-reviewed off-flavour review; a homebrewing text; a certification-body article | B / A / B / secondary |
| S-2 sourness / spoilage | Brewers Association lactic acid summary; the peer-reviewed review; Kunze printed p. 763 (visually verified); a homebrewing text | B / A / B / B. **Quality scope only** |
| S-3 light-struck | Peer-reviewed photochemistry abstracts; the peer-reviewed review; a homebrewing text; a certification-body article | A / A / B / secondary |
| Methodology notes | G3N §1.7, #435, #436; Kunze printed p. 505 and p. 762 for structural remarks only | Not registry facts |
| Bias note | One peer-reviewed consumer-preference study (limited scope); Kunze p. 763 remark | A (narrow) / B |

Kunze notes (Tier B, structural support only, industrial): printed pp. 376–377 (diacetyl and maturation), p. 505 (oxygen and ageing carbonyls; "many
transformations also take place without oxygen"), p. 762 (tasting needs established rules; industrial scheme = LATER), p. 763 (microbiological
remarks, **quality scope not health**). Printed page = PDF page + 2 (chapter 4) or + 3 (chapter 7); OCR-only text is a pointer, never an exact-claim
source. Reading marks for the later round: direct read; fetch summary (spot-check needed); abstract only; visually verified Kunze page; search snippet
(not a source).

## 23. Source gaps

- No evidence basis for a **health or safety claim** about spoiled homebrew, in either direction.
- **ASBC/EBC Tier A sensory-method sources** were not accessible during reconnaissance.
- The **Brewers Association full fact sheets** were not opened (page summaries only).
- **Serving-temperature numbers** are inadequately supported; none is taught.
- **Deeper oxidation/staling causality** is limited (Kunze p. 505 notes oxygen is not the only route); detail stays with Pakking / D58.
- **Astringency** evidence is weak (one Tier B homebrewing source).
- **Individual sensitivity** differences are not adequately sourced.
- **Bias evidence** is limited in scope (one consumer study).
- **White Labs commercial-interest** caveat (yeast and enzyme vendor); the page is dated April 2021.
- The **Palmer web edition** needs a later live check and an edition, date and access record; its off-flavour chapter also contains over-strong causal
  lines that must not be copied.
- Several **Kunze pages are OCR-only or unopened** (aldehydes, DMS/mercaptan pages, the taste-and-foam section).
- **No thresholds or concentration numbers** enter teaching.

## 24. Wording traps

Never teach:

- "butter = diacetyl"; "cardboard = splashed transfer"; "cooked corn = boil too short";
- "sour = infected"; "green apple = definitely immature"; "sulphur = infection";
- "phenolic = always a fault"; "astringent = bitter";
- "one smell proves the cause"; "descriptor = diagnosis"; "every descriptor is neutral";
- a fixed diacetyl-rest schedule; a fixed DMS boil time; "brown glass makes beer immune";
- "spoiled beer is safe"; "spoiled beer is dangerous";
- "sensory slider = measurement"; "flavour score = quality score";
- "blind tasting removes bias"; "the App/AI diagnoses the fault";
- calling the DMS **precursor** volatile (FACT-BOIL-0002: the precursor is not the volatile material; DMS itself is volatile).

## 25. NO/EN terminology strategy

Norwegian is the source language; English mirrors meaning. **Prefer plain sensory language before technical compound names**, and let fault names be
recognised, not memorised.

| NO | EN | Note |
|---|---|---|
| se · lukt · smak · følelse (munnfølelse) · notér | LOOK · SMELL · TASTE · FEEL · NOTE | Framework words; align with the Web page's step names at the reconciliation gate |
| observasjon | observation | What was perceived |
| tolkning | interpretation | "kan", "muligens" |
| hypotese | hypothesis | Not asserted truth |
| beslutning / neste endring | decision / next change | One deliberate change |
| smør / butterscotch | butter / butterscotch | Plain descriptor before "diacetyl" |
| kokt mais / kokte grønnsaker | cooked corn / cooked vegetable | Descriptor before "DMS" |
| papp / gammel / «stale» | cardboard / stale | Descriptor before "oksidasjon" |
| grønt eple | green apple | Descriptor before "acetaldehyd" |
| skunk / lyspåvirket (lightstruck) | skunky / light-struck | Descriptor first |
| syrlig / sur | sour / acidic | Intended vs unexpected |
| uønsket mikrobiell forurensning / bedervelse | unwanted microbial contamination / spoilage | Preferred over "infeksjon" |
| umoden / «grønn» øl | green / immature beer | The green-beer concept |
| tørr / snerpende | dry / puckering | Plain description in FEEL; not bitterness |

Terms not to use in teaching: "feil" as a blanket verdict; "diagnose" as something the App does; "score" or "poeng" for sensory notes. No vocabulary
memorisation of compound names.

## 26. Mastery concept IDs

Mastery ids equal the registry concept ids carried by question `concepts[]` in `bryggeskole/data/pilot_*.json` (existing convention; no new mastery
system). Proposed ids: `sensory.tasting_sequence`, `sensory.observation_vs_interpretation`, `sensory.evaluate_against_intent`,
`sensory.fault_vs_character`, `sensory.diacetyl`, `sensory.dms_recognition`, `sensory.oxidation_recognition`, `sensory.sourness_intent_vs_spoilage`,
`sensory.lightstruck`, `sensory.green_beer`, `sensory.tasting_habits`, `sensory.expectation_note`, `sensory.typical_descriptors`.

Existing ids reused in questions: `boil.volatile_removal`, `oxygen.post_pitch`, `oxygen.pre_pitch`, `oxygen.timing_distinction`, `yeast.organism_role`,
`fermentation.temperature`, `fermentation.flavor`, `fermentation.yeast_strain`, `cool.speed`, `cool.sanitation_boundary`, `hop.aroma_volatility`,
`malt.colour_flavour`. Questions asserting a fact carry the id of a verified record; methodology questions carry the methodology concept id and make no
`FACT-*` claim.

## 27. Recommended module / chunk structure

Module 10, after Oppskriftsforståelse. About seven Kompetent chunks:

1. **Taste on purpose** — LOOK · SMELL · TASTE · FEEL · NOTE; practical habits; a short bias note.
2. **Describe, don't diagnose** — observation, interpretation, hypothesis, decision; "still uncertain".
3. **Green beer** — diacetyl, acetaldehyde, temporary sulphur; maturation, qualitatively.
4. **Cooked corn and cardboard** — DMS and oxidation, reusing the process facts.
5. **Light, sour and spoilage** — light-struck; intended versus unwanted sourness; no health claim.
6. **Fault or character?** — intent, intensity, context; phenol and ester examples only.
7. **Evaluate and choose one change** — intended versus observed; Brew History; one deliberate next change.

Chunks 1, 2, 6 and 7 are methodology and need **no new facts**. Chunk 4 needs only the S-4 descriptor. Each chunk: short text, one interaction, a few
questions, no wall of text.

## 28. Recommended visuals / interactions

Specified only; **none is implemented here.**

- A **LOOK · SMELL · TASTE · FEEL · NOTE guided card** that helps write `sensing.notes`. No sliders, no scores.
- **Sort the statements** into observation / interpretation / hypothesis / decision, with "not sure yet" as an allowed answer.
- **Same smell, several possible causes:** cards showing one perception with several possible explanations and no single right answer.
- A **qualitative green-beer maturation visual:** immature-beer character easing while beer stays with healthy yeast, with no numbers.
- **Intended versus observed**, side by side, from the recipe and the notes, without numbers or scores.
- A **simple blind-swap checklist** for the bias habit (another person pours; no statistics).

Avoid: aroma-wheel memorisation, threshold tables, scores, an automatic fault finder.

## 29. One representative acceptance scenario

A brewer opens the Brew History entry for a lager they made three weeks ago. They pour it in a clean glass and smell it soon after pouring. Using
the guided card they note in their own words that the colour is pale and clear and that there is a **buttery** smell. They write these under `sensing.notes` as observations only.

They compare with the recipe's intent (a clean pale lager) and describe the difference in words: "buttery, which I did not intend." They mark
`sensing.judgment` as "maybe".

In the interpretation step they write "this could be diacetyl", holding other possibilities open; they do not conclude a cause. The hypothesis is "maybe
the yeast did not finish maturation." They check whether they packaged early, and record that they are **still uncertain**, which counts as complete.

Their decision is "next time I will let fermentation and maturation finish and verify the process", stored in `learning.nextTime`. They compare the beer
side by side with a commercial lager, and, for the next tasting, ask a friend to pour without telling which is which.

Pass criteria: observation kept apart from interpretation; no cause asserted as proven; no score and no slider taught as a measurement; no health claim;
no number learned; one deliberate change chosen.

## 30. Smallest implementation slices

Each slice is a separate child issue after Chief review; none is part of #438.

1. **Docs contract (this document).** No registry, code or UI change.
2. **Fact pack S-1** (`sensory.diacetyl`), sources read live, Chief review.
3. **Fact pack S-4** (`sensory.typical_descriptors`), one consolidated record.
4. **Fact pack S-2** (`sensory.sourness_intent_vs_spoilage`), quality scope only.
5. **Fact pack S-3** (`sensory.lightstruck`), reusable by Pakking later.
6. **Module chunks 1, 2, 6 and 7** on methodology alone.
7. **Chunks 3 and 4** as S-1 and S-4 land (chunk 4 also reuses FACT-BOIL-0002 and FACT-OXY-0002).
8. **Chunk 5** after S-2 and S-3.
9. **Brew History guidance** only as copy that points at the existing fields; no schema change.

Do not build UI before this contract is reviewed.

## 31. Dependencies / later gates

- **#435 M2** (stable gravity) is helpful for the "is it finished?" idea; **#436 R-2 / R-4** for perceived bitterness and balance wording.
- **BJCP numbers in Learn text** remain gated by the licence/attribution question already recorded in #436. BJCP stays context only.
- **Palmer live check** and an edition, date and access record before any Palmer-sourced record.
- **Source spot-checks** for every fetch-summary or snippet item; **re-view Kunze pages** for exact quotes.
- **Commercial-interest marking** for any vendor source.
- **Future App/Core issue** (not #438): any change to the `sensing.flavorProfile` numeric sliders; any optional structured-tasting field.
- **Spoilage wording:** no health claim; any precautionary wording would be a separate owner decision and never a sourced fact.
- **Registry id assignment** for `FACT-SENSORY-000n` at implementation time.
- **Pakking / D58:** deeper staling, time, warmth and shelf life; light-struck may be reused there.
- **Web sensorikk reconciliation gate:** §32.

## 32. Existing Web sensorikk reconciliation gate

`web/hjelp/sensorikk.html` **remains for now**. It is treated as the **advanced / Bryggmester layer**. It is an **unsourced wording lead, not
provenance**, and it is **not edited or deleted in #438.**

Later reconciliation (a separate issue) must:

- **align terminology** with this module (step names, fault words, "spoilage / unwanted microbial contamination" wording);
- **separate Kompetent from advanced depth**, so the page does not repeat the Kompetent basics or widen the beginner fault set silently;
- **source-review unsupported claims** on the page before any is reused in Learn text;
- **not delete automatically.**

## 33. Hard non-goals

This contract and its later slices must **not** include:

- registry changes in #438, or any new verified fact in this PR;
- module code, UI, or visual implementation;
- Brew History, Core or schema changes; App, Web or Sóti changes;
- BJCP judging, a BJCP scoresheet, or competition scoring;
- numeric sensory scoring, or teaching `sensing.flavorProfile` sliders as measurements;
- flavour thresholds, ppm or ppb numbers, concentrations;
- numeric serving temperatures;
- a professional tasting-panel procedure, or triangle-test statistics;
- chromatography or lab analysis;
- automatic fault diagnosis, or AI causal conclusions;
- an off-flavour encyclopaedia, or an expanded beginner fault set;
- a new detailed staling fact;
- a health or safety claim about spoiled beer;
- deploy.

## Explicitly not done in this document

Course Fact Registry unchanged; no source opened or promoted in this run; no module, question, UI, bridge or visual implemented; no Brew History,
Core or schema change; no App, Web or Sóti change; no edit to `web/hjelp/sensorikk.html`; no gate in §31 decided beyond the Chief decisions listed in
§1; no deploy.
