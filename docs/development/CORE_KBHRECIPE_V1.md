# Core `.kbhrecipe` V1 Contract

Version: 1.0
Status: Active
Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) — this
document is the active, normative Core precisification of the existing
`.kbhrecipe` V1 interchange contract. The full historical text remains
in [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md) §3–§11, which
this document does not replace or duplicate — it precisifies the parts
that were ambiguous or under-specified, and records the Core-Chief
decisions from Core Stabilization PRI 2/2A.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment. **This document does not
introduce `.kbhrecipe` V2** — `.kbhrecipe` remains `version: 1`
(KBHR-001).

---

## 1. Envelope

```
{
  format: "kbhrecipe",
  version: 1,
  exportedAt,
  generator,
  recipe: { ... }
}
```

`format` and `version` are required and normative. `exportedAt` and
`generator` are required but not currently validated for shape by
either implementation beyond presence in the writer output — a reader
must not fail if it can't interpret them further.

## 2. Required recipe fields

```
recipeSchemaVersion: 1
navn
volum
effektivitet
malt[]
humle[]
```

## 3. Optional known V1 fields

```
brygger
bryggeri
notater

gjaerId
gjaerCustom
attenuationOverride

valgtStil
bryggerStil

prosess

vann:
  kilde
  maal
  behandling
  maalinger

lagretDato
```

`lagretDato` is a Web-only field, not in the original V1 text (§3–§11).
Web has always written and read it internally, and recognizes it on
import — it is **not** passthrough data, since Web understands and owns
it. **QA-korreksjon (KBHR-009): recognizing a field on import is not the
same as exporting it.** `lagretDato` is Web's own "last assembled"
metadata (`app.js::samleOppskrift()` sets it fresh on every collection —
it is not something the user "has" in the recipe) and is **never**
written to a `.kbhrecipe` file. Concretely, `web/js/kbhrecipe.js`
separates this into three distinct sets:

- `KBHRECIPE_KJENTE_FELT` — fields Web *recognizes* on import (so they
  are not misfiled into passthrough); includes `lagretDato`.
- `KBHRECIPE_WEB_INTERNE_FELT` — the subset of the above that Web owns
  internally but must never write to a `.kbhrecipe` file; today just
  `lagretDato`.
- `KBHRECIPE_EKSPORTERBARE_FELT` — the actual writer whitelist
  (`KBHRECIPE_KJENTE_FELT` minus `KBHRECIPE_WEB_INTERNE_FELT` minus
  `KBHRECIPE_FORBUDTE_FELT`, §7) — this is what `_byggKjentPayload()`
  iterates over, not the raw known-fields list.

## 4. Units

Always metric: **liter, kilogram, gram, minutes, Celsius**. Display
units, locale preference, and UI formatting must never be stored in a
file. `effektivitet` is stored as a **percent number** in the file
(`75`), never a fraction (`0.75`) — the ×100 conversion happens only in
the adapter layer (App: `modules/kbh_contract.py`; Web: the field is
already a percent number in the DOM).

## 5. Writer rule — explicit whitelist

Both writers build the payload **field by field**, from an explicit
known-field list — never by copying or spreading a whole source object
into the file.

- App: `modules/kbh_contract.py::recipe_to_kbhrecipe_payload()` builds
  the payload key by key from `modules/recipe.py`'s internal Recipe
  Object.
- Web: `web/js/kbhrecipe.js::_byggKjentPayload()` builds the payload
  from `KBHRECIPE_KJENTE_FELT` (PRI 2A — previously
  `byggKbhRecipeInnhold()` wrapped the whole in-memory recipe object
  unchecked; this was closed in PRI 2A, see §9 below and the PRI 2A
  report for the before/after).

## 6. Passthrough rule (V1 §8)

An unknown **payload** field found on import — one not in the known
field list above, and not an explicitly forbidden field (§7) — must be
preserved unchanged through `read → edit → save/export`, even though
the application does not understand or display it.

Web implements this as a small, explicit, internal passthrough
mechanism (PRI 2A, KBHR-002):
- On import, `web/js/kbhrecipe.js::_normaliserOppskriftForImport()`
  collects every payload field not in `KBHRECIPE_KJENTE_FELT` and not
  in `KBHRECIPE_FORBUDTE_FELT` into one internal container field,
  `_kbhUkjenteFelt`.
- `_kbhUkjenteFelt` travels with the in-memory recipe object through
  the active-draft, `recipe_storage.js` save/load, and re-export paths
  exactly like any other field (no separate framework) — but it is
  **never itself** a V1 field: it is stripped out and only its
  *contents* are merged back into a fresh export, one key at a time,
  and only for keys a known/edited field doesn't already occupy.
- A field the user has actually edited (a known field) always wins
  over an old passthrough value with the same key.

Web does not need to understand `prosess` or `vann` to preserve them.
Any future, currently-unknown field is preserved the same way, with no
code change required for that new field specifically.

Passthrough exists for **data that arrived from outside** (an imported
file) that Web does not itself model — it is not a channel for Web's own
local metadata. The internal container field `_kbhUkjenteFelt` is never
itself part of the interchange format: it is not in
`KBHRECIPE_KJENTE_FELT`/`KBHRECIPE_EKSPORTERBARE_FELT`, so
`_byggKjentPayload()` never copies it, and `byggKbhRecipeInnhold()`
merges in only its *contents* (§7 lists it as a name explicitly skipped
during that merge, alongside the forbidden fields) — the key itself
never appears in an exported file (regression-tested, see PRI 2A QA-
korreksjon report).

App does not currently have a passthrough mechanism (no reader — see
§10). This document does not change that.

## 7. Forbidden export fields

These must **never** appear in an exported `.kbhrecipe` file, and must
**never** be reintroduced via passthrough, regardless of what an
import or a hand-edited local record contains:

- **`recipeId`** (or any local storage identity) — V1 §6: a shareable
  `.kbhrecipe` must never contain the receiving/sending system's local
  identity.
- **`stats`** — any engine-computed result (OG/FG/ABV/IBU/EBC).
- **`flavor_profile`** — engine-computed sensory result.
- Any other value computed by the calculation/flavor engine.

Web enforces this at two independent points (capture-time exclusion
during import, and merge-time exclusion during export) so a forbidden
field cannot leak even if it somehow ended up inside the passthrough
container itself (e.g. a hand-edited local draft).

## 8. Version policy

- Envelope `version: 1` is supported.
- Any other envelope `version` value is **rejected explicitly**, with
  a clear message — never guessed, never silently coerced.
  `version < 1`, `version > 1`, non-numeric, and missing are all
  rejected the same way today (Web: `parseKbhRecipeInnhold()`).
  **No support for a hypothetical `version: 0` is added by this
  document** (KBHR-007).
- `format` must equal `"kbhrecipe"` exactly, or the file falls back to
  the legacy raw-JSON heuristic (§11) rather than being read as a V1
  envelope.

## 9. `recipeSchemaVersion` — known gap, not fixed here

`recipeSchemaVersion` travels **inside** the payload (with the
payload, not the envelope) so it survives extraction into a
`.kbhrecipe` file or a future `.kbhbrew` snapshot on its own.

**Today's actual behavior (unchanged by PRI 2A):**
`web/js/recipe_storage.js::_normalisertRecipe()` unconditionally
overwrites `recipeSchemaVersion` to the current
`RECIPE_SCHEMA_VERSION` on every save, regardless of what value was
present on the incoming object (imported, or from an older stored
row). An unknown or higher `recipeSchemaVersion` is therefore never
detected or preserved — it is silently normalized away.

**Normative rule going forward:** an unknown or higher
`recipeSchemaVersion` must never be silently downgraded/overwritten.
**The correction to Web's behavior is out of scope for PRI 2A and is
deferred to PRI 2B** (KBHR-008). This section documents the rule and
the current gap; it does not change any code.

## 10. Custom ingredient boundary

V1's original text only names `gjaerCustom`. Custom malt and custom
hops are not mentioned in the historical text at all, but Web has
represented them for some time (`malt[].custom`, `humle[].custom`)
with locally-generated IDs (`egen_malt_*`, `egen_humle_*`).

**This document confirms only that:** existing, self-describing
custom-ingredient data (a `custom` sub-object carrying enough to
display and calculate without a master-data lookup) may continue to be
carried in a V1 `.kbhrecipe` file. **Global custom-ingredient identity
is explicitly not standardized here** — that is owned by a future PRI 4
(custom entity/pantry identity harmonization). PRI 2A does not change
the shape of `custom` sub-objects, does not give custom ingredients a
Core-wide ID scheme, and does not touch App's (currently absent)
custom-ingredient representation.

## 11. Unknown ingredient IDs

An `id` in `malt[]`/`humle[]` that does not resolve against loaded
master/custom data must **never** be fuzzy-matched, substituted with a
similar-looking ID, or silently defaulted (V1 §9, "no smart
guessing"). Today's actual behavior on Web is that an unresolved ID
simply contributes nothing to the calculation (silently, not visibly
flagged) — this is a known gap (PRI 2 report, finding G4), not
addressed by this document or by PRI 2A.

## 12. Legacy raw-JSON fallback

A file without the `{format, version, ...}` envelope is still accepted
if it structurally looks like a recipe (`_erGyldigOppskriftForm()`
checks for at least one known top-level field). This existing,
undocumented-in-V1 fallback is preserved as-is by this document — it
predates the wrapper format and lets old exports keep working.

## 13. What this document does not do

- Does not define `.kbhrecipe` V2, and does not add a new envelope
  version.
- Does not implement App import.
- Does not implement `recipeId`/`originRecipeId` end-to-end identity.
- Does not correct the `recipeSchemaVersion` overwrite (§9) — deferred
  to PRI 2B.
- Does not standardize custom-ingredient identity — owned by PRI 4.
- Does not touch `.kbhbrew`.
