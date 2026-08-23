# Kvernhaug Brygghus — Prosjektstatus (August 2026)

*Dato: 2026-08-23*
*Statusgrunnlag — siste kodecommit dette dokumentet ble skrevet mot: `beeb94c` (ikke nødvendigvis branch-HEAD: en dokumentasjonscommit kan strukturelt aldri pålitelig oppgi sin egen, endelige hash)*
*Testantall: 942 tester — 0 skipped, 0 errors, 0 failures (938 + 4 nav-kontrakttester fra P3B)*
*Python: 3.12.10 (repoets `.venv`)*

Dette dokumentet erstatter ikke `docs/PROJECT_STATUS_JULI_2026.md`, som beholdes som historikk. Det som er endret siden juli-statusen er først og fremst **web-versjonen**: den er lansert, og hjelpedelen er bygget kraftig ut.

---

## Arbeidskopi og remote

| Felt | Verdi |
|---|---|
| Aktiv arbeidskopi | `D:\Development\Kvernhaug Brygghus` |
| Remote (kanonisk) | `https://github.com/Joludvig/kvernhaug-brygghus.git` |
| Branch | `master` |
| HEAD ved skriving | `beeb94c` |
| Git-status | Ren, `master` == `origin/master` |

**Merk:** en eldre kopi finnes fortsatt under `C:\Users\jolud\OneDrive\Kvernhaug Brygghus`. Den er et ekte git-repo, men lå ved kontroll 2026-08-23 på `558cc0e` — 13 commits bak, uten Bryggeskole-arbeidet. Den skal **ikke** brukes som aktiv arbeidskopi. Ingen migrering eller opprydding er utført; dette er kun en statusnotis.

---

## Web — lansert

Web-versjonen (`web/`) er **deployet og live på `https://kvernhaugbrygghus.no`** (statisk hosting, Domeneshop).

- **Deploy** er en eksplisitt, manuell handling via `scripts/deploy_web.ps1` (interaktiv FTPS-innlogging, `-DryRun` tilgjengelig). Ingen CI/CD. Full deployflyt: `web/README.md`.
- **NO/EN**: norsk HTML er autoritativ kilde; `web/en/**` og `web/sitemap.xml` er 100 % generert av `scripts/generate_web_i18n_pages.py` og skal aldri håndredigeres. Nye sider må registreres i generatorens `PAGES`-liste.
- **SEO**: canonical/hreflang på alle sider, `sitemap.xml` (36 URL-er), `robots.txt`, utskriftssider `noindex` og utelatt fra sitemap.
- **Favicon**: fullt sett integrert, committet og live.

---

## Bryggeskole P0–P3B — ferdig

Et sammenhengende innholdsprogram som utvidet hjelpedelen fra 4 til **12 hjelpesider** gjennom Bryggeskole P0–P3B. P0–P3A er committet, pushet og live; P3B er ferdigstilt og verifisert, men ligger ved skriving som en uncommittet arbeidskopi (se «P3B — status» under).

| Runde | Innhold | Commit |
|---|---|---|
| P0 | Nybegynnerfundament | `e050b67` |
| P1A | Prosess, vann, etter gjæring | `744cd5e` |
| P1B | Gjær, karbonering, lagring, feilsøking | `708294e` |
| P2A | Avanserte meskemetoder | `d0e0aef` |
| P2B | Trykkgjæring, spunding, closed transfer | `e6831f4` |
| P2C | Sterke øl / high gravity | `cc986f0` |
| P2D | Gjærhøsting og gjenbruk | `a2a35b1` |
| P2E | Avansert vannkjemi | `d58c591` |
| P2F | Sensorikk og off-flavours | `f03be9f` |
| P3A | Humle i dybden + generell bryggesikkerhet | `beeb94c` |
| P3B | Gjærvalg + klaring/haze, gruppert hjelpe-nav | *uncommittet* |

(Favicon-runden `cee2a76` ligger mellom P2E og P2F.)

### De 12 hjelpesidene

`hjelp/index.html` (FAQ/ordliste-hub), `bryggedag.html`, `bryggemetoder.html`, `gjaervalg.html`, `trykkgjaering.html`, `sterke-ol.html`, `gjaerhosting.html`, `vannkjemi.html`, `humle.html`, `klaring.html`, `sensorikk.html`, `utstyr-brewzilla.html` — hver med engelsk speiling under `web/en/hjelp/`.

### Innholdsmønstre som gjelder

- **`hjelp/index.html` er kanonisk hub** for begrepsforklaringer (`#def-*`) og FAQ (`#faq-*`). Andre guidesider gir en kort kontekstuell omtale og lenker dit, i stedet for å gjenta definisjonen. Dette er den etablerte «god duplisering»-modellen og skal videreføres.
- **Faglig nyansering er et krav**, ikke en stilpreferanse: modeller (f.eks. Tinseth) omtales som modeller og ikke fysisk fasit; ingen universelle temperatur-/tid-/mengdefasiter; «kan/ofte/typisk/avhenger av» framfor absolutte påstander.
- **i18n-namespaces**: `hjelp.idx.*`, `hjelp.dag.*`, `hjelp.metoder.*`, `hjelp.brewzilla.*`, `hjelp.trykk.*`, `hjelp.sterkeOl.*`, `hjelp.gjaerhosting.*`, `hjelp.vannkjemi.*`, `hjelp.sensorikk.*`, `hjelp.humle.*`, `hjelp.gjaervalg.*`, `hjelp.klaring.*`. NO/EN må være symmetriske — generatoren feiler hardt ved asymmetri.

### Navigasjon (IA-beslutning)

**Historikk:** ved P3A var `hjelp-side-nav` flat med flex-wrap og 10 chips. Det ble den gangen vurdert reelt og bevisst beholdt, med den permanente beslutningen at gruppering skulle vurderes på nytt rundt side 11–12.

**Nå gjennomført ved side 12.** `hjelp-side-nav` er gruppert i **KOM I GANG** (Hjelp & FAQ, Bryggedag, Bryggemetoder), **BRYGGMESTER** (Gjærvalg, Trykkgjæring, Sterke øl, Gjærhøsting, Vannkjemi, Humle, Klaring, Sensorikk) og **UTSTYR** (BrewZilla). Gruppene speiler appens egne to modi (Bryggelærling/Bryggmester). Implementasjonen er ren HTML/CSS uten JS — `.hjelp-nav-gruppe` med `.hjelp-nav-gruppe-tittel` og `.hjelp-nav-lenker` inne i den eksisterende flex-wrap-nav-en; chip-reglene (padding, font-size, `min-height: 44px`) er uendret.

**Responsiv flattening under 900 px.** Gruppetitlene kostet for mye vertikal plass på smale skjermer (målt 293 px nav / 4 rader ved 768 px og 449 px / 7 rader ved 375 px, som dyttet første innhold under folden på en 375×667-telefon). Én media query under hjelpesidenes etablerte 900 px-brekkpunkt skjuler gruppetitlene og lar chipsene flyte ut som én wrappende rad (`display: contents`). Målt: 768 px 293 → 164 px, 375 px 449 → 320 px, hovedinnholdet 129 px lenger opp i begge. Desktop uendret.

Kontrakten er låst med fire nav-tester i `tests/test_generate_web_i18n_pages.py`: alle hjelpesider skal være representert i nav-en, hver gruppe skal ha i18n-merket tittel, og nøyaktig én aktiv chip skal peke på siden selv — også i den genererte EN-speilingen.

---

## Bryggeskole — beslutningsstatus

**Gap Audit V1** (utført før P3A) konkluderte:

- Fundament: **COMPLETE**
- Større innholdshull: **NEI**
- Retning: **B — én til to målrettede runder**, ikke fortsatt storstilt innholdsbygging

P3A var den første av disse rundene og lukket de to høyest prioriterte hullene (humle i dybden, generell sikkerhet utover trykk).

### P3B — gjennomført

P3B var den andre og siste av de målrettede rundene, og er **gjennomført**. Den er ikke lenger en kandidat.

| Del | Innhold |
|---|---|
| Gjærvalg (`hjelp/gjaervalg.html`) | Hva stammen faktisk påvirker, ale/lager/kveik, utgjæring (oppgitt vs. faktisk FG), flokkulering, ester og fenol/POF, alkoholtoleranse, temperaturarbeidsområde, tørr vs. flytende gjær, pitch, beslutningsflyt for stammevalg, lesing av produsentark, trykk og gjenbruk, feilsøking |
| Klaring (`hjelp/klaring.html`) | Hva «klart øl» betyr, haze-kilder, hot/cold break, trub, whirlpool, kettle finings (Irish moss/Whirlfloc), cold crash, gelatin og andre finings, chill haze vs. permanent haze, haze over tid, klarhet vs. stil, kobling til gjærvalg, feilsøking, klaringsplan |
| Nav-struktur | Gruppering KOM I GANG / BRYGGMESTER / UTSTYR gjennomført ved side 12 — se «Navigasjon» over |
| Responsiv justering | Flattening under 900 px etter målt nav-høyderegresjon på tablet/mobil |

Nøkkeltall etter P3B: `PAGES` 17 → 19, `sitemap.xml` 32 → 36 URL-er, i18n 1586 NO / 1586 EN (symmetrisk), testbaseline 942/942. Visuell regresjon kjørt i Chromium 151 + Firefox 153 × 1920/1280/900/768/375 px: 0 overflow, 0 klipping, 0 konsollfeil.

**Lavere prioritet / backlog (uendret):** maltforståelse i dybden, emballering/fat i dybden, servering/lagring, prosesseffektivitet nedbrutt.

> **Permanent status:** Med P3B ferdig er begge de målrettede rundene Gap Audit V1 pekte ut gjennomført. Bryggeskolen går nå over til struktur, polish og brukertesting. Terskelen for nye hjelpesider er høy — flere sider er ikke automatisk bedre, og en eventuell side 13 utløser samtidig en ny vurdering av nav-strukturen.

---

## Produktgrenser (uendret)

Kvernhaug Brygghus er **ikke** en Brewfather-klone, kommersiell bryggeriplattform, sosial plattform, automatisk AI-oppskriftsgenerator, cloud-first system eller IoT-plattform.

Kjernefilosofi: **plan → brew → observe → learn → next brew**

| Flate | Ansvar |
|---|---|
| Desktop (Streamlit) | Planlegging, design, masterdata, beregning |
| Web (statisk) | Bryggedag, gjennomføring, læring/hjelp, opplevelse/logging |
| Filer | Bro mellom flatene |

Core Contract (`.kbhrecipe`, `.kbhbrew`, passthrough-law, kanoniske enheter, eierskapsgrenser): `docs/development/KBH_CORE_CONTRACT.md`.

---

## Kjent dokumentasjonsgjeld — lukket 2026-08-23 (Documentation Stabilization V1)

Gjelden slik den sto ved statusskrivingen:

- **`web/CHANGELOG.md`** dekket rundene til og med Runde 25C (2026-08-15), men ikke favicon-runden eller Bryggeskole P0–P3A.
- **`web/README.md`** beskrev fortsatt bare de fire opprinnelige hjelpesidene og det opprinnelige i18n-namespace-settet, og hadde utdaterte sidetall for generator/sitemap/canonical.

Begge ligger under `web/` og ble bevisst ikke endret i den første dokumentasjonsrunden 2026-08-23, som hadde eksplisitt krav om null diff i `web/`. De ble deretter lukket i en egen, autorisert dokumentasjonsrunde samme dag: `web/CHANGELOG.md` fikk én kompakt samlepost for lansering, favicon og Bryggeskole P0–P3A, og `web/README.md` fikk oppdatert hjelpestruktur (10 sider), i18n-namespaces og generator-/sitemap-tall. Ingen funksjonell web-endring.

---

## Desktop

Ingen endringer i desktop-appen (`app.py`, `modules/`, `ui/`) i august-arbeidet utover `2a9da84` (path-uavhengig app-launcher). Juli-statusens beskrivelse av moduler, kjente svakheter og teknisk gjeld gjelder fortsatt — se `docs/PROJECT_STATUS_JULI_2026.md`.

Se `docs/ROADMAP.md` for full roadmap.
