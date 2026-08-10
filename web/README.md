# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- To visningsmoduser — **Bryggelærling** ("veiledet modus, lær mens du brygger") og **Bryggmester** ("full kontroll, alle detaljer tilgjengelig") — samme oppskrift, samme beregningsmotor, ren CSS-styrt visningsbryter. Bytte mellom dem endrer aldri oppskriftsdata.
- Små "?"-hjelpeknapper på sentrale begreper (OG/FG/ABV/IBU/EBC/utgjæring/alfasyre/stilmatch/smakshjul) — åpnes med klikk/tap (ikke hover), lukkes med ✕/Escape/klikk utenfor. Der et større hjelpeemne finnes får popoveren en "Les mer →"-lenke som åpner riktig seksjon i **Hjelp & bryggehåndbok** (`hjelp/`) i ny fane, uten å forstyrre oppskriften i byggeren.
- **Hjelp & bryggehåndbok** (`hjelp/index.html`) — how-to/FAQ/oppslagsverk (kom i gang, forstå oppskriften, ingredienser, FAQ), pluss egne sider for en generell **bryggedagsguide** (`hjelp/bryggedag.html`, 15 steg med hva/hvorfor/følg med på/vanlige feil), **bryggemetoder** (`hjelp/bryggemetoder.html`: BIAB/all-grain/alt-i-ett) og en **utstyrsspesifikk guide** (`hjelp/utstyr-brewzilla.html`, første av flere planlagte — kildeforankrede tall er tydelig skilt fra det som ennå ikke er verifisert)
- Søkbare dropdown-felt (skriv for å filtrere) for malt, humle, gjær og ølstil — ingen lange nedtrekkslister å bla gjennom. Søket dekker mer enn produktnavn: malt kan finnes på produsent/kategori, humle på opprinnelsesland/type, gjær på produsent — men bevisst **ikke** på frie smakstags, som ville gjort treffene for brede.
- Egendefinerte ingredienser — malt/humle/gjær som ikke finnes i biblioteket kan legges inn manuelt (navn + tekniske grunnverdier), fungerer fullt ut i beregningene og lagres/eksporteres med oppskriften. Humle-alfa kan i tillegg overstyres per rad for bibliotekshumle også (varierer fra pose til pose).
- Smakshjul — 18-akset radardiagram (egen SVG-komponent, ingen ekstern lib) som oppdaterer seg live når malt/humle/gjær endres
- Stilmatching mot **Kvernhaug Brygghus sitt eget stilbibliotek** (26 stiler): numerisk nærmeste stil, en vennlig tre-nivås stilveiledning ("innenfor" / "litt utenfor" / "tydelig utenfor" — aldri "FEIL"/"UGYLDIG"), nærliggende alternativer med "hva mangler" (Bryggmester), og manuelt valg av en spesifikk stil å sjekke oppskriften mot
- Brukeridentitet — **Ølnavn**, **Brygger** og valgfritt **Bryggeri**-felt i Grunndata, pluss et valgfritt notatfelt (Bryggmester). Brygger/bryggeri lagres på selve oppskriften (localStorage + JSON) og som en lett, egen brukerpreferanse som forhåndsutfyller nye oppskrifter — uten å overstyre en allerede lastet eller importert oppskrift.
- Lagre oppskrifter lokalt i nettleseren (`localStorage`) — ingenting sendes til noen server
- Eksportere/importere oppskriften som JSON (inkl. egendefinerte ingredienser og identitet)
- **Fire egne utskriftsdokumenter** (ikke bare et print av skjermbildet): **Oppskriftsark**, **Handleliste** (nøytral — ingen butikk/pris/lagerstatus), **Bryggedagsark** (arbeidsark med sjekkliste og felt for faktiske målinger) og **Bryggelogg** (tomt papirskjema til utfylling med penn). A4-vennlige, lys bakgrunn/mørk tekst uansett skjermtema. Brukerens ølnavn/brygger/bryggeri er hoveddokumentets identitet — Kvernhaug Brygghus vises kun diskret i en fotnote ("Laget med Kvernhaug Brygghus Oppskriftsbygger").

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

**Stilmatchen er IKKE "full BJCP-matching".** Kall den "stilmatching mot Kvernhaug Brygghus sitt stilbibliotek". `data/bjcp_styles.json` er identisk med — men ikke bredere enn — det biblioteket appen selv bruker i dag: 26 stiler (25 offisielle BJCP-understiler + Historisk Wiesn-Märzen, Tradisjonelt Norsk Gårdsøl/Kveik og Tradisjonelt Norsk Juleøl, alle tre eksplisitt merket som ikke-offisielle Kvernhaug-kategorier). Det offisielle BJCP 2021-stilheftet har rundt 100 understiler; hele stilfamilier (sure øl, saison, barleywine/sterk ale, amerikansk lager/cream ale, brown/scotch ale, øvrige hveteøl, moderne craft-stiler som session/black/brut IPA, frukt-/krydder-/trelagrede spesialøl) finnes ikke i biblioteket i det hele tatt — verken i web eller i desktop-appen.

Selve stilmatch-**logikken** er derimot en full port av `modules/style_engine.py` (numerisk avvik, styrkeklynge-demping, sensorisk `smak_krav` via en port av `modules/flavor_engine.py`, signaturbonus/-straff og de harde takene), men tar **ikke** med `modules/flavor_conflicts.py`, `modules/flavor_summary.py` (narrativ smakstekst) eller den ekstra "blomster-/parfymerisiko"-varselen i `ui/style_panel.py` — de er egne presentasjonslag utenpå Style Engine, ikke del av selve stilmatchingen, og holdt bevisst utenfor for å unngå unødvendig kompleksitet i den forenklede versjonen.

## Struktur

```
web/
  index.html          Oppskriftsbygger-UI
  css/style.css        Styling — Master Design V1-palett (mørk, gull/kobber/pergament), print-stilark, hjelpesider
  js/calc.js           OG/FG/ABV/IBU/EBC — portert fra modules/calculations.py
  js/flavor.js         Smaksprofil (poeng-beregning) — portert fra modules/flavor_engine.py
  js/radar.js           Smakshjul — vanilla SVG-radardiagram (ingen ekstern lib), tegner flavor.js sine poeng
  js/style.js           Stilmatching mot Kvernhaug-biblioteket — portert fra modules/style_engine.py
  js/veiledning.js       Vennlig tre-nivås stilveiledning -- web-only lag oppå style.js, samme tall
  js/combobox.js        Gjenbrukbar søkbar dropdown (malt/humle/gjær/stil)
  js/help.js             Delt hjelpepopover ("?"-knapper) + "Les mer"-lenker -- web-only, ingen Python-motstykke
  js/print.js            Fire utskriftsmaler (oppskriftsark/handleliste/bryggedagsark/bryggelogg) -- web-only
  js/app.js             UI-logikk: Lærling/Mester, identitet, egendefinerte ingredienser, localStorage, eksport/import
  data/malt.json         Generert fra data/master_malt.json — se "Ingrediensdata" under
  data/humle.json        Generert fra data/master_humle_v2.json
  data/gjaer.json         Generert fra data/master_gjaer_v2.json
  data/bjcp_styles.json   Generert fra modules/style_engine.py sitt bjcp_stiler-bibliotek
  hjelp/index.html        Hjelp & bryggehåndbok -- how-to/FAQ/oppslagsverk, mål for "Les mer"-lenkene
  hjelp/bryggedag.html    Generell bryggedagsguide, 15 steg
  hjelp/bryggemetoder.html   BIAB / all-grain / alt-i-ett -- strukturert for enkel utvidelse
  hjelp/utstyr-brewzilla.html   Første utstyrsspesifikke guide (og uformell mal for flere)
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

`js/combobox.js`, `js/radar.js`, `js/help.js`, `js/veiledning.js` og `js/print.js` er egne web-komponenter uten Python-motstykke — ingenting å synkronisere. `veiledning.js` bruker riktignok tall som `style.js` allerede regner ut (`felt_avvik`, lagt til per stil i `analyserStilOgBalanse` som et web-only tillegg utover det Python-originalen returnerer) — selve scoren/rangeringen er uendret av dette.

Ved endring i `modules/calculations.py`, `modules/style_engine.py` eller `modules/flavor_engine.py`: oppdater tilsvarende JS-fil i samme omgang, og kjør `scripts/generate_web_data.py` på nytt hvis stilgrensene eller ingrediensdataene endret seg.

## Egendefinerte ingredienser

Løses uten å røre `calc.js`/`flavor.js`/`style.js` i det hele tatt: for hver beregning bygger `app.js` sin `_effektiveDatasett()` et midlertidig oppslagsobjekt (`{...biblioteket, [egen_id]: egendefinertData}`) som sendes inn akkurat som det vanlige biblioteket. Egendefinerte ingredienser og alfa-overstyring på biblioteks-humle skriver **aldri** til `maltData`/`humleData`/`gjaerData` selv, og påvirker aldri andre rader eller andre oppskrifter. De lagres kun som en del av den enkelte oppskriften (localStorage og JSON-eksport), ikke i noe eget, delt bibliotek.

## Brukeridentitet

Oppskriften er brukerens, ikke Kvernhaug Brygghus sin. `Ølnavn`, `Brygger` og valgfritt `Bryggeri` ligger i Grunndata-panelet og lagres som del av selve oppskriften (`samleOppskrift()`/`_gjenopprettOppskrift()` i `app.js`) — de følger dermed localStorage og JSON-eksport/import akkurat som resten av oppskriften. I tillegg lagres `brygger`/`bryggeri` i en egen, lett localStorage-nøkkel (`kvernhaug_web_identitet`) som kun brukes til å forhåndsutfylle feltene på en **ny** oppskrift — den overstyrer aldri en allerede lastet eller importert oppskrift, og påvirker aldri det delte ingrediensbiblioteket.

## Print-arkitektur

De fire utskriftene i `js/print.js` er **egne dokumentmaler**, ikke et print av byggerskjermen. Hver mal bygges fra live oppskriftsdata (samme `lesMaltRader()`/`lesHumleRader()`/`_effektiveDatasett()` som beregningene bruker) rett før utskrift, og injiseres i sin egen skjulte `.utskrift-dokument`-container i `index.html`. `body[data-utskrift="..."]` (satt av `print.js` rett før `window.print()`) styrer via `@media print` i `style.css` hvilket ark som faktisk vises på papiret — resten av siden skjules automatisk for den utskriften, og attributten fjernes igjen ved `afterprint`.

Handlelisten er bevisst nøytral: kun navn/mengde/alfasyre — aldri butikk, pris, URL, lagerstatus eller pantry. Bryggeloggen er et rent papirskjema uten digital lagring denne runden (fylles ut med penn). Alle fire er A4-vennlige med lys bakgrunn/mørk tekst uansett skjermtema. Brukerens ølnavn/brygger/bryggeri er hoveddokumentets identitet; Kvernhaug Brygghus vises kun diskret i en fotnote.

## Hjelp & bryggehåndbok

`hjelp/` er egne, statiske sider (samme `style.css` for visuell identitet, ingen delt kjøretid med byggeren) som åpnes i ny fane fra "📖 Hjelp"-lenken i header og fra "? → Les mer"-lenker i hjelpepopoverne. `hjelp/index.html` samler kom-i-gang, begrepsforklaringer (med stabile anker-IDer som `#og`/`#ibu`/`#stilmatching` osv. — disse er "Les mer"-lenkenes mål og må ikke endres uten å oppdatere `HJELP_TEKSTER.lesMer` i `help.js` samtidig), ingrediensstoff og FAQ. `hjelp/bryggedag.html`, `hjelp/bryggemetoder.html` og `hjelp/utstyr-brewzilla.html` er egne sider for henholdsvis den fulle bryggedagsguiden, metodesammenligning og utstyrsspesifikke guider.

`hjelp/utstyr-brewzilla.html` skiller eksplisitt mellom fire slags tall/påstander, ingen behandlet som mer autoritative enn de faktisk er: (A) faktisk produktspesifikasjon (kjelekapasitet 35 L — ligger i produktnavnet), (B) Kvernhaugs egne standardverdier for beregning/utstyrsprofil (fordampning, dead space — hentet fra `modules/equipment.py`, men uttrykkelig merket som appens egne forutsetninger, ikke bekreftet produsentspesifikasjon), (C) generelle bryggeforutsetninger som ikke er BrewZilla-spesifikke i det hele tatt (meskeforhold, kornabsorpsjon), og (D) Kvernhaugs egen praktiske anbefaling (maks pre-boil ~30 L, en sikkerhetsmargin — ikke et produsenttall). Det som faktisk ikke er verifisert i det hele tatt, står i en egen, tydelig merket seksjon (`.hjelp-uverifisert`) — ingen oppdiktet teknisk informasjon. Filen har en HTML-kommentar øverst med dette proveniens-prinsippet, som fungerer som uformell mal for fremtidige utstyrsguider (f.eks. Grainfather).
