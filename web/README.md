# Kvernhaug Brygghus — Web (forenklet, offentlig versjon)

Frittstående, statisk web-versjon av oppskriftsbyggeren. Ingen build-steg, ingen npm-avhengigheter, ingen backend.

Web er en responsiv, noe forenklet videreføring av desktop-appen — ikke en visuell redesign. Farger, typografiprinsipp, paneler og resultatpresentasjon er hentet direkte fra `docs/branding/master_design_v1.md`, `ui/branding.py`, `modules/card_template.py` og — for selve app-kromet (bakgrunn/paneler/tekstfarger) — desktop-appens faktiske kjøretidsutseende: Streamlit har ingen `.streamlit/config.toml` i dette repoet og kjører dermed i sitt eget standard mørke tema (kald skifer), IKKE det varme brune fra oppskriftskortet. Se "Design og navigasjon" under for hvordan web speiler dette som to bevisst atskilte soner.

## Sider

Fem sider, hver med ett tydelig formål, delt av samme uttrekkbare venstremeny (åpnes fra hamburgerknappen i mastheaden på alle sider):

| Side | Formål |
|---|---|
| `index.html` — **Oppskriftsbygger** | Bygge oppskriften. Venstre kolonne = det du endrer, høyre kolonne (varm "recipe card"-sone) = det Kvernhaug forteller deg om resultatet. |
| `mine-oppskrifter.html` — **Mine oppskrifter** | Åpne eller slette lagrede oppskrifter. |
| `importer.html` — **Importer oppskrift** | Åpne en JSON-fil, ELLER lime inn ren tekst (samme kontrakt som `ui/sidebar.py`/`modules/recipe_importer.py`) med forhåndsvisning før den legges inn i byggeren. |
| `utskrift.html` — **Utskrift** | Skrive ut den aktive oppskriften — lagret eller ikke — eller en tidligere lagret oppskrift. |
| `hjelp/index.html` — **Hjelp** | How-to/FAQ/bryggehåndbok, se eget avsnitt under. |

## Hva den kan

- Bygge en oppskrift av malt, humle og gjær med live OG, FG, ABV, IBU og EBC
- To **reelle** visningsmoduser (fra Runde 11) — **Bryggelærling** ("veiledet modus, lær mens du brygger") og **Bryggmester** ("full kontroll, alle detaljer tilgjengelig") — samme oppskrift, samme beregningsmotor. Valg skjer i en førstegangsdialog ved første besøk, deretter via en liten status+bryter i venstremenyen (`.modus-knapp`, lagres i `localStorage`); bytte endrer aldri oppskriftsdata. Bryggelærling skjuler brygghuseffektivitet (75 % standard), malt-%-kolonnen og mål-IBU-feltet. Bryggmester låser opp desktop-appens faktiske malt kg↔%-arbeidsflyt (`ui/malt_panel.py`-kontrakten: kg er alltid kilden og oppdaterer % live; % → kg krever et eksplisitt "Bruk prosentfordeling"-klikk) og et mål-IBU→gram-felt per humletilsetning (portert inverse-Tinseth fra `modules/calculations.py::beregn_gram_fra_ibu`, kun via eksplisitt "Beregn gram"-knapp — aldri live, for å unngå en gram/IBU-feedback-loop).
- Ølstilvalg ligger i arbeidsflyten på venstre side, rett etter Grunndata og før Malt — starter blankt, valgfritt. Selve stilmatch-*resultatet* vises som ren informasjon i stilpanelet til høyre; du kan aldri redigere eller velge stil i det panelet.
- Små "?"-hjelpeknapper på sentrale begreper (OG/FG/ABV/IBU/EBC/effektivitet/utgjæring/alfasyre/stilmatch/smakshjul) — åpnes med klikk/tap (ikke hover), lukkes med ✕/Escape/klikk utenfor. Der et større hjelpeemne finnes får popoveren en "Les mer →"-lenke som åpner riktig seksjon i **Hjelp & bryggehåndbok** (`hjelp/`) i ny fane, uten å forstyrre oppskriften i byggeren.
- **Hjelp & bryggehåndbok** (`hjelp/index.html`) — how-to/FAQ/oppslagsverk (kom i gang, forstå oppskriften, ingredienser, FAQ), pluss egne sider for en generell **bryggedagsguide** (`hjelp/bryggedag.html`, 15 steg med hva/hvorfor/følg med på/vanlige feil), **bryggemetoder** (`hjelp/bryggemetoder.html`: BIAB/all-grain/alt-i-ett) og en **utstyrsspesifikk guide** (`hjelp/utstyr-brewzilla.html`, første av flere planlagte — kildeforankrede tall er tydelig skilt fra det som ennå ikke er verifisert)
- Søkbare dropdown-felt (skriv for å filtrere) for malt, humle, gjær og ølstil — ingen lange nedtrekkslister å bla gjennom. Søket dekker mer enn produktnavn: malt kan finnes på produsent/kategori, humle på opprinnelsesland/type, gjær på produsent — men bevisst **ikke** på frie smakstags, som ville gjort treffene for brede. Malt er i tillegg gruppert (Basemalt/Karamell/Røstet/Hvete m.fl., samme rekkefølge som `ui/malt_panel.py`) for å gjøre listen mer forståelig — søket går fortsatt på tvers av alle grupper.
- Egendefinerte ingredienser — malt/humle/gjær som ikke finnes i biblioteket kan legges inn manuelt (navn + tekniske grunnverdier), fungerer fullt ut i beregningene og lagres/eksporteres med oppskriften. Humle-alfa kan i tillegg overstyres per rad for bibliotekshumle også (varierer fra pose til pose).
- Smakshjul — 18-akset radardiagram (egen SVG-komponent, ingen ekstern lib) som oppdaterer seg live når malt/humle/gjær endres
- Stilmatching mot **Kvernhaug Brygghus sitt eget stilbibliotek** (26 stiler): numerisk nærmeste stil, en vennlig tre-nivås stilveiledning ("innenfor" / "litt utenfor" / "tydelig utenfor" — aldri "FEIL"/"UGYLDIG"), nærliggende alternativer med "hva mangler" (Bryggmester). En tom oppskrift viser "Ingen stilmatch ennå" i stedet for en meningsløs "Kreativt Brygg"-match — datadrevet sjekk (`harNokDataForStilmatch()`), ikke en visuell hardkoding.
- Brukeridentitet — **Ølnavn**, **Brygger** og **Bryggeri**-felt i Grunndata, pluss et notatfelt (Bryggmester). Lagres på selve oppskriften (localStorage + JSON) og som en lett, egen brukerpreferanse som forhåndsutfyller nye oppskrifter — uten å overstyre en allerede lastet eller importert oppskrift.
- Høyrekortets identitetsblokk (fra Runde 10E/11B) viser den manuelt **valgte** Ølstilen (ikke stilmatch-resultatet), pluss det nye KBH-emblemet (`assets/branding/kbh_emblem_master.png`, felles master-asset med desktop). Under identitetsblokken: en alltid synlig **Smaksprofil**-seksjon, etterfulgt av en sammenleggbar (`<details>`, lukket som standard) **Stilanalyse**-seksjon — erstatter den tidligere Smak/Stil-fanenavigasjonen.
- Lagre oppskrifter lokalt i nettleseren (`localStorage`) — ingenting sendes til noen server. Oppskriften du aktivt bygger på autolagres også fortløpende som en "aktiv kladd", uavhengig av eksplisitt "Lagre" — se "Aktiv kladd" under.
- Eksportere (JSON) fra byggeren; importere fra egen **Importer oppskrift**-side (`importer.html`) — enten som JSON-fil, eller som limt inn ren tekst (fuzzy-matches mot bibliotekene, viser forhåndsvisning av hva som ble gjenkjent FØR noe legges inn i byggeren) — se "Tekstimport" under
- **Fire egne utskriftsdokumenter** fra Utskrift-siden (ikke bare et print av skjermbildet): **Oppskriftsark**, **Handleliste** (nøytral — ingen butikk/pris/lagerstatus), **Bryggedagsark** (arbeidsark med sjekkliste og felt for faktiske målinger) og **Bryggelogg** (tomt papirskjema til utfylling med penn). A4-vennlige, lys bakgrunn/mørk tekst uansett skjermtema. Brukerens ølnavn/brygger/bryggeri er hoveddokumentets identitet — Kvernhaug Brygghus vises kun diskret i en fotnote ("Laget med Kvernhaug Brygghus Oppskriftsbygger").

## Hva den bevisst ikke har

Dette er ikke en nettversjon av hele Streamlit-appen. Ingen innlogging, ingen database, ingen vannkjemi, Pantry eller Smart Handleliste — se hovedappen (`app.py`) for full funksjonalitet.

**Stilmatchen er IKKE "full BJCP-matching".** Kall den "stilmatching mot Kvernhaug Brygghus sitt stilbibliotek". `data/bjcp_styles.json` er identisk med — men ikke bredere enn — det biblioteket appen selv bruker i dag: 26 stiler (25 offisielle BJCP-understiler + Historisk Wiesn-Märzen, Tradisjonelt Norsk Gårdsøl/Kveik og Tradisjonelt Norsk Juleøl, alle tre eksplisitt merket som ikke-offisielle Kvernhaug-kategorier). Det offisielle BJCP 2021-stilheftet har rundt 100 understiler; hele stilfamilier (sure øl, saison, barleywine/sterk ale, amerikansk lager/cream ale, brown/scotch ale, øvrige hveteøl, moderne craft-stiler som session/black/brut IPA, frukt-/krydder-/trelagrede spesialøl) finnes ikke i biblioteket i det hele tatt — verken i web eller i desktop-appen.

Selve stilmatch-**logikken** er derimot en full port av `modules/style_engine.py` (numerisk avvik, styrkeklynge-demping, sensorisk `smak_krav` via en port av `modules/flavor_engine.py`, signaturbonus/-straff og de harde takene), men tar **ikke** med `modules/flavor_conflicts.py`, `modules/flavor_summary.py` (narrativ smakstekst) eller den ekstra "blomster-/parfymerisiko"-varselen i `ui/style_panel.py` — de er egne presentasjonslag utenpå Style Engine, ikke del av selve stilmatchingen, og holdt bevisst utenfor for å unngå unødvendig kompleksitet i den forenklede versjonen.

## Struktur

```
web/
  index.html          Oppskriftsbygger — venstre: flat skjema-seksjonsflyt, høyre: sticky varm "recipe card"
  mine-oppskrifter.html  Åpne/slette lagrede oppskrifter
  importer.html        Importer oppskrift — fil (JSON) ELLER limt inn tekst, med forhåndsvisning
  utskrift.html        Velg aktiv kladd ELLER en lagret oppskrift, skriv ut de fire dokumentene
  css/style.css        Styling — to-lags palett (kaldt app-krom + varm merkevaresone), masthead/drawer, print, hjelp-TOC
  js/chrome.js          Delt "app-krom": masthead-krymping ved scroll + uttrekkbar venstremeny -- på alle sider
  js/calc.js           OG/FG/ABV/IBU/EBC — portert fra modules/calculations.py
  js/flavor.js         Smaksprofil (poeng-beregning) — portert fra modules/flavor_engine.py
  js/radar.js           Smakshjul — vanilla SVG-radardiagram (ingen ekstern lib), tegner flavor.js sine poeng
  js/style.js           Stilmatching mot Kvernhaug-biblioteket — portert fra modules/style_engine.py
  js/veiledning.js       Vennlig tre-nivås stilveiledning -- web-only lag oppå style.js, samme tall
  js/combobox.js        Gjenbrukbar søkbar dropdown (malt/humle/gjær/stil), støtter valgfri gruppering (malt)
  js/help.js             Delt hjelpepopover ("?"-knapper) + "Les mer"-lenker -- web-only, ingen Python-motstykke
  js/recipe_engine.js    DOM-fri beregningsorkestrering (effektivt datasett, full beregning, tomt-stilmatch-sjekk) --
                          delt av app.js OG utskrift_page.js, se "Arkitektur: recipe_engine.js" under
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
  assets/branding/kbh_icon_v1.png       KBH Icon v1 (Runde 12, godkjent) -- kompakt nav-/drawer-ikon (kråke +
                                          pilsglass + møllestein), web-optimert (260x390) kopi av den delte
                                          masteren assets/branding/kbh_icon_v1.png (autoritativ for web OG desktop,
                                          selv om desktop ikke har noen kompakt-ikon-rolle i dag, se web/README.md)
  assets/branding/kbh_emblem.png        Nytt KBH Emblem (Runde 11B) -- fullt emblem i identitetsblokken, web-optimert
                                          kopi av felles master assets/branding/kbh_emblem_master.png (delt med desktop)
  hjelp/index.html        Hjelp & bryggehåndbok -- how-to/FAQ/oppslagsverk, mål for "Les mer"-lenkene
  hjelp/bryggedag.html    Generell bryggedagsguide, 15 steg
  hjelp/bryggemetoder.html   BIAB / all-grain / alt-i-ett -- strukturert for enkel utvidelse
  hjelp/utstyr-brewzilla.html   Første utstyrsspesifikke guide (og uformell mal for flere)
```

## Design og navigasjon

Desktop-appen er designreferansen — web skal kjennes igjen som samme produktfamilie, ikke en egen visuell stil:

- **To-lags palett** (revidert etter visuell kontroll 2026-08-10): desktop-appen har INGEN `.streamlit/config.toml` og kjører dermed i Streamlits eget standard mørke tema for alt vanlig UI — kald skifer (`#0e1117`-aktig), ikke det varme brune fra oppskriftskortet. `--bg`/`--bg-sect`/`--bg-sect-2`/`--body`/`--muted` i `style.css` er derfor **kalde som standard** og brukes av venstre arbeidsområde, Hjelp-sidene og menyen. `--warm-*`-variantene (de gamle verdiene fra `modules/card_template.py`/`ui/branding.py`) er forbeholdt to konkrete, lokalt skopede soner: `.masthead` og `.bygger-hoyre` (høyrekortet) — sistnevnte overskriver `--bg-sect`/`--body`/`--muted` LOKALT som CSS-variabler, slik at alle vanlige regler (`.resultat-boks`, `.stil-kort` osv.) automatisk arver riktig varme uten duplisering. `--gold` er aksentfarge i begge soner (lenker, fokusrammer, primærknapper) — ikke lenger en bakgrunnsvask over alt.
- **Typografi**: desktop bruker serif KUN for merkevareelementer (`ui/branding.py`: header) og oppskriftskortet/A4-utskriften (`modules/card_template.py`). Alle vanlige Streamlit-widgets har ingen egen font-family satt, altså nettleserens/Streamlits standard sans-serif. Web speiler dette nøyaktig: `--sans` er standard for alt vanlig skjema-UI (nav, felt, knapper), `--serif` er forbeholdt masthead, identitets-/resultatkortet og stilpanelet til høyre (eksplisitt tillatt et "klassisk Kvernhaug-preg" der) samt utskriftsdokumentene.
- **Venstre kolonne = flat seksjonsflyt, ikke boks-i-boks**: `.panel` (Grunndata/Stilvalg/Malt/Humle/Gjær/Lagre) er bevisst uten egen bakgrunn/kant/skygge — kun en tynn nøytral toppstrek + gul seksjonsetikett skiller seksjonene, likt et skjemaark fremfor stablede kort. Høyrekortet bruker IKKE `.panel` i det hele tatt; det er sin egen, varme "recipe card"-boks.
- **To atskilte logo-roller, nå med separate, godkjente assets** (Runde 12, 2026-08-12): et lite **kompakt nav-/drawer-ikon** (`web/assets/branding/kbh_icon_v1.png`, i mastheaden/kompakt sticky-nav og venstremenyen) og et **fullt emblem** (høyrekortets identitetsblokk, se under). KBH Icon v1 er et brukerlevert, godkjent motiv — kråke + fullt pilsglass + gammel møllestein, transparent bakgrunn — og er IKKE en automatisk beskjæring av Master V1-kunsten slik forgjengeren (`kvernhaug_logo_kompakt.png`, nå fjernet) var. Master: `assets/branding/kbh_icon_v1.png` (1024×1536, urørt original); web-derivat: `web/assets/branding/kbh_icon_v1.png` (260×390, ren nedskalering). `.kompaktnav-logo`/`.sidemeny-logo` bruker `object-fit: contain` (ikke `cover`) fordi det nye motivet er en uklippet, stroende komposisjon — `cover` ville kappet vekk deler av glasset/møllesteinen i den runde 34-42px-badgen. Dette er fortsatt IKKE den formelt komponerte rundmedaljongen med buet `KVERNHAUG BRYGGHUS`-tekst som `docs/branding/master_design_v1.md` beskriver, og er heller ikke laget som favicon/mikrovariant ennå (se backlog i `docs/ROADMAP.md`).
- **Nytt KBH Emblem** (Runde 11B, 2026-08-12): høyrekortets fulle emblem byttet fra `master_v1_transparent.png` (liggende, 1125:900) til et brukerlevert, transparensrensket emblem — `assets/branding/kbh_emblem_master.png` (1024×1536, felles master for web OG desktop) og `web/assets/branding/kbh_emblem.png` (780×1170, web-optimert kopi). `.identitet-logo` gikk fra bredde- til høydestyrt CSS-sizing (`height: clamp(140px, 27vw, 310px); width: auto;`) for å bevare samme visuelle fotavtrykk med det nye, stående sideforholdet. Ingen ny illustrasjon — kun rensket alfakanal fra den leverte filen. De to gamle emblemfilene (`assets/branding/master_v1_transparent.png` og `web/assets/branding/master_v1_transparent.png`) er ikke lenger referert noe sted i koden — se sluttrapporten for dette checkpointet for vurdering av om de bør ryddes.
- **Bred masthead + krympende sticky header**: `.masthead` speiler `ui/branding.py` sin `render_header()`-komposisjon (logo + tekstblokk) i full sidebredde, ikke det gamle smale, sentrerte headerkortet. `web/js/chrome.js` legger til `.is-kompakt` når `scrollY > 40` — CSS krymper logo/skrift og skjuler motto/undertekst, slik at mastheaden tar lite plass mens man jobber, uten å slutte å være sticky.
- **Uttrekkbar venstremeny** (`.sidemeny`, åpnes fra hamburgerknappen i mastheaden på alle sider): speiler desktop-appens `st.sidebar` (`ui/sidebar.py`) som hovednavigasjon — Oppskriftsbygger / Mine oppskrifter / Importer oppskrift / Utskrift / Hjelp. Overlay-drawer på både desktop og mobil (samme komponent, ingen egen "collapsed rail"-variant denne runden — vurder det som en senere finpuss om ønskelig). Erstatter den forrige runde sin horisontale `.hovednav`-lenkerad.
- **Layout**: `index.html` bruker `app.py` sin faktiske `st.columns([2.0, 1.2])`-fordeling (≈ 62,5 % / 37,5 %) som mal for `.byggerlayout`s to kolonner på desktop-bredde. Bruddpunktet (1000px) er satt ut fra faktisk plassbehov (se kommentar i `style.css`), ikke en vilkårlig antakelse — under det er alt én kolonne, ingen sticky.
- **Hjelp-sidene** (`hjelp/*.html`) har fått en lokal innholdsmeny (`.hjelp-toc`) ved siden av hovedinnholdet på desktop (≥900px, sticky venstrekolonne) i stedet for én lang kortstabel — kollapser til en horisontal chip-rad på mobil. `hjelp/bryggedag.html` sine 15 stegkort har ikke lenger en gul venstrestrek (fjernet etter tilbakemelding — det tallmerkede rundmerket er visuelt anker nok). Utvidet igjen i polish-runden (2026-08-10): `.hjelp-layout` maks-bredde 1100px → 1400px, innholdskolonnen 780px → 920px, TOC 200px → 230px — den gamle bredden ga en "50 % av siden brukt"-følelse på brede skjermer.
- **Typografi/tekstfarger** (polish-runde 2026-08-10): `--muted` og `--warm-muted` er lysnet betydelig (bedre kontrast på both kald og varm sone). Feltlabels (`.felt-rad label`) byttet fra `--muted` til `--body` (nær-hvit) og noe større. Seksjonsoverskriftene (`.panel h2`/`.bygger-hoyre h2`) og de små gull-"eyebrow"-etikettene (`.resultat-label`, `.stil-headline-label`, `.stil-seksjon-tittel`, `.import-resultat-tittel`) er alle økt i størrelse og vekt. Prinsippet er uendret: gull er aksent (overskriftsdetaljer/borders/fokus/lenker/aktive elementer), ikke hovedfarge for løpende lesetekst.
- **Sticky høyrekort vs. masthead** (polish-runde 2026-08-10): `.bygger-hoyre` sin sticky `top`-offset var tidligere en fast `1rem` — mindre enn mastheadens faktiske høyde, så kortet kunne visuelt havne under/kollidere med headeren ved scroll. `web/js/chrome.js` måler nå mastheadens løpende høyde (ekspandert og kompakt, samt etter hver krympe-transition) og skriver den til CSS-variabelen `--masthead-h`, som `.bygger-hoyre` sin `top: calc(var(--masthead-h) + 1rem)` leser — offsetten følger dermed headeren nøyaktig i begge tilstander.

## Aktiv kladd (arkitektur)

Oppskriften som står i byggeren akkurat nå autolagres fortløpende til en egen localStorage-nøkkel (`kvernhaug_web_aktiv_kladd`) — ved hver beregning, ikke bare når du trykker "Lagre oppskrift". Dette gjør tre ting mulig uten backend:

1. Laster du `index.html` på nytt (eller lukker og åpner fanen igjen), gjenopprettes akkurat det du holdt på med.
2. **Utskrift**-siden kan bruke den aktive, *også ulagrede*, oppskriften direkte — du trenger ikke lagre først for å skrive ut. Utskrift-siden leser kun denne nøkkelen; den skriver aldri til den, så å forhåndsvise en lagret oppskrift der overskriver aldri det du faktisk holder på med i byggeren.
3. **Mine oppskrifter**-siden sin "Åpne i byggeren" og JSON-import bruker samme nøkkel som håndoverleveringsmekanisme: skriv oppskriften dit, naviger til `index.html`, som gjenoppretter den derfra ved oppstart.

## Tekstimport

`importer.html` sin tekstfane porter kontrakten fra `ui/sidebar.py` sin "📥 Importer oppskrift fra tekst"-expander (`modules/recipe_importer.py`) til `js/recipe_importer.js`: samme linjeformater (`5 kg Maris Otter`, `300 g CaraMunich`, `20 g Magnum 60 min`, `90% Maris Otter` + `Total malt: 6 kg`, en gjærlinje uten mengde), samme flyt (lim inn → "🔍 Analyser" → forhåndsvisning av matchet/ikke-gjenkjent → "✅ Legg inn i oppskriftsbygger"), og samme terskel (0.6) for fuzzy-treff. Selve regex-parsingen (`parseRecipeText()`) er en direkte 1:1-port av `parse_recipe_text()`. Fuzzy-matchingen (`matchImportedIngredients()`/`_finnBesteTreff()`) bruker en egen JS-implementasjon av samme Ratcliff/Obershelp lengste-felles-blokk-algoritme som Pythons `difflib.SequenceMatcher.ratio()` — samme prinsipp og terskel, men ikke bit-for-bit identisk output i alle kanttilfeller siden det er to uavhengige implementasjoner (ingen delt kjøretid mellom Python og JS, se "Vedlikehold" under). Ubekreftede/uklare treff vises tydelig atskilt fra matchede — aldri stille gjettet inn i oppskriften.

## Arkitektur: recipe_engine.js

Før denne runden lå hele beregningsorkestreringen (effektivt datasett, OG/FG/ABV/IBU/EBC, smaksprofil, stilmatch) inne i `app.js`, tett koblet til DOM-en. Siden Utskrift-siden må kunne beregne en VILKÅRLIG valgt oppskrift (aktiv kladd eller en lagret oppskrift) uten byggerens skjema til stede, er denne orkestreringen skilt ut i `recipe_engine.js` — rene funksjoner som tar en oppskrift + ingrediens-/stildata inn og returnerer et ferdig resultat, uten å røre `document` (bortsett fra `escHtml()`, som trenger et DOM-element for escaping). `app.js` og `utskrift_page.js` bruker begge denne filen; selve beregningsformlene i `calc.js`/`flavor.js`/`style.js` er **ikke** endret av denne refaktoreringen.

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

`js/combobox.js`, `js/radar.js`, `js/help.js`, `js/veiledning.js`, `js/recipe_engine.js`, `js/print.js`, `js/chrome.js`, `js/app.js`, `js/mine_oppskrifter_page.js`, `js/importer_page.js` og `js/utskrift_page.js` er egne web-komponenter uten Python-motstykke — ingenting å synkronisere. `js/recipe_importer.js` er et delvis unntak: parsingen er en eksakt port av `modules/recipe_importer.py`, men fuzzy-matchingen er en uavhengig JS-implementasjon av samme algoritme (se "Tekstimport" over) — hold linjeformat-regexene i sync manuelt hvis `parse_recipe_text()` endres. `veiledning.js` bruker riktignok tall som `style.js` allerede regner ut (`felt_avvik`, lagt til per stil i `analyserStilOgBalanse` som et web-only tillegg utover det Python-originalen returnerer) — selve scoren/rangeringen er uendret av dette.

Ved endring i `modules/calculations.py`, `modules/style_engine.py` eller `modules/flavor_engine.py`: oppdater tilsvarende JS-fil i samme omgang, og kjør `scripts/generate_web_data.py` på nytt hvis stilgrensene eller ingrediensdataene endret seg.

## Egendefinerte ingredienser

Løses uten å røre `calc.js`/`flavor.js`/`style.js` i det hele tatt: for hver beregning bygger `recipe_engine.js` sin `byggEffektiveDatasett()` et midlertidig oppslagsobjekt (`{...biblioteket, [egen_id]: egendefinertData}`) som sendes inn akkurat som det vanlige biblioteket. Egendefinerte ingredienser og alfa-overstyring på biblioteks-humle skriver **aldri** til `maltData`/`humleData`/`gjaerData` selv, og påvirker aldri andre rader eller andre oppskrifter. De lagres kun som en del av den enkelte oppskriften (localStorage og JSON-eksport), ikke i noe eget, delt bibliotek.

## Brukeridentitet

Oppskriften er brukerens, ikke Kvernhaug Brygghus sin. `Ølnavn`, `Brygger` og valgfritt `Bryggeri` ligger i Grunndata-panelet og lagres som del av selve oppskriften (`samleOppskrift()`/`_gjenopprettOppskrift()` i `app.js`) — de følger dermed localStorage og JSON-eksport/import akkurat som resten av oppskriften. I tillegg lagres `brygger`/`bryggeri` i en egen, lett localStorage-nøkkel (`kvernhaug_web_identitet`) som kun brukes til å forhåndsutfylle feltene på en **ny** oppskrift — den overstyrer aldri en allerede lastet eller importert oppskrift, og påvirker aldri det delte ingrediensbiblioteket.

## Print-arkitektur

De fire utskriftene lever på en egen side (`utskrift.html`), ikke inne i byggeren — printer du derfra, skriver du ALDRI ut byggerskjermen. `utskrift_page.js` velger en oppskrift (aktiv kladd eller en lagret oppskrift), kjører den gjennom `recipe_engine.js` sin `beregnOppskrift()`, og gir det ferdige resultatet videre til `print.js` sine rene `bygg*Html(ctx)`-funksjoner — de leser ALDRI live DOM-globaler selv, kun kontekst-objektet de får inn (`byggDokumentKontekst()`). Hver mal injiseres i sin egen skjulte `.utskrift-dokument`-container. `body[data-utskrift="..."]` (satt rett før `window.print()`) styrer via `@media print` i `style.css` hvilket ark som faktisk vises på papiret — resten av siden skjules automatisk, og attributten fjernes igjen ved `afterprint`.

Handlelisten er bevisst nøytral: kun navn/mengde/alfasyre — aldri butikk, pris, URL, lagerstatus eller pantry. Bryggeloggen er et rent papirskjema uten digital lagring denne runden (fylles ut med penn). Alle fire er A4-vennlige med lys bakgrunn/mørk tekst uansett skjermtema. Brukerens ølnavn/brygger/bryggeri er hoveddokumentets identitet; Kvernhaug Brygghus vises kun diskret i en fotnote.

## Hjelp & bryggehåndbok

`hjelp/` er egne, statiske sider (samme `style.css` for visuell identitet, ingen delt kjøretid med byggeren) som åpnes i ny fane fra "📖 Hjelp"-lenken i header og fra "? → Les mer"-lenker i hjelpepopoverne. `hjelp/index.html` samler kom-i-gang, begrepsforklaringer (med stabile anker-IDer som `#og`/`#ibu`/`#stilmatching` osv. — disse er "Les mer"-lenkenes mål og må ikke endres uten å oppdatere `HJELP_TEKSTER.lesMer` i `help.js` samtidig), ingrediensstoff og FAQ. `hjelp/bryggedag.html`, `hjelp/bryggemetoder.html` og `hjelp/utstyr-brewzilla.html` er egne sider for henholdsvis den fulle bryggedagsguiden, metodesammenligning og utstyrsspesifikke guider.

`hjelp/utstyr-brewzilla.html` skiller eksplisitt mellom fire slags tall/påstander, ingen behandlet som mer autoritative enn de faktisk er: (A) faktisk produktspesifikasjon (kjelekapasitet 35 L — ligger i produktnavnet), (B) Kvernhaugs egne standardverdier for beregning/utstyrsprofil (fordampning, dead space — hentet fra `modules/equipment.py`, men uttrykkelig merket som appens egne forutsetninger, ikke bekreftet produsentspesifikasjon), (C) generelle bryggeforutsetninger som ikke er BrewZilla-spesifikke i det hele tatt (meskeforhold, kornabsorpsjon), og (D) Kvernhaugs egen praktiske anbefaling (maks pre-boil ~30 L, en sikkerhetsmargin — ikke et produsenttall). Det som faktisk ikke er verifisert i det hele tatt, står i en egen, tydelig merket seksjon (`.hjelp-uverifisert`) — ingen oppdiktet teknisk informasjon. Filen har en HTML-kommentar øverst med dette proveniens-prinsippet, som fungerer som uformell mal for fremtidige utstyrsguider (f.eks. Grainfather).
