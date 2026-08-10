# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- Søkbare dropdown-felt (skriv for å filtrere) for malt, humle, gjær og ølstil — ingen lange nedtrekkslister å bla gjennom
- BJCP-stilmatch: numerisk nærmeste stil, nærliggende alternativer med "hva mangler", og manuelt valg av en spesifikk stil å sjekke oppskriften mot
- Lagre oppskrifter lokalt i nettleseren (`localStorage`) — ingenting sendes til noen server
- Skrive ut oppskriften eller eksportere den som JSON

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

Stilmatchen er en full port av `modules/style_engine.py` (numerisk avvik, styrkeklynge-demping, sensorisk `smak_krav` via en port av `modules/flavor_engine.py`, signaturbonus/-straff og de harde takene), men tar **ikke** med `modules/flavor_conflicts.py`, `modules/flavor_summary.py` (narrativ smakstekst) eller den ekstra "blomster-/parfymerisiko"-varselen i `ui/style_panel.py` — de er egne presentasjonslag utenpå Style Engine, ikke del av selve stilmatchingen, og holdt bevisst utenfor for å unngå unødvendig kompleksitet i den forenklede versjonen.

## Struktur

```
web/
  index.html         Oppskriftsbygger-UI
  css/style.css       Styling — Master Design V1-palett (mørk, gull/kobber/pergament), print-stilark
  js/calc.js          OG/FG/ABV/IBU/EBC — portert fra modules/calculations.py
  js/flavor.js        Smaksprofil (poeng-beregning) — portert fra modules/flavor_engine.py
  js/style.js         BJCP-stilmatch — portert fra modules/style_engine.py
  js/combobox.js      Gjenbrukbar søkbar dropdown (malt/humle/gjær/stil)
  js/app.js           UI-logikk, localStorage, print/eksport
  data/malt.json       Kuratert maltdatasett (navn, potensiale, ebc, kategorier)
  data/humle.json      Kuratert humledatasett (navn, alfa, kategorier)
  data/gjaer.json       Kuratert gjærdatasett (navn, attenuation, kategorier)
  data/bjcp_styles.json BJCP-stilbibliotek (22 stiler + 1 Kvernhaug/historisk kategori)
```

`kategorier`-feltet i malt/humle/gjær-dataene er smakstag-poengene fra masterdataene, kun inkludert der de faktisk finnes (ikke alle gjærtyper har dem) — brukes utelukkende av `flavor.js` til den sensoriske delen av stilmatchen.

## Kjøre lokalt

Må serveres over HTTP (ikke åpnes direkte som `file://`), siden `fetch()` av `data/*.json` krever det:

```bash
cd web
py -3 -m http.server 8000
# åpne http://localhost:8000
```

## Vedlikehold av data og formler

Ingen delt kjøretid mellom Python- og JS-siden — alt under `js/` er manuelle porter som må oppdateres for hånd hvis kilden i `modules/` endres:

| Web-fil | Portert fra |
|---|---|
| `js/calc.js` | `modules/calculations.py` |
| `js/flavor.js` | `modules/flavor_engine.py` (kun poeng-beregningen, ikke Plotly-diagrammet) |
| `js/style.js` | `modules/style_engine.py` (signatur-ID-settene er kopiert verbatim — hold dem i sync manuelt) |

`data/malt.json`, `data/humle.json`, `data/gjaer.json` er et engangs-ekstrahert utdrag av `data/master_malt.json`/`master_humle_v2.json`/`master_gjaer_v2.json` (navn + beregnings-/smaksrelevante felt — ingen pris eller butikklenker). `data/bjcp_styles.json` er tilsvarende ekstrahert fra `bjcp_stiler`-dictet i `modules/style_engine.py`. Begge regenereres ved behov med engangsskript (ikke committet, kjørt manuelt fra `modules/`-kildene) — ikke automatisert i en build-pipeline siden `web/` ikke har noen.

Ved endring i `modules/calculations.py`, `modules/style_engine.py` eller `modules/flavor_engine.py`: oppdater tilsvarende JS-fil i samme omgang, og re-ekstraher `data/bjcp_styles.json` hvis stilgrensene endret seg.
