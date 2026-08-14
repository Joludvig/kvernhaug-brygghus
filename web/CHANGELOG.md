# Kvernhaug Brygghus — Web changelog

Historisk, runde-for-runde narrativ for web-versjonens utvikling: hvorfor ting endret seg, hva det var før, og hvilken runde som gjorde det. For dagens arkitektur/kontrakt, se [README.md](README.md) — dette dokumentet er kun historikk og trengs sjelden for vanlig arbeid.

Nyeste runde øverst.

## Runde 15B.4 — SEO-metadata + sitemap + robots (2026-08-14)

Fullførte den tekniske SEO-grunnmuren for alle 16 språk-URL-ene — siste steg i SEO-/pre-render-arbeidet fra Runde 15A. Produksjonsdomene `https://kvernhaugbrygghus.no` (ingen `www.`-variant funnet noe sted i repoet, verifisert før bruk). URL-kontrakt: "pene" katalog-URL-er for de to index-sidene (`/`, `/hjelp/`, `/en/`, `/en/hjelp/`), eksplisitt `.html` for resten — kun brukt til canonical/hreflang/sitemap, selve navigasjonslenkene i HTML-en er urørt fra Runde 15B.3 (ingen redirect/rewrite innført eller forutsatt).

8 nye NO/EN-nøkkelpar (`meta.X.beskrivelse`) i `i18n.js` — én meta description per sidetype, naturlig og konkret, ingen keyword-stuffing, BrewZilla-teksten holder samme A/B/C/D/E-proveniensskille som resten av siden (Kvernhaug-standardverdier fremstilles aldri som produsentspesifikasjoner). Ny `data-i18n-content`-attributt i `applyI18n()`, samme mønster som `data-i18n-alt`/`-title`, kun brukt av `<meta name="description">`.

De 8 norske kildesidene fikk `<meta name="description">` + `<link rel="canonical">` + tre `<link rel="alternate" hreflang="no/en/x-default">` satt statisk i `<head>` (kirurgisk exact-string-innsetting rett etter `<title>`, samme minimal-diff-prinsipp som Runde 15B.3 — ingen BeautifulSoup-reserialisering av norsk kilde, som ville gitt stor, irrelevant formatteringsstøy). `scripts/generate_web_i18n_pages.py` overskriver disse fire lenkene til riktige EN-URL-er for `web/en/`-speilingen — samme "generator eier transformasjon, ikke tekst"-prinsipp. Generatoren feiler nå også hardt dersom en registrert side mangler description-nøkkel, canonical eller noen av de tre hreflang-lenkene i NO-kilden.

Ny `web/sitemap.xml` (generert, 16 `<url>`-entries, gjensidige hreflang-alternates via xhtml-namespace, ingen `lastmod`/`priority`/`changefreq` — ville vært enten falsk eller ikke-deterministisk data) og `web/robots.txt` (håndskrevet, `Allow: /`, peker til sitemap). Begge bygget fra generatorens eksisterende `PAGES`-liste, ingen egen sidestruktur-liste.

Verifisert: rå HTTP-respons (ingen JS) for alle 16 sider har korrekt `<html lang>`, unik tittel, meta description (>40 tegn), nøyaktig 1 selvrefererende canonical, og nøyaktig 3 hreflang-lenker med riktige verdier. Eksplisitt gjensidighetstest for alle 8 NO/EN-par (NO→EN, EN→NO, begge x-default→NO) — alle 8 par perfekte. `sitemap.xml` validert som velformet XML med riktig namespace, nøyaktig 16 URL-er, ingen duplikater, ingen asset-/data-URL-er, ingen `lastmod`. `robots.txt` validert. Full browser-regresjon (Chromium + Firefox × 4 viewport × 16 sider): 789/789 sjekker OK, pluss egne sjekker på at EN+nb-NO-browserlokalitet og NO+en-US-browserlokalitet begge forblir riktig språk (ekte `/en/`-sider, ikke prototype), og at hash bevares gjennom et faktisk språkbytte. Lett re-verifisering av state/`.kbhrecipe`/modus gjennom navigasjon — uendret, ingen schema-endring. 17 nye Python-tester (URL-kontrakt, description/canonical-guards, hreflang-gjensidighet, sitemap-struktur/-determinisme, robots.txt) — 40 generator-tester totalt, 899 Python-tester totalt, 0 feil. Determinisme bekreftet (to kjøringer → identisk `web/en/**` og `sitemap.xml`).

Ikke innført: Open Graph, Twitter Cards, structured data/JSON-LD, analytics/tracking, cookie-banner, Search Console-verifisering, `www.`-regler, trailing-slash-rewrites — bevisst utenfor omfanget, kan vurderes i en egen senere runde.

## Runde 15B.3 — Generator + committet /en/-tre (2026-08-14)

Hovedleveransen i SEO-/pre-render-arbeidet (Runde 15A-analysen): en committet, ekte engelsk speiling `web/en/**` — 8 statiske HTML-sider, samme filnavn/struktur som norsk, én katalognivå dypere. Generert av ny [`scripts/generate_web_i18n_pages.py`](../scripts/generate_web_i18n_pages.py) (BeautifulSoup, ingen nye avhengigheter). Norsk HTML forblir eneste strukturelle template; `TEKSTER.en` i `i18n.js` forblir eneste oversettelsesinnhold — generatoren eier ingen tekst selv. Verifisert: rå HTTP-respons (ingen JS kjørt) viser korrekt `<html lang="en">`, engelsk `<title>` og engelsk brødtekst direkte i HTML-en — reelt crawlbart, ikke bare rendret riktig etter JS.

`TEKSTER` parses fra `i18n.js` uten å evaluere JS: en liten, string-bevisst klamme-balanserer (ignorerer `{param}`-plassholdere inni oversettelsestekst) finner objektlitteralen, to regex-normaliseringer gjør den til gyldig JSON, og `json.loads` gjør resten. 590 nøkkelpar, verifisert NO/EN-symmetrisk. Generatoren feiler hardt (ingen delvis/stille output) ved: NO/EN-asymmetri, en HTML-referert nøkkel som mangler i `TEKSTER.en`, eller en norsk `*.html`-side som ikke er registrert i generatorens eksplisitte `PAGES`-liste — sistnevnte forhindrer at en fremtidig ny norsk side glemmes uten engelsk søster.

Språkvelgeren (NO/EN-knappene) gikk fra live DOM-bytte til ekte `<a href>`-navigasjon mellom speilede søstersider — de 8 norske kilde-HTML-filene fikk sine `.sprak-knapp`-elementer konvertert fra `<button>` til `<a>` (mekanisk, samme surgical exact-string-replacement på alle 8 filer, minimal diff). Mapping er ren katalog-aritmetikk (`index.html` ↔ `en/index.html`, `hjelp/bryggedag.html` ↔ `en/hjelp/bryggedag.html`), ingen rutetabell. Eneste gjenværende JS på selve knappene: bevare `location.hash`/`location.search` ved klikk (f.eks. `#steg-7` på en hjelpeside), siden en statisk `href` ikke kan vite hvilket anker brukeren står på — verifisert eksplisitt at hash bevares begge veier. `settSprak()` er beholdt som offentlig API (fortsatt i bruk av `applyI18n()`/dynamiske strenger) men ikke lenger koblet til knappene.

`i18n.js` sin `_oppdaterSprakvelgerUI()` bruker nå `aria-current="page"` i stedet for `aria-pressed` (riktig ARIA-semantikk for lenker, ikke toggle-knapper). CSS: `.sprak-knapp` fikk `text-decoration: none` + `:visited`/`:hover`/`:focus-visible`-nøytralisering (anchor-standardstiler som ikke fantes på `<button>`).

Verifisert via HTTP (Chromium): recipe-state, modus, identitet og beregnede tall (OG/FG/ABV/IBU/EBC) er 100 % identiske før/etter en ekte NO→EN-navigasjon (localStorage er delt per origin, ikke per sti — appens vanlige `init()`/aktiv-kladd-gjenoppretting trenger ingen endring). `.kbhrecipe`-eksport fra EN gir samme `recipe`-payload som fra NO (ekskl. tidsstempler). Importer/Mine oppskrifter/Utskrift sine interne handoff-navigasjoner (`window.location.href = "index.html"`) forblir i riktig språktre siden de er dokument-relative og hele treet er speilet symmetrisk. Full regresjon: Chromium + Firefox × [1920, 1280, 768, 375] × 16 sider (8 NO + 8 EN) — 914/914 sjekker OK (lang, 0 overflow, 0 konsoll-/sidefeil, 0 feilede requests, korrekt aktiv-språk-styling/flagg, `/en/index.html` sine malt/humle/gjær/stil-datasett > 0). EN-side + nb-NO-browserlokalitet forblir engelsk; NO-side + en-US-browserlokalitet forblir norsk (samme kontrakt som Runde 15B.2, nå verifisert på ekte generert output).

23 nye Python-tester (`tests/test_generate_web_i18n_pages.py`): TEKSTER-parsing, klamme-balansering rundt `{param}`, PAGES-guard (inkl. at en uregistrert side faktisk feiler), asset-sti-justering (rot- og hjelp-dybde), `data-i18n-html`-markup (ikke escaped tekst), språkvelger-href-mapping, manglende-nøkkel-feil, og determinisme (to kjøringer gir byte-identisk output — bekreftet både i test og manuelt via SHA-256).

Ingen `meta description`/`canonical`/`hreflang`/`sitemap.xml`/`robots.txt` ennå — egen fremtidig Runde 15B.4, ikke påbegynt.

## Runde 15B.2 — Dokument-språk som autoritativ kilde (2026-08-14)

Forarbeid for en fremtidig pre-rendret `/en/`-struktur (Runde 15A-analysen), del 2. Tidligere leste `gjeldendeSprak()` `localStorage` (og falt tilbake til `navigator.language`-gjetting) FØR dokumentets egen `<html lang>` — og skrev deretter det resultatet rett tilbake til `<html lang>` ved hver sideinnlasting. Det betydde at en fremtidig pre-rendret engelsk side kunne blitt vist på norsk (eller omvendt) avhengig av en tidligere lagret preferanse eller browserspråk, uavhengig av hva URL-en/HTML-kilden faktisk sa — SEO-kritisk galt.

Ny prioritet i `gjeldendeSprak()`: (1) dokumentets egen `<html lang>` (lest i en `DOKUMENT_SPRAK`-konstant helt i toppen av `i18n.js`, FØR noe annet kjører), (2) `localStorage` KUN som fallback for en side uten gyldig `lang`-attributt (skal aldri inntreffe i dag — alle 8 sider har korrekt `lang="no"` i kilden, bekreftet), (3) norsk default. `_nettleserSprakGjetning()` og all `navigator.language`-basert språkvalg er fjernet helt.

`localStorage`-nøkkelen (`kvernhaug_web_sprak`) endrer rolle fra "autoritativ side-språk" til "husket preferanse for live-bytte" — `settSprak()` (dagens same-URL NO↔EN-veksling) er uendret og skriver fortsatt til den, men en FULL reload av en norsk kilde-URL lar alltid `lang="no"` fra kilden vinne igjen, uansett hva som sist var lagret eller vist. Verifisert med to prototype-tester (midlertidig `<html lang="en">`-kopi av `index.html` + nb-NO browserlocale + `localStorage="no"` → forblir engelsk; ekte `index.html` + en-US browserlocale + `localStorage="en"` → forblir norsk), samt full NO→EN→NO-regresjon på alle 8 sider (tekst/tittel/help-markup/modus-status/localStorage-isolasjon/`.kbhrecipe`-payload uendret). Ingen `/en/`-struktur, URL-strategi eller språkvelger-navigasjon innført ennå.

## Runde 15B.1 — Dybde-uavhengig data-fetch (2026-08-14)

Forarbeid for en fremtidig pre-rendret `/en/`-struktur (Runde 15A-analysen). De 11 `fetch("data/*.json")`-kallene i `app.js`/`importer_page.js`/`utskrift_page.js` var dokument-relative og ville feilet fra en dypere katalog som `/en/` eller `/en/hjelp/`. Løst med `KBH_ROOT`, en global konstant i `i18n.js` beregnet fra scriptets egen `<script src>`-URL (`document.currentScript`) — ingen hardkodet domene, ingen språkspesifikk path, ingen duplisert `/en/data/`. Verifisert med midlertidige, script-genererte testsider på +1 og +2 katalogdybde; dagens rotside-oppførsel er uendret. Ingen URL-strategi, generator eller `/en/`-struktur er innført ennå — se README "Runtime data-paths".

## Runde 14B — Engelsk hjelp/bryggehåndbok (2026-08-14)

Fullførte NO/EN-dekningen fra Runde 14: alle fire `hjelp/`-sidenes brødtekst (`index.html` sitt kom-i-gang/begrepsforklaringer/ingredienser/ordliste/FAQ, `bryggedag.html` sine 15 steg, `bryggemetoder.html` sine tre metoder, `utstyr-brewzilla.html` sin BrewZilla-referanse) er nå oversatt til naturlig, idiomatisk bryggeengelsk — ikke maskinoversettelse. Samme arkitektur som resten av appen (`data-i18n`/`t()`/`TEKSTER` i `i18n.js`), ingen ny språkmodell. 282 nye nøkkelpar (NO+EN) under `hjelp.idx.*`/`hjelp.dag.*`/`hjelp.metoder.*`/`hjelp.brewzilla.*`.

Ny `data-i18n-html`-attributt lagt til i `applyI18n()` (`i18n.js`): identisk med `data-i18n`, men setter `innerHTML` i stedet for `textContent`. Nødvendig fordi hjelpeteksten har mye inline-markup (`<strong>`, `<em>`, ankerlenker som `<a href="#ibu">`) som ville forsvunnet med ren tekst-erstatning. Trygt fordi `TEKSTER`-ordboken er statisk, egen-forfattet innhold — aldri brukerinput — så ingen XSS-vektor oppstår.

BrewZilla-sidens proveniens-skille (faktisk produktspesifikasjon vs. Kvernhaug-standardverdi for beregning vs. generell bryggeforutsetning vs. praktisk Kvernhaug-anbefaling vs. ikke-verifisert) er bevart nøyaktig i engelsk tekst — kun språket endret, aldri den epistemiske statusen. Alle tall (35 L kjelekapasitet, 30 L pre-boil-varsel, 4,0 L/time fordampning, 2,0 L dead space, 3,2 L/kg meskeforhold, 1,0 L/kg kornabsorpsjon) uendret og fortsatt metriske — ingen imperial-konvertering.

Det midlertidige `.hjelp-sprak-merknad`-varselet fra Runde 14 (og tilhørende CSS) er fjernet nå som det ikke lenger er noe delvis-oversatt innhold å varsle om.

`docs/ROADMAP.md` sin fremtidige SEO-/pre-render-runde (egen crawlbar `/en/`-URL-struktur) er uendret og fortsatt ikke påbegynt — Runde 14B løste kun innholdsdekning, ikke URL-strategien fra Runde 14.

Manuell kontroll av førsteutkastet fant fire konsistensproblemer, rettet i et eget engelsk redaksjonspass før commit (kun EN-verdier i `i18n.js`, norsk urørt): moduspar-navnene («Homebrewer»/«Brewmaster») matchet ikke de faktiske UI-navnene og er nå konsekvent «Brewing Apprentice»/«Brewing Master»; standard-callouten («Why you should care:») var litt markedsføringspreget og er standardisert til «Why this matters:» (21 forekomster); «Save a Recipe»-avsnittet anbefalte fortsatt rå JSON-eksport som normal måte å flytte en oppskrift på — beskriver nå `.kbhrecipe` som primær portabel fil (Runde 13-kontrakten), med JSON beholdt som avansert/bakoverkompatibelt alternativ; «Open or Import a Recipe» skiller nå tydelig mellom å åpne en fil (`.kbhrecipe`/legacy JSON) og å importere fri tekst, med dagens faktiske knappetekster. Samme gjennomgang identifiserte at flere Bryggmester-features (batchskalering, malt kg/%, «Bruk prosentfordeling», mål-IBU, aktiv-kladd-beskyttelse, selve språkvalget) ikke er dokumentert i Help i det hele tatt — verken norsk eller engelsk — flagget som eget fremtidig innholdspunkt i `docs/ROADMAP.md`, ikke løst i denne runden.

## Runde 14 — Norsk/engelsk UI (2026-08-14)

Vanilla NO/EN-støtte (`js/i18n.js`) på tvers av hele app-UI-et — bygger, Mine oppskrifter, Importer, Utskrift, de fire print-dokumentene, first-run modusdialog og hjelpeknapper/tooltips. Ingen npm, ingen build-steg, ingen tredjeparts i18n-bibliotek. Norsk er fortsatt primærspråk/default; språkbytte skjer live (ingen reload) via en delt `kvernhaug:sprakendret`-hendelse, og lagres i en egen `kvernhaug_web_sprak`-nøkkel som aldri er del av selve oppskriftsdataen — se README "Språk (NO/EN)" for full arkitektur.

Viktigste designbeslutning: stilnavnene i `data/bjcp_styles.json` bruker det norske displaynavnet som eneste, stabile identitet (ingen egen id-kolonne, hverken i web eller `modules/style_engine.py`). I stedet for en risikabel schema-migrering (som ville brutt bakoverkompatibilitet med allerede lagrede oppskrifter/`.kbhrecipe`-filer) ble dette løst som et rent visningslag — `valgtStil` og malt-/smakskategori-nøklene forblir norske og uendret i logikk/lagring/eksport; kun rendering (combobox, resultatpanel, stilmatch-tekst, smakshjul-akser, print) går gjennom en NO→EN-oppslagstabell.

URL-strategi: klientside språkbytte på samme URL (ingen `/en/`), valgt fordi web ikke har noe build-steg — en egen `/en/`-filstruktur ville krevd enten manuell dobbel vedlikehold eller et nytt bygge-/pre-render-verktøy, begge utenfor omfanget denne runden. Kjent konsekvens: ingen egen, crawlbar engelsk URL for søkemotorer i V1 — en fremtidig, avgrenset pre-render-runde er anbefalt løsning, ikke påbegynt.

`hjelp/`-sidenes navigasjon/chrome er oversatt; selve brødteksten (~900 linjer glossar/guider) er bevisst IKKE oversatt denne runden — et synlig varsel i UI-et sier fra om dette når `<html lang="en">`. Flagget som egen Runde 14B i `docs/ROADMAP.md`.

Språkvelgeren (NO/EN-knappene i header/kompaktnav/uttrekksmeny) bruker lokale flaggbilder (`assets/ui/flag-no.webp`, `assets/ui/flag-gb.webp`) fremfor emoji — unicode-flaggemoji rendres upålitelig på tvers av OS/nettleser (bl.a. feil britisk flagg på enkelte plattformer). Bildene er godkjente, uendrede kopier av brukerens egne kildefiler, vist 20px bredt med bevart aspect ratio (`object-fit: contain`), rent dekorative (`alt=""`, `aria-hidden="true"`) siden NO/EN-teksten allerede dekker tilgjengelighet.

## Runde 13A — «Ny oppskrift» og trygg erstatning av aktiv kladd (2026-08-14)

Manuell testing av Runde 13 viste at å åpne en `.kbhrecipe`-fil stille erstattet aktiv kladd uten varsel eller mulighet til å starte blankt. La til en «Ny oppskrift»-knapp (samme bootstrap-standardtilstand som ved førstegangsbesøk) og en delt `oppskriftHarInnhold()`-sjekk (`js/kbhrecipe.js`) som «Ny oppskrift», byggerens «Åpne oppskriftsfil» og Importer-sidens håndoverlevering alle bruker: bekreftelse spørres kun når aktiv kladd har reelt innhold, og aldri før en fil er validert. Brygger/Bryggeri ble bevisst holdt utenfor «har innhold»-sjekken — de er en lett brukerpreferanse (`kvernhaug_web_identitet`) i tillegg til å være del av selve oppskriften, og forhåndsutfylles på nytt rett etter nullstilling.

## Runde 13 — Portabel `.kbhrecipe`-fil (2026-08-14)

Introduserte den versjonerte `.kbhrecipe`-filwrapperen (`js/kbhrecipe.js`) som primær lagrings-/delingsflyt, med rå JSON-eksport nedgradert til et "Avansert"-felt. Før denne runden var rå, uwrappet JSON-eksport eneste fil-alternativ (fortsatt lest/støttet automatisk som legacy-format av `parseKbhRecipeInnhold()` — ingen manuell konvertering kreves for gamle filer).

## Runde 12C/12D — Malt kg/%-kontrakt revidert (2026-08-13)

Malt %-redigering gikk gjennom flere iterasjoner før den landet på dagens multi-rad-lås-kontrakt (se README "Hva den kan"): først en enkel live-kobling (12B), deretter en enkelt-rad-låsing med eksplisitt knapp (12C), til slutt dagens modell der FLERE manuelt redigerte rader kan være låst samtidig og resten fordeles kun mellom urørte rader (12D). Hver iterasjon var en bevisst UX-korreksjon basert på manuell testing, ikke en bugfiks på forrige runde.

## Runde 12 — Oppskriftsskalering + KBH Icon v1 (2026-08-12/13)

- **Skaler oppskrift**: portert fra `ui/recipe_card.py`s "📐 Skaler oppskrift" til Bryggmester. Til forskjell fra desktop (som i tillegg auto-endrer oppskriftsnavnet ved skalering) ble navne-auto-endringen bevisst IKKE portert til web.
- **KBH Icon v1**: nytt kompakt nav-/drawer-ikon (kråke + fullt pilsglass + gammel møllestein, transparent bakgrunn), et brukerlevert og godkjent motiv — IKKE en automatisk beskjæring av Master V1-kunsten slik forgjengeren (`kvernhaug_logo_kompakt.png`, fjernet denne runden) var. Master: `assets/branding/kbh_icon_v1.png` (1024×1536, urørt original), web-derivat 260×390. `.kompaktnav-logo`/`.sidemeny-logo` byttet fra `object-fit: cover` til `contain` fordi det nye motivet er en uklippet komposisjon som `cover` ville kappet i den runde 34-42px-badgen.

## Runde 11B — Nytt KBH Emblem (2026-08-12)

Høyrekortets fulle emblem byttet fra `master_v1_transparent.png` (liggende, 1125:900) til et brukerlevert, transparensrensket emblem: `assets/branding/kbh_emblem_master.png` (1024×1536, felles master for web OG desktop), web-derivat 780×1170. `.identitet-logo` gikk fra bredde- til høydestyrt CSS-sizing (`height: clamp(140px, 27vw, 310px)`) for å bevare samme visuelle fotavtrykk med det nye, stående sideforholdet. Ingen ny illustrasjon — kun rensket alfakanal. Identitetsblokken (fra Runde 10E/11B) fikk samtidig sin nåværende form: valgt Ølstil (ikke stilmatch-resultatet) + emblemet, etterfulgt av alltid synlig Smaksprofil og sammenleggbar Stilanalyse — erstattet den tidligere Smak/Stil-fanenavigasjonen.

## Polish-runde (2026-08-10)

- **To-lags palett revidert** etter visuell kontroll: bekreftet at desktop-appen kjører i Streamlits standard mørke tema (ingen `.streamlit/config.toml`) — kald skifer, ikke det varme brune fra oppskriftskortet. `--bg`/`--bg-sect`/`--bg-sect-2`/`--body`/`--muted` satt kalde som standard; `--warm-*` (fra `modules/card_template.py`/`ui/branding.py`) forbeholdt `.masthead` og `.bygger-hoyre`.
- **Typografi/tekstfarger**: `--muted`/`--warm-muted` lysnet for bedre kontrast. Feltlabels byttet fra `--muted` til `--body`. Seksjonsoverskrifter og gull-"eyebrow"-etiketter økt i størrelse/vekt.
- **Hjelp-TOC utvidet**: `.hjelp-layout` maks-bredde 1100px → 1400px, innholdskolonne 780px → 920px, TOC 200px → 230px — den gamle bredden ga en "halvparten av siden brukt"-følelse på brede skjermer. `hjelp/bryggedag.html` sine stegkort mistet samtidig en gul venstrestrek (det tallmerkede rundmerket ble vurdert visuelt anker nok alene).
- **Sticky høyrekort-fix**: `.bygger-hoyre` sin sticky `top`-offset var en fast `1rem`, mindre enn mastheadens faktiske høyde, så kortet kunne kollidere med headeren ved scroll. `chrome.js` måler nå mastheadens løpende høyde og skriver den til `--masthead-h`, som `.bygger-hoyre` sin `top: calc(var(--masthead-h) + 1rem)` leser.

## Runde 7–11B — IA-redesign (2026-08-12, visuelt godkjent)

Fullbredde IA-redesign: Mine oppskrifter-/Importer-/Utskrift-sider, ny bredere app-lignende Oppskriftsbygger-layout, og — arkitekturmessig viktigst — beregningsorkestreringen (effektivt datasett, OG/FG/ABV/IBU/EBC, smaksprofil, stilmatch) skilt ut fra `app.js` til `recipe_engine.js`. Før dette lå orkestreringen tett koblet til DOM-en inne i `app.js`; siden Utskrift-siden må kunne beregne en VILKÅRLIG valgt oppskrift uten byggerens skjema til stede, ble den skilt ut som rene, DOM-frie funksjoner delt av `app.js` og `utskrift_page.js`. Bryggelærling/Bryggmester ble samtidig gjort til **reelle** modi (førstegangsvalg + drawer-bryter) i stedet for en ren CSS-visningsbryter, med Bryggmesters første malt kg↔%-arbeidsflyt (portert fra `ui/malt_panel.py`) og mål-IBU→gram via portert inverse Tinseth. Se `docs/snapshots/2026-08-12_Web_Desktop_Runde_11B_Checkpoint.md` for full detalj.

## Runde 6 (HEAD `14668af`)

Egen Hjelp & bryggehåndbok (`hjelp/`), brukeridentitet (ølnavn/brygger/valgfritt bryggeri/notater) på selve oppskriften, og fire egne nøytrale A4-utskriftsdokumenter i stedet for et rått sideprint.

## Runde 1–5 — kjernefunksjonalitet

OG/FG/ABV/IBU/EBC, smakshjul, søkbare dropdown-felt, stilmatching mot Kvernhaug Brygghus sitt eget stilbibliotek, lokal lagring, JSON-eksport/import, to visningsmoduser, vennlig stilveiledning, egendefinerte ingredienser, deterministisk generert ingrediensdata.
