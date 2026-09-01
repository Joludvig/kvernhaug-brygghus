# Core Status & Provenance Model

Version: 1.0
Status: Active
Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) —
this document defines the status and provenance model for the **Core**
domain established there. See also
[CORE_VERSIONING.md](CORE_VERSIONING.md) (`schema_version`,
`data_version`, `generated_at`, `verified_at`, `checksum`/`build_id`) —
this document is the deferred definition of the `provenance` field that
document deliberately left as a reserved placeholder.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## Purpose

Defines the minimum explicit model Core uses to answer three separate
questions about any piece of Core data or claim:

1. **Provenance** — where did this information come from?
2. **Status** — how far has Kvernhaug quality-assured it?
3. **Claim/evidence type** — what kind of statement is this (documented
   fact, observation, interpretation, assumption, or proposal)?

These three are deliberately kept separate. None of them is a
substitute for either of the others — see "Why these are not merged"
below.

This document does **not** migrate any existing masterdata, does not
change any legacy `verified` field, and does not build a workflow
engine, crawler, import pipeline, or review UI. It documents semantics
only. See `core/status_provenance.json` for the same model in
machine-readable form.

---

## 1. Status model

Core status describes how far a piece of data has been
quality-assured. It is a property of a *specific Core entry/claim*, not
of an entire dataset file.

| Status | Meaning |
|---|---|
| `draft` | Proposed or in progress. Must **not** be treated as verified canonical truth by products or agents. |
| `reviewed` | Reviewed by a human/professional process. Not necessarily documented well enough yet to be `verified`. |
| `verified` | Approved as Core's best verified representation **at this point in time**. Requires sufficient provenance for the kind of claim/data involved (see §3). Does **not** mean eternal truth — see the Core Contract's principle that canonical master is "the best verified representation Kvernhaug has now." |
| `deprecated` | Must not be used as the current canonical representation. Kept when history/backward-compatibility requires it. Should reference a replacement/superseding entry where relevant. |

### 1.1 Allowed transitions

```
draft → reviewed → verified → deprecated
```

Only these three forward transitions are defined:

- `draft → reviewed`
- `reviewed → verified`
- `verified → deprecated`

No workflow engine is built for this. This document defines the
semantics only; nothing in this round enforces or automates a
transition.

### 1.2 What is deliberately not decided here

Rollback/reopen transitions (e.g. `reviewed → draft`,
`verified → reviewed`, un-deprecating an entry) are **not** defined in
this round. If a real need for one arises, it should be reported and
decided explicitly then — not pre-designed speculatively here.

---

## 2. Provenance — minimum record

A technology-independent provenance record. Not tied to Python, JS, or
any storage format — any Core component may represent these fields
however fits its own storage.

| Field | Type | Meaning |
|---|---|---|
| `source_type` | opaque string, or `null` | What kind of source this came from (e.g. supplier datasheet, professional literature, crawler suggestion, human tasting note, sensor reading). Core does not enumerate a fixed vocabulary for this field in this round. |
| `source_ref` | opaque string, or `null` | A reference/pointer to the actual source (URL, document name, file path, citation) — not the source content itself. |
| `source_date` | ISO 8601 date, or `null` | The date the *source itself* is dated to, if known — distinct from when Kvernhaug captured/reviewed/verified it. |
| `captured_at` | ISO 8601 timestamp, or `null` | When Kvernhaug recorded this claim/entry into Core. Named `captured_at` for consistency with the "capture" terminology already established in `tests/fixtures/legacy/README.md`'s CAPTURE PROVENANCE section, rather than introducing a second name (`recorded_at`) for the same concept. |
| `reviewed_at` | ISO 8601 timestamp, or `null` | When the entry reached `reviewed` status, if known. |
| `verified_at` | ISO 8601 timestamp, or `null` | When the entry reached `verified` status, if known. Same semantics as `verified_at` in [CORE_VERSIONING.md](CORE_VERSIONING.md) §4, applied here at the level of an individual provenance record rather than a whole dataset. Must never be fabricated or backfilled — `null` when not known. |
| `reviewer_ref` | opaque string, or `null` | A reference/identifier for whoever (or whatever process) reviewed/verified the entry, where appropriate. Core does not define an identity system here — this is a free-form reference (a name, a role, a link to a review note), not a foreign key into some registry that does not yet exist. |
| `notes` | string, or `null` | Free-text context. |

`confidence` is deliberately **not** part of this record — see "Why
these are not merged" below. Nothing in this round adds a `confidence`
field anywhere.

---

## 3. Claim/evidence type

A separate, explicit classification of *what kind of statement* a
piece of Core data represents:

| Value | Meaning |
|---|---|
| `documented_fact` | A directly documented, sourced fact (e.g. a value taken from a supplier datasheet). |
| `documented_observation` | A recorded observation, not necessarily a settled fact (e.g. Brew Lab sensory notes on a specific batch — an observation, not automatically `documented_fact`). |
| `interpretation` | A reasoned interpretation of underlying facts/observations. |
| `assumption` | An explicit, stated assumption, not yet confirmed. |
| `proposal` | A suggested change or addition (e.g. from a future crawler/import step) that has not been reviewed or accepted. |

### 3.1 Relationship to the existing Vault Canon `source_layer` model

The project's separate Obsidian Vault (`C:\Vault\Kvernhaug Brygghus`,
outside this repository — see
[VAULT.md](VAULT.md)) already has its own, pre-existing `source_layer`
field (`fact` / `probable` / `canon`) and its own `status` lifecycle
(`idea → draft → review → approved → deprecated → archived`, defined
in `Canon Rules.md`), used for Canon notes about the real place,
history, and brand identity.

This is a genuinely different model, in a different domain, from the
one defined here: the Vault's model governs narrative/identity/
historical claims (outside this repository, not part of the Core
domain), while this document governs Core brewing masterdata claims
(malt/humle/gjær and future Core datasets, inside this repository).
Nothing in `KBH_CORE_CONTRACT.md` (v2.0) or elsewhere states that Core
must reuse the Vault's vocabulary, and the two vocabularies do not
actually overlap in meaning (`reviewed`/`verified` here vs.
`review`/`approved` there; a 5-value `documented_fact`/…/`proposal`
scale here vs. a 3-value `fact`/`probable`/`canon` scale there).

No attempt was made to harmonize the two in this round — that would be
a real architecture decision (whether Core's status/claim model should
ever be unified with the Vault's Canon model) with no basis in current
governance to make unprompted. Flagged explicitly in the Oppdrag 4
report as a non-blocking observation for Core-Chief awareness, not
treated as a blocking conflict, since the two apply to disjoint data
domains today.

---

## 4. Why these are not merged

Provenance, status, and claim/evidence type answer different
questions and must not collapse into one field:

- Two entries can have identical **provenance** (same source, same
  capture date) but different **status** (one `reviewed`, one still
  `draft` pending a second reviewer).
- Two entries can have the same **status** (`verified`) but different
  **claim/evidence type** (one a `documented_fact` from a datasheet,
  one a `documented_observation` from a tasting panel) — both can be
  legitimately `verified` without becoming the same kind of claim.
- `confidence` was considered and deliberately excluded: a numeric or
  qualitative confidence score would either duplicate `status`
  (how far something has been quality-assured) or duplicate
  `claim/evidence type` (what kind of claim it is), creating double
  semantics for the same underlying question. If a genuine need for a
  distinct confidence axis emerges later, it should be proposed and
  reviewed explicitly then, not folded in here.

---

## 5. Legacy `verified` policy

`data/master_malt.json`, `master_humle_v2.json`, and
`master_gjaer_v2.json` carry a legacy per-entry `verified: true`/
`false` boolean with **uneven coverage** (spot-checked read-only for
this round: malt — 53/53 entries carry `verified`, all `true`; humle —
60/60 entries carry `verified`, 46 `true` / 14 `false`; gjær — 81/103
entries carry `verified`, none `false`, 22 entries have no `verified`
field at all). It is set only by `ui/review_panel.py` on manual human
approval of a new entry and is not read/consumed by any other logic in
`modules/` or `ui/` today.

Explicit rules, effective immediately:

- `verified: true` does **not** automatically mean Core status
  `verified`.
- `verified: false` does **not** automatically mean Core status
  `draft`.
- A missing `verified` field does **not** automatically mean any new
  Core status.
- Migrating any legacy entry to a Core status/provenance record
  requires a separate, explicit rule and a provenance review — it is
  not implied or performed by this document.
- The existing legacy `verified` field is left completely untouched in
  this phase; no masterdata file is modified by Oppdrag 4.

This mirrors, and is machine-testable via, `legacy_verified_mapping`
in `core/status_provenance.json` (§6 below).

---

## 6. Machine-readable policy

`core/status_provenance.json` expresses the status values, allowed
transitions, claim/evidence types, provenance field definitions, and
the legacy-verified-mapping rule above in machine-readable form.
`legacy_verified_mapping` is set to `"requires_review"` — not
`"none"` — meaning: no automatic mapping exists today, and any future
mapping requires an explicit, separate reviewed rule; it does not mean
a mapping can never exist.

`policy_schema_version` follows the same plain-integer convention
established in [CORE_VERSIONING.md](CORE_VERSIONING.md) (no SemVer).

---

## 7. What this document does not do

- Does not migrate `data/master_malt.json`, `master_humle_v2.json`, or
  `master_gjaer_v2.json`, and does not add any status/provenance field
  to them.
- Does not set any existing masterdata entry to Core status `verified`
  (or any other Core status) — no entry has a Core status yet; this
  document only defines what the values *would* mean once assigned.
- Does not fabricate `verified_at`, `reviewed_at`, or `captured_at`
  for any existing data.
- Does not build a crawler, import pipeline, review UI, or workflow
  engine.
- Does not harmonize App/Web, change `.kbhrecipe`/`.kbhbrew`, change
  pantry/custom entities, or change stable IDs.
- Does not build a Sóti integration or introduce RAG.
- Does not attempt to harmonize this model with the Vault's Canon
  `source_layer`/`status` model (see §3.1).
