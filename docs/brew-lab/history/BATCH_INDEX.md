# Brew Lab batch identity index

Issue: #318

Status: **working reconstruction — identity map locked from direct brewer clarification; measurements still review-required where noted**

Purpose: keep **name/lineage**, **recipe identity**, and **physical brewed batch** separate so later chat archaeology cannot silently merge different beers.

## Current brewed batch identities

| Batch ID | Physical batch / identity | Lineage / rename | Yeast | Status / key note |
|---|---|---|---|---|
| BL-2026-SOMMERGLOD-V1 | Sommerglød v1 | first Sommerglød | W-34/70 | brewed; smoke faded faster than desired |
| BL-2026-SOMMERGLOD-V2 | Sommerglød v2 | v2 development | W-34/70 | brewed; separate batch from v1 |
| BL-2026-SKUMRING | first Eldsvenn batch, later named **Skumring** | **first Eldsvenn → Skumring** | historical record under review | brewed; first Eldsvenn was judged too dark and renamed |
| BL-2026-VARDELDR-SPLIT | Varðeldr test batch | **developed from Skumring**, but recipe/ingredients changed | split **M42 vs M15** | brewed small split-batch; not the same recipe/batch as Skumring |
| BL-2026-MARZEN | historical main **Märzen** | main beer | **LalBrew Diamond** | brewed; OG 1.064 datapoint preserved |
| BL-2026-TINYBEER | **TinyBeer / Kvernhaug Suttlevatn** | weak after-beer from Märzen malt | harvested **W-34/70 from Sommerglød** | brewed; separate from main Märzen |
| BL-2026-ELDSVENN-LATER | later/current **Eldsvenn** | separate later Eldsvenn line | **Wyeast 1318** | brewed; currently fermenting in Sept 2026 context |
| BL-2026-ELDSVENN-SMALL | Eldsvenn small beer / parti-gyle | after-beer from BL-2026-ELDSVENN-LATER | **Wyeast 1318** | brewed; separate from TinyBeer/Suttlevatn |

## Lineage map

- first Eldsvenn **→ renamed Skumring**
- Skumring **→ Varðeldr development**
  - Varðeldr is a **changed recipe with different ingredients**, not a rename or re-yeast of Skumring
  - concrete Varðeldr test was split M42 vs M15
- historical Märzen = **main beer**
  - Märzen malt **→ TinyBeer / Kvernhaug Suttlevatn** after-beer
- later/current Eldsvenn = **separate later batch**
  - later Eldsvenn **→ Eldsvenn small beer** from the same brewing session

## Hard guards

- **TinyBeer = Kvernhaug Suttlevatn.**
- **TinyBeer/Suttlevatn is not the historical main Märzen.**
- **Eldsvenn small beer is not TinyBeer/Suttlevatn.**
- **Skumring is the first Eldsvenn batch after rename.**
- **Varðeldr developed from Skumring, but is a new/changed recipe and a separate physical batch.**
- Do not infer one batch's gravity, yeast, sensory note, or package volume onto another merely because they share lineage.

## Still pending archaeology

- exact first-Eldsvenn/Skumring brew date and final source-verified measurement timeline
- exact Varðeldr recipe evolution from Skumring
- remaining concrete Brew Lab batches not yet represented as bounded records
- mine App-local history sources where available: current `recipes/_kbhbrew/*.json`, legacy `recipes/_logs/*_logg.json`, older root-level `recipes/*_logg.json`, and saved recipe JSON as plan/snapshot evidence
- extract-set brew history, if recovered from primary chat evidence
- fermentation/tasting/next-brew observations for batches still in progress

Ragnarok R1–R6 remains a preserved research snapshot and is not listed here as a completed physical brewed batch unless concrete brew evidence is separately reconstructed.
