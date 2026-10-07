# V2.2 — Gjæring Kompetent: G1/G2 source pack (proposal, not verified)

Version: 0.1 (2026-10-05, offline)

**Status refresh 2026-10-05:**
- Chief live source spot-check: **PASS** on G1 and G2.
- Chief decisions:
  - BREW numbering (`FACT-BREW-0004`, `FACT-BREW-0005`), no `FACT-FERM-*`;
  - both `documented_fact`;
  - the bounded claims of §1.2 and §2.2;
  - the teaching sentence "not everything can be fixed by waiting" / "ikke alt kan rettes opp ved å vente" is **dropped
    entirely**;
  - G2 names neither acetaldehyde nor sulphur.
- Both records were then added to the registry as **verified** on `offline/fermentation-kompetent-implementation`.
- The registry records are authoritative. The §1.6/§2.6 learner wording and the §1.7/§2.7 objects below are the pre-review proposal,
  kept for the record.

Original status (pre-review):
- **CANDIDATE / DRAFT — prepared for a Chief live source spot-check.** Nothing in this document is verified.
- **The Course Fact Registry is unchanged.** `bryggeskole/data/course_fact_registry.json` is byte-identical to the integration base.
- No product code, lesson JSON, mastery concept or UI is changed. Gjæring Kompetent is not implemented and stays **CLOSED**.
- Recorded offline during the GitHub outage. Not on GitHub/master.

Governed by:
- Gjæring Kompetent contract `v22_fermentation_kompetent_module_contract.md` §3 (topics A/B), §9 and §10 (fact pack G1 + G2).
- Chief decision 2026-10-05:
  - contract GREEN;
  - do not split the implementation;
  - keep the stage closed until G1 and G2 are verified;
  - narrow the G1/G2 wording to exactly what the sources support.

Integration base: `6f53e7597751e630da320e53a4bff6e4910e4ff5` (offline).

**Outcome: PASS.** G1 and G2 each have at least two independent, brewing-relevant sources, read in full. Each includes a Tier A yeast
producer (White Labs) and at least one independent Tier B brewing text. Several draft clauses were narrowed or moved into notes
(§1.5, §2.5).

## 0. How the sources were read

- Every source was downloaded on **2026-10-05** as the original page HTML. Its full text was extracted locally (HTML tags stripped)
  and read.
- No search-result snippet, AI summary or secondary summary is used as evidence. Web searches were used only to find candidate URLs.
- Dates come from the pages themselves: the byline, `datePublished`/`dateModified` metadata, or the printed copyright line.
- **SOURCE-ACCESS LIMITATION:** `howtobrew.com` served an **expired TLS certificate** on 2026-10-05. The page was fetched read-only
  with certificate checking switched off. The Chief should open it live in a browser and confirm the same text.
- **Independence:** Dr. Chris White is the founder of White Labs. His BYO article (S3) and his Oxford Companion entry "lag phase" (S4)
  are therefore **not independent of S1 (White Labs)**. They are treated as one source line.
  - The independent lines are White Labs (S1/S3/S4), John Palmer (S2) and the other Oxford Companion authors (S5–S8: Stewart, Hampson,
    Buttrick, Oliver).
- Commercial interest:
  - S1, S3 and S4 (White Labs and its founder) and S9 (Wyeast) are yeast sellers.
  - S2 is a book sold by its author.
  - S5–S8 are dictionary entries from a published reference book.

## Source list (shared by G1 and G2)

| # | Title | Author / organisation | URL | Date | Accessed | Tier | Commercial interest | Full original source read |
|---|---|---|---|---|---|---|---|---|
| S1 | Glossary — entries "Primary Fermentation", "Secondary Fermentation", "Flocculation", "Lagering/Conditioning" | White Labs | https://www.whitelabs.com/glossary | not shown (footer © 2026) | 2026-10-05 | A (yeast producer) | **YES** (yeast seller) | YES |
| S2 | How to Brew, Section 1, Chapter 8 — Fermentation | John Palmer | https://howtobrew.com/section-1/chapter-8 | © 1999–2015; contains an "Author's Note (2025)" | 2026-10-05 | B (brewing text) | **YES** (author sells the book) | YES |
| S3 | Fermentation Timeline | Dr. Chris White, Brew Your Own | https://byo.com/articles/fermentation-time-line/ | datePublished 2001-07-08, dateModified 2025-11-05 | 2026-10-05 | B | **YES** (author founded White Labs) | YES |
| S4 | lag phase (The Oxford Companion to Beer, via Craft Beer & Brewing) | Chris White; ed. Garrett Oliver; © Oxford University Press 2012 | https://www.beerandbrewing.com/dictionary/MkKGQWjuiT | 2012 | 2026-10-05 | B (reference work) | **YES** (author founded White Labs) | YES |
| S5 | maturation (Oxford Companion to Beer) | Graham G. Stewart; © OUP 2012 | https://www.beerandbrewing.com/dictionary/7JSOfuS2SQ | 2012 | 2026-10-05 | B | no | YES |
| S6 | green beer (Oxford Companion to Beer) | Tim Hampson; © OUP 2012 | https://www.beerandbrewing.com/dictionary/m7kpIIbx7I | 2012 | 2026-10-05 | B | no | YES |
| S7 | secondary fermentation (Oxford Companion to Beer) | Paul KA Buttrick; © OUP 2012 | https://www.beerandbrewing.com/dictionary/ARPMOtabKC | 2012 | 2026-10-05 | B | no | YES |
| S8 | conditioning (Oxford Companion to Beer) | Garrett Oliver; © OUP 2012 | https://www.beerandbrewing.com/dictionary/SPzTs0I06Q | 2012 | 2026-10-05 | B | no | YES |
| S9 | Activator instructions for homebrewing | Wyeast Laboratories | https://wyeastlab.com/activator-instructions-for-homebrewing/ | datePublished 2024-01-12, dateModified 2024-11-27 | 2026-10-05 | A (yeast producer) | **YES** (yeast seller) | YES |

Opened and read but **not cited**:
- OCB "aging of beer" (`/dictionary/wyphNb2YK8`) and "cask conditioning" (`/dictionary/dr3wlD9enF`): about long ageing and UK
  cask practice, outside this scope.
- OCB "zymurgy" (`/dictionary/otpTOQM7Op`): reached by a wrong search hit; irrelevant.

---

## 1. G1 — fermentation phases

### 1.1 Proposed fact ID, concept, classification

- **Proposed ID:** `FACT-BREW-0004`. This is a proposal only and is not inserted into the registry.
  - The fermentation records use the `FACT-BREW` prefix (0001–0003 exist).
  - If the Chief prefers a new prefix, the alternative is `FACT-FERM-0001`; `ID_PATTERN` allows it.
- **Concept:** `fermentation.phases` (Gjæring Kompetent contract §5).
- **Classification:** **`documented_fact`**.
  - Every clause in §1.2 is stated in at least two independent source lines.
  - The "sources divide it differently" clause is directly observable across S1, S2 and S3.

### 1.2 Bounded candidate claim (EN)

> After yeast is pitched, fermentation does not run at one steady rate. Brewing sources describe it in stages: an early period in which
> the yeast adapts to the wort before active fermentation gets going; a main, more active period in which most of the fermentable sugar
> is consumed; and a later, slower period in which fermentation continues at a reduced rate. The stages overlap rather than switching
> sharply, sources name and divide them differently, and how long and how vigorous each stage is depends on the yeast, the wort and the
> fermentation conditions.

How this differs from the contract §10 draft (narrowed to the evidence):
- **"with little change in gravity" is removed** from the early period. No source states gravity behaviour for the lag/adaptation
  period. S3 and S4 say only that little ethanol or flavour is produced, and both come from the same author line.
- **"gravity falls fastest" is removed.** Only S2 states that most of the gravity drop happens in the primary phase. "Most of the
  fermentable sugar is consumed" is stated by S1, S2 and S3. Gravity stays with FACT-MEAS-0001 and is not restated here.
- **"Overlap" and "sources name and divide them differently" are added.** S2 and S5 say the stages overlap. S1 (primary/secondary),
  S2 (adaptation/attenuative/maturation) and S3 (lag/exponential growth/stationary) use different divisions. The course therefore
  teaches no phase taxonomy.

### 1.3 Support matrix

| Claim fragment | Sources | Exact location |
|---|---|---|
| Fermentation does not run at one steady rate | S2, S3, S1 | S2 "Total fermentation is better defined as three phases…"; S3 the three phases; S1 Secondary Fermentation "occurs after primary fermentation when the rate of fermentation decreases" |
| Early period: yeast adapts to the wort before active fermentation | S2; S3/S4 (one line); S9 (lag time exists) | S2 "Lagtime or Adaptation Phase": "Immediately after pitching, the yeast start adjusting to the wort conditions…" and "work through the adaptation phase and begin primary fermentation"; S4 "the period between adding (pitching) yeast into wort and the beginning of fermentation … acclimate to its new environment"; S3 "Lag Phase … a process of acclimation"; S9 "shortens lag time" |
| Main, more active period; most fermentable sugar consumed | S1, S2, S3 | S1 Primary Fermentation: "the initial phase of fermentation where yeast growth happens and most of the wort sugars are consumed"; S2 "Primary or Attenuative Phase … a time of vigorous fermentation … The majority of the attenuation occurs during the primary phase"; S3 "Exponential Growth Phase … consume the sugars" |
| Later, slower period; fermentation continues at a reduced rate | S1, S2, S3 | S1 Secondary Fermentation "when the rate of fermentation decreases"; S2 "Secondary or Maturation Phase … slow reduction of the remaining fermentables"; S3 "Stationary Phase … yeast growth slows down" |
| Stages overlap | S2, S5 | S2 "The yeast do not end Primary before beginning Secondary, the processes occur in parallel"; S5 "there is significant overlap between the two" |
| Sources name and divide them differently | S1, S2, S3 | compare the three divisions above |
| Length/vigour depends on yeast, wort, conditions | S4 (S3 line), S2, S9 | S4 lag phase "depending on such factors as wort type and gravity, temperature, yeast strain, yeast health, pitching rate, and aeration"; S2 primary "depending on conditions"; S2 "depending on the yeast strain and the fermentation environment"; S9 lag time is shortened by activation |

### 1.4 Notes / wording traps (candidate `notes` text)

> Gjæring Kompetent G1 (contract §10). Teaches only that fermentation changes over time and that one moment does not describe the whole
> process. It is NOT a phase taxonomy: the sources divide and name the stages differently (White Labs primary/secondary; Palmer
> adaptation/attenuative/maturation; Chris White lag/exponential growth/stationary), so no stage name is taught as the correct one.
>
> Deliberately NOT claimed:
> - any duration or day count, although S2, S3 and S4 give hours and days;
> - gravity behaviour during the early period;
> - an exact rate curve;
> - airlock, krausen or foam as proof of a stage (S2 and S3 mention them descriptively; FACT-MEAS-0002 still governs completion);
> - lag time as a quality measure (S2 says a short lagtime "does not guarantee an exemplary fermentation");
> - oxygen, sterol or growth biochemistry (FACT-OXY-0001 owns oxygen);
> - pitch-rate numbers (FACT-YEAST-0004 owns pitching).
>
> Ownership:
> - FACT-MEAS-0001: gravity falls as sugar is fermented.
> - FACT-MEAS-0002: repeated stable readings = plausibly finished.
> - FACT-YEAST-0001: sugar → alcohol + CO2 + flavour.
> - FACT-BREW-0001: warmer = faster.
>
> Independence: S3 and S4 (Chris White) are not independent of White Labs (S1).

### 1.5 NON-CLAIMS (G1)

- No fixed durations or universal day counts. The hours/days in S2, S3 and S4 are deliberately not used.
- No visible krausen, foam or bubbles as proof of a phase. No "fermentation is complete because activity stopped".
- No exact gravity-rate curve. No "little gravity change in the early period".
- No lag time as a quality metric.
- No three-phase model presented as the one true taxonomy.
- No yeast growth biochemistry (budding, sterols, aerobic/anaerobic switch).
- Completion remains FACT-MEAS-0002 (repeated stable readings).

### 1.6 Suggested learner wording

**EN:**
> Fermentation does not run at one steady pace. Right after pitching there is a start-up period while the yeast adapts to the wort. Then
> comes the main, most active period, when most of the fermentable sugar is used up. After that, fermentation continues more slowly.
> These stages blend into each other, and brewing books name and divide them differently. How long each lasts depends on the yeast, the
> wort and the conditions. One look at the fermenter, or one moment in time, does not tell you where the whole fermentation is. To know
> whether it has finished, you still use repeated gravity readings.

**NO:**
> Gjæringen går ikke i ett jevnt tempo. Rett etter at gjæren er tilsatt, er det en oppstartsperiode mens gjæren tilpasser seg vørteren.
> Så kommer hoveddelen, den mest aktive perioden, der det meste av det gjærbare sukkeret brukes opp. Etterpå fortsetter gjæringen
> roligere. Disse delene glir over i hverandre, og bryggebøker navngir og deler dem inn ulikt. Hvor lenge hver del varer, avhenger av
> gjæren, vørteren og forholdene. Ett blikk på gjæringskaret, eller ett øyeblikk, forteller ikke hvor hele gjæringen står. Om den er
> ferdig, finner du fortsatt ut med gjentatte tetthetsmålinger.

### 1.7 Proposed registry object (TEXT ONLY — not inserted)

```json
{
  "id": "FACT-BREW-0004",
  "claim": "After yeast is pitched, fermentation does not run at one steady rate. Brewing sources describe it in stages: an early period in which the yeast adapts to the wort before active fermentation gets going; a main, more active period in which most of the fermentable sugar is consumed; and a later, slower period in which fermentation continues at a reduced rate. The stages overlap rather than switching sharply, sources name and divide them differently, and how long and how vigorous each stage is depends on the yeast, the wort and the fermentation conditions.",
  "classification": "documented_fact",
  "status": "draft",
  "sources": [
    {"tier": "A", "type": "manufacturer glossary (commercial interest: yeast seller)", "ref": "White Labs, Glossary (Primary Fermentation; Secondary Fermentation), https://www.whitelabs.com/glossary", "note": "Supports: primary = initial phase where yeast growth happens and most wort sugars are consumed; secondary = after primary when the rate of fermentation decreases. Does NOT support: an early lag/adaptation period, durations, overlap."},
    {"tier": "B", "type": "brewing text (commercial interest: author's book)", "ref": "John Palmer, How to Brew, Section 1, Chapter 8 - Fermentation, https://howtobrew.com/section-1/chapter-8", "note": "Supports: three overlapping phases (adaptation, attenuative/primary, maturation/secondary); majority of attenuation in primary; slower maturation; durations depend on conditions. Does NOT support (not used): its day counts and gravity fractions. Expired TLS certificate on 2026-10-05."},
    {"tier": "B", "type": "homebrew magazine article (author founded White Labs)", "ref": "Chris White, Fermentation Timeline, Brew Your Own, https://byo.com/articles/fermentation-time-line/", "note": "Supports: lag (acclimation), exponential growth (sugar consumption), stationary (growth slows). Not independent of White Labs. Does NOT support (not used): its hour/day ranges, oxygen ppm, temperature advice."},
    {"tier": "B", "type": "reference work (author founded White Labs)", "ref": "Chris White, 'lag phase', The Oxford Companion to Beer (ed. G. Oliver, OUP 2012), https://www.beerandbrewing.com/dictionary/MkKGQWjuiT", "note": "Supports: lag = period between pitching and the beginning of fermentation while yeast acclimates; length depends on wort, gravity, temperature, strain, yeast health, pitch rate, aeration. Not independent of White Labs."},
    {"tier": "B", "type": "reference work", "ref": "Graham G. Stewart, 'maturation', The Oxford Companion to Beer (OUP 2012), https://www.beerandbrewing.com/dictionary/7JSOfuS2SQ", "note": "Supports: significant overlap between fermentation and maturation."}
  ],
  "concepts": ["fermentation.phases"],
  "notes": "<§1.4 text>"
}
```

There is no `verified_at`, because the status is draft. The Wyeast source (S9) is listed in §1.3 as weak Tier A corroboration that a
lag time exists. It is optional in the record.

---

## 2. G2 — conditioning / maturation

### 2.1 Proposed fact ID, concept, classification

- **Proposed ID:** `FACT-BREW-0005`. This is a proposal only; the alternative is `FACT-FERM-0002`.
- **Concept:** `fermentation.conditioning`.
- **Classification:** **`documented_fact`** (recommended). Each kept clause is stated by White Labs (Tier A) and by at least one
  independent Tier B text.
- **Alternative: `professional_interpretation`**, if the Chief weighs the terminology problem more heavily:
  - "conditioning" is a catch-all term that also covers carbonation and refermentation in bottle or cask (S8, S7);
  - "maturation", "conditioning", "lagering", "aging" and (for homebrewers) "secondary" are used for overlapping things (S5, S7).
  - The claim avoids that problem by describing the *time after the most active fermentation*, not by defining the word.

### 2.2 Bounded candidate claim (EN)

> After the most active part of fermentation, beer is commonly given further time before it is packaged or served; brewers call this
> maturation or conditioning, and it overlaps with the end of fermentation. During this time yeast that is still active can reduce some
> of the by-products formed earlier in fermentation. Yeast and other suspended material also tend to settle, so the beer often becomes
> clearer, although how much depends on the yeast strain and some beers are meant to stay hazy. How long is needed depends on the beer,
> the yeast and the conditions; there is no single universal duration.

The four candidate ideas from the brief, verified separately:

| Idea | Kept? | Why |
|---|---|---|
| Further yeast activity / reduction of **some** by-products | **KEPT, as "some"** | S1, S2, S3, S5, S6 |
| Yeast and suspended material settle | **KEPT** | S1, S2, S3, S6 |
| Beer may become clearer | **KEPT as "often … depends on the yeast strain; some beers meant to stay hazy"** | S1 ("often resulting in a clear beer"; low-flocculation strains stay in suspension "creating haze"), S2, S3; S6 "unless it is of a type that is meant to be served hazy" |
| No universal duration | **KEPT** | S2, S5, S6 |

Moved from the claim into notes:
- **"Not every unwanted flavour can be removed by time."** Only S2 states it ("Once created, these flavors cannot be reduced by
  conditioning", for fusels and excess esters). One source is below the bar for a claim clause, so it is a teaching boundary in notes.
  The claim itself already says only "**some** of the by-products".
- **The by-product names** (diacetyl, acetaldehyde, hydrogen sulphide). The sources name them, but naming acetaldehyde or sulphur as
  maturation-reduced would cross the Smak boundary: sensory contract §30–§31 allows no acetaldehyde/sulphur maturation claim without
  a separately approved fact. That is a separate Chief decision, so G2 stays generic. Diacetyl remains with FACT-SENSORY-0001.

### 2.3 Support matrix

| Claim fragment | Sources | Exact location |
|---|---|---|
| Further time after the most active fermentation, before packaging/serving | S5, S6, S2, S1, S3 | S5 "includes all transformations between the end of primary fermentation and the removal of yeast … in preparation for packaging … the vast majority of beers are not yet ready to drink when the yeast finishes its primary work"; S6 green beer "has yet to undergo a period of conditioning before packaging"; S2 "Secondary or Maturation Phase"; S1 Lagering/Conditioning "a beer's maturation step"; S3 "Beer is matured in the stationary phase of growth, also known as the conditioning phase" |
| Called maturation or conditioning | S5, S8, S1, S3 | S5 "Maturation is also referred to variously as conditioning, lagering, and aging"; S8 conditioning "a catchall term"; S1 "Lagering/Conditioning"; S3 "conditioning phase" |
| Overlaps with the end of fermentation | S5, S2 | S5 "significant overlap between the two"; S2 "the processes occur in parallel" |
| Still-active yeast can reduce some by-products formed earlier | S2, S1, S5, S6, S3 | S2 "Once the easy food is gone, the yeast start re-processing some of these by-products"; S1 "allows yeast to clean up the beer"; S5 "reduced, either by the continuing action of the yeast or by other organic chemical pathways"; S6 "The yeast still has some work to do to remove some of the unwanted by-products"; S3 "Yeast reabsorb diacetyl" |
| Yeast and other suspended material tend to settle | S1, S2, S3, S6 | S1 Flocculation "falling out of suspension at the end of fermentation"; S1 Lagering/Conditioning "allowing solids to precipitate out of solution"; S1 Secondary "yeast can settle out of suspension"; S2 "the suspended yeast flocculates (settles out) … High molecular weight proteins also settle out"; S3 "yeast begin to settle out, or flocculate"; S6 "often cloudy with unsettled yeast" |
| Often clearer; depends on the strain; some beers meant to be hazy | S1, S2, S3, S6 | S1 "often resulting in a clear beer … a low flocculant strain will stay in suspension much longer creating haze"; S2 "the beer clears"; S3 "wait for the fermenter to 'clear'"; S6 "unless it is of a type that is meant to be served hazy" |
| How long depends on beer/yeast/conditions; no universal duration | S6, S5, S2 | S6 "may be as little as a few days for some British cask beers or as long as a few months for very traditional Czech pilsner"; S5 ales "can be quite short" vs "weeks of cold maturation" for lagers; S2 "a few days or weeks of maturation, depending on the yeast strain and the fermentation environment" |

### 2.4 Notes / wording traps (candidate `notes` text)

> Gjæring Kompetent G2 (contract §10). This is the general "why wait" concept. It describes the time after the most active fermentation,
> not a definition of the word "conditioning". Terminology overlaps (OCB: conditioning is a catch-all that also covers carbonation and
> refermentation in bottle or cask). The Norwegian course text uses "modning" as the main word, so it does not collide with Pakking's
> "flaskekondisjonering" (FACT-PACK-0001).
>
> Deliberately NOT claimed:
> - that yeast removes all off-flavours, or that more time always improves beer. S2 says fusel and excess-ester flavours "cannot be
>   reduced by conditioning", and warns that very long contact with a dormant yeast cake can create off-flavours;
> - any duration or day count, although S2, S5 and S6 give some;
> - mandatory cold conditioning, lagering schedules or temperatures;
> - finings or clarification depth (curriculum D28);
> - that every beer must become clear;
> - packaging after a fixed number of days;
> - named by-products. Diacetyl stays with FACT-SENSORY-0001. Acetaldehyde and sulphur maturation claims are outside this record
>   (sensory contract §30–§31).
>
> Ownership:
> - completion = FACT-MEAS-0002;
> - bottle conditioning/priming = FACT-PACK-0001;
> - oxygen = FACT-OXY-0002.

### 2.5 NON-CLAIMS (G2)

- No "yeast cleans up all off-flavours"; no "more time always improves beer".
- No universal conditioning duration; no packaging after an arbitrary number of days.
- No mandatory cold conditioning; no lagering schedules or temperatures.
- No clarification/finings depth.
- No "every beer must become bright/clear".
- No named by-product reduction: the diacetyl mechanism stays in FACT-SENSORY-0001, and there is no acetaldehyde/sulphur claim.
- No completion rule: stable gravity stays with FACT-MEAS-0002.
- No secondary-vessel advice. S2's 2025 note no longer recommends secondary fermenters, and this is out of scope anyway.

### 2.6 Suggested learner wording

**EN:**
> When the most active part of fermentation is over, the beer is usually given more time before you package or serve it. Brewers call
> this maturation or conditioning, and it blends into the end of fermentation. Yeast that is still active can reduce some of the
> by-products made earlier, though not everything can be fixed by waiting. Yeast and other particles also tend to settle, so the beer
> often becomes clearer. How much depends on the yeast, and some beers are meant to stay hazy. How long this takes depends on the beer,
> the yeast and the conditions. There is no single right number of days.

**NO:**
> Når den mest aktive delen av gjæringen er over, får ølet vanligvis mer tid før du pakker eller serverer det. Bryggere kaller dette
> modning (også kalt kondisjonering), og det glir over i slutten av gjæringen. Gjær som fortsatt er aktiv, kan redusere noen av
> biproduktene som ble laget tidligere, men ikke alt kan rettes opp ved å vente. Gjær og andre partikler synker også gjerne til bunns,
> så ølet blir ofte klarere. Hvor mye, avhenger av gjæren, og noen øl skal være uklare. Hvor lang tid dette tar, avhenger av ølet,
> gjæren og forholdene. Det finnes ikke ett riktig antall dager.

"Ikke alt kan rettes opp ved å vente" / "not everything can be fixed by waiting" carries the notes boundary. It is not a registry claim
clause. It may be used in teaching text only if the Chief accepts S2 as single-source support for a teaching boundary; otherwise the
sentence is dropped.

### 2.7 Proposed registry object (TEXT ONLY — not inserted)

```json
{
  "id": "FACT-BREW-0005",
  "claim": "After the most active part of fermentation, beer is commonly given further time before it is packaged or served; brewers call this maturation or conditioning, and it overlaps with the end of fermentation. During this time yeast that is still active can reduce some of the by-products formed earlier in fermentation. Yeast and other suspended material also tend to settle, so the beer often becomes clearer, although how much depends on the yeast strain and some beers are meant to stay hazy. How long is needed depends on the beer, the yeast and the conditions; there is no single universal duration.",
  "classification": "documented_fact",
  "status": "draft",
  "sources": [
    {"tier": "A", "type": "manufacturer glossary (commercial interest: yeast seller)", "ref": "White Labs, Glossary (Lagering/Conditioning; Secondary Fermentation; Flocculation), https://www.whitelabs.com/glossary", "note": "Supports: maturation step lets yeast clean up the beer and solids precipitate; after primary, flavour can mellow and yeast settle; flocculation often gives a clear beer, strain-dependent, low-flocculation strains leave haze. Does NOT support: durations, temperatures as a rule."},
    {"tier": "B", "type": "brewing text (commercial interest: author's book)", "ref": "John Palmer, How to Brew, Section 1, Chapter 8 - Fermentation, https://howtobrew.com/section-1/chapter-8", "note": "Supports: maturation overlaps primary; yeast re-process some by-products; yeast and proteins settle and the beer clears; days or weeks depending on strain and environment; some flavours cannot be reduced by conditioning (notes only). Not used: day counts, secondary-vessel advice, finings. Expired TLS certificate on 2026-10-05."},
    {"tier": "B", "type": "reference work", "ref": "Graham G. Stewart, 'maturation', The Oxford Companion to Beer (OUP 2012), https://www.beerandbrewing.com/dictionary/7JSOfuS2SQ", "note": "Supports: maturation between end of primary and packaging; also called conditioning/lagering/aging; overlap; undesirable compounds reduced by continuing yeast action or other pathways; ales short vs lagers weeks. Not used: industrial immobilised-yeast detail, temperatures, finings."},
    {"tier": "B", "type": "reference work", "ref": "Tim Hampson, 'green beer', The Oxford Companion to Beer (OUP 2012), https://www.beerandbrewing.com/dictionary/m7kpIIbx7I", "note": "Supports: a conditioning period before packaging; yeast removes some unwanted by-products; often cloudy with unsettled yeast unless meant to be hazy; a few days to a few months depending on the beer."},
    {"tier": "B", "type": "reference work", "ref": "Garrett Oliver, 'conditioning', The Oxford Companion to Beer (OUP 2012), https://www.beerandbrewing.com/dictionary/SPzTs0I06Q", "note": "Supports: conditioning is a post-fermentation catch-all for maturation and carbonation (terminology note only)."}
  ],
  "concepts": ["fermentation.conditioning"],
  "notes": "<§2.4 text>"
}
```

There is no `verified_at`. S3 (Chris White, BYO) and S7 (Buttrick) are corroborating and optional in the record.

---

## 3. Chief live spot-check list

| Source | Open | Check these sections / sentences |
|---|---|---|
| S1 | https://www.whitelabs.com/glossary | Entries **Primary Fermentation**, **Secondary Fermentation**, **Flocculation**, **Lagering/Conditioning** |
| S2 | https://howtobrew.com/section-1/chapter-8 (**expired certificate** on 2026-10-05; accept the browser warning or use another copy of the same edition) | Paragraph starting "Total fermentation is better defined as three phases"; sections **Lagtime or Adaptation Phase**, **Primary or Attenuative Phase**, **Secondary or Maturation Phase**; paragraph starting "Green apple flavors from acetaldehyde … cannot be reduced by conditioning"; **Maturation Processes**, paragraph starting "At the end of fermentation, the suspended yeast flocculates"; the "a few days or weeks of maturation, depending on the yeast strain" sentence |
| S3 | https://byo.com/articles/fermentation-time-line/ | Intro sentence "Ale fermentation … follows three phases"; **Stationary Phase** paragraph ("Beer is matured in the stationary phase … also known as the conditioning phase") |
| S4 | https://www.beerandbrewing.com/dictionary/MkKGQWjuiT | First paragraph (definition and the list of factors) |
| S5 | https://www.beerandbrewing.com/dictionary/7JSOfuS2SQ | First two paragraphs (definition; "significant overlap"; "reduced, either by the continuing action of the yeast"); fourth paragraph (ales short) |
| S6 | https://www.beerandbrewing.com/dictionary/m7kpIIbx7I | Paragraphs 1–3 (conditioning before packaging; "a few days … a few months"; "unless it is of a type that is meant to be served hazy") |
| S8 | https://www.beerandbrewing.com/dictionary/SPzTs0I06Q | The single definition paragraph (catch-all) |
| S9 (optional) | https://wyeastlab.com/activator-instructions-for-homebrewing/ | "shortens lag time" sentence |

## 4. Explicitly not done

Not done in this source pack:
- no registry mutation; nothing is marked verified; no `verified_at`;
- no CHUNK-FERM-E…K or Q-FERM-004…011; no `pilot_fermentation.py`, lesson JSON or mastery-concept change;
- no change to Foundation, Measurement, Recipe or Sensory;
- no stage UI, Web, #471 or issue-477 change;
- no GitHub contact.

Sync note: when GitHub access returns, mirror this on #419 / the #343 roadmap. No new issue number is assigned here.
