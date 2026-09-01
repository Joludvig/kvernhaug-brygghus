# Core Versioning Model

Version: 1.0
Status: Active
Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) — this
document defines the version model for the **Core** domain established
there. It does not redefine domain ownership.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## Purpose

Defines the minimum, explicit, machine-readable version model Core
datasets and artifacts use. This is the fundament the manifest
(`core/manifest.json`) is built on — not a migration, not a redesign of
any existing data.

---

## 1. `schema_version`

The version of a dataset's **structure/contract/semantic shape**.

Changes when a consumer must understand a new or changed
structure/semantics to read the data correctly — a field renamed,
removed, retyped, or given new meaning.

Does **not** change when records are merely added, corrected, or
removed within the same structure.

## 2. `data_version`

The version of the **canonical dataset's content**, within the same
`schema_version`.

Can change when records are corrected, improved, added, or removed —
without the schema necessarily changing. `schema_version` and
`data_version` are independent counters; bumping one never implies
bumping the other.

## 3. `generated_at`

The timestamp a distribution/generated artifact was **produced**.

Must never be confused with when the underlying data was
professionally/factually verified — see `verified_at`. An artifact can
be regenerated (new `generated_at`) from unchanged, already-verified
source data (unchanged `verified_at`).

## 4. `verified_at`

The timestamp relevant canonical data/revision was last
professionally/factually verified, **if known**.

`null` when not known. The existing legacy per-entry `verified: true`/
`false` boolean in `data/master_*.json` records a one-time human review
decision on a single ingredient entry — it is not a timestamp and does
not by itself establish when (or whether) the dataset as a whole was
last verified. `verified_at` must never be fabricated or backfilled
from that legacy boolean.

## 5. `provenance`

The manifest can **reference** provenance. The detailed
provenance/status schema (what a reference actually points to, how it
relates to the legacy `verified` boolean, how status is tracked) is
defined in a later, separate round. This document and the baseline
manifest deliberately leave `provenance` as a reserved placeholder
(`null`) — not designed further here.

## 6. `checksum` / `build_id` (optional)

**`checksum`** — optional content-integrity metadata for a file
(`{"algorithm": "sha256", "value": "<hex>"}`). A checksum proves the
file's *bytes* are what they were recorded as; it says nothing about
whether the content is factually correct. Content correctness is what
`verified_at` is for.

**`build_id`** — optional, identifies a specific generation/build run
of an artifact. It identifies *which run produced this file*, not the
schema or data version of what it contains.

Neither field is required. Omit rather than fabricate: a checksum
absent from today's generation tooling (e.g. `scripts/generate_web_data.py`
does not currently emit a build id) is left out, not invented.

**Checksum in the active Core manifest is live integrity metadata. A
mismatch means the manifest and referenced artifact are out of sync
and requires explicit review.**

This is distinct from the legacy fixtures under `tests/fixtures/legacy/`,
which freeze historical evidence and are deliberately verified against
themselves, never against a live source (see that directory's README).
`core/manifest.json` describes the *current* Core state, so its
checksums are expected to track the files they point to — a stale
checksum is a real signal, not noise.

A checksum mismatch is a **drift signal, not a verdict**:
- a changed checksum is **not**, by itself, automatic proof of a
  semantic/factual change to the dataset — it only proves the file's
  bytes changed;
- `data_version` is bumped when a dataset changes **semantically**
  (records corrected, added, removed — see §2 above), a decision made
  by whoever changes the data, not derived from the checksum;
- a pure byte-level/formatting change (re-serialization, whitespace,
  key ordering) can change the checksum without necessarily requiring
  a `data_version` bump;
- no automation (generator hook, CI check, auto-update) recomputes or
  reconciles the manifest's checksums today — keeping them in sync is
  a manual review step for now, deliberately not built in this round.

---

## Versioning rules

- **`schema_version` and `data_version` are plain integers**, starting
  at `1`, incremented by 1. This matches the version convention already
  used throughout the codebase (`modules/pantry.py::SCHEMA_VERSION`,
  and every Web `localStorage` contract: `RECIPE_SCHEMA_VERSION`,
  `OPPSKRIFT_STORE_VERSION`, `PANTRY_VERSION`, `UTSTYR_VERSION`,
  `BREW_STORE_VERSION`, `BREW_FIL_VERSION`, `KBHRECIPE_VERSION`,
  `KBH_ENGINE_VERSION` — all plain integers, none SemVer). No new
  versioning scheme is introduced; this is the established convention,
  reused.
- **SemVer is not used.** Nothing about Core datasets today needs
  independent major/minor/patch signaling — a single incrementing
  integer per concept is simpler and matches what the rest of the
  system already does. Reconsider only if a real, demonstrated need
  arises.
- **Field types:**
  | Field | Type |
  |---|---|
  | `schema_version` | integer |
  | `data_version` | integer |
  | `generated_at` | ISO 8601 string, or `null` |
  | `verified_at` | ISO 8601 string, or `null` |
  | `provenance` | reserved — `null` (Oppdrag 4 defines the shape) |
  | `checksum` | `{algorithm: opaque string, value: opaque hex string}`, or `null` |
  | `build_id` | opaque string, or `null` |
  | dataset key / `name` | opaque string |
  | `source_path` / artifact `path` | opaque string (repo-relative path) |
  | `type` | opaque string enum (`"canonical_dataset"` \| `"generated_artifact"`) |

  "Opaque string" means: compared for equality only, never parsed as a
  number or interpreted structurally.
- **Backward compatibility:** a consumer that only understands a lower
  `schema_version` must be able to detect the mismatch (the field is
  always present) and refuse or degrade gracefully, never silently
  misread newer data. This mirrors the existing `.kbhrecipe`
  `version`-check pattern in `web/js/kbhrecipe.js`.
- **Baseline values:** where no established `data_version` exists yet
  for a dataset (true for all of today's canonical masterdata),
  `data_version: 1` is used as an explicit **stabilization baseline** —
  not a claim that this is the dataset's first-ever revision, only that
  it is the first revision tracked under this model.

---

## Relationship to existing legacy contracts

This model governs the **Core** manifest introduced in this round. It
does not change, migrate, or reinterpret:
- `data/master_malt.json` / `master_humle_v2.json` / `master_gjaer_v2.json`
  (untouched — still the canonical files, still keyed by their existing
  stable IDs)
- the legacy `verified`/`source` fields inside those files (still
  exactly what they were — see `tests/fixtures/legacy/README.md` for
  the frozen evidence of their current shape)
- `.kbhrecipe`/`.kbhbrew` (untouched, per
  [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md) §3–§11)
