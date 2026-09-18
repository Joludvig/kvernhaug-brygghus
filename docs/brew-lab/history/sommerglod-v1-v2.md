# Sommerglød — reconstructed Brew Lab record

Reconstruction status: **review required**

## Sommerglød v1 — 2026-06-01

### Instrument measurements
- Expected OG noted in conversation: **1.048**
- Measured OG: **1.050**
- Later hydrometer FG: **1.009**
- Later stated ABV: approximately **5.4%**
- Temperature at the later FG-check context: approximately **15 °C**

### Process observations
- Beer direction: pils/lager with smoke.
- Rauchmalz: **7%**.
- Yeast: **W-34/70**.
- Historical fermentation discussion records a warm storm-fermentation period reaching approximately **18–20 °C**, followed by cooling to approximately **9 °C**.
- At the 1.009 FG discussion, about **12 days** had passed since pitching and there had been no meaningful pressure increase for several days.
- The brewer planned a cold crash before kegging to reduce suspended material/grums.

These are observations from this batch/timeline, not a recommended fermentation program.

### Sensory observations
- Malt/bread character was noted, with a light smoke character.
- Smoke character was observed to fade/disappear quickly.

### Interpretation
- Later Kvernhaug discussion treated the **7% Rauchmalz** smoke level in v1 as too subtle/short-lived for the intended Kvernhaug smoke signature.

### App-local evidence
Legacy App log `recipes/kvernhaug_sommerglød_logg.json` records:
- date **2026-06-01**
- volume **25.0 L**
- OG **1.050**
- FG **1.0086588198424**
- ABV **5.4%**

The legacy FG is byte-identical to the recipe-computed FG, so the App file alone does not prove it was independently measured. The user-authored chat's later hydrometer reading around **1.009** remains separate evidence.

The App recipe plan records **25.0 L**, W-34/70 and a 7% Rauchmalz grist consistent with the chat reconstruction.

### Open questions
- Exact packaged volume and exact pressure history are not safely reconstructed in this pass.

---

## Sommerglød v2 — 2026-07-12

### Instrument measurements
- Refractometer reading at brew/start: **1.052**
- Fermentation temperature: **12 °C**
- Spunding/pressure: approximately **2 psi**

### Process
- Smoke malt target recorded as **10%**.
- Mash water: **17.0 L**.
- Mash temperature: **66 °C**.
- Mashout: **78 °C**.
- The RAPT/controller accidentally started heating toward boil before sparging.
- No stirring after mash-in; the upper screen was used and the brewer noted clearer wort.
- During runoff, a volume reading of **13.5 L** was recorded; the kettle was later stopped below **33 L**, described as the practical maximum.
- **Saaz** was added during the boil.
- Yeast: **2 × W-34/70**, rehydrated.
- Wort was cooled to **15.7 °C** for pitching.
- Inkbird/thermowell was set to **12 °C**.
- Approximately **26 L** went to the fermenter.
- Refractometer OG: **1.052**.
- One whole Whirlfloc tablet was added at about **15 min** remaining, although roughly half a tablet had been planned.
- Kegged: **2026-07-25**.
- W-34/70 slurry harvested: **2026-07-25**.
- Keg/batch recorded as empty: **2026-08-27**.

### Sensory observations
- Later discussion described the smoke in Sommerglød v2 as still too subtle for the stronger Kvernhaug smoke signature desired in darker beers.

### App-local evidence
Legacy App log `recipes/kvernhaug_sommerglodv2_logg.json` contains **two entries on 2026-07-13**:
- entry A: volume **25.0 L**, OG **1.052**, FG **1.0086588198424**, ABV **5.7%**
- entry B: volume **25.0 L**, OG **1.052**, FG **1.010**, ABV **5.5%**, process `Enkel infusjon`

These entries conflict on FG/ABV and are preserved separately. Entry A's FG is byte-identical to the recipe-computed FG, so it may be auto-carried; no silent reconciliation is made.

### Interpretation
- v2 became a practical reference point showing that 10% smoke malt in this specific beer/process did not read as strongly smoky to the brewer.

### Boundary
This is one Kvernhaug batch observation, not a universal rule for Rauchmalz percentage or smoke perception.
