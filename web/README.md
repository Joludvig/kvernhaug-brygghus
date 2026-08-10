# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- Lagre oppskrifter lokalt i nettleseren (`localStorage`) — ingenting sendes til noen server
- Skrive ut oppskriften eller eksportere den som JSON

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen BJCP-stilmatch, vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

## Struktur

```
web/
  index.html       Oppskriftsbygger-UI
  css/style.css     Styling (lys/mørk modus, print-stilark)
  js/calc.js        Beregningsformler — portert fra modules/calculations.py
  js/app.js         UI-logikk, localStorage, print/eksport
  data/*.json       Kuratert malt-/humle-/gjærdatasett (navn + beregningsrelevante felt)
```

## Kjøre lokalt

Må serveres over HTTP (ikke åpnes direkte som `file://`), siden `fetch()` av `data/*.json` krever det:

```bash
cd web
py -3 -m http.server 8000
# åpne http://localhost:8000
```

## Vedlikehold av data og formler

`js/calc.js` er en manuell JS-port av `modules/calculations.py` (OG, EBC, FG/ABV, IBU). Ingen delt kjøretid mellom Python- og JS-siden — hvis formlene endres i `modules/calculations.py`, må `js/calc.js` oppdateres manuelt i samme omgang.

`data/*.json` er en engangs-ekstrahert delmengde av `data/master_malt.json`, `data/master_humle_v2.json` og `data/master_gjaer_v2.json` (kun navn + `potensiale`/`ebc`/`alfa`/`attenuation` — ingen pris eller butikklenker). Regenereres ved behov med et engangsscript som leser masterdataene og skriver de kuraterte filene på nytt; ikke automatisert i en build-pipeline siden `web/` ikke har noen.
