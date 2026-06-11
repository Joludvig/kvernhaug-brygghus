# Kvernhaug Brygghus — Sesjonslogg 2026-06-11

Dato: 2026-06-11  
Commits: 8 (9c3d665 → 74cee50)  
Filer endret: `data/master_malt.json`, `data/master_humle_v2.json`, `data/master_gjaer_v2.json`, `modules/style_engine.py`  
Sesjonstid: To kontekstvinduer (context compaction mellom Flavor Engine og Style Engine-arbeid)

---

## 1. Executive Summary

Sesjonen fullførte tre separate arbeidspakker som hadde vært planlagt siden databasearkitektur-fasen:

**Flavor Engine Calibration** (Phase 1 + Phase 2): Alle 18 engine-akser er nå bekreftet i bruk. `Fruktig`-aksen ble omdøpt til `Fruktighet` i databasen for å matche engine-koden. 19 gjærstammer fikk `kategorier`-profiler (var 0 bidrag til smakshjulet). Dødtaster (`Kremete`, `Krydret`) håndtert.

**Database Calibration Phase 2**: Seks ingrediens-profiler kalibrert mot produsent- og stildata. To metadata-felt (produsent) rettet for generiske malt-entries. Tre display_name-kollisjoner løst.

**Style Engine Fix Phase 1 + 2**: Tre av fire identifiserte feil i stilmatchingen er rettet. Sommerglød matches nå korrekt til Tysk Pilsner (100%) i stedet for Belgisk Witbier. Eldsvenn viser nå "Kreativt Brygg" (maks 30%) i stedet for English Dark Mild 63%. Varðeldr er nedskalert fra 97% ESB til 56% ESB.

---

## 2. Endringer i Flavor Engine

### Kontekst

Flavor Engine (`modules/flavor_engine.py`) var ikke endret — koden var korrekt. Problemet var at databasen brukte aksenavn som ikke samsvarte med engine-koden, og at mange ingredienser manglet `kategorier`-profiler fullstendig.

### Commit 9c3d665 — Flavor Engine Calibration Phase 1

**Fil:** `data/master_malt.json`  
**Endring:** 9 malt-entries hadde `"Fruktig"` som aksekode. Engine bruker `"Fruktighet"`. Alle 9 ble migrert.

Berørte malter:
- carapils, crystal_maple_carapils, caramunich_1, caramunich_2, caramunich_3, crystal_dark, special_b, melanoidin, amber_malt

**Fil:** `data/master_gjaer_v2.json`  
**Endring:** 19 gjærstammer fikk `kategorier`-profiler. Disse bidro tidligere med 0 til smakshjulet, noe som svekket stilmatchingen for alle recipes som brukte disse gjærene.

| Gjær | Profil |
|---|---|
| SafAle US-05 | Fruktighet: 0.5 |
| SafAle S-04 | Fruktighet: 2.0, Brød: 1.0 |
| SafLager W-34/70 | Fruktighet: 1.0, Maltfylde: 1.0 |
| Wyeast 1318 London Ale III | Fruktighet: 4.0, Steinfrukt: 2.0, Tropisk: 1.0, Maltfylde: 1.0 |
| WLP013 London Ale | Fruktighet: 2.0, Jordlig: 1.0 |
| WLP066 London Fog Ale | Fruktighet: 4.0, Steinfrukt: 2.0, Tropisk: 1.0 |
| SafAle WB-06 | Fruktighet: 5.0, Krydder: 4.0 |
| LalBrew Voss Kveik | Sitrus: 5.0, Tropisk: 3.0, Fruktighet: 4.0, Honning: 2.0 |
| K.1 Voss | Sitrus: 5.0, Tropisk: 3.0, Fruktighet: 4.0, Honning: 2.0 |
| K.14 Eitrheim | (kveik-profil) |
| Voss Kveik M12 | Sitrus: 5.0, Tropisk: 3.0, Fruktighet: 4.0, Honning: 2.0 |
| WLP530 Abbey Ale | Fruktighet: 4.0, Krydder: 4.0, Vinøs: 2.0 |
| LalBrew Abbaye | Fruktighet: 4.0, Krydder: 4.0, Vinøs: 2.0 |
| WLP565 Saison | Krydder: 5.0, Fruktighet: 4.0, Sitrus: 2.0 |
| WLP566 Saison II | Krydder: 5.0, Fruktighet: 4.0, Sitrus: 2.0 |
| French Saison M29 | Krydder: 4.0, Fruktighet: 3.0, Sitrus: 2.0 |
| LalBrew Farmhouse | Krydder: 4.0, Fruktighet: 3.0, Sitrus: 2.0 |
| New World Strong M42 | Fruktighet: 1.5, Maltfylde: 1.0 |
| LalBrew Nottingham | Fruktighet: 1.0 |
| Lutra Kveik | Fruktighet: 1.0 |

### Commit e8bd67a — Dead Keys og Manglende Profiler

**Fil:** `data/master_malt.json`  
Flaket Havre: `Kremete` (eksisterer ikke i engine) fjernet. Erstatt med `Maltfylde: 5`.

**Fil:** `data/master_humle_v2.json`  
East Kent Goldings: Manglende `Jordlig: 3` lagt til. EKG har tydelig earthy-karakter som var uten bidrag.

**Fil:** `data/master_gjaer_v2.json`  
New World Strong M42: Profil lagt til (`Fruktighet: 1.5, Maltfylde: 1.0`). Brukes i Varðeldr, Eldsvenn og en tredje recipe — bidro 0 til smakshjulet.

### Commit 378d0e4 — Kremete i oat_malt

**Fil:** `data/master_malt.json`  
Oat Malt: `Kremete` fjernet (samme dead key som flaket_havre). Maltfylde økt fra 3 til 5 for å bevare den opplevde body-bidraget fra havre.

---

## 3. Endringer i Databaser

### Commit a50564d — Ingrediens-kalibrering Phase 2

Seks profiler kalibrert mot produsent-data og stilkunnskap:

**Malt:**

| Malt | Endring | Begrunnelse |
|---|---|---|
| Vienna | Brød 5→4, ny Toast: 2 | Kilning gir lett toast-karakter; 5 er for høyt |
| Chocolate Wheat | ny Nøtter: 2 | Hvetebase gir rundere, mer nøtteaktig roast enn ren chocolate |
| Carafa Special 2 | Toast 3→1, ny Maltfylde: 2 | Avskallet → undertrykt toast-preg; gir body uten bitterhet |

**Humle:**

| Humle | Endring | Begrunnelse |
|---|---|---|
| Saaz | Jordlig 4→5, Krydder 5→4 | Bohemisk karakter er mer earthy (jordlig) enn krydret |

**Gjær:**

| Gjær | Endring | Begrunnelse |
|---|---|---|
| Wyeast 1318 | Tropisk 1.5→1.0, ny Maltfylde: 1.0 | 73% attenuation etterlater maltfylde |
| LalBrew Nottingham | Brød 1.0 fjernet, Fruktighet 1.5→1.0 | Yeast er ikke brød-flavor; er veldig ren |

### Commit 05b7c4f — Display Name Kollisjoner

**Fil:** `data/master_malt.json`  
Tre kollisjoner løst:

- Jaermalt Standard + Extra Pale + Pale Ale: fikk `(Jaermalt)` suffix for å skille fra Weyermann/Fawcett-varianter med like navn
- Caramalt 30: ny `(30 EBC)` suffix for klarhet
- Weyermann Pilsner: utvide aliases fra 2 til 5 for å fange opp vanlige butikk-varianter

### Commit 335dcf4 — Metadata-fix for Generiske Malter

Disse to entries dekker produkter fra flere produsenter (ulike butikker linker til ulike merker):

| Entry | Endring |
|---|---|
| crystal_maple_carapils | `produsent`: "Viking Malt" → "Viking / Weyermann" |
| biscuit | `produsent`: "Brewferm" → "Brewferm / Castle Malting" |

**Beslutning:** Ingen split av entries — begge er funksjonelt ekvivalente produkter. Feltet avspeiler nå faktisk dekning i butikk_match.

---

## 4. Endringer i Style Engine

### Bakgrunn: Style Engine Audit

Tre oppskrifter ga unintuitive resultater:
- **Varðeldr** (OG=1.088, ABV=9.07%): matchet ESB 97% — et øl 3× sterkere enn stilens ABV-range
- **Sommerglød** (saflager W-34/70 + Saaz + pilsnermalt): matchet Belgisk Witbier 72-74% i stedet for Pilsner
- **Eldsvenn** (OG=1.092, ABV=8.80%): matchet English Dark Mild 63% — et 9% øl i en 3.8%-maks-stil

Audit avdekket fire strukturelle problemer:

1. **ABV ble ikke scoret** — variabelen var tilordnet men brukt aldri i scoring-loopen
2. **english_ale-boost ubetinget** — +20 ble gitt til alle English Bitter-stiler uten hensyn til om OG faktisk passet
3. **Ingen lager-signatur** — saflager, noble hops, pilsnermalt utløste ingen boost for Pilsner-stiler
4. **Dark Mild som gravitasjonsbrønn** — minste smakskrav av alle stiler (3 akser, lave verdier) + bred EBC-range (24–100)

### Commit bf5b051 — Style Engine Phase 1

**Fil:** `modules/style_engine.py`

**Tiltak C: Lager-signatur**

Lagt til `_LAGER_YEASTS` (19 stammer):
- Fermentis: saflager_w3470, saflager_s23, saflager_s189, saflager_e30
- Lallemand: lalbrew_diamond_lager, lalbrew_nova_lager
- Mangrove Jack's: bohemian_lager_m84, california_lager_m54, bavarian_lager_m76, versa_lager_m24
- White Labs: wlp_800, wlp_802, wlp_810, wlp_820, wlp_830, wlp_833, wlp_838, wlp_850, wlp_940

`detect_recipe_signatures()` returnerer nå `"lager": True/False`.  
Scoring-loopen: `if sigs["lager"] and stil in _LAGER_BOCK_STYLES: score += 20`

**Tiltak B3: English Ale OG-gate**

Boost gis kun hvis `og <= stil_maks_OG + 0.020`. Lager-straff forblir ubetinget.

```python
if sigs["english_ale"]:
    og_max = bjcp_stiler[stil]["og"][1]
    if og <= og_max + 0.020:
        if stil in _ENGLISH_STYLES_BASE:
            score += 20
        elif stil in _ENGLISH_STYLES_DARK and sigs["dark_malt"]:
            score += 20
    if stil in _LAGER_BOCK_STYLES:
        score -= 20   # uendret, alltid aktiv
```

**Resultat:**

| Recipe | Før | Etter Phase 1 |
|---|---|---|
| Sommerglød | Witbier #1 | Pilsner 100% (#1), Witbier #5 (74%) |
| Varðeldr | ESB 97% | ESB 77% (boost fjernet) |
| Eldsvenn | Dark Mild 63% | Dark Mild 63% (uendret — ingen boost her uansett) |

### Commit 74cee50 — Style Engine Phase 2

**Fil:** `modules/style_engine.py`

**Tiltak A: ABV-scoring (7.5× multiplikator)**

```python
if abv < krav["abv"][0]:
    score -= (krav["abv"][0] - abv) * 7.5
elif abv > krav["abv"][1]:
    score -= (abv - krav["abv"][1]) * 7.5
```

Plasseringen: etter EBC-penalty, før smak_krav — samme mønster som OG/FG/IBU/EBC.

**Multiplikator-valg:** Tre varianter ble simulert (5×, 7.5×, 10×, 15×). 7.5× ble valgt fordi:
- 5× løste ikke Eldsvenn (Dark Mild forble #1)
- 7.5× bringer Eldsvenn under 40%-terskelen → "Kreativt Brygg"
- 10×/15× er unødvendig aggressivt for mellomtilfellet
- Normal ESB (ABV i range): nullpåvirkning ved alle multipliere

**Resultat:**

| Recipe | Etter Phase 1 | Etter Phase 2 |
|---|---|---|
| Varðeldr | ESB 77% | ESB 56% (Belgisk Tripel 38% som #2) |
| Sommerglød | Pilsner 100% | Pilsner 100% (uendret) |
| Eldsvenn | Dark Mild 63% | **"Kreativt Brygg"** — maks 30% (Belgisk Tripel) |

**Validering mot referanser:**

| Recipe | ABV i range? | Påvirkning |
|---|---|---|
| Normal ESB (5.6%) | Ja — ESB (4.6–6.2%) | Null |
| Normal Dark Mild (3.2%) | Ja — Dark Mild (3.0–3.8%) | Null |
| Baltic Porter ref (7.5%) | Ja — Baltic Porter (7.0–9.5%) | Null |

---

## 5. Naming Audit-resultater

### Axis-navn: Fruktig → Fruktighet

Engine-aksen het `"Fruktighet"`. Databasen brukte `"Fruktig"` på 9 malt-entries. Bidraget fra disse maltene til Fruktighet-aksen var 0. Alle migrert til `"Fruktighet"` i commit 9c3d665.

### Dead Keys oppryddet

| Aksekode | Årsak | Handling |
|---|---|---|
| `Kremete` | Eksisterer ikke i flavor_engine.py | Fjernet fra flaket_havre og oat_malt. Erstatt med Maltfylde. |
| `Krydret` | Ser ut som typo for `Krydder` | Finnes kun i bonsak_rugmalt. **Utsatt** (lav prioritet, sjelden brukt malt). |

### Display Name kollisjoner

Tre tilfeller der ulike malt-entries hadde identisk display_name, noe som brøt flavor_engine-oppslaget (som er display_name-nøklet):

| Entry | Problem | Løsning |
|---|---|---|
| jaermalt_standard/extra_pale/pale_ale | Kolliderte med Weyermann-navn | Suffix `(Jaermalt)` |
| caramalt_30 | Uklar EBC-betegnelse | Suffix `(30 EBC)` |
| weyermann_pilsner | For få aliases → savnet butikk-varianter | 5 aliases |

### 18 engine-akser bekreftet i bruk

Alle 18 akser i `generer_smakshjul()` er nå representert i minst én ingrediens i databasen:
`Maltfylde, Brød, Toast, Karamell, Honning, Nøtter, Sjokolade, Kaffe, Røyk, Bitterhet, Furunøl, Jordlig, Krydder, Sitrus, Tropisk, Fruktighet, Steinfrukt, Vinøs`

---

## 6. Gjenstående TODO

### Lav prioritet — bevisst utsatt

| Element | Begrunnelse for utsettelse |
|---|---|
| `Krydret` dead key i bonsak_rugmalt | Sjelden brukt malt, ingen recipes berørt |
| `Syrlig`/`Frisk` i acidulated malt | Ingen Syrlig/Frisk-akse i engine; utsatt til aksen ev. legges til |
| `source_quality`-felt | Utsatt til det faktisk brukes i UI |
| 83 gjærstammer uten kategorier-profil | Kun aktive stammer i bruk er prioritert; resten kan legges til på forespørsel |
| 16 humler med `alfa_typisk: null` | Scraping utsatt |

### Style Engine — kjente gjenværende svakheter

| Svakhet | Status |
|---|---|
| Dark Mild har fortsatt minste smakskrav av alle stiler | Vil tiltrekke tvetydige mørke recipes med korrekt ABV. Ikke fikset — krever enten stilbibliotek-endring eller smakskrav-økning. |
| `english_ale`-signatur trigger på én ingrediens | Deliberat valg for nå. Kan strammes inn, men er ikke en prioritert feil. |
| Belgisk Tripel dukker opp for høygravitets-recipes | Korrekt teknisk atferd (ABV i range), men merkelig for brukeren. Ikke fikset. |
| Ingen stiler for høygravitets smoke ale / hybrid | Eldsvenn viser "Kreativt Brygg" — det er korrekt, men man mangler en "Strong Smoke Ale"-kategori. Utenfor scope. |

---

## 7. Anbefalt neste fokusområde

Basert på dagens arbeid og eksisterende backlog er naturlig progresjon:

### NEXT: Supply Engine V1

**Hva det er:** Pantry-/lagersystem for råvarer (humle, gjær, evt. malt).

**Hvorfor nå:** Style Engine og Flavor Engine er nå stabile nok til at man kan bygge funksjonalitet på toppen. Supply Engine er blokkeren for Smart Handleliste V2.

**Minste implementasjon:**
- `data/pantry.json` — nøkkel er master-DB-ID, enhet: gram/kg/pakker
- `modules/pantry.py` — `les_pantry()`, `lagre_pantry()`, `beregn_mangler()`
- `ui/pantry_panel.py` — enkel list-visning med input-felt

**Deretter:**

**Humlelager** (del av Supply Engine) — spesifikt for humle med høsting-dato og alfabeta-tracking.

**Smart Handleliste** (krever pantry) — `trenger = oppskrift - hjemme`, clamp til 0. To blokker: "har hjemme" og "må kjøpes".

**Mangellister** — output fra Smart Handleliste med butikklinker og priser.

---

*Logg skrevet 2026-06-11. Commits dokumentert: 9c3d665, e8bd67a, 378d0e4, a50564d, 05b7c4f, 335dcf4, bf5b051, 74cee50.*
