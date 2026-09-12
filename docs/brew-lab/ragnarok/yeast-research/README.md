# Ragnarok yeast research archive

This folder is the durable Git snapshot for Kvernhaug Brew Lab's Ragnarok yeast research (R1–R6, 2026-09-12/13).

## What is preserved in Git

- `RESEARCH_STATE.md` — current research state, methodology, rankings, solo/combination tracks, evidence hierarchy and R6 conclusions.
- `ARTIFACT_MANIFEST.md` — names and SHA-256 hashes of the exact spreadsheet artifacts created during R1–R6.

The research state is deliberately stored as normal text so it is diffable, searchable and survives independently of the ChatGPT session.

## Exact spreadsheet artifacts

The exact `.xlsx` workbooks were created in the ChatGPT artifact runtime. The connected GitHub writer available in this chat only accepts UTF-8 text files; it cannot safely commit the binary `.xlsx` files. An attempted encoded-binary archive was abandoned and removed rather than leaving an incomplete archive in Git.

The cumulative R6 workbook is:

`Kvernhaug_Ragnarok_Yeast_R6_case_studies_2026-09-13.xlsx`

It contains 36 sheets spanning the R1 candidate universe through the R6 case-study/evidence layer. The exact artifact hashes are recorded in `ARTIFACT_MANIFEST.md` so future copies can be verified byte-for-byte.

## Governance

These are **Brew Lab research artifacts**, not Core canonical masterdata. Producer data, brewer observations, interpretation, hypotheses and decisions are kept distinct. One batch or one community report must never silently become general technical truth, and Brew Lab findings must not silently modify Core contracts/masterdata.

## Current decision boundary

No final Ragnarok yeast has been chosen yet. The remaining major missing input is the actual **Ragnarok V1 fermentation task**: target OG, desired FG/body, realistic ABV range, malt-vs-Demerara gravity contribution, sugar-addition timing and wort fermentability. Solo and helper/combo finalists must be evaluated against that same concrete wort model before a final choice.
