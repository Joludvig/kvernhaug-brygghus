# Kvernhaug Brygghus — Testing

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Hvordan kjøre

```bash
py -3 -m unittest discover -s tests -b
```

`-b`/`--buffer` demper stdout/stderr fra hver test (inkl. print()-støy fra enkelte scraper-moduler i `modules/`) for tester som består — output for feilende tester vises fortsatt i sin helhet, uendret. Ingen testlogikk endres av flagget.

Ved siste kjente fulle kjøring (jf. `docs/PROJECT_STATUS_JULI_2026.md`, punkt-i-tid — verifiser alltid faktisk antall ved behov fremfor å stole på et gammelt tall): 581 tester, 0 skipped/errors/failures, fordelt på ~50 testfiler i `tests/`.

## Full suite vs. avgrenset kjøring

`tests/` dekker i hovedsak desktop-appen (`app.py`/`modules/`/`ui/`), men **ikke bare** den: `tests/test_generate_web_i18n_pages.py` (49 tester) dekker `web/**` gjennom i18n-generatoren — TEKSTER-parsing og NO/EN-nøkkelsymmetri, `PAGES`-guarden mot uregistrerte sider, asset-/språkvelger-stier, determinisme, canonical/hreflang-gjensidighet, meta-description, `sitemap.xml`, `robots.txt`, noindex og favicon-dekning — inkludert at committet `web/en/**` og `sitemap.xml` er byte-identiske med en fersk generatorkjøring. En endring i `web/**` kan derfor bryte suiten.

Det finnes derimot ingen browser-/E2E-dekning i `tests/`: funksjonell, responsiv og konsollfeil-verifisering i ekte nettleser er en egen, manuell Playwright-sveip (se `.claude/skills/web-full-regression/SKILL.md`). Se testpolicy i [`.claude/rules/testing.md`](../../.claude/rules/testing.md) for når full suite faktisk trengs kontra en avgrenset/intermediate runde.

### Ekte, kjørende JS-dekning av DOM-frie web/js-moduler (WEB PRI 5, issue #51) — BLOKKERT

De første web-testene i `tests/` (f.eks. `test_web_mode_storage_fix.py`, `test_web_custom_ingredient_id_active_draft.py`) antok at miljøet ikke har noen JavaScript-kjøretid, og verifiserer derfor kun at kildeteksten i `web/js/**` matcher bestemte regex-mønstre ("kilde-kontrakt"-tester) — de kan bevise at koden SER riktig ut, aldri hva den faktisk RETURNERER. Dette er fortsatt gjeldende, aktivt mønster for nye DOM-frie web/js-tester.

Et forsøk på ekte, kjørende dekning (`tests/web_js_runtime.py` + `tests/js_runtime/eval_web_js.js`, som lastet `web/js/*.js` inn i en Node `vm`-kontekst) ble avvist i Chief-review (PR #53, hode `56dcab8`): implementasjonen shellet ut til `node` fra en tillatt `python3 -m unittest ...`-prosess, noe reviewen fastslo er en omgåelse av Agent Bridge sin Bash-tillatelsesliste (`docs/development/AGENT_WORKFLOW.md` definerer listen som det minimale, eksplisitte kommandosettet — kun listede kommandoer er tillatt; å tunnelere `node`, som selv ikke står på listen, gjennom en tillatt Python-subprosess omgår kontrollen i stedet for å utvide den). `run_web_js()` nekter nå å kjøre, og de fire opprinnelige testfilene som brukte den (`tests/test_web_js_calc.py`, `tests/test_web_js_kbhrecipe.py`, `tests/test_web_js_custom_ingredient_id.py`, `tests/test_web_js_brew_storage.py`) er `@unittest.skip`-et — beholdt (ikke slettet) som golden-vector-referanse for en fremtidig, eksplisitt egen-reviewet Bridge-tillatelsesendring, ikke noe en Web-test-runde skal gjeninnføre på egen hånd.

En andre Chief-review (PR #53, hode `92e2ba2`) påpekte at det blokkerte forsøket alene ikke leverte NOEN aktiv dekning (30 skippede tester beviser ingenting), og krevde ett avgrenset, aktivt increment innenfor allerede-autoriserte kommandoer. `tests/test_web_calc_js_parity.py` dekker dette for `calc.js` (issue #51 sitt førsteprioriterte "kalkulasjonssemantikk"-område): `web/js/calc.js` sin egen headerkommentar erklærer den som en manuelt vedlikeholdt port av `modules/calculations.py` ("hold i sync manuelt hvis formlene endres i Python-siden") — et løfte uten håndheving før denne testfilen. Den leser BEGGE de virkelige, kjørende kildefilene (JS via regex, Python via `ast`/`inspect` — aldri en hånd-kopiert snippet) og sammenligner, med ekte verdi-/sekvenslikhetsassertions (ikke bare "mønster finnes"), de fem delte konverteringskonstantene og den ordnede tall-/operatorsekvensen i hver portede funksjonskropp (`beregnOG`/`beregn_og`, `beregnEBC`/`beregn_ebc`, `beregnGramFraIBU`/`beregn_gram_fra_ibu` inkl. dens dokumenterte, bit-identiske men tekstlig ulike avrundingsuttrykk, `beregnFgOgAbv`/`beregn_fg_og_abv`) — verifisert (og reversert igjen) til faktisk å feile på en injisert konstant-/formelendring på kun én side, ikke bare til å bestå tautologisk. `modules/calculations.py` selv har fra før solid, ekte EXECUTED golden-vector-dekning andre steder (`test_calculation_golden_vectors.py`, `test_calculations_gravity.py`, `test_calculations_ibu_alfa.py`, `test_ebc_calculation.py`); denne filen dekker spesifikt PARITETEN mellom det og JS-porten, uten noensinne å starte `node`.

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
