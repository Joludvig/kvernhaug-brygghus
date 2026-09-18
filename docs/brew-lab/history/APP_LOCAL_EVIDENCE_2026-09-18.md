# App-local Brew Lab archaeology — 2026-09-18

Issue: #318  
PR: #319  
Source status: **read-only local extraction supplied by owner from Local Claude inspection**

This document preserves the local-App evidence extraction as a separate provenance layer. It does not override direct brewer clarification or user-authored chat history. Recipe files are PLAN evidence; legacy log entries are ACTUAL/NOTE evidence only to the extent their own fields support that classification.

## Source inventory

Read-only checkout inspected:
`D:\Development\Kvernhaug Brygghus`

Local data found:
- `recipes/_kbhbrew/*.json`: **1**
- `recipes/_logs/*_logg.json`: **0**; directory absent locally
- root legacy `recipes/*_logg.json`: **5**
- saved recipe/plan JSON under `recipes/`: **10**, of which one was an unrelated test/demo recipe
- supplementary recipe backups:
  - `recipes/_backup/*.backup_*`: **3**
  - `recipes_backup_20260727_215605/`: **15**
- separate `demo_recipes/`: **3**, treated as non-authoritative/demo provenance

Known dirty checkout files were observed but not changed:
- `docs/development/VAULT.md`
- `raw_data/unmatched_malt.json`

No files were changed during extraction.

## Sommerglød v1

PLAN — `recipes/kvernhaug_sommerglød.json`:
- batch: **25.0 L**
- malt: Weyermann Pilsner **4.576 kg**, Rauchmalz **0.364 kg**, Vienna **0.26 kg**
- hops: Saaz **35 g @ 60**, Hallertau Mittelfrüh **10 g @ 15**, Tettnang **10 g @ 5**
- yeast: **W-34/70**
- computed: OG **1.0481**, FG **1.00866**, ABV **5.18%**, IBU **19.69**, EBC **3.86**

LEGACY ACTUAL — `recipes/kvernhaug_sommerglød_logg.json`:
- date: **2026-06-01**
- volume: **25.0 L**
- OG: **1.050**
- FG: **1.0086588198424**
- ABV: **5.4%**
- note: empty

Caution: legacy FG is byte-identical to the recipe-computed FG, so the file alone cannot prove it was independently measured. User-authored chat separately records a later hydrometer FG around **1.009**.

Possible duplicate:
- `recipes/kvernhaug_sommerglod_logg.json`
- `recipes/kvernhaug_sommerglød_logg.json`
contain byte-identical log content and no brew identity field.

## Sommerglød v2

PLAN — `recipes/kvernhaug_sommerglodv2.json`:
- batch: **25.0 L**
- malt: Weyermann Pilsner **4.42 kg**, Rauchmalz **0.52 kg**, Vienna **0.26 kg**
- same hop schedule as v1
- yeast: **W-34/70**
- computed: OG **1.0481**, FG **1.00866**, ABV **5.18%**, IBU **11.64**, EBC **4.19**

LEGACY ACTUAL — `recipes/kvernhaug_sommerglodv2_logg.json`, two entries on **2026-07-13**:
1. volume **25.0 L**, OG **1.052**, FG **1.0086588198424**, ABV **5.7%**
2. volume **25.0 L**, OG **1.052**, FG **1.01**, ABV **5.5%**, process `Enkel infusjon`

Conflict is preserved. Entry 1 FG is byte-identical to PLAN FG and may be auto-carried; no decision is made here.

## First Eldsvenn → Skumring

PLAN — `recipes/eldsvenn_v1.json`:
- name: **Eldsvenn V1**
- batch: **20.0 L**
- malt:
  - Weyermann Pilsner **5.0 kg**
  - Rauchmalz **1.5 kg**
  - pale wheat **0.5 kg**
  - flaked oats **0.4 kg**
  - Crystal Maple Carapils **0.3 kg**
  - chocolate wheat **0.2 kg**
  - Carafa Special II **0.1 kg**
- East Kent Goldings **25 g @ 60**
- yeast: **Wyeast 1318**
- computed: OG **1.0918**, FG **1.02479**, ABV **8.80%**, IBU **9.90**, EBC **29.33**

LEGACY ACTUAL — `recipes/eldsvenn_v1_logg.json`:
- date: **2026-03-28**
- volume: **20.0 L**
- OG: **1.075**
- FG: **1.013**
- ABV: **8.1%**

No local file named Skumring exists. Identity mapping **first Eldsvenn → Skumring** comes from direct brewer clarification, not from App filenames.

## Varðeldr

PLAN — `recipes/vardeldr.json`, 25 L:
- style label: **Imperial Nordisk Røykstout**
- pale ale malt **6.5 kg**
- Rauchmalz **1.5 kg**
- flaked oats **0.5 kg**
- CaraMunich II **0.4 kg**
- chocolate wheat **0.3 kg**
- Carafa Special II **0.3 kg**
- East Kent Goldings **100 g @ 60**
- yeast: **M42**
- computed: OG **1.0875**, FG **1.01838**, ABV **9.07%**, IBU **38.20**, EBC **44.84**

PLAN — `recipes/varðeldr_-_8l_batch.json`:
- scaled 8 L version
- same ingredient ratios
- yeast field: **M42**
- same computed OG/FG/ABV/IBU/EBC

Archived plan — `recipes/_archive/varðeldr.json`:
- earlier 25 L state
- IBU **32.93** instead of 38.20
- missing later style-label field

LEGACY ACTUAL — `recipes/vardeldr_-_8l_batch_logg.json`:
1. **2026-07-06** — 8.0 L, OG **1.100**, FG **1.01837531899**, ABV **10.7%**
2. **2026-08-09** — 8.0 L, OG **1.100**, FG **1.024**, ABV **10.0%**, process `Reiterated mash (dobbel mesk)`

These two log entries are not assigned to M42/M15 arms because the local App data does not label an M15 arm. User-authored chat remains the source for the explicit M42-vs-M15 split and arm-specific FG/sensory evidence.

## Historical Märzen main beer

Base PLAN — `recipes/kvernhaug_wiesn-märzen_1872.json`, 25 L:
- Munich I **0.7 kg**
- Munich II **4.6 kg**
- Vienna **1.8 kg**
- Tettnang **88 g @ 60**
- yeast field: **W-34/70**
- computed: OG **1.0640**, FG **1.01152**, ABV **6.89%**, IBU **22.20**, EBC **15.06**

Brew-specific PLAN — `recipes/kvernhaug_wiesn-märzen_1872_-_23l_batch.json`:
- batch: **23 L**
- scaled grist
- Tettnang **81 g @ 60**
- yeast: **LalBrew Diamond Lager**
- computed: OG **1.0640**, FG **1.01280**, ABV **6.72%**, IBU **22.21**, EBC **20.74**
- process: **Hochkurz** — 63 °C / 40 min, 70 °C / 30 min, 77 °C / 10 min
- water target: **Maltpreget tysk lager**

Backup comparison shows the 23 L file was first saved with W-34/70 and no process/water-profile fields, then edited in place on **2026-08-28** to Diamond + Hochkurz + water target.

No paired local App actual/log file was found for either Märzen recipe. Actual Diamond fermentation observations remain sourced from user-authored chat.

## TinyBeer / Kvernhaug Suttlevatn

No App recipe/log/_kbhbrew/backup record under TinyBeer/Suttlevatn aliases was found. This branch therefore remains reconstructed from user-authored chat/direct brewer clarification rather than local App history.

## Later/current Eldsvenn + Eldsvenn small beer

No second Eldsvenn-named local recipe/log was found. The one local Eldsvenn V1 pair is dated 2026-03-28 and is kept with the first-Eldsvenn/Skumring record.

The later/current Eldsvenn and its small beer therefore remain chat/direct-brewer sourced in this reconstruction.

## Other local structured brew record

`Gamleguten klone`:
- recipe: `recipes/gamleguten_klone.json`
- structured brew under `recipes/_kbhbrew/`
- brewId: `brew-2ab2c66b-363f-4b13-ab7e-8dd2b113cce3`
- status: `active`
- createdAt: **2026-09-06T10:14:46Z**
- brewedAt: **null**
- actuals/sensing/learning: empty
- plan uses **Wyeast 1318**

This proves an App brew record was created, but does **not** prove a physical brew occurred. Keep outside the brewed-batch index until owner/history evidence confirms its real-world status.

## Provenance guards

- Direct brewer clarification wins for rename/lineage identity.
- User-authored chat remains primary for physical process/sensory evidence not present in App.
- Local recipe JSON is PLAN evidence.
- Legacy `*_logg.json` entries are historical App evidence, but auto-carried calculated values are possible and must not be silently promoted to independently measured values.
- Conflicting log entries remain separate.
- Demo-recipe content is not promoted to durable batch truth without corroboration.
