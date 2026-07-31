# Kvernhaug Brygghus — Git-regler

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Grunnregel

- **Aldri commit automatisk.**
- **Aldri push automatisk.**
- Vis alltid: endrede filer, hvorfor de ble endret, og foreslått commit-melding. Vent deretter på eksplisitt godkjenning fra brukeren.
- Godkjenning gjelder for det som faktisk ble spurt om — en tidligere "ja, push" er ikke stående fullmakt til å pushe neste gang uten å spørre.

## Før du committer: sjekk om arbeidstreet er "rent" for oppgaven

Dette repoet samler ofte opp flere økters ferdig-men-uncommitted arbeid samtidig. Før du kjører `git commit` for en avgrenset oppgave:

1. Kjør `git status` og `git diff --stat` og se om andre, urelaterte endringer ligger i samme filer.
2. Hvis filer blander flere features' hunks: ikke bare bundle alt i én commit. Spør brukeren om å splitte i flere commits, bundle bevisst, eller committe kun den rent avgrensede delen.
3. Fil som er helt urelatert til oppgaven skal stå ucommittet med mindre brukeren spesifikt ber om den.

En misvisende commit-melding (tittel sier "vannkjemi", diffen inneholder også en urelatert fiks) er verre enn den ekstra jobben det er å separere hunks.

## Filer som ALDRI skal committes

Utover det som allerede er dekket av `.gitignore` (se den for fullstendig, oppdatert liste — ikke dupliser den her manuelt), er disse verdt å huske eksplisitt fordi konsekvensen av en feil er alvorlig:

- **`raw_data/malt_raw.json`** — kjent beskyttet fil fra tidligere prosjektregler. Ikke stag denne selv om den vises som endret, med mindre brukeren eksplisitt ber om det.
- **Alt under `/recipes/`** og `/recipes_backup_*/` — brukerens private oppskrifter.
- **`data/pantry.json`, `data/humle_lager.json`, `data/equipment.json`** (+ backup-/tmp-varianter) — privat runtime-data. Se [PROJECT_MAP.md](PROJECT_MAP.md#datalag-data) for hvorfor disse er gitignoret mens `master_*.json` og `water_*.json` er git-sporet.
- **`data/*.bak`, `data/*.json.backup_*`** — automatiske backup-artefakter av masterdata.

Når du stager filer for en commit: bruk eksplisitt filliste, ikke `git add -A` eller `git add .` — det reduserer risikoen for å dra med seg noe av det ovenstående ved et uhell.

## Commit-meldinger

- Ny commit fremfor `--amend`, med mindre brukeren eksplisitt ber om amend.
- Aldri `--no-verify`, `--no-gpg-sign` eller andre hook-/signeringshopp uten eksplisitt forespørsel.
- Meldingen skal forklare *hvorfor*, ikke bare hva — se `git log` for stilen som allerede brukes i repoet.

## Release-prosess

Deploy er direkte koblet til `git push`:

- **Repo**: `https://github.com/Joludvig/kvernhaug-brygghus` (offentlig)
- **Default branch**: `master`
- **Streamlit Community Cloud** følger `master` automatisk. En push til `master` trigger redeploy av den offentlige demoen på `https://kvernhaug-brygghus.streamlit.app`, kjørt med `DEMO_MODE=1`.

Konsekvens: en push til `master` er ikke bare en kodehandling — det er en publisering til en live, offentlig demo. Behandle det deretter:

- Før du foreslår push: bekreft at Demo Mode faktisk er verifisert for endringen (fase 3 i [WORKFLOW.md](WORKFLOW.md), se [DEMO_MODE.md](DEMO_MODE.md)).
- Flagg alltid til brukeren at en push vil trigge redeploy av den offentlige demoen, slik at det ikke skjer som en overraskelse.
- Hvis repoet er flere commits foran `origin` (dvs. tidligere upushet arbeid), si ifra om det eksplisitt før du pusher — ikke push stille forbi det.
