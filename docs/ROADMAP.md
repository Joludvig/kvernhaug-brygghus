# Kvernhaug Brygghus — Roadmap

*Sist oppdatert: 2026-08-03 (Steg F6 — malt-variantmodell/lagerstatus/eksakt-mål-status rettet). Se `docs/PROJECT_STATUS_JULI_2026.md` for full status, nøkkeltall og kjent teknisk gjeld.*

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

## Pågår / akseptansetesting

- **Reell Wiesn-akseptansetest** med brukerens faktiske lagerdata: teknisk lager-/handlelisteflyt er verifisert, ekte humle og EC-1118 er registrert i Pantry. Malt og den faktiske gjæren (W-34/70) gjenstår før en fullstendig lagerkontroll kan regnes som gjennomført.
- **Web-versjon V1** (`web/`) — separat, offentlig, forenklet nettversjon av oppskriftsbyggeren: OG/FG/ABV/IBU/EBC, smakshjul (vanilla SVG), søkbare dropdown-felt (malt/humle/gjær/stil — søkbart på bl.a. produsent/opprinnelse/type) og stilmatching mot Kvernhaug Brygghus sitt eget 26-stils bibliotek (**ikke** hele det offisielle BJCP-heftet — se [../web/README.md](../web/README.md) for presis dekning), lokal lagring i nettleser, JSON-eksport/import. To visningsmoduser — **Bryggelærling** (veiledet, med "?"-hjelpetekster på sentrale begreper) og **Bryggmester** (full detalj) — deler samme oppskrift og beregningsmotor. Stilmatchen har en vennlig tre-nivås stilveiledning i stedet for feilmeldinger. Egendefinerte ingredienser (malt/humle/gjær) støttes per oppskrift, inkl. alfa-overstyring på biblioteks-humle. Ingrediens-/stildata regenereres fra desktop sine masterdata via `scripts/generate_web_data.py` — ingen egen, manuelt vedlikeholdt web-database. Egen **Hjelp & bryggehåndbok** (`hjelp/`: kom i gang, begrepsforklaringer, ingredienser, FAQ, bryggedagsguide, bryggemetoder, første utstyrsguide/BrewZilla) med "? → Les mer"-lenker fra hjelpepopoverne. Brukeridentitet (ølnavn/brygger/valgfritt bryggeri) på selve oppskriften. Fire egne, nøytrale utskriftsdokumenter (oppskriftsark/handleliste/bryggedagsark/bryggelogg) i stedet for et rått sideprint. Bygget og test-/polish-rundet 2026-08-10, committet men ikke deployet ennå.

## Neste

1. Fullføre Wiesn-akseptansetesten
2. **Bryggelogg V1** — registrere faktiske bryggeresultater mot planlagt oppskrift. Lav terskel er hoveddesignkravet: obligatorisk er kun dato + målt OG; FG, karakter, smaksnotater og "neste gang" er valgfritt. Ett loggfil per oppskrift, snapshot av oppskriftsdata ved logg-opprettelse.
3. **Equipment Profile** — erstatte hardkodede BrewZilla 35L-standardverdier med redigerbare utstyrsinnstillinger (kjelevolum, fordampning, meskeforhold, dødvolum, kornabsorpsjon), lagret i `data/equipment.json`.
4. **Aktivere ekte Vestbrygg-variantdata, deretter full butikksammenligning** — variantmodell, lagerstatus, eksakt mål og 25 kg-sperre er ferdig kodet og testet (se «Ferdig» over); det som faktisk gjenstår er (a) å kjøre scraper/matcher mot ekte Vestbrygg-produktsider slik at `master_malt.json` får reelle varianter/lagerstatus, og (b) deretter side-om-side prissammenligning på tvers av Vestbrygg/Ølbrygging.no for hele oppskriften.
5. **Migrering og avvikling av legacy-humlelager** — fase ut det gamle, ikke-Pantry-synkroniserte humlelageret og den gamle handlelisten når Smart Handleliste er fullt validert i reell bruk.
6. **Web-versjon — videre**: flere utstyrsspesifikke guider utover BrewZilla (f.eks. Grainfather), kobling mellom en fremtidig Equipment Profile og riktig utstyrsguide (ingen kobling bygget ennå — se punkt 3), og et eventuelt lett, lokalt gjenbruksbibliotek for egendefinerte ingredienser (bevisst utelatt som "nice-to-have" i runden som la til egendefinerte ingredienser).

## Senere

- Etikettgenerator
- Egen PDF-eksportmotor (i stedet for dagens innebygde utskriftsvisning)
- Avansert meske-pH-/syredosemodell (automatisk beregning — i dag er pH kun et manuelt målefelt)
- Automatisk lagerreservasjon
- Lagertransaksjonshistorikk
- Multi-bruker / first-run-oppsett (butikkvalg, katalogfiltrering per butikk), delt oppskriftsbibliotek

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
