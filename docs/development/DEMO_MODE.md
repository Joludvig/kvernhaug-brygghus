# Kvernhaug Brygghus — Demo Mode

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Prinsipp

Demo Mode skal alltid være en **1:1 representasjon av fullversjonen**, med tre unntak:

- ingen permanente filer skrives
- ingen brukerdata leses eller endres
- ingen ekte databaser (masterdata) endres

En bruker som åpner Demo Mode skal få nøyaktig samme opplevelse som i fullversjonen, bortsett fra at alle endringer er midlertidige.

**Konsekvens for hver ny funksjon**: undersøk alltid om endringen påvirker Demo Mode (fase 3 i [WORKFLOW.md](WORKFLOW.md)). Hvis ja: oppdater Demo Mode etter mønsteret under. Hvis nei — fordi funksjonen er ren beregningslogikk uten fil-I/O, eller fordi den allerede er dekket av et eksisterende gate — forklar hvorfor i sluttrapporten.

## Arkitektur

`config.py::DEMO_MODE` (`os.getenv("DEMO_MODE", "0") == "1"`) er **eneste kilde til sannhet**. Alt annet i denne filen er konsekvenser av det ene flagget.

Det finnes to komplementære mønstre, brukt sammen:

### 1. Skriv-guard i `modules/`

Enhver funksjon i `modules/` som skriver til disk skal starte med:

```python
from config import DEMO_MODE

def lagre_noe(data):
    if DEMO_MODE:
        return
    ...
```

Dette er den *minimale* beskyttelsen — den hindrer skade, men gjør ikke panelet interaktivt (uten overlay under vil et "lagre"-klikk se ut som det ikke gjør noe).

### 2. Session-scoped overlay (`ui/demo_state.py`)

For paneler som skal forbli **fullt interaktive** i demo — brukeren skal kunne legge til/endre/slette fritt innenfor økten, uten at noe treffer disk — brukes `ui/demo_state.py`. Den holder data i `st.session_state` i stedet for på disk, og speiler samme funksjonssignatur som modulen den erstatter (`hent_x()` / `lagre_x(data)`).

Viktig arkitekturvalg: denne overlay-logikken ligger i `ui/`, **ikke** i `modules/`, fordi `modules/` per regel aldri skal importere Streamlit (`st.session_state` er en Streamlit-konstruksjon). Se [PROJECT_MAP.md](PROJECT_MAP.md#den-harde-arkitekturgrensen-modules-vs-ui) for hvorfor denne grensen håndheves strengt.

Panelet bruker en liten wrapper for å velge riktig kilde:

```python
from config import DEMO_MODE
from ui import demo_state

def _hent_pantry():
    return demo_state.hent_pantry() if DEMO_MODE else pantry.last_pantry()

def _lagre_pantry(data):
    if DEMO_MODE:
        demo_state.lagre_pantry(data)
    else:
        pantry.lagre_pantry(data)
```

### Hva overlayen er trygg å seede fra

- **Git-sporet, delt referansedata** (`data/pantry.example.json`, `data/water_sources.json`, `data/water_targets.json`) — trygt, siden dette allerede er ment å deles.
- **Interne standardverdier** (f.eks. `modules/equipment.py::DEFAULTS`) — trygt.
- **ALDRI** gitignoret privat brukerdata (`data/pantry.json`, `data/equipment.json`, `data/humle_lager.json`, `recipes/`) — heller ikke for å "seede" en engangs-demo-verdi. Overlayen skal ikke ha noen kodesti som leser disse filene når `DEMO_MODE=1`.

## Dekningstabell (per siste gjennomgang)

| Funksjon | Skriv-guard | Interaktiv i demo (overlay) |
|---|---|---|
| Pantry (`pantry.py` / `pantry_panel.py`) | ✅ | ✅ (`demo_state.hent_pantry`/`lagre_pantry`) |
| Smart Handleliste | — (leser pantry) | ✅ (deler samme session-pantry som Pantry-panelet) |
| Utstyrsprofil (`equipment.py` / `equipment_panel.py`) | ✅ | ✅ |
| Vannkjemi — kilder/mål (`water_chemistry.py` / `water_panel.py`) | ✅ | ✅ |
| Eldre humlelager (`humle_lager.py` / `humle_lager_panel.py`) | ✅ | ✅ |
| Oppskriftslagring (`recipe_storage.py` / `recipe_card.py`) | ✅ | Nei — lagre/kopier/slett skjules bevisst |
| Masterdata-scaffold (`app.py::last_json_data`) | ✅ (ingen fil opprettes) | n/a — ren lesefallback |
| Import / scraper (`import_panel.py` og alt bak den) | ✅ (helt gatet) | Nei — se under |
| Bryggedagsjournal per oppskrift (`recipe_card.py`, brewday-resultat) | ✅ (helt gatet) | Nei — se under |

## Bevisst fortsatt avslått, og hvorfor

- **Import / scraper / leverandørpanel**: ingen trygg "demo"-ekvivalent finnes — funksjonen *er* nettverkskall og skriving til masterdata/brukerens produktbibliotek. Å late som dette virker i demo ville enten kreve ekte nettverkskall fra en offentlig demo-container (uønsket) eller en helt separat fake-pipeline (uforholdsmessig kompleksitet for liten gevinst). Forblir bak `import_panel.py`s eksisterende `if DEMO_MODE: return`-gate.
- **Bryggedagsjournal-visning per oppskrift**: slår opp ekte loggnotater via `hent_logg(oppskriftsnavn)`, nøkkelbasert på oppskriftsnavn. Siden demo-oppskriftene sannsynligvis har navn som overlapper med brukerens ekte private oppskrifter, er risikoen at demo-visningen ved et uhell viser innhold fra brukerens ekte, private bryggedagsnotater. Latt stå bak `if not DEMO_MODE:` inntil det finnes en navnekollisjon-sikker løsning.

## Regel for nytt arbeid

Enhver ny funksjon i `modules/` som skriver til disk **skal** ha `if DEMO_MODE: return` fra dag én — ikke ettermontert senere. Hvis den tilhørende UI-funksjonaliteten bør forbli interaktiv i demo, legg til et tilsvarende par i `ui/demo_state.py` etter mønsteret over, fremfor å gate hele panelet med en blanke `if DEMO_MODE: return`.
