# Kvernhaug Brygghus — Project Map

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

Formålet med dette dokumentet er at en ny økt raskt skal forstå **hvor ting bor** og **hvorfor**, uten å måtte lese hele kodebasen. For produktnivå (hva appen *kan*) og status, se `docs/ROADMAP.md` og `docs/PROJECT_STATUS_JULI_2026.md` (eller nyeste status-dokument — status-dokumenter er punkt-i-tid og erstattes, ikke overskrives).

---

## Arkitektur på ett blikk

```
app.py                 → Inngangspunkt. Setter opp session_state, laster masterdata,
                          bygger 4 tabs, kaller bygg_recipe_context() (den sentrale motoren)
                          og render-funksjonene i riktig rekkefølge.
config.py               → DEMO_MODE-flagget. Eneste kilde til sannhet for demo-modus.
modules/                → "Ren Python" — beregningslogikk, dataflyt, lagring
ui/                     → Ett panel per fane-seksjon — all Streamlit-rendering
data/                   → Masterdatabaser (delt, git-sporet) + private runtime-filer (gitignoret)
recipes/                → Brukerens lagrede oppskrifter (gitignoret, opprettes automatisk)
demo_recipes/           → 3 demo-oppskrifter, committed til git
raw_data/                → Skrapet rådata og review-filer for masterdata-pipelinen
tests/                  → Testsuite (unittest + streamlit.testing.v1.AppTest)
docs/                   → Produktdokumentasjon (denne mappen: docs/development/ = prosessdokumentasjon)
assets/                 → Bilder og branding
web/                    → Separat, frittstående statisk web-versjon (vanilla HTML/CSS/JS, ingen build-steg).
                          IKKE en del av Streamlit-appens modules/ui-arkitektur — egen liten JS-port av
                          utvalgte formler fra modules/calculations.py. Se web/README.md.
```

## Den harde arkitekturgrensen: `modules/` vs. `ui/`

Dette er den viktigste strukturregelen i prosjektet, og den håndheves som en hard grense:

- **`modules/*.py` er ren Python og skal ALDRI importere `streamlit`.** All beregningslogikk, all fil-I/O, all datavalidering hører hjemme her. Flere filer har dette som eksplisitt docstring-krav (f.eks. `modules/card_template.py`: *"No Streamlit imports — safe to call from any context."*).
- **`ui/*.py` eier all Streamlit-rendering** og kaller inn i `modules/` for logikk. UI-filer skal ikke inneholde forretningslogikk utover ren visningstilstand (widget keys, session_state-koordinering).

Konsekvens for nytt arbeid: hvis du er usikker på om kode hører hjemme i `modules/` eller `ui/`, still spørsmålet "kan dette kalles uten en Streamlit-kontekst (f.eks. fra en test)?" — hvis ja, hører det til i `modules/`.

## Den sentrale motoren

`modules/recipe_context.py::bygg_recipe_context()` er navet appen kjøres rundt. Den tar inn valgt malt/humle/gjær + databasene, og returnerer en samlet `ctx`-struktur (OG/IBU/EBC/ABV, smaksprofil, stilmatch) som alle nedstrøms paneler (recipe_card, style_panel, brewday_panel, water_panel, pantry_panel osv.) leser fra. `app.py` bygger `ctx` étt sted, rett etter at input-panelene (malt/humle/gjær) har rendret.

## Moduloversikt (`modules/`)

| Område | Filer |
|---|---|
| Beregning (kjerne) | `calculations.py`, `recipe.py`, `recipe_context.py` |
| Style / smak | `style_engine.py`, `flavor_engine.py`, `flavor_summary.py`, `flavor_conflicts.py`, `flavor_relationships.py` |
| Prosess / bryggedag | `process_profiles.py`, `brewday_calc.py`, `brewday_template.py` |
| Vannkjemi | `water_chemistry.py` |
| Utstyr | `equipment.py` |
| Lager (Pantry) | `pantry.py`, `humle_lager.py`, `malt_packaging.py`, `smart_shopping_list.py` |
| Oppskriftslagring | `recipe_storage.py` |
| Eksport | `export_format.py`, `card_template.py`, `shopping_template.py` |
| Masterdata / import | `master_data_io.py`, `recipe_importer.py`, `ingredient_matcher.py`, `ingredient_normalizer.py`, `validation.py`, `db_cleanup.py` |
| Scraper / prissynk | `store_scraper.py`, `store_sync.py`, `store_matcher.py`, `product_link_scraper.py`, `validate_sync.py` |

## Panel­oversikt (`ui/`)

Ett panel per fane-seksjon; navnet forteller ansvaret (`malt_panel.py`, `hop_panel.py`, `yeast_panel.py`, `pantry_panel.py`, `smart_shopping_list_panel.py`, `humle_lager_panel.py`, `water_panel.py`, `process_panel.py`, `brewday_panel.py`, `equipment_panel.py`, `recipe_card.py`, `style_panel.py`, `supplier_panel.py`, `import_panel.py`, `review_panel.py`, `shopping_list_panel.py`, `sidebar.py`, `branding.py`). `ui/demo_state.py` er unntaket — ingen render-funksjon, kun session-state-hjelpere for Demo Mode (se [DEMO_MODE.md](DEMO_MODE.md)).

## Fire tabs (definert i `app.py`)

| Tab | Innhold |
|---|---|
| 🍺 Oppskrift | malt/hop/yeast-paneler, recipe_card, style_panel |
| 🛒 Innkjøp & Lager | pantry_panel, smart_shopping_list_panel, (eldre) shopping_list_panel + humle_lager_panel |
| 🧪 Bryggdag | process_panel, water_panel, brewday_panel, equipment_panel |
| 🔧 Verktøy | supplier_panel, import_panel |

## Datalag (`data/`)

**Git-sporet / delt referansedata** — trygt å lese fra, også i Demo Mode:
`master_malt.json`, `master_humle_v2.json`, `master_gjaer_v2.json`, `water_sources.json`, `water_targets.json`, `pantry.example.json`.

**Gitignoret / privat brukerdata** — skal ALDRI leses eller skrives i Demo Mode, og skal ALDRI committes:
`pantry.json` (+ `.tmp`/`.backup_*`), `humle_lager.json`, `equipment.json`, samt alt under `/recipes/`.

Fullstendig `.gitignore`-liste og begrunnelse: [GIT_RULES.md](GIT_RULES.md). For selve masterdata-pipelinen (scrape → normaliser → review → master): [../MASTER_DATA_FLOW.md](../MASTER_DATA_FLOW.md).

## Navnekonvensjon

Domenelogikk (funksjoner, variabler som representerer bryggedomenet) navngis på **norsk**: `bygg_recipe_context`, `last_json_data`, `lagre_pantry`, `les_lager`, `beregn_og`. UI-tekst er gjennomgående norsk. Generiske tekniske mønstre (klassenavn, standard Python-konvensjoner som `snake_case`, testfil-prefiks `test_`) følger vanlig engelsk/PEP8-praksis. Ikke bland — ikke oversett domenefunksjoner til engelsk, og ikke gi tekniske hjelpefunksjoner norske navn uten grunn.

## Etablerte state-mønstre (Streamlit)

Disse er ikke opplagte fra koden alene og har vært kilde til bugs tidligere — gjenbruk dem fremfor å finne opp nye:

- **Shadow key**: f.eks. `_batch_volum_preserved`, `_gjeldende_navn_preserved` i `app.py` — synkes tidlig, før noe panel kan kalle `st.rerun()`, slik at en widget-bundet nøkkel kan gjenopprettes hvis Streamlit sletter den under en mid-render rerun.
- **Pending key**: f.eks. `_pending_batch_volum`, `_pending_gjeldende_navn` — lagrer en verdi som skal appliseres *øverst* i neste kjøring, før noen widget instansieres (unngår `StreamlitAPIException` ved å sette en widget-bundet key etter at widgeten er opprettet).
- **Versjonsnøkkel for widget-reset**: `import_versjon` i `session_state` brukes som del av widget-keys (`malt_ui_{i}_v{_v}`) — inkrementeres for å tvinge frem et rent widget-reset uten å slette nøkler manuelt.
