# Legacy fixtures — Core Stabilization Oppdrag 2B

Disse fixturene fryser dagens **faktiske** datakontrakter, slik de er
implementert i kode i dag, FØR Core Stabilization sitt schema-/
manifestarbeid begynner.

- De er **compatibility evidence** — bevis på hva dagens kode faktisk
  gjør — ikke nødvendigvis ønsket fremtidig design.
- Syntetiske fixtures (`app/`, `kbhrecipe/`, `web/`) inneholder INGEN
  private brukerdata. Alt innhold er oppdiktet eller hentet fra ekte,
  ikke-private, allerede git-tracket bibliotekinnhold i produksjonskode
  (f.eks. `modules/process_profiles.py::STANDARDPROFILER["enkel_infusjon"]`,
  `modules/water_chemistry.py::SALTER["gips"]`).
- `masterdata/`-subsettene ble fanget FRA canonical
  `data/master_malt.json` / `master_humle_v2.json` / `master_gjaer_v2.json`
  ved capture-commiten dokumentert under, med de opprinnelige, stabile
  dict-key-IDene og verdiene urørt. De er deretter frosset — se
  CAPTURE PROVENANCE under for regelen om at de IKKE oppdateres bare
  fordi canonical master endres senere.
- Web brygg-/`.kbhbrew`-fixturene (`web/brew_store_v1.json`,
  `web/kbhbrew_v1.json`) dokumenterer dagens eksisterende Web-
  bryggmodell (`web/js/brew_storage.js`). De gjør IKKE denne modellen
  til canonical Core-kontrakt — det er en egen, separat beslutning
  ingen fixture her tar stilling til.
- Fixturene skal **ikke ryddes opp** når nye schemas innføres.
  Fremtidig migrering/bakoverkompatibilitet skal testes MOT disse
  filene, ikke rundt dem.

## Struktur

| Mappe | Kontrakt |
|---|---|
| `masterdata/` | Canonical malt-/humle-/gjær-master (subset, frosset — se CAPTURE PROVENANCE) |
| `app/` | App (Streamlit) native oppskrift + bryggelogg + pantry (syntetisk/frosset) |
| `kbhrecipe/` | `.kbhrecipe` V1 — faktisk output fra `modules/kbh_contract.py` |
| `web/` | Web localStorage-kontrakter (oppskrift, brygg/`.kbhbrew`, pantry) |

Se `tests/test_legacy_fixtures.py` for integritetstestene som håndhever
disse påstandene.

## CAPTURE PROVENANCE — frosset historisk evidens, IKKE en live speiling

**Regel:** legacy-fixturene i `masterdata/` og `app/pantry_v1.json`
skal **IKKE** oppdateres bare fordi dagens canonical masterdata eller
`data/pantry.example.json` senere endres. De er et frosset øyeblikksbilde
tatt ved capture-commiten under, ikke et vindu inn i "master slik den
er akkurat nå". En fremtidig, legitim Core-masteroppdatering skal
**aldri** gjøre disse fixturene ugyldige eller kreve at de oppdateres i
samme runde — testene i `tests/test_legacy_fixtures.py` verifiserer
fixturene MOT SEG SELV (eksplisitte forventede IDs/shapes + faste
SHA-256-hasher av fixture-filene), ikke mot den levende
`data/master_*.json`/`data/pantry.example.json`.

**Capture commit:** `3ed82cf42c8bb4b0c53e8c74b21c965e1699775a`

### `masterdata/malt.json`
- Source path: `data/master_malt.json`
- Captured stable IDs: `bohemian_pilsner_floor`, `crystal_maple_carapils`,
  `weyermann_pilsner`, `vienna`, `flaket_havre`
- SHA-256 (fixture-filen som helhet, UTF-8, LF): `1634ae503e66f8df5123f0ab713abe616da3a5c8385f8a775c55337cbafaeddd`

### `masterdata/humle.json`
- Source path: `data/master_humle_v2.json`
- Captured stable IDs: `amarillo`, `comet`, `east_kent_goldings`, `tettnang`
- SHA-256: `47ce1187b2e51c64df1aced5010755fb6138b347ceb3afe814619bf5063c7e61`

### `masterdata/gjaer.json`
- Source path: `data/master_gjaer_v2.json`
- Captured stable IDs: `saflager_w3470`, `wlp_810`, `lalvin_ec1118`,
  `lalbrew_diamond_lager`
- SHA-256: `54e8c5f84324a3af256ab9913e5df93598a948c36c2b0f59ed97a0dfe434f477`

### `app/pantry_v1.json`
- Source path: `data/pantry.example.json` (allerede eksplisitt sanert,
  git-tracket, ingen privat brukerdata — eksakt kopi tillatt)
- SHA-256: `8457221a4e7c5b26304e7d864569b9d142b91ea177cb95ade9a140e566222f60`
- `data/pantry.example.json` selv forblir det **levende** eksempelet
  (kan endres av fremtidige runder); `app/pantry_v1.json` er den
  **frosne** Phase 0-fixturen og endres ikke i takt med den.

Alle fire hasher er verifisert i `tests/test_legacy_fixtures.py` og
regnes på nytt fra fixture-filen hver gang testen kjører — de beviser
at fixture-INNHOLDET ikke har driftet siden capture, uavhengig av hva
kildefilene inneholder i dag.
