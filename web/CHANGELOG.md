# Kvernhaug Brygghus — Web changelog

Historisk, runde-for-runde narrativ for web-versjonens utvikling: hvorfor ting endret seg, hva det var før, og hvilken runde som gjorde det. For dagens arkitektur/kontrakt, se [README.md](README.md) — dette dokumentet er kun historikk og trengs sjelden for vanlig arbeid.

Nyeste runde øverst.

## TOOLS — Standalone ABV-kalkulator (issue #77, 2026-09-05)

Ny, syvende Verktøy-side (`verktoy.html`) med en frittstående ABV-kalkulator
-- tar målt OG+FG direkte, uten å opprette/åpne/endre en oppskrift eller et
brygg. Lagt til i sidemenyen på alle 19 eksisterende NO-sider (samt
tilsvarende EN-speiling).

**Core-kontrakt, delt med App:** `web/js/calc.js` fikk `beregnAbvFraOgFg()`
(pluss `beregnAbvStandard()`/`beregnAbvHighGravity()`/`validerMaaltOgFg()`),
en direkte port av `modules/calculations.py`s nye
`beregn_abv_fra_og_fg()`-familie -- egen kontrakt fra `beregnFgOgAbv()`
(som er en forventet-FG-planleggingsberegning, ikke en målt-verdi-
kalkulator). Se `core/calculation_golden_vectors.json`s nye
`measured_abv`-cases og docs/development/CORE_CALCULATION_CONTRACT.md.

**To eksplisitte estimater, aldri stille byttet ut:** standardformelen
`(OG-FG)*131.25` vises alltid; et separat high-gravity-estimat vises i
tillegg når OG >= 1.070 (samme presentasjonsterskel som App sin
`ui/abv_calculator_panel.py`) -- ren UI-logikk, ikke en del av
Core-kontrakten.

**Filer:** `verktoy.html` (ny), `web/en/verktoy.html` (generert), `js/calc.js`,
`js/verktoy_page.js` (ny), `js/i18n.js` (nye `verktoy.*`/`nav.verktoy`/
`meta.verktoy.*`-nøkler, NO+EN), `css/style.css` (`.verktoy-feil`),
`scripts/generate_web_i18n_pages.py` (`PAGES`), `sitemap.xml` (regenerert),
sidemeny-lenke lagt til på alle 19 øvrige NO-sider + EN-speilinger.

## PRI 4C — Core custom-ingredient identity-kontrakt (2026-09-04)

Web-siden adopsjon av `docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md`
for NYE egendefinerte ingredienser, etter App P4A/P4B (issue #38/#48). Rent
internt/datamodell — ingen synlig UI-endring.

**Ett delt, opakt navnerom.** Web mintet tidligere TRE separate custom-id-
navnerom: `egen_malt_<timestamp>_<teller>`, `egen_humle_<timestamp>_<teller>`
(begge `app.js::nyEgendefinertId()`) og `egen_pantry_<type>_<unik>`
(`pantry.js::nyPantryCustomId()`). Fra og med nå mintes ENHVER ny custom
malt/humle/gjær/pantry-ingrediens i kontraktens kanoniske
`kbh-custom-<uuidv4>`-format via ny, delt `js/custom_ingredient_id.js`
(`nyCustomIngredientId()`), med generasjonstids-kollisjonssjekk på tvers av
pantry (`allePantryItems()`), alle lagrede oppskrifter (`alleOppskrifter()`)
og alle frosne brygg-snapshots (`alleBrygg()`) -- de tre eneste lokale
lagringsstedene som kan holde en custom-id i dag. Allerede lagrede
`egen_*`-ider er permanent grandfatret (kontraktens §9) og røres ikke.

**Custom-gjær fikk endelig en stabil id.** `gjaerCustom` hadde tidligere
INGEN id i det hele tatt (kontraktens §5, tredje dokumenterte Web-hull) --
kun det selvbeskrivende navn/produsent/gjaertype/attenuation-innholdet.
Mintes nå lazy (`app.js::_lesGjaerEgendefinert()`), stabilt gjennom
redigering/lagring/eksport/import/reload av samme oppskrift.

**Script-lasting.** `js/pantry.js` lastes nå også på `index.html` (for
kollisjonssjekkens `allePantryItems()`), og `js/brew_storage.js` lastes nå
også på `pantry.html` (for `alleBrygg()`) -- begge sider laster i tillegg
den nye `js/custom_ingredient_id.js`. `web/en/index.html`/`web/en/pantry.html`
regenerert tilsvarende.

## Bryggeskole P3B — Gjærvalg, Klaring og responsiv navigasjon (2026-08-23)

Den andre og siste av de målrettede rundene Gap Audit V1 pekte ut. **P3B er
ferdigstilt** — den er ikke lenger en kandidat.

**To nye hjelpesider.** `hjelp/gjaervalg.html` dekker hva stammen faktisk
påvirker, ale/lager/kveik uten de vanlige forenklingene, utgjæring (oppgitt vs.
faktisk FG), flokkulering, ester- og fenolkarakter/POF, alkoholtoleranse,
temperaturarbeidsområde, tørr vs. flytende gjær, «én pakke er ikke en pitch
rate», en beslutningsflyt for stammevalg, lesing av produsentark, trykk og
gjenbruk, samt feilsøking. `hjelp/klaring.html` dekker hva «klart øl» betyr,
haze-kilder, hot og cold break, trub, whirlpool som trub-håndtering, kettle
finings (Irish moss/Whirlfloc), cold crash, gelatin og andre finings, chill haze
kontra permanent haze, haze over tid, klarhet vs. stil, koblingen til gjærvalg,
feilsøking og en praktisk klaringsplan.

Hjelpedelen går dermed fra 10 til **12 sider**. Ingen beregningslogikk er rørt:
oppskriftsbyggeren vurderer verken gjærstammer eller klarhet, og det står
eksplisitt på begge sidene.

**NO/EN.** Begge sidene har full engelsk speiling under `web/en/hjelp/`, generert
som vanlig av `scripts/generate_web_i18n_pages.py`. Nye namespaces
`hjelp.gjaervalg.*` (122 nøkler) og `hjelp.klaring.*` (102 nøkler); i18n er
1586 NO / 1586 EN og symmetrisk. NO og EN ble forfattet parvis, ikke
maskinoversatt.

**Registrering og SEO.** `PAGES` 17 → 19, `sitemap.xml` 32 → **36 URL-er**
(18 sider × NO/EN, `utskrift.html` fortsatt ekskludert), canonical/hreflang og
meta-description på plass for begge nye sider, favicon arvet fra sidemalen.
Generatoren er deterministisk verifisert: byte-identisk output ved re-kjøring.

**Krysslenker.** Sidene lenker til eksisterende Bryggeskole framfor å duplisere
den (gjærhelse, starter, sterke øl, trykkgjæring, gjærhøsting, sensorikk, humle,
vannkjemi, OG/FG, mesking). Sju reverse-lenker er lagt inn fra eksisterende
sider — bevisst begrenset for å unngå link-spaghetti. Kontroll av alle interne
href-er over de 24 hjelpesidene: 0 brutte lenker, 0 manglende ankere.

**Navigasjon — gruppering ved side 12.** Den permanente beslutningen fra P3A var
å vurdere nav-en på nytt rundt side 11–12. Det er nå gjort, og `hjelp-side-nav`
er gruppert i **KOM I GANG / BRYGGMESTER / UTSTYR**. Gruppene speiler appens egne
to modi (Bryggelærling/Bryggmester) og er ren HTML/CSS uten JS — ingen
dropdown-engine, ingen ny avhengighet. Chip-reglene (padding, font-size,
`min-height: 44px`) er uendret.

**Responsiv tilpasning.** Grupperingen kostet for mye vertikal plass på smale
skjermer: målt 293 px nav (4 rader) ved 768 px og 449 px (7 rader) ved 375 px,
som dyttet første innhold under folden på en 375×667-telefon. Løst med én media
query under hjelpesidenes etablerte 900 px-brekkpunkt, som skjuler gruppetitlene
og lar chipsene flyte ut som én wrappende rad (`display: contents`). Målt effekt:
768 px 293 → **164 px** (4 → 3 rader), 375 px 449 → **320 px** (7 → 6 rader),
hovedinnholdet 129 px lenger opp i begge. Desktop er uendret.

**Verifikasjon.** Full visuell regresjon etter `web-full-regression`-skillet:
Chromium 151 + Firefox 153 × 1920/1280/900/768/375 px, 90 sidelastinger. 0
horisontal overflow, 0 klippede chips, 0 chip-overlapp, 44 px minste
touch-target, nøyaktig én korrekt aktiv chip per side, 0 tabeller utenfor
viewport, 0 rå i18n-nøkler, 0 «undefined», 0 konsollfeil, 0 nettverksfeil.
Testbaseline **942/942 PASS** (938 + 4 nye nav-kontrakttester som låser at alle
hjelpesider er representert i nav-en og at aktiv chip peker på siden selv).

*Kjent kosmetisk detalj:* ved nøyaktig 900 px overlapper nav-ens
`max-width: 900px` med TOC-ens `min-width: 900px`, slik at nav-en er flat mens
resten er i desktop-modus. Alt fungerer; en eventuell justering til `899.98px`
er ikke gjort.

## Lansering, favicon og Bryggeskole P0–P3A (2026-08-14 → 2026-08-23)

Samlepost for milepælene etter Runde 25C. Disse rundene ble dokumentert per
commit og i `docs/PROJECT_STATUS_AUGUST_2026.md` framfor som egne changelog-
seksjoner; posten her lukker historikk-hullet uten å duplisere statusdokumentet.

**Produksjon.** `web/` er deployet og live på `https://kvernhaugbrygghus.no`
(statisk hosting, Domeneshop). Deploy er en eksplisitt, manuell handling via
`scripts/deploy_web.ps1` (interaktiv FTPS-innlogging, `-DryRun` tilgjengelig) —
ingen CI/CD, ingen automatisk deploy.

**Favicon** (`cee2a76`). Fullt favicon-sett integrert på alle sider, committet og
live. Generatoren justerer favicon-stiene for `/en/`-dybden på samme måte som
øvrige asset-stier, og `tests/test_generate_web_i18n_pages.py` har egen
favicon-dekning (alle NO- og EN-sider har lenkene, filene finnes faktisk, stiene
er dybdejustert).

**Bryggeskole P0–P3A** — et sammenhengende innholdsprogram som utvidet hjelpe-
delen fra 4 til 10 hjelpesider:

| Runde | Innhold | Commit |
|---|---|---|
| P0 | Nybegynnerfundament | `e050b67` |
| P1A | Prosess, vann, etter gjæring | `744cd5e` |
| P1B | Gjær, karbonering, lagring, feilsøking | `708294e` |
| P2A | Avanserte meskemetoder | `d0e0aef` |
| P2B | Trykkgjæring, spunding, closed transfer | `e6831f4` |
| P2C | Sterke øl / high gravity | `cc986f0` |
| P2D | Gjærhøsting og gjenbruk | `a2a35b1` |
| P2E | Avansert vannkjemi | `d58c591` |
| P2F | Sensorikk og off-flavours | `f03be9f` |
| P3A | Humle i dybden + generell bryggesikkerhet | `beeb94c` |

Nye sider: `hjelp/trykkgjaering.html`, `sterke-ol.html`, `gjaerhosting.html`,
`vannkjemi.html`, `sensorikk.html`, `humle.html` — hver med engelsk speiling
under `web/en/hjelp/` og eget i18n-namespace (`hjelp.trykk.*`, `hjelp.sterkeOl.*`,
`hjelp.gjaerhosting.*`, `hjelp.vannkjemi.*`, `hjelp.sensorikk.*`, `hjelp.humle.*`).
`hjelp/index.html` er kanonisk hub for begrepsforklaringer/FAQ; guidesidene lenker
dit framfor å gjenta definisjonene. `hjelp-side-nav` var ved P3A fortsatt
flat med flex-wrap — bevisst beholdt etter reell vurdering, med gruppering
utsatt til rundt side 11–12 (gjennomført i P3B, se posten over).

**Gap Audit V1** (utført før P3A): fundamentet er COMPLETE, ingen større
innholdshull, og retningen er «B — én til to målrettede runder» framfor fortsatt
storstilt innholdsbygging. P3A var den første av disse; P3B (gjærvalg + klaring)
ble den andre og siste — se posten over.

**Testbaseline** ved P3A: 938 tester, 0 skipped / 0 errors / 0 failures
(Python 3.12.10, repoets `.venv`). Av disse ligger 49 i
`tests/test_generate_web_i18n_pages.py` og dekker web/**-generatoren direkte.

## Runde 25C — Bryggeloggen som brukeropplevelse (2026-08-15)

Første synlige lag over 25B-datamodellen: ny side `bryggelogg.html`
(+ generert EN, sitemap 20 → 22 URL-er, ny «🪓 Bryggelogg»-lenke i
sidemenyen på alle sider) og ny `web/js/brygg_page.js`. Ingen nytt
designsystem — `.panel`, `.knapperad`, `.felt-rad`, `.modus-bryter` og
`.utstyr-liste`/`.utstyr-rad` gjenbrukes uendret, og den ene nye
komponenten (`.brygg-kort`) låner rammespråket fra `.utstyr-rad`.

Det bærende UX-valget: siden organiseres etter brukerens NESTE HANDLING,
ikke etter datamodellen. Ordene «snapshot», «actuals» og «sensing»
finnes ikke i noe brukeren ser — der står det «Fikk du målt OG?», «Står
ølet fortsatt til gjæring?» og «Ville du brygget dette igjen?». Hvilket
kort et brygg får, utledes av en ny `bryggFase()` fra hva som faktisk er
fylt ut, ikke av lagret `status`. Aktene er dermed en fortelling som
oppstår av dataene, ikke en låst prosess: felt kan fylles i vilkårlig
rekkefølge, hoppes over, og et forkastet brygg forblir gyldig historikk
med sitt eget «Neste gang».

Hver registrering gir noe TILBAKE i stedet for å kvittere med «Lagret».
Ny `faktiskEffektivitet()` utleder faktisk meskeutnyttelse ved å
eliminere totalpoengene mellom plan og faktisk — utelukkende fra det
frosne snapshotet, aldri fra det levende biblioteket, så et brygg fra i
fjor gir samme svar i dag. Bryggedagen svarer «Du traff OG 1.049 mot
planlagt 1.052. Det gir 71 % effektivitet mot planlagt 75 %»;
gjæringen svarer med faktisk ABV, utgjæringsgrad og retning på
FG-avviket. Ingen av tallene lagres — alt regnes ut ved visning.

«Neste gang» behandles som førsteklasses informasjon, ikke et notatfelt
nederst: eget gullrammet felt, egen plass i historikkraden, og — den
sirkulære sløyfen — vist i byggeren FØR neste brygg startes, via en
bevisst lettvekts `sisteErfaringForOppskrift()` som henter kun den ene
tekststrengen.

Smakshjulet krever aldri 18 felt. «Ikke vurdert» og «vurdert likt som
planlagt» skilles uten ny datamodell: sier brukeren «Ja, som forventet»,
lagres den predikerte profilen som faktisk profil (nøyaktig hva brukeren
påstår), og da finnes `sensing.flavorProfile`. Har brukeren ikke sagt
noe, finnes den ikke. Detaljerte justeringer ligger bak en `<details>`,
forhåndsutfylt fra prediksjonen.

## Runde 25B — .kbhbrew datafundament (2026-08-15)

Ren datamodell-runde: ingen UI, ingen nye sider, ingen bryggelogg-visning.
Ny `web/js/brew_storage.js` (DOM-fri) etablerer brygget som et
førsteklasses objekt ved siden av oppskriften. En oppskrift er PLANEN; et
brygg er den historiske HENDELSEN.

Fem lag, med grenser satt etter tidspunkt og type sannhet: identitet/
livssyklus, frosset snapshot, actuals (målinger), sensing (opplevelse) og
learning (`whatWorked`/`whatChanged`/`nextTime`). Lagring:
`kvernhaug_web_brygg` med `{format:"kbh-brews", version:1, items:[]}` —
samme envelope- og valideringsmønster som resten av systemet.

Snapshotet er rundens kjerne og svarer på ett spørsmål: *hva visste KBH da
dette brygget startet?* Det fryser både inndata (hele recipe-payloaden,
de FULLE masterdata-oppføringene for de refererte ingrediensene, aktiv
utstyrsprofil) og utdata (predikert OG/FG/ABV/IBU/EBC/BU:GU,
smaksprofil-vektoren, stilmatch-navn og -score), pluss proveniens
(motorversjon, recipeSchemaVersion, bibliotekstørrelser, tidspunkt).
Grunnen er at predikerte verdier IKKE kan gjenskapes pålitelig senere:
maltpotensialer korrigeres, alfasyrer oppdateres, beregningsmotoren
forbedres og BJCP-data revideres. Uten frysing ville "forventet" endret
seg i ettertid, og hele plan-mot-faktisk-premisset falt.

Motsatt lagres aldri noe som KAN gjenskapes: avvik mellom plan og faktisk,
og faktisk ABV, regnes ut ved visning (`planVsFaktisk()`, `faktiskAbv()`).
Heller ikke frosset: SVG/grafikk, språk- og enhetspreferanser, hele
masterdata-biblioteket, og — viktig — de lokaliserte tekstene fra
stilanalysen (`balanse`, `problemer`, `mangler`), som er bygget med `t()`
og ville bakt brukerens språk inn i historikken.

Et ufullstendig brygg er gyldig: alle felt i lag 3-5 er valgfrie og kan
fylles ut i vilkårlig rekkefølge, når som helst. Status er metadata med
tre fritt omsettelige verdier (`active`/`done`/`discarded`), ikke en
tilstandsmaskin — et forkastet brygg er fullverdig historikk.
`recipeId` er en SVAK referanse: slettes eller omdøpes oppskriften, er
brygget fortsatt komplett, fordi snapshotet er autoritativt.

Nytt `.kbhbrew`-filformat med en identitetspolicy som bevisst avviker fra
`.kbhrecipe`: en importert oppskrift lander i kladden og lagres først når
brukeren vil, mens en importert brygghistorikk må skrives rett i lageret.
Å bare mynte ny id ved hver import ville derfor duplisert hele historikken
ved gjentatt import. Løsningen skiller `brewId` (lokal lagringsidentitet,
myntes alltid lokalt, adopteres aldri fra fil) fra `originBrewId`
(historisk identitet, følger filen) — så egen historikk kan flyttes til ny
maskin, brygg kan deles uten id-kollisjon, og gjentatt import gjenkjennes
som duplikat i stedet for å dobles stille.

## Runde 25A — Versjonert oppskriftslagring + stabile recipeId-er (2026-08-15)

Kirurgisk foundation-runde uten nye brukerfunksjoner.
`kvernhaug_web_oppskrifter` var den siste lagringskontrakten uten
format/version-wrapper: en flat ordbok nøklet på OPPSKRIFTSNAVN, slik at
navnet også var identiteten. Det ga to problemer — å endre navn og lagre
opprettet en NY rad og lot den gamle bli liggende (utilsiktet duplikat),
og ingen annen del av systemet kunne holde en referanse til en oppskrift
som overlevde et navnebytte.

Ny `web/js/recipe_storage.js` (DOM-fri, samme mønster som `equipment.js`/
`pantry.js`) eier nå nøkkelen med formen `{format:"kbh-recipes",
version:1, items:[{recipeId, recipe}]}`. Kontrakten er: **recipeId =
stabil lokal identitet** (genereres én gang, overlever navnebytte, aldri
utledet fra navnet), **navn = ren visningsmetadata**. Payloaden ligger
nestet under `recipe` slik at den er nøyaktig samme selvstendige objekt
som `.kbhrecipe` sitt `recipe`-felt — ett objekt som kan løftes ut og
fryses i sin helhet, uten at lagringsmetadata blør inn i historikk eller
eksporterte filer. `recipeSchemaVersion` ligger INNE i payloaden, ikke
som søsken, fordi versjonen må reise sammen med oppskriften inn i filer
som skal tolkes om mange år.

Migrering fra den flate ordboken skjer automatisk ved første lesing,
usynlig for brukeren, med insettingsrekkefølge og alle canonical verdier
bevart. Rå kopi av den gamle strengen skrives til
`kvernhaug_web_oppskrifter_legacy_backup` med verifiserende
tilbakelesing FØR hovednøkkelen overskrives — feiler noe underveis, står
den gamle nøkkelen urørt og appen kjører videre på den migrerte staten i
minnet. Backupen overskrives aldri senere.

Lagring er nå upsert på recipeId i stedet for på navn, så navnebytte
oppdaterer riktig rad. Navneunikhet er bevisst BEVART fra den gamle
kontrakten (den flate ordboken gjorde duplikatnavn umulig) — denne
runden åpner ikke nytt UX-scope. Oppskriftsvelgerne i Utskrift og Pantry
bruker nå recipeId som `<option>`-verdi i stedet for navn. Aktiv kladd
kan bære `recipeId` når den redigerer en lagret oppskrift.

`.kbhrecipe`-identitet: recipeId skrives ALDRI til fil og leses ALDRI
fra fil — den er lokal, aldri global. En delt eller gjeninnlest fil får
fersk lokal identitet først når brukeren lagrer, slik at to nettlesere
aldri kan ende med samme id for to uavhengige oppskrifter. En fil som
likevel inneholder en recipeId (håndredigert) får den strippet ved
import. `recipeSchemaVersion` følger derimot med payloaden.

Fant og fikset underveis: lagring til localStorage kunne feile stille.
`lagreOppskrift()` skrev tidligere uten try/catch, så full lagringskvote
eller privat nettlesing kastet et ufanget unntak i klikk-handleren —
brukeren så ingen bekreftelse og ingen feil. Skriving verifiseres nå ved
tilbakelesing, og feil vises som en vennlig melding i det eksisterende
statusfeltet.

Dette fjerner den siste blokkeren for et fremtidig `.kbhbrew`, som må
kunne peke svakt på en oppskrift (recipeId) og samtidig bære et sterkt,
frosset snapshot av den (`item.recipe` + `recipeSchemaVersion`).

## Runde 24C — Pantry V1 polish: backup + quick add (2026-08-15)

Tredje og siste steg i Pantry V1: gjør lageret trygt å stole på som
eneste lagringssted (local-first uten sync) og lukker sløyfen mellom
"Hva mangler du?" og selve lageret.

Eget, portabelt `.kbhpantry`-backupformat i `pantry.js`
(`{format:"kbhpantry", version:1, exportedAt, generator,
pantry:{items:[...]}}`) — helt adskilt fra `.kbhrecipe`, alltid
canonical (kg/gram/antall), aldri valgt display-enhet. Eksport laster
ned `Kvernhaug-Pantry-Backup-YYYY-MM-DD.kbhpantry` lokalt (samme
Blob-mønster som `kbhrecipe.js`), ingen server-request. Import er
RESTORE/REPLACE, ikke merge — brukeren bekreftes eksplisitt før
eksisterende lager erstattes, og en avslått bekreftelse endrer
ingenting. Valideringskontrakt: wrapper-feil (ugyldig JSON, feil
format/version, `pantry.items` ikke en array) avviser HELE importen;
enkelt-item-feil (negativ mengde, desimal gjær-antall, custom uten
navn, o.l.) filtreres bort stille SÅ LENGE wrapperen selv er gyldig —
samme prinsipp som `lesPantryState()` allerede bruker for korrupt
localStorage-innhold.

Ny "Legg til i lager"-knapp på hver tracked shortage-rad i "Hva mangler
du?" — bruker ALLTID `pantry_compare.js` sin kanoniske
`shortage`-verdi direkte (aldri et parset/avrundet display-tall, for å
unngå drift på tvers av Metric/US). Merger inn i eksisterende
pantry-rad om varen allerede finnes, oppretter ny ellers. Skjules helt
når kravet allerede er dekket. Egendefinerte oppskrift-rader får aldri
denne knappen — de forblir i "Ikke sporet i lager" med en kort
forklaring om at de må legges inn manuelt.

Ingen nye sider (sitemap fortsatt 20 URL-er), ingen endring i
`.kbhrecipe`- eller andre localStorage-nøkler (kun
`kvernhaug_web_pantry` leses/skrives av backup/import). 32 nye
symmetriske NO/EN-nøkler. Pantry V1 anses funksjonelt komplett etter
denne runden — se `web/README.md`.

## Runde 24B — Oppskrift ↔ lager-sammenligning + handleliste (2026-08-15)

Andre steg i Pantry/Shopping V1: ny `web/js/pantry_compare.js` (DOM-fri
sammenligningsmotor, samme oppdeling som `recipe_engine.js`) regner ut
`required`/`available`/`shortage` per ingrediens ved å slå sammen en valgt
oppskrift (aktiv kladd eller lagret oppskrift -- gjenbruker EKSAKT
`utskrift_page.js` sitt velger-/lagringsmønster, ingen ny oppskrifts-
storage-kontrakt) mot `pantry.js` sin `allePantryItems()`. Malt-/
humlerader med samme masterdata-id summeres FØR sammenligning (flere
humletilsetninger ved ulik koketid teller som ett behov); gjær har ingen
eksplisitt pakke-count i dagens oppskriftsmodell, så en valgt gjær-id
telles som `required = 1 pakke`. Status er `nok`/`knapp`/`mangler` --
"knapp" (mindre enn 5% margin for malt, 10% for humle) er rent
rådgivende og teller aldri som shortage. Egendefinerte oppskrift-rader
matches ALDRI mot lageret (verken bibliotek- eller custom-pantryvarer,
selv ved identisk navn) -- de vises i en egen "Ikke sporet i lager"-
seksjon, bevisst sikkerhet mot feil matching (se Runde 24 pkt. 6/8).
Ukjent/fjernet masterdata-id (oppskriften refererer en ingrediens som
ikke lenger finnes) viser en trygg "Ukjent / ikke sporet"-fallback i
stedet for å gjette.

`web/pantry.html` fikk to nye seksjoner foran lagerlisten: "Oppskrift"
(velger) og "Hva mangler du?" (rad-basert resultatliste + oppsummering +
"Ikke sporet i lager"-blokk + en "Kopier handleliste"-knapp som kun
kopierer shortage-varer og ikke-sporet-varer som ren tekst -- ingen
pris/butikk/valuta, shop-agnostisk per Runde 24B sitt eksplisitte krav).
Sammenligningen regnes ALLTID på nytt fra oppskrift+lager (aldri
persistert) og oppdateres live -- uten reload -- ved enhver
pantry-mutasjon, oppskriftsbytte, enhetsbytte (Metric/US) eller
språkbytte, siden `visPantryListe()` nå alltid ender med et kall til
`_oppdaterSammenligning()`. Ingen ny side, ingen sitemap-endring (fortsatt
20 URL-er), ingen endring i `.kbhrecipe`- eller
`kvernhaug_web_oppskrifter`-kontraktene.

Én reell bug funnet og fikset underveis: `visPantryListe()` sin
early-return for tomt lager lå FØR det nye `_oppdaterSammenligning()`-
kallet, så sammenligningen ble stående med utdaterte tall når siste
pantry-vare ble slettet (viste f.eks. fortsatt "På lager: 5 kg" etter at
varen var borte). Flyttet kallet inn i early-return-grenen også.

## Runde 24A — Pantry V1: storage + lager-CRUD (2026-08-15)

Første steg i Pantry/Shopping V1 (se Runde 24 sin arkitekturanalyse):
lokal, kontofri lagerstyring for malt/humle/gjær, helt separat fra
recipes/utstyr/preferanser/.kbhrecipe. Ny `web/js/pantry.js` (DOM-fri
state-modul, samme mønster som `equipment.js`) eier
`kvernhaug_web_pantry`-nøkkelen (`{format:"kbh-pantry", version:1,
items:[]}`) med samme defensive fallback-til-tom-state-kontrakt ved
korrupt/manglende/feil data. Identitet er ALLTID eksakt masterdata-id
(samme skjema som oppskrift-ingredienser) valgt via samme `combobox.js`
som byggeren bruker -- aldri fritekst/fuzzy-matching. Custom pantry-varer
får sin egen `egen_pantry_<type>_<unik>`-navnerom, bevisst forskjellig fra
oppskriftenes `egen_<type>_<timestamp>_<teller>`, og matches ALDRI
automatisk mot oppskrift-custom (kommer evt. som eksplisitt, brukerstyrt
kobling i en senere runde, ikke i V1).

Ny side `web/pantry.html` (+ generert `web/en/pantry.html`, sitemap
18→20 URL-er, ny "📦 Lager"/"Pantry"-lenke i sidemenyen på alle sider,
IKKE gatet bak Bryggmester-modus). Rad-basert liste (gjenbruker
`.utstyr-liste`/`.utstyr-rad`-mønsteret fra utstyrsprofiler, ikke en
HTML-tabell) med ett delt legg-til/rediger-skjema (samme ett-skjema-
prinsipp som `_apneUtstyrSkjema()`). Mengde vises/tas imot i valgt
Metric/US customary via eksisterende `units.js`
(`formatMaltMass`/`parseMaltMass`/`formatHopMass`/`parseHopMass`) --
ingen ny konverteringslogikk. Gjær er rent pakke-antall (heltall, ingen
enhetskonvertering). Duplikat-forsøk på samme biblioteks-id spør
eksplisitt om mengden skal legges til eksisterende beholdning, i stedet
for å opprette en ny rad stille.

To reelle bugs funnet og fikset underveis: (1) samme `[hidden]`-vs-
`display:flex`-spesifisitetsfelle som Runde 21B.2 løste for
`.utstyr-rad-handlinger` traff nå `#pantry-type-bryter`/`#pantry-velger-rad`
også -- egne scopede overrides lagt til. (2) skjemaets `required`/`step`-
attributter blokkerte stille `submit`-eventet via nettleserens native
constraint validation før JS-valideringen fikk kjøre (samme bugklasse som
Runde 22 sitt utstyrsfelt-funn) -- fikset med `novalidate` på skjemaet,
all validering skjer nå kun i JS med vennlige, oversatte feilmeldinger.

Ingen recipe-sammenligning/mangelliste ennå -- det er Runde 24B.

## Runde 23A — Importer preview: unit-aware display (2026-08-15)

Lukker det siste kjente display-gapet fra Runde 23: treff-listen i
Importer sin tekstforhåndsvisning viste alltid hardkodet `kg`/`g`
(`import.treffMalt`/`import.treffHumle` i i18n.js), uansett valgt
unitSystem. Malen inneholder ikke lenger enheten selv -- `mengde`/`gram`
formateres nå via `formatMaltMass()`/`formatHopMass()` fra units.js
(samme helper byggeren bruker) FØR verdien settes inn i malen, så
oversettelsestekstene forblir enhetsnøytrale. Et enhetsbytte mens
forhåndsvisningen står synlig rerendrer den nå direkte fra sist parsede
data via en ny `kvernhaug:enhetendret`-lytter i importer_page.js -- ingen
ny analyse nødvendig. Ingen endring i parser, canonical data eller
.kbhrecipe -- rent display-only, som forventet.

## Runde 23 — Unit completeness: Importer forstår US customary (2026-08-15)

Lukker den mest synlige gjenværende glippen etter Runde 22: fritekstimport
på Importer-siden var fortsatt metrisk-spesifikk (kun `kg`/`g`/`L`), mens
resten av appen siden Runde 22 lot brukeren velge US customary.
`recipe_importer.js` sine regex-mønstre for batch/malt/humle er utvidet
til å i tillegg forstå `US gal`/`gal`/`gallon(s)` (alltid tolket som US
gallon, aldri Imperial/UK), `lb`/`lbs`/`pound`/`pounds`, og `oz`/
`ounce`/`ounces` -- parseren tolker ALLTID enheten som faktisk står i
teksten, uavhengig av brukerens valgte visningsenhet, og returnerer alltid
canonical metrisk (liter/kg/gram), akkurat som før. Selve konverteringen
gjenbruker `units.js` sine `parseVolume`/`parseMaltMass`/`parseHopMass`
direkte, så det finnes fortsatt bare én kilde til
US_GALLON_L/LB_KG/OZ_G-konstantene i hele web-appen. Eksplisitt "imperial
gallon(s)" gir en vennlig advarsel i stedet for å stille bli tolket som US
gallon. Dette er et bevisst avvik fra desktop-portens 1:1-prinsipp --
desktop har ingen unitSystem-velger og forblir uendret. Importer-siden
laster nå `units.js`, og hjelpeteksten i "Lim inn oppskriftstekst"-fanen
viser ett metrisk og ett US-eksempel per format.

## Runde 22 — Faktisk enhetsvalg: Metric / US customary (2026-08-14)

Bygger videre på Runde 21C sin unit-ready arkitektur og gjør US customary
til en faktisk brukbar visning, ikke bare en helper. Ny, DOM-uavhengig
`web/js/preferences.js` styrer `kvernhaug_web_preferanser`
(`{format:"kbh-preferences", version:1, unitSystem:"metric"|"us"}`) --
default metric, trygg fallback ved manglende/korrupt/ugyldig state.
Kompakt to-knappers "Måleenheter"-bryter i drawer-menyen på alle 9 sider
(samme sted som språkvelgeren, men helt uavhengig av språkvalg), koblet
via en ny `kvernhaug:enhetendret`-hendelse.

`units.js` utvidet med `formatMaltMass`/`parseMaltMass` (kg/lb) og
`formatHopMass`/`parseHopMass` (g/oz), pluss `formatTemperature`/
`parseTemperature` (°C/°F, arkitektur klar men ikke koblet til noe UI --
web har ingen brukerredigerbare temperaturfelt). Batchvolum, skaler-til,
malt-kg, humle-gram og utstyrsprofilenes kjelekapasitet/maks-batch viser
og tar imot tall i valgt unitSystem. Hvert felt holder canonical
metric-verdi i et `data-canonical`-attributt (aldri avrundet) -- et
unit-bytte rerendrer ALLTID fra dette attributtet, aldri ved å tolke
allerede avrundet displaytekst på nytt, slik at gjentatte Metric↔US-bytter
ikke driver. Recipe-/utstyr-beregninger (OG/FG/ABV/IBU/EBC, malt-%-
binding, batch-advarsel-terskel) forblir uendret av unit-bytte, siden de
alltid leser samme canonical-attributt uavhengig av visning.

`.kbhrecipe` og `kvernhaug_web_utstyr` uendret -- ingen `unitSystem`-felt
lagt til noe sted i lagret data, kun en egen, separat UI-preferanse.
print.js sine tidligere rå `" L"/"kg"/"g"`-interpoleringer (rapportert i
Runde 21B.1) er nå ryddet til samme formatteringspunkt som resten av
appen. Én reell HTML5 step-valideringsbug funnet og fikset underveis
(samme klasse som Runde 21B sin: `step="0.5"` på utstyrsskjemaets
kapasitet/maks-felt avviste stille gyldige US gallon-desimaltall som
"13.21" -- endret til `step="0.01"`).

## Runde 21C — Unit-readiness: metric canonical / US-klar arkitektur (2026-08-14)

Liten, kontrollert arkitekturrunde: ingen ny funksjonalitet, ingen
konvertering til US customary er slått på noe sted i UI-et. Ny
DOM-uavhengig modul `web/js/units.js` samler volum-formattering/parsing
bak `formatVolume(liter, unitSystem)`/`parseVolume(tekst, unitSystem)` —
`unitSystem` støtter i dag kun `"metric"` i praksis, men `"us"` finnes
teknisk implementert (gallons, US_GALLON_L = 3.785411784) som et
demonstrert extension point uten at noe UI kaller det ennå. `_fmtVolum()`
i `app.js` delegerer nå til samme modul i stedet for å duplisere
avrundingslogikken. Utstyrsprofilenes tre visningstekster
(`utstyr.detaljKapasitet`/`detaljMaks`/`batchAdvarsel`) går nå gjennom
ett formatteringspunkt i stedet for hardkodet " L" i i18n-malene.
Canonical storage uendret (liter, `kettleCapacityL`/`maxRecommendedBatchL`
som rene tall) — `kvernhaug_web_utstyr` og `.kbhrecipe` har ingen
schemaendring, ingen `unitSystem`-felt lagt til noe sted. LB_KG/OZ_G-
konstanter dokumentert i `units.js` som fremtidig kontrakt; masse- og
temperaturkonvertering er eksplisitt ikke bygget denne runden.

## Runde 19 — Google Search Console-verifisering (2026-08-14)

Ren dokumentasjons-/verifiseringsrunde, ingen kodeendring. Domain
property `kvernhaugbrygghus.no` verifisert i Google Search Console
via DNS TXT-record hos Domeneshop (én permanent record, ingen andre
DNS-endringer). `sitemap.xml` sendt inn og akseptert — Search Console
rapporterte status «Fullført» med 18/18 URL-er oppdaget, som matcher
nettstedets faktiske sitemap (9 NO + 9 EN). Manuell «Be om
indeksering» sendt for de 4 høyest prioriterte sidene (`/`, `/en/`,
`/hjelp/`, `/en/hjelp/`); resten av de 18 sidene håndteres via
sitemap fremfor enkeltvise forespørsler.

Første URL Inspection av `/` viste «Oppdaget – ikke indeksert for
øyeblikket», uten noen teknisk blokkering indikert — forventet status
for et nettsted som ble publisert samme dag Search Console ble satt
opp, ikke et tegn på en SEO-feil. Uavhengig teknisk re-verifisering
av produksjon (robots.txt, sitemap-innhold, canonical, hreflang,
noindex, HTTPS/TLS, HTTP→HTTPS-redirect) fant ingen nye funn — samme
grønne status som ved deploy i Runde 18. `www.kvernhaugbrygghus.no`
serverer fortsatt identisk innhold direkte i stedet for å
301-redirecte til non-www (uendret SHOULD/backlog-status, ikke en
blocker — canonical peker uansett korrekt til non-www). Videre
indekseringsstatus avhenger nå av Googles egen crawl-takt.

## Runde 18 — Første produksjonsdeploy + "Uten navn"-hotfix (2026-08-14)

Første offentlige produksjonsdeploy av web-versjonen, til
`https://kvernhaugbrygghus.no` (Domeneshop, `/www` som document root).
Full pre-deploy-verifisering (generator-sync, 899 Python-tester,
manuell pre-deploy-regresjon) grønn før push av commit `ef1a2c3` til
`origin/master` og manuell FTP-opplasting av `web/`-innholdet (uten
`README.md`/`CHANGELOG.md`, som er utviklerdokumentasjon). Full
produksjons-smoke rett etter deploy: alle 18 sider (NO/EN), rå SEO
(canonical/hreflang/description), sitemap.xml (18 URL-er), robots.txt,
HTTP→HTTPS-redirect, TLS, 0 tredjeparts runtime-requests — alt grønt.

**Hotfix (samme dag, commit `56c924e`):** en ekte iPhone Safari-bruker
oppdaget at EN-builderens "Beer name"-felt viste den norske interne
sentinelverdien "Uten navn" i stedet for en lokalisert engelsk
placeholder/default. Root cause: `_gjenopprettOppskrift()` i `app.js`
satte input-feltets `.value` direkte fra `oppskrift.navn` uten
displaylag-oversettelse — i motsetning til recipe card-visningen
(`identitet-navn`), som allerede gjorde dette riktig. Samme
lekkasjemønster (`navn || fallback`, som aldri trigger siden "Uten
navn" er en ikke-tom streng) ble funnet og rettet fire steder til:
lagre-status-meldingen, Utskrift-sidens info-linje og nedtrekksvelger,
print-dokumentenes `<h1>`, og Mine oppskrifter-listens tittel. Ny delt
display-helper `visningsnavn()` i `i18n.js` brukes for all READ-ONLY
visning (viser "Untitled" på EN, "Uten navn" på NO, brukerskrevne
navn uendret). Det REDIGERBARE navnefeltet fikk en annen løsning —
vises tomt (ikke oversatt tekst) når intern navn er sentinelen, slik
at den allerede lokaliserte placeholderen ("Name of the beer") vises
naturlig, uten risiko for at "Untitled" ved et uhell lagres som et
faktisk brukernavn. Intern `recipe.navn`-kontrakt, `.kbhrecipe`-format
og `samleOppskrift()`/`_gjenopprettOppskrift()`-signaturen er
uendret — kun visningslaget endret.

**Deploy mismatch underveis:** det første FTP-opplastingsforsøket av
disse 5 JS-filene resulterte i at produksjonen fortsatt serverte den
gamle, pre-hotfix-koden — bekreftet ved direkte byte-diff mot lokal
`HEAD`. Server-headerne (`Last-Modified`) viste at filene faktisk
_var_ nylig overskrevet, som utelukket cache som forklaring — årsaken
var at feil lokal kildemappe (en eldre deploy-/scratch-kopi) ble brukt
i FTP-klienten i stedet for det faktiske repoets `web/js/`. Andre
opplastingsforsøk (fra riktig kildemappe) verifisert byte-identisk mot
lokal `HEAD` for alle 5 filer, og full produksjons-smoke av det
opprinnelige bug-scenarioet (inkl. 1000ms+ stabilitetssjekk over flere
NO↔EN-runder) bekreftet fikset.

## Runde 17 — Kontakt og personvern (2026-08-14)

Offentlig kontakt-e-post (`post@kvernhaugbrygghus.no`, bekreftet opprettet hos Domeneshop) og en minimal, ærlig personvernforklaring før første lansering — ingen cookie-banner, ingen consent-framework, ingen analytics (bekreftet på nytt: ingen `fetch`/`XMLHttpRequest`/`sendBeacon`/tredjeparts script/iframe noe sted i `web/`).

Ny niende side, `web/personvern.html` (NO) / generert `web/en/personvern.html` (EN) — "Kontakt og personvern" / "Contact & Privacy", registrert i generatorens `PAGES`-liste med samme kontrakt som de øvrige åtte sidene (hero/kompaktnav/sidemeny-krom, `data-i18n-tittel-nokkel`, canonical/hreflang, egen meta description). Tre korte seksjoner: Kontakt (mailto-lenke, ren tekst, samme adresse på begge språk), Oppskriftene dine (lokal lagring, ingen konto/sentral database, `.kbhrecipe` for backup/flytting), Personvern (ingen egen analyse/reklame/sporing i denne versjonen; e-postkontakt innebærer naturligvis at adresse+innhold mottas for å kunne svare — ingen bredere/udokumenterbare påstander som "ingen data forlater noensinne enheten").

Ny, delt footer-kontaktlinje (`Kvernhaug Brygghus · post@kvernhaugbrygghus.no · Kontakt og personvern`, `mailto:`-lenke + lenke til `personvern.html`) lagt til på alle 8 eksisterende sider — inkl. de 4 Hjelp-sidene, som tidligere ikke hadde noen `<footer>` i det hele tatt. Ingen ny CSS — gjenbruker eksisterende `footer`/`a`-styling, ingen visuell nyredesign.

13 nye NO/EN-nøkkelpar i `i18n.js` (`meta.personvern.*`, `personvern.*`, `footer.kontaktLenke`) — 611 nøkkelpar totalt, fortsatt NO/EN-symmetrisk. `scripts/generate_web_i18n_pages.py` oppdatert (`PAGES`, docstring-tallet 16→18) — kjørt to ganger, byte-identisk output begge ganger (SHA-256-verifisert). `web/sitemap.xml` nå 18 URL-er (9 sider × NO/EN), `web/robots.txt` uendret (trengte ingen endring).

Testoppdateringer i `tests/test_generate_web_i18n_pages.py`: fjernet hardkodede "8"/"16"-tall fra testnavn/assertions (nå dynamisk mot `len(gen.PAGES)`), slik at antallet aldri kan bli stille feil neste gang en side legges til. Full Python-suite: 899 tester, 0 feil (samme antall som før — ingen nye Python-tester lagt til denne runden, kun eksisterende justert).

**Microfix (manuell kontroll, samme runde):** footer-/panel-teksten "Data lagres kun lokalt i denne nettleseren (localStorage) — ingenting sendes til noen server" var for absolutt — kontakt via e-post innebærer naturligvis serverkommunikasjon, og teksten ga et udokumenterbart løfte om hosting/serverlogger. Endret til "Oppskriftene dine lagres lokalt i denne nettleseren (localStorage)" — samme sannhet (`localStorage`-basert lagring), men uten løftet om at *ingenting* noensinne sendes noe sted. Rettet i `footer.enkel`/`footer.builder` (5 sider), `mineOppskrifter.hjelpetekst` og `meta.mineOppskrifter.beskrivelse` (samme absolutte formulering funnet der under et sitewide-søk), samt `hjelp.idx.lagreOppskrift.hvorfor` (Hjelp-siden, inkl. den rå NO-kildeteksten som hadde driftet fra `TEKSTER.no` siden Runde 16 sin polish av samme nøkkel). NO/EN-nøkkeltall uendret (611 — kun verdier endret, ingen nye nøkler). Sitewide-søk etter frasen (case-insensitivt) bekreftet 0 gjenværende treff etter fiksen, inkl. i regenerert `web/en/`.

Ikke innført: Open Graph/Twitter Cards, JSON-LD, analytics/tracking, cookie-banner, Search Console-verifisering — bevisst utenfor omfanget, som før.

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
