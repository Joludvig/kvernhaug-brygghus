# Varðeldr — M42 vs M15 split-batch reconstruction

Reconstruction status: **review required**

Date: **2026-07-05** (test batch)

## Identity / origin
The brewer has directly clarified that **Varðeldr developed out of Skumring**.

This was a **recipe development**, not the same beer carried forward unchanged: the recipe was altered and the ingredients were **not the same** as Skumring. The concrete Varðeldr test brew was then made as a **small batch split between two yeast types**, M42 and M15.

Preserve the distinction:
- lineage / development: **Skumring → Varðeldr**;
- recipe identity: changed ingredients, therefore not the same recipe;
- experiment: one Varðeldr wort split into M42 and M15 arms.

## Development intent
Before the July split batch, user-authored chat records the intended Varðeldr direction as a **smoked imperial stout**: more complex flavor, somewhat higher strength than the earlier dark beer, and a simpler ingredient list carrying fuller flavors. An early target discussed for the first Varðeldr version was around **9% ABV**. These are design decisions/intent, not measured batch outcomes.

## Experiment design
- Brewed **2026-07-05** as roughly **8 L total**, split into two small fermenters at under 4 L each.
- Same wort in both arms.
- User-authored chat states oxygenation, **Fermaid K**, wort and fermentation temperature were held the same; **yeast was the intended experimental variable**.
- Yeast arms:
  - Mangrove Jack's **M42**
  - Mangrove Jack's **M15**

## Instrument measurements
- OG measured from the circulation-pump sample: approximately **1.100 @ 20 °C**.
- M42 FG measured: **1.022**.
- M15 FG measured: **1.037–1.038**.
- The hydrometer later read about **0.998 in water**; using that observed offset, the brewer/analysis context treated the corrected estimates as roughly:
  - M42: about **1.024**, around **10% ABV**
  - M15: about **1.039–1.040**, around **7.9–8.0% ABV**

The measured values and the correction estimates are kept separate; the correction is not silently substituted for the original readings.

## Process observations
- Both arms showed fermentation after roughly **3 hours**.
- Fermentation temperature was around **17 °C**.
- After about one day, **M15 appeared the most active/lively**.
- By **2026-07-16**, M15 was described as less vigorous and as having stopped earlier than M42.
- M15 ultimately stopped substantially higher than M42 in this batch.
- Both split arms were set to approximately **2 °C cold crash on 2026-07-24**; 2026-07-25 was described as day 2 of that cold-crash period.

## Sensory observation
- **M42 was preferred** over M15 in this batch.

## Interpretation
- The result increased confidence in M42 for this specific strong dark-beer context and reduced confidence in M15 as a solo choice under the same conditions.

## Guard
Do **not** convert this into a universal “M42 is better than M15” rule. It is one Kvernhaug split batch.

## Existing durable cross-reference
The same one-batch observation is already preserved in the Ragnarok R1–R6 research state as supporting Brew Lab observation, explicitly not general technical truth.


## App-local plan evidence

Current 25 L recipe `recipes/vardeldr.json` records:
- pale ale malt **6.5 kg**
- Rauchmalz **1.5 kg**
- flaked oats **0.5 kg**
- CaraMunich II **0.4 kg**
- chocolate wheat **0.3 kg**
- Carafa Special II **0.3 kg**
- East Kent Goldings **100 g @ 60 min**
- yeast field **M42**
- computed OG **1.0875**
- computed FG **1.01838**
- computed ABV **9.07%**
- IBU **38.20**
- EBC **44.84**
- style label **Imperial Nordisk Røykstout**

The 8 L recipe is a proportional scaled version and also carries M42 in the recipe field.

An archived 25 L recipe copy records IBU **32.93** and lacks the later style-label field, showing recipe-plan evolution.

## App-local legacy log evidence

`recipes/vardeldr_-_8l_batch_logg.json` contains two entries:
- **2026-07-06** — 8.0 L, OG **1.100**, FG **1.01837531899**, ABV **10.7%**
- **2026-08-09** — 8.0 L, OG **1.100**, FG **1.024**, ABV **10.0%**, process `Reiterated mash (dobbel mesk)`

Do **not** assign these App log entries to the M42 and M15 arms. The local App files do not label an M15 arm, and the first App FG is byte-identical to the computed plan FG. The explicit M42/M15 split, arm-specific FG values and sensory preference remain sourced from user-authored chat history.
