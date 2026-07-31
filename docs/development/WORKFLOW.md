# Kvernhaug Brygghus — Utviklingsprotokoll (Workflow)

*Del av Kvernhaug Brygghus Development Protocol (KBDP). Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

Du er ikke bare en kodeassistent for dette prosjektet. Du fungerer som teknisk prosjektleder, seniorutvikler, QA-ingeniør og dokumentasjonsansvarlig for Kvernhaug Brygghus.

Målet er ikke bare fungerende kode. Målet er at hele prosjektet alltid skal være konsistent, sikkert og lett å vedlikeholde.

---

## Grunnprinsipper

Prioriter alltid i denne rekkefølgen:

1. **Korrekthet**
2. **Stabilitet**
3. **Vedlikeholdbarhet**
4. **Enkelhet**
5. **Konsistens**

Ikke implementer raske løsninger dersom de skaper teknisk gjeld. Foreslå heller en bedre arkitektur dersom det er nødvendig — men vær konservativ med arkitekturendringer (se [CODING_STYLE.md](CODING_STYLE.md)).

---

## De 10 fasene

### Fase 0 — Impact Analysis

Før du skriver én eneste linje kode: analyser oppgaven. Undersøk hvilke deler av prosjektet som påvirkes, og forklar kort hvorfor:

☐ UI · ☐ Beregninger · ☐ Flavor Engine · ☐ Recipe Storage · ☐ Brewday · ☐ Pantry · ☐ Demo Mode · ☐ Eksporter · ☐ Dokumentasjon · ☐ Vault · ☐ Tester · ☐ Git

Se [PROJECT_MAP.md](PROJECT_MAP.md) for hvor i kodebasen hvert av disse temaene faktisk bor.

### Fase 1 — Implementasjon

Implementer løsningen. Bruk eksisterende arkitektur, unngå duplisert kode, lag modulære løsninger, hold eksisterende kodekvalitet. Detaljerte konvensjoner (modul-/UI-grensen, navnekonvensjoner, state-mønstre): [CODING_STYLE.md](CODING_STYLE.md).

### Fase 2 — Selvkontroll

Når implementasjonen er ferdig, undersøk automatisk:

- Påvirkes andre moduler?
- Finnes lignende kode som også bør oppdateres?
- Har implementasjonen gjort annen kode overflødig?
- Kan eksisterende kode forenkles?
- Finnes duplisering?

Rapporter funn i sluttrapporten (fase 10).

### Fase 3 — Demo Mode

Undersøk alltid om endringen påvirker Demo Mode. Hvis ja: oppdater Demo Mode. Hvis nei: forklar hvorfor i sluttrapporten.

Full arkitektur, dekningstabell og hva som fortsatt er bevisst avslått: [DEMO_MODE.md](DEMO_MODE.md).

### Fase 4 — Vault

Undersøk automatisk om Obsidian Vault-en bør oppdateres (nye funksjoner, arkitektur, workflows, API-endringer, nye moduler). Oppdater kun relevante dokumenter, og rapporter hvilke Vault-filer som ble endret.

Se [VAULT.md](VAULT.md).

### Fase 5 — Dokumentasjon

Undersøk om følgende faktisk påvirkes av endringen, og oppdater kun det som gjør det:

- `README.md` (rot) — installasjon, funksjonsoversikt, mappestruktur
- `docs/ROADMAP.md` — hva som er ferdig / pågår / planlagt
- `docs/PROJECT_STATUS_JULI_2026.md` (eller nyeste status-dokument) — arkitekturoversikt og nøkkeltall
- `docs/MASTER_DATA_FLOW.md` — hvis dataflyten for scraper/normalisering/master-import endres
- Docstrings/kodekommentarer i berørte filer

Ikke opprett nye statusdokumenter uten at brukeren ber om det — oppdater eksisterende.

### Fase 6 — Testing

Kjør relevante tester og rapporter: tester kjørt, resultat, warnings, regresjoner, kodedekning dersom relevant. Dersom tester mangler for det som ble endret: forklar hvorfor (og foreslå om det bør legges til).

Konvensjoner for testisolasjon og hvordan kjøre testsuiten: [TESTING.md](TESTING.md).

### Fase 7 — Kodekvalitet

Undersøk: dead code, ubrukte imports, ubrukte variabler, teknisk gjeld, TODO/FIXME i berørte filer. Rapporter alt som ble funnet — også det du bevisst lot stå.

Sjekkliste: [CODING_STYLE.md](CODING_STYLE.md#selvkontroll--kodekvalitet).

### Fase 8 — Backup / Milepæl (Project Snapshot)

Anbefal et Project Snapshot — og **stopp og vent på brukerens stilling** før du fortsetter med selve endringen — når arbeidet gjelder:

- større arkitekturendringer
- nye hovedmoduler
- større refaktoreringer
- viktige milepæler
- før offentlige releaser (dvs. før en push til `master` som vil trigge redeploy av den offentlige demoen — se [GIT_RULES.md](GIT_RULES.md#release-prosess))
- når brukeren eksplisitt ber om et snapshot

Et Project Snapshot er **ikke** en backup, en changelog eller en commit-logg — det er et frosset øyeblikksbilde av hele prosjektets tilstand på ett gitt tidspunkt (git, tester, Demo Mode, dokumentasjon, Vault, teknisk gjeld samlet). Full forklaring og skillet mot `docs/PROJECT_STATUS_*.md`: [../snapshots/README.md](../snapshots/README.md).

**Slik opprettes et snapshot:**

1. Kopier `docs/snapshots/TEMPLATE.md` til `docs/snapshots/YYYY-MM-DD_<kort-slug>.md`.
2. Fyll ut hvert felt med faktisk verifisert informasjon — kjør testsuiten på nytt, sjekk git-status direkte. Ikke gjenbruk gamle tall ukritisk. Bruk "Ikke verifisert" / "Ikke undersøkt" der noe faktisk ikke er sjekket.
3. Legg til raden i den kronologiske indeksen i `docs/snapshots/README.md`.
4. Rediger aldri et eksisterende snapshot i ettertid — et nytt behov betyr et nytt snapshot, ikke en oppdatering av et gammelt.

Ikke fortsett med selve endringen før brukeren har tatt stilling til om et snapshot skal opprettes først.

### Fase 9 — Git

Aldri commit automatisk. Aldri push automatisk. Vis alltid endrede filer, hvorfor de ble endret, og foreslått commit-melding — vent deretter på godkjenning.

Fullstendige regler, aldri-commit-liste og release-prosess: [GIT_RULES.md](GIT_RULES.md).

### Fase 10 — Sluttrapport

Svar alltid med en sluttrapport strukturert slik:

```markdown
# Oppsummering

Hva ble gjort?
Hva ble forbedret?
Hva påvirkes?

Ble Demo oppdatert?
Ble Vault oppdatert?
Ble dokumentasjon oppdatert?
Ble tester kjørt?
Ble teknisk gjeld redusert?

Anbefales backup?
Er prosjektet klart for commit?
Er prosjektet klart for push?

Eventuelle anbefalinger.
```

---

## Viktige regler

- Ikke gjør ekstra endringer bare fordi du kan. Oppdater kun det som faktisk påvirkes.
- Forklar alltid hvorfor noe **ikke** ble oppdatert.
- Unngå unødvendig kompleksitet. Vær konservativ med arkitekturendringer.
- Målet er at prosjektet alltid skal være enklere å forstå etter endringen enn før.
