# Project Snapshot — 2026-08-03 — Vestbrygg-variantmodell ferdig, ekte data-aktivering gjenstår

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-03 |
| Tid | ca. 21:20 (systemklokke på utviklingsmaskinen; tidssone ikke verifisert) |
| Versjon | Ingen semantisk versjonsnummerering i aktiv bruk. Nyeste git-tag `v2-stable` peker fortsatt til commit `30ef046` (2026-05-25) — betydelig eldre enn dette snapshotet, ikke representativ. |
| Git branch | `master` |
| Siste commit | `1b3578b` — "docs: oppdater status for maltvarianter og Vestbrygg-aktivering" |
| GitHub-status | Lokal `master` er 12 commits foran `origin/master` (ingen av de 12 er pushet, inkludert denne). |

## Prosjektstatus

**Kort oppsummering**

Siden forrige snapshot (`2026-07-31_KBDP_V1.md`) er en sammenhengende utviklingsrekke (Steg A–F6, 10 commits) fullført: Smart Handleliste sin malt-kjøpsflyt har fått deterministisk matching, en formalisert kjøpsresultat-kontrakt, en full Vestbrygg-variantmodell med lagerstatus, en «bestill til eksakt mål»-modus for knust malt, og en sikkerhetssperre mot at en hel 25 kg-sekk feilaktig kan inngå i det eksakte-mål-løftet. Alt dette er ferdig kodet og testet (720 tester grønne), men **ikke aktivert med ekte data** — dette snapshotet fryser nettopp grensen mellom "kodeferdig" og "aktivert", rett før den planlagte, kontrollerte første aktiveringen.

**Nye milepæler**

- **Produkttypefiltrering** (`cbec1b2`-serien, commit `4af0fcc`): brødsmulebasert gate skiller komplette ølsett fra råvarer før raw_data/matcher.
- **Deterministisk maltmatching** (`cbec1b2`): konkurrerende pakningsvarianter gir en stabil, deterministisk representativ flat pris/URL i stedet for en tilfeldig/rekkefølgeavhengig én.
- **Kjøpsresultat-kontrakten** (`fc52e47`): `{pris, mottatt_mengde, bestilling}` formalisert som én atomisk enhet fra samme valgte pakkekombinasjon — ikke tre separat utregnede felt.
- **Restberegning fra kjøpsresultat** (`ef3d447`): bevist (ikke bare antatt) at Pantry-/restlogikken i Smart Handleliste bruker kjøpsresultatets `mottatt_mengde`, ikke en separat utregning.
- **Ølbrygging-variantsamling** (`1a78c2b`): alle faktiske maltpakkealternativer for Ølbrygging.no samles i én `varianter`-liste, samme kontrakt som Vestbrygg.
- **Vestbrygg-scraperutvidelse** (`ee11d48`): mor-sider utvides til faktiske barn-SKU-er; mor-sidens «Fra X,-»-pris brukes ALDRI som produktpris for en spesifikk variant; faktiske lenker brukes — ingen ID-aritmetikk for å gjette URL-er.
- **Vestbrygg-variantmodell + lagerstatus** (`71ed4ad`): `butikk_match.vestbrygg.varianter` med `pakningsstorrelse_gram`, `malttype`, `pris`, `url`, `lagerstatus` (`pa_lager`/`utsolgt`/`ukjent`). Utsolgte varianter beholdes som katalogdata (fjernes ikke), men ekskluderes fra alle kjøpsforslag.
- **«Bestill til eksakt mål»** (`5d37313`): eksplisitt brukervalg, kun Vestbrygg + knust malt. Pris beregnes fra faktiske valgte SKU-er; mottatt_mengde kan settes til eksakt oppskriftsbehov i stedet for SKU-summen. Ingen automatisk melding sendes, ingen automatisk utsjekking skjer. Sluttkontrollrunde avdekket og rettet et separat fallback-hull (falskt kjøpsforslag når alle relevante varianter er utsolgt) i samme commit.
- **25 kg-sikkerhet** (`e3799a7`): en hel, ferdigpakket 25 kg-sekk identifiseres eksplisitt på gramtall (`SEKK_STORRELSE_GRAM = 25_000`, ALDRI som "største registrerte pakningsstørrelse") og kan ikke inngå i eksakt-mål-løftet — ordinær pakkelogikk og Pantry-rest brukes i stedet når en sekk inngår i den valgte kombinasjonen.
- **Dokumentasjonsopprydding** (`1b3578b`): `docs/MASTER_DATA_FLOW.md`, `docs/ROADMAP.md`, `docs/PROJECT_STATUS_JULI_2026.md` oppdatert til å beskrive faktisk status (implementert i kode, ikke aktivert med ekte data) i stedet for foreldede "planlagt"/"fremtidig"-formuleringer.

**Status på hovedmoduler**

Kilde: `docs/PROJECT_STATUS_JULI_2026.md` (datert 2026-07-28, skrevet mot commit `8abfb15`) + denne øktens eget arbeid for malt-relaterte rader. Øvrige rader sitert, ikke reverifisert i denne økten:

| Område | Status |
|---|---|
| Oppskriftsbygger, skalering, bryggedagsark/A4 | Ferdig (sitert, ikke reverifisert) |
| Prosessprofiler (inkl. Hochkurz) | Ferdig (sitert, ikke reverifisert) |
| Style Engine (22 BJCP-stiler) | Ferdig (sitert, ikke reverifisert) |
| Water Chemistry V1 | Ferdig (sitert, ikke reverifisert) |
| Pantry V1 | Ferdig (sitert, ikke reverifisert) |
| Smart Handleliste V1 + maltpakningsoptimalisering | Ferdig, **utvidet denne økten**: variantmodell, lagerstatus, eksakt mål, 25 kg-sperre — alt kodeferdig, testet, IKKE aktivert med ekte data (se Fase 4/Ikke-aktivert nedenfor) |
| Vestbrygg-scraper (barn-/variantoppdagelse) | Ferdig kodet og testet (Steg F1), ikke kjørt mot ekte butikkdata ennå |
| Legacy humlelager / gammel handleliste | Beholdt, bevisst ikke synkronisert med Pantry — kjent, separat maltprisbug i det gamle, flate prisfeltet (se Bevisst utsatt arbeid) |
| Demo Mode | 1:1, uendret av denne økten (se "Demo Mode" under) |

**Kjente begrensninger**

Fra `docs/PROJECT_STATUS_JULI_2026.md` ("Kjente svakheter"/"Teknisk gjeld"), ikke fullstendig reverifisert i denne økten, pluss nye funn fra denne utviklingsrekken:

- Belgisk Witbier kan i enkelte tilfeller få for høyt numerisk stiltreff uten reell belgisk gjærsignatur. (Ikke reverifisert i denne økten.)
- Vannkjemi V1 har bevisst ingen automatisk pH-/syredosemodell. (Ikke reverifisert i denne økten.)
- Legacy humlelager/handleliste er ikke koblet mot Pantry, og har en tidligere identifisert, separat maltprisbug knyttet til gamle, flate prisfelt — Smart Handleliste er den korrekte, nye flyten; denne bugen er bevisst IKKE rettet i denne utviklingsrekken (utenfor scope).
- `hent_tilgjengelige_malttyper()` kan fortsatt omtale en maltform som tilgjengelig ut fra rå variantliste, selv om ALLE varianter av den formen er utsolgt — påvirker kun advarselstekst, ikke selve kjøpsanbefalingen (som allerede korrekt ekskluderer utsolgte varianter via `_varianter_for_form()`). Kjent, bevisst ikke rettet (lav prioritet, se Steg F2-rapporten).
- **(Verifisert i denne økten)** 0 forekomster av `TODO`/`FIXME` i `modules/`, `ui/`, `app.py`, `config.py`.
- **(Verifisert i denne økten)** Seks eksisterende, uavklarte lokale dataendringer — se eget avsnitt under.

**Pågående arbeid**

Ingen pågående, ufullført kodearbeid ved dette snapshotets tidspunkt — Steg A–F6 er en avsluttet, committet rekke. Det eneste gjenstående er den planlagte, ENDA IKKE PÅBEGYNTE første ekte data-aktiveringen (se Fase 6/Aktiveringsrekkefølge under) og den reelle Wiesn-akseptansetesten (sitert fra `docs/ROADMAP.md`, ikke reverifisert i denne økten — malt og faktisk gjær W-34/70 gjenstår der).

## Kode

**Tester**

Kjørt på nytt i denne økten: `py -3 -m unittest discover -s tests` → **720 tester, 0 failures, 0 errors, "OK"**, kjøretid 31.1s (2026-08-03, ca. 21:19). Opp fra 581 ved forrige snapshot (2026-07-31) — +139 tester gjennom hele Steg A–F6-rekken.

Testene bruker fixtures/mocks (fabrikerte variant-/lagerstatus-/kjøpsresultat-data) — de validerer at KODEN oppfører seg korrekt gitt en gyldig datastruktur, men validerer IKKE i seg selv at kommende ekte Vestbrygg-masterdata faktisk vil ha riktig skjema (feltnavn, verditype) når den først skrives. Se Fase 6/Aktiveringsrekkefølge, steg 5 og 8, for hvordan dette dekkes ved aktivering.

**Demo Mode**

1:1 med fullversjonen per `docs/development/DEMO_MODE.md` — verifisert i denne økten at ingen av de nye filene (`modules/malt_packaging.py`, `modules/smart_shopping_list.py`) har noen `DEMO_MODE`-betinget gren i det hele tatt; eneste `DEMO_MODE`-referanse i hele denne funksjonalitetens kode-sti er den allerede eksisterende Pantry-datakilde-bryteren i `ui/smart_shopping_list_panel.py:135` (`demo_state.hent_pantry() if DEMO_MODE else pantry.last_pantry()`). Demo Mode arver dermed variantmodell/lagerstatus/eksakt-mål/25kg-sperre automatisk og identisk med fullversjonen, siden all ny logikk ligger i `modules/`, ikke i noen demo-spesifikk gren. MÅ likevel verifiseres manuelt mot ekte Vestbrygg-data før en fremtidig push/redeploy (se Fase 7).

**Dokumentasjon**

`docs/MASTER_DATA_FLOW.md`, `docs/ROADMAP.md`, `docs/PROJECT_STATUS_JULI_2026.md` oppdatert i forrige commit (`1b3578b`, Steg F6) til å reflektere faktisk status. `docs/PROJECT_STATUS_JUNI_2026.md` og `docs/Status Juli 2026.md` (et Obsidian-vault-utkast som ved en feiltakelse ligger i `docs/`) er bevisst IKKE omskrevet — se Steg F6-rapporten for begrunnelse (historiske dokumenter skal reflektere hva som var sant da de ble skrevet).

**Vault**

Søkt og vurdert i Steg F6 (samme økt-rekke, rett før dette snapshotet): Canon- og Handover-dokumentene i `C:\Vault\Kvernhaug Brygghus` ble søkt gjennom for "variant"/"eksakt mål"/"lagerstatus"/"pakke_gram"/"25 kg"/"Handleliste" — ingen relevant Canon- eller Handover-innhold refererer til denne funksjonaliteten i det hele tatt, og er derfor ikke gjort foreldet av Steg A–F6. Ingen Vault-oppdatering var nødvendig. Ikke re-undersøkt på nytt i dette snapshotet utover å bekrefte at konklusjonen fra Steg F6 fortsatt er gyldig (ingen Vault-endring har skjedd mellom Steg F6 og dette snapshotet).

**Teknisk gjeld**

0 forekomster av `TODO`/`FIXME` funnet ved grep i `modules/`, `ui/`, `app.py`, `config.py` (samme dekningsbegrensning som forrige snapshot: dekker ikke `tests/` eller frittstående kommentarer uten disse nøkkelordene). Nytt siden forrige snapshot:

- De seks kjente, uavklarte lokale dataendringene (se eget avsnitt under) — uendret gjennom hele Steg A–F6, ikke rørt av noen kode- eller dokumentasjonsendring i denne rekken.
- Hybrid med hele sekker + eksakt mål kun på restdelen — bevisst utsatt, venter på Vestbrygg-avklaring (se Bevisst utsatt arbeid).
- `hent_tilgjengelige_malttyper()`s advarselstekst-unøyaktighet (se Kjente begrensninger over).
- Legacy humlelager sin separate maltprisbug (se Kjente begrensninger over) — bevisst ikke rørt, utenfor scope for denne rekken.

For øvrig dokumentert gjeld: se `docs/PROJECT_STATUS_JULI_2026.md` → "Teknisk gjeld" (sitert, ikke linje-for-linje reverifisert i denne økten for de punktene som ikke gjelder malt-variantarbeidet).

**Arkitektur**

`modules/` vs. `ui/`-grensen (se `docs/development/PROJECT_MAP.md`) er intakt gjennom hele Steg A–F6: verifisert i denne økten at `modules/malt_packaging.py` og `modules/smart_shopping_list.py` ikke importerer `streamlit` (ren Python, som dokumentert i begge filers egne moduldocstrings), og at all ny rendering (checkbox, eksakt-mål-instruks, advisory-visning) ligger utelukkende i `ui/smart_shopping_list_panel.py`. Ingen nye arkitekturelle avvik identifisert.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 10 (`4af0fcc` t.o.m. `1b3578b`, telt fra rett etter forrige snapshot-commit `cdb3d1f`) |
| Klar for release? | Nei — se "Ikke aktivert ennå" og de seks uavklarte lokale dataendringene under. Kodefundamentet er ferdig, men funksjonaliteten er ikke reelt brukbar før ekte Vestbrygg-variantdata er aktivert. |
| Klar for push? | Kodemessig: ja, ingen kjente blokkere for de 12 commitene som allerede er lokalt gjort. Praktisk: brukeren har eksplisitt bedt om at push avventes til etter den kontrollerte aktiveringen (se Aktiveringsrekkefølge) — ikke push før eksplisitt godkjenning per `docs/development/GIT_RULES.md`. |

## Ikke aktivert ennå (skille mellom kodeferdig og aktivert)

- Ekte Vestbrygg-barn-SKU-er er IKKE skrevet til `raw_data/malt_raw.json` gjennom den nye scraper-flyten (Steg F1) — scraperkoden er skrevet og enhetstestet, men aldri kjørt mot ekte, live Vestbrygg-sider i denne rekken.
- `data/master_malt.json` inneholder fortsatt INGEN faktiske varianter eller lagerstatus-data for noen malt — verifisert ved at de seks kjente lokale diffene (under) er de eneste endringene i denne filen, og ingen av dem stammer fra en ekte matcher-kjøring i denne rekken.
- Smart Handleliste har derfor ALDRI brukt variant-/lagerstatus-/eksakt-mål-/25kg-sperre-funksjonaliteten mot ekte Vestbrygg-data — kun mot fabrikerte testfixtures.
- Ingen kontrollert datamigrering er utført.
- Ingen ny datapakke er committet.
- De 12 lokale commitene (inkl. dette snapshotets forberedende arbeid) er IKKE pushet til `origin/master`.
- Den offentlige demoen (`kvernhaug-brygghus.streamlit.app`) er derfor IKKE redeployet med noen av disse endringene — den kjører fortsatt koden fra sist pushede commit (`44752e7`, jf. forrige snapshot).

## De seks kjente lokale dataendringene

Følgende seks filer har vært lokalt endret, uncommittet og urørt gjennom HELE Steg A–F6-rekken (bekreftet identiske ved hvert steg sin post-commit-verifisering):

- `data/master_gjaer_v2.json`
- `data/master_humle_v2.json`
- `data/master_malt.json`
- `raw_data/gjaer_raw.json`
- `raw_data/humle_raw.json`
- `raw_data/malt_raw.json`

Disse er **eksisterende, uavklarte lokale arbeidsendringer fra FØR Steg A–F6 startet** — de er IKKE en del av den frosne, committede kodebaselinen dette snapshotet dokumenterer, og de stammer IKKE fra noe arbeid i denne rekken. `raw_data/malt_raw.json` sin diff er allerede kjent og dokumentert i `docs/PROJECT_STATUS_JULI_2026.md` sin "Teknisk gjeld"-seksjon (en uavklart scrape-arbeidskopi — bl.a. et Bohemian Pilsner-produkt fanget med en annen variant/pakningsstørrelse enn dagens master).

Disse seks filene MÅ avklares (beholdes, committes separat, eller forkastes bevisst) FØR ny scraping kjøres som del av den planlagte aktiveringen — kjøres scraperen på nytt uten at diffen er avklart først, blandes gammel og ny endring sammen i samme fil og blir umulig å skille fra hverandre i ettertid. Se Aktiveringsrekkefølge, steg 1–3.

## Bevisst utsatt arbeid (åpne, kjente avgrensninger)

- **Hybrid med hele 25 kg-sekker + eksakt mål kun på restdelen** er ikke implementert. Dagens kode sperrer eksakt mål helt for enhver kombinasjon som inneholder en sekk (Steg F5) — den splitter IKKE kjøpet i en fast sekkedel og en eksakt restdel. Dette venter bevisst på avklaring fra Vestbrygg. Foreslått spørsmål (fra Steg F4-rapporten): *«Dersom en kunde bestiller én eller flere 25 kg-sekker sammen med mindre poser, kan restmengden i de mindre posene fortsatt bestilles til et eksakt mål via meldingsfeltet, uavhengig av sekkene?»*
- **`hent_tilgjengelige_malttyper()`** kan fortsatt omtale en maltform som tilgjengelig basert på rå variantliste, selv om alle variantene av den formen faktisk er utsolgt. Dette påvirker KUN advarselsteksten («flere maltformer tilgjengelig») — selve kjøpsanbefalingen er upåvirket, siden `_varianter_for_form()` allerede ekskluderer utsolgte varianter korrekt før noen kombinasjon bygges. Lav prioritet, bevisst ikke rettet.
- **Legacy humlelager/gammel handleliste** har en tidligere identifisert, separat maltprisbug knyttet til gamle, flate prisfelt (ikke variant-/lagerstatus-bevisst). Smart Handleliste er den korrekte, nye flyten som ikke har denne svakheten. Denne bugen rettes bevisst IKKE i dette snapshotet eller denne utviklingsrekken — den ligger i en modul denne rekken aldri har rørt.

## Aktiveringsrekkefølge (neste fase, IKKE påbegynt)

1. Avklar de seks eksisterende lokale dataendringene.
2. Bestem hvilke som skal beholdes, committes eller forkastes.
3. Sørg for en forståelig, ren Git-status før ny scraping.
4. Kjør kontrollert scraper.
5. Inspiser `raw_data/malt_raw.json`.
6. Kjør matcher.
7. Inspiser `data/master_malt.json` manuelt.
8. Kontroller varianter og lagerstatus mot kjente butikkprodukter.
9. Kjør full testsuite.
10. Kjør manuell Smart Handleliste-test med ekte oppskrift og Pantry.
11. Commit kun tilsiktede dataendringer.
12. Verifiser Demo Mode.
13. Vurder push først etter eksplisitt godkjenning.

Punkt 4 skal IKKE påbegynnes før punkt 1–3 er avklart — kjøres scraperen før de gamle, lokale datadiffene er avklart, blandes gammel og ny endring sammen i samme fil uten mulighet til å skille dem fra hverandre i ettertid.

## Kommentar

Dette snapshotet ble tatt fordi brukeren eksplisitt ba om det, som Steg F7 i en lengre, disiplinert utviklingsrekke (Steg A–F6) — nettopp for å fryse et referansepunkt rett før den første kontrollerte aktiveringen av ekte Vestbrygg-variant-/lagerstatusdata. Milepælen er avslutningen av et sammenhengende kodearbeid (matching → kjøpsresultat-kontrakt → variantmodell → lagerstatus → eksakt mål → 25 kg-sikkerhet → dokumentasjonsopprydding); neste fase er av en annen karakter (drift/datainnsamling/aktivering, ikke arkitektur-/kodearbeid), og et snapshot her gir et konkret sammenligningsgrunnlag dersom aktiveringen avdekker uforutsette problemer.
