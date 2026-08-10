# Project Snapshot — 2026-08-10 — Web-versjon: Bryggelærling/Bryggmester-runden ferdig

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-10 |
| Tid | 14:46 (lokal tid) |
| Versjon | Ikke versjonsnummerert (ingen `VERSION`-fil eller tilsvarende i repoet) |
| Git branch | `master` |
| Siste commit | `d974772` — "feat: legg til Bryggelærling/Bryggmester-moduser, stilveiledning, hjelpetekster og egendefinerte ingredienser i web-versjonen" (2026-08-10) |
| GitHub-status | `master` er 9 commits foran `origin/master` (ikke pushet) |

## Prosjektstatus

**Kort oppsummering**

Siden forrige snapshot ([2026-08-10_Web_V1_Pre_Deploy.md](2026-08-10_Web_V1_Pre_Deploy.md)) har web-versjonen fått to nye runder: først smakshjul (vanilla SVG), en rettelse av BJCP-metadata i selve kildekoden (`modules/style_engine.py`) og delt, deterministisk generert ingrediensdata mellom web og desktop (`scripts/generate_web_data.py`); deretter en større runde som la til to visningsmoduser (Bryggelærling/Bryggmester), veiledende "?"-hjelpetekster, en vennlig tre-nivås stilveiledning, egendefinerte ingredienser (malt/humle/gjær) med alfa-overstyring på biblioteks-humle, og JSON-import (eksport fantes fra før). Web-versjonen er funksjonelt ferdig for denne fasen, nettleser-testet, men **fortsatt ikke deployet**. Dette snapshotet fryser tilstanden rett før neste web-runde (Hjelp/FAQ, bryggedagsguide, brukeridentitet, utskriftsmaler).

**Nye milepæler**

Siden forrige snapshot — 3 commits (`dcb390d`, `d974772`, samt selve snapshot-commiten `5d318a2` for forrige snapshot):
- Smakshjul implementert som egen vanilla SVG-radarkomponent (`web/js/radar.js`), 18 akser, ingen ekstern lib/CDN — tegner poengene fra `flavor.js`.
- BJCP-metadatafeil rettet i kildekoden: `"Tradisjonelt Norsk Gårdsøl / Kveik"` og `"Tradisjonelt Norsk Juleøl"` var feilaktig klassifisert som offisielle BJCP-stiler i `modules/style_engine.py` — nå eksplisitt `bjcp_offisiell: False`, sammen med `"Historisk Wiesn-Märzen"`.
- Stilmatch-teksten omdøpt fra "BJCP-matching" til presist "stilmatching mot Kvernhaug Brygghus sitt stilbibliotek" gjennomgående.
- `scripts/generate_web_data.py` — nytt, deterministisk, stdlib-only script som regenererer `web/data/*.json` direkte fra desktop-appens masterdata og `style_engine.py`. Web har dermed ingen egen, manuelt vedlikeholdt ingrediensdatabase lenger.
- To visningsmoduser — **Bryggelærling** ("veiledet modus, lær mens du brygger") og **Bryggmester** ("full kontroll") — rent CSS-styrt, samme oppskrift og beregningsmotor i begge; modusbytte mister aldri data (verifisert i test).
- Delt hjelpepopover-komponent (`web/js/help.js`) med "?"-knapper på OG/FG/ABV/IBU/EBC/utgjæring/alfasyre/stilmatch/smakshjul — klikk/tap, ikke hover.
- Ny, vennlig tre-nivås stilveiledning (`web/js/veiledning.js`): "innenfor"/"litt utenfor"/"tydelig utenfor" i rolig språk, bygget oppå et lite, additivt per-felt-avvikstillegg i `style.js` (samme underliggende tall som scoringen, ingen ny beregning).
- Egendefinerte malt-, humle- og gjær-ingredienser samt alfa-overstyring på biblioteks-humle — løst uten å røre de allerede verifiserte beregningsmodulene (`calc.js`/`flavor.js`/`style.js`), via et midlertidig "effektivt" oppslagsobjekt bygget per beregning i `app.js`.
- JSON-import lagt til (fantes ikke før), rundtur-testet inkl. egendefinerte ingredienser.
- CSS-spesifisitetsbug funnet og fikset under testing: `[hidden]` ble overstyrt av en `display:flex`-regel, som gjorde alle egendefinert-skjemaene alltid synlige i stedet for skjulte til brukeren ba om dem.

**Status på hovedmoduler**

Uendret for Streamlit-appen siden forrige snapshot. For `web/` spesifikt:

| Del | Status |
|---|---|
| Oppskriftsbygger (OG/FG/ABV/IBU/EBC) | Ferdig, testet |
| Søkbare dropdown-felt | Ferdig, testet (touch/tastatur/desktop) |
| Stilmatch mot Kvernhaug-biblioteket (26 stiler) | Ferdig, numerisk verifisert mot Python |
| Smakshjul (visuelt) | Ferdig — vanilla SVG, live oppdatering |
| Bryggelærling/Bryggmester | Ferdig, testet (modusbytte mister aldri oppskriftsdata) |
| Hjelpetekster ("?"-knapper) | Ferdig, testet med mus, touch, Escape, klikk utenfor |
| Stilveiledning (tre nivåer) | Ferdig, testet i begge moduser |
| Egendefinerte ingredienser + alfa-overstyring | Ferdig, testet i beregning, lagring og JSON-eksport/import |
| Lagre/laste/eksport/import/print | Ferdig, testet |
| Hosting/deploy | Ikke startet |

**Kjente begrensninger**

- BJCP-biblioteket i web (`data/bjcp_styles.json`, 26 stiler) er identisk med — men ikke bredere enn — Kvernhaug-appens eksisterende stilbibliotek. Dekker **ikke** hele det offisielle BJCP 2021-stilheftet (~100 understiler). Uendret fra forrige snapshot, presist beskrevet i `web/README.md`.
- Ingen personlig gjenbruksbibliotek for egendefinerte ingredienser (bevisst utelatt som "nice-to-have" denne runden).
- Ingen mesketemperaturfelt i web ennå.
- Ingen egen Hjelp/How-to/FAQ-side, bryggedagsguide, bryggemetode- eller utstyrsspesifikke guider ennå — planlagt neste web-runde (se `docs/ROADMAP.md`).
- Ingen brukeridentitet (bryggernavn) i web ennå.
- Ingen egne utskriftsmaler for oppskrift/handleliste/bryggedag/bryggelogg i web ennå (dagens utskrift er den samme siden i print-CSS).
- Øvrige begrensninger uendret fra forrige snapshot (ingen delt kjøretid mellom Python og JS — manuelle porter må holdes i sync for hånd).

**Pågående arbeid**

Ingenting pågående i web-versjonen akkurat nå — denne runden er ferdig, testet og committet. Neste planlagte runde (Hjelp/FAQ, bryggedagsguide, brukeridentitet, utskriftsmaler) er beskrevet i `docs/ROADMAP.md`, men ikke påbegynt.

## Kode

**Tester**

Kjørt på nytt i dette snapshotet: `py -3 -m unittest discover -s tests` → **859 tester, 0 skipped, 0 errors, 0 failures**. (1 test flere enn forrige snapshots 858 — økningen kommer fra `tests/test_style_engine.py` sin oppdaterte `TestBjcpOffisiellKlassifisering`, lagt til i commit `dcb390d`.)

**Demo Mode**

Ikke påvirket — `web/` er fortsatt et helt separat produkt utenfor `config.py::DEMO_MODE`-arkitekturen. Ingen endring siden forrige snapshot.

**Dokumentasjon**

- `web/README.md` — oppdatert i samme commit (`d974772`): dokumenterer moduser, hjelpetekster, egendefinerte ingredienser, stilveiledning.
- `docs/development/PROJECT_MAP.md` — sjekket denne runden: har fortsatt en kort, riktig 4-linjers beskrivelse av `web/` og `scripts/` med henvisning videre til `web/README.md`. Ingen detaljert filliste å holde i sync (bevisst, per eksisterende mønster), så ingen endring nødvendig.
- `docs/ROADMAP.md` — oppdatert i denne økten (før dette snapshotet ble opprettet): web-bulletet under "Pågår / akseptansetesting" nevner nå moduser, hjelpetekster, stilveiledning, egendefinerte ingredienser, alfa-overstyring, JSON-import, og HEAD `d974772`. Neste web-runde lagt til som nytt punkt 6 under "Neste".
- `docs/PROJECT_STATUS_JULI_2026.md` — fortsatt punkt-i-tid fra 2026-07-28, ikke oppdatert (uendret vurdering fra forrige snapshot; gjelder primært Streamlit-appen, ikke web).
- Obsidian Vault (`C:\Vault\Kvernhaug Brygghus`) — oppdatert tidligere i dag: `System/Kvernhaug Brygghus App.md` fikk en ny "Web-versjon"-seksjon og fersk teknisk status; `System/Kvernhaug Handover.md` fikk oppdatert App-repo-avsnitt og en ny endringslogglinje.

**Vault**

Oppdatert i dag (se over) — først et eget dokumentasjonssteg, deretter dette snapshotet. `System/Kvernhaug Brygghus App.md` og `System/Kvernhaug Handover.md` reflekterer nå HEAD `d974772`, 859 tester og web-versjonens faktiske funksjonsomfang.

**Teknisk gjeld**

Uendret Python-side (se tidligere snapshots). Web-spesifikk gjeld, uendret eller presisert denne runden:
- Ingen delt kjøretid mellom Python og JS — `calc.js`/`flavor.js`/`style.js` er manuelle porter, må oppdateres for hånd ved endring i `modules/`. `veiledning.js` bygger videre på `style.js` sitt `felt_avvik`-tillegg (additivt, ikke en ny beregningskilde).
- `help.js`, `veiledning.js`, `radar.js` og `combobox.js` er egne web-komponenter uten Python-motstykke — ingenting å synkronisere for disse.
- Ingen ny teknisk gjeld identifisert utover det som allerede sto i forrige snapshot.

**Arkitektur**

`modules/` vs. `ui/`-grensen intakt (ingen Python-filer utenom `modules/style_engine.py`s metadatafiks og tilhørende testoppdatering er rørt i denne kommit-serien). `web/` forblir bevisst utenfor denne grensen som et frittstående, klientside-produkt. Egendefinerte ingredienser og alfa-overstyring er løst via et midlertidig "effektivt datasett" i `app.js` uten å endre de verifiserte beregningsmodulenes grensesnitt — ingen ny arkitektonisk kobling introdusert.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 3 (`dcb390d`, `d974772`, samt `5d318a2` som var selve forrige snapshot-commiten) |
| Klar for release? | Web-versjonen er funksjonelt ferdig og testet for denne runden, men **ikke** deployet — hosting/deploy er en egen, ikke igangsatt beslutning |
| Klar for push? | `master` er 9 commits foran `origin/master`; ikke pushet i denne økten |

## Kommentar

Tatt på brukerens eksplisitte forespørsel, rett etter at Bryggelærling/Bryggmester-runden (moduser, hjelpetekster, stilveiledning, egendefinerte ingredienser) ble committet, og rett etter at `docs/ROADMAP.md` ble brakt i sync med samme HEAD. Fryser en stabil tilstand før neste, større web-runde (Hjelp/FAQ, bryggedagsguide, brukeridentitet, utskriftsmaler) startes.
