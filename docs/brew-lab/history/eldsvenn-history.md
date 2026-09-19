# Eldsvenn / Skumring — reconstructed historical record

Reconstruction status: **review required**

This record now keeps three separate histories distinct:

1. **First Eldsvenn → Skumring** — the first beer brewed under the Eldsvenn name became too dark and was later renamed Skumring.
2. **Current/later Eldsvenn** — a separate later Eldsvenn batch, currently fermenting in the brewer's September 2026 context.
3. **Varðeldr** — a later **development from Skumring**, but as a new recipe rather than the same beer: ingredients were changed. The concrete Varðeldr brew was a small split-batch experiment with M42 vs M15.

## First Eldsvenn → Skumring

The brewer has now clarified the identity directly:

> The first Eldsvenn was too dark, so it was renamed **Skumring**.

### App-local plan and actual evidence

PLAN — `recipes/eldsvenn_v1.json`:
- batch **20.0 L**
- Wyeast **1318**
- Pilsner 5.0 kg
- Rauchmalz 1.5 kg
- pale wheat 0.5 kg
- flaked oats 0.4 kg
- Crystal Maple Carapils 0.3 kg
- chocolate wheat 0.2 kg
- Carafa Special II 0.1 kg
- East Kent Goldings 25 g @ 60 min
- computed OG **1.0918**
- computed FG **1.02479**
- computed ABV **8.80%**
- IBU **9.90**
- EBC **29.33**

ACTUAL — `recipes/eldsvenn_v1_logg.json`:
- date **2026-03-28**
- volume **20.0 L**
- OG **1.075**
- FG **1.013**
- ABV **8.1%**

The App filename remains Eldsvenn V1; the identity transition **first Eldsvenn → Skumring** comes from the brewer's direct clarification. No local file named Skumring was found.

Sensory notes attached to that batch:
- dark tones
- coffee
- light smoke
- dry finish
- not sweet/sticky/syrupy
- highly drinkable

### Historical naming discussion
Older June 2026 chat contains a temporary naming phase where **Varðeldr** was proposed/accepted for the dark first-Eldsvenn beer because it had drifted away from the intended Gamlegut-like direction. The brewer's newer direct clarification supersedes that historical naming attempt:

- the physical first Eldsvenn batch is **Skumring**;
- **Varðeldr** is the later changed-recipe development from Skumring.

Keep the older Varðeldr naming messages as historical naming-process evidence, not as current batch identity.

### Physical fermentation / packaging timeline
User-authored chat adds a concrete physical timeline around the first batch:
- fermentation context around **18 °C**;
- by **2026-03-31**, it was still bubbling weakly around **20 °C**, with krausen partly fallen but still present;
- a later direct gravity recollection gives OG around **1.075 @ 20 °C**, matching the App legacy log's 1.075;
- an earlier rough chat estimate had placed OG around **1.080–1.084**; preserve this as a conflicting early estimate rather than replacing the later/App value;
- on **2026-04-12**, FG was measured around **1.012**;
- the beer went to keg on **2026-04-12**, after roughly **14 days**;
- carbonation was set to approximately **1 bar CO₂**.

The App legacy log later records FG **1.013**, so the user-authored ~1.012 measurement and App 1.013 remain separate, closely agreeing observations rather than a single silently normalized value.

### Original design intent and sensory direction
User-authored chat records the first Eldsvenn concept as **"Gamlegut + litt røyk"**. The brewer later described the result as **very good**, but not truly the intended Eldsvenn/Gamlegut direction; smoke also became less prominent over time.

Sensory evolution in direct chat includes:
- **2026-04-12**: smoke + chocolate;
- later partner tasting: **"litt bacon"**;
- the brewer described an earlier sharper/sour-ish smoke with a somewhat **"fårepølse"** association that became less prominent with age;
- later keg tasting: dry finish, coffee/dark notes, light background smoke, easy-drinking, not sweet/sticky/syrupy.

This helps explain why the batch was separated from the later Eldsvenn line rather than treated as a successful final version of that concept.

### Identity status
This batch's later/final name is **Skumring**.

Varðeldr later **grew out of Skumring as a development direction**, but it was not simply Skumring with another yeast or name. The recipe was changed and the ingredients were not the same. Treat the lineage as conceptual/recipe development, while keeping the actual batches distinct.

---

## Current/later Eldsvenn — separate batch now fermenting

This is **not Skumring**. It is a later Eldsvenn brew. User-authored chat anchors the brewday to **2026-09-06**.

Concrete brew observations from the Eldsvenn thread include:
- pre-boil **30 L @ 1.052**
- the Wyeast 1318 starter had been **cold-crashed for about 48 hours** before brewday
- after about 60 min boil: **1.061**
- later gravity reading: **1.075**
- pitch temperature about **17 °C**
- **Wyeast 1318** slurry/starter used
- wort transferred through a sieve to remove solids and promote oxygenation
- approximately **90%** of the yeast slurry pitched
- notably large early krausen
- spunding later recorded at **5 psi**

A **small beer / parti-gyle** was made from the same Eldsvenn brewing session. User-authored chat records the intended yeast order explicitly: the main Eldsvenn got the **1318 first**, then the **remaining 1318** went to the small beer.

These are batch observations and should remain separate from recipe targets until the complete timeline is reconstructed.

### App-local search result
No second Eldsvenn-named local recipe/log was found in the read-only App archaeology pass. The later/current Eldsvenn therefore remains sourced from the user-authored brew chat and direct brewer clarification, not from the older local App files.

## Open reconstruction work
- Reconstruct the detailed brewday/process timeline for the first Eldsvenn that became Skumring; App-local evidence now anchors its log date and actual OG/FG/volume.
- Reconstruct the remaining fermentation/FG/package/tasting timeline for the current/later Eldsvenn; brewday is now anchored to **2026-09-06**.
- Keep the identities distinct even though the brewer has now directly clarified the lineage **Skumring → Varðeldr**: Varðeldr is a recipe development from Skumring with changed ingredients, not the same batch/recipe.
