# Kvernhaug Brygghus — Status Juli 2026

*Utkast for Obsidian-vault. Ingen Obsidian-mappe ble funnet i repoet ved skrivetidspunktet, så denne filen ligger under `docs/` i påvente av at brukeren selv flytter/limer den inn i vaulten.*

Commit: `9bd4fe1` · Dato: 2026-07-27

## Ferdig

- Process Profiles og Hochkurz
- Style Engine-kalibrering (epsilon-toleranser, normalisert avvik, kritiske tak, Historisk Wiesn-Märzen)
- Water Chemistry V1
- Pantry V1
- Smart Handleliste V1
- Pantry backup/restore
- Lalvin EC-1118 og egendefinerte lageringredienser
- Felles gjærpakkeberegning for bryggedag, Pantry og Smart Handleliste

## Siste teststatus

357 tester — 0 skipped, 0 errors, 0 failures. 15 private oppskrifter (gitignoret, ikke del av repoet).

## Kjente åpne punkter

- Reell Wiesn-akseptansetest: **pågår** — teknisk flyt og humle/EC-1118 verifisert, malt og W-34/70 gjenstår
- `raw_data/malt_raw.json` har en uavklart, ucommittet scrape-arbeidskopi — venter på manuell butikkontroll
- `wip/gjaer-id-migrasjon`-branch har gammel base fra før Pantry/Smart Handleliste — må rebases før eventuell merge, røres ikke nå
- Kjent Witbier-signaturgap i Style Engine (kan gi for høyt numerisk treff uten belgisk signatur)
- Ingen automatisk pH-/syredosemodell (bevisst, manuelt målefelt i dag)

## Neste prioritet

1. Fullføre Wiesn-akseptansetesten
2. Bryggelogg V1
3. Equipment Profile
4. Butikksammenligning og maltvariantmodell
5. Migrering/avvikling av legacy-humlelager

## Viktige commit-hasher

- `19d84a3` — Pantry-motor
- `afab6a2` — Smart Handleliste-motor
- `781e0ad` — EC-1118 + egendefinerte lagervarer
- `f67d8d1` — felles gjærpakkeformel
- `0887377` / `9bd4fe1` — Pantry test isolation and backup hardening

Full detaljert status: `docs/PROJECT_STATUS_JULI_2026.md`. Full roadmap: `docs/ROADMAP.md`.
