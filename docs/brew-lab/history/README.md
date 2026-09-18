# Brew Lab historical reconstruction

Issue: #318

Status: **reconstructed evidence — review required before treating as durable batch truth**

This folder preserves batch/experiment evidence recovered from prior Kvernhaug brewing conversations.

## Evidence classes

Each record keeps these separate:

1. **Instrument measurements** — gravity, volume, temperature, pressure, dates/times.
2. **Process observations/deviations** — what physically happened.
3. **Sensory observations** — taste, aroma, body, appearance.
4. **Interpretation** — what an observation may mean.
5. **Hypothesis/open question** — not yet proven.
6. **Decision/next brew** — what was chosen for later work.

A one-batch observation is never promoted to general brewing truth.

## Reconstruction rules

- Do not invent missing measurements.
- Approximate values stay approximate.
- Conflicting historical values are preserved as conflicts instead of silently normalized.
- Producer/spec data is not the same thing as Brew Lab observation.
- Existing Ragnarok R1–R6 files remain the authoritative preserved research snapshot for that research.
- App batch data and Brew Lab evidence may overlap, but ownership remains separate: App may hold structured batch records; Brew Lab owns experiments, observations, interpretations and learning.

## Pass 1 records

- `sommerglod-v1-v2.md`
- `vardeldr-m42-vs-m15.md` — **developed from Skumring**, but with a changed recipe/ingredients; concrete test was split M42 vs M15
- `eldsvenn-history.md` — separates **first Eldsvenn → Skumring** from the **current/later Eldsvenn now fermenting**
- `eldsvenn-partigyle-2026-08.md` — small beer from the current/later Eldsvenn session, using the same yeast
- `diamond-fermentation-observation.md` — **Märzen → TinyBeer**, with the Diamond fermentation datapoint preserved as one concrete batch observation

More chat archaeology is still pending.
