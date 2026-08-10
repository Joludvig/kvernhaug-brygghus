# Project Snapshot — 2026-08-10 — Web-versjon V1 klar, før hosting/deploy

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-10 |
| Tid | 12:20 (lokal tid) |
| Versjon | Ikke versjonsnummerert (ingen `VERSION`-fil eller tilsvarende i repoet) |
| Git branch | `master` |
| Siste commit | `1dcba53` — "feat: legg til BJCP-stilmatch og søkbare felt i web-versjonen, redesign etter Master V1-palett" (2026-08-10) |
| GitHub-status | `master` er 6 commits foran `origin/master` (ikke pushet) |

## Prosjektstatus

**Kort oppsummering**

Siden forrige snapshot ([2026-08-10_Pre_Web_Versjon.md](2026-08-10_Pre_Web_Versjon.md)) er den forenklede, offentlige web-versjonen (`web/`) bygget fra bunnen i to trinn: først en grunnleggende oppskriftsbygger (OG/FG/ABV/IBU/EBC, localStorage, print/eksport), deretter en test-/polish-runde som la til full BJCP-stilmatch, søkbare dropdown-felt og visuell redesign etter Master Design V1-paletten. Ingen hosting/deploy er satt opp ennå — dette snapshotet fryser tilstanden rett før den beslutningen tas, og rett etter en kartlegging av tre åpne spørsmål (smakshjul-status, faktisk BJCP-dekning, ingrediens-masterdata-felt) som bevisst ikke er besvart med kodeendringer ennå.

**Nye milepæler**

Siden forrige snapshot — 2 commits (`e55504a`, `1dcba53`):
- Web-versjon V1: statisk HTML/CSS/vanilla JS, oppskriftsbygger med live OG/FG/ABV/IBU/EBC, localStorage-lagring, print/JSON-eksport.
- Full port av Style Engine (`modules/style_engine.py`) og Flavor Engine-poengberegningen (`modules/flavor_engine.py`) til `web/js/style.js`/`web/js/flavor.js`, numerisk parallelltestet mot Python-kilden (identisk resultat på tre signatur-scenarier).
- Ny gjenbrukbar søkbar dropdown-komponent (`web/js/combobox.js`) for malt/humle/gjær/stil.
- Visuell redesign av `web/` etter Master Design V1-paletten.
- Reell nettleser-testing (Playwright/Chromium, installert lokalt for testing — ikke i `requirements.txt`): full brukerflyt, responsivt design på desktop/nettbrett/mobil, 0 konsoll-/sidefeil. Ett print-CSS-avvik funnet og fikset (mørke inputfelt/stilkort uleselige på hvitt papir).

**Status på hovedmoduler**

Uendret for Streamlit-appen siden forrige snapshot (se der for full status). For `web/` spesifikt:

| Del | Status |
|---|---|
| Oppskriftsbygger (OG/FG/ABV/IBU/EBC) | Ferdig, testet |
| Søkbare dropdown-felt | Ferdig, testet (touch/tastatur/desktop) |
| BJCP-stilmatch (numerisk + sensorisk + signatur) | Ferdig, numerisk verifisert mot Python |
| Smakshjul/radardiagram (visuelt) | **Ikke implementert** — kun den underliggende poeng-beregningen (`flavor.js`) finnes, brukt internt av stilmatchen. Ingen radar-/spider-graf i UI-et. Avklart eksplisitt med bruker 2026-08-10, bevisst ikke bygget videre uten avtale. |
| Lagre/laste/eksport/print | Ferdig, testet |
| Hosting/deploy | Ikke startet |

**Kjente begrensninger**

- Smakshjulet er ikke visuelt implementert i web-versjonen (se over).
- BJCP-biblioteket i web (`data/bjcp_styles.json`, 26 stiler) er identisk med — men ikke bredere enn — Kvernhaug-appens eksisterende stilbibliotek. Dette dekker **ikke** hele det offisielle BJCP 2021-stilheftet (som har rundt 100 understiler på tvers av ~34 kategorier); hele familier (sure øl, saison/belgisk utover Witbier/Dubbel/Tripel, barleywine/sterke ale, amerikansk lager/cream ale, brown/scotch ale, øvrige hveteøl-stiler, frukt-/krydder-/trelagrede spesialøl) mangler helt. Se sluttrapport i samtalen 2026-08-10 for full liste.
- `web/data/malt.json`/`humle.json`/`gjaer.json` er et engangs-ekstrahert, kuratert utdrag av masterdataene (kun kalkulasjons-/smaksrelevante felt) — **ikke** samme sannhetskilde som desktop-appen leser direkte. Kartlagt i detalj 2026-08-10; ingen endring gjort ennå (bevisst, etter eksplisitt instruks om å ikke gjøre større endringer før videre avklaring).
- Øvrige begrensninger uendret fra forrige snapshot (Belgisk Witbier-numerisk-overlapp, ingen automatisk pH-modell, legacy humlelager usynkronisert).

**Pågående arbeid**

- Avventer brukerens beslutning om: (1) om/hvordan smakshjulet skal visualiseres i web, (2) hvordan "BJCP-dekning" skal kommuniseres presist i produktteksten, (3) om/hvordan ingrediens-masterdata skal konsolideres til én delt sannhetskilde mellom desktop og web. Ingen av delene er implementert — kun undersøkt og rapportert.
- Hosting/deploy for web-versjonen er ikke startet.

## Kode

**Tester**

Kjørt på nytt i dette snapshotet: `py -3 -m unittest discover -s tests` → **858 tester, 0 failures/errors** (uendret antall fra forrige snapshot — ingen Python-kode er rørt i denne runden, kun `web/` og dokumentasjon).

**Demo Mode**

Ikke påvirket — `web/` er fortsatt et helt separat produkt utenfor `config.py::DEMO_MODE`-arkitekturen. Ingen endring siden forrige snapshot.

**Dokumentasjon**

`web/README.md`, `docs/ROADMAP.md` og `docs/development/PROJECT_MAP.md` er oppdatert i takt med kodeendringene i denne runden. `docs/PROJECT_STATUS_JULI_2026.md` er fortsatt punkt-i-tid fra 2026-07-28 og ikke oppdatert (uendret vurdering fra forrige snapshot).

**Vault**

Ikke undersøkt i dette snapshotet — `C:\Vault\Kvernhaug Brygghus` ble ikke åpnet.

**Teknisk gjeld**

Uendret Python-side (se forrige snapshot). Ny, web-spesifikk gjeld lagt til denne runden:
- Ingen delt kjøretid mellom Python og JS — `web/js/calc.js`, `web/js/flavor.js`, `web/js/style.js` er manuelle porter som må oppdateres for hånd ved endring i `modules/calculations.py`/`flavor_engine.py`/`style_engine.py`. Dokumentert i `web/README.md`.
- `web/data/*.json` er separate, kuraterte kopier av masterdataene — ikke én delt sannhetskilde. Eksplisitt flagget av bruker 2026-08-10 som noe som bør konsolideres før web vokser videre.
- Smakshjul-visualisering gjenstår (se over).

**Arkitektur**

`modules/` vs. `ui/`-grensen intakt (ingen Python-filer rørt denne runden). `web/` forblir bevisst utenfor denne grensen som et frittstående, klientside-produkt.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 2 (`e55504a`, `1dcba53`) |
| Klar for release? | Web-versjonen er funksjonelt testet, men **ikke** klar for offentlig deploy før de tre avklaringspunktene (smakshjul, BJCP-dekningstekst, ingrediensdata) er tatt stilling til |
| Klar for push? | `master` er 6 commits foran `origin/master`; ikke pushet i denne økten |

## Kommentar

Tatt på brukerens eksplisitte forespørsel, rett før hosting/deploy-beslutningen for web-versjonen — og rett etter at bruker ba om en presis kartlegging av tre uavklarte punkter (smakshjul, BJCP-dekning, ingrediens-masterdata) fremfor å gå videre. Fryser tilstanden slik den er *før* noen av de tre punktene eventuelt følges opp med kode.
