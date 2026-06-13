# Kvernhaug Brygghus

En lokal webapp for hjemmebryggere. Legg inn malt, humle og gjær — appen regner ut OG, IBU, EBC og ABV live, matcher oppskriften mot BJCP-stiler, og lager en komplett bryggedagsplan med vannberegninger, meskeplan og gjæranbefalinger. Alt lagres lokalt og kjøres i nettleseren via Streamlit, uten ekstern server eller database.

---

## Krav

- **Python 3.12 eller nyere** (anbefalt — eldre versjoner kan fungere, men er ikke testet)
- Windows, macOS eller Linux

---

## Installasjon

```bash
# 1. Klon repoet
git clone https://github.com/<din-bruker>/kvernhaug-brygghus.git
cd kvernhaug-brygghus

# 2. Opprett virtuelt miljø (Windows)
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer avhengigheter
pip install -r requirements.txt

# 4. Start appen
streamlit run app.py
```

Appen åpner seg automatisk i standardnettleseren på `http://localhost:8501`.

---

## Hva er bygget

**Oppskriftsbygger**
Malttabell med andeler (redistribuerer proporsjonalt ved endring), humleplan med Tinseth IBU-beregning, gjærvelger med utgjæringsgrad og fermenteringstemperatur. Batch-volum og oppskriftsnavn er redigerbare.

**Analyse og stil**
22 BJCP-stiler med prosentvis matching. Sensorisk smakshjul basert på malt- og humlekategorier. Balanseanalyse og advarsler (underhopping, overhopping, etc.).

**Humlelager**
Registrer beholdning i gram per humle-ID. Handlelisten viser automatisk hva du har hjemme, hva du mangler, og kjøpsberegning rundet opp til hel pakke.

**Handleliste**
Genereres fra gjeldende oppskrift med prisestimat og produktlenker per butikk (Vestbrygg / Ølbrygging.no). Eksport som .txt og .html.

**Bryggeplan og utskrift**
Bryggeplan med meskevann, skyllevann, pre-boil, meskeplan, koketid, humletilsetninger og gjæranbefalinger. To nedlastbare A4-ark: kompakt oppskriftsark og bryggedagsark med avkrysningsbokser.

**Datapipeline**
Tre masterfiler (`data/master_malt.json`, `data/master_humle_v2.json`, `data/master_gjaer_v2.json`) er manuelt kuratert med aliases, sensoriske tags og butikk-match. Import-panelet synkroniserer priser til runtime-filene appen leser fra.

---

## Mappestruktur

```
app.py              → Inngangspunkt, tab-layout
ui/                 → Én fil per panel (malt, humle, gjær, handleliste, bryggdag, ...)
modules/            → Beregningslogikk (recipe_context, brewday_calc, style_engine, ...)
data/               → Masterdatabaser (rediger her) + runtime-filer (genereres)
recipes/            → Dine lagrede oppskrifter (opprettes automatisk, ikke delt)
assets/             → Bilder og branding
docs/               → Teknisk dokumentasjon og sesjonlogger
```

### `data/` — hva er hva

| Fil | Beskrivelse |
|-----|-------------|
| `master_humle_v2.json` | Kuratert humledatabase med sensoriske tags og butikk-match |
| `master_gjaer_v2.json` | Kuratert gjærdatabase |
| `master_malt.json` | Kuratert maltdatabase |
| `humle.json` / `malt.json` / `gjaer.json` | Runtime-databaser (generert fra master, leses av appen) |
| `humle_lager.json` | Din lokale humlebeholdning (opprettes automatisk, ikke delt) |
| `equipment.json` | Din utstyrsprofil (opprettes automatisk, ikke delt) |

### `recipes/` — dine oppskrifter

Oppskrifter lagres som JSON-filer i `recipes/`. Mappen opprettes automatisk ved første kjøring og er ikke inkludert i git — oppskriftene dine deles ikke.

---

## Begrensninger

- **Lokal app** — kjører kun på din maskin, ingen ekstern server
- **Én bruker** — ingen innlogging eller bruker-separasjon
- **Ingen sky-synk** — data lagres i `data/` og `recipes/` på din harddisk
- **JSON-lagring** — ingen database; all tilstand er lesbare tekstfiler
- **Scraper-funksjonalitet** krever internett-tilkobling og kan bryte ved endringer hos Vestbrygg / Ølbrygging.no

---

## Tabs og arbeidsflyt

Appen er organisert i fire tabs:

| Tab | Innhold |
|-----|---------|
| 🍺 **Oppskrift** | Ingredienser, beregninger, smakshjul, BJCP-matching |
| 🛒 **Innkjøp & Lager** | Handleliste med lagerberegning, humlelager-registrering |
| 🧪 **Bryggdag** | Bryggedagsark, utstyrsprofil |
| 🔧 **Verktøy** | Leverandørkontroll, oppskriftsimport |

---

## Lisens

Privat prosjekt. Ikke lisensiert for redistribusjon.
