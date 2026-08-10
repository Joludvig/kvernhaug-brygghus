# Project Snapshot — 2026-08-10 — Før oppstart av offentlig web-versjon

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-10 |
| Tid | 11:12 (lokal tid) |
| Versjon | Ikke versjonsnummerert (ingen `VERSION`-fil eller tilsvarende i repoet) |
| Git branch | `master` |
| Siste commit | `5586c16` — "feat: demp korrelert OG/FG/ABV i stilscoringen" (2026-08-07) |
| GitHub-status | `master` er 4 commits foran `origin/master` (ikke pushet) |

## Prosjektstatus

**Kort oppsummering**

Kvernhaug Brygghus er en moden, aktivt vedlikeholdt Streamlit-app med Pantry V1, Smart Handleliste V1 og Water Chemistry V1 ferdigstilt (jf. `docs/PROJECT_STATUS_JULI_2026.md`, 2026-07-28). Siden den datoen er Vestbrygg-maltdata aktivert i master, og stilscoringen/IBU-beregningen har fått flere korrekthetsfikser. Dette snapshotet fryser tilstanden rett før arbeidet med en ny, separat leveranse starter: en offentlig, forenklet web-versjon av oppskriftsbyggeren.

**Nye milepæler**

Siden forrige snapshot (`2026-08-05_Post-Raw_Pre-Master.md`) — 11 commits:
- Levende Vestbrygg-maltdata aktivert i `master_malt.json` (butikkfilter, dry-run, navnevask, pakningstype-rydding).
- Stilscoring: unngår å telle korrelert avvik i OG/FG/ABV dobbelt (samme underliggende gjæringsavvik ga tidligere kunstig lavt stiltreff).
- IBU-beregning respekterer nå eksplisitt 0 % alfasyre i stedet for å falle tilbake til standardverdi.
- Brygghuseffektivitet omdøpt/korrigert konsekvent (planlagt effektivitet kalles nå riktig brygghuseffektivitet).
- Stilforklaringer viser nå faktisk verdi og avvik, ikke bare terskel.
- Direkte regresjonstester lagt til for OG/FG/ABV.

**Status på hovedmoduler**

Speiler `docs/PROJECT_STATUS_JULI_2026.md` (2026-07-28) — ingen store modulstatus-endringer siden da, kun korrekthetsfikser i eksisterende beregningslogikk og datamateriale:

| Område | Status |
|---|---|
| Oppskriftsbygger, skalering, bryggedagsark/A4 | Ferdig |
| Style Engine | Ferdig (korrigert siden juli: korrelasjonsdemping, mer presise forklaringer) |
| Water Chemistry V1 | Ferdig |
| Pantry V1 / Smart Handleliste V1 | Ferdig |
| Vestbrygg-variantmodell (lager, "bestill til eksakt mål", 25 kg-sikkerhet) | Ferdig kodet og testet; ekte Vestbrygg-maltdata nå aktivert i master (siden `1c3f02d`) |
| Legacy humlelager + gammel handleliste | Beholdt, ikke synkronisert med Pantry |

**Kjente begrensninger**

Hentet fra `docs/PROJECT_STATUS_JULI_2026.md` og ikke motsagt av noe funnet i dette snapshotet:
- Belgisk Witbier kan i enkelte tilfeller få for høyt numerisk stiltreff ved ren tallmessig overlapp uten reell belgisk gjærsignatur.
- Water Chemistry V1 har bevisst ingen automatisk pH-/syredosemodell.
- Legacy humlelager/gammel handleliste kan avvike fra reell Pantry-beholdning.

**Pågående arbeid**

- Wiesn-akseptansetesten er fortsatt ikke fullført (malt- og W-34/70-registrering i Pantry gjenstår) — uendret siden juli-status.
- Ny, separat leveranse starter rett etter dette snapshotet: offentlig web-versjon av oppskriftsbyggeren (forenklet — kun OG/FG/ABV/IBU/EBC-beregning, lokal lagring i nettleser, print/eksport, ingen innlogging/database). Vanilla HTML/CSS/JS i ny undermappe `web/` i samme repo. Ikke påbegynt kode ennå på snapshot-tidspunktet.

## Kode

**Tester**

Kjørt på nytt i dette snapshotet: `py -3 -m unittest discover -s tests` → **858 tester, 0 failures/errors** (opp fra 581 i juli-statusen — testsuiten har vokst betydelig siden da, primært knyttet til Vestbrygg-aktivering og stilscoring-regresjon).

**Demo Mode**

Ikke fullstendig re-revidert i dette snapshotet, men ingen av commits siden juli-statusen berører fil-I/O eller nye skriveoperasjoner (stilscoring/IBU/effektivitet-fiksene er ren beregningslogikk i `modules/`, Vestbrygg-dataaktiveringen er en masterdata-oppdatering, ikke ny kode-sti). Ingen kjent avvik fra dekningstabellen i [DEMO_MODE.md](../development/DEMO_MODE.md).

**Dokumentasjon**

`docs/PROJECT_STATUS_JULI_2026.md` er fra 2026-07-28 og dermed 11 commits bak faktisk kode — forventet, siden statusdokumenter er punkt-i-tid og ikke oppdateres løpende (jf. WORKFLOW.md). `CLAUDE.md` og `docs/development/`-dokumentene ble lest i forbindelse med dette snapshotet og er i sync med faktisk kodestruktur (arkitekturgrense, testkommando, snapshot-prosess).

**Vault**

Ikke undersøkt i dette snapshotet — `C:\Vault\Kvernhaug Brygghus` ble ikke åpnet. Siden endringene siden forrige snapshot er interne korrekthetsfikser (ikke nye brukervendte funksjoner eller ølidentitetsrelevante endringer), vurderes det som lite sannsynlig at Vault-en trenger oppdatering, men dette er ikke verifisert direkte.

**Teknisk gjeld**

Uendret fra `docs/PROJECT_STATUS_JULI_2026.md`: uavklart `raw_data/malt_raw.json`-arbeidskopi, `master_malt.json`-filnavn beholder eldre navn til tross for v2-format, `wip/gjaer-id-migrasjon`-branch venter fortsatt på rebase, `hent_alle_oppskrifter()` kan kollapse navnekolliderende oppskrifter uten varsel. Ingen nye TODO/FIXME-markører funnet i `modules/`, `ui/`, `app.py` eller `config.py` i dette snapshotet.

**Arkitektur**

`modules/` vs. `ui/`-grensen er intakt — ingen Streamlit-imports funnet utenfor `ui/` i denne gjennomgangen. Den nye web-versjonen (`web/`) er bevisst utenfor denne grensen: den er ikke en del av Streamlit-appens `modules/`/`ui/`-arkitektur, men et frittstående, klient-side JavaScript-produkt som vil portere utvalgte formler fra `modules/calculations.py` manuelt (ingen delt kjøretidsavhengighet mellom Python- og JS-siden).

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 11 (siden `2026-08-05_Post-Raw_Pre-Master.md`) |
| Klar for release? | Ja for eksisterende funksjonalitet — ingen kjente regresjoner, full testsuite grønn |
| Klar for push? | `master` er 4 commits foran `origin/master`; ikke pushet i denne økten (ingen automatisk push per Git-reglene) |

## Kommentar

Tatt på brukerens eksplisitte forespørsel, rett før oppstart av en ny hovedleveranse: en offentlig, forenklet web-versjon av oppskriftsbyggeren (`web/`-mappe, vanilla HTML/CSS/JS, ingen innlogging/database, lokal nettleserlagring). Formålet er å fryse prosjektets tilstand slik den var *før* dette nye, separate arbeidet startet, i tråd med KBDP fase 8 (nye hovedmoduler).
