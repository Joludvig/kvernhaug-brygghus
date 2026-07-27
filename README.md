# Kvernhaug Brygghus

En lokal webapp for hjemmebryggere. Legg inn malt, humle og gjær — appen regner ut OG, IBU, EBC og ABV live, matcher oppskriften mot BJCP-stiler, beregner vannkjemi og saltdosering, og lager en komplett bryggedagsplan med meskeplan, gjæranbefalinger og prosessprofiler (inkl. Hochkurz). Et eget Pantry-lager og en smart handleliste holder styr på hva du faktisk har hjemme. Alt lagres lokalt og kjøres i nettleseren via Streamlit, uten ekstern server eller database.

---

## Krav

- **Python 3.12 eller nyere** (anbefalt — eldre versjoner kan fungere, men er ikke testet)
- Windows, macOS eller Linux

---

## Installasjon og oppstart

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

På Windows kan `start_app.bat` brukes som snarvei for steg 4.

Appen åpner seg automatisk i standardnettleseren på `http://localhost:8501`.

---

## Viktigste funksjoner

- **Oppskriftsbygger** — malt/humle/gjær med live OG, IBU, EBC, ABV; redigerbart batch-volum
- **Style Engine** — 22 BJCP-stiler med prosentvis matching, sensorisk smakshjul, balanseanalyse
- **Vannkjemi** — kildevann, målprofilbibliotek, saltdosering, mesk/skyll-fordeling
- **Bryggeplan og bryggedagsark** — prosessprofiler, meskeplan, gjæranbefaling, utskriftsvennlige A4-ark
- **Pantry (📦 Lager)** — reell lagerbeholdning per ingrediens, inkl. egendefinerte varer, med automatisk backup og gjenoppretting
- **Smart Handleliste** — beregner reell mangel og kjøpsforslag ut fra Pantry
- **Datapipeline** — kuraterte masterdatabaser for malt, humle og gjær, med butikk-prissynk

Se [docs/ROADMAP.md](docs/ROADMAP.md) og [docs/PROJECT_STATUS_JULI_2026.md](docs/PROJECT_STATUS_JULI_2026.md) for hva som er ferdig, hva som pågår, og hva som er planlagt.

---

## Private data

`recipes/` og alle private runtime-filer i `data/` (blant annet `pantry.json` og tilhørende backupfiler, `humle_lager.json`, `equipment.json`) er gitignoret — de opprettes automatisk lokalt og deles aldri via git.

---

## Tester

```bash
py -3 -m unittest discover -s tests
```

Ingen test skal berøre dine ekte, private filer i `recipes/` eller `data/pantry.json` — testene bruker isolerte, midlertidige kataloger.

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
| 🛒 **Innkjøp & Lager** | Pantry, Smart Handleliste, eldre handleliste/humlelager |
| 🧪 **Bryggdag** | Prosessprofiler, vannkjemi, bryggedagsark, utstyrsprofil |
| 🔧 **Verktøy** | Leverandørkontroll, oppskriftsimport |

---

## Lisens

Privat prosjekt. Ikke lisensiert for redistribusjon.
