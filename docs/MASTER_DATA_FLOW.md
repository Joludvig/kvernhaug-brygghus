# Kvernhaug Brygghus — Master Data Flow

*Oppdatert 2026-07-28 til å reflektere den faktiske, nåværende flyten. Den tidligere versjonen av dette dokumentet beskrev `data/malt.json` som runtime-filen `app.py` laster, og en "Importer til Master DB"-knapp som et eget publiseringssteg. Ingen av delene stemmer lenger — se historikk-notatet nederst.*

## Oversikt

```
Nettbutikker
   │
   ▼
raw_data/*_raw.json              ← skrapet rådata (scraper)
   │
   ▼  ("🧠 Kjør AI-normalisering" i Import-panelet)
   │
   ├──► data/master_malt.json    ← matchede produkter oppdateres DIREKTE
   ├──► data/master_humle_v2.json    (pris/URL i butikk_match)
   └──► data/master_gjaer_v2.json
   │
   ▼  (umatchede produkter)
raw_data/unmatched_*.json        ← venter i "📋 Pending Review"
   │
   ▼  (Match eksisterende / Opprett i master / Avvis)
data/master_*.json               ← review skriver OGSÅ DIREKTE hit
   │
   ▼  app.py laster ALLE TRE filene direkte ved oppstart
malt_database / humle_database / gjaer_database  (dict i minnet)
```

**Det finnes ikke noe eget "runtime"-lag eller "importer til master"-steg lenger.** `data/master_malt.json`, `data/master_humle_v2.json` og `data/master_gjaer_v2.json` ER runtime-dataene — appen laster dem direkte, og både automatisk matching og manuell review-godkjenning skriver direkte til dem.

---

## Filer og ansvar

### Masterfiler (rediger her — dette ER runtime-dataene)

| Fil | Innhold | Lastes av |
|-----|---------|-----------|
| `data/master_malt.json` | Alle malt-entries med aliases, butikk_match, tags | `app.py` direkte |
| `data/master_humle_v2.json` | Alle humle-entries | `app.py` direkte |
| `data/master_gjaer_v2.json` | Alle gjær-entries | `app.py` direkte |

```python
# app.py
malt_database  = last_json_data("master_malt.json")
humle_database = last_json_data("master_humle_v2.json")
gjaer_database = last_json_data("master_gjaer_v2.json")
```

Ingen av de tre går via et flatenert/generert mellomlag — `last_json_data()` leser filen direkte og filtrerer bort `_`-prefikserte metadata-nøkler.

> **`master_malt.json` — filnavn vs. format:**
> Filen er i praksis v2-format (samme struktur som `master_humle_v2.json` og `master_gjaer_v2.json`:
> `butikk_match`, `aliases`, `verified`, nested store-data).
> Filnavnet er gammelt og vil på et passende tidspunkt renames til `master_malt_v2.json`.
> **Ikke rename ennå** — krever oppdatering av `store_matcher.py` og `app.py`.

### Skriving til masterfilene

All skriving til de tre masterfilene går gjennom `modules/master_data_io.py::skriv_master_json_atomisk()` — atomisk (midlertidig fil + `os.replace`) med automatisk tidsstemplet backup av forrige versjon (`data/*.json.backup_*`, gitignoret, se `.gitignore`). To steder skriver:

- `modules/store_matcher.py` — automatisk matching mot allerede kjente aliaser (kalt fra Import-panelets "🧠 Kjør AI-normalisering"). Oppdaterer kun `butikk_match` (pris/URL) på en EKSISTERENDE entry; oppretter aldri nye ingredienser automatisk.
- `ui/review_panel.py` — manuell godkjenning av et "pending review"-element: enten et alias+prisoppdatering på en eksisterende entry ("🔗 Match eksisterende"), eller en helt ny entry ("➕ Ny ingrediens"). Sistnevnte blokkerer eksplisitt hvis den auto-genererte ID-en allerede finnes i master (`MasterIdKollisjon`) eller er tom (`TomMasterId`) — se `ui/review_panel.py::_opprett_og_fjern()`.

Begge stedene skriver til nøyaktig samme filer `app.py` laster ved oppstart — en godkjent review-endring er synlig i appen med én gang (etter en `st.rerun()`/ny sideinnlasting), uten noe mellomsteg.

### Pending review (midlertidige arbeidsfiler)

| Fil | Innhold |
|-----|---------|
| `raw_data/unmatched_malt.json` | Skrapede malt-produkter som ikke matchet noe alias i master |
| `raw_data/unmatched_hops.json` | Samme for humle |
| `raw_data/unmatched_gjaer.json` | Samme for gjær |

Disse er ikke masterdata og skrives med enkel, direkte JSON-skriving (`ui/review_panel.py::_skriv_json()`) — de er en kø, ikke en kilde til sannhet.

### Legacy-filer (IKKE lest av appen — beholdt, ikke slettet)

| Fil | Status |
|-----|--------|
| `data/malt.json` | Skrives ikke lenger av noe — "Importer til Master DB"-knappen som skrev den er fjernet (se historikk-notat). Leses ikke av `app.py`. |
| `data/humle.json` | Samme — skrives ikke, leses ikke. |
| `data/gjaer.json` | Samme — skrives ikke, leses ikke av appen. Brukt som ENGANGS-inndata av `modules/db_cleanup.py` sitt `__main__`-skript under en historisk gjær-opprydding; den jobben er allerede gjort. |

Disse tre er bevisst **ikke slettet** — en fjerning krever en egen, dokumentert avhengighetskontroll (se `docs/PROJECT_STATUS_JULI_2026.md`), ikke noe som gjøres som del av en dokumentasjonsoppdatering.

---

## Dataflyt i detalj

### Malt, Humle og Gjær (identisk flyt for alle tre siden 2026-07-28)

```
master_malt.json / master_humle_v2.json / master_gjaer_v2.json
         │
         │ app.py → last_json_data(...)
         ▼
malt_database / humle_database / gjaer_database (dict i minnet)
         │
         ├── malt_panel.py / hop_panel.py / yeast_panel.py → dropdown + pris-visning
         ├── recipe_context.py → OG, EBC, IBU, ABV, flavor-beregninger
         └── shopping_list_panel.py → priser og URL-er
```

---

## Kjente mangler og svakheter i masterdata

### master_malt.json

| Mangel | Status | Løsning |
|--------|--------|---------|
| Ølbrygging.no malt-data er svakere enn Vestbrygg | Mange `pris_olbrygging`-verdier er satt manuelt, ikke fra scraper. Ølbrygging.no malt-URLer er ikke systematisk hentet. | Oppdater scraper til å hente ølbrygging malt-sider korrekt |

`knust_tilgjengelig: true/false` er erstattet av variant-listen beskrevet under (per-variant `malttype`), og beholdes ikke lenger som eneste kilde til format-informasjon.

#### Variant-modell for malt (Steg F1–F5, 2026-08)

Malt er ikke én SKU per butikk — variantmodellen som håndterer dette er
**implementert og testet i kode** (`modules/malt_packaging.py`,
`modules/smart_shopping_list.py`, 720 tester grønne). Det som gjenstår er
utelukkende å **aktivere modellen med ekte data**: `data/master_malt.json`
har i dag ingen reelle varianter, lagerstatus eller eksakt-mål-data ennå —
scraper/matcher for Vestbryggs faktiske barn-/variantprodukter er skrevet
(Steg F1), men ikke kjørt mot ekte butikkdata i produksjon. Se
`docs/development/PROJECT_MAP.md`/snapshot-dokumentasjon for aktiveringsplanen.

Faktisk datastruktur (skrevet av matcher, lest av `bygg_pakningsforslag()`):

```json
"butikk_match": {
  "vestbrygg": {
    "varianter": [
      { "pakningsstorrelse_gram": 100,   "malttype": "knust", "pris": 15.0, "url": "...", "lagerstatus": "pa_lager" },
      { "pakningsstorrelse_gram": 1000,  "malttype": "knust", "pris": 45.0, "lagerstatus": "pa_lager" },
      { "pakningsstorrelse_gram": 1000,  "malttype": "hel",   "pris": 42.0 },
      { "pakningsstorrelse_gram": 25000, "malttype": "hel",   "pris": 750.0, "lagerstatus": "utsolgt" }
    ]
  }
}
```

Uten et `varianter`-felt (dagens virkelighet for all ekte masterdata)
faller malt tilbake til den eldre, enklere `pakke_kg`-modellen — ingen
regresjon for eksisterende data.

Implementert og testet, men IKKE aktivert med ekte data:

- **Variantmodell** — kombinasjonssøk per malttype (hel/knust), rangert
  etter billigst/minst overkjøp/balansert, med et dekningsgrad-vern
  (`_MAKS_RIMELIG_DEKNINGSGRAD`) som hindrer at store pakninger anbefales
  urimelig for et lite behov.
- **Lagerstatus** — valgfritt `lagerstatus`-felt per variant
  (`pa_lager`/`utsolgt`/`ukjent`, kun brukt av Vestbrygg foreløpig).
  Utsolgte varianter ekskluderes fra alle kjøpsforslag; manglende felt
  tolkes som tilgjengelig (fravær av signal er aldri kjent utsolgt).
- **«Bestill til eksakt mål»** — for knust Vestbrygg-malt, eksplisitt
  brukervalg: mottatt_mengde settes til det eksakte oppskriftsbehovet i
  stedet for SKU-summen (Vestbrygg opplyser at knust malt kan bestilles
  til eksakte mål via melding til salgsavdelingen).
- **25 kg-sekk-sperren** — en hel, ferdigpakket 25 kg-sekk kan aldri inngå
  i «eksakt mål»-løftet (identifisert eksplisitt på gramtall, aldri som
  "største registrerte pakningsstørrelse") — kjøpsresultatet faller da
  tilbake til det ordinære, ikke-eksakte resultatet.

Bevisst IKKE implementert ennå:

- **Hybrid med eksakt restdel** — å la eksakt mål gjelde KUN restmengden
  etter én eller flere hele 25 kg-sekker (i stedet for å sperre eksakt mål
  helt for slike kombinasjoner). Venter på bekreftelse fra Vestbrygg om at
  dette faktisk støttes for kjøp som også inkluderer hele sekker.
- Butikksammenligning (side-om-side pris på tvers av Vestbrygg/Ølbrygging)
  — se `docs/ROADMAP.md`.

---

### master_humle_v2.json / master_gjaer_v2.json

Ingen kjente strukturelle mangler. Ølbrygging-data for gjær (Fermentis US-05, S-04, W-34/70) er ikke tilgjengelig fra Vestbrygg og mangler URL fra ølbrygging.

---

## Feltnavn i master

| Felt | Merknad |
|------|---------|
| `butikk_match.vestbrygg.pris` / `.olbrygging.pris` | Pris per butikk |
| `aliases` | Brukt av matching (`store_matcher.py`) og av "🔗 Match eksisterende" i review — IKKE fjernet/flatenert noe sted lenger, siden det ikke finnes noe eget runtime-lag |
| `verified`, `source` | Metadata fra opprinnelig seed/import |
| `alfa` / `alfa_typisk` (humle) | Begge nøklene forekommer i eksisterende data (historisk navnedrift) |

`calculations.py` og `hop_panel.py` håndterer begge humle-alfa-nøklene med fallback:
`entry.get("alfa") or entry.get("alfa_typisk") or 5.0`

---

## Sync-validering

```
python -m modules.validate_sync
```

**Merk:** dette skriptet sammenligner `data/master_malt.json` mot `data/malt.json` — en fil `app.py` ikke lenger leser (se "Legacy-filer" over). Et avvik her betyr IKKE lenger at appens faktiske malt-data er utdatert; det betyr bare at den ubrukte `malt.json`-kopien har driftet fra master, noe som ikke har noen praktisk konsekvens siden ingenting leser den. Skriptet er ikke oppdatert/fjernet som del av denne dokumentasjonsrunden — se `docs/PROJECT_STATUS_JULI_2026.md` for teknisk gjeld.

---

## Regler

- Rediger **alltid** i masterfilene (`data/master_malt.json`, `data/master_humle_v2.json`, `data/master_gjaer_v2.json`) — de ER runtime-dataene, det finnes ikke noe eget publiseringssteg å huske på lenger.
- Bruk Import-panelets "🧠 Kjør AI-normalisering" og "📋 Pending Review" for skrapet butikkdata i stedet for manuell redigering der det er mulig — begge skriver atomisk med automatisk backup (`modules/master_data_io.py`).
- En manuell redigering av en masterfil er øyeblikkelig live ved neste sideinnlasting av appen — ingen mellomliggende fil å regenerere.
- Nye kategorier i masterdata vises automatisk i UI (dynamisk kategori-lasting).

---

## Historikk

- **2026-08-03 (Steg F6):** Erstattet seksjonen "Fremtidig variant-modell for malt" (som beskrev en ikke-bygget, planlagt modell) med en status-seksjon: variantmodell, lagerstatus, «bestill til eksakt mål» og 25 kg-sekk-sperren er implementert og testet i kode (Steg F1–F5), men ikke aktivert med ekte data ennå. Hybrid med eksakt restdel er fortsatt bevisst ikke bygget.
- **2026-07-28:** Fjernet "📥 Importer til Master DB"-knappen fra Import-panelet. Den skrev flatenerte kopier til `data/malt.json`/`humle.json`/`gjaer.json` — filer `app.py` aldri har lest for humle/gjær, og malt-lastingen ble på et tidspunkt endret til å lese `master_malt.json` direkte også, uten at denne knappen eller dette dokumentet ble oppdatert til å reflektere det. Rettet samtidig: humle-matching/-review pekte mot en manglende fil (`data/master_humle_v0_1.json`) i stedet for `master_humle_v2.json`.
