# V2.2 G3P-1 — Råvarer P1 Malt core: source-gap record

Governed by [#426](https://github.com/Joludvig/kvernhaug-brygghus/issues/426); contract
`v22_g3p_raw_material_learning_contract.md` (§5 P1, §13). Base: `95326ce17b82133fe5fb14956d2f51dec7a20665`.

## Outcome

**No registry record was added.** The Course Fact Registry (`bryggeskole/data/course_fact_registry.json`) is unchanged.

The issue's source gate requires every cited source to be opened and read in the same run, and forbids filling gaps from general
brewing knowledge or AI. In this run the agent's only means of opening external pages were denied by the run's permission
configuration: `WebFetch` ("requested permissions … haven't been granted") and `curl` via Bash ("requires approval"). No source was
therefore opened, and nothing can honestly be marked `verified`.

## Status per required concept

| Concept | Status | Reason |
|---|---|---|
| `malt.what_is_malt` | UNRESOLVED SOURCE GAP | Briess "The Malting Process" not opened in this run. |
| `malt.base_vs_specialty` | UNRESOLVED SOURCE GAP | Briess "Understanding a Malt Analysis" / "The Malting Process" not opened in this run. |
| `malt.colour_flavour` | UNRESOLVED SOURCE GAP | Briess pages and Prado et al. 2021 not opened in this run. |
| `malt.grist_percentage` | UNRESOLVED SOURCE GAP | No source opened; no candidate source identified beyond the reconnaissance list. |
| `malt.extract_fermentability` | Covered by reuse | FACT-MASH-0001 and FACT-MASH-0004, within their existing scope; not duplicated. |

Kunze (Tier B) was not available and was not used.

## Sources still to open (from the issue; unchanged)

- Briess — The Malting Process — https://brewingwithbriess.com/malting-101/malting-process/
- Briess — Understanding a Malt Analysis — https://brewingwithbriess.com/blog/understanding-a-malt-analysis/
- Prado et al. 2021 — https://ift.onlinelibrary.wiley.com/doi/abs/10.1111/1541-4337.12806

## Next step

Re-run #426 in an environment where these pages can be fetched (grant `WebFetch`, or allow read-only `curl`), then add the four
records with tier, scope, and wording traps per the issue's red flags (no numeric colour ranges, no "specialty malt never converts").
No tests were changed; the existing registry tests are unaffected.
