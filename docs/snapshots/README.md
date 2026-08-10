# Project Snapshots

Denne mappen inneholder **Project Snapshots** — daterte øyeblikksbilder av hele prosjektets tilstand ved viktige milepæler.

Se [../development/WORKFLOW.md](../development/WORKFLOW.md#fase-8--backup--milepæl-project-snapshot) for når et snapshot skal anbefales, og [TEMPLATE.md](TEMPLATE.md) for malen.

## Hva et Snapshot er — og ikke er

| Er | Er ikke |
|---|---|
| Et frosset øyeblikksbilde på ett gitt tidspunkt | En backup (ingen filer sikkerhetskopieres) |
| Skrives én gang, redigeres aldri senere | En changelog (ingen liste over enkeltendringer over tid) |
| Dekker hele prosjektet samlet: kode, tester, Demo Mode, dokumentasjon, Vault, git | En commit-logg (`git log` er allerede autoritativ for det) |
| Peker til andre dokumenter (f.eks. `PROJECT_STATUS_*.md`) fremfor å duplisere dem | En erstatning for produktdokumentasjonen i `docs/` |

Se [../development/WORKFLOW.md](../development/WORKFLOW.md) for skillet mot `docs/PROJECT_STATUS_*.md` i detalj.

## Navnekonvensjon

```
docs/snapshots/YYYY-MM-DD_<kort-slug>.md
```

- `YYYY-MM-DD` — datoen snapshotet ble tatt (ikke datoen milepælen startet).
- `<kort-slug>` — 2-4 ord, PascalCase eller understrek, som kort identifiserer milepælen (f.eks. `KBDP_V1`, `Pantry_V1_Ferdig`, `Pre_Release_v3`).
- Ved flere snapshots samme dag: legg til `_2`, `_3` osv. på slutten av slug.

## Kronologisk indeks

| Dato | Fil | Milepæl |
|---|---|---|
| 2026-07-31 | [2026-07-31_KBDP_V1.md](2026-07-31_KBDP_V1.md) | KBDP etablert, CLAUDE.md restrukturert til utviklersystem, Snapshot-system innført |
| 2026-08-03 | [2026-08-03_Vestbrygg_Variantmodell_Ferdig.md](2026-08-03_Vestbrygg_Variantmodell_Ferdig.md) | Vestbrygg-variantmodell, lagerstatus, «bestill til eksakt mål» og 25 kg-sikkerhet ferdig kodet og testet (Steg A–F6) — fryst rett før første ekte data-aktivering |
| 2026-08-05 | [2026-08-05_Post-Raw_Pre-Master.md](2026-08-05_Post-Raw_Pre-Master.md) | Levende malt-rådata hentet og godkjent (Steg F9), Vestbrygg-only butikkfilter/dry-run i maltmatcheren kodet, testet og bevist trygt (Steg F10C–F10D) — fryst rett før første Vestbrygg-only-masteraktivering |
| 2026-08-10 | [2026-08-10_Pre_Web_Versjon.md](2026-08-10_Pre_Web_Versjon.md) | Vestbrygg-maltdata aktivert, stilscoring/IBU-korrekthetsfikser, 858 tester grønt — fryst rett før oppstart av offentlig, forenklet web-versjon av oppskriftsbyggeren (`web/`) |

*Oppdater denne tabellen (nyeste øverst eller nederst — vær konsistent) hver gang et nytt snapshot legges til. Selve snapshot-filene skal aldri redigeres i ettertid; denne indeksen er det eneste som vedlikeholdes løpende.*
