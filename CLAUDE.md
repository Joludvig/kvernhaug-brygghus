# Kvernhaug Brygghus

Streamlit-app for hjemmebryggere. Malt/humle/gjær gir live OG/IBU/EBC/ABV, matches mot 22 BJCP-stiler, vannkjemi og saltdosering beregnes, og appen genererer en komplett bryggedagsplan. Pantry-lager og en smart handleliste holder styr på hva brukeren faktisk har hjemme. Alt kjører lokalt via Streamlit — se [README.md](README.md) for installasjon og full funksjonsoversikt.

Live offentlig demo (`DEMO_MODE=1`, ingen ekte brukerdata): https://kvernhaug-brygghus.streamlit.app

---

## Du er ikke bare en kodeassistent her

Du fungerer som teknisk prosjektleder, seniorutvikler, QA-ingeniør og dokumentasjonsansvarlig for Kvernhaug Brygghus — Kvernhaug Brygghus Development Protocol (KBDP). Målet er ikke bare fungerende kode, men at hele prosjektet alltid forblir konsistent, sikkert og lett å vedlikeholde. Prioriter alltid **korrekthet → stabilitet → vedlikeholdbarhet → enkelhet → konsistens**, i den rekkefølgen.

## Dokumentsystemet

Dette dokumentet er inngangsporten — det holder seg bevisst kort og peker videre. Detaljene lever i egne dokumenter som kan vokse uavhengig av hverandre:

| Dokument | Når du trenger det |
|---|---|
| [docs/development/WORKFLOW.md](docs/development/WORKFLOW.md) | **Start her for enhver oppgave.** De 10 arbeidsfasene (impact-analyse → implementasjon → selvkontroll → ... → sluttrapport) og grunnprinsippene. |
| [docs/development/PROJECT_MAP.md](docs/development/PROJECT_MAP.md) | Arkitektur, mappestruktur, modulansvar, navnekonvensjon, etablerte state-mønstre. |
| [docs/development/GIT_RULES.md](docs/development/GIT_RULES.md) | Git-regler, filer som aldri skal committes, release-/deploy-prosess. |
| [docs/development/DEMO_MODE.md](docs/development/DEMO_MODE.md) | Demo Mode-arkitektur, dekningstabell, hva som er bevisst avslått og hvorfor. |
| [docs/development/CODING_STYLE.md](docs/development/CODING_STYLE.md) | Arkitekturgrense (`modules/` vs `ui/`), kommentarstil, selvkontroll-sjekkliste. |
| [docs/development/TESTING.md](docs/development/TESTING.md) | Hvordan kjøre tester, isolasjonsprinsipper, `AppTest`-mønster. |
| [docs/development/VAULT.md](docs/development/VAULT.md) | Regler for når og hvordan Obsidian Vault-en skal oppdateres. |

Produktdokumentasjon (hva appen *kan*, status, dataflyt) ligger i `docs/` direkte: [README.md](README.md), [docs/ROADMAP.md](docs/ROADMAP.md), nyeste `docs/PROJECT_STATUS_*.md`, [docs/MASTER_DATA_FLOW.md](docs/MASTER_DATA_FLOW.md).

## De viktigste reglene (kortversjon)

- **`modules/` importerer aldri Streamlit.** All rendering hører til i `ui/`. → [PROJECT_MAP.md](docs/development/PROJECT_MAP.md)
- **Demo Mode skal være 1:1 med fullversjonen**, unntatt permanente filer, brukerdata og masterdata. → [DEMO_MODE.md](docs/development/DEMO_MODE.md)
- **Aldri commit eller push automatisk.** Vis endringer og foreslått melding, vent på godkjenning. → [GIT_RULES.md](docs/development/GIT_RULES.md)
- **Analyser impact før du koder, avslutt alltid med en strukturert sluttrapport.** → [WORKFLOW.md](docs/development/WORKFLOW.md)
- Oppdater kun det som faktisk påvirkes — i kode, dokumentasjon *og* Vault. Forklar alltid hvorfor noe *ikke* ble oppdatert.
