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

**PR #3 Chief review correction: `bryggerStil`, `prosess`, and `vann`
are *not* in Web's `KBHRECIPE_KJENTE_FELT`, even though they are valid
optional V1 fields (this section).** They previously were, which caused
a real regression: Web has no dedicated UI/state for any of the three
(no DOM field, no module variable — neither `samleOppskrift()` nor
`_gjenopprettOppskrift()` in `app.js` handles them), so classifying
them as "known" only meant `_normaliserOppskriftForImport()` did *not*
capture them into passthrough — and since nothing else in Web retained
them either, they were silently dropped somewhere between import and
the next `samleOppskrift()` call, contradicting the passthrough/
losslessness rule below (§6). **Fix:** Web now treats these three
exactly like any genuinely unknown future field — captured into and
carried opaquely via `_kbhUkjenteFelt` (§6) — which `app.js` already
correctly carries through the full edit/save/export cycle for any such
field. No change to `app.js` was needed. On the App side, the
equivalent fields are natively modeled (`bryggerStil` → `brygger_stil`,
`prosess` → `process_profile`, `vann.*` → `water_*`, see §13) — this is
a Web-implementation-specific gap being closed, not a Core V1 rule
change.

## 4. Units

Always metric: **liter, kilogram, gram, minutes, Celsius**. Display
units, locale preference, and UI formatting must never be stored in a
file. `effektivitet` is stored as a **percent number** in the file
(`75`), never a fraction (`0.75`) — the ×100 conversion happens only in
the adapter layer (App: `modules/kbh_contract.py`; Web: the field is
already a percent number in the DOM).

**`effektivitet` is recipe-scoped, not equipment-scoped (PRI 2C0,
KBHR-019).** A concrete recipe's `effektivitet` is that recipe's own
value — an equipment/brewhouse profile (App:
`modules/equipment.py::last_equipment()`; a global, App-local setting
with no `.kbhrecipe` representation of its own) is only ever a
**default for a genuinely new recipe that has no value of its own**.
Opening/importing a recipe must never overwrite the global equipment
profile, and must never silently replace a recipe's own `efficiency`
with the equipment default — see
`modules/recipe.py::resolve_recipe_efficiency()` and
`modules/recipe_context.py`, and the PRI 2C0 report for the concrete,
proven before/after behavior. This section documents the policy; it
does not change the wire format — `effektivitet` was already a
required payload field (§2).

## 5. Writer rule — explicit whitelist

Both writers build the payload **field by field**, from an explicit
known-field list — never by copying or spreading a whole source object
into the file.

- App: `modules/kbh_contract.py::recipe_to_kbhrecipe_payload()` builds
  the payload key by key from `modules/recipe.py`'s internal Recipe
  Object.
- Web: `web/js/kbhrecipe.js::_byggKjentPayload()` builds the payload
  from `KBHRECIPE_EKSPORTERBARE_FELT` — **not** `KBHRECIPE_KJENTE_FELT`
  directly, since the latter also includes Web-internal fields
  (`lagretDato`) that must never reach the file; see §3 above (PRI 2A —
  previously `byggKbhRecipeInnhold()` wrapped the whole in-memory
  recipe object unchecked; this was closed in PRI 2A, see §9 below and
  the PRI 2A report for the before/after). *(PR #3 Chief review: this
  section previously named the wrong constant — corrected.)*

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

Web does not need to understand `bryggerStil`, `prosess`, or `vann` to
preserve them — they are captured into and carried via this same
passthrough mechanism (§3 correction above, PR #3). Any future,
currently-unknown field is preserved the same way, with no code change
required for that new field specifically.

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

App's own passthrough mechanism (PRI 2C1 reader, PRI 2C2
recipe/session_state/writer wiring) is built on the same principle —
see §13. App represents it as a single internal recipe field,
`_kbh_passthrough` (`modules/recipe.py::bygg_recipe_object()`'s
`kbh_passthrough` parameter — a plain dict, deep-copied at every
boundary, omitted entirely from the recipe object when empty), mirrored
by one internal, non-widget-bound `session_state` key,
`_aktiv_kbh_passthrough` (same lifecycle pattern as
`_aktiv_recipe_efficiency`, PRI 2C0). Like Web's `_kbhUkjenteFelt`, it
is never itself a V1 field — `modules/kbh_contract.py`'s writer merges
its *contents* back into a fresh export as unknown top-level fields
(`_flett_inn_passthrough()`), and a known Core field the writer already
builds always wins over a stale passthrough value with the same key.
**Not yet wired into a Streamlit import UI** (no file uploader, no
import preview, no save-on-import) — that is PRI 2C3.

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

## 9. `recipeSchemaVersion` — normative policy (PRI 2B, KBHR-008)

`recipeSchemaVersion` travels **inside** the payload (with the
payload, not the envelope) so it survives extraction into a
`.kbhrecipe` file or a future `.kbhbrew` snapshot on its own. It is
**required** on the wrapped `.kbhrecipe` payload (§2) — a distinct
thing from the envelope's `version` (§8): envelope `version` governs
the `.kbhrecipe` file format itself; `recipeSchemaVersion` governs the
shape of the `recipe` payload inside it. The two are validated
independently, with independent, distinct rejection messages.

**Policy:**

- `recipeSchemaVersion === 1` — fully supported. Can be edited/saved
  normally.
- `recipeSchemaVersion` present but not `1` (higher, or any other
  numeric value) — the file is identified as a `.kbhrecipe` file, but
  Web does **not** enter the normal editable flow with it: import is
  **rejected explicitly**
  (`web/js/kbhrecipe.js::parseKbhRecipeInnhold()`, before
  `_gjenopprettOppskrift()` is ever reached), with a message distinct
  from an unsupported *envelope* version
  (`kbhrecipe.ustottetRecipeSchemaVersion` vs.
  `kbhrecipe.ustottetVersjon`/`kbhrecipe.nyereVersjon`). It is never
  saved as a local schema-1 recipe.
- `recipeSchemaVersion` missing, non-numeric, or otherwise invalid on
  a wrapped `.kbhrecipe` payload — rejected explicitly
  (`kbhrecipe.manglerRecipeSchemaVersion`), **never guessed to be 1**
  (the wrapped V1 contract requires the field — §2).
- The pre-wrapper legacy raw-JSON fallback (§12) predates
  `recipeSchemaVersion`'s existence entirely and is explicitly
  preserved as-is — this policy applies only to the wrapped
  `{format: "kbhrecipe", ...}` envelope path, not to that fallback.

**No silent downgrade, anywhere, ever:**
`web/js/recipe_storage.js::_normalisertRecipe()` — which runs on every
save **and** on every read of the local recipe store
(`lesOppskriftState()` normalizes every stored row on every load) —
previously overwrote `recipeSchemaVersion` to the current
`RECIPE_SCHEMA_VERSION` unconditionally, regardless of the incoming
value. **Fixed (PRI 2B):** a present, valid numeric
`recipeSchemaVersion` is now left **unchanged**, whatever its value —
only a missing/invalid one (a fresh Web-native recipe, or a row
migrated from the old pre-schema-version flat dictionary, §"Migrering
fra flat, navne-nøklet ordbok" in that file) is assigned the local
`RECIPE_SCHEMA_VERSION`. This is a second, independent line of
defense in the storage layer itself — the primary gate is the import
rejection above, which normally prevents an unsupported schema from
ever reaching storage at all.

**No migration built.** A future migrator that can actually interpret
and upgrade an older/newer `recipeSchemaVersion` is explicitly out of
scope here — today Web only ever produces and understands schema `1`.
This document does not define a V2 recipe schema.

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

## 13. App reader (PRI 2C1) — current App capability, not a universal V1 rule

`modules/kbh_import.py` is App's pure, side-effect-free `.kbhrecipe` V1
reader (parse + validate + reverse-adapt to App-native recipe data —
the mirror of `modules/kbh_contract.py`'s writer direction). Its
`passthrough` result is wired into the App-native recipe object,
`session_state`, `recipe_storage`, and the writer's re-export (PRI
2C2 — see §6 and the bullet below). **Not yet wired into a Streamlit
import UI** (no file uploader, no import preview, no save-on-import)
— that is PRI 2C3.

**This section describes what today's App reader accepts or rejects.
It is a statement of current App capability, not a new normative rule
for the `.kbhrecipe` V1 format itself** — a different reader (a future
App version, or another system entirely) may legitimately accept more
than this without violating V1. Where this section would conflict with
§1–§12 above, §1–§12 (the actual Core V1 contract) governs. *(PR #3
Chief review: this previously referenced itself, §1–§13 including this
section — corrected to point to the preceding normative sections.)*

- **No wrapperless legacy fallback.** §12 documents Web's own,
  Web-specific, undocumented-in-V1-proper compatibility path
  (`_erGyldigOppskriftForm()`); nothing in this document requires other
  readers to replicate it. App's reader requires the full
  `{format: "kbhrecipe", version: 1, ...}` envelope.
- **Strict canonical ID validation, no fuzzy matching.** Every
  `malt[].id`/`humle[].id`/`gjaerId` must exist verbatim in App's
  currently loaded master data (KBHR-013). No near-match, no
  display-name lookup, no default substitution — an unresolved ID
  rejects the whole import, with every unresolved ID listed together.
- **Unsupported custom ingredients and calculation overrides are
  rejected, not silently dropped or silently applied.** Actual content
  in `malt[].custom`, `humle[].custom`, `humle[].alfaOverride`,
  `gjaerCustom`, or `attenuationOverride` rejects the import (KBHR-012,
  KBHR-016, KBHR-017) — today's App has no calculation path that can
  honor them correctly. This is an App capability gap, not a V1
  restriction; PRI 4 (custom identity) may lift parts of it later.
- **`effektivitet` (percent) is converted to App's native fraction**
  (`68` → `0.68`) after validation — see §4/KBHR-019. The App-local
  equipment/brewhouse default profile is never read from or written to
  by the parser itself.
- **`prosess` is only imported when App's own normalization would not
  silently change its semantics** — a known `process_id` must match
  App's canonical standard profile exactly (structurally), or be
  `"egendefinert"` (custom steps are that mode's entire point, always
  safe). An unknown `process_id` — which would otherwise silently fall
  back to `enkel_infusjon` — still rejects the import (KBHR-018), since
  there is no canonical profile to preserve data against in the first
  place. **A known `process_id` whose structural fields *diverge* from
  App's canonical profile is no longer rejected (PR #3 Chief review,
  owner decision, 2026-09-02): it is imported losslessly as an
  App-safe `"egendefinert"` process instead** — `mash_steps` and any
  other structural field actually present in the file are preserved
  verbatim (never normalized to the canonical profile's own steps,
  never claimed to *be* that canonical profile); a structural field
  genuinely absent from the file falls back to the canonical profile's
  value for that one field only. This uses `"egendefinert"` exactly as
  designed — the one mode `normaliser_prosessprofil()` never
  overwrites — so it required no new representation and no change to
  `modules/process_profiles.py`. See
  `modules/kbh_import.py::_bygg_egendefinert_fra_avvikende_standard()`.
- **Non-calculation-affecting metadata is preserved opaquely via
  passthrough**, not dropped (KBHR-011/KBHR-014): `brygger`, `bryggeri`,
  `notater`, `valgtStil`, and any currently-unknown top-level payload
  field. `bryggerStil` and `valgtStil` are **not** the same thing
  (KBHR-015, see also PRI 2C's D6) — `bryggerStil` maps to App's native
  `brygger_stil`; `valgtStil` has no native App slot and goes to
  passthrough unchanged. `stats`, `flavor_profile`, and `recipeId` are
  never native-imported and never passed through, regardless of what a
  file contains under those names (same two-independent-points defense
  already used on the Web writer side).
- **The App writer can re-emit preserved passthrough on export (PRI
  2C2).** `modules/kbh_contract.py::recipe_to_kbhrecipe_payload()`
  builds all known Core fields first, exactly as before, then merges in
  `recipe["_kbh_passthrough"]`'s contents as unknown top-level fields
  (`_flett_inn_passthrough()`) — never with a blind `dict.update()`.
  Any key already in App's known-field list (§2/§3) is skipped
  unconditionally, whether or not the writer actually populated it this
  round, so a known Core field the user has genuinely changed always
  wins over a stale passthrough value with the same key (e.g. an edited
  `navn`/`volum` always overrides an old passthrough copy of the same
  name). `recipeId`, `stats`, `flavor_profile`, and the
  `_kbh_passthrough` container name itself are filtered out
  independently of the known-field list, so they can never leak back
  out even if they somehow ended up inside a hand-edited passthrough
  dict.

**Frozen legacy fixtures are compatibility evidence, not an import-safety
guarantee (KBHR-020).** `tests/fixtures/legacy/kbhrecipe/*.json` (frozen
in Core Stabilization, commit `b25276c`) prove that a historical writer
actually produced that exact text — they are not, by that fact alone,
proof that every current or future reader can import that text
losslessly. A reader is entitled to reject a syntactically valid,
historically genuine V1 payload if importing it would make the reader's
own native model silently diverge from what the file says — this is the
same principle §9/KBHR-018 already states for `recipeSchemaVersion` and
process-profile normalization, just spelled out explicitly for fixture
handling. The general principle stands; **its original concrete example
here has since been superseded (PR #3 Chief review, owner decision,
2026-09-02).** `tests/fixtures/legacy/kbhrecipe/full.json`'s `prosess`
block (one mash step) does not structurally match today's App canonical
`enkel_infusjon` (two steps, `modules/process_profiles.py`) — App's
reader no longer rejects that field; it now imports it losslessly as an
App-safe `"egendefinert"` process instead (see the bullet above,
`tests/test_kbh_import.py::test_2`), rather than either silently
renormalizing it, rejecting it outright, or weakening the canonical
equality check to accommodate it. The fixture itself is still not
touched, and today's App process-profile shape is still not a universal
Core rule (see above) — a reader remains entitled to reject old
evidence it cannot represent safely; App's reader has simply widened
what it can represent safely, without weakening the underlying
semantic-preservation guarantee itself.

## 14. What this document does not do

- Does not define `.kbhrecipe` V2, and does not add a new envelope
  version.
- Does not implement a Streamlit import UI (file uploader, import
  preview, save-on-import) — PRI 2C1 is a pure parser only, and PRI 2C2
  only wires its `passthrough` result into the recipe object,
  `session_state`, storage, and the writer (§13); the UI itself is PRI
  2C3.
- Does not implement `recipeId`/`originRecipeId` end-to-end identity.
- Does not build a `recipeSchemaVersion` migrator — an unsupported
  schema is rejected explicitly (§9), never interpreted or upgraded.
- Does not standardize custom-ingredient identity — owned by PRI 4.
- Does not touch `.kbhbrew`.
