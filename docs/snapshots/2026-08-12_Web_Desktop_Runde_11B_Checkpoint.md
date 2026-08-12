# Project Snapshot — 2026-08-12 — Web + Desktop, Runde 8–11B checkpoint

## Generelt

| Felt | Verdi |
|---|---|
| Dato | 2026-08-12 |
| Tid | 18:18 (lokal tid, rett før commit) |
| Versjon | Ikke versjonsnummerert (ingen `VERSION`-fil eller tilsvarende i repoet) |
| Git branch | `master` |
| Siste commit | Tas rett etter dette snapshotet — se sluttrapporten i samme økt for faktisk hash |
| GitHub-status | `master` var 12 commits foran `origin/master` før denne checkpoint-commiten (ikke pushet) |

## Prosjektstatus

**Kort oppsummering**

Siden forrige snapshot ([2026-08-10_Web_Runde_6_Ferdig_Pre_Deploy.md](2026-08-10_Web_Runde_6_Ferdig_Pre_Deploy.md)) har web-versjonen gjennomgått en større IA- og visuell runde (internt kalt Runde 8–11B): fullbredde hero-header, en bredere, mer app-lignende Oppskriftsbygger-layout, et nytt recipe card-oppsett, Bryggelærling/Bryggmester gjort til reelle modi (ikke lenger en ren CSS-visningsbryter) med Bryggmesters faktiske malt kg↔%-arbeidsflyt og mål-IBU→gram-beregning, og et helt nytt KBH Emblem som felles master-asset. De samme desktop-endringene (hero-header, nytt emblem i recipe card) er del av samme godkjente milepæl. Alt arbeidet er visuelt godkjent av brukeren og fryses nå som ett samlet checkpoint før neste feature-runde starter.

**Nye milepæler**

Siden forrige snapshot (uncommittet arbeid frem til nå, flere økter):
- **Fullbredde web hero-header** — masthead-komposisjonen fra `ui/branding.py::render_header()` speilet i web i full bredde, ikke det gamle smale, sentrerte headerkortet.
- **Bredere, app-lignende Oppskriftsbygger-layout** — venstre kolonne som flat seksjonsflyt (ikke boks-i-boks), høyre kolonne som sticky, varm "recipe card"-sone. Layoutbruddet ved 1000px er satt ut fra faktisk plassbehov.
- **Nytt recipe card-oppsett (Runde 10E)** — emblem +13% (senere byttet helt ut, se under), tettere vertikal spacing i identitetsblokken, riktig «valgt stil»-semantikk (kortet viser brukerens manuelt VALGTE Ølstil, ikke det automatiske stilmatch-resultatet), Smak/Stil-fanenavigasjonen fjernet til fordel for en alltid synlig **Smaksprofil**-seksjon etterfulgt av en sammenleggbar (`<details>`, lukket som standard) **Stilanalyse**-seksjon.
- **Bryggelærling/Bryggmester som reelle modi (Runde 11)** — modusvalg flyttet fra en stor, permanent bryter i arbeidsflaten til (a) en førstegangsdialog ved første besøk og (b) en liten status+bryter i venstremenyen, lagret i `localStorage`. Bryggmester låser opp desktop-appens faktiske malt kg↔%-kontrakt (`ui/malt_panel.py`: kg er alltid kilden og oppdaterer % live på hver endring; % → kg krever et eksplisitt «Bruk prosentfordeling»-klikk som leser alle synlige %-verdier og fordeler nåværende total-kg proporsjonalt) og et mål-IBU→gram-felt per humletilsetning, portert fra `modules/calculations.py::beregn_gram_fra_ibu` (inverse Tinseth), kun via et eksplisitt «Beregn gram»-klikk — aldri live, for å unngå en feedback-loop mellom gram- og IBU-feltet.
- **Nytt KBH Emblem (Runde 11B)** — et brukerlevert emblem («KBH Emblem» fra Downloads) etablert som ny, felles master-asset (`assets/branding/kbh_emblem_master.png`, 1024×1536, transparensrensket fra filens egen alfakanal — ingen ny illustrasjon). Erstattet i web sin identitetsblokk (`web/assets/branding/kbh_emblem.png`, 780×1170) og i desktop sitt recipe card (`ui/branding.py`, `ui/recipe_card.py`, `modules/card_template.py`). CSS-sizing justert for det nye stående sideforholdet (web: bredde- → høydestyrt clamp; desktop: `height:300px` → `height:400px`) for å bevare tilsvarende visuell dominans som før.
- **Desktop hero-header** — tilsvarende breddefylt hero-komposisjon i `ui/branding.py::render_header()` (utført i en tidligere, ikke separat snapshotet økt før denne).

**Status på hovedmoduler**

Uendret for Streamlit-appens kjernefunksjonalitet (oppskriftsbygger, Style Engine, vannkjemi, Pantry, Smart Handleliste) siden forrige snapshot — se `docs/PROJECT_STATUS_JULI_2026.md` (2026-07-28) for detaljer om disse, uendret av denne runden. For `web/` og branding spesifikt:

| Del | Status |
|---|---|
| Web hero/header (fullbredde) | Ferdig, testet |
| Web Oppskriftsbygger-layout (bredere, app-lignende) | Ferdig, testet |
| Web recipe card V2 (identitet, Smaksprofil/Stilanalyse) | Ferdig, testet |
| Web Bryggelærling/Bryggmester (reelle modi) | Ferdig, testet |
| Malt kg↔%-arbeidsflyt (Bryggmester) | Ferdig, testet — portert 1:1 fra `ui/malt_panel.py` |
| Mål-IBU → gram (inverse Tinseth, Bryggmester) | Ferdig, testet — portert 1:1 fra `modules/calculations.py` |
| Nytt KBH Emblem (web + desktop, felles master) | Ferdig, testet |
| Desktop hero-header | Ferdig, testet |
| Desktop recipe card med nytt emblem | Ferdig, testet |
| Import (`importer.html`), Mine oppskrifter, Utskrift | Uendret i denne runden (bygget i tidligere Runde 6-arbeid), verifisert fortsatt fungerende i dette checkpointets funksjonstest |
| Hosting/deploy | Ikke startet |

**Kjente begrensninger**

Uendret fra forrige snapshot, pluss presiseringer fra denne runden:
- Ikke deployet/hostet ennå; ingen kobling til `KvernhaugBrygghus.no`.
- Ikke full BJCP 2021 — kun det eksisterende 26-stils Kvernhaug-biblioteket (uendret).
- Ingen personlig gjenbruksbibliotek for egendefinerte ingredienser (bevisst utelatt, uendret).
- Ingen mesketemperaturfelt i web (uendret).
- Bryggeloggen er foreløpig kun et utskrivbart papirskjema (uendret).
- Web mangler fortsatt oppskriftsskalering i Bryggmester (finnes i desktop via `ui/recipe_card.py`, ikke portert).
- Stilbasert ingrediensveiledning krever bedre/rikere ingrediensdata enn det som finnes i dag.
- Ingen portabel `.kbhrecipe`-fil (kun rå JSON-eksport/import).
- Norsk + engelsk er fortsatt ikke løst — kun norsk, og er markert must-have før lansering.
- Ingen SEO-grunnarbeid, kontakt-e-post eller personvern-/cookieside ennå.
- Eget kompakt-ikon (kråke + pils + møllestein) og favicon er ikke laget — dagens `kvernhaug_logo_kompakt.png` (automatisk beskjæring) er en midlertidig løsning.
- To gamle emblemfiler (`assets/branding/master_v1_transparent.png` og `web/assets/branding/master_v1_transparent.png`) er nå ubrukte i koden etter emblembyttet — se sluttrapporten for denne checkpoint-økten for vurdering.
- `docs/branding/master_design_v1.md` er ikke oppdatert til å beskrive det nye KBH Emblemet — beskriver fortsatt det opprinnelige Master V1-motivet.

**Pågående arbeid**

Ingenting pågående akkurat nå — Runde 8–11B er visuelt godkjent, testet og fryses i dette checkpointet. Neste fase er en ny, ikke påbegynt feature-runde (se `docs/ROADMAP.md` for backlog).

## Kode

**Tester**

Kjørt på nytt i dette snapshotet: `py -3 -m unittest discover -s tests` → **859 tester, 0 skipped, 0 errors, 0 failures**. I tillegg en egen Playwright-sweep (Chromium + Firefox, 1280/768/375px, alle 8 web-sider: overflow- og konsollfeilsjekk) samt en Chromium-funksjonstest av Lærling/Mester-bryter, malt kg↔%, mål-IBU→gram, emblem-lasting, import og utskrift — se sluttrapporten for denne økten for fullt resultat.

**Demo Mode**

Ikke påvirket av denne runden. Desktop-endringene (hero-header, nytt emblem) er rene branding-/asset-bytter i `ui/branding.py`/`ui/recipe_card.py`/`modules/card_template.py` — ingen `DEMO_MODE`-gren berørt. `web/` er fortsatt et helt separat produkt utenfor `config.py::DEMO_MODE`-arkitekturen.

**Dokumentasjon**

`docs/ROADMAP.md` oppdatert i denne økten: web-bullet under «Pågår / akseptansetesting» utvidet med Runde 7–11B, «Branding og identitet»-seksjonen fikk et nytt «Gjort»-punkt for KBH Emblemet, «Neste» punkt 6 (pre-deploy) presisert med eksplisitte delkrav (norsk+engelsk, SEO, kontakt-e-post, personvern), og «Senere» fikk nye punkter (forskningsbatch, eksempeloppskrifter, oppskriftsskalering i web, stilbasert ingrediensveiledning, portabel `.kbhrecipe`, kompakt-ikon kråke+pils+møllestein, favicon). `web/README.md` oppdatert: mode-switch-beskrivelsen (var feilaktig «ren CSS-styrt visningsbryter»), ny identitetsblokk-/Smaksprofil-/Stilanalyse-beskrivelse, nytt emblem-avsnitt under «Design og navigasjon», ny `kbh_emblem.png`-linje i strukturoversikten. `docs/development/PROJECT_MAP.md` sjekket — peker allerede kun videre til `web/README.md`, ingen egne detaljer å oppdatere der.

**Vault**

Se sluttrapporten for denne økten for hvilke Vault-filer som faktisk ble oppdatert (`System/Kvernhaug Brygghus App.md` og eventuelt `System/Kvernhaug Handover.md`, per etablert mønster fra forrige snapshot).

**Teknisk gjeld**

Uendret Python-side utover branding-bytte (kun asset-referanser og CSS-tall endret, ingen ny logikk). Web-spesifikk gjeld, uendret eller presisert:
- Ingen delt kjøretid mellom Python og JS (uendret).
- To ubrukte emblemfiler ligger fortsatt i repoet etter bytte (se «Kjente begrensninger» over) — bevisst ikke slettet uten brukerens bekreftelse.
- `docs/branding/master_design_v1.md` er nå ute av synk med det faktiske emblemet i bruk — ikke rettet i denne runden.

**Arkitektur**

`modules/` vs. `ui/`-grensen intakt — emblembyttet er rene konstant-/CSS-endringer i `ui/branding.py`, `ui/recipe_card.py` og `modules/card_template.py`, ingen ny Streamlit-import i `modules/`. `web/` forblir bevisst utenfor denne grensen som et frittstående, klientside-produkt. Modus-arkitekturen (`settModus()` som itererer `.modus-knapp` på tvers av førstegangsdialog og drawer) og malt kg↔%/mål-IBU-arbeidsflytene er additive JS-mønstre uten nye avhengigheter.

## Git

| Felt | Verdi |
|---|---|
| Antall commits siden forrige snapshot | 0 commits — hele Runde 8–11B har ligget uncommittet frem til denne checkpoint-økten (samles i én commit rett etter dette snapshotet) |
| Klar for release? | Nei — web er fortsatt ikke deployet; en egen pre-deploy/lanseringsklar-runde gjenstår |
| Klar for push? | Nei — brukeren har eksplisitt bedt om kun commit, ikke push, i denne økten |

## Kommentar

Tatt på brukerens eksplisitte forespørsel («CHECKPOINT — GODKJENT WEB + DESKTOP ETTER RUNDE 8–11B») rett etter at all IA-redesign, reelle Lærling/Mester-moduser, malt kg↔%, mål-IBU→gram og det nye KBH Emblemet ble visuelt godkjent på tvers av web og desktop. Fryser en stabil, testet tilstand — flere ukommitterte økters arbeid samlet i én milepæl-commit — rett før en ny, ikke påbegynt feature-runde starter.
