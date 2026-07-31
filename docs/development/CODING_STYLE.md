# Kvernhaug Brygghus — Kodestil og arkitekturprinsipper

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Arkitekturgrensen

Den viktigste regelen i prosjektet — se [PROJECT_MAP.md](PROJECT_MAP.md#den-harde-arkitekturgrensen-modules-vs-ui) for full forklaring:

- `modules/*.py` er ren Python. Aldri `import streamlit`.
- `ui/*.py` eier all rendering og kaller inn i `modules/`.

Test: kan koden kalles fra en test uten en Streamlit-kontekst? Hvis ja, hører den til i `modules/`.

## Prinsipper for implementasjon (fase 1)

- Bruk eksisterende arkitektur og eksisterende mønstre (se state-mønstrene i [PROJECT_MAP.md](PROJECT_MAP.md#etablerte-state-mønstre-streamlit)) fremfor å finne opp nye.
- Unngå duplisert kode — hvis samme logikk trengs to steder, del den ut til `modules/`.
- Lag modulære løsninger, men ikke design for hypotetiske fremtidige behov. Tre like linjer er bedre enn en for tidlig abstraksjon.
- Hold eksisterende kodekvalitet og navnekonvensjon (se [PROJECT_MAP.md](PROJECT_MAP.md#navnekonvensjon) — norsk for domenelogikk, engelsk/PEP8 for generiske tekniske mønstre).
- Ikke legg til feilhåndtering, fallbacks eller validering for scenarioer som ikke kan skje. Valider ved systemgrenser (brukerinput, eksterne API-er), stol på interne garantier ellers.

## Selvkontroll / kodekvalitet

Etter enhver implementasjon (fase 2 og 7 i [WORKFLOW.md](WORKFLOW.md)), sjekk og rapporter:

- **Andre moduler**: påvirkes noe utenfor filene du endret?
- **Lignende kode**: finnes et tilsvarende mønster andre steder som burde fått samme fiks? (Dette har vært en reell feilkilde i prosjektet — se [DEMO_MODE.md](DEMO_MODE.md)s dekningstabell, der flere `lagre_*`-funksjoner manglet samme guard fordi fiksen ikke ble spredt konsekvent første gang.)
- **Overflødighet**: gjorde implementasjonen annen kode unødvendig? Fjern den — ikke la den ligge som en kommentert-ut eller "kanskje trengs senere"-rest.
- **Duplisering**: finnes duplisert logikk som kunne vært slått sammen?
- **Dead code**: ubrukte imports, ubrukte variabler, ureflekterte TODO/FIXME i berørte filer.

Rapporter alt som ble funnet — også det du bevisst lot stå og hvorfor.

## Kommentarer

Standard: ingen kommentarer med mindre *hvorfor* er ikke-opplagt (en skjult begrensning, en subtil invariant, en workaround for en spesifikk bug). Ikke forklar *hva* koden gjør — gode navn gjør det allerede. Ikke referer til gjeldende oppgave, fiks eller kalleren i kommentarer ("brukt av X", "lagt til for Y") — det hører hjemme i commit-meldingen, ikke i koden, og råtner etter hvert som koden endrer seg videre.

## Backwards-compat-hacks

Unngå omdøping av ubrukte variabler med understrek-prefiks, re-eksport av typer for kompatibilitet, `# removed`-kommentarer for fjernet kode, eller feature flags for ting som bare kan endres direkte. Hvis noe er bekreftet ubrukt: slett det fullstendig.
