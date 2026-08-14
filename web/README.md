# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

Web er en responsiv, noe forenklet videreføring av desktop-appen — ikke en visuell redesign. Farger, typografiprinsipp, paneler og resultatpresentasjon er hentet fra `docs/branding/master_design_v1.md`, `ui/branding.py`, `modules/card_template.py` og desktop-appens faktiske kjøretidsutseende (se "Design og navigasjon" under). Historisk runde-for-runde narrativ for hvordan web kom dit den er i dag: [CHANGELOG.md](CHANGELOG.md).

## Sider

Seks sider, hver med ett tydelig formål, delt av samme uttrekkbare venstremeny (åpnes fra hamburgerknappen i mastheaden på alle sider):

| Side | Formål |
|---|---|
| `index.html` — **Oppskriftsbygger** | Bygge oppskriften. Venstre kolonne = det du endrer, høyre kolonne (varm "recipe card"-sone) = det Kvernhaug forteller deg om resultatet. |
| `mine-oppskrifter.html` — **Mine oppskrifter** | Åpne eller slette lagrede oppskrifter. |
| `importer.html` — **Importer oppskrift** | Åpne en `.kbhrecipe`-/JSON-fil, ELLER lime inn ren tekst (samme kontrakt som `ui/sidebar.py`/`modules/recipe_importer.py`) med forhåndsvisning før den legges inn i byggeren. |
| `utskrift.html` — **Utskrift** | Skrive ut den aktive oppskriften — lagret eller ikke — eller en tidligere lagret oppskrift. |
| `hjelp/index.html` — **Hjelp** | How-to/FAQ/bryggehåndbok, se eget avsnitt under. |
| `personvern.html` — **Kontakt og personvern** | Kontakt-e-post og en kort, ærlig forklaring av hvordan V1 behandler data (lokal lagring, ingen analytics/tracking). Lenket fra footer på alle sider, ikke fra hovedmenyen. Lagt til Runde 17. |

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- To **reelle** visningsmoduser — **Bryggelærling** (veiledet, lær mens du brygger) og **Bryggmester** (full kontroll) — samme oppskrift, samme beregningsmotor. Valg skjer i en førstegangsdialog, deretter via status+bryter i venstremenyen (`.modus-knapp`, lagres i `localStorage`); bytte endrer aldri oppskriftsdata. Bryggelærling skjuler brygghuseffektivitet, malt-%-kolonnen, "Bruk prosentfordeling", mål-IBU-feltet og "Skaler oppskrift" — kun enkel kg-flyt. Bryggmester låser opp:
  - **Malt kg ↔ %** (se `js/app.js::brukMaltProsentfordeling()`): kg er alltid fasit og oppdaterer % live. %-redigering er en egen, eksplisitt retning — mens du skriver i ett eller flere %-felt endres kun de feltene + "Prosent-sum" (lest direkte fra synlige input); kg og andre %-felt er urørt til du trykker "Bruk prosentfordeling". Hver rad du manuelt redigerer siden forrige kg-endring/vellykkede fordeling regnes som **låst** og beholdes eksakt; resten fordeles proporsjonalt kun mellom de urørte radene. Total maltvekt bevares alltid. Bevisst, eksplisitt-knapp-basert kontrakt — ikke en ordrett kopi av `ui/malt_panel.py`s enklere "alltid normaliser mot kg-total". Utviklingshistorikk: [CHANGELOG.md](CHANGELOG.md).
  - **Skaler oppskrift** (portert fra `ui/recipe_card.py`s "📐 Skaler oppskrift"): eksplisitt knapp i Lagre/eksporter-panelet. Faktor = målvolum ÷ nåværende batchvolum; skalerer malt (kg) og humle (gram) proporsjonalt, oppdaterer batchvolum. Rører aldri gjær, humletid, alfasyre-overstyring, valgt stil, navn/metadata eller egendefinerte ingrediensfelt.
  - Et mål-IBU→gram-felt per humletilsetning (portert inverse-Tinseth fra `modules/calculations.py::beregn_gram_fra_ibu`, kun via eksplisitt "Beregn gram"-knapp — aldri live).
- Ølstilvalg i arbeidsflyten på venstre side, rett etter Grunndata og før Malt — starter blankt, valgfritt. Stilmatch-*resultatet* vises som ren informasjon i stilpanelet til høyre; kan aldri redigeres der.
- Små "?"-hjelpeknapper på sentrale begreper — åpnes med klikk/tap, lukkes med ✕/Escape/klikk utenfor. "Les mer →"-lenker åpner riktig seksjon i **Hjelp & bryggehåndbok** i ny fane.
- **Hjelp & bryggehåndbok** (`hjelp/index.html`) — how-to/FAQ/oppslagsverk, pluss egne sider for en generell **bryggedagsguide** (`hjelp/bryggedag.html`), **bryggemetoder** (`hjelp/bryggemetoder.html`) og en **utstyrsspesifikk guide** (`hjelp/utstyr-brewzilla.html`, mal for flere).
- Søkbare dropdown-felt for malt, humle, gjær og ølstil. Søket dekker produsent/kategori/opprinnelse/type — bevisst ikke frie smakstags. Malt er gruppert (Basemalt/Karamell/Røstet/Hvete m.fl., samme rekkefølge som `ui/malt_panel.py`).
- Egendefinerte ingredienser — malt/humle/gjær som ikke finnes i biblioteket kan legges inn manuelt, fungerer fullt ut i beregningene og lagres/eksporteres med oppskriften. Humle-alfa kan overstyres per rad også for bibliotekshumle.
- Smakshjul — 18-akset radardiagram (egen SVG-komponent, ingen ekstern lib), oppdateres live.
- Stilmatching mot **Kvernhaug Brygghus sitt eget stilbibliotek** (26 stiler): numerisk nærmeste stil, vennlig tre-nivås stilveiledning ("innenfor"/"litt utenfor"/"tydelig utenfor" — aldri "FEIL"), nærliggende alternativer med "hva mangler" (Bryggmester). Tom oppskrift viser "Ingen stilmatch ennå" (datadrevet sjekk, ikke visuell hardkoding).
- Brukeridentitet — **Ølnavn**, **Brygger**, **Bryggeri** i Grunndata, pluss notatfelt (Bryggmester). Lagres på oppskriften og som en lett brukerpreferanse som forhåndsutfyller nye oppskrifter — uten å overstyre en allerede lastet/importert oppskrift.
- Høyrekortets identitetsblokk viser den manuelt **valgte** Ølstilen (ikke stilmatch-resultatet) pluss KBH-emblemet. Under: alltid synlig **Smaksprofil**, deretter sammenleggbar **Stilanalyse**.
- Lagre oppskrifter lokalt i nettleseren (`localStorage`). Oppskriften du aktivt bygger på autolagres fortløpende som en "aktiv kladd" — se "Aktiv kladd" under.
- **Portabel `.kbhrecipe`-fil** — "Lagre oppskriftsfil" laster ned én fil du kan sende, dele, ta backup av eller flytte til en annen enhet. Åpnes igjen med "Åpne oppskriftsfil" eller på Importer-siden. Rå JSON-eksport finnes fortsatt, nedgradert til et "Avansert"-felt — se "Portabel oppskriftsfil (.kbhrecipe)" under.
- **Ny oppskrift** — "🆕 Ny oppskrift" i Lagre og eksporter-panelet nullstiller byggeren til samme blanke starttilstand som ved førstegangsbesøk (også malt-%-låser, mål-IBU-arbeidsfelt og skaleringsmål), og forhåndsutfyller Brygger/Bryggeri fra den lagrede identitetspreferansen. Spør om bekreftelse først dersom aktiv kladd har meningsfullt innhold — se "Aktiv kladd" under.
- Importere fra **Importer oppskrift**-siden — `.kbhrecipe`-/JSON-fil eller limt inn tekst (fuzzy-matches mot bibliotekene, forhåndsvisning før noe legges inn) — se "Tekstimport" under.
- **Fire egne utskriftsdokumenter**: **Oppskriftsark**, **Handleliste** (nøytral), **Bryggedagsark** (arbeidsark med sjekkliste) og **Bryggelogg** (papirskjema). A4-vennlige, lys bakgrunn/mørk tekst uansett skjermtema. Brukerens identitet er hoveddokumentet; Kvernhaug Brygghus vises kun diskret i en fotnote.
- **Norsk/engelsk UI** (NO er standard) — hele app-grensesnittet (bygger, Mine oppskrifter, Importer, Utskrift, print-dokumentene, Hjelp) finnes som ekte, crawlbare engelske sider under `en/` (samme filnavn/struktur, én katalognivå dypere). Språkvelgeren navigerer mellom dem; recipe-state/modus/identitet er delt (localStorage per origin) og upåvirket av navigasjonen. Se "Språk (NO/EN)" under.

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

**Stilmatchen er IKKE "full BJCP-matching".** Kall den "stilmatching mot Kvernhaug Brygghus sitt stilbibliotek". `data/bjcp_styles.json` er identisk med — men ikke bredere enn — biblioteket appen selv bruker i dag: 26 stiler (25 offisielle BJCP-understiler + tre eksplisitt merkede, ikke-offisielle Kvernhaug-kategorier). Det offisielle BJCP 2021-heftet har rundt 100 understiler; hele stilfamilier (sure øl, saison, barleywine, moderne craft-stiler m.fl.) finnes ikke i biblioteket — verken i web eller desktop.

Selve stilmatch-**logikken** er en full port av `modules/style_engine.py`, men tar ikke med `modules/flavor_conflicts.py`, `modules/flavor_summary.py` eller "blomster-/parfymerisiko"-varselen i `ui/style_panel.py` — egne presentasjonslag utenpå Style Engine, holdt utenfor for å unngå unødvendig kompleksitet i den forenklede versjonen.

## Struktur

```
web/
  index.html          Oppskriftsbygger — venstre: flat skjema-seksjonsflyt, høyre: sticky varm "recipe card"
  mine-oppskrifter.html  Åpne/slette lagrede oppskrifter
  importer.html        Importer oppskrift — fil (.kbhrecipe/JSON) ELLER limt inn tekst, med forhåndsvisning
  utskrift.html        Velg aktiv kladd ELLER en lagret oppskrift, skriv ut de fire dokumentene
  personvern.html       Kontakt og personvern -- e-post, kort forklaring av lokal lagring/ingen tracking (Runde 17)
  css/style.css        Styling — to-lags palett (kaldt app-krom + varm merkevaresone), masthead/drawer, print, hjelp-TOC
  js/chrome.js          Delt "app-krom": masthead-krymping ved scroll + uttrekkbar venstremeny -- på alle sider
  js/calc.js           OG/FG/ABV/IBU/EBC — portert fra modules/calculations.py
  js/flavor.js         Smaksprofil (poeng-beregning) — portert fra modules/flavor_engine.py
  js/radar.js           Smakshjul — vanilla SVG-radardiagram (ingen ekstern lib), tegner flavor.js sine poeng
  js/style.js           Stilmatching mot Kvernhaug-biblioteket — portert fra modules/style_engine.py
  js/veiledning.js       Vennlig tre-nivås stilveiledning -- web-only lag oppå style.js, samme tall
  js/combobox.js        Gjenbrukbar søkbar dropdown (malt/humle/gjær/stil), støtter valgfri gruppering (malt)
  js/help.js             Delt hjelpepopover ("?"-knapper) + "Les mer"-lenker -- web-only, ingen Python-motstykke
  js/i18n.js              NO/EN-motor: t()/settSprak()/gjeldendeSprak(), data-i18n-skanning, stil-/kategori-/
                          maltgruppe-visningslag -- lastes FØRST på alle sider, se "Språk (NO/EN)" under
  js/recipe_engine.js    DOM-fri beregningsorkestrering (effektivt datasett, full beregning, tomt-stilmatch-sjekk) --
                          delt av app.js OG utskrift_page.js, se "Arkitektur: recipe_engine.js" under
  js/kbhrecipe.js         Portabel .kbhrecipe-fil: format/versjon/eksport/parse/filnavn -- delt av app.js OG
                          importer_page.js, se "Portabel oppskriftsfil (.kbhrecipe)" under
  js/recipe_importer.js  Tekstimport: parsing + fuzzy-match -- portert fra modules/recipe_importer.py, se "Tekstimport" under
  js/print.js            Fire utskriftsmaler -- ren presentasjon, tar imot et allerede beregnet kontekst-objekt
  js/app.js             Oppskriftsbygger-siden: skjema, faner, modus, identitet, aktiv-kladd-autolagring
  js/mine_oppskrifter_page.js   Mine oppskrifter-siden
  js/importer_page.js    Importer oppskrift-siden: fil-modus + tekst-modus (kaller recipe_importer.js)
  js/utskrift_page.js    Utskrift-siden: velger aktiv kladd/lagret oppskrift, kaller recipe_engine.js + print.js
  data/malt.json         Generert fra data/master_malt.json — se "Ingrediensdata" under
  data/humle.json        Generert fra data/master_humle_v2.json
  data/gjaer.json         Generert fra data/master_gjaer_v2.json
  data/bjcp_styles.json   Generert fra modules/style_engine.py sitt bjcp_stiler-bibliotek
  assets/branding/kbh_icon_v1.png       Kompakt nav-/drawer-ikon (kråke + pilsglass + møllestein), web-optimert
                                          (260x390) kopi av delt master assets/branding/kbh_icon_v1.png (autoritativ
                                          for web OG desktop, selv om desktop ikke bruker den i dag)
  assets/branding/kbh_emblem.png        Fullt emblem i identitetsblokken, web-optimert kopi av felles master
                                          assets/branding/kbh_emblem_master.png (delt med desktop)
  assets/ui/flag-no.webp                 Norsk flagg, språkvelger (Runde 14) -- uendret kopi av godkjent kildefil
  assets/ui/flag-gb.webp                 Union Jack, språkvelger (Runde 14) -- uendret kopi av godkjent kildefil
  hjelp/index.html        Hjelp & bryggehåndbok -- how-to/FAQ/oppslagsverk, mål for "Les mer"-lenkene
  hjelp/bryggedag.html    Generell bryggedagsguide, 15 steg
  hjelp/bryggemetoder.html   BIAB / all-grain / alt-i-ett -- strukturert for enkel utvidelse
  hjelp/utstyr-brewzilla.html   Første utstyrsspesifikke guide (og uformell mal for flere)
  en/                    GENERERT engelsk speiling av de 9 sidene over (samme filnavn/struktur, én katalognivå
                          dypere) -- håndrediger ALDRI, kjør scripts/generate_web_i18n_pages.py på nytt i stedet.
                          Deler css/js/assets/data med resten av web/ (ikke kopiert inn). Se "Engelsk pre-render
                          (web/en/)" under.
  sitemap.xml             GENERERT -- 18 URL-er (9 sider x NO/EN) med gjensidige hreflang-alternates, samme
                          PAGES-liste som resten av generatoren. Håndrediger ALDRI.
  robots.txt              Håndskrevet, statisk -- Allow: /, peker til sitemap.xml.
```

## Språk (NO/EN)

Runde 14. Vanilla NO/EN-støtte i `js/i18n.js` — ingen npm, ingen build-steg, ingen tredjeparts i18n-bibliotek, samme mønster som resten av web-versjonen. Norsk er primærspråk/default.

**Arkitektur**: `js/i18n.js` er lastet FØRST på hver side (før `chrome.js`) og eksponerer globalt: `t(nøkkel, params)` (enkel `{param}`-substitusjon, ingen pluralregler), `gjeldendeSprak()`, `settSprak(kode)`, `applyI18n(root)`. Statisk HTML dekoreres med `data-i18n="nøkkel"` (setter `textContent`), `data-i18n-html="nøkkel"` (setter `innerHTML` — for tekst med inline-markup som `<strong>`/`<a href="#anker">`) og `data-i18n-placeholder`/`data-i18n-aria-label`/`data-i18n-title`/`data-i18n-alt` (setter tilsvarende attributt) — anvendes automatisk på `DOMContentLoaded`. Dynamiske strenger (statusmeldinger, `confirm()`-dialoger, stilmatch-/veiledningstekst, print-dokumentene) kaller `t()` direkte i JS i stedet for å hardkode norsk. Alle tekster ligger i én flat, dobbel `TEKSTER = { no: {...}, en: {...} }`-ordbok i `i18n.js` — 611 nøkkelpar (Runde 17), verifisert NO/EN-symmetrisk av `scripts/generate_web_i18n_pages.py` ved hver generering.

**Legg til en ny UI-streng**: gi den en dotted-namespace-nøkkel (`side.seksjon.ting`), legg den til i BÅDE `no`- og `en`-objektet i `i18n.js`, referer den via `data-i18n="nøkkel"` i den norske kilde-HTML-en eller `t("nøkkel")` i JS, og kjør generatoren på nytt (se "Engelsk pre-render (web/en/)" under) hvis nøkkelen brukes på en registrert side. Ingen andre filer trenger å vite om det.

**Språkpreferanse**: egen, liten nøkkel (`kvernhaug_web_sprak`) — ALDRI en del av `recipe`-objektet, `.kbhrecipe`-filer, `localStorage`-lagrede oppskrifter eller aktiv kladd. En norsk oppskrift vises like fullt i engelsk UI og omvendt; å bytte språk endrer aldri malt/humle/gjær/stilidentitet/tall.

**Autoritativ språkkilde**: dokumentets EGEN `<html lang>` — satt i HTML-kilden, og i den genererte `/en/`-speilingen — er autoritativ, lest av `gjeldendeSprak()` FØR noe annet (`DOKUMENT_SPRAK`-konstanten i i18n.js). `localStorage`-preferansen er kun fallback for en side uten gyldig `lang`-attributt (skal i praksis aldri inntreffe — alle 18 sider har korrekt `lang` i kilden/generert output). Browser-språkgjetting (`navigator.language`) brukes ikke noe sted — en pre-rendret engelsk side forblir engelsk uansett browserspråk eller tidligere lagret preferanse, og omvendt for norsk. `settSprak(kode)` (bytter DOM-tekst direkte, uten navigasjon) finnes fortsatt som offentlig API og brukes fortsatt internt av `applyI18n()`/dynamiske JS-strenger, men er IKKE lenger koblet til språkvelgerens knapper i UI-et — se "Språkbytte via URL-navigasjon" under.

**Stil-/kategori-/maltgruppenavn — visningslag, ikke ny identitet**: `data/bjcp_styles.json` bruker det norske displaynavnet som eneste, stabile identitet (dict-nøkkel = `oppskrift.valgtStil` = combobox-verdi — ingen egen id-kolonne finnes, verken i web eller i `modules/style_engine.py`). En bred migrering til en separat stabil id ble vurdert og bevisst avvist denne runden — bakoverkompatibilitet med allerede lagrede oppskrifter/`.kbhrecipe`-filer veier tyngre enn en penere datamodell. Løsningen er i stedet et rent presentasjonslag i `i18n.js`: `STIL_NAVN_EN`/`SMAKS_KATEGORI_EN`/`MALT_GRUPPE_LABEL_EN` er NO→EN-oppslagstabeller brukt KUN av `stilVisningsnavn()`/`smaksKategoriVisning()`/`maltGruppeVisning()` ved rendering (combobox-labels, resultatpanel, stilmatch-/veiledningstekst, smakshjul-akser, print-dokumenter). `valgtStil`, `SMAKS_KATEGORIER` (flavor.js) og malt-gruppenes sorteringsrekkefølge forblir norske og uendret overalt i logikk, beregning, lagring og eksport. `style.js` sin scoringsmatematikk er ikke rørt — kun tekstmalene rundt `mangler`/`onsket_sensorisk`/`balanse`/`problemer` er gjort språkbevisste via `t()`.

### Språkbytte via URL-navigasjon (Runde 15B.3)

Språkvelgeren (NO/EN-knappene i header/kompaktnav/uttrekksmeny) er ekte `<a href>`-lenker til søstersiden i det speilede treet, IKKE knapper med JS-håndtert live DOM-bytte — se "Engelsk pre-render" under. `index.html` sin EN-lenke peker på `en/index.html`; `en/hjelp/bryggedag.html` sin NO-lenke peker tilbake på `../../hjelp/bryggedag.html`. Mapping er mekanisk (samme filnavn, katalogstrukturen er speilet 1:1) — ingen stor rute-tabell. Aktiv side er markert statisk (`.aktiv`-klasse + `aria-current="page"`), satt av generatoren/kilde-HTML-en, ikke bare av JS.

**Eneste JS som fortsatt trengs for selve navigasjonen** (`_initSprakvelger()` i i18n.js): bevare et ev. `location.hash` (f.eks. `#steg-7` på en hjelpeside) og `location.search` ved klikk, siden en statisk `href` aldri kan vite hvilket anker brukeren faktisk står på. Ingen routing, ingen historikk-håndtering utover dette.

**State/data er upåvirket av navigasjonen**: recipe-state (`kvernhaug_web_aktiv_kladd`), modus (`kvernhaug_web_modus`), identitet (`kvernhaug_web_identitet`) og lagrede oppskrifter (`kvernhaug_web_oppskrifter`) ligger i `localStorage`, som er delt per origin — ikke per sti. Å navigere fra `index.html` til `en/index.html` er en vanlig, full sideinnlasting til en annen URL, men appens `init()` leser samme localStorage-nøkler uansett hvilken sti siden ble lastet fra, så aktiv oppskrift/modus/identitet gjenopprettes identisk. `.kbhrecipe`-eksport fra en EN-side gir samme `recipe`-payload som fra NO (bortsett fra `lagretDato`/`exportedAt`) — ingen language-felt er introdusert i formatet.

## Engelsk pre-render (web/en/)

`web/en/` er en fullstendig, committet speiling av `web/*.html` og `web/hjelp/*.html` — samme filnavn, samme katalogstruktur, ett nivå dypere. Generert av [`scripts/generate_web_i18n_pages.py`](../scripts/generate_web_i18n_pages.py):

```bash
py -3 scripts/generate_web_i18n_pages.py
```

**Kjør på nytt** hver gang en registrert NO-side eller `TEKSTER` i `i18n.js` endres, og før commit av `web/en/`.

**Arkitektur** (uendret fra Runde 15A-analysen): de norske HTML-filene er ENESTE strukturelle template/fasit; `TEKSTER.en` i `i18n.js` er ENESTE oversettelsesinnhold. Generatoren eier ingen tekst selv — kun transformasjonen: setter `<html lang="en">`, anvender engelsk tekst på alle `data-i18n-*`-attributter (inkl. `data-i18n-html` → ekte markup, ikke escaped tekst — verifisert eksplisitt for `utskrift.tomTekst2` og `hjelp.idx.alfaVariasjon.hvorfor`, de to defektene fra Runde 15B.0), setter engelsk `<title>` fra sidens `data-i18n-tittel-nokkel`, justerer relative `css/js/assets`-stier for én ekstra katalogdybde (`css/style.css` → `../css/style.css` på rotnivå, `../css/style.css` → `../../css/style.css` på hjelp-nivå), kobler språkvelgeren til riktig søsterside, og overskriver canonical/hreflang-lenkene til riktige EN-URL-er (Runde 15B.4, se "URL-kontrakt" under). Vanlige side-til-side-navigasjonslenker (`index.html`, `../index.html`, `bryggedag.html#anker`) røres IKKE — de er allerede riktige fordi hele treet er speilet på samme relative dybde.

**Delt runtime, ingen duplisering**: `web/en/` inneholder KUN generert HTML. `css/`, `js/`, `assets/`, `data/` er IKKE kopiert inn — engelske sider laster nøyaktig samme kjøretidskode og data som norske, via `KBH_ROOT` (Runde 15B.1, delt web-rot uavhengig av katalogdybde). Ingen parallell app, ingen egen datakopi.

**TEKSTER-parsing uten å evaluere JS**: `i18n.js` sin `TEKSTER`-konstant leses som tekst, ikke kjørt — en liten, string-bevisst klamme-balanserer finner `{...}`-blokken (ignorerer `{param}`-plassholdere inni oversettelsesstrenger), to regex-normaliseringer gjør den til gyldig JSON (quote de to bare `no`/`en`-nøklene, fjern trailing commas), og resultatet parses med `json.loads`. NO/EN-nøkkelsymmetri valideres eksplisitt — asymmetri eller en manglende nøkkel referert fra HTML får generatoren til å avbryte hardt, ikke skrive delvis/feil output.

**Guard mot glemte sider**: generatoren skanner faktiske `*.html`-filer i `web/`/`web/hjelp/` og sammenligner mot sin egen `PAGES`-liste — en ny norsk side som ikke er registrert der får generatoren til å avbryte med en tydelig feilmelding, i stedet for stille å mangle en engelsk søster.

**Hygiene**: hver kjøring rydder `web/en/` fra bunnen (kun filer som starter med generator-signaturen `GENERERT AV scripts/generate_web_i18n_pages.py` slettes — en uventet ikke-HTML-fil eller en fil uten signaturen får generatoren til å avbryte UTEN å slette noe, i tilfelle noen ved et uhell har lagt fremmed innhold i `web/en/`). Deterministisk: uendret kildeinnhold gir byte-identisk output ved re-kjøring (`git diff --exit-code web/en/` etter en re-kjøring er en gyldig hygiene-sjekk).

**web/en/ SKAL committes** — samme begrunnelse som `web/data/*.json` (generert av `scripts/generate_web_data.py`, også committet): deploy er fortsatt "last opp `web/`-mappen" uten build-steg eller CI. Håndrediger ALDRI en fil under `web/en/` — endre norsk kilde-HTML eller `TEKSTER` i `i18n.js`, og kjør generatoren på nytt.

### URL-kontrakt (canonical/hreflang) — Runde 15B.4

**Produksjonsdomene**: `https://kvernhaugbrygghus.no` — eneste sted dette er hardkodet (`PROD_BASE` i generatoren). Ingen `www.`-variant er i bruk noe sted i repoet; verifisert eksplisitt før innføring.

**URL-form**: "pene" katalog-URL-er for de to index-sidene (`/` og `/hjelp/` NO, `/en/` og `/en/hjelp/` EN), eksplisitt `.html` for alle andre sider (`/mine-oppskrifter.html`, `/en/hjelp/bryggedag.html` osv.) — standard `DirectoryIndex`-oppførsel på vanlig statisk hosting (Apache/Domeneshop) antatt, ingen server-rewrite konfigurert eller forutsatt av dette repoet. Denne kontrakten brukes KUN til canonical/hreflang/sitemap — selve navigasjonslenkene i HTML-en (drawer, sidenav, "Les mer"-lenker) er URØRT dokument-relative `.html`-lenker, uendret fra Runde 15B.3. Ingen redirect, ingen `www.`-regel, ingen trailing-slash-rewrite er innført.

**Meta description**: samme arkitektur som title — én nøkkel per side og språk i `TEKSTER` (`meta.X.beskrivelse`, 9 par NO/EN), referert fra `<meta name="description" content="..." data-i18n-content="nøkkel">` i HTML-en via en ny `data-i18n-content`-attributt (samme mønster som `data-i18n-alt`/`-title`). Norsk kilde har den norske teksten statisk i `content`; generatoren overskriver den til engelsk for `web/en/`, akkurat som for `data-i18n`/`data-i18n-html`.

**Canonical + hreflang**: alle 18 sider har `<link rel="canonical">` (selvrefererende, absolutt HTTPS) og tre `<link rel="alternate" hreflang="...">` (`no`, `en`, `x-default` → alltid norsk). De 9 norske kilde-sidene har disse fire lenkene satt statisk i `<head>` (satt for NO-konteksten); generatoren overskriver dem til riktige EN-URL-er for `web/en/`-speilingen — samme "generator overskriver, eier ikke teksten selv"-prinsipp som resten av transformasjonen. Verifisert gjensidig for alle 9 par (NO→EN, EN→NO, begge x-default→NO) og selvreferanse for alle 18 canonical-lenker.

**sitemap.xml + robots.txt**: `web/sitemap.xml` genereres deterministisk fra samme `PAGES`-liste som resten av generatoren (ingen egen sitemap-spesifikk liste) — 18 `<url>`-entries med gjensidige hreflang-alternates (xhtml-namespace), ingen `lastmod`/`priority`/`changefreq` (ville enten vært falsk eller ikke-deterministisk). `web/robots.txt` er en liten, håndskrevet statisk fil (`Allow: /`, pekt til sitemap) — ingen sider/mapper er blokkert.

**SEO-guard**: generatoren feiler hardt dersom en registrert side mangler `data-i18n-content` på description-taggen, `<link rel="canonical">`, eller noen av de tre hreflang-lenkene i NO-kilden — ingen stille fallback til en generisk description.

**Ikke gjort ennå** (bevisst utenfor omfanget til Runde 15B): Open Graph, Twitter Cards, structured data/JSON-LD, analytics/tracking, cookie-banner, Search Console-verifiseringsfil. Kan vurderes i en egen, senere runde ved behov.

**Runtime data-paths (Runde 15B.1, forarbeid for pre-render)**: `fetch("data/*.json")`-kallene i `app.js`/`importer_page.js`/`utskrift_page.js` var dokument-relative og ville feilet fra en fremtidig `/en/`- eller `/en/hjelp/`-katalog. Løst med `KBH_ROOT` i `i18n.js` — en global konstant beregnet fra `i18n.js` sin egen `<script src>`-URL (`document.currentScript`, lest synkront ved script-lasting, siden `i18n.js` alltid lastes FØRST og som vanlig `<script src>` på alle sider). `js/`-mappen ligger alltid rett under web-roten uansett hvor dypt selve siden ligger, så `new URL("../", scriptUrl)` gir alltid riktig rot. De 11 `fetch()`-kallene bruker nå `KBH_ROOT + "data/..."` i stedet for `"data/..."`. Ingen produksjonsdomene hardkodet, ingen språkspesifikk path, ingen duplisert `/en/data/`. Testet med midlertidige, script-genererte sider på +1 og +2 katalogdybde (simulerer `/en/` og `/en/hjelp/`) — data lastes korrekt fra felles rot i begge tilfeller; scratch-filene er slettet igjen, ikke en del av repoet.

**Status**: hele app-en er NO/EN — bygger, Mine oppskrifter, Importer, Utskrift, print-dokumentene, first-run modusdialog, hjelpeknapper/tooltips, OG `hjelp/`-sidenes fulle brødtekst (Runde 14B, 2026-08-14): alle fire hjelpesider (kom-i-gang/begrepsforklaringer/FAQ, bryggedagsguide, bryggemetoder, BrewZilla-utstyrsguide) er fullt oversatt til naturlig, idiomatisk bryggeengelsk — ikke maskinoversettelse. Det midlertidige `.hjelp-sprak-merknad`-varselet fra Runde 14 er fjernet sammen med tilhørende CSS, siden det ikke lenger er noe å varsle om.

**Vedlikehold av hjelpeinnhold**: `hjelp/`-sidenes brødtekst følger nøyaktig samme mønster som resten av UI-et — `data-i18n`/`data-i18n-html` på HTML-elementet, nøkkel under `hjelp.idx.*`/`hjelp.dag.*`/`hjelp.metoder.*`/`hjelp.brewzilla.*` i `i18n.js`. `data-i18n-html` (i stedet for vanlig `data-i18n`) brukes der teksten trenger inline-markup (`<strong>`/`<em>`/`<a href="#anker">`) — den setter `innerHTML` i stedet for `textContent`, trygt fordi `TEKSTER` er statisk, selv-forfattet innhold uten noen brukerinput-vei. Legger du til ny hjelpetekst: gi den en nøkkel i samme namespace, fyll inn BÅDE `no`- og `en`-verdien i `i18n.js`, og referer den fra HTML-en. BrewZilla-siden har i tillegg en streng proveniens-konvensjon (se filens toppkommentar) — oversett språket, aldri den epistemiske statusen (produktspesifikasjon vs. Kvernhaug-standardverdi vs. generell forutsetning vs. ikke-verifisert).

## Design og navigasjon

Desktop-appen er designreferansen — web skal kjennes igjen som samme produktfamilie, ikke en egen visuell stil. Fullstendig historikk for hvordan paletten/typografien/logoene fikk sin nåværende form: [CHANGELOG.md](CHANGELOG.md).

- **To-lags palett**: desktop-appen kjører i Streamlits standard mørke tema for alt vanlig UI (kald skifer), IKKE det varme brune fra oppskriftskortet. `--bg`/`--bg-sect`/`--bg-sect-2`/`--body`/`--muted` i `style.css` er derfor kalde som standard (venstre arbeidsområde, Hjelp-sidene, menyen). `--warm-*`-variantene (fra `modules/card_template.py`/`ui/branding.py`) er forbeholdt `.masthead` og `.bygger-hoyre` (høyrekortet) — sistnevnte overskriver `--bg-sect`/`--body`/`--muted` LOKALT som CSS-variabler, slik at vanlige regler automatisk arver riktig varme. `--gold` er aksentfarge i begge soner.
- **Typografi**: `--sans` er standard for alt vanlig skjema-UI. `--serif` er forbeholdt masthead, identitets-/resultatkortet, stilpanelet til høyre og utskriftsdokumentene — speiler desktops bruk av serif kun for merkevareelementer og oppskriftskortet.
- **Venstre kolonne = flat seksjonsflyt, ikke boks-i-boks**: `.panel` er bevisst uten egen bakgrunn/kant/skygge — kun en tynn nøytral toppstrek + gul seksjonsetikett skiller seksjonene. Høyrekortet bruker IKKE `.panel`; det er sin egen, varme "recipe card"-boks.
- **To atskilte logo-roller**: et lite **kompakt nav-/drawer-ikon** (`kbh_icon_v1.png`, i mastheaden/kompakt sticky-nav og venstremenyen) og et **fullt emblem** (høyrekortets identitetsblokk). `.kompaktnav-logo`/`.sidemeny-logo` bruker `object-fit: contain` (ikke `cover`) fordi motivet er en uklippet komposisjon. Ingen av delene er formelt den rundmedaljongen med buet `KVERNHAUG BRYGGHUS`-tekst som `docs/branding/master_design_v1.md` beskriver, og ingen er laget som favicon/mikrovariant ennå (se backlog i `docs/ROADMAP.md`).
- **Bred masthead + krympende sticky header**: `.masthead` speiler `ui/branding.py` sin `render_header()`-komposisjon i full sidebredde. `web/js/chrome.js` legger til `.is-kompakt` når `scrollY > 40` — CSS krymper logo/skrift og skjuler motto/undertekst.
- **Uttrekkbar venstremeny** (`.sidemeny`, hamburgerknapp i mastheaden på alle sider): speiler desktop-appens `st.sidebar` (`ui/sidebar.py`) som hovednavigasjon. Overlay-drawer på både desktop og mobil.
- **Layout**: `index.html` bruker `app.py` sin faktiske `st.columns([2.0, 1.2])`-fordeling (≈ 62,5 % / 37,5 %) som mal for `.byggerlayout`s to kolonner på desktop-bredde. Bruddpunkt 1000px — under det er alt én kolonne, ingen sticky.
- **Hjelp-sidene** har en lokal innholdsmeny (`.hjelp-toc`) ved siden av hovedinnholdet på desktop (≥900px, sticky venstrekolonne), kollapser til horisontal chip-rad på mobil.
- **Sticky høyrekort vs. masthead**: `web/js/chrome.js` måler mastheadens løpende høyde og skriver den til CSS-variabelen `--masthead-h`, som `.bygger-hoyre` sin `top: calc(var(--masthead-h) + 1rem)` leser — offsetten følger headeren nøyaktig i begge tilstander (ekspandert/kompakt).

## Aktiv kladd (arkitektur)

Oppskriften som står i byggeren akkurat nå autolagres fortløpende til en egen localStorage-nøkkel (`kvernhaug_web_aktiv_kladd`) — ved hver beregning, ikke bare når du trykker "Lagre oppskrift". Dette gjør tre ting mulig uten backend:

1. Laster du `index.html` på nytt (eller lukker og åpner fanen igjen), gjenopprettes akkurat det du holdt på med.
2. **Utskrift**-siden kan bruke den aktive, *også ulagrede*, oppskriften direkte — du trenger ikke lagre først for å skrive ut. Utskrift-siden leser kun denne nøkkelen; den skriver aldri til den, så å forhåndsvise en lagret oppskrift der overskriver aldri det du faktisk holder på med i byggeren.
3. **Mine oppskrifter**-siden sin "Åpne i byggeren" og fil-/tekstimport bruker samme nøkkel som håndoverleveringsmekanisme: skriv oppskriften dit, naviger til `index.html`, som gjenoppretter den derfra ved oppstart. Byggerens "Ny oppskrift", byggerens "Åpne oppskriftsfil", Importer-sidens import og Mine oppskrifter sin "Åpne i byggeren" spør alle brukeren om bekreftelse før en aktiv kladd med meningsfullt innhold overskrives eller nullstilles (se `oppskriftHarInnhold()` i `js/kbhrecipe.js`) — men aldri før en fil er validert (ugyldige filer avvises med en statusmelding, ingen dialog), og aldri når byggeren allerede er reelt tom.

## Portabel oppskriftsfil (.kbhrecipe)

Vanlige brukere skal kunne lagre, dele, ta backup av og gjenåpne en oppskrift som ÉN fil, uten å måtte forholde seg til "rå JSON" som konsept. `js/kbhrecipe.js` er en liten, delt modul (brukt av `app.js` og `importer_page.js`) som gjør nettopp dette rundt det eksisterende oppskriftsobjektet (samme form som `samleOppskrift()`/`_gjenopprettOppskrift()` allerede bruker) — ingen parallell datamodell.

**Format** — en liten, versjonert JSON-wrapper:

```json
{
  "format": "kbhrecipe",
  "version": 1,
  "exportedAt": "2026-08-14T12:00:00.000Z",
  "generator": "Kvernhaug Brygghus",
  "recipe": { "navn": "...", "malt": [...], "humle": [...], "..." : "..." }
}
```

`recipe` inneholder alt `samleOppskrift()` allerede lagrer (ølnavn, brygger, bryggeri, batchvolum, effektivitet, notater, valgt stil, malt/humle inkl. egendefinerte ingredienser og alfa-overstyring, gjær/gjærCustom, utgjæringsoverstyring) — aldri UI-tilstand som Lærling/Mester-visning, malt-%-edit-locks, mål-IBU-arbeidsfelt eller drawer-state. Filendelsen er `.kbhrecipe`, internt UTF-8 JSON (brukeren trenger aldri vite det); et trygt filnavn bygges fra ølnavnet (`tryggFilnavn()` — fjerner kun faktisk ugyldige Windows-tegn, translittererer bevisst ikke Æ/Ø/Å/Unicode), med fallback til `Kvernhaug-oppskrift.kbhrecipe` hvis navn mangler.

**Eksport**: "📄 Lagre oppskriftsfil (.kbhrecipe)" i byggerens Lagre og eksporter-panel bygger wrapperen fra aktiv oppskrift og laster den ned direkte (Blob + midlertidig object URL, ingen server involvert). Rå JSON-eksport (samme enkle oppskriftsobjekt, uten wrapper) finnes fortsatt, men er nedgradert til et lukket "Avansert"-felt for debugging/videre bearbeiding.

**Import/autodeteksjon**: "📂 Åpne oppskriftsfil" i byggeren og "⬆️ Velg en .kbhrecipe-fil" på Importer oppskrift-siden bruker samme `parseKbhRecipeInnhold()`. Filen leses lokalt i nettleseren (aldri opplastet noe sted) og skilles automatisk mellom tre tilfeller: (1) ny `.kbhrecipe`-wrapper med kjent `version` → oppskriften pakkes ut og lastes; (2) eldre, rå oppskrifts-JSON uten wrapper → gjenkjennes på at objektet har minst ett kjent oppskriftsfelt og lastes akkurat som før, ingen manuell konvertering nødvendig; (3) alt annet (tom fil, ugyldig JSON, vilkårlig JSON, manglende `recipe`, ukjent/nyere `version`) → avvises med en vennlig, norsk statusmelding (aldri "INVALID"/"ERROR"/stacktrace til bruker). En gyldig fil laster oppskriften inn som aktiv kladd og går inn i nøyaktig samme aktive oppskriftsmodell som vanlig redigering — ingen egen "importert oppskrift"-modus.

## Tekstimport

`importer.html` sin tekstfane porter kontrakten fra `ui/sidebar.py` sin "📥 Importer oppskrift fra tekst"-expander (`modules/recipe_importer.py`) til `js/recipe_importer.js`: samme linjeformater (`5 kg Maris Otter`, `300 g CaraMunich`, `20 g Magnum 60 min`, `90% Maris Otter` + `Total malt: 6 kg`, en gjærlinje uten mengde), samme flyt (lim inn → "🔍 Analyser" → forhåndsvisning av matchet/ikke-gjenkjent → "✅ Legg inn i oppskriftsbygger"), og samme terskel (0.6) for fuzzy-treff. Selve regex-parsingen (`parseRecipeText()`) er en direkte 1:1-port av `parse_recipe_text()`. Fuzzy-matchingen bruker en egen JS-implementasjon av samme Ratcliff/Obershelp-algoritme som Pythons `difflib.SequenceMatcher.ratio()` — samme prinsipp og terskel, men ikke bit-for-bit identisk output i alle kanttilfeller (to uavhengige implementasjoner, se "Vedlikehold" under). Ubekreftede/uklare treff vises tydelig atskilt fra matchede — aldri stille gjettet inn i oppskriften.

## Arkitektur: recipe_engine.js

`recipe_engine.js` inneholder hele beregningsorkestreringen (effektivt datasett, OG/FG/ABV/IBU/EBC, smaksprofil, stilmatch) som rene funksjoner — tar en oppskrift + ingrediens-/stildata inn og returnerer et ferdig resultat, uten å røre `document` (bortsett fra `escHtml()`, som trenger et DOM-element for escaping). Dette lar Utskrift-siden beregne en VILKÅRLIG valgt oppskrift (aktiv kladd eller en lagret oppskrift) uten byggerens skjema til stede. `app.js` og `utskrift_page.js` bruker begge denne filen; selve beregningsformlene i `calc.js`/`flavor.js`/`style.js` er separate og uendret av denne orkestreringen.

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

`js/combobox.js`, `js/radar.js`, `js/help.js`, `js/veiledning.js`, `js/recipe_engine.js`, `js/kbhrecipe.js`, `js/print.js`, `js/chrome.js`, `js/app.js`, `js/mine_oppskrifter_page.js`, `js/importer_page.js` og `js/utskrift_page.js` er egne web-komponenter uten Python-motstykke — ingenting å synkronisere. `js/recipe_importer.js` er et delvis unntak: parsingen er en eksakt port av `modules/recipe_importer.py`, men fuzzy-matchingen er en uavhengig JS-implementasjon av samme algoritme (se "Tekstimport" over) — hold linjeformat-regexene i sync manuelt hvis `parse_recipe_text()` endres. `veiledning.js` bruker tall som `style.js` allerede regner ut (`felt_avvik`, et web-only tillegg i `analyserStilOgBalanse` utover det Python-originalen returnerer) — selve scoren/rangeringen er uendret av dette.

Ved endring i `modules/calculations.py`, `modules/style_engine.py` eller `modules/flavor_engine.py`: oppdater tilsvarende JS-fil i samme omgang, og kjør `scripts/generate_web_data.py` på nytt hvis stilgrensene eller ingrediensdataene endret seg.

## Egendefinerte ingredienser

Løses uten å røre `calc.js`/`flavor.js`/`style.js` i det hele tatt: for hver beregning bygger `recipe_engine.js` sin `byggEffektiveDatasett()` et midlertidig oppslagsobjekt (`{...biblioteket, [egen_id]: egendefinertData}`) som sendes inn akkurat som det vanlige biblioteket. Egendefinerte ingredienser og alfa-overstyring på biblioteks-humle skriver **aldri** til `maltData`/`humleData`/`gjaerData` selv, og påvirker aldri andre rader eller andre oppskrifter. De lagres kun som en del av den enkelte oppskriften (localStorage og JSON-eksport), ikke i noe eget, delt bibliotek.

## Brukeridentitet

Oppskriften er brukerens, ikke Kvernhaug Brygghus sin. `Ølnavn`, `Brygger` og valgfritt `Bryggeri` ligger i Grunndata-panelet og lagres som del av selve oppskriften (`samleOppskrift()`/`_gjenopprettOppskrift()` i `app.js`) — de følger dermed localStorage og JSON-eksport/import akkurat som resten av oppskriften. I tillegg lagres `brygger`/`bryggeri` i en egen, lett localStorage-nøkkel (`kvernhaug_web_identitet`) som kun brukes til å forhåndsutfylle feltene på en **ny** oppskrift — den overstyrer aldri en allerede lastet eller importert oppskrift, og påvirker aldri det delte ingrediensbiblioteket.

## Print-arkitektur

De fire utskriftene lever på en egen side (`utskrift.html`), ikke inne i byggeren — printer du derfra, skriver du ALDRI ut byggerskjermen. `utskrift_page.js` velger en oppskrift (aktiv kladd eller en lagret oppskrift), kjører den gjennom `recipe_engine.js` sin `beregnOppskrift()`, og gir det ferdige resultatet videre til `print.js` sine rene `bygg*Html(ctx)`-funksjoner — de leser ALDRI live DOM-globaler selv, kun kontekst-objektet de får inn (`byggDokumentKontekst()`). Hver mal injiseres i sin egen skjulte `.utskrift-dokument`-container. `body[data-utskrift="..."]` (satt rett før `window.print()`) styrer via `@media print` i `style.css` hvilket ark som faktisk vises på papiret — resten av siden skjules automatisk, og attributten fjernes igjen ved `afterprint`.

Handlelisten er bevisst nøytral: kun navn/mengde/alfasyre — aldri butikk, pris, URL, lagerstatus eller pantry. Bryggeloggen er et rent papirskjema uten digital lagring (fylles ut med penn). Alle fire er A4-vennlige med lys bakgrunn/mørk tekst uansett skjermtema. Brukerens ølnavn/brygger/bryggeri er hoveddokumentets identitet; Kvernhaug Brygghus vises kun diskret i en fotnote.

## Hjelp & bryggehåndbok

`hjelp/` er egne, statiske sider (samme `style.css` for visuell identitet, ingen delt kjøretid med byggeren) som åpnes i ny fane fra "📖 Hjelp"-lenken i header og fra "? → Les mer"-lenker i hjelpepopoverne. `hjelp/index.html` samler kom-i-gang, begrepsforklaringer (med stabile anker-IDer som `#og`/`#ibu`/`#stilmatching` osv. — disse er "Les mer"-lenkenes mål og må ikke endres uten å oppdatere `HJELP_TEKSTER.lesMer` i `help.js` samtidig), ingrediensstoff og FAQ. `hjelp/bryggedag.html`, `hjelp/bryggemetoder.html` og `hjelp/utstyr-brewzilla.html` er egne sider for henholdsvis den fulle bryggedagsguiden, metodesammenligning og utstyrsspesifikke guider.

`hjelp/utstyr-brewzilla.html` skiller eksplisitt mellom fire slags tall/påstander, ingen behandlet som mer autoritative enn de faktisk er: (A) faktisk produktspesifikasjon, (B) Kvernhaugs egne standardverdier for beregning/utstyrsprofil (fra `modules/equipment.py`, merket som appens egne forutsetninger), (C) generelle bryggeforutsetninger som ikke er BrewZilla-spesifikke, og (D) Kvernhaugs egen praktiske anbefaling. Det som ikke er verifisert i det hele tatt, står i en egen, tydelig merket seksjon (`.hjelp-uverifisert`) — ingen oppdiktet teknisk informasjon.
