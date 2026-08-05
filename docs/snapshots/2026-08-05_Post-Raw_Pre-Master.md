# Project Snapshot — 2026-08-05 — Post-Raw, Pre-Master (før første Vestbrygg-only-maltaktivering)

## Formål

- Fryse tilstanden etter at levende malt-rådata er hentet og godkjent (Steg F9B/F9E), og etter at den planlagte Vestbrygg-only-aktiveringen er kodet, testet og bevist trygg gjennom en godkjent dry-run (Steg F10C/F10D) — men FØR selve masterdataen faktisk er aktivert.
- Gjøre den kommende, kontrollerte masterendringen sporbar og reversibel: dette snapshotet er referansepunktet en fremtidig aktivering kan sammenlignes mot, og et sted å gå tilbake til dersom aktiveringen avdekker noe uforutsett.

## Git-baseline

| Felt | Verdi |
|---|---|
| HEAD | `8c29c5a` |
| Raw-data-commit | `a7b8879` — "data: oppdater maltkatalog med levende variant- og lagerdata" |
| Sekk/sack-fiks | `4d84111` — "fix: fjern pakningstype sekk og sack fra maltmatcherens navn" |
| Butikkfilter/dry-run | `8c29c5a` — "feat: legg til butikkfilter og dry-run i maltmatcheren" |
| Branch | `master` |
| Git-status | Helt ren ved snapshot-tidspunktet |

## Testbaseline

`py -3 -m unittest discover -s tests` → **785 tester, 0 failures, 0 errors, "OK"** (kjørt på nytt ved dette snapshotets pre-flight, F10E).

## Rådatastatus

- `raw_data/malt_raw.json`: 119 maltposter (91 Vestbrygg, 28 Ølbrygging).
- 119 unike URL-er blant de 119 postene — verifisert ved mengdesammenligning, ingen duplikater.
- Alle 119 raw-poster har et `lagerstatus`-felt (verifisert direkte på filen, ikke antatt) — kun verdiene `pa_lager` og `utsolgt` forekommer i rådataene (Vestbrygg bruker begge; Ølbrygging sine 28 poster har i praksis kun `pa_lager` i denne snapshotten, men feltet er til stede på alle).
- Ingen komplette ølsett blant de 119 postene — verifisert ved søk etter "sett"/"kit" i produktnavn (0 treff) og ved at eneste `kategori`-verdier i bruk er `malt` og `spraymalt`.

## Godkjent Vestbrygg-only dry-run

Kilde: Steg F10D, verifisert på nytt mot committet kode (`8c29c5a`) og de samme rådata-/masterfilene ved F10D sin post-commit-kontroll.

**Vestbrygg**
- raw: 91
- matchet: 87
- unmatched: 4
- varianter: 87
- slots funnet/oppdatert: 23/23

**Ølbrygging**
- raw: 28
- matchet: 23
- unmatched: 5
- slots analysert: 15
- slots oppdatert: 0

**Totalt**
- raw: 119
- matchet: 110
- unmatched: 9
- analyserte slots: 38
- faktisk oppdaterte slots: 23
- master-ID-sett: 53 før og etter (uendret av dry-run, verifisert direkte mot `data/master_malt.json`)

## Planlagt aktiveringsomfang

Første aktivering skal bruke:

    butikker={"vestbrygg"}
    dry_run=False

Kun `butikk_match.vestbrygg` får endres.

Følgende skal forbli urørt:

- alle `butikk_match.olbrygging`
- humle- og gjærmaster (`data/master_humle_v2.json`, `data/master_gjaer_v2.json`)
- raw-data (`raw_data/*.json`)
- master-ID-settet (ingen IDer legges til eller slettes)
- øvrige masterfelt (`display_name`, `aliases`, `verified`, osv.)

## Kjente og aksepterte begrensninger

### Crystal Maple / Carapils

- Mangler fra Vestbryggs kategorisnapshot ved F9B sin levende skraping (rotårsak isolert i Steg F9D til et forbigående butikk-/kategoriforhold, ikke en scraper- eller matcherfeil).
- Eksisterende Vestbrygg-mastermatch fryses urørt — dry-run har bevist dette punktvis (Steg F10D, punkt 14).
- Ingen ferske varianter eller lagerstatus for Crystal Maple/Carapils skrives i denne aktiveringen.

### Spraymalt Extra Light

- Forblir unmatched (bevisst, se Steg F8F).
- Skal ikke blandes med vanlig Spraymalt Light — kvalifikatorsperren (`_produktkvalifikatorer()`, Steg F8F) hindrer nettopp dette.
- Egen master-ID for Extra Light er utsatt til et senere steg.

### Ølbrygging

- Aktiveres ikke i denne runden.
- Caramel Pale-feilmatchen mot master `crystal` (via det brede "Caramel Malt"-aliaset, se Steg F10A/F10B) utsettes til et eget, senere Ølbrygging-/masterkurateringsspor.
- Bohemian Pilsner og Château Acid har kjent default-variant-instabilitet (se tidligere `docs/PROJECT_STATUS_JULI_2026.md`-dokumentasjon av rå-datakvalitet).
- Hele Ølbrygging-sporet behandles samlet, separat, senere.

## CaraMalt

Fire Vestbrygg-varianter (bekreftet i den godkjente dry-run-en, Steg F10D):

- 100 g knust
- 1 kg hel
- 1 kg knust
- 25 kg hel

25 kg-varianten er registrert `utsolgt` ved skrapetidspunktet, men beholdes i katalogen som kjent, gyldig pakningsdata (fjernes ikke — kun ekskludert fra Smart Handlelistes kjøpsforslag så lenge den er utsolgt). Flat representant (butikk_match.vestbrygg sine flate `pris`/`url`-felt) er 1 kg hel.

## Sikkerhetsgarantier

- Dry-run og ekte aktivering bruker samme matcherlogikk — begge kaller `_bygg_malt_matchresultat()` (Steg F10D), ingen parallell matcher finnes.
- Butikkfilteret (`butikker={"vestbrygg"}`) begrenser kun hvilke butikk-slots som faktisk skrives inn i masterforslaget — matching og statistikk kjøres uansett over hele rådatasettet.
- Dry-run har bevist, punkt for punkt, at alle `butikk_match.olbrygging`-data forblir identiske ved en Vestbrygg-only-aktivering (Steg F10D, punkt 12).
- Ingen master-IDer legges til eller slettes av en Vestbrygg-only-aktivering (53 før, 53 etter — bevist, ikke antatt).
- Ingen AI-normalisering inngår i noe steg i denne rekken (F9–F10D).

## SHA-256

Registrert ved dette snapshotets pre-flight (F10E), mot committet tilstand `8c29c5a`:

| Fil | SHA-256 |
|---|---|
| `raw_data/malt_raw.json` | `7d24bedec3cf9be67157e0fa74610e07a490cb93b64bff412cb51d1985ee4bdc` |
| `data/master_malt.json` | `d29ac7bf9f57c6d4509c136ae86f3cb8134b25cae2166c8269ddd9d1d681be54` |
| `raw_data/humle_raw.json` | `82dc5eb4389cef39821daa5e0a33a5a54b3a58def18dad76fb0503fbbe6893d9` |
| `raw_data/gjaer_raw.json` | `2016679905b2560864f849c744555d3ed3010fe9c1b2acc79af683ae97b44af9` |
| `data/master_humle_v2.json` | `98ba322d74974eefaca9a1f222c91fda97fc936c61dfa3a788b132adb424ee69` |
| `data/master_gjaer_v2.json` | `18d5c408e1ff649c7a0984cbdfa06f7c2c91f553617d50502df9556a64e25434` |

## Neste operative steg

Eget, kontrollert steg (ikke påbegynt av dette snapshotet):

1. Kjør matcher med `butikker={"vestbrygg"}`, `dry_run=False`.
2. Kontroller masterdiff mot dette snapshotets forventede omfang (kun `butikk_match.vestbrygg`, 23 slots).
3. Test Smart Handleliste manuelt mot de nye Vestbrygg-varientene.
4. Commit kun det godkjente master-/unmatched-resultatet.
5. Ingen push uten egen, eksplisitt godkjenning.

Dette snapshotet er append-only og redigeres ikke i ettertid — en eventuell oppdatering skjer som et nytt, senere snapshot. Det tidligere snapshotet ved `8b351fb` (`2026-08-03_Vestbrygg_Variantmodell_Ferdig.md`) er ikke rørt av dette steget.
