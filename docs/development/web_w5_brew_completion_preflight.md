# Web W5 — Brygg-fullføring: statisk preflight-analyse (issue #118)

*Del av KBDP, forberedelse til #101 Fase 1 / W5 / B04. Se [../../CLAUDE.md](../../CLAUDE.md)
for oversikt over dokumentsystemet.*

**Status: docs-only analyse, ingen implementasjon.** Alt under er lest direkte ut av
repoets nåværende kildekode (`web/js/brew_storage.js`, `web/js/brygg_page.js`,
`web/js/app.js`, `web/bryggelogg.html`, `web/js/i18n.js`) og av `web/CHANGELOG.md`/
`web/README.md` sine egne runde-referater (Runde 25B/25C). Ingen `web/**`-fil er endret
av dette issuet.

---

## 1. Kort oppsummering for Chief

Web sin bryggelogg har **ingen eksplisitt fullførings-tilstandsmaskin**. Et brygg sin
synlige "fase" (`bryggFase()`) utledes utelukkende av hvilke felt som faktisk er fylt
ut, mens `status` (`active`/`done`/`discarded`) er en helt separat, brukerstyrt
markering satt av egne knapper. Historikklisten ("Ferdige brygg") krever at **begge**
er sanne samtidig (`bryggFase(b) === "ferdig" && b.status === "done"`,
`brygg_page.js:403`). Fordi "Avslutt"-knappen som setter `status:"done"` er synlig og
klikkbar allerede fra `fase === "smaking"` — FØR brukeren har avgitt en dom
(`sensing.judgment`) — kan et brygg få `status:"done"` mens `bryggFase()` fortsatt
returnerer `"smaking"`. Et slikt brygg forsvinner **ikke** til historikken; det blir
liggende under "Under arbeid" på ubestemt tid, fortsatt vist med spørsmålet "Ville du
brygget dette igjen?" og en fungerende "Avslutt"-knapp — uten noe synlig tegn på at
brukeren allerede har trykket den. Dette er den mest konkrete, kode-beviste kandidaten
for B04 (§5 under), og trolig kjernen i hva W5 må rette opp.

---

## 2. Nåværende tilstandskart

### 2.1 Datamodellen (`web/js/brew_storage.js`)

Fem lag, etablert i Runde 25B (issue-referanse i changelog, ingen egen issue-lenke i
kildekoden selv):

| Lag | Felt | Kommentar |
|---|---|---|
| 1 identitet/livssyklus | `brewId`, `recipeId` (svak referanse), `parentBrewId`, `originBrewId`, `status`, `createdAt`, `brewedAt` | `status` er **metadata**, eksplisitt dokumentert som "ikke en tilstandsmaskin" (`brew_storage.js:25`, `:103-106`) |
| 2 snapshot | `snapshot.recipe`, `snapshot.predicted`, ingrediens-/utstyrsdata, proveniens | Frosset ved opprettelse, aldri skrevet om (§2.2) |
| 3 actuals | `actuals.og`, `actuals.fg`, `actuals.volumeL`, `actuals.notes` | Alt valgfritt, sparsomt (`BREW_ACTUALS_KJENTE_FELT`, `brew_storage.js:72`) |
| 4 sensing | `sensing.judgment` (`yes`/`maybe`/`no`), `sensing.flavorProfile`, `sensing.notes` | `judgment` er feltet `bryggFase()` sjekker for "ferdig" |
| 5 learning | `learning.nextTime`, `learning.whatWorked`, `learning.whatChanged` | "Neste gang"-sløyfen, §2.6 |

`status` har nøyaktig tre verdier, fritt omsettelige i alle retninger:
`BREW_STATUSER = ["active", "done", "discarded"]` (`brew_storage.js:107`).

Lagring: `localStorage["kvernhaug_web_brygg"]`
(`BREW_NOKKEL = "kvernhaug_web_brygg"`, `brew_storage.js:27`), envelope
`{format:"kbh-brews", version:1, items:[...]}`. Aktiv oppskriftskladd (separat fra
brygg) ligger i `localStorage["kvernhaug_web_aktiv_kladd"]`
(`AKTIV_KLADD_NOKKEL`, `app.js:27`) — de to nøklene er uavhengige, brygg-oppretting
leser kladden men skriver aldri til den.

### 2.2 Frosset snapshot

`opprettBrygg({snapshot, recipeId, parentBrewId})` (`brew_storage.js:466-484`) er
eneste sted et `snapshot` settes; `oppdaterBrygg()` (`brew_storage.js:490-515`)
kopierer eksplisitt `snapshot: forrige.snapshot` inn uendret — snapshotet kan aldri
endres etter opprettelse. `snapshot` inneholder hele oppskrifts-payloaden, de FULLE
masterdata-oppføringene for refererte ingredienser, aktiv utstyrsprofil, og alle
predikerte verdier (OG/FG/ABV/IBU/EBC/BU:GU, smaksprofil-vektor, stilnavn+score) pluss
proveniens (motorversjon `KBH_ENGINE_VERSION`, `brew_storage.js:101`,
`recipeSchemaVersion`, bibliotekstørrelser, tidspunkt) — se README.md §"Brygghistorikk:
.kbhbrew" (linje 242–264) for det fulle kontraktreferatet. Alt som *kan* gjenskapes
(avvik plan/faktisk, faktisk ABV/effektivitet/utgjæring) beregnes ved visning og lagres
ALDRI — `faktiskAbv()`, `planVsFaktisk()`, `faktiskEffektivitet()`, `faktiskUtgjaering()`
(`brew_storage.js:530-582`).

`recipeId` er bevisst en SVAK referanse: sletter eller omdøper brukeren oppskriften,
forblir brygget fullstendig lesbart fordi snapshotet er autoritativt
(`brew_storage.js:623-643`, README.md linje 262).

Brukervendt bekreftelse av nøyaktig denne semantikken finnes allerede i i18n
(`builder.brygg.hjelpetekst`, `i18n.js:466`/`:2209`): *"Når du starter et brygg,
fryser KBH oppskriften slik den er nå — så historikken din endrer seg aldri selv om
oppskriften gjør det."*

### 2.3 Fase-utledning — `bryggFase()`

```js
// brew_storage.js:611-619
function bryggFase(brew) {
  if (!brew) return null;
  if (brew.status === "discarded") return "forkastet";
  const a = brew.actuals || {};
  if (!isFinite(a.og)) return "bryggedag";
  if (!isFinite(a.fg)) return "gjaering";
  if (!brew.sensing || !brew.sensing.judgment) return "smaking";
  return "ferdig";
}
```

Fem mulige verdier: `bryggedag` → `gjaering` → `smaking` → `ferdig`, eller `forkastet`
(sjekkes først, og overstyrer alt annet — et forkastet brygg med fullt utfylte
`actuals`/`sensing` viser likevel `"forkastet"`). Dette er en **utledet, ikke-lagret**
verdi — kalt på nytt ved hver rendering, aldri persistert.

### 2.4 UI — "Ferdig"-handlingen og listeplassering (`web/js/brygg_page.js`)

- **Eksplisitt fullførings-knapp**: `"Avslutt"` (i18n `brygg.avsluttKnapp`), synlig og
  aktiv for **både** `fase === "smaking"` **og** `fase === "ferdig"`
  (`brygg_page.js:198-278`, knapp bundet på linje 266-278). Klikk kaller
  `oppdaterBrygg(brew.brewId, {status:"done", learning:{...}})` — **uten noen sjekk på
  om `sensing.judgment` faktisk er satt**.
- **Dom-knappene** (`yes`/`maybe`/`no`, `.brygg-dom-knapp`, linje 203-212) setter
  `sensing.judgment` uavhengig av `status` — de endrer aldri `status` selv.
- **"Under arbeid"-liste** (`#brygg-aktive-liste`, `bryggelogg.html` linje 75-80,
  i18n `brygg.aktiveTittel` = "Under arbeid"): `aktive = alle.filter(b =>
  !ferdige.includes(b))` (`brygg_page.js:404`) — dvs. **alt** som ikke er i
  `ferdige`-lista, inkludert forkastede brygg (fase `forkastet` rendres også her, med
  "Gjenoppta"-knapp, `brygg_page.js:281-304`).
- **"Ferdige brygg"-liste** (`#brygg-ferdige-liste`, `bryggelogg.html` linje 82-87,
  i18n `brygg.ferdigeTittel`): `ferdige = alle.filter(b => bryggFase(b) === "ferdig"
  && b.status === "done")` (`brygg_page.js:403`) — **AND-betingelse** på to
  uavhengige signaler.
- Kortmalen (`#brygg-kort-mal`, brukt for "Under arbeid") og radmalen
  (`#brygg-ferdig-mal`, brukt for "Ferdige brygg") er strukturelt forskjellige —
  historikkraden (`_byggFerdigRad()`, linje 322-360) viser faktisk OG/FG/ABV,
  "Neste gang"-tekst og dom-merke; det aktive kortet (`_byggKort()`, linje 137-320)
  viser fasens spørsmål og innputfelt.

### 2.5 Målinger/state som overlever fullføring

Alt i lag 3-5 (actuals/sensing/learning) er permanent og uavhengig av `status` —
`oppdaterBrygg()` skriver dem uendret om brygget senere gjenåpnes
(`status: "active"` via "Gjenåpne"-knappen, `brygg_page.js:345-351`, eller
"Gjenoppta" for forkastede, linje 298-303). Det finnes ingen "lås" som hindrer videre
redigering av et `status:"done"`-brygg via UI-et — men i praksis vises et `done`-brygg
kun i den enkle historikkraden, som ikke har inputfelt, så videre redigering krever
først "Gjenåpne".

### 2.6 "Neste gang"-sløyfen

`sisteErfaringForOppskrift(recipeId)` (`brew_storage.js:588-601`) henter kun
`learning.nextTime`-teksten fra det nyeste brygget (sortert på `createdAt`) med samme
`recipeId` OG et faktisk utfylt `nextTime` — **uavhengig av `status` eller
`bryggFase()`**: et brygg som fortsatt er `active`/`smaking`, men har fått et
"Neste gang"-notat lagret via "Lagre notat"-knappen (linje 249-264, som IKKE krever
`status:"done"`), kan altså allerede vises som "Erfaring fra forrige gang" i byggeren
før brygget selv noensinne er markert ferdig. Vises i byggeren via
`visForrigeErfaring()` (`app.js:1698-1711`) FØR "Start brygging" klikkes.
`bryggForOppskrift(recipeId)` (`brew_storage.js:456-459`) — som kunne gitt full
historikk for en oppskrift — er definert men **ikke kalt fra noe sted i UI-et**
(kun brukt internt i egen fil); eneste eksterne bruker i hele `web/js/` er
`custom_ingredient_id.js:100` sin `alleBrygg()`-basert kollisjonssjekk, ikke
`bryggForOppskrift()` selv.

### 2.7 Start-fullføring (motstykket til W5, for kontekst)

`startBrygging()` (`app.js:1676-1693`) fryser oppskriften "som den er nå"
(`samleOppskrift()` → `beregnOppskrift()` → `byggBrewSnapshot()`) og kaller
`opprettBrygg({snapshot, recipeId: _aktivRecipeId})` — **ingen sjekk** på om et annet
`active`-brygg allerede finnes for samme `recipeId`. To klikk på "Start brygging" for
samme oppskrift (uten mellomliggende navigasjon) oppretter to uavhengige `active`-brygg,
begge synlige under "Under arbeid". Ingen bekreftelsesdialog vises.

### 2.8 Save/autosave/localStorage

To uavhengige nøkler er relevante:

| Nøkkel | Eier | Rolle |
|---|---|---|
| `kvernhaug_web_brygg` | `brew_storage.js` (`BREW_NOKKEL`) | All brygghistorikk (`{format:"kbh-brews", version:1, items:[]}`) |
| `kvernhaug_web_aktiv_kladd` | `app.js` (`AKTIV_KLADD_NOKKEL`) | Den aktive, ulagrede oppskriftskladden i byggeren |

`opprettBrygg()`/`oppdaterBrygg()`/`slettBrygg()` skriver kun til `BREW_NOKKEL`, aldri
til kladdenøkkelen — å starte/fullføre et brygg endrer aldri den aktive kladden i
byggeren. Skriving sjekkes med en synkron round-trip
(`localStorage.setItem` → `localStorage.getItem` sammenlignet mot det serialiserte,
`brew_storage.js:439-444`) og et eksplisitt `korrupt`-flagg
(`bryggStateErKorrupt()`, `:421`) forhindrer at uleselig rådata overskrives stille
(issue #74-arven, se kommentar `brygg_page.js:364-372`).

`.kbhbrew`-import/eksport-**datalaget** finnes ferdig
(`byggKbhBrewInnhold()`/`parseKbhBrewInnhold()`/`importerBrygg()`,
`brew_storage.js:677-779`, identitetspolicy `brewId` vs. `originBrewId` for
duplikatgjenkjenning), men **ingen side eller knapp i `web/**` kaller disse
funksjonene** — bekreftet ved `grep` på tvers av alle `.js`/`.html`-filer utenfor
`brew_storage.js` selv. Import/eksport av brygghistorikk er altså et W5-relevant hull,
ikke en implementert funksjon som kan regresjonstestes.

### 2.9 NO/EN i18n-nøkler (namespace `brygg.*`, `builder.brygg.*`)

Bekreftet symmetriske NO/EN-par i `web/js/i18n.js` (samme mønster som resten av appen,
verifisert av `tests/test_generate_web_i18n_pages.py`):

- Fase-etiketter: `brygg.fase.{bryggedag,gjaering,smaking,ferdig,forkastet}`
  (`i18n.js:477-481` NO, `:2220-2224` EN) — merk at NO `"ferdig"` ("Ferdig") og
  status-verdien `"done"` er to helt forskjellige symbolske navn (fase-strengen er
  norsk UI-tekst, status-strengen er en intern engelsk konstant) — ingen tekstlig
  kobling som kunne avslørt sammenblandingen ved lesing av koden alene.
- Listetitler: `brygg.aktiveTittel` ("Under arbeid"/"In progress"),
  `brygg.ferdigeTittel` ("Ferdige brygg"/"Finished brews").
- Handlinger: `brygg.avsluttKnapp`, `brygg.forkastKnapp`, `brygg.gjenopptaKnapp`,
  `brygg.gjenapneKnapp`, `brygg.lagreFg`, `brygg.settTilGjaering`.
- Spørsmål per fase: `brygg.sporsmalBryggedag/Gjaering/Smaking/Forkastet`.
- Builder-side: `builder.brygg.startKnapp`, `builder.brygg.tomOppskrift`,
  `builder.brygg.startetStatus`, `builder.brygg.erfaringTittel`.

### 2.10 Learner/Master (Bryggelærling/Bryggmester)

**Ingen branching funnet.** `bryggelogg.html`/`brygg_page.js` laster verken
`preferences.js`s modus-lesing i noen egen gren, og det finnes ingen
`hentVisningsmodus()`/`modus ===`-sjekk noe sted i `brygg_page.js`. Den eneste
tilsynelatende koblingen er kosmetisk: dom-knappene (`yes`/`maybe`/`no`) gjenbruker
CSS-klassene `.modus-bryter`/`.modus-knapp` fra Bryggelærling/Bryggmester-bryteren
(`bryggelogg.html` linje 133-137) — ren visuell gjenbruk, ingen funksjonell kobling.
Bryggeloggen oppfører seg identisk uansett modus.

---

## 3. Filer/funksjoner involvert (samlet)

| Fil | Rolle |
|---|---|
| `web/js/brew_storage.js` | DOM-fri datamodell: CRUD, `bryggFase()`, avledede verdier, `.kbhbrew`-format (ubrukt UI-messig) |
| `web/js/brygg_page.js` | Bryggelogg-siden: kortrendering, listefiltrering (`visLogg()`), alle handlingsknapper |
| `web/bryggelogg.html` | Statisk struktur, to `<template>`-er, i18n-dekorerte overskrifter |
| `web/js/app.js` | `startBrygging()`, `visForrigeErfaring()`, `hentAktivKladd()` — byggerens side av sløyfen |
| `web/js/i18n.js` | `brygg.*`/`builder.brygg.*`-nøkler, NO+EN |
| `web/js/custom_ingredient_id.js` | Eneste eksterne bruker av `alleBrygg()` utenfor `brygg_page.js`/`brew_storage.js` selv (kollisjonssjekk for custom-id-mynting) |
| `web/en/bryggelogg.html` | Generert EN-speiling (ikke håndredigert, se `.claude/rules/web.md`) |

---

## 4. Lagrede felt/statusverdier (samlet)

`status`: `active` / `done` / `discarded` (fritt omsettelig, ikke en tilstandsmaskin).
`bryggFase()` (utledet, ikke lagret): `bryggedag` / `gjaering` / `smaking` / `ferdig` /
`forkastet`. Disse to er **uavhengige akser** — det finnes 3 × 5 = 15 teoretiske
kombinasjoner, hvorav flere er nåbare via UI-et i dag (se §5).

---

## 5. Hvor motstridende tilstander kan sameksistere i dag (B04-kandidater)

1. **Hovedfunn — "done" uten dom** (høy tillit, direkte kode-bevist): "Avslutt"-knappen
   er aktiv fra `fase === "smaking"` (`brygg_page.js:198,266-278`), altså FØR
   `sensing.judgment` er satt. Klikk setter `status:"done"` uten å sjekke `judgment`.
   `bryggFase()` forblir `"smaking"` til `judgment` faktisk settes (linje 617). Følgelig:
   - `ferdige`-filteret (linje 403, AND-betingelse) ekskluderer brygget permanent —
     det vises aldri i "Ferdige brygg" før brukeren (kanskje mye senere, kanskje
     aldri) også trykker en dom-knapp.
   - Brygget blir liggende under "Under arbeid" og rendres på nytt med
     `fase:"smaking"` — fase-badgen sier "Klar for smaking"/"Ready to taste"
     (`brygg.fase.smaking`), spørsmålet "Ville du brygget dette igjen?" vises fortsatt,
     og "Avslutt"-knappen er fortsatt der og klikkbar igjen (idempotent, men villedende).
   - Ingen UI-indikasjon noe sted forteller brukeren at de allerede har trykket
     "Avslutt" — `status` leses aldri i `_byggKort()` for `fase !== "forkastet"`.
2. **Sekundært funn — flere samtidige `active`-brygg per oppskrift**: `startBrygging()`
   (`app.js:1676-1693`) og `opprettBrygg()` (`brew_storage.js:466-484`) har ingen
   sjekk mot eksisterende `active`-brygg for samme `recipeId`. Er dette tilsiktet
   (bruker brygger samme oppskrift flere ganger samtidig, f.eks. parallelle kar) eller
   en regresjonsrisiko UI-et bør varsle om, er et åpent spørsmål (§7).
3. **Lavere tillit — "Neste gang" synlig før fullføring**: `sisteErfaringForOppskrift()`
   (§2.6) leser kun `learning.nextTime`, uavhengig av `status`/fase. Et notat lagret
   midt i et fortsatt `active` brygg (via "Lagre notat", som ikke krever "Avslutt")
   vises allerede som "forrige gangs erfaring" i byggeren. Sannsynligvis tilsiktet
   (dokumentert som bevisst lettvekts, README linje 260-264: "Neste gang… vist i
   byggeren FØR neste brygg startes"), men det betyr at "Neste gang" kan referere til
   et brygg brukeren selv ikke opplever som "ferdig" ennå — verdt å bekrefte eksplisitt
   i W5-kontrakten, ikke bare anta.
4. **Ingen tilsvarende risiko funnet** for forkastet-status: `forkastet` sjekkes først
   i `bryggFase()` og overstyrer alt, så et forkastet brygg kan ikke samtidig telle som
   `ferdig` i UI-et. Renders alltid i "Under arbeid" med "Gjenoppta"-knapp
   (`status:"active"`), aldri i "Ferdige brygg".
5. **Latent, samme rotårsak, via import-stien**: `importerBrygg(filBrew)`
   (`brew_storage.js:751-779`) setter `status: BREW_STATUSER.includes(filBrew.status)
   ? filBrew.status : "done"` (linje 774) — en fil uten gyldig `status`-felt (eller et
   håndredigert/eldre `.kbhbrew` uten feltet) importeres altså med `status:"done"` som
   fallback, uavhengig av om `actuals`/`sensing` faktisk er utfylt i filen. Er
   `og`/`fg`/`judgment` fraværende i den importerte filen, vil `bryggFase()` returnere
   `"bryggedag"`/`"gjaering"`/`"smaking"` — samme divergens som funn 1, denne gangen
   introdusert via import fremfor normal UI-flyt. **Ikke observerbar i dag** siden
   ingen side kaller `importerBrygg()` (§2.8) — men enhver fremtidig W5- eller
   senere-runde som kobler på import-UI-et bør løse funn 1 og dette samtidig, ikke
   hver for seg.

**Om B04 spesifikt**: det finnes ingen egen, tidligere dokumentert "B04"-referanse
noe sted i repoet (`docs/`, `web/CHANGELOG.md`, `web/README.md`) — søkt eksplisitt og
ikke funnet. B04 er trolig en ekstern audit-referanse (fra #101 sitt Fase 1-arbeid)
uten et lokalt spor. Funn 1 over er den sterkeste, direkte kode-beviste kandidaten for
hva en slik revisjon ville ha observert (et brygg som virker "avsluttet" fra brukerens
handling, men aldri når historikken), men dette dokumentet kan ikke bekrefte at det
faktisk ER B04 uten å se selve audit-teksten.

---

## 6. Foreslått, minste sammenhengende produktkontrakt for W5

*Dette er et forslag til Chief for scoping — IKKE en vedtatt kontrakt, og IKKE
implementert av dette issuet.*

**Kjerneprinsipp å bevare**: `status` skal fortsatt være fri, ikke-håndhevet metadata
(README/brew_storage.js sin eksplisitte, gjentatte kontrakt) — en tilstandsmaskin med
harde overganger ville motsi hele Runde 25B/25C-designfilosofien ("et ufullstendig
brygg er gyldig", "ingen rekkefølge håndheves").

Minste endring som lukker funn 1 uten å bryte det prinsippet:

- **Alternativ A (anbefalt retning)**: la `ferdige`-filteret i `visLogg()`
  (`brygg_page.js:403`) bruke KUN `b.status === "done"` — dropp
  `bryggFase(b) === "ferdig"`-betingelsen. Et `done`-brygg havner alltid i historikken
  umiddelbart, uansett om dom er avgitt. `_byggFerdigRad()` må da håndtere manglende
  `sensing.judgment` pent (i dag skjuler den `.brygg-dom-merke` når judgment mangler,
  linje 338-344 — ser ut til allerede å tåle dette).
- **Alternativ B**: fjern "Avslutt"-knappen fra `fase === "smaking"`-grenen (kun vis
  den i `fase === "ferdig"`-grenen, dvs. etter avgitt dom) — tvinger brukeren gjennom
  dom FØR avslutning er mulig. Enklere logisk kontrakt, men fjerner en eksisterende,
  kanskje bevisst, "avslutt uten å smake ennå"-mulighet (brukeren kan ha gode grunner
  til å avslutte uten å ville vurdere smak — f.eks. et batch de heller aldri smakte).
- **Alternativ C**: behold dagens AND-betingelse, men gi et synlig, permanent varsel
  på et `status:"done"`-brygg som fortsatt mangler dom ("Du markerte dette som
  avsluttet — vil du også si noe om resultatet?") i stedet for å late som ingenting
  har skjedd.

Uansett alternativ bør W5 eksplisitt bestemme: (a) skal "Neste gang" fortsatt være
synlig for et ennå-ikke-`done`-brygg (§5 punkt 3), og (b) skal `startBrygging()` varsle
ved eksisterende `active`-brygg for samme oppskrift (§5 punkt 2) — begge er reelle,
kode-bekreftede åpne spørsmål, ikke antagelser.

---

## 7. Implementasjonsberøringspunkter (for en fremtidig W5-runde, IKKE utført her)

- `web/js/brygg_page.js`: `visLogg()` (filterlogikk, linje 403-404), `_byggKort()`
  (knappe-/betingelseslogikk for `fase === "smaking"`-grenen, linje 184-197 og
  266-278), `_byggFerdigRad()` (manglende-dom-visning, linje 322-360).
- `web/js/brew_storage.js`: `bryggFase()` selv trolig **uendret** (den beskriver
  faktisk datainnhold korrekt) — endringen hører hjemme i filterlogikken i
  `brygg_page.js`, ikke i modellaget, med mindre Chief velger Alternativ B (som ville
  kreve UI-endring, ikke modell-endring, uansett).
- `web/js/i18n.js`: eventuelle nye nøkler for et "avsluttet uten dom"-varsel
  (Alternativ C) — NO+EN parvis, aldri maskinoversatt (`.claude/rules/web.md`).
- `web/js/app.js`: `startBrygging()` (linje 1676-1693) hvis §5 punkt 2 tas med i scope.
- `tests/test_generate_web_i18n_pages.py`: automatisk dekket ved enhver ny
  `data-i18n-*`-nøkkel, ingen manuell handling utover selve i18n-tilføyelsen.
- **Ingen** Python/`app.py`/`modules/**`-berøring — dette er isolert til `web/**`.

---

## 8. Regresjonsrisiko

- **W3 save-state truth** (issue #106, `app.js` sin `lagreTilstandForOppskrift()`):
  ingen kobling funnet mellom brygg-fullføring og oppskriftens
  kladd/lagret/endret-badge — `startBrygging()`/`oppdaterBrygg()` skriver aldri til
  `AKTIV_KLADD_NOKKEL` eller kaller noen lagre-state-funksjon. Lav risiko, men bør
  reverifiseres manuelt (Playwright) etter faktisk W5-implementasjon, ikke kun antas
  trygt fra statisk lesing.
- **`.kbhbrew` import/eksport**: siden ingen UI-kobling finnes i dag (§2.8), er det
  ingen eksisterende bruker-synlig funksjonalitet W5 kan regressere her — men enhver
  W5-endring i `oppdaterBrygg()`s kontrakt (f.eks. nye påkrevde felt) må fortsatt
  respektere det ferdige, testede datalaget i `brew_storage.js` hvis/når import/eksport
  kobles til senere.
- **"Neste gang"-sløyfen**: en endring i §6 Alternativ A/B påvirker IKKE
  `sisteErfaringForOppskrift()` sin egen logikk (den er allerede uavhengig av
  `status`/fase, §2.6) — men bør reverifiseres at forventet oppførsel (§5 punkt 3)
  fortsatt stemmer med den valgte kontrakten.
- **Ingen kjente touchpoints** mot `utskrift.html`/print-dokumentene: `README.md`
  (linje 369) bekrefter at det trykte "Bryggelogg"-skjemaet er et rent, ikke-digitalt
  papirskjema uten kobling til `brew_storage.js` — bekreftet ved fravær av
  `brew_storage.js`/`brygg`-referanser i `utskrift_page.js` (kun `grep`-verifisert
  fravær av `alleBrygg`/`bryggFase`/`oppdaterBrygg` i den filen, ikke lest i sin
  helhet i denne runden — se §9 kjente ubesvarte spørsmål).

---

## 9. Foreslått akseptansematrise for W5 (ekte nettleser, Chief skal kreve dette)

| # | Scenario | Forventet utfall |
|---|---|---|
| A1 | Klikk "Avslutt" fra `fase:"smaking"` UTEN å avgi dom først | Brygget skal (per valgt kontrakt §6) enten havne i "Ferdige brygg" umiddelbart, eller UI-et skal tydelig vise at det er markert avsluttet mens dom mangler — aldri stille bli værende identisk med en uavsluttet `smaking`-tilstand |
| A2 | Avgi dom, deretter klikk "Avslutt" (normal rekkefølge) | Havner i "Ferdige brygg" umiddelbart, som i dag |
| A3 | "Gjenåpne" et ferdig brygg, deretter "Avslutt" på nytt uten endringer | Går tilbake til historikken uendret, ingen dobbel oppføring |
| A4 | Forkast et brygg som allerede har `status:"done"` (hvis UI-et tillater dette — verifiser om det er mulig i dag) | Skal vises som `forkastet`, ikke dukke opp i "Ferdige brygg" (bekreft `bryggFase()`s forkastet-først-presedens holder) |
| A5 | Klikk "Start brygging" to ganger på rad for samme oppskrift, uten navigasjon mellom | Bekreft faktisk observert oppførsel i nettleser (to uavhengige `active`-brygg, ingen advarsel) — avgjør om dette er en bug eller tilsiktet, jf. §5 punkt 2 |
| A6 | "Neste gang"-notat lagret på et fortsatt `active` brygg, deretter start et nytt brygg av samme oppskrift | Bekreft notatet faktisk vises i byggeren FØR ny "Start brygging" (README-kontrakten), og avklar om det er ønsket når kilde-brygget ikke er `done` |
| A7 | NO/EN-parallell for alle badge-/knappetekster involvert i en eventuell W5-endring | 0 rå i18n-nøkler, 0 "undefined", identisk oppførsel begge språk |
| A8 | 0 konsollfeil/nettverksfeil under hele scenariosettet over, i både Chromium og Firefox | Som etablert baseline for øvrige web-runder (`web-full-regression`-skillet) |
| A9 *(kun relevant hvis W5 også kobler på import-UI, §5 funn 5)* | Importer en `.kbhbrew`-fil uten `status`-felt og uten `actuals.og`/`fg` | Bekreft at import-fallbacken (`status:"done"` uten fullført data, `brew_storage.js:774`) enten er løst sammen med funn 1, eller eksplisitt utelatt fra scope med begrunnelse |

---

## 10. Kjente ubesvarte spørsmål (kan ikke løses fra repo-bevis alene)

1. **B04 sin faktiske ordlyd** — dette dokumentet kan ikke bekrefte at §5 punkt 1
   faktisk ER B04 uten å se selve audit-funnet fra #101 Fase 1.
2. **Er Alternativ A/B/C (§6) den retningen Chief ønsker**, eller finnes det en fjerde
   løsning (f.eks. en eksplisitt bekreftelsesdialog ved "Avslutt uten dom")? Ikke en
   kodebevist konklusjon — et produktvalg.
3. **`utskrift_page.js` er ikke lest i sin helhet** i denne runden (kun grep-verifisert
   fravær av direkte brygg-referanser) — dersom W5 utvider bryggeloggens datamodell,
   bør denne filen leses eksplisitt før implementasjon, ikke kun antas urørt.
4. **Er §5 punkt 2 (flere samtidige `active`-brygg) i det hele tatt i scope for W5**,
   eller et helt separat, senere issue? Issuet som spesifiserte dette preflight-arbeidet
   nevner ikke dette funnet eksplisitt — det dukket opp underveis i den statiske
   analysen og rapporteres her per "si fra i stedet for å gjette"-prinsippet, ikke fordi
   det nødvendigvis hører til B04.
5. **Faktisk `bryggForOppskrift()`-bruk** (§2.6) — funksjonen er ferdig implementert
   men ubrukt fra UI. Er den tiltenkt en fremtidig runde (f.eks. "vis alle tidligere
   brygg av denne oppskriften" i byggeren), eller dødt gjenstående kode fra en tidligere
   plan? Ikke avgjørbart fra koden alene.
