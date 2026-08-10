# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- To visningsmoduser — **Bryggelærling** ("veiledet modus, lær mens du brygger") og **Bryggmester** ("full kontroll, alle detaljer tilgjengelig") — samme oppskrift, samme beregningsmotor, ren CSS-styrt visningsbryter. Bytte mellom dem endrer aldri oppskriftsdata.
- Små "?"-hjelpeknapper på sentrale begreper (OG/FG/ABV/IBU/EBC/utgjæring/alfasyre/stilmatch/smakshjul) — åpnes med klikk/tap (ikke hover), lukkes med ✕/Escape/klikk utenfor
- Søkbare dropdown-felt (skriv for å filtrere) for malt, humle, gjær og ølstil — ingen lange nedtrekkslister å bla gjennom. Søket dekker mer enn produktnavn: malt kan finnes på produsent/kategori, humle på opprinnelsesland/type, gjær på produsent — men bevisst **ikke** på frie smakstags, som ville gjort treffene for brede.
- Egendefinerte ingredienser — malt/humle/gjær som ikke finnes i biblioteket kan legges inn manuelt (navn + tekniske grunnverdier), fungerer fullt ut i beregningene og lagres/eksporteres med oppskriften. Humle-alfa kan i tillegg overstyres per rad for bibliotekshumle også (varierer fra pose til pose).
- Smakshjul — 18-akset radardiagram (egen SVG-komponent, ingen ekstern lib) som oppdaterer seg live når malt/humle/gjær endres
- Stilmatching mot **Kvernhaug Brygghus sitt eget stilbibliotek** (26 stiler): numerisk nærmeste stil, en vennlig tre-nivås stilveiledning ("innenfor" / "litt utenfor" / "tydelig utenfor" — aldri "FEIL"/"UGYLDIG"), nærliggende alternativer med "hva mangler" (Bryggmester), og manuelt valg av en spesifikk stil å sjekke oppskriften mot
- Lagre oppskrifter lokalt i nettleseren (`localStorage`) — ingenting sendes til noen server
- Skrive ut oppskriften, eller eksportere/importere den som JSON (inkl. egendefinerte ingredienser)

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

**Stilmatchen er IKKE "full BJCP-matching".** Kall den "stilmatching mot Kvernhaug Brygghus sitt stilbibliotek". `data/bjcp_styles.json` er identisk med — men ikke bredere enn — det biblioteket appen selv bruker i dag: 26 stiler (25 offisielle BJCP-understiler + Historisk Wiesn-Märzen, Tradisjonelt Norsk Gårdsøl/Kveik og Tradisjonelt Norsk Juleøl, alle tre eksplisitt merket som ikke-offisielle Kvernhaug-kategorier). Det offisielle BJCP 2021-stilheftet har rundt 100 understiler; hele stilfamilier (sure øl, saison, barleywine/sterk ale, amerikansk lager/cream ale, brown/scotch ale, øvrige hveteøl, moderne craft-stiler som session/black/brut IPA, frukt-/krydder-/trelagrede spesialøl) finnes ikke i biblioteket i det hele tatt — verken i web eller i desktop-appen.

Selve stilmatch-**logikken** er derimot en full port av `modules/style_engine.py` (numerisk avvik, styrkeklynge-demping, sensorisk `smak_krav` via en port av `modules/flavor_engine.py`, signaturbonus/-straff og de harde takene), men tar **ikke** med `modules/flavor_conflicts.py`, `modules/flavor_summary.py` (narrativ smakstekst) eller den ekstra "blomster-/parfymerisiko"-varselen i `ui/style_panel.py` — de er egne presentasjonslag utenpå Style Engine, ikke del av selve stilmatchingen, og holdt bevisst utenfor for å unngå unødvendig kompleksitet i den forenklede versjonen.

## Struktur

```
web/
  index.html          Oppskriftsbygger-UI
  css/style.css        Styling — Master Design V1-palett (mørk, gull/kobber/pergament), print-stilark
  js/calc.js           OG/FG/ABV/IBU/EBC — portert fra modules/calculations.py
  js/flavor.js         Smaksprofil (poeng-beregning) — portert fra modules/flavor_engine.py
  js/radar.js           Smakshjul — vanilla SVG-radardiagram (ingen ekstern lib), tegner flavor.js sine poeng
  js/style.js           Stilmatching mot Kvernhaug-biblioteket — portert fra modules/style_engine.py
  js/veiledning.js       Vennlig tre-nivås stilveiledning -- web-only lag oppå style.js, samme tall
  js/combobox.js        Gjenbrukbar søkbar dropdown (malt/humle/gjær/stil)
  js/help.js             Delt hjelpepopover ("?"-knapper) -- web-only, ingen Python-motstykke
  js/app.js             UI-logikk: Lærling/Mester, egendefinerte ingredienser, localStorage, print/eksport/import
  data/malt.json         Generert fra data/master_malt.json — se "Ingrediensdata" under
  data/humle.json        Generert fra data/master_humle_v2.json
  data/gjaer.json         Generert fra data/master_gjaer_v2.json
  data/bjcp_styles.json   Generert fra modules/style_engine.py sitt bjcp_stiler-bibliotek
```

## Ingrediensdata — sannhetskilde

Web-versjonen har **ingen egen, manuelt vedlikeholdt ingrediensdatabase**. `data/malt.json`, `data/humle.json`, `data/gjaer.json` og `data/bjcp_styles.json` genereres av [`scripts/generate_web_data.py`](../scripts/generate_web_data.py) (kjøres fra repo-roten: `py -3 scripts/generate_web_data.py`), som leser direkte fra desktop-appens masterdata (`data/master_malt.json`, `data/master_humle_v2.json`, `data/master_gjaer_v2.json`) og fra `bjcp_stiler`-dictet i `modules/style_engine.py` (via `ast.literal_eval` på selve kildekode-literalen, ikke en hånd-transkribert kopi). Scriptet er deterministisk — uendret kildedata gir byte-identisk output ved re-kjøring.

**Kjør scriptet på nytt** hver gang masterdataene eller BJCP-biblioteket i `style_engine.py` endres, og før enhver release.

Feltene som tas med per ingrediens:

| | Beregningskritisk | Presentasjon/søk | Bevisst utelatt |
|---|---|---|---|
| Malt | `potensiale`, `ebc` | `produsent`, `kategori`, `display_group`, `smakstags` | `maks_prosent`, `anbefalte_stiler`, `knust_tilgjengelig`, `aliases`, `canonical_style` |
| Humle | `alfa` | `opprinnelse`, `type`, `smakstags` | `aliases` |
| Gjær | `attenuation` | `produsent`, `kategori`, `gjaertype`, `smakstags` | `beskrivelse` (finnes kun på 1 av 103 gjærtyper i masterdata — ikke representativt), `aliases` |
| Alle | `kategorier` (Flavor Engine-poeng, kun tatt med der de finnes) | — | `source`, `verified` (dataprovenans, ikke relevant for sluttbruker) |

**Aldri tatt med, uansett**: `butikk_match` (pris/URL/lagerstatus/pakningsstørrelse/butikkspesifikke `search_terms`) og all pantry-/lagerdata. Dette er en offentlig side — kommersielle avtaler og brukerens private lagerdata hører aldri hjemme her.

`smakstags` brukes kun til visning — **ikke** til søk (ville gjort treffene for brede, f.eks. ville "sitrus" truffet dusinvis av humler) og **ikke** til selve Flavor Engine-poengene (som utelukkende bruker det numeriske `kategorier`-feltet).

## Kjøre lokalt

Må serveres over HTTP (ikke åpnes direkte som `file://`), siden `fetch()` av `data/*.json` krever det:

```bash
cd web
py -3 -m http.server 8000
# åpne http://localhost:8000
```

## Vedlikehold av formler og stillogikk

Ingen delt kjøretid mellom Python- og JS-siden. `js/calc.js`, `js/flavor.js` og `js/style.js` er manuelle porter som må oppdateres for hånd hvis kilden i `modules/` endres:

| Web-fil | Portert fra |
|---|---|
| `js/calc.js` | `modules/calculations.py` |
| `js/flavor.js` | `modules/flavor_engine.py` (kun poeng-beregningen, ikke Plotly-diagrammet) |
| `js/style.js` | `modules/style_engine.py` (signatur-ID-settene er kopiert verbatim — hold dem i sync manuelt) |

`js/combobox.js`, `js/radar.js`, `js/help.js` og `js/veiledning.js` er egne web-komponenter uten Python-motstykke — ingenting å synkronisere. `veiledning.js` bruker riktignok tall som `style.js` allerede regner ut (`felt_avvik`, lagt til per stil i `analyserStilOgBalanse` som et web-only tillegg utover det Python-originalen returnerer) — selve scoren/rangeringen er uendret av dette.

Ved endring i `modules/calculations.py`, `modules/style_engine.py` eller `modules/flavor_engine.py`: oppdater tilsvarende JS-fil i samme omgang, og kjør `scripts/generate_web_data.py` på nytt hvis stilgrensene eller ingrediensdataene endret seg.

## Egendefinerte ingredienser

Løses uten å røre `calc.js`/`flavor.js`/`style.js` i det hele tatt: for hver beregning bygger `app.js` sin `_effektiveDatasett()` et midlertidig oppslagsobjekt (`{...biblioteket, [egen_id]: egendefinertData}`) som sendes inn akkurat som det vanlige biblioteket. Egendefinerte ingredienser og alfa-overstyring på biblioteks-humle skriver **aldri** til `maltData`/`humleData`/`gjaerData` selv, og påvirker aldri andre rader eller andre oppskrifter. De lagres kun som en del av den enkelte oppskriften (localStorage og JSON-eksport), ikke i noe eget, delt bibliotek.
