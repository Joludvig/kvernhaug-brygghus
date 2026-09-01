# KBH Core Contract

Version: 2.0
Status: Active
Supersedes: `docs/development/KBH_CORE_CONTRACT_V1.md` (Version 1.0,
"KBH Core Contract", established 2026-08-15) as the governing Core
Contract, in its entirety, effective 2026-08-31. That document is
preserved as historical record — see its own updated header.

This is not a locked text. It is a versioned document. Changes to this
contract require explicit review and a version increment.

`docs/development/KBH_CORE_CONTRACT.md` is the canonical path for the
governing Core Contract — always the currently active version.
Historical contracts use a versioned filename
(`KBH_CORE_CONTRACT_V1.md`, etc.).

---

## Why V2 exists

V1 organized the project around two implementation workspaces —
Streamlit (desktop) and Web (mobile) — and assigned domain ownership
(masterdata, water chemistry, planning, brew log, learning) directly
to whichever workspace happened to implement it at the time.

The project has since grown functional areas that don't map cleanly
onto "which codebase currently renders this": canonical masterdata
needs an owner independent of any one app; brewing education
(Bryggeskole) and hands-on brewing practice (Brew Lab) are distinct
areas of work, not features bolted onto Web; and an AI/agent layer
(Sóti) now exists as a domain of its own.

V2 replaces the two-workspace ownership model with a five-domain
ownership model. It does not redesign the `.kbhrecipe`/`.kbhbrew` file
contracts, does not touch any schema, ID, or masterdata, and does not
change any code that exists today — see Section 4, "What this document
does not do."

---

## Section 1 — Domain ownership (governs)

| Domain | Owns |
|---|---|
| **Core** | Canonical masterdata, stable IDs, schemas, dataformats, versioning, provenance, validation, and shared semantic contracts. |
| **App/Web** | Product implementation, UI, local storage/cache/distribution, and user data. |
| **Bryggeskole** | Brewing research, explanation, and pedagogy. |
| **Brew Lab** | Actual brews, observations, and experiments. |
| **Sóti** | The AI/agent layer. |

A functional area belongs to exactly one domain for ownership
purposes, even where its code today happens to live inside the
Streamlit or Web codebase. Where existing code implements more than
one domain's concern in the same module today (for example: Streamlit
currently both computes canonical masterdata *and* renders product
UI), that is an implementation detail for a future, separately
authorized stabilization round — this document does not change any
code to match the new ownership lines.

---

## Section 2 — Principles carried forward from V1

The following V1 principles are still valid and are reused, one with a
narrowing noted below:

**Store what cannot be regenerated.**
(V1 §1, "Core philosophy") — actual measurements, the brewer's
reflections, frozen calculation inputs and historical snapshots are
stored.

**Default: don't store what can be recalculated.**
(V1 §1) — live-derived values (ABV, deviations, converted units,
engine-derived flavor) are not stored by default. This is a **default
principle, not an absolute prohibition**: it does not forbid an
explicit, deliberate historical snapshot that captures computed values
as a historical record for reproducibility. V1 itself already
establishes exactly this exception — "Computed historical values are
frozen into the `.kbhbrew` snapshot at brew time. They are never
frozen into the recipe." (V1 §10). This document does not design any
new snapshot, `.kbhbrew`, or schema solution — see Section 4.

**No single application owns the file format.**
(V1 §2, "KBH data ownership") — applications may read, write, display
and interpret a KBH file, but the file contract stands above the code
that happens to implement it today. Under V2 this principle now sits
explicitly with the **Core** domain rather than with either
implementation workspace.

**KBH files must be movable between systems without their identity or
meaning changing.**
(V1 §2) — unchanged.

---

## Section 3 — Status of the legacy `.kbhrecipe` technical contract

The `.kbhrecipe` file contract — wrapper shape, required/optional
payload fields, the whitelist rule, units/normalization, the
`recipeId`/`originRecipeId` identity policy, the passthrough law, "no
smart guessing", and the relationship to `.kbhbrew` — is documented in
full in `docs/development/KBH_CORE_CONTRACT_V1.md`, §3–§11.

- V1 documents the **operative legacy `.kbhrecipe` contract** that
  today's implementation (`modules/kbh_contract.py`,
  `ui/recipe_card.py`) still actually uses.
- That legacy contract is respected for backward compatibility — it is
  not changed by this document.
- It is **not** the governing Core architecture baseline. V1 is
  superseded in its entirety, including §3–§11, by this document.
- Its future — whether it is re-homed under the **Core** domain as-is,
  revised, or replaced — is decided only by a separate, explicitly
  authorized Core review. This document does not decide that now.
- No `.kbhrecipe` change is made by this document.

---

## Section 4 — What this document does not do

- It does not redefine, alter, or reimplement the `.kbhrecipe` file
  contract — see Section 3.
- It does not implement `.kbhbrew`.
- It does not touch pantry or custom-entity schema work.
- It does not change any masterdata file, any stable ID, or any user
  data.
- It does not change any App or Web code.

---

## Section 5 — Status of V1

`docs/development/KBH_CORE_CONTRACT_V1.md` (Version 1.0) is superseded
as the governing Core Contract by this document, in its entirety,
effective 2026-08-31. It is preserved as historical record — see
Section 3 above for the status of its §3–§11 legacy `.kbhrecipe`
contract specifically.

---

## Section 6 — Ownership vs. distribution (Core Stabilization Oppdrag 5)

Section 1's domain table already assigns canonical masterdata, stable
IDs, schemas/dataformats, versioning, provenance, and validation to
**Core**, and product implementation, UI, local storage/cache/
distribution, and user data to **App/Web**. This section makes four
boundary cases explicit that were implicit but not spelled out when
Section 1 was first written, ahead of `core/manifest.json` and
`core/status_provenance.json` (Core Stabilization Oppdrag 3–4):

- **Generated Web data** (`web/data/malt.json`, `humle.json`,
  `gjaer.json`, produced by `scripts/generate_web_data.py`) are
  **generated/distribution artifacts**, not a canonical master in their
  own right. They must be regenerable from the canonical Core source
  (`data/master_*.json`) and may carry their own checksum/build
  metadata (see `core/manifest.json`) without that giving them
  canonical ownership — the canonical dataset remains owned by Core,
  the artifact stays a distribution copy of it.
- **App's local storage of a user's concrete batch data** (a specific
  brew log entry, a specific pantry count) makes App the local
  authoritative store for *that user's data*, exactly as Section 1
  already says. It does **not** make App an owner of Core's schema or
  semantic contracts — those stay owned by Core regardless of which
  application happens to read or write a given file today.
- **Brew Lab** owns the observation, experiment, and interpretation
  that results when a user's batch data is used as hands-on brewing
  work — consistent with Section 1's existing "actual brews,
  observations, and experiments" — independent of which application's
  storage the underlying batch data physically lives in.
- **`core/manifest.json` and `core/status_provenance.json`** (Core
  Stabilization Oppdrag 3–4) are Core-owned artifacts, covered by the
  existing "versioning, provenance, validation" ownership grant in
  Section 1 — this section does not expand that grant, only names the
  files it now applies to.

This section documents existing ownership more explicitly; it does not
change any ownership assignment already made in Section 1, and it does
not move, migrate, or reimplement any file.

---

## Section 7 — Governance discoverability (Core-Chief authority order)

Foundation Audit 1.0 and the locked Kvernhaug charters that this Core
Stabilization phase implements are not repo files — they exist as
decisions made directly by Core-Chief in each Oppdrag's own governing
instructions. This section records the authority order those
instructions establish, so it is discoverable from the repo itself
rather than only from conversation history:

1. Locked Kvernhaug charters and newer explicit architecture decisions
   from Core-Chief.
2. This active Core Contract and other current repo governance docs
   (`docs/development/CORE_VERSIONING.md`,
   `docs/development/CORE_STATUS_PROVENANCE.md`,
   `docs/development/GIT_RULES.md`, etc.).
3. Relevant context in the separate Obsidian Vault
   (`C:\Vault\Kvernhaug Brygghus`) — see
   [VAULT.md](VAULT.md).
4. Historical/superseded documents (e.g.
   `KBH_CORE_CONTRACT_V1.md`).

A newer, explicit decision at a higher level always takes precedence
over an older document at the same or a lower level. **Git is
authoritative evidence of what actually changed** — a document
describing an intended state is not proof that the state was reached;
`git log`, `git diff`, and the actual current file contents are.

Foundation Audit 1.0 is referenced above as the decision basis for
Core Stabilization without reproducing its text here, since it does
not exist as a file in this repository — the goal of this section is
discoverability of the governance chain, not duplication of charter
text.
