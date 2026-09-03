# Core `.kbhbrew` V1 fixtures — normative, not legacy evidence

Unlike `tests/fixtures/legacy/` (frozen evidence of what existing code
*actually* produces, kept byte-stable against drift), the fixtures here
are **normative examples** of the ratified Core `.kbhbrew` V1 contract
([docs/development/CORE_KBHBREW_V1.md](../../../../docs/development/CORE_KBHBREW_V1.md),
schema: [core/kbhbrew_v1.schema.json](../../../../core/kbhbrew_v1.schema.json)).
They are allowed to evolve if the V1 contract itself is revised.

| File | Purpose |
|---|---|
| `minimal_v1.json` | The smallest record that satisfies the schema's `required` rules. |
| `full_v1.json` | A representative full brew: all five layers populated, full embedded ingredient/equipment snapshot, and the new normative `provenance.datasets` (Core manifest `schema_version`/`data_version`/`checksum`) shape — distinct from the legacy `provenance.masterdata` entry-count proxy still readable on `tests/fixtures/legacy/web/kbhbrew_v1.json`. |

Neither fixture carries a canonical `actual_abv` or V1 actual-process
field (Owner decisions #3/#5) — see
`tests/test_kbhbrew_schema_contract.py` for the tests that enforce this
and validate both files (plus the frozen legacy Web fixture) against
the schema.
