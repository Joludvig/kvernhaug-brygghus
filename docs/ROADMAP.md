# Kvernhaug Brygghus — Roadmap

*Sist oppdatert: 2026-07-27. Se `docs/PROJECT_STATUS_JULI_2026.md` for full status, nøkkeltall og kjent teknisk gjeld.*

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
- Felles gjærpakkeberegning — samme formel brukt av bryggedagsark, Pantry og Smart Handleliste
- Fritekst oppskriftsimporter, leverandørpanel (pris-synk / produktlenkekontroll), scraper + normaliseringspipeline

## Pågår / akseptansetesting

- **Reell Wiesn-akseptansetest** med brukerens faktiske lagerdata: teknisk lager-/handlelisteflyt er verifisert, ekte humle og EC-1118 er registrert i Pantry. Malt og den faktiske gjæren (W-34/70) gjenstår før en fullstendig lagerkontroll kan regnes som gjennomført.

## Neste

1. Fullføre Wiesn-akseptansetesten
2. **Bryggelogg V1** — registrere faktiske bryggeresultater mot planlagt oppskrift. Lav terskel er hoveddesignkravet: obligatorisk er kun dato + målt OG; FG, karakter, smaksnotater og "neste gang" er valgfritt. Ett loggfil per oppskrift, snapshot av oppskriftsdata ved logg-opprettelse.
3. **Equipment Profile** — erstatte hardkodede BrewZilla 35L-standardverdier med redigerbare utstyrsinnstillinger (kjelevolum, fordampning, meskeforhold, dødvolum, kornabsorpsjon), lagret i `data/equipment.json`.
4. **Butikksammenligning og maltvariantmodell** — side-om-side prissammenligning Vestbrygg/Ølbrygging.no, samt en variantmodell for malt (knust/hel, ulike pakningsstørrelser per butikk) som forutsetning for reell maltpris-sammenligning.
5. **Migrering og avvikling av legacy-humlelager** — fase ut det gamle, ikke-Pantry-synkroniserte humlelageret og den gamle handlelisten når Smart Handleliste er fullt validert i reell bruk.

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
- `master_malt.json` has no variant model per store. Malt is sold in multiple formats and sizes (Vestbrygg: 100 g / 1 kg / 25 kg, knust og hel; Ølbrygging: 1 kg / 5 kg / 25 kg, knust og hel). Unlike hops, malt does not have a single canonical package size — a simple `pakke_gram` field would be misleading. No schema change is made now: today's shopping list only needs price and URL; the user chooses format at checkout. A `varianter` list under `butikk_match` is the planned structure, to be introduced when store comparison or a smarter shopping list actually requires it.
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
