# Project Snapshot — 2026-08-10 — Web Runde 6 ferdig, før pre-deploy-vurdering

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-10 |
| Tid | 15:29 (lokal tid, commit-tidspunkt) |
| Versjon | Ikke versjonsnummerert (ingen `VERSION`-fil eller tilsvarende i repoet) |
| Git branch | `master` |
| Siste commit | `14668af` — "feat: legg til hjelp/bryggehåndbok, brukeridentitet og profesjonelle utskrifter i web-versjonen" (2026-08-10) |
| GitHub-status | `master` er 11 commits foran `origin/master` (ikke pushet) |

## Prosjektstatus

**Kort oppsummering**

Siden forrige snapshot ([2026-08-10_Web_Laerling_Mester_Ferdig.md](2026-08-10_Web_Laerling_Mester_Ferdig.md)) har web-versjonen fått en full "Web Runde 6": en egen Hjelp & bryggehåndbok, "?→Les mer"-lenker fra hjelpepopoverne, brukeridentitet på selve oppskriften, og fire egne, profesjonelle utskriftsdokumenter i stedet for et rått sideprint. En etterfølgende, egen kvalitetskontroll rettet proveniensen i BrewZilla-guiden slik at Kvernhaugs egne beregningsstandarder aldri fremstår som offisielle produsentspesifikasjoner. Web-versjonen er funksjonelt ferdig for denne fasen og testet, men **fortsatt ikke deployet**. Dette snapshotet fryser tilstanden rett før en planlagt, egen "Pre-deploy / lanseringsklar"-vurdering.

**Nye milepæler**

Siden forrige snapshot — 2 commits (`400c8df`, `14668af`):
- Egen Hjelp & bryggehåndbok (`web/hjelp/`, 4 nye sider): `index.html` (Kom i gang, 13 begrepsforklaringer, ingredienshjelp, 10-spørsmål FAQ), `bryggedag.html` (generell 15-stegs all-grain-bryggedag med hva/hvorfor/følg med på/vanlige feil per steg), `bryggemetoder.html` (BIAB/vanlig all-grain/alt-i-ett), `utstyr-brewzilla.html` (første utstyrsguide).
- "?"-hjelpeknappene har fått en "Les mer →"-lenke (`help.js`) som åpner riktig hjelpeemne i ny fane — oppskriften i byggeren forstyrres aldri.
- Brukeridentitet: Ølnavn (omdøpt fra "Oppskriftsnavn"), Brygger, valgfritt Bryggeri og valgfritt Notater-felt, lagret på selve oppskriften (localStorage + JSON) og som en egen, lett lokal preferanse som forhåndsutfyller nye oppskrifter uten å overstyre lastede/importerte.
- Ny print-arkitektur (`web/js/print.js`): fire egne dokumentmaler (Oppskriftsark, Handleliste, Bryggedagsark, Bryggelogg) bygget fra live oppskriftsdata, vist via `body[data-utskrift]` + `@media print` — erstatter det tidligere rå sideprintet. Handlelisten er bevisst nøytral (ingen butikk/pris/lagerstatus/pantry). Brukerens ølnavn/brygger/bryggeri har visuell prioritet; Kvernhaug Brygghus vises kun diskret i en fotnote.
- Egen kvalitetskontroll (samme dag, etter implementasjon): BrewZilla-guidens tekniske tall ble gjennomgått og omklassifisert i fire tydelige kategorier — faktisk produktegenskap (kjelekapasitet 35 L), Kvernhaug-standard for beregning (fordampning, dead space), generell bryggeforutsetning (meskeforhold, kornabsorpsjon) og Kvernhaugs praktiske anbefaling (maks pre-boil ~30 L) — samt en egen "ikke verifisert ennå"-seksjon. En sidefunnet visningsfeil (feilaktig gjenbruk av en print-only CSS-klasse på skjermtabeller) ble også rettet.

**Status på hovedmoduler**

Uendret for Streamlit-appen siden forrige snapshot. For `web/` spesifikt:

| Del | Status |
|---|---|
| Oppskriftsbygger (OG/FG/ABV/IBU/EBC) | Ferdig, testet |
| Bryggelærling/Bryggmester, søkbare felt, smakshjul, stilmatch | Ferdig, testet (uendret siden forrige snapshot) |
| Egendefinerte ingredienser + alfa-overstyring | Ferdig, testet (uendret siden forrige snapshot) |
| Hjelp & bryggehåndbok (`hjelp/`) | Ferdig, testet — 4 sider, navigasjon, anchors, "Les mer"-integrasjon |
| Brukeridentitet (ølnavn/brygger/bryggeri/notater) | Ferdig, testet — oppskrift + preferanse + JSON-rundtur |
| Fire utskriftsdokumenter | Ferdig, testet i print-emulering — riktig innhold, riktig skjuling, nullstilles ved afterprint |
| BrewZilla-guidens proveniens | Rettet og testet på nytt etter egen kvalitetskontroll |
| Hosting/deploy | Ikke startet |

**Kjente begrensninger**

- Ikke deployet/hostet ennå; ingen kobling til `KvernhaugBrygghus.no`.
- Ikke full BJCP 2021 — kun det eksisterende 26-stils Kvernhaug-biblioteket (uendret).
- Ingen personlig gjenbruksbibliotek for egendefinerte ingredienser (bevisst utelatt, uendret).
- Ingen mesketemperaturfelt i web (uendret).
- Bryggeloggen er foreløpig kun et utskrivbart papirskjema — ingen digital lagring av faktiske bryggeresultater (det er en egen, allerede planlagt "Bryggelogg V1"-funksjon i roadmapen for desktop-appen, ikke del av web-arbeidet).
- Ingen kobling mellom en fremtidig Equipment Profile og utstyrsguiden.
- BrewZilla-guidens kontrollpanel-/rengjørings-/quirk-informasjon er eksplisitt markert "ikke verifisert ennå" og trenger ekstern, verifisert dokumentasjon før publisering som fakta.

**Pågående arbeid**

Ingenting pågående i web-versjonen akkurat nå — Runde 6 er ferdig, testet og committet. Neste planlagte fase er en egen "Pre-deploy / lanseringsklar"-vurdering (funksjonsomfang for V1, innholdskvalitet i Hjelp/bryggehåndbok, datakvalitet malt/humle/gjær, stilbibliotek-dekning, visuell sluttpolish, utskriftskontroll med ekte oppskrifter, personvern-/cookievurdering, hosting/opplasting, `KvernhaugBrygghus.no`, produksjonstest etter deploy) — beskrevet i `docs/ROADMAP.md`, men **ikke påbegynt**.

## Kode

**Tester**

Kjørt på nytt i dette snapshotet: `py -3 -m unittest discover -s tests` → **859 tester, 0 skipped, 0 errors, 0 failures** (uendret antall — ingen Python-kode er rørt i Runde 6, kun `web/` og dokumentasjon).

**Demo Mode**

Ikke påvirket — `web/` er fortsatt et helt separat produkt utenfor `config.py::DEMO_MODE`-arkitekturen. Ingen endring siden forrige snapshot.

**Dokumentasjon**

`web/README.md` og `docs/ROADMAP.md` er oppdatert i takt med Runde 6 (nye seksjoner for brukeridentitet, print-arkitektur, Hjelp & bryggehåndbok, samt en presis firedelt beskrivelse av BrewZilla-guidens proveniensskille). `docs/development/PROJECT_MAP.md` er vurdert og funnet fortsatt korrekt uendret — den korte web/-beskrivelsen peker allerede videre til `web/README.md` uten å liste enkeltfiler. `docs/PROJECT_STATUS_JULI_2026.md` er fortsatt punkt-i-tid fra 2026-07-28, uendret vurdering.

**Vault**

Oppdatert i samme økt som dette snapshotet: `System/Kvernhaug Brygghus App.md` fikk en ny "Web Runde 6"-underseksjon (Hjelp & bryggehåndbok, BrewZilla-proveniens, brukeridentitet, utskrifter, oppdaterte kjente begrensninger, milepæl-commit-tabell) og fersk teknisk status (HEAD `14668af`, 859 tester, 11 commits foran origin). `System/Kvernhaug Handover.md` fikk oppdatert App-repo-avsnitt og en ny endringslogglinje.

**Teknisk gjeld**

Uendret Python-side. Web-spesifikk gjeld, uendret eller presisert denne runden:
- Ingen delt kjøretid mellom Python og JS (uendret, dokumentert i `web/README.md`).
- `HJELP_TEKSTER.lesMer`-ankrene i `help.js` må holdes i sync manuelt med anchor-IDene i `hjelp/index.html` — ny, dokumentert avhengighet denne runden.
- Ingen ny uventet teknisk gjeld utover det som allerede var kjent.

**Arkitektur**

`modules/` vs. `ui/`-grensen intakt (ingen Python-filer rørt denne runden). `web/` forblir bevisst utenfor denne grensen som et frittstående, klientside-produkt. Print-arkitekturen (skjulte `.utskrift-dokument`-containere + `body[data-utskrift]`) og Hjelp-sidene (egne statiske HTML-filer under `web/hjelp/`, delt `style.css`) er begge additive, klientside-only mønstre uten nye avhengigheter eller arkitektoniske koblinger til Python-siden.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 2 (`400c8df`, `14668af`) |
| Klar for release? | Web-versjonen er funksjonelt ferdig og testet for denne runden, men **ikke** deployet — en egen pre-deploy/lanseringsklar-vurdering gjenstår før offentlig lansering |
| Klar for push? | `master` er 11 commits foran `origin/master`; ikke pushet i denne økten |

## Kommentar

Tatt på brukerens eksplisitte forespørsel, rett etter at Web Runde 6 (Hjelp & bryggehåndbok, "?→Les mer", brukeridentitet, fire utskriftsdokumenter) og en påfølgende BrewZilla-proveniensrettelse ble committet. Fryser en stabil tilstand før en egen, ikke påbegynt "Pre-deploy / lanseringsklar"-vurdering — dette snapshotet dekker altså sluttpunktet for funksjonell web-utvikling før den vurderingen starter, ikke selve lanseringen.
