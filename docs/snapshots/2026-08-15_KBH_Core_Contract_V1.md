# Project Snapshot — 2026-08-15 — KBH Core Contract V1

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-15 |
| Tid | 23:10 (lokal tid) |
| Versjon | Ingen versjonskonstant finnes i prosjektet (verken desktop eller web) |
| Git branch | master |
| Siste commit | `bfe3f1fb8487c0b4029c9d92d41768e39d7b4ff0` — "feat(desktop): add KBH recipe export workflow" |
| GitHub-status | Pushet — `origin/master` = `bfe3f1f`, ingen lokale commits foran remote |

## Prosjektstatus

**Kort oppsummering**

Streamlit-siden (desktop) kan nå eksportere en oppskrift som en portabel
`.kbhrecipe`-fil, i tråd med en ny, eksplisitt datakontrakt
(`docs/development/KBH_CORE_CONTRACT.md`). Dette er første fysiske del av
filbroen mellom Streamlit (oppskriftslaboratorium) og web (bryggegjennomføring)
— kun eksportretningen, ingen import, ingen `.kbhbrew`, ingen migrering av
eksisterende oppskrifter.

**Nye milepæler** (Runde 26D–26F)

- KBH Core Contract V1 etablert: `docs/development/KBH_CORE_CONTRACT.md`
  (versjonert, "Status: Active") — definerer `.kbhrecipe`-formatet,
  hviteliste-prinsippet, enheter/normalisering, identitetspolicy
  (`recipeId` vs. `originRecipeId`) og passthrough-loven for ukjente felt.
- `modules/kbh_contract.py` etablert — ren, testbar oversetter (ingen
  Streamlit-avhengighet, ingen disk-I/O): `recipe_to_kbhrecipe_payload()`
  og `bygg_kbhrecipe_konvolutt()`.
- Streamlit-eksport til `.kbhrecipe` fungerer i praksis: ny knapp
  "📦 Eksporter KBH-oppskrift (.kbhrecipe)" i `ui/recipe_card.py`, bygger
  JSON i minnet og tilbyr den via `st.download_button` — ingen skriving
  til disk på serversiden.
- 929 tester passerer (full suite, kjørt på nytt for dette snapshotet —
  se "Tester" under).
- Ingen web-endringer i disse rundene — `web/` er urørt av 26D–26F.

**Status på hovedmoduler**

Ingen nyere `docs/PROJECT_STATUS_*.md` finnes enn
`docs/PROJECT_STATUS_JULI_2026.md` (juli 2026) — den dekker ikke dette
arbeidet og er ikke oppdatert som del av dette snapshotet (se "Kjente
begrensninger").

**Kjente begrensninger**

- Ingen ny `docs/PROJECT_STATUS_AUGUST_2026.md` er opprettet — status-
  laget mellom `docs/PROJECT_STATUS_JULI_2026.md` og dagens kode har et
  dokumentasjonshull for hele august (både web sitt i18n-/enhets-/
  pantry-/kbhbrew-arbeid OG denne KBH Core Contract-milepælen).
- Ingen `recipe_id`/`originRecipeId` lagres eller tildeles ennå —
  identitetspolicyen i kontraktens §6/§7 er kun BESKREVET, ikke
  implementert. En re-eksport av samme oppskrift genererer i dag ingen
  stabil, gjenkjennbar identitet på web-siden.
- Ingen importvei finnes på web for `.kbhrecipe` fra Streamlit — kun
  eksport er bygget. En bruker kan laste ned filen, men web har ingen
  UI som leser den tilbake fra denne kilden ennå.
- Samme "carry-over"-hull som identifisert tidligere i KBH-broarbeidet
  (`web/js/app.js::samleOppskrift()`) er ikke rettet — vann-/
  prosessdata i en importert fil ville fortsatt gått tapt ved første
  lagring i web. Ikke undersøkt på nytt i dette snapshotet, kun videreført
  som kjent, uløst funn.

**Pågående arbeid**

Ingenting uferdig eller halvveis committet — `git status` er ren og
`origin/master` er synkronisert. Neste steg i KBH-broen (import til web,
`.kbhbrew`-kobling) er ikke påbegynt.

## Kode

**Tester**

`py -3 -m unittest discover -s tests -b` — kjørt på nytt for dette
snapshotet: **929 tester, OK** (45.4s). Ingen feil, ingen skip.

**Demo Mode**

Ikke undersøkt i full bredde for dette snapshotet (ingen endring i
Demo Mode-dekningen fra forrige kjente tilstand er gjort av 26D–26F).
Den nye eksportknappen skriver aldri til disk (kun
`st.download_button` med data generert i minnet) og er derfor ikke
lagt bak en `DEMO_MODE`-sjekk — speiler samme mønster som den
eksisterende A4-eksportknappen i samme panel, som heller ikke er gatet.

**Dokumentasjon**

`docs/development/KBH_CORE_CONTRACT.md` er ny og i sync med koden
(kontrakten ble skrevet først, adapteren implementert deretter, i
samme rundeserie). CLAUDE.md er ikke endret. Ingen andre
`docs/development/`-filer er oppdatert til å nevne kbh_contract.py.

**Vault**

Ikke oppdatert. `C:\Vault\Kvernhaug Brygghus\System\Kvernhaug
Handover.md` og `...\Kvernhaug Brygghus App.md` hadde
`LastWriteTime` 2026-08-12 — tre dager før denne milepælen — og
inneholder ingen referanse til KBH Core Contract, `.kbhrecipe`-
eksport eller Runde 26D–26F (bekreftet i forrige rundes
synk-sjekk, ikke re-verifisert på nytt her).

**Teknisk gjeld**

Ny gjeld lagt til av 26D–26F (ingen av disse var "ikke gjør"-punkter
i rundene — de er bevisste, dokumenterte utsettelser):
- Ingen `recipe_id`-tildeling/-persistens (kontraktens §6 beskriver
  løsningen, men den er ikke bygget).
- Ingen web-side import av `.kbhrecipe` fra Streamlit.
- Ingen retting av carry-over-hullet i `web/js/app.js` for vann/
  prosessdata ved re-lagring i web.

**Arkitektur**

Arkitekturgrensen er intakt: `modules/kbh_contract.py` importerer
ikke Streamlit, gjør ingen disk-I/O og har ingen sideeffekter — kun
UI-koblingen ligger i `ui/recipe_card.py`, som forventet av
`.claude/rules/desktop.md`. Ingen avvik siden forrige snapshot.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 32 commits (`43ea94b`..`bfe3f1f`) — hvorav kun den siste (`bfe3f1f`) er del av 26D–26F. De øvrige 31 er separat web-arbeid (i18n/engelsk web, enhetsvalg, pantry, kbhbrew-grunnlag, bryggeloggUX m.m.), allerede dekket av `web/CHANGELOG.md` og utenfor dette snapshotets fokus. |
| Klar for release? | Ikke aktuelt — ingen releaseprosess er trigget av denne milepælen alene. |
| Klar for push? | Allerede pushet — `origin/master` = `bfe3f1f`. |

## Kommentar

Snapshotet tas ved avslutning av Runde 26F (26F.6 — "avsluttende
synkronisering") for å fryse KBH Core Contract V1-milepælen før
prosjektet parkeres: kontrakten, den rene adapteren og
Streamlit-eksportknappen er alle committet, testet (929/929) og
pushet. Bevisst avgrenset til 26D–26F selv om 31 andre commits landet
i samme vindu — se "Antall commits siden forrige snapshot".
