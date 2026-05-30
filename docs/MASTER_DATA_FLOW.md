# Kvernhaug Brygghus — Master Data Flow

## Oversikt

```
Nettbutikker
   │
   ▼
raw_data/*_raw.json          ← skrapet rådata (scraper)
   │
   ▼  (AI-normalisering via Import-panel)
raw_data/*_review.json       ← unmatched entries til manuell review
   │
   ▼  (Importer til Master DB via Import-panel)
data/master_*.json           ← canonical masterdata (rediger HER)
   │
   ├──► data/malt.json       ← generert runtime-fil for malt (IKKE editer)
   │
   └──► data/humle.json      ← generert men IKKE brukt av appen
        data/gjaer.json      ← generert men IKKE brukt av appen
```

---

## Filer og ansvar

### Canonical masterfiler (rediger her)

| Fil | Innhold | Brukes av |
|-----|---------|-----------|
| `data/master_malt.json` | Alle malt-entries med aliases, butikk_match, tags | Import-panel → malt.json |
| `data/master_humle_v2.json` | Alle humle-entries | Appen direkte |
| `data/master_gjaer_v2.json` | Alle gjær-entries | Appen direkte |

> **`master_malt.json` — filnavn vs. format:**
> Filen er i praksis v2-format (samme struktur som `master_humle_v2.json` og `master_gjaer_v2.json`:
> `butikk_match`, `aliases`, `verified`, nested store-data).
> Filnavnet er gammelt og vil på et passende tidspunkt renames til `master_malt_v2.json`.
> **Ikke rename ennå** — krever oppdatering av `store_matcher.py`, `import_panel.py`, og `app.py`.

### Runtime-fil (IKKE editer direkte)

| Fil | Generert fra | Brukes av |
|-----|-------------|-----------|
| `data/malt.json` | `master_malt.json` via Import-panel | `app.py` → UI og beregninger |

> `malt.json` er en flattenert versjon av master_malt.json:
> `butikk_match.vestbrygg.pris` → `pris_vestbrygg`, aliaser fjernes, etc.
> Filen har en `_meta`-nøkkel øverst som markerer den som generert.
> `app.py` filtrerer automatisk `_`-nøkler ved lasting.

### Ubrukte genererte filer

`data/humle.json` og `data/gjaer.json` skrives av Import-panel men leses ikke
av appen. Appen leser masterfiler direkte for humle og gjær.

---

## Dataflyt i detalj

### Malt

```
master_malt.json
  display_name, produsent, kategori, ebc, potensiale,
  maks_prosent, smakstags, kategorier, anbefalte_stiler,
  aliases, butikk_match, verified, source
         │
         │ Import-panel (Importer til Master DB)
         ▼
malt.json
  display_name, produsent, kategori, ebc, potensiale,
  maks_prosent, smakstags, kategorier, anbefalte_stiler,
  knust_tilgjengelig, pris_vestbrygg, pris_olbrygging
         │
         │ app.py → last_json_data("malt.json")
         ▼
malt_database (dict i minnet)
         │
         ├── malt_panel.py   → dropdown + pris-visning
         ├── recipe_context.py → OG, EBC, flavor-beregninger
         └── supplier_panel.py → priser
```

### Humle og Gjær

```
master_humle_v2.json / master_gjaer_v2.json
         │
         │ app.py → last_json_data("master_humle_v2.json")
         ▼
humle_database / gjaer_database (dict i minnet)
         │
         ├── hop_panel.py / yeast_panel.py → dropdown
         └── recipe_context.py → IBU, ABV, flavor
```

---

## Kjente mangler og svakheter i masterdata

### master_malt.json

| Mangel | Status | Fremtidig løsning |
|--------|--------|-------------------|
| Malt-varianter mangler i `butikk_match` | Malt selges i flere formater og størrelser — ingen av dem er modellert per butikk | Se variant-modell nedenfor |
| `knust_tilgjengelig: true/false` er utilstrekkelig | Booleanen sier ikke hvilke størrelser som finnes knust, eller URL/pris per variant | Erstattes av variant-liste når crushed-støtte prioriteres |
| Ølbrygging.no malt-data er svakere enn Vestbrygg | Mange `pris_olbrygging`-verdier er satt manuelt, ikke fra scraper. Ølbrygging.no malt-URLer er ikke systematisk hentet. | Oppdater scraper til å hente ølbrygging malt-sider korrekt |

#### Fremtidig variant-modell for malt

Malt er ikke én SKU per butikk — det er en liste med varianter. Kjente varianter per Vestbrygg:

| Format | Størrelse | Modelleres i V1? |
|--------|-----------|-----------------|
| Knust  | 100 g     | Ja              |
| Knust  | 1 kg      | Ja              |
| Hel    | 1 kg      | Ja              |
| Hel    | 25 kg     | Nei (ignoreres) |

Foreslått datastruktur (ikke implementert ennå):

```json
"butikk_match": {
  "vestbrygg": {
    "varianter": [
      { "format": "knust", "pakke_gram": 100,  "pris": 0.0, "url": "" },
      { "format": "knust", "pakke_gram": 1000, "pris": 0.0, "url": "" },
      { "format": "hel",   "pakke_gram": 1000, "pris": 0.0, "url": "" }
    ]
  }
}
```

Shopping-listen må da velge én variant per kjøp (standard: 1 kg hel, med mulighet for knust).
Feltet `knust_tilgjengelig` i master kan fjernes når variant-modellen er på plass.

---

### master_humle_v2.json / master_gjaer_v2.json

Ingen kjente strukturelle mangler. Ølbrygging-data for gjær (Fermentis US-05, S-04, W-34/70) er ikke tilgjengelig fra Vestbrygg og mangler URL fra ølbrygging.

---

## Feltforskjeller mellom master og runtime

| Felt i master | Felt i runtime (malt.json) | Merknad |
|--------------|---------------------------|---------|
| `butikk_match.vestbrygg.pris` | `pris_vestbrygg` | Flattenert |
| `butikk_match.olbrygging.pris` | `pris_olbrygging` | Flattenert |
| `aliases` | — (fjernes) | Kun til fuzzy-matching i importer |
| `verified`, `source` | — (fjernes) | Intern metadata |
| `alfa_typisk` (humle) | `alfa` (humle.json) | Renaming ved runtime-generering |

`calculations.py` og `hop_panel.py` håndterer begge nøkler med fallback:
`entry.get("alfa") or entry.get("alfa_typisk") or 5.0`

---

## Sync-validering

Kjør for å oppdage drift mellom master og runtime:

```
python -m modules.validate_sync
```

Sjekker:
- Antall entries master == runtime
- Alle required felter finnes i runtime
- Ingen kategorier mangler i runtime

---

## Regler

- Rediger **alltid** i masterfiler, aldri direkte i runtime-filer
- Etter endringer i `master_malt.json`: klikk "Importer til Master DB" i appen
- Nye kategorier i masterdata vises automatisk i UI (dynamisk kategori-lasting)
- Bruk `python -m modules.validate_sync` etter større dataendringer
