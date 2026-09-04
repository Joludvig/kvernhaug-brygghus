# Kvernhaug Design System — v1.0

*Grunnlagsdokument for issue #59 (CORE PRI 7). Etablerer ett eksplisitt,
versjonert sett med delte designprinsipper og maskinlesbare tokens som
konsumeres av App (Streamlit) og Web — uten å tvinge frem identiske
grensesnitt eller skrive om noen av produktene. Dette er additiv
infrastruktur, ikke en redesign — se "Hva denne versjonen bevisst ikke
gjør" nederst.*

**Token-kilde:** [`design/tokens.json`](../design/tokens.json), lastet og
validert i Python av [`modules/design_tokens.py`](../modules/design_tokens.py)
(ingen Streamlit-import — trygg å kalle fra hvilken som helst kontekst, jf.
[`.claude/rules/desktop.md`](../.claude/rules/desktop.md)).
Testdekning: [`tests/test_design_tokens.py`](../tests/test_design_tokens.py).

**Forhold til eksisterende dokumenter:** [`docs/branding/master_design_v1.md`](branding/master_design_v1.md)
forblir den låste sannhetskilden for selve **illustrasjonen/logoen** —
kråken, vannkvernen, den ovale rammen, symbolikken, hva som er forbudt
(ravn, runer, viking-motiv, sans-serif i merkevarekontekst, lys bakgrunn
for primærlogoen). Dette dokumentet gjentar eller overstyrer ingenting av
det — det dekker **systemet** rundt: fargeroller, typografiroller,
avstand, kontroller, tilstander, tilgjengelighet, responsivitet, tone, og
hvordan de samme tokens tilpasses per produkt.
[`web/README.md`](../web/README.md) sitt avsnitt "Design og navigasjon" og
toppkommentaren i [`web/css/style.css`](../web/css/style.css) dokumenterte
allerede det meste av dette uformelt, kontrollert direkte mot
desktop-appens faktiske kjøretidsutseende 2026-08-10. Dette dokumentet
formaliserer akkurat den samme inventaren som én eksplisitt, versjonert
referanse pluss selve token-filen — det introduserer ingen nye verdier.

---

## 1. Fargeroller

Seks **aksentfarger** utgjør `design/tokens.json` sin `color.accent` — den
ene sannhetskilden for dem. Hver av de tre håndvedlikeholdte konsumentene
brukte allerede sitt eget delsett av disse seks verdiene, byte-identisk der
de faktisk overlapper, før dette dokumentet fantes; ingen av dem definerte
alle seks:

| Rolle | Token-nøkkel | Hex | Brukes til | Brukes i |
|---|---|---|---|---|
| Gull | `accent.gold` | `#c49a2a` | Primær merkevareaksent — rammer, lenker, aktive tilstander, fokusring | `ui/branding.py`, `modules/card_template.py`, `web/css/style.css` |
| Pergament | `accent.pergament` | `#dfd0a0` | Primær overskrifts-/emfasetekst på mørk/varm bakgrunn | `ui/branding.py`, `modules/card_template.py`, `web/css/style.css` |
| Mosegrønn | `accent.moss` | `#3d6b2a` | Sekundær merkevareaksent — stil-/undertekst, positiv-aktig tone | `ui/branding.py`, `modules/card_template.py`, `web/css/style.css` |
| Kobber | `accent.copper` | `#9e6030` | Varm aksent — besøkte lenker, rustikk detalj | `ui/branding.py`, `modules/card_template.py`, `web/css/style.css` |
| Elfenbein | `accent.elfenbein` | `#c8b882` | Dempet merkevaretekst — bildetekster, motto, footer | `modules/card_template.py`, `web/css/style.css` (ikke `ui/branding.py`) |
| Danger | `accent.danger` | `#c0605a` | Kun feil-/destruktiv tilstand — aldri dekorativ | `web/css/style.css` (ikke `ui/branding.py` eller `card_template.py`) |

Dette er **ikke** nye ønskeverdier: det er de samme verdiene som allerede
sto håndskrevet i `ui/branding.py` (fire av de seks: gull, pergament,
mosegrønn, kobber), `modules/card_template.py` (fem: de fire over pluss
elfenbein) og `web/css/style.css` sin `:root`-blokk (alle seks) før dette
dokumentet fantes. Å formalisere dem som tokens gjør en tilfeldighet til
en kontrakt — `tests/test_design_tokens.py` feiler dersom noen av disse
tre konsumentenes eksisterende delsett driver bort fra
`design/tokens.json`, eller fra CSS, for de fargene den faktisk definerer.

### Overflatefarger (bakgrunn/tekst/dempet) er bevisst per kontekst

I motsetning til aksentfargene er bakgrunns-/tekst-/dempet-fargene **ikke**
slått sammen til én verdi — de to produktene (og to soner innad i hvert
produkt) har reelt forskjellige, allerede utrullede overflatefarger, og å
tvinge dem identiske ville vært en reell visuell endring (utenfor dette
dokumentets omfang, se §10). `design/tokens.json` sin `color` beholder
derfor fire separate overflategrupper, hver dokumentert, ikke slått sammen:

| Gruppe | Hvor den brukes | bg | bg_sect | body | muted |
|---|---|---|---|---|---|
| `web_cold_chrome` | Web sitt standard-UI (nav, skjema, vanlige paneler) — bevisst kaldt skifer, speiler Streamlits egen standard mørke tema | `#0d0f15` | `#171a22` | `#f0f1f4` | `#adb5c4` |
| `web_warm_brand_zone` | Web sin masthead + høyre identitets-/resultatkort + utskriftsdokumenter | `#100b06` | `#1a1208` | `#f2ede0` | `#b7ad9c` |
| `app_warm_card` | Desktop sitt oppskriftskort (`modules/card_template.py`) | `#0f0c07` | `#1a1208` | `#e8e0d0` | `#9a9080` |
| `illustration_reference` | Master V1-illustrasjonens egen nær-sorte, kun brukt av `ui/branding.py` sin header-banner-overlay | `#0a0a0a` | — | — | — |

Alle fire er varme, nær-sorte mørke i samme familie — ingen av dem er
"feil" — men de er ikke byte-identiske i dag, og dette dokumentet noterer
det ærlig i stedet for stille å velge en vinner. En fremtidig runde
*kan* velge å konvergere dem (ført opp som utsatt arbeid, §10), men det er
en visuell-migrasjonsbeslutning eieren må ta eksplisitt — ikke noe dette
token-grunnlaget gjør på egen hånd.

### Linje-/rammefarger

`rgba(255, 255, 255, 0.12)` (standard hårfin linje) og
`rgba(255, 255, 255, 0.22)` (sterkere, hover-/fokus-tilstøtende) — kun
web i dag (`--line`/`--line-strong` i `style.css`). Desktop bruker i dag
Streamlits egne standard widget-rammer og har ingen tilsvarende definert,
så disse er ikke løftet inn i `tokens.json` ennå.

---

## 2. Typografiroller

To typografi-rolle-tokens, `typography.serif` og `typography.sans`, i
`design/tokens.json` — begge allerede delt byte-for-byte mellom
`web/css/style.css` og `modules/card_template.py`:

- **`sans`** (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
  'Source Sans Pro', Helvetica, Arial, sans-serif`) — standard for **alt**
  vanlig UI: skjema, nav, knapper, brødtekst. Desktop setter aldri egen
  `font-family` på vanlige Streamlit-widgets i det hele tatt — den lar
  bare være å overstyre Streamlits egen sans-serif-standard, som er
  hvorfor denne rollen er "fraværet av en overstyring" på App-siden og en
  eksplisitt regel på Web-siden.
- **`serif`** (`'Palatino Linotype', Palatino, 'Book Antiqua', Georgia,
  serif`) — forbeholdt **utelukkende** merkevare-/identitetsoverflater:
  masthead/header-banner, identitets-/resultatkortet (begge produkter),
  stilpanelet, og utskriftsdokumenter. Aldri brukt for vanlig skjema-UI i
  noen av produktene — dette speiler `master_design_v1.md` sin "aldri
  sans-serif for Kvernhaug-branding"-regel, anvendt motsatt vei (aldri
  serif for *ikke*-merkevare-UI), slik at de to produktene leses som én
  familie uten at noen av dem føles utkledd.

Ingen ny type-skala (størrelser/vekter/linjehøyder) er definert i v1.0 —
begge produkter størrer i dag tekst ad hoc per element (`clamp()` på Web,
`em`/eksplisitt `px`/`rem` spredt gjennom `card_template.py`). Å etablere
en delt numerisk type-skala er utsatt (§10) — denne versjonen låser kun de
to *font-family*-rollene, som allerede var delt i praksis.

---

## 3. Avstandsskala

`design/tokens.json` sin `spacing_rem` definerer den **kanoniske skalaen
for nytt arbeid fremover**: `0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0`
(rem).

Ingen av produktenes eksisterende håndskrevne CSS/inline-stiler er bygget
mot en skala — `web/css/style.css` alene bruker dusinvis av ad hoc-verdier
(`0.3rem`, `0.55rem`, `0.65rem`, `0.9rem`, …) akkumulert runde for runde.
Dette dokumentet skriver **ikke** om den CSS-en til å følge den nye
skalaen (det ville vært akkurat den "wholesale visual migration" som er
utenfor omfang, §10) — det etablerer skalaen som referansen nye
avstandsbeslutninger bør hente fra, og lukker gapet gradvis etter hvert
som seksjoner uansett røres av andre grunner.

---

## 4. Radius-, ramme- og skygge-prinsipper

`design/tokens.json` sin `radius_px` og `shadow` fanger verdier som
allerede er i aktiv, gjentatt bruk (ikke nye oppfinnelser):

| Token | Verdi | Typisk bruk observert i dag |
|---|---|---|
| `radius_px.sm` | 4px | Små inline-elementer (stat-bokser) |
| `radius_px.md` | 6px | Knapper, felt, de fleste kontroller |
| `radius_px.lg` | 8px | Kort, paneler, masthead-banneret |
| `radius_px.xl` | 12px | Modaler |
| `radius_px.pill` | 999px | Pille-/merke-former |
| `shadow.sm` | `0 4px 20px rgba(0,0,0,0.45)` | Knapper, små flytende elementer |
| `shadow.md` | `0 8px 24px rgba(0,0,0,0.5)` | Dropdowns, popovere |
| `shadow.lg` | `0 12px 40px rgba(0,0,0,0.5)` | Modaler, sidemenyens skuff |

**Rammeprinsipp:** merkevare-nære overflater (kort, knapper, masthead)
bruker en 1–2px heltrukket ramme i `accent.gold`, i full eller redusert
opasitet (f.eks. `rgba(196, 154, 42, 0.25–0.4)`) — aldri en kald grå ramme
i en varm sone, og aldri en varm gull-ramme i den kalde skifer-sonen.

---

## 5. Kontroller, knapper, kort

- **Knapper** bruker `radius_px.md`, `shadow.sm`, `accent.gold` som
  primær interaktiv farge, og en varm-til-nøytral bakgrunn avhengig av
  sone. Begge produkter konvergerer allerede på denne formen uavhengig av
  hverandre (Streamlits eget standard knapp-krom på App, `.legg-til-knapp`
  / `.knapperad button` osv. på Web).
- **Kort** (oppskrift-/identitetskortet, begge produkter) ligger alltid i
  den **varme merkevaresonen** (§1), bruker `radius_px.lg`, en 1–2px
  gull-ramme og `typography.serif` — dette er overflaten der de to
  produktene er visuelt nærmest identiske, med hensikt (det er artefaktet
  brukeren skriver ut og deler).
- **Paneler** (vanlige skjema-seksjoner) er bevisst **ikke** boksede —
  Web sin `.panel` har ingen egen bakgrunn/ramme/skygge, kun en tynn
  nøytral toppstrek pluss en gul seksjonsetikett. Dette holder
  arbeidsflaten rolig og reserverer "boks-kort"-behandlingen for den ene
  overflaten som faktisk skal skille seg ut.

---

## 6. Tilstander: fokus, hover, disabled, feil, suksess

| Tilstand | Regel | Token |
|---|---|---|
| Fokus | En synlig ring, aldri fjernet — `box-shadow: 0 0 0 2px rgba(196,154,42,0.25)` pluss en gull rammefarge | `focus_ring` i `tokens.json` |
| Hover | Subtil — en fargeforskyvning mot `pergament` (lenker/tekst) eller en liten `transform`/`opacity`-overgang (knapper), aldri et brått hopp | — (bruker `accent.pergament`) |
| Disabled | Redusert opasitet, ingen fargeendring utover det — aldri en helt avmettet grå som bryter den varme paletten | — |
| Feil | `accent.danger` (`#c0605a`) for tekst/ramme — reservert **utelukkende** til dette; aldri brukt dekorativt andre steder. En mildere, ikke-blokkerende rådgivende tone (f.eks. et forsiktig varsel) bruker bevisst en dempet/nøytral farge i stedet for `danger`, slik at en ekte feil alltid skiller seg ut ved kontrast — ikke ved å være ett av flere rødlige elementer på siden | `accent.danger` |
| Suksess / positiv | Ingen egen "suksess"-token finnes ennå — `accent.moss` brukes der en positiv/rolig tone ønskes (f.eks. "brygg denne igjen: ja"). Dette er et bevisst minimalt sett, ikke en forglemmelse (§10) | `accent.moss` |

---

## 7. Tilgjengelighet og kontrastregler

- Brødtekstfarge velges alltid mot **sin egen sones** bakgrunn —
  `web_cold_chrome.body` (`#f0f1f4`) mot `web_cold_chrome.bg` (`#0d0f15`),
  `web_warm_brand_zone.body` (`#f2ede0`) mot `web_warm_brand_zone.bg`
  (`#100b06`), osv. — aldri blandet på tvers av soner. Hvert
  tekst-/bakgrunnspar over måler godt over WCAG AA (4.5:1) for normal
  tekst ved de størrelsene som faktisk brukes.
- `accent.gold` mot en varm/nær-sort bakgrunn brukes for **overskrifter
  og stor/fet tekst**, der WCAG sin lavere AA-terskel (3:1) gjelder —
  aldri for liten brødtekst, der kontrastmarginen er trangere.
- Fokusringer fjernes aldri for tastaturbrukere; `:focus-visible` brukes
  eksplisitt på Web (`a:focus-visible`, `.meny-knapp:focus-visible`,
  `.sidemeny-lenke:focus-visible`, …) slik at museklikk ikke viser en
  fokusring, mens tastaturfokus forblir fullt synlig.
- Utskriftsdokumenter (`modules/card_template.py::render_a4_html`, Web
  sine fire utskriftsmaler) forlater bevisst den mørke paletten til fordel
  for **lys bakgrunn / mørk tekst**, uansett brukerens skjermtema —
  papirlesbarhet vinner alltid over merkevarekonsistens for noe som skal
  skrives ut.

---

## 8. Responsivitetsprinsipper

- **Ett bruddpunkt, brukt konsekvent på Web:** `640px` for det trangeste
  mobil-layoutet (stabling, full-bredde kontroller), med et lite antall
  sekundære bruddpunkt (`900px`/`1000px`) for topalonne-oppsett (byggeren,
  Hjelp-TOC) som kollapser til én kolonne. Ikke noe tredje mellomliggende
  "nettbrett"-bruddpunkt brukes — bevisst holdt enkelt.
- **`clamp()` fremfor faste media-query-fontbytter** for masthead-/hero-
  og identitetskort-typografi i begge produkter, slik at tekst skalerer
  kontinuerlig i stedet for å hoppe ved noen få faste bredder.
- **Desktop (Streamlit) har ikke noe eget responsivt lag** — den sikter
  mot ett enkelt skrivebordsvindu; Web er det eneste produktet med en
  mobil/responsiv overflate. Dette er en bevisst produktomfangsforskjell
  (Streamlit selv gjør ikke responsivt layout lett å kontrollere), ikke
  noe dette dokumentet prøver å endre.

---

## 9. Tone- og mikrotekstprinsipper

- **Serif-stemme vs. sans-stemme**: merkevare-/identitetstekst
  (`typography.serif`) leses med mer seremoni — fulle mottoer,
  store-bokstaver-spasiering, historisk innramming ("Ved Dalelva i
  Åsane"). Vanlig UI-tekst (`typography.sans`) er enkel, oppgavefokusert,
  prøver aldri å høres ut som merkevarestemmen.
- **Norsk er domenets hjemmespråk.** Jf.
  [`.claude/rules/desktop.md`](../.claude/rules/desktop.md) navngis/
  skrives bryggedomenebegreper på norsk først. Web tilbyr i tillegg et
  fullt, ekte engelsk oversettelseslag (`web/js/i18n.js`), men
  sannhetskilden og tonen er norsk-først i begge produkter.
- **Aldri alarmerende der det ikke trengs.** Stilveiledningsspråket er et
  konkret, allerede utrullet eksempel på dette prinsippet: tre vennlige
  nivåer ("innenfor" / "litt utenfor" / "tydelig utenfor") brukes i stedet
  for et brått "FEIL" — rådgivende, ikke dømmende. Samme prinsipp bør
  gjelde all fremtidig validerings-/veiledningstekst: si hva som er sant,
  ikke at brukeren gjorde noe galt.
- **Merkevaremotto og undertekst er faste strenger, skal ikke
  omskrives:** "Brygg med ild. Del med ære." og "Håndverk • Tradisjon •
  Karakter" — brukt ordrett i begge produkters merkevareoverflater og
  utskriftsdokumenter.

---

## 10. Produkttilpasning: Web vs. App

Dette avsnittet gjør eksplisitt hva som er **delt** vs. hva hvert produkt
står fritt til å tilpasse, slik at en fremtidig bidragsyter ikke må gjette:

**Alltid delt (skal ikke forgrenes):**
- De seks `accent`-fargene (§1) — ethvert nytt UI-element som trenger en
  merkevareaksent bruker en av disse seks, i begge produkter, aldri en ny
  engangs-hex.
- De to typografirollene (§2) — serif kun for merkevare/identitet, sans
  for alt annet, i begge produkter.
- Merkevaremotto/undertekst-teksten (§9), ordrett.
- Illustrasjons-/logoreglene fra `master_design_v1.md` (uendret, utenfor
  dette dokumentets omfang) — kråke ikke ravn, historisk kvern ikke
  moderne vindmølle, ingen norrøn mytologi-bilder, ingen sans-serif i
  merkevarekontekst, ingen lys bakgrunn for primærlogoen.

**Fritt å tilpasse per produkt (skal ikke tvinges identisk):**
- Overflatefarger (§1) — App og Web beholder hver sine allerede utrullede
  nær-sort-/tekst-/dempet-verdier; kun *mønsteret* (en kald standardsone +
  en varm merkevaresone) er delt, ikke de eksakte hex-verdiene.
- Responsiv oppførsel (§8) — Web har reelle bruddpunkt; App har ingen, og
  forventes ikke å få det bare for symmetriens skyld.
- Eksakte avstands-/radius-/skygge-verdier i *allerede utrullet* kode —
  skalaen i §3/§4 er referansen for **nytt** arbeid, ikke et mandat til å
  rette opp hver eksisterende pikselverdi.
- Layout-struktur — Web sin flate, ubokse `.panel`-seksjoner vs. App sin
  native Streamlit-widget-layout er begge gyldige; den delte kontrakten er
  "kort-/identitetsoverflaten er varm+serif+omrammet", ikke "hele
  sidelayouten må matche".

---

## Hva denne versjonen (v1.0) bevisst ikke gjør

Per issue #59 sitt eget omfang:

- **Ingen wholesale visuell migrasjon.** Eksisterende håndskrevet
  CSS/inline-stiler i `web/css/style.css` og `modules/card_template.py`
  står urørt, bortsett fra det ene, lille, ikke-forstyrrende
  konsumpsjonsbeviset under.
- **Ingen rammeverk-/byggesteg-endring.** Web har ingen bundler og får
  ingen her — `design/tokens.json` konsumeres direkte av Python
  (`modules/design_tokens.py`); på Web-siden verifiseres den mot den
  håndvedlikeholdte `:root`-blokken av `tests/test_design_tokens.py`
  fremfor å genereres inn i den, siden å introdusere et JSON→CSS-byggesteg
  er en strukturell endring dette issue-omfanget eksplisitt utelukker
  ("ingen rammeverksmigrasjon").
- **Ingen produktatferdsendring.** Ingenting ved hva noen av produktene
  beregner, lagrer eller viser endres.
- **Ett lite, reelt konsumpsjonsbevis, ikke en masseombygging:**
  `ui/branding.py` sin `_COLORS`-ordbok henter nå sine fire
  aksentverdier fra `modules/design_tokens.get_accent_colors()` i stedet
  for en lokal hardkodet kopi — samme resulterende verdier, altså ingen
  visuell endring, men reelt bevis på at token-filen faktisk er lastbar
  og brukbar fra produktkode, jf. issue-en sin eksplisitte "wire a tiny
  non-disruptive proof of consumption if necessary"-instruks.

**Utsatt til en fremtidig runde** (ikke påbegynt her): konvergere de fire
overflatefarge-gruppene i §1 til færre verdier; en delt numerisk
type-skala (størrelser/vekter/linjehøyder); en egen "suksess"-token
adskilt fra `accent.moss`; retrofit av eksisterende avstands-/
radius-verdier i allerede utrullet CSS til den nye skalaen; generere
`web/css/style.css` sin `:root`-blokk direkte fra `design/tokens.json`.
Hver av disse er en reell design- eller arkitekturbeslutning eieren må ta
eksplisitt — ikke noe som skal snike seg inn under dette
grunnlagsissuet.
