# V2.2 — Måling og bryggelogg: M7 instrument-check source pack (proposal, not verified)

Version: 0.1 (2026-10-05, offline)

**Status refresh 2026-10-05:**
- Chief live source spot-check: **PASS**.
- Chief decisions:
  - hydrometer + refractometer only; thermometer excluded
  - classification `professional_interpretation`
  - Tier-B-only hydrometer support accepted
  - no universal "a hydrometer cannot be reset" claim
- `FACT-MEAS-0006` was then added to the registry as **verified**, with that narrower claim, on
  `offline/measurement-kompetent-implementation` (measurement contract §24).
- Its sources are AHA, BYO (Jon Stika), Craft Beer & Brewing, Hanna HI96841 and MISCO. BYO (Dave Green) is not cited.
- The §4 claim text and §10 object below are the pre-review proposal, kept for the record. The registry record is authoritative.

Original status (pre-review):
- **CANDIDATE / DRAFT — prepared for a Chief live source spot-check.** Nothing in this document is verified.
- **The Course Fact Registry is unchanged.** `bryggeskole/data/course_fact_registry.json` is byte-identical to the integration base, and
  `test_m5_and_m7_are_not_registry_records` stays valid.
- Recorded offline during the GitHub outage. Not on GitHub/master.

Governed by:
- measurement contract `v22_measurement_brewlog_module_contract.md`: §5 M7, §6 G4, §21.6, §23.2–§23.4
- Chief decision 2026-10-04 (§23.4): Measurement Kompetent is **not split**. It stays closed until `measurement.instrument_check` is
  verified.

Integration base: `6724833793bc6b8e45beeefc33661a1898b2ef09` (offline).

This is a docs-only source pack. It contains no product code, lesson JSON, UI or registry mutation, and does not implement Measurement
Kompetent.

## 0. How the sources were read

- Every source below was downloaded on **2026-10-05** as the original page HTML or PDF. Its full text was extracted locally (HTML tags or
  PDF text) and read.
- No search-result snippet is used as evidence.
- One earlier summarising fetch of the BYO (Dave Green) page was discarded, and the page was re-read from its raw HTML.
- The dates below come from the pages themselves: the byline, or the page's `datePublished`/`dateModified` metadata, or the manual's
  revision code.
- The Chief must still re-open each source live (§11). This pack is not a substitute for that check.

## 1. Proposed fact ID

**`FACT-MEAS-0006`**: a proposal only. It is the next free `FACT-MEAS` number (0001–0005 exist). It is not inserted into the registry.

## 2. Proposed concept

`measurement.instrument_check` (measurement contract §3, §11). No new concept id is proposed.

## 3. Proposed classification

**`professional_interpretation`**:
- The "check against water / offset" half is documented in several sources.
- The "passing the check does not prove every later reading is right" half is a synthesis. It draws on:
  - CB&B: the scale spacing can still be wrong after the water point.
  - MISCO: a list of other error causes.
  - Hanna: repeat the zero when conditions change.
- No single source states that half in those words.

Precedent: FACT-MASH-0004 and FACT-BREW-0003, where classification is kept separate from verification status.

Alternative for Chief: **`documented_fact`**, if the claim is cut to the first two sentences of §4. That cut is not recommended, because it
drops the "does not prove" boundary that §2 outcome 3 requires.

## 4. Proposed bounded claim (EN; candidate text)

> A brewing hydrometer or refractometer can be checked against a known reference before it is relied on. In distilled water, a hydrometer
> should read the value for pure water (1.000 specific gravity) when the water is at the reference temperature stated for that hydrometer.
> A refractometer is zeroed or checked with distilled (or deionised) water as its instructions describe. Such a check can reveal an offset.
> A hydrometer cannot be reset, so a consistent offset is noted and taken into account in later readings. Passing the water check does not
> prove that every later reading is correct: other error sources remain, for example a sample at another temperature, scale errors away from
> the water point, or, for a refractometer, alcohol in the sample.

**Scope: hydrometer + refractometer only. The thermometer is excluded** (§6.C, §8).

## 5. Proposed notes / wording traps (candidate `notes` text)

> Measurement-side M7 only (Kompetent / L2), limited to the hydrometer and refractometer. The thermometer is deliberately NOT covered: only
> one brewing-relevant Tier B source (BYO, Jon Stika) describes a thermometer check, and the only Tier A thermometer guidance found is
> food-safety scope (§6 G4). The check is a simple habit, not lab calibration.
>
> Deliberately NOT claimed:
> - any universal reference temperature (FACT-MEAS-0003 owns the instrument-stated reference temperature)
> - any temperature-correction formula or table
> - any refractometer alcohol-correction equation (FACT-MEAS-0004)
> - any two-point or slope-correction formula
> - any known-solution recipe (DME or sucrose amounts and their expected readings)
> - any universal tolerance or "acceptable offset" number
> - any accuracy hierarchy ("hydrometer is always more accurate", "refractometer is always better")
> - that a passed water check proves the instrument is accurate across its range
> - that the two instruments should always agree
> - that a hydrometer may be physically modified (filing glass, nail polish, tape)
> - that every hydrometer ships with correction documentation
> - any brand recommendation
> - any calibration interval
> - food-safety thermometer generalisation
>
> '1.000' is the reference value of pure water. It is not a tolerance and not a temperature.
>
> SOURCE LIMITATIONS:
> - No Tier A source was found for the hydrometer water check. The hydrometer half rests on three independent Tier B brewing sources
>   (AHA, BYO Green, CB&B) plus BYO Stika.
> - The refractometer half has Tier A support from two refractometer manufacturers, both commercial-interest: Hanna (a digital beer
>   refractometer manual) and MISCO (a technical note).
> - The "does not prove" half is a synthesis (classification `professional_interpretation`).
>
> SOURCE-ACCESS: sources read in full by Local Claude on 2026-10-05 from the original HTML or PDF. A Chief live spot-check is required
> before promotion.

## 6. Source table (full evidence review)

| # | Source | Author / org | URL | Date | Accessed | Tier | Instrument(s) | Commercial interest | Read in full |
|---|---|---|---|---|---|---|---|---|---|
| S1 | "How to Take an Accurate Hydrometer Reading" | American Homebrewers Association (no author byline shown; page cites Palmer, *How to Brew*, and Hausotter, *Zymurgy* Sep/Oct 2007) | https://homebrewersassociation.org/how-to-brew/how-to-take-an-accurate-hydrometer-reading/ | published 2014-05-13, modified 2023-02-02 (page metadata) | 2026-10-05 | B | hydrometer | No (trade association) | YES |
| S2 | "Hydrometers and Refractometers" | Dave Green, *Brew Your Own* | https://byo.com/article/hydrometers-and-refractometers/ (also served at `/articles/…`) | published 2023-12-08, modified 2025-07-09 (page metadata; no date in the byline) | 2026-10-05 | B | hydrometer, refractometer | No direct (magazine) | YES |
| S3 | "Calibrating Equipment" | Jon Stika, *Brew Your Own* | https://byo.com/articles/calibrating-equipment-techniques/ | published 2009-11-23, modified 2026-01-21 (page metadata) | 2026-10-05 | B | thermometer, hydrometer (also scales, vessels) | No direct (magazine) | YES |
| S4 | "Calibrating Your Hydrometer" | Jester Goldman, *Craft Beer & Brewing* | https://beerandbrewing.com/calibrating-your-hydrometer/ | 2016-12-02 (byline) | 2026-10-05 | B | hydrometer | No direct (magazine) | YES |
| S5 | HI96841 Digital Beer Refractometer, Instruction Manual (revision MAN96841 07/24) | Hanna Instruments Inc. | https://www.documentation.hannainst.com/manuals/preview/1834 (catalogue entry HI96841 / MAN96841_07_24, EN, version date 2024-07-06; the QR route is https://manuals.hannainst.com/HI96841) | 2024-07-06 (catalogue version date; "MAN96841 07/24" on the last page) | 2026-10-05 | A | refractometer (this digital model) | **YES**: instrument maker, product manual | YES |
| S6 | "How to Use a Refractometer to Brew Beer", REV140407-1 | MISCO | https://www.misco.com/wp-content/uploads/2012/11/MISCO-TB-BEER-1.pdf | revision code REV140407-1 (2014-04-07 implied by the code; no other date shown) | 2026-10-05 | A | refractometer (also hydrometer temperature context) | **YES**: refractometer maker; contains product claims and benchmark marketing | YES (7 pp.) |

**Per-source review**

**S1 AHA** (section "Hydrometer Correction and Calibration"):
- *Supports:*
  - hydrometers are calibrated for a liquid at a certain temperature, stated in the instrument's instructions
  - "You may also want to verify the calibration of your hydrometer, as it is not uncommon for them to be off"
  - the check is distilled water at the hydrometer's calibration temperature, against 1.000
- *Does not support:* any thermometer or refractometer check, or a known-solution second point.
- *Traps:*
  - "If the hydrometer reading is 1.000, your instrument is correctly calibrated" over-claims, and is not adopted.
  - "Use a file to shave off some of the glass … nail polish … tape" (physical modification) is excluded.
  - The temperature-correction pointer and the page's gravity ranges (1.030–1.070, up to 1.100) are excluded.
  - The page lists 59–60 °F / up to 70 °F as examples. These are not universal and are not adopted.

**S2 BYO, Dave Green** (intro paragraph; "Hydrometers" paragraph 2; "Calibration"):
- *Supports:*
  - "Distilled water should measure 1.000 specific gravity on both a hydrometer and refractometer"
  - "store-purchased distilled water will allow for calibration of both instruments"
  - "Refractometers generally have a knob to adjust the line to zero"
  - "Hydrometers cannot be reset to zero (1.000) but if you know that the scale is reading three points too high, then you can still use
    the hydrometer by making that 3-point correction to your readings"
  - "note the temperature calibration on the hydrometer you are using"
- *Does not support:* any thermometer check, or the claim that a passed check proves accuracy.
- *Traps:*
  - The DME known solution ("2 oz. (56 g) … should read at 1.040") and the author's starter ("100 g … reads 1.035") are excluded. They
    are personal practice with numbers, and are not independently sourced.
  - "60 °F (16 °C) or 68 °F (20 °C)" are examples, not universal.
  - "3-point" is an example offset, not a tolerance.
  - The ABV and CO₂ content is out of scope.
  - "We recommend purchasing from a reputable supplier" is excluded.

**S3 BYO, Jon Stika** ("Thermometers"; "Hydrometers"):
- *Supports:*
  - the hydrometer is checked in distilled water at its own standardised temperature (read from the instrument itself)
  - a reading away from 1.000 gives an adjustment factor for future readings
  - the sample temperature must still be measured and its adjustment applied in addition to the calibration adjustment, which supports
    "other error sources remain"
  - *Thermometer:* an ice/distilled-water equilibrium check of a brewing thermometer, with a dial-nut adjustment or a recorded offset. This
    is brewing-relevant, but it is the only such source (§6.C).
- *Does not support:* the refractometer.
- *Traps:*
  - "If your hydrometer reads precisely 1.000, you have an instrument that is spot-on and requires no adjustment factor" over-claims, and is
    not adopted.
  - "all hydrometers have accompanying documentation" over-generalises, and is not adopted.
  - The 4 °C density statement mixes density and specific gravity, and is not used.
  - The scale and vessel calibration (penny weight, graduated cylinder, mL/oz figures) is out of scope.
  - Retailer URLs in the text are not used.

**S4 Craft Beer & Brewing, Jester Goldman** ("Picking Known Points", "Taking Measure", "Reconciliation"):
- *Supports:*
  - "distilled water should read as 1.000 at the hydrometer's reference temperature"
  - the sample is kept at the reference temperature identified on the hydrometer
  - "If they're not the same, then your hydrometer readings will need to incorporate the difference"
  - "while the first measurement sets a base skew for the hydrometer, the markings themselves might be too close or too far apart", which
    is the key support for "passing the water check does not prove later readings are correct"
- *Does not support:* thermometer or refractometer checks (thermometers are mentioned only as an analogy).
- *Traps:*
  - The 15 °Plato sucrose solution, the 1.061 target, the correction formula and the worked example are excluded.
  - "Most brewers just assume … could be off by enough to affect the quality" is framing and is not adopted.
  - "I'd get a new one" is opinion.

**S5 Hanna HI96841 manual** (§2 General Description; §7 Calibration Procedure; §8 Measurement Procedures; §11 Error Messages):
- *Supports:*
  - "Samples are measured after a simple user calibration with deionized or distilled water"
  - the zero is set by filling the sample well with distilled or deionised water and pressing ZERO
  - "Verify the instrument has been calibrated before taking measurements"
  - "Calibration should be performed daily, before measurements are made, when the battery has been replaced, between a long series of
    measurements, or if environmental changes have occurred since the last calibration", which supports "the check is a habit, not a
    one-time proof"
  - the error messages for the "Wrong solution used to zero instrument" case
- *Does not support:*
  - hydrometers or thermometers
  - analog refractometers (this is one digital model; its procedure is product-specific)
  - alcohol correction (the manual is silent on it)
- *Traps:*
  - "eliminates the uncertainty associated with mechanical refractometers" and "years of experience" are marketing, not adopted.
  - The accuracy, range and ATC numbers (±0.2 °Plato, 10–40 °C and others) are excluded.
  - The sucrose standard-solution recipe (analytical balance) is lab practice and is excluded.
  - The product-specific button procedure must not be taught as universal.

**S6 MISCO REV140407-1** (p. 4: "How to use a Refractometer to Measure Beer", tip 1; "Problems with Beer Refractometer Readings", items
1–7):
- *Supports:*
  - "Follow the recommended procedure to calibrate your refractometer to distilled water"
  - "Using a refractometer that was not calibrated before use" is one cause of refractometer/hydrometer disagreement
  - the same list names other causes that a zero check does not remove: hydrometer sample temperature not measured or corrected; no or
    out-of-range temperature compensation; sucrose-based compensation on maltose wort; use after fermentation has started without a
    correction; poor instrument quality
- *Does not support:* any hydrometer water check, or thermometers.
- *Traps:*
  - The benchmark marketing (DMA5000, ±0.001) and "you get what you pay for" are excluded.
  - "Brix × 4" and the scale discussions are excluded.
  - The "50 to 86 °F" compensation range is excluded.
  - It is already a registry source for FACT-MEAS-0001…0004, a commercial-interest manufacturer.

**Examined and rejected (not evidence):**
- *MoreWine/MoreBeer "MT300 Hydrometer Instructions 2022" (PDF).* A retailer's private-label instruction sheet. It contains no water-check
  content, and it includes an ABV formula and a correction chart.
- *Retailer and blog pages from search results* (MoreBeer, Adventures in Homebrewing, Brew Cabin, Mr. Beer, and others). Retailer advice
  was not used, because stronger material exists.
- *WSU Extension "Calibrating a Thermometer" (from USDA).* Food-safety scope. Deliberately not used (§6 G4).
- *The Hanna HI96841 Brazilian-Portuguese manual* (BR_HI96841_11_20). The same content; it is superseded by the English S5.

### 6.A Hydrometer

- *Can it be checked against a known reference?* **Yes.** It is checked in distilled water at the reference temperature stated for that
  hydrometer, against 1.000 (S1, S2, S3, S4; Tier B ×4, three independent publishers).
- *What it establishes:* whether the instrument reads the pure-water value at its reference temperature. A difference there is an offset
  (a "base skew") that can be noted and applied to later readings (S2, S3, S4). Sources say hydrometers are "not uncommon" to be off (S1),
  and that they cannot be reset to zero (S2).
- *What it does not establish:*
  - That the scale is right elsewhere: the markings can be too close or too far apart (S4).
  - That later samples at other temperatures read correctly: sample temperature still has to be measured and handled (S1, S3, FACT-MEAS-0003).
  - That readings of finished beer are unaffected by alcohol or CO₂ (S2; outside this claim).
- *Tier A:* **none found.** This is a recorded gap (§8).

### 6.B Refractometer

- *Can it be zeroed or checked with a known reference?* **Yes.** It is zeroed or checked with distilled (or deionised) water following the
  instrument's own instructions (S5 Tier A, S6 Tier A, S2 Tier B).
- *What it establishes:* that the zero point is correct for the current conditions (S5: "Verify the instrument has been calibrated before
  taking measurements"; repeat it daily and after changes).
- *What it does not establish:*
  - Correct readings after alcohol is present (S6 item 6; FACT-MEAS-0004).
  - Correct temperature compensation, outside its range or for maltose versus sucrose (S6 items 2, 4, 5).
  - Agreement with a hydrometer (S6, list of causes).
  - That the zero holds forever (S5: repeat the calibration).

### 6.C Thermometer — EXCLUDED from the proposed claim

- *Brewing-relevant evidence:* only S3 (BYO, Jon Stika, Tier B): an ice/distilled-water check with adjustment or a recorded offset.
- *Why it is excluded:*
  - There is a single Tier B source.
  - No Tier A brewing source exists.
  - The only Tier A thermometer guidance found is food-safety (WSU/USDA; FSIS returned 403 earlier, §6 G4).
  - The brief says not to import food-safety guidance.
- *Chief option, not recommended now:* a later, separate thermometer extension if a second brewing-relevant source (preferably Tier A, for
  example a thermometer maker's manual for a brewing thermometer) is opened and read.

## 7. Support matrix (claim fragment → sources)

| # | Claim fragment | Supporting sources | Strength |
|---|---|---|---|
| F1 | A hydrometer can be checked against a known reference before it is relied on | S1, S2, S3, S4 | Tier B ×4 (3 publishers) |
| F2 | In distilled water a hydrometer should read the pure-water value (1.000) when the water is at that hydrometer's stated reference temperature | S1, S2, S3, S4; FACT-MEAS-0003 for "stated reference temperature" | Tier B ×4 + verified record |
| F3 | A refractometer is zeroed or checked with distilled (or deionised) water as its instructions describe | S5 (§2, §7, §8), S6 (p. 4 tip 1), S2 | Tier A ×2 (commercial) + Tier B |
| F4 | The check can reveal an offset | S1 ("not uncommon for them to be off"), S2 ("three points too high"), S3 (adjustment factor), S4 ("base skew"), S6 (uncalibrated = a cause of disagreement) | Tier B ×4 + Tier A |
| F5 | A hydrometer cannot be reset; a consistent offset is noted and taken into account | S2 ("cannot be reset … making that 3-point correction"), S3, S4 | Tier B ×3. (S1's filing or nail-polish modification is deliberately excluded) |
| F6 | Passing the water check does not prove every later reading is correct | S4 (markings may be too close or far apart), S3 (temperature adjustment *in addition to* the calibration factor), S5 (recalibrate daily or after changes), S6 (other causes, items 1–7) | Synthesis: `professional_interpretation` |
| F7 | Other error sources: sample temperature | S1, S3, S6 item 1; FACT-MEAS-0003 | Tier B + Tier A + verified record |
| F8 | Other error sources: scale errors away from the water point | S4 | Tier B ×1 (scoped as an example only) |
| F9 | Other error sources: alcohol in a refractometer sample | S6 item 6; FACT-MEAS-0004 | Tier A + verified record |

## 8. NON-CLAIMS (not justified by these sources, or deliberately excluded)

- Any thermometer check, including the ice-water method (§6.C).
- Any lab calibration procedure, analytical-balance standard, sucrose or DME known solution, or second-point / slope correction formula.
- Any universal reference temperature (60 °F, 68 °F, 20 °C and similar are examples only), temperature-correction table or formula.
- Any universal tolerance, "acceptable offset" number or calibration interval. Hanna's "daily" is one product's instruction.
- That a reading of 1.000 in water proves the hydrometer is accurate or "spot-on" (S1 and S3 over-claim this; S4 contradicts it).
- That hydrometer and refractometer readings should always agree.
- Any accuracy hierarchy, or "buy a better instrument" advice.
- Physically modifying a hydrometer (filing, nail polish, tape).
- That every hydrometer comes with correction documentation.
- That one product's button procedure applies to every refractometer.
- Refractometer alcohol correction maths (owned as a boundary by FACT-MEAS-0004).
- Any claim about scales, kettles or fermenter volume markings (S3 covers them; out of M7 scope).
- Any food-safety thermometer guidance.
- A Tier A hydrometer source. **None was found**, and the hydrometer half is Tier B only. This is recorded so it cannot be mistaken for
  Tier A support.

## 9. Suggested learner wording (Kompetent depth; candidate only, not lesson JSON)

**NO:**
> Før du stoler på et måleinstrument, kan du sjekke det mot noe du vet svaret på. Et hydrometer i destillert vann skal vise verdien for rent
> vann (1,000) når vannet har den referansetemperaturen som står oppgitt for akkurat ditt hydrometer. Et refraktometer nullstilles eller
> sjekkes med destillert vann slik bruksanvisningen sier. Viser hydrometeret noe annet i vannet, har du funnet et avvik. Et hydrometer kan
> ikke justeres, så du noterer avviket og tar hensyn til det i senere målinger. Men en bestått vannsjekk beviser ikke at alle senere målinger
> er riktige. Prøvens temperatur, feil lenger opp på skalaen og alkohol i prøven (for refraktometeret) kan fortsatt gi feil.

**EN:**
> Before you rely on a measuring instrument, you can check it against something whose answer you know. A hydrometer in distilled water should
> read the value for pure water (1.000) when the water is at the reference temperature stated for your hydrometer. A refractometer is zeroed
> or checked with distilled water as its instructions describe. If the hydrometer reads something else in the water, you have found an offset.
> A hydrometer cannot be adjusted, so you note the offset and take it into account in later readings. But passing the water check does not
> prove that every later reading is right. The sample's temperature, errors further up the scale and alcohol in the sample (for the
> refractometer) can still cause errors.

Wording traps (both languages):
- never "kalibrert = nøyaktig" / "calibrated = accurate"
- never a tolerance number
- never a reference-temperature number
- never "file the glass"
- never "check your thermometer in ice water"
- never "the hydrometer is more accurate"

## 10. Proposed registry object (TEXT ONLY — NOT APPLIED)

This object is **not** inserted into `bryggeskole/data/course_fact_registry.json`.
- It is shown with `status: "draft"` and **no `verified_at`**, matching the existing draft-record shape (FACT-MASH-0003).
- It must never be described as verified until the Chief spot-check passes and a separate registry round promotes it.
- That round must also change `test_m5_and_m7_are_not_registry_records` so it no longer forbids `measurement.instrument_check`, and add
  claim-boundary tests in the style of `test_instrument_choice_claim_boundaries`.

```json
{
  "id": "FACT-MEAS-0006",
  "claim": "A brewing hydrometer or refractometer can be checked against a known reference before it is relied on: in distilled water a hydrometer should read the value for pure water (1.000 specific gravity) when the water is at the reference temperature stated for that hydrometer, and a refractometer is zeroed or checked with distilled (or deionised) water as its instructions describe. Such a check can reveal an offset; a hydrometer cannot be reset, so a consistent offset is noted and taken into account in later readings. Passing the water check does not prove that every later reading is correct: other error sources remain, for example a sample at another temperature, scale errors away from the water point, or, for a refractometer, alcohol in the sample.",
  "classification": "professional_interpretation",
  "status": "draft",
  "sources": [
    {"tier": "A", "type": "instrument manufacturer instruction manual (Hanna Instruments) -- refractometer maker, commercial interest; digital beer refractometer, product-specific procedure", "ref": "Hanna Instruments, HI96841 Digital Beer Refractometer Instruction Manual, MAN96841 07/24 -- https://www.documentation.hannainst.com/manuals/preview/1834", "note": "Local Claude full read 2026-10-05 (PDF): sections 2, 7, 8, 11. Pending Chief live spot-check."},
    {"tier": "A", "type": "manufacturer technical note (MISCO) -- refractometer manufacturer, commercial interest", "ref": "MISCO, How to Use a Refractometer to Brew Beer, REV140407-1 -- https://www.misco.com/wp-content/uploads/2012/11/MISCO-TB-BEER-1.pdf", "note": "Local Claude full read 2026-10-05 (PDF): p. 4, calibrate to distilled water; causes of refractometer/hydrometer disagreement items 1-7. Pending Chief live spot-check."},
    {"tier": "B", "type": "trade association guide (American Homebrewers Association)", "ref": "AHA, How to Take an Accurate Hydrometer Reading -- https://homebrewersassociation.org/how-to-brew/how-to-take-an-accurate-hydrometer-reading/", "note": "Local Claude full read 2026-10-05: section 'Hydrometer Correction and Calibration'. Physical-modification advice excluded. Pending Chief live spot-check."},
    {"tier": "B", "type": "trade magazine article (Brew Your Own, Dave Green)", "ref": "BYO, Dave Green, Hydrometers and Refractometers -- https://byo.com/article/hydrometers-and-refractometers/", "note": "Local Claude full read 2026-10-05 (raw HTML): intro and 'Calibration'. Page metadata: published 2023-12-08, modified 2025-07-09. Known-solution numbers excluded. Pending Chief live spot-check."},
    {"tier": "B", "type": "trade magazine article (Brew Your Own, Jon Stika)", "ref": "BYO, Jon Stika, Calibrating Equipment -- https://byo.com/articles/calibrating-equipment-techniques/", "note": "Local Claude full read 2026-10-05: section 'Hydrometers' (the 'Thermometers' section is NOT used for this claim). Page metadata: published 2009-11-23, modified 2026-01-21. Pending Chief live spot-check."},
    {"tier": "B", "type": "trade magazine article (Craft Beer & Brewing, Jester Goldman)", "ref": "Craft Beer & Brewing, Jester Goldman, Calibrating Your Hydrometer (2016-12-02) -- https://beerandbrewing.com/calibrating-your-hydrometer/", "note": "Local Claude full read 2026-10-05: 'Picking Known Points', 'Taking Measure', 'Reconciliation'. Supports base skew vs scale spacing; formula and sucrose solution excluded. Pending Chief live spot-check."}
  ],
  "concepts": ["measurement.instrument_check"],
  "notes": "<§5 text>"
}
```

## 11. Chief live spot-check checklist

Open each source live and confirm the listed passages. Mark each one PASS, FAIL or NOT MATCHED.

1. **S5 Hanna HI96841 manual (MAN96841 07/24)**: https://www.documentation.hannainst.com/manuals/preview/1834
   - §2 "General Description": "user calibration with deionized or distilled water".
   - §7 "Calibration Procedure": the frequency sentence and steps 2–3 (fill with distilled/deionised water; press ZERO).
   - §8 "Measurement Procedures": the first line, "Verify the instrument has been calibrated before taking measurements".
   - §11 "Error Messages": "Wrong solution used to zero instrument".
   - Confirm the revision on the last page and the catalogue version date (2024-07-06).
2. **S6 MISCO REV140407-1**: https://www.misco.com/wp-content/uploads/2012/11/MISCO-TB-BEER-1.pdf
   - Page 4: "How to use a Refractometer to Measure Beer", tip 1.
   - Page 4: "Problems with Beer Refractometer Readings", items 1–7, especially item 3 ("not calibrated before use") and item 6 (after
     fermentation has started).
3. **S1 AHA**: https://homebrewersassociation.org/how-to-brew/how-to-take-an-accurate-hydrometer-reading/
   - Section "Hydrometer Correction and Calibration", the last paragraph ("not uncommon for them to be off"; distilled water at the
     calibration temperature).
   - Confirm that the filing/nail-polish advice is excluded.
4. **S2 BYO, Dave Green**: https://byo.com/article/hydrometers-and-refractometers/
   - The intro paragraph ("Distilled water should measure 1.000 … on both").
   - "Hydrometers" paragraph 2 ("note the temperature calibration").
   - "Calibration" paragraph 1 ("knob to adjust the line to zero"; "cannot be reset to zero … correction").
   - Confirm that the page shows no byline date, and check the published/modified dates if visible.
5. **S3 BYO, Jon Stika**: https://byo.com/articles/calibrating-equipment-techniques/
   - The "Hydrometers" section: the paragraph on the standardised temperature, the adjustment-factor paragraph, and the sentence about the
     temperature adjustment "in addition to any calibration adjustment factor".
6. **S4 Craft Beer & Brewing, Jester Goldman**: https://beerandbrewing.com/calibrating-your-hydrometer/
   - "Picking Known Points", sentence 2.
   - "Taking Measure", paragraphs 1–3, especially "the markings themselves might be too close or too far apart".
   - Confirm the 2016-12-02 byline.
7. **Decisions for Chief:**
   - (a) Hydrometer + refractometer only, with the thermometer excluded (§6.C)?
   - (b) Classification `professional_interpretation` vs `documented_fact` (§3)?
   - (c) Is the hydrometer half acceptable on Tier B only, with no Tier A found?
   - (d) Does the claim text in §4 stay inside the evidence?

Only after a Chief PASS may a registry round add a verified FACT-MEAS record. Only then does Measurement Kompetent become
implementation-ready (measurement contract §23.3–§23.4).
