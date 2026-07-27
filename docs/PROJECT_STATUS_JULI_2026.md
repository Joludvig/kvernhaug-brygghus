# Kvernhaug Brygghus — Prosjektstatus (Juli 2026)

*Dato: 2026-07-27*
*Gjeldende master-commit: `9bd4fe1`*
*Testantall: 357 tester — 0 skipped, 0 errors, 0 failures*
*Python-filer i repoet: 85*
*Lagrede private oppskrifter: 15 (kun antall — filnavn og innhold er ikke del av denne rapporten)*

Dette dokumentet erstatter ikke `docs/PROJECT_STATUS_JUNI_2026.md`, som beholdes som historikk.

---

## Kort arkitekturoversikt

- **Streamlit-app** (`app.py`) organisert i fire tabs: Oppskrift, Innkjøp & Lager, Bryggdag, Verktøy.
- **`modules/`** — beregningslogikk (oppskriftskontekst, bryggedag, style engine, vannkjemi, pantry, smart handleliste, scraper/normalisering).
- **`ui/`** — én panelfil per fane-seksjon, rendrer mot `modules/`.
- **`data/`** — kuraterte masterdatabaser (malt/humle/gjær) + private, gitignorede runtime-filer (`pantry.json`, `humle_lager.json`, `equipment.json`, vannmål).
- **`recipes/`** — brukerens lagrede oppskrifter. Gitignoret; ikke delt i det offentlige repoet.
- **`tests/`** — 23 testfiler, inkludert committede fixtures (sanitiserte oppskrift-kopier uten personlig innhold) slik at ingen test er avhengig av private, lokale data.

---

## Ferdige hovedmoduler

| Område | Status |
|---|---|
| Oppskriftsbygger, skalering, bryggedagsark/A4 | Ferdig |
| Prosessprofiler (inkl. Hochkurz) | Ferdig |
| Gjærpakkeberegning — felles formel for bryggedag, Pantry og Smart Handleliste | Ferdig |
| Style Engine (epsilon-toleranser, normalisert avvik, kritiske tak, numerisk nærmeste stil, «Historisk Wiesn-Märzen» som egen Kvernhaug-kategori) | Ferdig |
| Water Chemistry V1 (kildevann, målprofilbibliotek, salter, solver, full/delvis/uoppnåelig-klassifisering, mesk/skyll-fordeling, manuelt pH-felt, eksport) | Ferdig |
| Pantry V1 (flere ingredienstyper, egendefinerte varer, EC-1118, backup/restore, sikker testisolasjon) | Ferdig |
| Smart Handleliste V1 (Pantry som sannhetskilde, reell mangel, kjøpsforslag, rest etter kjøp, prisestimat, knapp-margin, skalering) | Ferdig |
| Legacy humlelager + gammel handleliste | Beholdt, tydelig separert, ikke synkronisert med Pantry |

## Pågår / akseptansetesting

**Reell brukerakseptanse med Wiesn-lagerdata** — delvis gjennomført, ikke fullført:
- Teknisk lager-/handlelisteflyt er verifisert med produksjonskode.
- Ekte humlebeholdning og Lalvin EC-1118 er registrert i Pantry.
- Fortsatt mangler: malt-registrering og registrering av den faktiske gjæren som brukes i Wiesn-oppskriften (W-34/70), så en fullstendig lagerkontroll er ikke gjennomført ennå.

---

## Nylige milepæler (commit-hasher)

- `19d84a3` — Pantry-motor
- `8022257` — Pantry-UI (📦 Lager)
- `afab6a2` — Smart Handleliste-motor
- `d977992` — Smart Handleliste-UI
- `781e0ad` — Lalvin EC-1118 + egendefinerte lagervarer
- `f67d8d1` — felles gjærpakkeformel (bryggedag/Pantry/Smart Handleliste)
- `ec25629` — regresjonstest mot ekte 23L Wiesn-batch (ikke 20L)
- `72e6b77`, `0887377`, `9bd4fe1` — **Pantry test isolation and backup hardening** (se eget avsnitt under)

---

## Pantry test isolation and backup hardening

En destruktiv test-cleanup i testsuiten ble identifisert og fjernet. Testene bruker nå utelukkende midlertidige kataloger (`TemporaryDirectory` + miljøvariabel-basert sti-overstyring) og rører aldri den ekte, private `data/pantry.json` direkte. Der en test likevel må kjøre mot en ekte, eksisterende Pantry-fil, sammenlignes filinnholdet byte-for-byte før og etter kjøring for å garantere at ingenting er endret.

Som et permanent sikkerhetsnett er det i tillegg innført:
- Automatisk, rullerende backup ved hver reell endring av Pantry (oppdatering, sletting, hurtigjustering, full overskriving, import).
- En egen «Gjenopprett fra backup»-funksjon i UI-et, med forhåndsvisning og eksplisitt bekreftelse — ingen automatisk gjenoppretting.

---

## Private datafiler (uten innhold/verdier)

- `data/pantry.json` — inneholder reelle, private lagerdata. Gitignoret.
- `data/pantry.json.backup_*` — rullerende backupfiler av samme fil. Gitignoret.
- `recipes/*.json` — 15 private oppskrifter. Gitignoret.
- `data/humle_lager.json`, `data/equipment.json` — private, gitignorede runtime-filer.

---

## Kjente svakheter

- Belgisk Witbier kan i enkelte tilfeller få et for høyt numerisk stiltreff ved ren tallmessig overlapp, uten at en reell belgisk gjærsignatur er til stede.
- Vannkjemi V1 har bevisst ingen automatisk pH-/syredosemodell — pH er et manuelt målefelt, ikke en beregnet anbefaling.
- Legacy humlelager og gammel handleliste er ikke koblet mot Pantry og kan avvike fra den reelle beholdningen.

## Teknisk gjeld

- `raw_data/malt_raw.json` har en ucommittet, uavklart scrape-arbeidskopi: hovedsakelig rekkefølgeendringer, ett nytt Spraymalt-produkt, ett manglende Crystal Maple/Carapils-produkt, og én Bohemian Pilsner-side fanget med en annen variant/pakningsstørrelse enn i dagens master. Skal **ikke** committes eller reverteres før manuell butikkontroll.
- `master_malt.json` er strukturelt v2-format, men beholder et eldre filnavn (dokumentert siden juni 2026-statusen); ingen rename planlagt før en bredere datarefaktorering.
- `wip/gjaer-id-migrasjon` finnes som egen branch, men har en gammel base **fra før** Pantry/Smart Handleliste-arbeidet. Den må rebases og gjennomgås grundig før en eventuell merge vurderes, og skal ikke røres nå.

## Eksplisitt parkerte funksjoner

- Etikettgenerator
- Egen PDF-eksportmotor
- Avansert meske-pH-/syredosemodell (automatisk)
- Automatisk lagerreservasjon
- Lagertransaksjonshistorikk
- Automatisk bestilling uten offentlig leverandør-API (permanent avvist i denne formen)

## Anbefalt neste prioritet

1. Fullføre den pågående Wiesn-akseptansetesten (registrere malt og W-34/70, bekrefte full lagerkontroll).
2. Bryggelogg V1.
3. Equipment Profile.
4. Butikksammenligning og maltvariantmodell.
5. Migrering og avvikling av legacy-humlelager.

Se `docs/ROADMAP.md` for full roadmap.
