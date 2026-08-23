# Kvernhaug Brygghus — Prosjektstatus (August 2026)

*Dato: 2026-08-23*
*Statusgrunnlag — siste kodecommit dette dokumentet ble skrevet mot: `beeb94c` (ikke nødvendigvis branch-HEAD: en dokumentasjonscommit kan strukturelt aldri pålitelig oppgi sin egen, endelige hash)*
*Testantall: 938 tester — 0 skipped, 0 errors, 0 failures*
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
- **SEO**: canonical/hreflang på alle sider, `sitemap.xml` (32 URL-er), `robots.txt`, utskriftssider `noindex` og utelatt fra sitemap.
- **Favicon**: fullt sett integrert, committet og live.

---

## Bryggeskole P0–P3A — ferdig og live

Et sammenhengende innholdsprogram som utvidet hjelpedelen fra 4 til **10 hjelpesider**.

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

(Favicon-runden `cee2a76` ligger mellom P2E og P2F.)

### De 10 hjelpesidene

`hjelp/index.html` (FAQ/ordliste-hub), `bryggedag.html`, `bryggemetoder.html`, `trykkgjaering.html`, `sterke-ol.html`, `gjaerhosting.html`, `vannkjemi.html`, `sensorikk.html`, `humle.html`, `utstyr-brewzilla.html` — hver med engelsk speiling under `web/en/hjelp/`.

### Innholdsmønstre som gjelder

- **`hjelp/index.html` er kanonisk hub** for begrepsforklaringer (`#def-*`) og FAQ (`#faq-*`). Andre guidesider gir en kort kontekstuell omtale og lenker dit, i stedet for å gjenta definisjonen. Dette er den etablerte «god duplisering»-modellen og skal videreføres.
- **Faglig nyansering er et krav**, ikke en stilpreferanse: modeller (f.eks. Tinseth) omtales som modeller og ikke fysisk fasit; ingen universelle temperatur-/tid-/mengdefasiter; «kan/ofte/typisk/avhenger av» framfor absolutte påstander.
- **i18n-namespaces**: `hjelp.idx.*`, `hjelp.dag.*`, `hjelp.metoder.*`, `hjelp.brewzilla.*`, `hjelp.trykk.*`, `hjelp.sterkeOl.*`, `hjelp.gjaerhosting.*`, `hjelp.vannkjemi.*`, `hjelp.sensorikk.*`, `hjelp.humle.*`. NO/EN må være symmetriske — generatoren feiler hardt ved asymmetri.

### Navigasjon (IA-beslutning)

`hjelp-side-nav` er fortsatt **flat med flex-wrap**, nå 10 chips. Ved P3A ble dette vurdert reelt og bevisst beholdt: nav-en wrapper allerede korrekt, chipsene er fortsatt gyldige touch-targets, og gruppering ville krevd markup-/CSS-endring på tvers av 10 NO-sider + genererte EN-speilinger.

**Gruppering (KOM I GANG / BRYGGMESTER / UTSTYR) bør vurderes på nytt rundt side 11–12** — det er ikke en hastesak eller en kjent defekt i dag.

---

## Bryggeskole — beslutningsstatus

**Gap Audit V1** (utført før P3A) konkluderte:

- Fundament: **COMPLETE**
- Større innholdshull: **NEI**
- Retning: **B — én til to målrettede runder**, ikke fortsatt storstilt innholdsbygging

P3A var den første av disse rundene og lukket de to høyest prioriterte hullene (humle i dybden, generell sikkerhet utover trykk).

### Gjenværende kandidat (ikke besluttet)

**Mulig P3B** — gjærvalg (ale/lager/kveik, utgjæring, flokkulering, ester-/fenolprofil, alkoholtoleranse, valg av stamme til oppskrift) og klaring (hot break, cold break, Whirlfloc/Irish moss, gelatin/finings, chill haze).

**Lavere prioritet / backlog:** maltforståelse i dybden, emballering/fat i dybden, servering/lagring, prosesseffektivitet nedbrutt.

> **Permanent status:** Etter P3A skal prosjektet **vurdere** om én målrettet P3B (gjærvalg + klaring) gir nok verdi før Bryggeskolen går over til struktur/polish/brukertesting. Terskelen for nye hjelpesider skal være høy — flere sider er ikke automatisk bedre.

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

## Kjent dokumentasjonsgjeld

- **`web/CHANGELOG.md`** stopper ved Runde 15B.1 (2026-08-14) og dekker ikke favicon-runden eller Bryggeskole P0–P3A.
- **`web/README.md`** beskriver fortsatt bare de fire opprinnelige hjelpesidene og det opprinnelige i18n-namespace-settet.

Begge ligger under `web/` og ble bevisst ikke endret i dokumentasjonsrunden 2026-08-23, som hadde eksplisitt krav om null diff i `web/`. Bør tas som en egen, autorisert dokumentasjonsrunde.

---

## Desktop

Ingen endringer i desktop-appen (`app.py`, `modules/`, `ui/`) i august-arbeidet utover `2a9da84` (path-uavhengig app-launcher). Juli-statusens beskrivelse av moduler, kjente svakheter og teknisk gjeld gjelder fortsatt — se `docs/PROJECT_STATUS_JULI_2026.md`.

Se `docs/ROADMAP.md` for full roadmap.
