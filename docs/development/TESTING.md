# Kvernhaug Brygghus — Testing

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Hvordan kjøre

```bash
py -3 -m unittest discover -s tests
```

Ved siste kjente fulle kjøring (jf. `docs/PROJECT_STATUS_JULI_2026.md`, punkt-i-tid — verifiser alltid faktisk antall ved behov fremfor å stole på et gammelt tall): 581 tester, 0 skipped/errors/failures, fordelt på ~50 testfiler i `tests/`.

## Isolasjonsprinsipp

**Ingen test skal berøre brukerens ekte, private filer** (`recipes/`, `data/pantry.json`, `data/humle_lager.json`, `data/equipment.json`). Dette håndheves på to måter i eksisterende tester:

- **Midlertidige kataloger**: tester som øver på lagring peker moduler mot isolerte temp-kataloger i stedet for de ekte filstiene (se f.eks. mønsteret i `test_recipe_storage_isolation.py`, `test_pantry_integration.py`).
- **Committede, saniterte fixtures**: `tests/` inneholder egne fixture-kopier av oppskrifter (renset for personlig innhold) slik at ingen test er avhengig av brukerens faktiske, lokale data.

Ny test som trenger eksempeldata skal følge samme mønster — aldri peke direkte mot en fil som er gitignoret som privat brukerdata.

## `streamlit.testing.v1.AppTest`

Prosjektets etablerte rammeverk for full-script integrasjonstesting av Streamlit-UI (brukt i 20+ testfiler, f.eks. `test_water_target_ui_integration.py`, `test_humle_lager_panel_ui.py`, `test_process_panel.py`). Kjører hele `app.py` (eller en liten wrapper-app for et enkelt panel, se `tests/_*_app.py`-filene) i en headless test-runner og lar deg klikke knapper / sette widget-verdier / lese resultater uten nettleser.

Bruk dette mønsteret fremfor manuell blackbox-testing når en UI-endring skal verifiseres og ikke bare regnes ut for hånd. For engangs smoke-testing under en økt (ikke ment som permanent testsuite-tillegg) kan et throwaway-script i scratchpad-katalogen bruke samme mønster — legg det kun i den permanente `tests/`-mappen hvis det faktisk skal kjøres videre.

## Fase 6 i arbeidsflyten

Etter enhver implementasjon: kjør relevante tester og rapporter tester kjørt, resultat, warnings, regresjoner, og kodedekning der relevant (se [WORKFLOW.md](WORKFLOW.md#fase-6--testing)). Hvis testdekning mangler for det som ble endret, forklar hvorfor — og vurder om det bør legges til, uten å legge til tester brukeren ikke har bedt om for urelatert kode.
