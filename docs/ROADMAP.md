# Kvernhaug Brygghus — Roadmap

*Sist oppdatert: 2026-08-14 (Web Runde 14B — engelsk hjelp/bryggehåndbok, full NO/EN-dekning). Se `docs/PROJECT_STATUS_JULI_2026.md` for full status, nøkkeltall og kjent teknisk gjeld.*

Roadmapen er organisert etter faktisk status, ikke etter en fast versjonsrekkefølge — features flyttes mellom kategoriene etter hvert som virkelig bruk avgjør hva som trengs.

---

## Ferdig

- Oppskriftsbygger med live OG / IBU / EBC / ABV, redigerbare malt-andeler og batch-volum
- Style Engine — 22 BJCP-stiler, epsilon-toleranser, normalisert avvik, kritiske tak, numerisk nærmeste stil, «Historisk Wiesn-Märzen» som egen Kvernhaug/historisk kategori
- Prosessprofiler og Hochkurz
- Bryggeplan/bryggedagsark (to-kolonne A4, utskriftsvennlig)
- Water Chemistry V1 (kildevann, målprofilbibliotek, salter, solver, full/delvis/uoppnåelig-klassifisering, mesk/skyll-fordeling, eksport)
- Pantry V1 (flere ingredienstyper, egendefinerte varer, Lalvin EC-1118)
- Pantry backup/restore (automatisk rullerende backup + manuell gjenoppretting med forhåndsvisning)
- Smart Handleliste V1 (Pantry som sannhetskilde, reell mangel, kjøpsforslag, rest etter kjøp)
- Maltpakningsoptimalisering i Smart Handleliste (butikkvarianter, hel/knust, kombinasjonsforslag rangert etter billigst/minst overkjøp/balansert, lagerstatusfiltrering, «bestill til eksakt mål» for knust Vestbrygg-malt, 25 kg-sekk-sperre — se `docs/MASTER_DATA_FLOW.md`. Kode og tester er ferdig; ekte Vestbrygg-variantdata er ikke aktivert i `master_malt.json` ennå)
- Felles gjærpakkeberegning — samme formel brukt av bryggedagsark, Pantry og Smart Handleliste
- Fritekst oppskriftsimporter, leverandørpanel (pris-synk / produktlenkekontroll), scraper + normaliseringspipeline
- Oppskriftskort — automatisk innholdshøyde (erstatter en tidligere pikselheuristikk; krever Streamlit ≥ 1.57)
- Web: oppskriftsskalering i Bryggmester (Runde 12, portert fra `ui/recipe_card.py`s «Skaler oppskrift» — eksplisitt «Skaler oppskrift»-knapp, faktor = målvolum/nåværende volum, skalerer malt kg (3 desimaler) og humle gram (1 desimal) proporsjonalt, batchvolum oppdateres; gjær, humletid, alfasyre-overstyring, valgt stil, navn/metadata og egendefinerte ingrediensfelt endres aldri)
- Web: koblet malt kg/%-redigering i Bryggmester (Runde 12C/12D) — kg er alltid fasit og oppdaterer % live; %-redigering krever et eksplisitt «Bruk prosentfordeling»-klikk. Flere maltrader kan redigeres manuelt (låses individuelt) før knappen trykkes: låste prosenter beholdes eksakt, resten fordeles proporsjonalt kun mellom urørte rader (én urørt rad får hele resten; alle urørte på 0 % fordeles likt); er alle rader manuelt redigert aksepteres en sum på ~100 % eksakt, ellers vises en vennlig melding uten å endre data. Dette er en bevisst videreføring av — ikke en ordrett kopi av — `ui/malt_panel.py`s enklere «alltid normaliser»-kontrakt.
- Portabel `.kbhrecipe`-fil (Runde 13) — brukervennlig, delbar oppskriftsfil for web: én liten, versjonert JSON-wrapper (`format: "kbhrecipe"`, `version: 1`, `recipe: {...}`) rundt det eksisterende oppskriftsobjektet, ingen parallell datamodell. «Lagre oppskriftsfil» er nå hovedhandlingen i byggerens Lagre og eksporter-panel; rå JSON-eksport er beholdt, men nedgradert til et lukket «Avansert»-felt. Import (byggerens «Åpne oppskriftsfil» og Importer-siden) skiller automatisk mellom ny `.kbhrecipe`-wrapper og eldre, rå oppskrifts-JSON (fortsatt støttet uten manuell konvertering) — ukjent/nyere versjon eller ugyldig fil avvises med en vennlig melding, aldri en krasj eller en aggressiv feiltekst. Alt skjer lokalt i nettleseren, ingen server involvert.
- «Ny oppskrift» og trygg erstatning av aktiv kladd (Runde 13A) — egen «Ny oppskrift»-knapp nullstiller byggeren til bootstrap-standardtilstanden (inkl. malt-%-låser, mål-IBU-arbeidsfelt, skaleringsmål) og forhåndsutfyller Brygger/Bryggeri fra identitetspreferansen. «Ny oppskrift», byggerens «Åpne oppskriftsfil» og Importer-sidens håndoverlevering spør nå alle om bekreftelse før en aktiv kladd med reelt innhold overskrives — aldri før en fil er validert, og aldri når byggeren allerede er tom (`oppskriftHarInnhold()` i `js/kbhrecipe.js`, delt av alle tre inngangene).
- Web: norsk/engelsk UI (Runde 14 + 14B) — vanilla NO/EN-støtte (`js/i18n.js`, ingen npm/build-steg/tredjepartsbibliotek) på tvers av HELE web-appen: bygger, Mine oppskrifter, Importer, Utskrift, print-dokumentene, first-run modusdialog, OG (Runde 14B, 2026-08-14) alle fire `hjelp/`-sidenes fulle brødtekst — oversatt til naturlig bryggeengelsk, ikke maskinoversettelse. Norsk fortsatt default; språkbytte er live (ingen reload, ingen tap av data) og lagres i en egen preferansenøkkel aldri koblet til selve oppskriftsdataen. Stilnavn/smakskategorier/maltgrupper løst som et rent visningslag oppå den eksisterende norske identiteten (`valgtStil` m.fl. uendret i lagring/logikk). BrewZilla-sidens proveniens-skille (produktspesifikasjon vs. Kvernhaug-standardverdi vs. generell forutsetning vs. ikke-verifisert) bevart nøyaktig i engelsk tekst. Se `web/README.md` "Språk (NO/EN)" for full arkitektur og URL-strategi (klientside, samme URL i V1 — kjent SEO-begrensning, egen fremtidig runde, se «Neste» under).

## Pågår / akseptansetesting

- **Reell Wiesn-akseptansetest** med brukerens faktiske lagerdata: teknisk lager-/handlelisteflyt er verifisert, ekte humle og EC-1118 er registrert i Pantry. Malt og den faktiske gjæren (W-34/70) gjenstår før en fullstendig lagerkontroll kan regnes som gjennomført.
- **Web-versjon** (`web/`) — separat, offentlig, forenklet nettversjon av oppskriftsbyggeren. **Runde 1–5 (kjernefunksjonalitet, gjennomført):** OG/FG/ABV/IBU/EBC, smakshjul (vanilla SVG), søkbare dropdown-felt (malt/humle/gjær/stil — søkbart på bl.a. produsent/opprinnelse/type) og stilmatching mot Kvernhaug Brygghus sitt eget 26-stils bibliotek (**ikke** hele det offisielle BJCP-heftet — se [../web/README.md](../web/README.md) for presis dekning), lokal lagring i nettleser, JSON-eksport/import, to visningsmoduser (**Bryggelærling**/**Bryggmester**, samme oppskrift og beregningsmotor), vennlig tre-nivås stilveiledning, egendefinerte ingredienser inkl. alfa-overstyring, deterministisk generert ingrediens-/stildata (`scripts/generate_web_data.py`, ingen egen web-database). **Runde 6 (gjennomført, HEAD `14668af`):** egen **Hjelp & bryggehåndbok** (`hjelp/`: kom i gang, begrepsforklaringer, ingredienser, FAQ, 15-stegs bryggedagsguide, bryggemetoder, første utstyrsguide/BrewZilla med et eksplisitt proveniensskille mellom faktiske produktegenskaper, Kvernhaug-standardverdier for beregning, Kvernhaug-praktiske anbefalinger, generelle bryggeforutsetninger og ikke-verifisert informasjon) med "? → Les mer"-lenker fra hjelpepopoverne; brukeridentitet (ølnavn/brygger/valgfritt bryggeri/notater) på selve oppskriften; fire egne, nøytrale A4-utskriftsdokumenter (oppskriftsark/handleliste/bryggedagsark/bryggelogg — bryggeloggen foreløpig et papirskjema, ikke en digital logg) i stedet for et rått sideprint, brukerens identitet foran diskret Kvernhaug-branding. **Runde 7–11B (gjennomført, visuelt godkjent 2026-08-12 — se `docs/snapshots/2026-08-12_Web_Desktop_Runde_11B_Checkpoint.md`):** fullbredde IA-redesign (Mine oppskrifter-/Importer-/Utskrift-sider, `recipe_engine.js`-orkestrering delt mellom bygger og utskrift, egen `chrome.js` for masthead/drawer), bredere app-lignende Oppskriftsbygger-layout, nytt recipe card-oppsett med alltid synlig Smaksprofil + sammenleggbar Stilanalyse (erstatter tidligere fane-navigasjon), Bryggelærling/Bryggmester gjort til **reelle** modi (førstegangsvalg + drawer-bryter, ikke lenger en ren CSS-visningsbryter) med Bryggmesters faktiske malt kg↔%-arbeidsflyt (portert fra `ui/malt_panel.py`) og mål-IBU→gram via portert inverse Tinseth (`modules/calculations.py::beregn_gram_fra_ibu`), samt et nytt **KBH Emblem** som felles master-asset for web og desktop (se «Branding og identitet» under). Tilsvarende desktop-endringer (hero-header, nytt emblem i recipe card) er del av samme godkjente milepæl. **Runde 12 (gjennomført, godkjent 2026-08-13):** eksplisitt «Skaler oppskrift» i Bryggmester (portert fra `ui/recipe_card.py`), og en revidert Bryggmester-kontrakt for malt kg/%: kg er alltid fasit og oppdaterer % live; %-redigering er eksplisitt (flere rader kan redigeres/låses manuelt, «Bruk prosentfordeling» fordeler resten kun mellom urørte rader og beholder låste verdier eksakt) — se «Ferdig» over for full kontrakt (KBH Icon v1, samme runde, er allerede dekket under «Branding og identitet» nedenfor). **Runde 13/13A (gjennomført, godkjent og committet):** portabel `.kbhrecipe`-fil for lagring/deling/backup av oppskrifter, samt «Ny oppskrift» og trygg confirm-basert erstatning av aktiv kladd — se «Ferdig» over for full kontrakt. **Runde 14 + 14B (gjennomført, godkjent):** norsk/engelsk UI for hele app-en inkludert full oversettelse av hjelp/bryggehåndbok-brødteksten, se «Ferdig» over for full kontrakt. **Fortsatt ikke deployet** — gjenstår en egen pre-deploy-vurdering, se punkt 6 under «Neste».

## Neste

1. Fullføre Wiesn-akseptansetesten
2. **Bryggelogg V1** — registrere faktiske bryggeresultater mot planlagt oppskrift. Lav terskel er hoveddesignkravet: obligatorisk er kun dato + målt OG; FG, karakter, smaksnotater og "neste gang" er valgfritt. Ett loggfil per oppskrift, snapshot av oppskriftsdata ved logg-opprettelse.
3. **Equipment Profile** — erstatte hardkodede BrewZilla 35L-standardverdier med redigerbare utstyrsinnstillinger (kjelevolum, fordampning, meskeforhold, dødvolum, kornabsorpsjon), lagret i `data/equipment.json`.
4. **Aktivere ekte Vestbrygg-variantdata, deretter full butikksammenligning** — variantmodell, lagerstatus, eksakt mål og 25 kg-sperre er ferdig kodet og testet (se «Ferdig» over); det som faktisk gjenstår er (a) å kjøre scraper/matcher mot ekte Vestbrygg-produktsider slik at `master_malt.json` får reelle varianter/lagerstatus, og (b) deretter side-om-side prissammenligning på tvers av Vestbrygg/Ølbrygging.no for hele oppskriften.
5. **Migrering og avvikling av legacy-humlelager** — fase ut det gamle, ikke-Pantry-synkroniserte humlelageret og den gamle handlelisten når Smart Handleliste er fullt validert i reell bruk.
6. **Web: Help-innholdshull for Bryggmester-features (funnet under Runde 14B)** — flere funksjoner finnes i dagens app uten egen forklaring i Hjelp/bryggehåndboken: batchskalering, malt kg/%-arbeidsflyten, «Bruk prosentfordeling»/«Apply percentage split», mål-IBU-verktøyet, beskyttelse av aktiv kladd ved Ny/Åpne/Importer/Mine oppskrifter, og selve NO/EN-språkvalget. Ikke en blokkerende mangel — bygger-UI-et er selvforklarende nok til daglig bruk — men bør dekkes i en fremtidig Help-innholdsrunde, på begge språk samtidig (ikke bare engelsk) siden ingen av delene er dokumentert i norsk heller.
7. ~~**Web — fremtidig SEO-URL-strategi**~~ — **Ferdig (Runde 15A–15B.4, 2026-08-14).** Egen, ekte crawlbar engelsk URL-struktur under `/en/**` (8 sider, speilet 1:1), generert deterministisk av `scripts/generate_web_i18n_pages.py` fra norsk kilde-HTML + `TEKSTER` i `i18n.js` — ingen manuell dobbel vedlikeholdsbyrde. Fullt teknisk SEO-grunnlag på plass: unik `<title>`/meta description per side og språk, selvrefererende canonical, gjensidig hreflang no/en/x-default, `web/sitemap.xml` (16 URL-er) og `web/robots.txt`. Se `web/README.md` "Engelsk pre-render (web/en/)" og "URL-kontrakt".
8. **Web-versjon — Pre-deploy / lanseringsklar-runde** (før publisering på `KvernhaugBrygghus.no`, ikke påbegynt): vurdere endelig funksjonsomfang for første offentlige versjon, innholdskvalitet i Hjelp/bryggehåndbok, datakvalitet for malt/humle/gjær, stilbibliotek/dekning, visuell sluttpolish på mobil/desktop, utskriftskontroll med ekte oppskrifter, hosting/opplasting, kobling til `KvernhaugBrygghus.no`, og en produksjonstest etter deploy (inkl. faktisk Search Console-innsending/indekseringsverifisering — kan først gjøres etter offentlig lansering). Kjente delkrav som ikke må forsvinne før lansering:
   - **Norsk + engelsk er must-have** — app-UI og hjelp/bryggehåndbok begge ferdig oversatt (Runde 14 + 14B); egen crawlbar engelsk URL OG teknisk SEO-grunnarbeid er nå ferdig (punkt 7); Bryggmester-innholdshullene i punkt 6 bør også vurderes før lansering.
   - Open Graph/Twitter Cards, structured data (JSON-LD), analytics/tracking, Search Console-verifiseringsfil, www-/trailing-slash-redirects — bevisst utenfor omfanget til punkt 7, ikke vurdert ennå.
   - Kontakt-e-post — mangler et sted brukere kan nå Kvernhaug Brygghus.
   - Personvern-/cookieside eller -tekst — mangler, avhenger av faktisk funksjonalitet ved lansering.

## Senere

- Etikettgenerator
- Forskningsbatch (dedikert liten-skala/eksperimentell brygg-modus)
- Eksempeloppskrifter (ferdige, kuraterte oppskrifter for nye brukere — web og/eller desktop)
- Egen PDF-eksportmotor (i stedet for dagens innebygde utskriftsvisning)
- Avansert meske-pH-/syredosemodell (automatisk beregning — i dag er pH kun et manuelt målefelt)
- Automatisk lagerreservasjon
- Lagertransaksjonshistorikk
- Multi-bruker / first-run-oppsett (butikkvalg, katalogfiltrering per butikk), delt oppskriftsbibliotek
- Web: flere utstyrsspesifikke guider utover BrewZilla (f.eks. Grainfather)
- Web: kobling mellom en fremtidig Equipment Profile og riktig utstyrsguide (ingen kobling bygget ennå)
- Web: et eventuelt lett, lokalt gjenbruksbibliotek for egendefinerte ingredienser (bevisst utelatt som "nice-to-have")
- Web: digital Bryggelogg-funksjon (i dag kun et utskrivbart papirskjema — se Bryggelogg V1-punktet over, som gjelder desktop-appen)
- Web: stilbasert ingrediensveiledning ("hvilke ingredienser gir denne stilen") — krever bedre/rikere ingrediensdata enn det som finnes i dag før dette kan gjøres godt
- Favicon og andre ekstremt små (16–24px) branding-plasseringer — KBH Icon v1 (se «Branding og identitet» under) er vurdert og funnet for detaljert til å være lesbar så langt ned; krever en egen, bevisst forenklet mikrovariant. Desktopens 24px eksport-ikon (`master_v1_header_24px.png`) beholdes uendret til dette er laget.

## Parkert / permanent avvist

- **Automatisk bestilling uten offentlig leverandør-API** — avvist i denne formen; ingen slik integrasjon planlegges med mindre leverandørene tilbyr et offentlig API.

---

## Kjent WIP-branch

`wip/gjaer-id-migrasjon` finnes i repoet, men er gren ut fra en base **fra før** Pantry V1 og Smart Handleliste V1 ble bygget. Den er ikke et oppdatert parallelt spor og må rebases mot master og gjennomgås grundig før en eventuell merge vurderes. Den skal ikke røres eller blandes inn i annet arbeid nå.

---

## Branding og identitet — Parallelt spor

**Kilde:** `docs/branding/master_design_v1.md`
**Prinsipp:** Branding rulles ut gradvis — header og eksport før UI-farger. Kalkulasjoner og oppskriftslogikk røres ikke.

### Gjort

- Master Design V1 dokumentert som permanent sannhetskilde (`docs/branding/master_design_v1.md`)
- App-header implementert: logo, tittel, motto og sekundærtekst (`ui/branding.py` / `render_header()`)
- Bildefil på plass: `assets/branding/master_v1.png`
- Merch-standard definert: brystlogo, armtekst, ryggillustrasjon (i branding-dokumentet)
- Fargepalett med estimerte HEX-verdier dokumentert
- **Nytt KBH Emblem** (2026-08-12) — brukerlevert, transparensrensket emblem etablert som felles master-asset (`assets/branding/kbh_emblem_master.png`, 1024×1536) for både web og desktop. Erstattet det gamle `master_v1_transparent.png` i web sin identitetsblokk (Runde 11B) og i desktop sitt recipe card (`ui/branding.py`, `ui/recipe_card.py`, `modules/card_template.py`). Ingen ny illustrasjon — kun rensket alfakanal fra den leverte filen. `docs/branding/master_design_v1.md` beskriver fortsatt det opprinnelige Master V1-motivet og er **ikke** oppdatert til å referere det nye emblemet ennå.
- **KBH Icon v1** (2026-08-12, Runde 12, visuelt godkjent) — brukerlevert, godkjent kompaktikon (kråke + pils + møllestein, transparent bakgrunn) etablert som autoritativ kompakt-logo, atskilt fra det fulle emblemet over. Master: `assets/branding/kbh_icon_v1.png` (1024×1536, urørt original). Brukes i web drawer (`.sidemeny-logo`) og kompakt sticky-nav (`.kompaktnav-logo`) på alle 8 sider, via web-derivatet `web/assets/branding/kbh_icon_v1.png` (260×390). `object-fit` byttet fra `cover` til `contain` på begge CSS-klasser siden det nye motivet er en uklippet, stroende komposisjon (ikke en forhåndsbeskåret sirkel som forgjengeren). Erstattet og fjernet `assets/branding/kompaktlogo_kraake_kvern.png`/`web/assets/branding/kvernhaug_logo_kompakt.png` (ingen gjenværende referanser). Ikke brukt på desktop — appen har ingen tilsvarende kompakt-nav-rolle i dag. Branding-systemet er nå: HERO = stedet, FULLT EMBLEM = `kbh_emblem_master.png`, KOMPAKT IKON = `kbh_icon_v1.png`.

### Neste steg (i prioritert rekkefølge)

1. Test app-header visuelt — kjør Streamlit og verifiser at layout, fonter og farger ser riktige ut på skjermen
2. Om Kvernhaug Brygghus-panel — enkel informasjonsside eller expander: bryggeriets historie, Dalelva, Kvernhaug-eiendommen, motto
3. Oppskriftskort med branding — legg til kompaktlogo og typografi fra Master V1 i HTML-oppskriftskortet
4. PDF / Brewday Plan-eksport med branding — logo og fargepalett i topp/bunn på utskriftssider
5. Produksjonsklare merch-filer — isolerte PNG/SVG-filer optimalisert for trykk (brystlogo, armtekst, ryggillustrasjon)

### Avgrensninger

- Ikke fargelegg tabeller, knapper eller grafer i oppskriftsbyggeren ennå
- Ikke brand hele UI-et før header og eksportdokumenter er testet i bruk
- Ikke endre kalkulasjoner, IBU-logikk eller oppskriftslagring som del av branding-arbeid

---

## Data Architecture Direction

Current state: store prices and URLs are embedded inside master product databases.

Long-term direction (when a third store is added or multi-user is needed):

```
LAYER 1 — Product Catalog     catalog/malt.json etc.
          Sensory, style, canonical IDs, aliases
          Source: manual curation + producer data

LAYER 2 — Store Inventory     stores/vestbrygg.json etc.
          Price, URL, pakke_gram, in_stock
          Source: scraper, per store

LAYER 3 — App View            data/malt.json etc.
          Join of catalog + store data for selected stores
          Only includes products with at least one active store match
```

Trigger for this refactor: adding a third store.

**Known technical debt in current master data:**
- `master_malt.json` is already v2-format in structure, but the filename is a legacy holdover. Future rename to `master_malt_v2.json` requires updating `store_matcher.py`, `import_panel.py`, and `app.py` — do not rename in isolation.
- `master_malt.json`'s variant model (`varianter` list under `butikk_match`, per size/format/price/lagerstatus) is implemented and tested in code (`modules/malt_packaging.py`) — see `docs/MASTER_DATA_FLOW.md`. What remains is activation with real data: no entry in today's `master_malt.json` has actual variants yet, so the shopping list still falls back to the older flat price/URL behavior for every real malt.
- Ølbrygging.no malt data is weaker than Vestbrygg — many prices are set manually, not from scraper.

---

## Guiding Principles

- **Do not overbuild.** Each feature should come from a real brewing need.
- **Keep the app stable.** New features are additive, not replacements.
- **Small commits.** One logical change per commit.
- **Real use drives priorities.** Polish comes from actual brewday testing, not assumptions.
- **Low friction over completeness.** A feature that is used beats a feature that is thorough but skipped.
- **Master DB = product knowledge.** EBC, flavor, style. Stable.
- **Store data = commercial availability.** Price, URL, stock. Volatile.
- **Producer data = enrichment.** Authoritative for technical specs. Does not replace curation.
- **Ask first:** "Løser dette et faktisk problem som oppstår under bruk?" — ikke "Ville dette vært kult å ha?"
