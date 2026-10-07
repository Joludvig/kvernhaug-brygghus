# V2.2 — Mesking Kompetent: M1/M2 source pack (proposal, not verified)

Version: 0.1 (2026-10-05, offline)

Status:
- **CANDIDATE / DRAFT — prepared for a Chief live source spot-check.** Nothing in this document is verified.
- **The Course Fact Registry is unchanged.** FACT-MASH-0003 is untouched.
- No Mesking product code, lesson JSON or mastery concept is changed. Mesking Kompetent stays **NOT IMPLEMENTATION READY** until M1/M2
  are verified.
- Recorded offline during the GitHub outage. Not on GitHub/master.

Governed by:
- Mesking Kompetent contract `v22_mashing_kompetent_module_contract.md` §4, §8, §9.
- Stage allocation contract §F.2:
  - D18 grain separation = MUST;
  - D19 wort collection travels with it;
  - milling, the conversion check, mash pH and efficiency are SHOULD and out of scope.

Integration base: `c1b95373f0d2be084bfad816680cf536d6ae383d` (offline).

**Outcome: PASS.** M1 and M2 each have at least two independent, brewing-relevant sources, read in full, plus producer manuals
(Tier A, commercial) for the system-specific clauses. Clauses were narrowed where evidence was method-specific (§1.2, §2.2).

## 0. How the sources were read

- Every source was downloaded on **2026-10-05** as the original page HTML or PDF. Its full text was extracted locally (HTML tags
  stripped, or `pdftotext -layout`) and read.
- Search results were used only to find URLs; no snippet or summary is evidence.
- **Non-Kunze throughout** (curriculum map §19.1 gap, printed pp. 257, 259–260).
- **SOURCE-ACCESS LIMITATION:** `howtobrew.com` served an **expired TLS certificate** on 2026-10-05, as in the G1/G2 pack. It was
  fetched read-only without certificate checking; the Chief should open it live.
- **Independence:**
  - Dave Carpenter wrote both CB&B pieces S5 and S6, so they are **one line**.
  - Palmer (S1), the OCB entry (Keith Thomas, S2), BYO (Joe Vella, S3) and CB&B (Libby Murphy, S4) are independent of each other.
  - The two system manuals (S7 Grainfather, S8 KegLand BrewZilla) are separate producers.
- **System manuals support only their own system's procedure** (lift basket/malt pipe, drain, sparge over it). They are not used
  for general claims.

## Source list (shared)

| # | Title | Author / organisation | URL | Date | Accessed | Tier | Commercial interest | Full original read |
|---|---|---|---|---|---|---|---|---|
| S1 | How to Brew, Section 3, Chapter 17 — Lautering (with ch. 18 *Extraction* and ch. 19 *Your First All-Grain Batch*, read for context) | John Palmer | https://howtobrew.com/section-3/chapter-17 (ch. 18: …/chapter-18; ch. 19: …/chapter-19) | © 1999–2015; site © 2025 (contains "Author's note, 2025") | 2026-10-05 | B (brewing text) | **YES** (author sells the book) | YES |
| S2 | sparging (The Oxford Companion to Beer, via Craft Beer & Brewing) | Keith Thomas; ed. Garrett Oliver; © OUP 2012 | https://beerandbrewing.com/dictionary/Yibra5GU76 | 2012 | 2026-10-05 | B (reference work) | no | YES |
| S3 | Lautering 101 | Joe Vella, Brew Your Own | https://byo.com/articles/lautering/ | published 2017-08-17, modified 2025-09-02 | 2026-10-05 | B | no (magazine) | YES |
| S4 | The Art and the Science of the Vorlauf Process | Libby Murphy, Craft Beer & Brewing | https://beerandbrewing.com/the-art-and-the-science-of-the-vorlauf-process/ | 2016-07-12 | 2026-10-05 | B | no (magazine) | YES |
| S5 | Lautering and Sparging | Dave Carpenter, Craft Beer & Brewing | https://www.beerandbrewing.com/lautering-and-sparging | 2016-02-09 | 2026-10-05 | B | no (magazine) | YES |
| S6 | Lautering & Sparging: Get the Wort Out (Illustrated Guide to Homebrewing, ch. 15) | Dave Carpenter, Craft Beer & Brewing | https://beerandbrewing.com/the-illustrated-guide-to-homebrewing-chapter-15-collecting-wort | 2023-09-02 | 2026-10-05 | B | no (magazine; same author as S5) | YES |
| S7 | Grainfather Connect (G30) Instructions | Grainfather | https://help.grainfather.com/hc/en-us/article_attachments/15548590179345 (PDF) | not shown | 2026-10-05 | A (system maker) | **YES** (equipment seller) | YES |
| S8 | 65L BrewZilla Gen 4 Instruction Manual | KegLand Distribution PTY LTD (PDF hosted by MoreBeer/MoreWine) | https://morewine.com/cdn/shop/files/BrewZilla-65L-Gen-4-US-Instructions-MB.pdf | "Last Updated 30/08/2022" | 2026-10-05 | A (system maker) | **YES** (equipment seller) | YES |

Opened and read but **not cited**:
- BYO "Lautering Techniques" (2003, modified 2025) and BYO "Easy Tips for Better Lautering" (2001, modified 2025): redundant with S3.
- The Grainfather G70 quick-start guide (help.grainfather.com attachment 15548215066897): assembly only.

---

## 1. M1 — grain separation

### 1.1 Proposed fact ID, concept, classification

- **Proposed ID:** `FACT-MASH-0005` (next free MASH number; 0003 is the untouched draft, 0004 exists). Proposal only; not
  inserted.
- **Concept:** `mashing.grain_separation`.
- **Classification:** `documented_fact`. Each kept clause is stated in at least two independent lines (§1.3).

### 1.2 Bounded candidate claim (EN)

> After the mash, the sweet wort is separated from the spent grain. How this is done depends on the equipment. In a mash/lauter tun,
> the wort drains out through a false bottom, manifold or similar, and the bed of grain itself acts as the filter. In an all-in-one
> system, the grain sits in a basket or malt pipe that is lifted and left to drain. In brew-in-a-bag, the bag holding the grain is
> lifted out. When draining through a grain bed in a lauter tun, the first runnings are often cloudy with bits of grain, and many
> brewers gently recirculate them over the grain bed (vorlauf) until the wort runs largely free of grain particles. It does not need
> to be perfectly clear.

General vs method-specific (as the brief requires):
- **General:** wort is separated from spent grain after the mash (S1, S2, S3, S5, S6).
- **Method-specific:**
  - the grain bed as the filter, and vorlauf → **lauter tun** (S1, S2, S3, S4, S6);
  - basket/malt pipe lift-and-drain → **all-in-one** (S7, S8; already verified as a layout in FACT-METHOD-0003);
  - bag lift → **BIAB** (S3 "fabric filter in the brewpot"; already verified in FACT-METHOD-0001).
- The claim does **not** say every method uses a grain-bed filter or a vorlauf step.

Narrowed from the contract §9 draft:
- **"commonly recirculate … until the wort runs clearer" → "many brewers … until largely free of grain particles; it does not
  need to be perfectly clear".**
  - S4 notes "solid arguments for and against" vorlauf and that crystal clear is "really not necessary".
  - S6 says that "it's likely that the wort will be rather cloudy, but it should be free of grain chunks".
- **Recirculation in all-in-one systems is not claimed as a clarity step.** S8 describes mash recirculation for an even temperature
  through the grain bed, which is a different purpose.

### 1.3 Support matrix

| Claim fragment | Sources | Exact location |
|---|---|---|
| Wort is separated from the spent grain after the mash | S1, S3, S5, S6, S2 | S1 "Lautering is the method of separating the sweet wort from the mash"; S3 "separates the liquid sweet wort … from the solid spent grain once the mash is complete"; S5 "separating sweet wort from the grain bed"; S6 "the physical separation of liquid from the solids"; S2 "the mash must be drained and separated from the residual solids" |
| Depends on equipment | S3, S5, S1 | S3 "a number of different methods … a mash-lauter tun … Brew-In-A-Bag (BIAB) which uses a fabric filter in the brewpot"; S5 "false bottom, screen, manifold, or braid"; S1 false bottom or manifold |
| Lauter tun: drains through a false bottom/manifold; the grain bed is the filter | S1, S2, S4, S6 | S1 "The grain bed forms its own filter … the grain bed is the filter, the false bottom or manifold underneath only serves to distribute the wort collection points"; S2 "filtered by these solids which are held on the mash or lauter plates"; S4 "A set grain bed also creates a filter"; S6 "filter through the husks and emerge as clear wort" |
| All-in-one: basket/malt pipe lifted and drained | S7, S8 | S7 "LIFT THE BASKET AND ROTATE … Allow the mash liquid to drain into the boiler"; S8 "Using the malt pipe handle lift the malt pipe out of the boiler and rotate 90 degrees" |
| BIAB: the bag is lifted out | S3 (+ FACT-METHOD-0001, verified) | S3 "Brew-In-A-Bag (BIAB) which uses a fabric filter in the brewpot" |
| First runnings cloudy with grain bits; recirculated over the bed (vorlauf) | S1, S3, S4, S6 | S1 "What is Recirculation? … The first few quarts are always cloudy with proteins and grain debris … poured back in on top of the grain bed. This is also known as the vorlauf step"; S3 "first few quarts … very cloudy … pour the wort back over the top of the grain bed … 'vorlauf'"; S4 "your wort is cloudy and has a few grains floating in it … pour the cloudy wort over the top"; S6 "carefully poured back on top of the grain bed" |
| "Many brewers"; largely free of grain particles, not perfectly clear | S4, S6, S1 | S4 "arguments for and against … Some brewers like to run their vorlauf until the wort is crystal clear, but that's really not necessary … the most important goal … is to clear the wort of grains"; S6 "rather cloudy, but it should be free of grain chunks"; S1 "still be dark and a little bit cloudy, but chunk free" |

### 1.4 NON-CLAIMS (M1)

- No run-off speed, valve opening, times or volumes. The sources' "2 quarts" and "10–20 minutes" are not used.
- No stuck-mash/stuck-sparge depth, no grain-bed depth, no rice hulls, no lauter-tun engineering.
- No bag-squeezing claim either way.
- No mashout, sparge chemistry, pH, tannin temperature rule or other temperature rule. The sources' 170 °F / 75–80 °C are not used.
- No claim that every method uses a grain-bed filter or a vorlauf step, and no claim that all-in-one recirculation clarifies.
- No method hierarchy (FACT-METHOD-0005 governs).
- No crush/milling (D16, SHOULD).

### 1.5 Suggested learner wording

**EN:**
> After the mash, the sweet wort has to be separated from the spent grain – how depends on your equipment. In a mash/lauter tun, the
> wort drains through a false bottom or manifold, and the grain bed itself does the filtering. Many brewers first collect the cloudy
> first runnings and gently pour them back over the grain bed until the wort runs largely free of grain bits; it does not have to be
> perfectly clear. In an all-in-one system, you lift the basket or malt pipe and let it drain. In BIAB, you lift the bag out. Same
> job, different hardware – none is the "proper" way.

**NO:**
> Etter meskingen må den søte vørteren skilles fra masken – hvordan avhenger av utstyret ditt. I en mesk-/silekar renner vørteren ut
> gjennom en falsk bunn eller et rørsystem, og selve kornsengen gjør filtreringen. Mange bryggere samler først opp den grumsete
> første vørteren og heller den forsiktig tilbake over kornsengen til vørteren renner stort sett uten kornbiter; den trenger ikke å
> være helt klar. I et alt-i-ett-anlegg løfter du kurven eller maltrøret og lar det renne av. Med BIAB løfter du posen ut. Samme
> jobb, ulikt utstyr – ingen av dem er «den riktige» måten.

### 1.6 Proposed registry object (TEXT ONLY — not inserted)

```json
{
  "id": "FACT-MASH-0005",
  "claim": "After the mash, the sweet wort is separated from the spent grain. How this is done depends on the equipment: in a mash/lauter tun the wort drains out through a false bottom, manifold or similar and the bed of grain itself acts as the filter; in an all-in-one system the grain sits in a basket or malt pipe that is lifted and left to drain; in brew-in-a-bag the bag holding the grain is lifted out. When draining through a grain bed in a lauter tun, the first runnings are often cloudy with bits of grain, and many brewers gently recirculate them over the grain bed (vorlauf) until the wort runs largely free of grain particles; it does not need to be perfectly clear.",
  "classification": "documented_fact",
  "status": "draft",
  "sources": [
    {"tier": "B", "type": "homebrewing text (commercial interest: author's book)", "ref": "John Palmer, How to Brew, Section 3, Chapter 17 - Lautering -- https://howtobrew.com/section-3/chapter-17", "note": "Supports: lautering separates sweet wort from the mash; the grain bed is the filter, the false bottom/manifold only collects; recirculation (vorlauf) of the cloudy first quarts until chunk free. Does not support (not used): quantities, times, temperatures, crush/mashout/stuck-sparge depth. Expired TLS certificate on 2026-10-05."},
    {"tier": "B", "type": "reference work", "ref": "Keith Thomas, 'sparging', The Oxford Companion to Beer (OUP 2012) -- https://beerandbrewing.com/dictionary/Yibra5GU76", "note": "Supports: the mash is drained and separated from the residual solids, which filter the wort. Does not support (not used): pH/tannin, flow-rate matching."},
    {"tier": "B", "type": "homebrew magazine article", "ref": "Joe Vella, Lautering 101, Brew Your Own (2017, modified 2025) -- https://byo.com/articles/lautering/", "note": "Supports: separation of sweet wort from spent grain; equipment varies (mash-lauter tun with false bottom/manifold/braid; BIAB fabric filter); first runnings very cloudy, recirculated over the grain bed (vorlauf) until clear. Does not support (not used): temperatures, times, ratios."},
    {"tier": "B", "type": "magazine article", "ref": "Libby Murphy, The Art and the Science of the Vorlauf Process, Craft Beer & Brewing (2016-07-12) -- https://beerandbrewing.com/the-art-and-the-science-of-the-vorlauf-process/", "note": "Supports: a set grain bed creates a filter; cloudy first runnings poured back over the bed; arguments for and against; crystal clear not necessary, the goal is to clear the wort of grains. Does not support (not used): finings, cold crash, tannin temperature."},
    {"tier": "A", "type": "system manual (commercial interest: equipment seller) -- all-in-one only", "ref": "Grainfather Connect (G30) Instructions -- https://help.grainfather.com/hc/en-us/article_attachments/15548590179345", "note": "Supports (all-in-one only): lift the basket, rotate onto the support ring and let the mash liquid drain into the boiler. Does not support: any general claim."},
    {"tier": "A", "type": "system manual (commercial interest: equipment seller) -- all-in-one only", "ref": "KegLand, 65L BrewZilla Gen 4 Instruction Manual (last updated 30/08/2022) -- https://morewine.com/cdn/shop/files/BrewZilla-65L-Gen-4-US-Instructions-MB.pdf", "note": "Supports (all-in-one only): lift the malt pipe out of the boiler and suspend it to drain. Its mash recirculation is for even temperature, NOT a clarity step (not used as such)."}
  ],
  "concepts": ["mashing.grain_separation"],
  "notes": "<§1.4 non-claims + ownership: FACT-METHOD-0001..0005 own the method layouts and no-hierarchy; source-access limitation (howtobrew expired TLS); Chief spot-check line to be added at verification>"
}
```

There is no `verified_at`.

---

## 2. M2 — wort collection

### 2.1 Proposed fact ID, concept, classification

- **Proposed ID:** `FACT-MASH-0006`. Proposal only.
- **Concept:** `mashing.wort_collection`.
- **Classification:** `documented_fact`.

### 2.2 Bounded candidate claim (EN)

> After the mash has drained, sugar-rich wort is still held in the wet grain. Sparging – rinsing the grain with more hot water,
> continuously or in one or more batches – recovers more of that sugar. In a no-sparge approach, the full water volume goes into
> the mash and only the first runnings are collected; this is simpler, but more sugar is left behind. When wort is collected in
> stages, later runnings are weaker than the first. How much wort and sugar a brewer collects therefore depends on the method and on
> their own system.

The brief's clauses, checked separately:

| Clause | Kept? | Why |
|---|---|---|
| Grain retains wort/sugar after draining | **KEPT** | S2, S1, S8, S6 |
| Sparging recovers additional sugar | **KEPT** | S1, S2, S3, S5, S6, S7, S8 |
| Full-volume / no-sparge collects differently | **KEPT** | S1 and S5/S6 (two independent lines: Palmer and Carpenter) |
| Later runnings weaker | **KEPT** | S1 (parti-gyle: first runnings about twice the gravity of the second), S2 (parti-gyle: beers of different strengths from one mash), S6 (first, second and third runnings → barleywine, pale ale, ordinary bitter). S8 (sparge until the runnings reach a low gravity) is corroborating |
| Collection is part of planning one's own system | **KEPT, generic** | S5 "keeping good notes so that you understand how your system behaves"; S1 ch. 18 "your extract efficiency is dependent on your methods and equipment". The planning numbers stay with FACT-METHOD-0004 |

Not claimed:
- the "grain absorbs a set amount of water" number (S1 calculations; the S7 sparge-water formula);
- efficiency percentages or points-per-pound (Bryggemester).

### 2.3 Support matrix

| Claim fragment | Sources | Exact location |
|---|---|---|
| Sugar-rich wort remains held in the wet grain | S2, S1, S8, S6 | S2 "much will remain on the surface and crevices of the husks … Removing this residue requires rinsing"; S1 (no-sparge) "quite a bit of wort is left behind"; S8 "rinse the grain of the majority of the remaining sugars"; S6 "rinsing the solids that remain … to leave behind as little sugar as possible" |
| Sparging = rinsing with more hot water, continuous or batch, recovers more sugar | S1, S2, S3, S5, S6, S7, S8 | S1 "Sparging is the rinsing of the grain bed to extract as much of the sugars …", "Continuous Sparging", "Batch Sparging"; S2 "spraying of fresh hot liquor … to rinse out residual sugars"; S3 batch and fly sparging; S5 "Fly-sparge … Batch-sparge"; S6 "Three methods are popular"; S7 "Gently pour the sparge water evenly over the grain"; S8 "Sparging involves rinsing the grain bed with warm water to extract as much sugar as possible" |
| No-sparge: full volume in the mash, first runnings only, simpler but more sugar left behind | S1, S5, S6 | S1 "No-Sparge … least efficient … the beer is produced entirely from first runnings", "quite a bit of wort is left behind"; S5 "The mash is conducted with the full volume of water … reduced efficiency"; S6 "grain is mashed using the entire batch's volume of water … at the cost of efficiency" |
| Later runnings weaker than the first | S1, S2, S6 (S8) | S1 Parti-Gyle "The first runnings is typically … twice the gravity of the second runnings"; S2 "a number of beers of different strengths could be produced from a single mash"; S6 "The first runnings might become a barleywine, the second runnings a pale ale, and the third runnings an ordinary bitter"; S8 "keep sparging … until the wort falling from the underside of the malt pipe reaches" a low gravity |
| Depends on method and own system | S5, S1 | S5 "doing what works best for you and your equipment … keeping good notes so that you understand how your system behaves"; S1 ch. 18 "your extract efficiency is dependent on your methods and equipment" |

### 2.4 NON-CLAIMS (M2)

- No efficiency, yield or points-per-pound numbers or maths (D66 SHOULD, calculation Bryggemester).
- No sparge-water volume formula, absorption factor, gravity cut-off or temperatures. The sources' 1.008/1.010, 170 °F and
  75–80 °C are not used.
- No fly-vs-batch "better" ranking, and no claim that no-sparge makes better or worse beer. Palmer's "smoother, richer tasting"
  is not used.
- No parti-gyle teaching. It is used only as evidence that runnings get weaker.
- No tannin/pH chemistry. No conversion check. No milling.
- No App field mapping. Pre-boil measurement truth stays with FACT-MEAS-0001/0005.

### 2.5 Suggested learner wording

**EN:**
> When the mash has drained, the wet grain still holds sugar-rich wort. Rinsing the grain with more hot water – sparging, done
> continuously or in one or more batches – recovers more of it. Some brewers skip sparging and put all the water into the mash
> instead (no-sparge); that is simpler, but more sugar stays behind in the grain. If you collect the wort in stages, the later
> runnings are weaker than the first. So how much wort and sugar you end up with depends on your method and your own system – note
> it, and plan with your own numbers.

**NO:**
> Når mesken har rent av, holder den våte masken fortsatt på sukkerrik vørter. Skyller du masken med mer varmt vann – skylling
> (sparging), enten kontinuerlig eller i én eller flere omganger – får du ut mer av den. Noen bryggere hopper over skyllingen og
> bruker i stedet alt vannet i meskingen (uten skylling); det er enklere, men mer sukker blir igjen i masken. Samler du vørteren i
> flere omganger, er de senere avrenningene svakere enn den første. Hvor mye vørter og sukker du ender med, avhenger derfor av metoden
> og ditt eget anlegg – noter det, og planlegg med dine egne tall.

### 2.6 Proposed registry object (TEXT ONLY — not inserted)

```json
{
  "id": "FACT-MASH-0006",
  "claim": "After the mash has drained, sugar-rich wort is still held in the wet grain. Sparging - rinsing the grain with more hot water, continuously or in one or more batches - recovers more of that sugar. In a no-sparge approach the full water volume goes into the mash and only the first runnings are collected, which is simpler but leaves more sugar behind. When wort is collected in stages, later runnings are weaker than the first. How much wort and sugar a brewer collects therefore depends on the method and on their own system.",
  "classification": "documented_fact",
  "status": "draft",
  "sources": [
    {"tier": "B", "type": "homebrewing text (commercial interest: author's book)", "ref": "John Palmer, How to Brew, Section 3, Chapter 17 - Lautering (ch. 18 Extraction for the equipment-dependence sentence) -- https://howtobrew.com/section-3/chapter-17", "note": "Supports: sparging rinses residual sugar; continuous and batch sparging; no-sparge uses first runnings only and leaves quite a bit of wort behind; parti-gyle first runnings about twice the gravity of the second; efficiency depends on methods and equipment. Does not support (not used): volumes, gravity cut-offs, efficiency numbers, temperatures, 'richer tasting'. Expired TLS certificate on 2026-10-05."},
    {"tier": "B", "type": "reference work", "ref": "Keith Thomas, 'sparging', The Oxford Companion to Beer (OUP 2012) -- https://beerandbrewing.com/dictionary/Yibra5GU76", "note": "Supports: much sugar remains on the husks; rinsing with fresh hot liquor removes it; parti-gyle produced beers of different strengths from one mash. Does not support (not used): pH/tannin, flow matching."},
    {"tier": "B", "type": "magazine article", "ref": "Dave Carpenter, Lautering and Sparging, Craft Beer & Brewing (2016-02-09) -- https://www.beerandbrewing.com/lautering-and-sparging", "note": "Supports: fly, batch and no-sparge; no-sparge mashes with the full water volume at reduced efficiency; choose what works for your equipment and keep notes on how your system behaves. Same author as the CB&B Illustrated Guide ch. 15 (corroborating, not independent)."},
    {"tier": "B", "type": "homebrew magazine article", "ref": "Joe Vella, Lautering 101, Brew Your Own (2017, modified 2025) -- https://byo.com/articles/lautering/", "note": "Supports: sparging rinses residual sugars from the grain bed; batch and fly sparging. Does not support (not used): temperatures, times."},
    {"tier": "A", "type": "system manual (commercial interest: equipment seller) -- all-in-one only", "ref": "KegLand, 65L BrewZilla Gen 4 Instruction Manual (last updated 30/08/2022) -- https://morewine.com/cdn/shop/files/BrewZilla-65L-Gen-4-US-Instructions-MB.pdf", "note": "Supports (own system): sparging rinses the grain of the majority of the remaining sugars; sparge until the runnings fall to a low gravity. Not used: water volumes, temperatures, the 1.010 figure."}
  ],
  "concepts": ["mashing.wort_collection"],
  "notes": "<§2.4 non-claims + ownership: FACT-METHOD-0004 owns equipment planning numbers, FACT-MEAS-0001/0005 own pre-boil measurement; source-access limitation; Chief spot-check line to be added at verification>"
}
```

There is no `verified_at`.

---

## 3. Chief live spot-check list

| Source | Open | Check |
|---|---|---|
| S1 | https://howtobrew.com/section-3/chapter-17 (**expired certificate**) | Paragraph "The insoluble grain husks … the grain bed is the filter"; **What is Recirculation?**; **What is Sparging?**; **Parti-Gyle** (last sentence: first runnings about twice the gravity of the second); **Batch Sparging**; **No-Sparge**; **Rinsing vs. Draining** ("quite a bit of wort is left behind") |
| S1 ch. 18 | https://howtobrew.com/section-3/chapter-18 | Sentence "your extract efficiency is dependent on your methods and equipment" |
| S2 | https://beerandbrewing.com/dictionary/Yibra5GU76 | Paragraphs 1–3 (filtered by the solids; much remains on the husks; rinsing; parti-gyle beers of different strengths) |
| S3 | https://byo.com/articles/lautering/ | Paragraphs 1–2 (separation; equipment incl. BIAB fabric filter); "The Steps" recirculation paragraph; sparging paragraph |
| S4 | https://beerandbrewing.com/the-art-and-the-science-of-the-vorlauf-process/ | "Why to do it" (set grain bed creates a filter); "How to do it" (cloudy first runnings poured back; crystal clear not necessary; arguments for and against in the intro) |
| S5 | https://www.beerandbrewing.com/lautering-and-sparging | "Lauter"; "No-sparge brewing"; last paragraph (keep notes on how your system behaves) |
| S6 | https://beerandbrewing.com/the-illustrated-guide-to-homebrewing-chapter-15-collecting-wort | "Lautering" and "Vorlauf" paragraphs ("rather cloudy, but … free of grain chunks"); "Sparging" (no-sparge, full volume); "Batch Sparge" (first/second/third runnings) |
| S7 | Grainfather PDF (link above) | Section **SPARGING**: "LIFT THE BASKET AND ROTATE" and "SPARGE" panels |
| S8 | BrewZilla Gen 4 PDF (link above) | pp. 19–21 "Sparging" (lift the malt pipe; rinse the grain of the majority of the remaining sugars); the recirculation paragraph (even temperature, not clarity) |

## 4. Explicitly not done

Not done in this source pack:
- no registry mutation; nothing is marked verified; no `verified_at`; FACT-MASH-0003 untouched;
- no CHUNK-MASH-D…F or Q-MASH-004…008; no pilot_mashing.py, lesson JSON or mastery change;
- no milling, mash pH or efficiency work;
- no stage UI, Web, #471 or issue-477 change;
- no GitHub contact.

Sync note: mirror on #419 / the #343 roadmap when GitHub returns. No issue number is assigned.
