# Core `.kbhbrew` V1 Contract

Version: 1.0
Status: Active
Ratified by: PRI 3A.2 (issue #22), from the owner's explicit PRI 3A
review decisions recorded in Section 8. `.kbhbrew` V1 is now the
governing Core contract — the same pattern
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) went through before it was
marked Active. A machine-readable schema now exists:
[core/kbhbrew_v1.schema.json](../../core/kbhbrew_v1.schema.json)
(Section 7).

Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) —
Core owns the shared wire contract; App/Web own their local storage,
UI, and user data (Section 1); Brew Lab owns the observation/
experiment/interpretation activity that happens *around* a brew record,
independent of which application's storage the record physically lives
in (Section 6). See also [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md)
(the sibling `.kbhrecipe` contract, whose conventions this document
follows where applicable) and [CORE_VERSIONING.md](CORE_VERSIONING.md) /
[CORE_STATUS_PROVENANCE.md](CORE_STATUS_PROVENANCE.md) (the general
Core version/provenance model this contract reuses rather than
reinventing).

**This is PRI 3A.2: ratification + schema + required Web compatibility
work.** It does not implement `.kbhbrew` in App (PRI 3B, separately
authorized), does not migrate any user data, and does not decide PRI 4
(custom ingredient identity). See Section 9, "What this document does
not do."

## PRI 3A.2 ratification summary (issue #22)

The five PRI 3A "owner decisions required" (former Section 8) are now
resolved and locked, per the owner's explicit review:

1. **Ingredient/equipment snapshot** — Option A, full embed. No
   historical masterdata archive invented; Core manifest provenance
   (`schema_version`/`data_version`/`checksum`) is additionally captured
   per referenced dataset at snapshot time where available (see
   "Provenance implementation status" below for the one known Web
   publication gap).
2. **Unknown-field passthrough** — Option A, required in V1. Implemented
   in `web/js/brew_storage.js` this round (Section 2/Section 6 updated
   below); the schema's `additionalProperties: true` throughout is the
   schema-level half of this guarantee.
3. **Derived `actual_abv` on the wire** — Option A, omit entirely. The
   schema does not define an actuals-layer ABV field; a canonical reader
   always recomputes from `actuals.{og,fg}`.
4. **Legacy App `note` mapping** — Option C, explicit split at
   conversion/write time. Deferred to PRI 3B as an adapter/UI decision;
   not implemented here. The wire shape (`actuals.notes` +
   `sensing.notes`, distinct and independent) is unaffected either way.
5. **"Actual process used"** — Option B, defer. No V1 field added; App's
   `process_profile_navn` remains product-local/legacy evidence.

These are locked for this contract unless implementation reveals a
genuine contradiction that makes one of them impossible or unsafe — see
the issue's own scope-change rule.

---

## 1. What is a Kvernhaug brew/batch record?

A **recipe** is the plan. A **brew** is the historical event: what was
planned, what actually happened, what was learned. They are separate
objects with separate lifecycles — a recipe can be edited freely; a
brew's frozen portion, once written, never changes.

`web/js/brew_storage.js` (Web, "Runde 25B") already implements this as
a five-layer model, boundaries drawn by *when* something is known and
*what kind of truth* it is:

| Layer | Content | When written |
|---|---|---|
| 1. Identity/lifecycle | `brewId`, `recipeId` (weak ref), `status`, timestamps | Mutable throughout the record's life |
| 2. Snapshot | Frozen plan: recipe payload, referenced ingredient master-data entries, equipment profile, predicted OG/FG/ABV/IBU/EBC/flavor/style, provenance | Written once, at brew creation, never again |
| 3. Actuals | Sparse instrument measurements (OG, FG, volume) | Whenever the user has a number to enter, in any order |
| 4. Sensing | The brewer's subjective experience (judgment, tasted flavor profile, notes) | Comes late, after tasting |
| 5. Learning | What to carry forward (`whatWorked`, `whatChanged`, `nextTime`) | Whenever, freely editable |

This five-layer model is adopted here as the analytical frame for the
rest of this document because it is the only one of the two existing
implementations that actually embodies the "store what cannot be
regenerated, never store what can be recalculated" principle already
stated in `KBH_CORE_CONTRACT_V1.md` §1 and carried forward in
`KBH_CORE_CONTRACT.md` §2 — see Section 4 below for where the App
implementation diverges from it.

**A brew is valid even if incomplete.** No field in layers 3–5 is
required, and no order is enforced — a user may record OG today, FG in
three weeks, and a reflection three months later. `status` is metadata,
not a state machine: `active` / `done` / `discarded` are freely
interchangeable, and a discarded batch (infected, dumped) is full,
valid history, not an error state.

---

## 2. Inventory — Web `.kbhbrew` / `kvernhaug_web_brygg` (current implementation)

Source: `web/js/brew_storage.js` (single file, DOM-free, no UI in this
round per its own header — a visible surface was added later,
`bryggelogg.html`, per `web/README.md` "Brygghistorikk" section).
Legacy evidence: `tests/fixtures/legacy/web/brew_store_v1.json` (full
localStorage store, three synthetic brews covering `active`/`done`/
`discarded`) and `tests/fixtures/legacy/web/kbhbrew_v1.json` (a single
exported `.kbhbrew` file).

- **Local store**: `localStorage["kvernhaug_web_brygg"]`, shape
  `{format: "kbh-brews", version: 1, items: [...]}` (`BREW_STORE_FORMAT`/
  `BREW_STORE_VERSION`) — read/written/verified-on-write exactly like
  `recipe_storage.js`/`pantry.js` (`lesBrewState()`/`_skrivBrewState()`,
  read-back verification, corrupt/mismatched envelope falls back to an
  empty store rather than crashing).
- **File format**: `.kbhbrew`, `{format: "kbhbrew", version: 1,
  exportedAt, generator, brew: {...}}` (`BREW_FIL_FORMAT`/
  `BREW_FIL_VERSION`) — same envelope shape as `.kbhrecipe`.
- **Identity — three distinct concepts, deliberately not collapsed**:
  - `brewId` — local storage identity. Minted locally
    (`crypto.randomUUID()` or a timestamp+random fallback), **never**
    adopted from an imported file. Prevents id collision across
    browsers/machines.
  - `originBrewId` — historical/file identity. Travels with an export
    and identifies the same real-world brewing event across machines.
    Defaults to `brewId` at creation.
  - `parentBrewId` — reserved, unused in V1 ("future shared batch, same
    wort, two fermenters"). Present in the schema, always `null` today.
  - `recipeId` — a **weak** reference for navigation/grouping only
    (`bryggForOppskrift()`). Display must never depend on it; the
    snapshot is authoritative. Deleting or renaming the recipe leaves
    the brew fully readable.
- **Validation**: `_gyldigBrew()` requires only `brewId` (non-empty
  string), `status ∈ {active, done, discarded}`, and `_gyldigSnapshot()`
  (an object with a `recipe` object and a `predicted` object). Layers
  3–5 are always optional.
- **Snapshot construction** (`byggBrewSnapshot()`): a full deep copy of
  the recipe payload; the **complete** master-data entries (not a
  hand-picked subset) for every non-custom ingredient the recipe
  actually references; the active equipment profile (or `null`);
  predicted `og`/`fg`/`abv`/`ibu`/`ebc`/`buGu`/`flavorProfile`/`style`
  (style reduced to `{stil, score}` — the localized `balanse`/
  `problemer`/`mangler` text is deliberately **not** frozen, since it is
  built with `t()` and would bake the exporting user's UI language into
  history); and `provenance` (`engineVersion`, `recipeSchemaVersion`,
  a weak `masterdata` entry-count proxy per ingredient type, and
  `capturedAt`).
- **Actuals/sensing/learning normalization**: each of
  `_normaliserActuals()`/`_normaliserSensing()`/`_normaliserLearning()`
  reads a **fixed, named set of fields** off the input object —
  `actuals` recognizes `og`/`fg`/`volumeL`/`notes`; `sensing`
  `judgment`/`flavorProfile`/`notes`; `learning`
  `whatWorked`/`whatChanged`/`nextTime` — but, **as of PRI 3A.2 (issue
  #22)**, no longer silently drops anything else. Every field outside
  the named set, on any of these three layers *and* on the top-level
  `brew` object, is now captured into a passthrough container
  (`_kbhBrewUkjenteFelt`, one per layer where it applies) and carried
  through read/normalize/import/export — the same general principle as
  `.kbhrecipe`'s `_kbhUkjenteFelt` (`web/js/kbhrecipe.js`, documented in
  [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §6), under a distinct
  internal name since brew passthrough is per-layer rather than a single
  recipe-wide container. The frozen `snapshot` layer never needed this
  fix: it is stored as an unfiltered deep copy already, so it was always
  effectively passthrough-safe (see Section 5.13). The **file envelope**
  (`format`/`version`/`exportedAt`/`generator`/`brew`) is preserved the
  same way, via a distinct container (`_kbhBrewEnvelopeUkjenteFelt`,
  captured on import in `parseKbhBrewInnhold()`, carried on the
  persisted brew object, and merged back into a freshly built envelope
  on export in `byggKbhBrewInnhold()`) — added in the Chief review round
  on PR #23 after the initial implementation was found to preserve
  unknown fields on the brew and its three sub-layers but not on the
  envelope itself. **Forbidden derived values are filtered even through
  passthrough**: `actual_abv`/`abv`/`actualAbv` are not in
  `BREW_ACTUALS_KJENTE_FELT`, so an imported/hand-edited value under one
  of those names is captured like any other unknown `actuals` field, but
  a dedicated export-time filter (`BREW_ACTUALS_FORBUDTE_EKSPORTFELT`,
  same PR #23 fix) still strips it before it ever reaches a written file
  — closing a gap where the generic passthrough guarantee would
  otherwise have let a forbidden Core field (Section 8 #3) leak back
  onto the wire. This closes the gap Section 6 previously documented as
  open — see Owner decision #2's ratified outcome above.
- **Derived values — never stored, always computed at display time**:
  `faktiskAbv()` ((actual OG − actual FG) × 131.25), `planVsFaktisk()`
  (plan-vs-actual deltas for OG/FG/ABV/volume), `faktiskEffektivitet()`
  (actual mash efficiency, algebraically derived from the frozen
  snapshot's OG/efficiency/volume plus actual OG/volume — **never** by
  re-running `beregnOG()` against today's live library, so a brew from
  last year gives the same answer today), `faktiskUtgjaering()`
  (apparent attenuation %), `bryggFase()` (a UI-only phase derived from
  what's actually filled in — `bryggedag → gjaering → smaking → ferdig`,
  or `forkastet` — not from `status` alone).
- **Import/identity policy** (`importerBrygg()`): a fresh local
  `brewId` is always minted on import; import is rejected as a
  duplicate (`{ok:false, duplikat:true}`, not silently re-created) if
  an existing brew already carries the same `originBrewId`. No
  merge/overwrite is ever automatic. `recipeId` is dropped on import
  (it is local-machine-scoped and meaningless on a receiving machine);
  the snapshot alone keeps the imported brew fully readable.
- **No App-side counterpart exists.** Nothing under `modules/`
  references `"kbhbrew"`, `brewId`, or an equivalent import/export
  format. App has no `.kbhbrew` reader or writer today.

---

## 3. Inventory — App brew log (current implementation)

Source: `modules/recipe_storage.py`
(`lagre_logg_entry()`/`hent_logg()`/`_logg_filsti()`/
`_legacy_logg_filsti()`/`_klassifiser_legacy_kandidat()`), wired from
`ui/recipe_card.py::_render_brewday_result_panel()`. Legacy evidence:
`tests/fixtures/legacy/app/brew_log.json`. Test coverage:
`tests/test_brewlog_logs_namespace.py`,
`tests/test_brewlog_schema_validation.py`,
`tests/test_brewlog_backup_and_corruption.py`,
`tests/test_legacy_logg_kandidat_klassifisering.py` — this is
production behavior with real regression coverage, not a stub.

- **Storage envelope**: `recipes/_logs/<generated-filename>_logg.json`
  (new location) or, for logs created before this namespace existed,
  `<generated-filename>_logg.json` directly in the recipes folder root
  (`_legacy_logg_filsti()` — read-only fallback, never auto-migrated).
  The file is a **flat JSON list of entries** — there is no wrapper
  object, no `format`/`version` envelope at all, and no single object
  representing "one brew."
- **Identity**: **none.** A log entry has no id of its own; entries are
  addressed only by their position in the list. The whole log is
  addressed only by the **recipe's name** (via `generer_filnavn()`),
  which is validated schema-wise (`hent_logg()` now requires the root to
  be a list and every element to be an object — `LoggKorruptError`
  otherwise, never a silent `AttributeError` or a stale-history
  overwrite) but is not itself a stable identity: `recipe_storage.py`'s
  rename handling (`_arkiver_kildefil_etter_omdoeping()`) explicitly
  migrates a log's *file* to the recipe's new name, but this is a
  storage-layer convenience, not an identity field carried inside the
  data itself the way Web's `originBrewId`/`recipeId` are.
- **Entry shape** (one dict per brewing event, all fields observed in
  `ui/recipe_card.py` and the legacy fixture):

  ```json
  {
    "date": "2026-02-20",
    "actual_volume_l": 23.0,
    "actual_og": 1.053,
    "actual_fg": 1.011,
    "actual_abv": 5.5,
    "note": "free text",
    "process_profile_navn": "Enkel infusjon"
  }
  ```

  `process_profile_navn` is optional (added by the UI only when an
  active process profile exists at save time); the legacy fixture's
  first entry omits it entirely, confirming it is not required.
- **No frozen snapshot of any kind.** The entry does not copy the
  recipe, its ingredients, its equipment, or its predicted values. The
  log lives *alongside* the live, mutable recipe file — if the recipe
  is later edited, nothing about the log entry's own "what was the plan
  when this was brewed" is preserved anywhere. This is the most
  significant structural gap relative to Web's model.
- **A derived value is stored, not computed**: `actual_abv` is
  precomputed by the UI (`round((actual_og - actual_fg) * 131.25, 1)`)
  and written into the entry, the opposite of Web's explicit "actual
  ABV is always recomputed from actuals, never stored" rule. This is a
  real, documented divergence — see Section 6/Section 8.
- **No status, no judgment, no sensing/learning layers.** `note` is a
  single free-text field doing the job Web splits across
  `actuals.notes` and `sensing.notes` — App has no concept of "measured
  observation" vs. "subjective tasting note" as separate fields, and no
  `whatWorked`/`whatChanged`/`nextTime` equivalent at all.
- **No `.kbhbrew` import/export exists.** App cannot read or write a
  `.kbhbrew` file today, in either direction.
- **Related but distinct: App's Recipe Object already caches computed
  values on the *recipe* itself.** `modules/recipe.py::bygg_recipe_object()`
  stores `stats` (`og`/`fg`/`abv`/`ibu`/`ebc`) and `flavor_profile`
  directly on the saved recipe object — a different pattern from Web,
  where the recipe (the plan) never carries predicted values and they
  are computed live, then frozen only inside a *brew's* snapshot.
  App's `stats`/`flavor_profile` are explicitly **forbidden** from
  `.kbhrecipe` export ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §7)
  but do exist in App's local on-disk recipe model. This is recipe-level
  state, not brew-level state, so it is out of this document's scope,
  but it is relevant context: App already has one precedent for storing
  a derived value locally that Web deliberately never persists.

---

## 4. Field-level mapping

`KEEP` = already suitable as Core V1 semantics · `ADAPT` = useful
concept, shape/name needs controlled change · `APP_ONLY`/`WEB_ONLY` =
legitimate product-local state, not wire contract · `DEFER` = useful,
not safe/necessary for V1 · `REJECT` = should not enter the Core
contract as-is.

| Concept | Web field/path | App field/path | Proposed Core meaning | Disposition |
|---|---|---|---|---|
| File envelope | `{format:"kbhbrew", version:1, exportedAt, generator, brew}` | *(none — no file format exists)* | Same envelope shape as `.kbhrecipe` §1 | ADAPT |
| Local storage identity | `brewId` (local-only, never adopted from a file) | *(none — list position only)* | Core: local storage identity policy, minted locally | KEEP (concept) |
| Portable/file identity | `originBrewId` | *(none)* | Core: cross-machine identity, distinct from local id, dedup-on-import key | KEEP (concept) |
| Reserved shared-batch link | `parentBrewId` (unused in V1) | *(none)* | Reserved field, no V1 semantics yet | DEFER |
| Recipe linkage | `recipeId` (weak, navigation-only) | Recipe **name** via filename (weaker — renameable, no id at all) | Core: a weak reference; the frozen snapshot is always authoritative for display | ADAPT |
| Frozen recipe payload | `snapshot.recipe` (full deep copy) | *(none — no per-brew freeze exists)* | Core: immutable frozen recipe payload, written once | KEEP (concept), gap on App side |
| Frozen ingredient master-data | `snapshot.ingredients.{malt,humle,gjaer}` — full referenced entries, not a hand-picked subset | *(none)* | Full embed (Section 8 #1, ratified) | KEEP (Web's current behavior is now the Core V1 contract) |
| Frozen equipment profile | `snapshot.equipment` (or `null`) | *(none — App's `modules/equipment.py` profile is live/global, never frozen per brew)* | Core: optional frozen equipment snapshot | ADAPT |
| Frozen predicted values | `snapshot.predicted.{og,fg,abv,ibu,ebc,buGu,flavorProfile,style}` | *(none per brew — App's `stats`/`flavor_profile` live on the mutable recipe object instead, see §3)* | Core: frozen prediction snapshot, per `KBH_CORE_CONTRACT.md` §2's explicit exception for historical reproducibility | KEEP (concept), shape depends on OWNER DECISION #1 |
| Snapshot provenance | `snapshot.provenance.{engineVersion, recipeSchemaVersion, masterdata: {…count}, capturedAt}` | *(none)* | Core: needed for reproducibility. `core/manifest.json` already provides a stronger per-dataset foundation (`schema_version`, `data_version`, `checksum`) than Web's entry-count proxy; a Core-compliant writer should capture those manifest fields per referenced dataset. Web's entry-count proxy remains readable as legacy/de-facto provenance on brews already captured under it | ADAPT |
| Status | `status ∈ {active, done, discarded}`, freely reassignable metadata | *(none)* | KEEP | KEEP |
| Judgment | `sensing.judgment ∈ {yes, maybe, no}` | *(none)* | KEEP | KEEP |
| Measured actuals: OG/FG/volume | `actuals.{og, fg, volumeL}` (canonical SG points, liters) | `actual_og`, `actual_fg`, `actual_volume_l` (same canonical units, snake_case) | KEEP concept; naming/casing convergence is a product decision, not a wire-contract blocker | ADAPT |
| Actual ABV | **Never stored** — always `faktiskAbv()` from actuals | **Stored explicitly** (`actual_abv`, precomputed by the UI) | Wire contract only: omitted entirely (Section 8 #3, ratified). Does not require App to change its local storage — App's cached copy is product-local and out of scope | **REJECT** on the wire (never authoritative, never emitted by a canonical writer); App's local field remains APP_ONLY |
| Actual process used | *(absent — Web's actuals has no process-used field at all)* | `process_profile_navn` (name string only, no full profile) | A genuinely new candidate Core field ("what was actually done"), not yet present on either side in a complete form | DEFER (needs its own design, same caution `.kbhrecipe`'s `prosess` field already required) |
| Measurement/observation notes | `actuals.notes` (measurement-adjacent) + `sensing.notes` (tasting-adjacent) — two distinct fields | `note` — a single merged field covering both | Core V1 wire shape: both `actuals.notes` and `sensing.notes`, optional and independent, matching Web (§5.8) — not an open wire question | KEEP (Web's two-field shape); App's single `note` → this shape is a PRI 3B adapter/migration decision (Section 8 #4, ratified: explicit split at write time), not decided here |
| Sensory flavor profile | `sensing.flavorProfile` (numeric map, same axes as predicted) | *(none)* | KEEP | KEEP |
| Learning: whatWorked/whatChanged/nextTime | `learning.{whatWorked, whatChanged, nextTime}` | *(none)* | KEEP | KEEP |
| Timestamps | `createdAt` + `brewedAt` (both ISO 8601, distinct meanings) | `date` only (a single date; ambiguous whether it means "brew day" or "log entry day" — in practice always brew day) | Core: needs at least a "when brewed" timestamp; `createdAt` (record creation) vs. `brewedAt` (the actual brew day) is a real, useful distinction Web already draws | ADAPT |
| Unknown-field passthrough | **Implemented as of PRI 3A.2** (issue #22) — the four normalizers now capture unrecognized fields into a per-layer passthrough container instead of dropping them | N/A (flat list; no schema-aware writer to lose data from) | `.kbhrecipe` already requires this ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §6); `.kbhbrew` now provides the equivalent guarantee (Section 8 #2, ratified: Option A, required in V1) | KEEP (required) |
| Import duplicate detection | `originBrewId`-keyed, explicit `{duplikat:true}` result, never silent | *(none — no import mechanism exists)* | KEEP as the Core V1 identity/dedup policy | KEEP |
| `_kbh_passthrough` (recipe-level opaque fields) | N/A — this is a `.kbhrecipe` mechanism, not `.kbhbrew` | Recipe-scoped only (`modules/recipe.py`), not brew-scoped | Out of scope: this is `.kbhrecipe`'s mechanism, unrelated to a brew record | APP_ONLY / WEB_ONLY (recipe-scoped, not this contract's concern) |

Where evidence was absent for a cell, it is marked so explicitly above
rather than guessed (per the issue's instruction) — the "recipe
linkage," "actual process used," and "provenance" rows are the ones
carrying the most uncertainty.

---

## 5. Proposed `.kbhbrew` V1 Core contract

### 5.1 Purpose and non-goals

**Purpose**: define the minimum shared meaning of a Kvernhaug brew/batch
record so any current or future Core-compliant reader/writer (App, Web,
a future Brew Lab surface) can interpret one without reverse-engineering
`web/js/brew_storage.js`.

**Non-goals**: this proposal does not require App to implement
`.kbhbrew` (PRI 3B, separately authorized), does not migrate any
existing App brew-log data, does not change Web's implementation, and
does not resolve custom-ingredient identity (PRI 4).

### 5.2 Envelope and `schemaVersion`/format/version rules

Same shape and rules as `.kbhrecipe`
([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §1/§8): `{format:
"kbhbrew", version: 1, exportedAt, generator, brew: {...}}`. `format`
must equal `"kbhbrew"` exactly; any envelope `version` other than `1`
is rejected explicitly, never guessed or coerced. Unlike `.kbhrecipe`,
`.kbhbrew` has **no legacy wrapperless fallback** to preserve — Web's
`.kbhbrew` export has always used the wrapper, so no equivalent to
`.kbhrecipe`'s raw-JSON heuristic (§12 there) is needed here.

The frozen recipe payload inside `snapshot.recipe` carries its own
`recipeSchemaVersion`, exactly as `.kbhrecipe` requires
([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §9) — this is the same
field, travelling with the payload, not duplicated with new meaning.

### 5.3 Brew/batch identity policy

Three distinct identifiers, per Section 2 above, none of them
optional/interchangeable:

- `brewId` — local storage identity. Minted locally on creation or
  import. Never read from an imported file's `originBrewId`/`brewId`.
- `originBrewId` — portable/historical identity. Travels with an
  exported file. Defaults to `brewId` at creation if not otherwise set.
- `parentBrewId` — reserved for a future shared-batch concept. Always
  `null` in V1; no reader may assign meaning to a non-null value yet.

A reader importing a file whose `originBrewId` matches an
already-stored brew must report a duplicate and refuse to silently
create a second copy or silently merge — matching Web's
`importerBrygg()` behavior today.

### 5.4 Relationship to `.kbhrecipe`

A brew's `snapshot.recipe` is a frozen **copy** of a `.kbhrecipe`-shaped
payload (same fields, same `recipeSchemaVersion` semantics) — it is not
a live reference to a stored recipe file, and a brew record must remain
fully readable even if the original recipe (and its `recipeId`) no
longer exists. `recipeId` at the brew's top level is always a **weak**
reference for grouping/navigation only; no calculation or display may
depend on it resolving.

### 5.5 Frozen snapshot semantics and immutability boundary

The snapshot (layer 2: `recipe`, `ingredients`, `equipment`,
`predicted`, `provenance`) is written exactly once, at brew creation,
and never modified afterward — not even to fix a typo. This is the
entire point of freezing it: "what did Kvernhaug know when this brew
started?" must have one unambiguous, permanent answer. A reader must
reject or ignore any write attempt that targets an existing brew's
`snapshot` — only layers 1/3/4/5 (`status`, `actuals`, `sensing`,
`learning`, plus `brewedAt`) may ever be updated after creation.

### 5.6 Canonical units and nullable/optional semantics

Same canonical units as `.kbhrecipe`
([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §4): liters, kilograms,
grams, minutes, Celsius; specific gravity as a plain decimal number
(`1.053`), never "SG points." Display units/locale must never be
stored. Every field in layers 3–5 is optional and independently
nullable/omittable — there is no minimum "complete" brew beyond layer 1
+ a valid snapshot.

### 5.7 Measured actuals vs. derived values

**Measured actuals** (layer 3: `og`, `fg`, `volumeL`) are raw instrument
readings, stored as-entered. **Derived values** — actual ABV, plan-vs-
actual deviation, actual efficiency, actual attenuation — are, on the
**wire**, **always** computed at read/use time from stored actuals and
the frozen snapshot, and **never carried as an authoritative field**,
per the "store what cannot be regenerated" principle already
established for Core (`KBH_CORE_CONTRACT.md` §2) and already
implemented this way in Web (`faktiskAbv()`, `planVsFaktisk()`,
`faktiskEffektivitet()`, `faktiskUtgjaering()`).

This is a statement about the **`.kbhbrew` wire contract only**, not
about App's internal persistence. Core does not own, and this document
does not decide, what App keeps in its own local storage/workflow
(`KBH_CORE_CONTRACT.md` §1) — App's current `actual_abv` field is
product-local convenience state, not a wire-contract violation by
itself. What Core V1 does require: a canonical `.kbhbrew` reader always
recomputes ABV from `actuals.{og,fg}` and never trusts a carried value
as authoritative; a canonical `.kbhbrew` exporter must either omit
`actual_abv` entirely or mark it explicitly non-authoritative, treating
any App-side cached value it disregards on export as safely
discardable, not as data loss. Section 8 #3 records this as **ratified:
Option A, omit entirely** — the wire schema does not define an
`actual_abv`/`abv` field at all, and a canonical `.kbhbrew` writer must
never emit one, including via generic unknown-field passthrough (see
Section 2's "forbidden derived-ABV spellings" filter).

### 5.8 Sensory/documented observations vs. instrument measurements

Layer 3 (`actuals`) is instrument/measured data (a gravity reading, a
measured volume). Layer 4 (`sensing`) is the brewer's subjective,
documented experience (a judgment call, a tasted flavor profile, a
tasting note) — the two must not be collapsed into one field, per the
issue's explicit requirement and per `KBH_CORE_CONTRACT.md`'s
Brew-Lab ownership of "observation/interpretation" as a distinct
category from raw measurement. Where a batch is treated as Brew Lab
work, `sensing`/`learning` are the layers Brew Lab semantically owns
the *interpretation* of — Core still owns their wire meaning (so any
reader can display them), matching the same non-storage-ownership
pattern `KBH_CORE_CONTRACT.md` §6 already draws for App's local batch
data ("makes App the local authoritative store... does not make App an
owner of Core's schema").

Because measurement-adjacent notes and tasting-adjacent notes are two
different categories under this same distinction, Core V1 defines two
free-text fields, both optional and independently populated:
`actuals.notes` (measurement-adjacent, e.g. "kettle boiled over
slightly") and `sensing.notes` (tasting/experience-adjacent, e.g. "more
bitter than predicted"). This matches Web's already-implemented shape
(Section 2).
`.kbhbrew` V1 has exactly one canonical shape for this concept — it
does not also define a merged single-field alternative. How a product
whose own local storage only has one merged field (App's `note`, see
Section 3) would map onto these two fields if and when it implements a
`.kbhbrew` writer is a separate, deferred adapter question — see
Section 8 #4.

### 5.9 Learning/notes semantics

Layer 5 (`learning`) is forward-looking payload for the *next* brew of
the same recipe: `whatWorked`, `whatChanged`, `nextTime` — free text,
all optional, all independently editable at any time. `nextTime` is the
single most important value in the model (Web's
`sisteErfaringForOppskrift()` surfaces exactly this one field before a
new brew starts) — a future Core-compliant reader should treat it as
the field most worth surfacing prominently, though this document does
not mandate any specific UI.

### 5.10 Status semantics (metadata, not a state machine)

`status ∈ {active, done, discarded}`. Freely reassignable in any
direction — there is no enforced lifecycle/ordering, and "has this brew
been fermented yet" must be derived from whether `actuals.fg` is
present, never encoded redundantly into `status`. A `discarded` brew is
full, valid history.

### 5.11 Timestamps

`createdAt` (when the record was created — always present, ISO 8601)
and `brewedAt` (the actual brew day, ISO 8601, optional — may be set
later than `createdAt`, or never, if unknown). These are deliberately
two different questions ("when did Kvernhaug learn about this brew" vs.
"when did the brew actually happen") and must not be merged into one
field, unlike App's current single `date`.

### 5.12 Provenance / calculation-engine and data-version references

`snapshot.provenance` must record enough to know *which* calculation
engine and *which* masterdata revision produced the frozen `predicted`
values — `engineVersion` (bumped manually when `calc.js`/`flavor.js`/
`style.js` change output for the same input) plus, per referenced
dataset (`malt`/`humle`/`gjaer`), the `schema_version`, `data_version`
and `checksum` already recorded in `core/manifest.json`
(`CORE_VERSIONING.md`). This is materially stronger than an entry-count
proxy: `data_version` is bumped on any semantic content change
(corrected malt potential, added/removed entries) independent of
whether the count happens to stay the same, and the checksum lets a
future tool detect even a byte-level change the count would miss.
Capturing the manifest's *current* `data_version`/`checksum` per
dataset at snapshot time is implementable today — it does not require,
and this document does not invent, a historical archive of prior
masterdata revisions. Without such an archive, a captured
`data_version` proves *that* the referenced dataset has since drifted
(current manifest value ≠ captured value) but not *what* changed; that
limit is inherent to not having an archive, not to the manifest itself.

Web's current `masterdata: {…count}` proxy is de-facto legacy
provenance: it remains a valid, readable field on brews already
captured under it, but it is **not** the normative Core V1 provenance
target — a Core-compliant writer should populate the manifest-derived
fields above instead. See Section 8 #1, whose embedding-vs-reference
tradeoff also turns on what the manifest can and cannot reconstruct.

### 5.13 Unknown-field preservation policy

**Required (ratified, Section 8 #2, Option A)**: a Core-compliant
`.kbhbrew` reader/writer must preserve unknown fields on every layer —
the envelope, the top-level `brew` object, and `actuals`/`sensing`/
`learning` — the same way `.kbhrecipe` already does via its passthrough
container (`_kbhUkjenteFelt` / `_kbh_passthrough`). **Implemented as of
PRI 3A.2** (issue #22) in `web/js/brew_storage.js` (Section 2) via a
per-layer passthrough container (`_kbhBrewUkjenteFelt` on the top-level
`brew` object and each of `actuals`/`sensing`/`learning`; a distinct
`_kbhBrewEnvelopeUkjenteFelt` for the file envelope itself, added in the
PR #23 review round), round-trip-tested in
`tests/js/test_kbhbrew_contract.js`.

### 5.14 Import identity / duplicate/copy behavior

As Section 5.3: dedup on `originBrewId`, fresh `brewId` always minted
on import, explicit duplicate signal rather than silent re-creation or
silent overwrite/merge.

### 5.15 Forwards/backwards compatibility expectations

A reader that only understands `version: 1` must detect and reject
(never silently misinterpret) any other envelope `version`, mirroring
the existing `.kbhrecipe` pattern. Because Web's normalizers now
preserve unknown fields on every layer rather than silently dropping
them (§5.13, implemented as of PRI 3A.2), a *future* additive V1.1
field survives a round trip through today's Web reader instead of being
lost — the forward-compatibility gap this section used to document is
closed for Web; the passthrough requirement (Section 8 #2) remains the
mechanism that makes same-major-version evolution safe for any other
implementation too.

### 5.16 Validation: reject vs. normalize vs. preserve

- **Reject outright**: unsupported envelope `format`/`version`; a
  missing/invalid `brewId` or `status` on the top-level record; a
  missing/invalid snapshot (`recipe` object, `predicted` object).
- **Normalize**: numeric-ish actuals/sensing values coerced the way
  Web's `_tallEllerUndefined()`/`_tekstEllerUndefined()` already do
  (accept a parseable number/non-empty trimmed string, drop otherwise) —
  this is tolerant-input normalization, not silent semantic
  reinterpretation.
- **Preserve**: everything else — see §5.13 (required policy, ratified
  and implemented) and Section 8 #2 (ratified: Option A, required).

### 5.17 Explicit ownership boundaries — Core / App / Web / Brew Lab

- **Core** owns: the envelope, the five-layer shape, field names/units/
  nullability, the identity policy (`brewId`/`originBrewId`/
  `parentBrewId`), the "derived values are never authoritative if
  stored" rule, and the unknown-field preservation policy once decided.
- **App/Web** own: their local storage location/format details (a
  JSON file under `recipes/_logs/` vs. a `localStorage` array), their
  UI, and the user's concrete data values (the actual OG a user typed
  in) — consistent with `KBH_CORE_CONTRACT.md` §6.
- **Brew Lab** owns: the interpretation/experiment/observation activity
  that happens when a batch is treated as hands-on brewing work — the
  *meaning* a user or a future Brew Lab feature assigns to `sensing`/
  `learning` content, independent of which app's storage physically
  holds the record.

---

## 6. Compatibility / migration analysis (no migration performed)

**Is today's Web `.kbhbrew` wire-lossless on its own round-trip?**
As of PRI 3A.2 (issue #22), **yes, structurally**, not merely by
coincidence: `web/js/brew_storage.js`'s four normalizer functions now
capture any field outside their known set into a passthrough container
per layer (Section 2), closing the forward-compatibility gap §5.15
previously described. Before this round it was only true *in practice*
(Web only ever wrote fields already in its own whitelist).

**Can current Web `.kbhbrew` be treated as Core V1 as-is?**
**Yes — this is now the ratified Core V1 baseline.** The two caveats
this section previously listed as open are resolved:

1. Unknown-field passthrough (Section 8 #2, ratified: required) —
   implemented this round, see Section 2.
2. Ingredient embedding (Section 8 #1, ratified: full embed, Option A)
   — Web's existing full master-data-copy behavior is the Core V1
   contract as-is; no code change was needed for this half.

Nothing else in Web's model changed to serve as Core V1: no
backwards-incompatible reader adaptation was required, and it should
**not** be treated as a mere "product-local pre-Core format" — it was
already, and remains, the only implementation that satisfies the
five-layer model, the identity policy, and the derived-value discipline
this contract requires.

**App compatibility/gap summary.**
App implements, at most, the **actuals** layer of the five-layer model,
in a structurally different, non-frozen, non-identified shape (Section
3): no `brewId`/`originBrewId`, no frozen snapshot of any kind, no
`sensing`/`learning` layers, no `status`, one merged `note` field, and
one derived value (`actual_abv`) stored where Core/Web say it should be
recomputed. App also has **zero** `.kbhbrew` reader or writer today.
Adopting `.kbhbrew` in App would therefore be **new App feature work**,
not a migration of an existing compatible format — there is no
"convert App's brew log to `.kbhbrew`" adapter that can be written
today without first resolving what a frozen App-side snapshot would
even contain (App's Recipe Object does not carry the same
plan/prediction separation Web's does — see Section 3's closing note).
This confirms the App gap is real and non-trivial, not a naming
mismatch.

**What legacy data must remain readable.**
`tests/fixtures/legacy/app/brew_log.json` (flat App shape) and
`tests/fixtures/legacy/web/brew_store_v1.json` /
`tests/fixtures/legacy/web/kbhbrew_v1.json` (full Web shape) are frozen
compatibility evidence per `tests/fixtures/legacy/README.md` — they
document what each implementation actually produces today and must
keep validating unchanged regardless of any future Core `.kbhbrew`
work. This document does not touch them.

**What cannot currently be represented / requires an adapter.**
An App brew-log entry cannot be losslessly represented as a Core
`.kbhbrew` brew record today, because it lacks the entire snapshot
layer (there is nothing to freeze — App has no per-brew capture of
"what the recipe/ingredients/equipment looked like at brew time"). A
future App→`.kbhbrew` writer would need to either (a) freeze the
recipe/ingredients/equipment *at the moment* a log entry is created —
new App behavior, not a data transformation of existing entries — or
(b) explicitly represent old App log entries as `.kbhbrew` records with
an empty/absent snapshot, which the current `_gyldigSnapshot()` policy
in Web (`recipe` + `predicted` objects required) does not allow. Neither
option is decided or built here — this is exactly the kind of
cross-product migration this issue explicitly excludes.

---

## 7. Machine-readable schema

PRI 3A left this deferred pending the two decisions (#1 ingredient
embedding vs. reference; #2 passthrough requirement) that directly
determine the **shape** of `snapshot.ingredients`/`snapshot.equipment`
and of every layer's tolerance for extra fields — a JSON Schema written
before either was resolved would either (a) have hard-coded Web's shape
as permanent Core law without an owner having actually chosen it, or
(b) needed rewriting the moment either decision landed.

**Both are now resolved (Section 8, ratified by PRI 3A.2 / issue #22)**,
so the schema is added this round:
[core/kbhbrew_v1.schema.json](../../core/kbhbrew_v1.schema.json) (JSON
Schema, draft 2020-12). It encodes: the envelope and its pinned
`format`/`version`; the identity fields (`brewId`/`originBrewId`/
`parentBrewId`/`recipeId`), all optional at the schema level since a
canonical exported file omits the two local-only ones (`brewId`/
`recipeId` — see the frozen legacy fixture,
`tests/fixtures/legacy/web/kbhbrew_v1.json`); the frozen snapshot's
required minimum shape (`recipe` + `predicted` objects); full embedded
ingredient/equipment snapshot semantics (Section 8 #1); a provenance
structure covering both the new normative Core-manifest-derived
`provenance.datasets.{malt,humle,gjaer}.{schema_version,data_version,
checksum}` shape and the legacy `provenance.masterdata` entry-count
proxy, which remains readable but is not the V1 target (Section 5.12);
the optional `actuals`/`sensing`/`learning` layers with distinct
`actuals.notes`/`sensing.notes`; canonical `status`/timestamp fields;
no canonical `actual_abv` or V1 actual-process field (Section 8 #3/#5);
and `additionalProperties: true` throughout, the schema-level
expression of the unknown-field passthrough requirement (Section 8 #2).

Contract fixtures and tests live in
`tests/fixtures/core/kbhbrew/{minimal_v1,full_v1}.json` and
`tests/test_kbhbrew_schema_contract.py` — covering a minimal valid
brew, a representative full brew (including the new manifest-provenance
shape), unknown fields surviving validation at every layer, rejection
of an unsupported envelope format/version, enforcement of the required
identity/snapshot rules, absence of a canonical `actual_abv`/process
field, and that the frozen legacy Web `.kbhbrew` fixture still
validates unchanged against this schema.

---

## 8. Owner decisions — ratified (PRI 3A.2, issue #22)

The five decisions below were left open by PRI 3A's discovery round and
are now resolved by explicit owner review. Each entry keeps the
original options/rationale for context, with the ratified outcome
stated first. These are **locked** for this contract unless
implementation reveals a genuine contradiction that makes one
impossible or unsafe.

### 1. Ingredient/equipment snapshot: embed full records, or reference by id + pinned version?

**Ratified: Option A — full embed.** Core V1 keeps Web's current
self-contained historical snapshot model; no historical masterdata
archive is invented. Core manifest provenance
(`schema_version`/`data_version`/`checksum`) is additionally captured
per relevant dataset at snapshot time where the writer has trustworthy
access to it (see Section 5.12 and "Provenance implementation status"
below for the one documented Web gap).

- **Option A — full embed (Web's current behavior).** Self-contained:
  a brew remains fully readable even if the referenced master-data
  entry is later deleted, renamed, or its id reused. Cost: snapshot
  size scales with ingredient record size (today's records include
  `butikk_match` pricing/URL blocks, aliases, etc. — see the fixture
  examples in Section 2), and there is no way to tell, from the brew
  alone, whether the embedded copy still matches today's canonical
  entry.
- **Option B — reference by id + pinned `data_version`/`checksum`.**
  Smaller, and *recording* the pin is implementable today —
  `core/manifest.json` already exposes per-dataset `schema_version`,
  `data_version` and `checksum` (`CORE_VERSIONING.md`) to capture at
  snapshot time. The real cost is narrower than "not implementable":
  a pinned `data_version` only proves *whether* the referenced dataset
  has drifted since (current manifest value vs. captured value) — it
  cannot *reconstruct* what the specific ingredient entry looked like
  at brew time, because no historical archive of prior masterdata
  revisions exists yet. So Option B can tell a reader "this snapshot's
  ingredient reference is now stale," but only full embedding (Option
  A) can show the reader the actual historical values without one.
- **Option C — hybrid (embed only calculation-relevant fields).**
  Already implicitly rejected by Web's own code comment (§ `web/js/
  brew_storage.js` lines 60–67): a hand-picked subset "would quietly
  become wrong the day a calculation starts using one more field."
- **Ratified outcome**: Option A, pragmatically, until Option B's
  prerequisite (a real historical masterdata archive) exists — this was
  the discovery round's recommendation, and the owner has since made it
  the binding decision (see the ratified outcome stated at the top of
  this entry).

### 2. Is unknown-field passthrough required for `.kbhbrew` V1?

**Ratified: Option A — required now.** `.kbhbrew` V1 must preserve
unknown fields across read/normalize/write/import/export round trips,
matching `.kbhrecipe`'s existing guarantee. Implemented this round in
`web/js/brew_storage.js` (Section 2) — see
`tests/js/test_kbhbrew_contract.js` for the Web round-trip proof and
`core/kbhbrew_v1.schema.json` (`additionalProperties: true` throughout)
for the schema-level half.

- **Option A — require it now.** Matches `.kbhrecipe`'s existing
  guarantee; requires new Web implementation work (adding a passthrough
  container to all four normalizers) that is explicitly out of scope
  for this docs-only PRI 3A round.
- **Option B — defer explicitly to a V1.1,** documenting the current
  gap as a known, accepted limitation of V1.
- **Option C — accept the asymmetry with `.kbhrecipe` permanently**,
  on the reasoning that a brew record's fields are more fixed/closed
  than a recipe's (arguable — the issue itself and this document have
  already identified two candidate future fields, "actual process
  used" and richer provenance, that a passthrough gap would silently
  discard from any writer that gets ahead of the reader).

### 3. Should the `.kbhbrew` wire schema carry a derived value (e.g. `actual_abv`) at all?

**Ratified: Option A — omit it from the wire entirely.** Canonical
`.kbhbrew` carries OG/FG actuals only; ABV is always recomputed. A
future App exporter may keep any local convenience/cache value
internally — Core does not dictate App local persistence.

This is scoped to the **wire contract only** — it does not decide, and
must not be read as deciding, whether App keeps `actual_abv` in its own
local storage. App owns its local persistence/workflow
(`KBH_CORE_CONTRACT.md` §1); that is unaffected regardless of which
option below is chosen.

- **Option A — omit it from the wire entirely.** Canonical readers
  always recompute ABV from `actuals.{og,fg}`; a `.kbhbrew` exporter
  never writes `actual_abv`, even if the exporting product (e.g. a
  future App writer) has a locally cached value. Simplest, no
  authoritative/non-authoritative ambiguity on the wire.
- **Option B — allow it as an optional, explicitly non-authoritative
  field**, with a rule that any reader must recompute and treat a
  present value as informational only, silently overridden on
  conflict. Lets a future App exporter carry its local convenience
  value through export without losing it, at the cost of a wire field
  whose value a spec-compliant reader is required to ignore for
  correctness.

### 4. How should App's single legacy `note` field map onto Core's two-field notes shape?

**Ratified: Option C — explicit split at conversion/write time.** This
is a PRI 3B adapter/UI decision, not work for this issue — not
implemented here. Core's wire shape remains the distinct optional
`actuals.notes`/`sensing.notes` pair regardless.

This is **not** a wire-schema ambiguity — Section 5.8 already fixes the
wire shape as two distinct, optional, independent fields
(`actuals.notes` and `sensing.notes`), matching Web. `.kbhbrew` V1 does
not define a second, merged-field wire representation of the same
concept alongside it. What remains open is a narrower, product-side
adapter/migration question, deferred to PRI 3B (not decided here, and
not needed for this docs-only round): if and when App implements a
`.kbhbrew` writer, how does its existing single `note` field populate
the two-field wire shape?

- **Option A — write it into `sensing.notes` only.** App's UI collects
  `note` after OG/FG are entered, closer to a tasting/summary note than
  a pure measurement annotation; `actuals.notes` is left absent.
- **Option B — write it into both fields.** Simplest to implement,
  but duplicates the same text under two semantically distinct
  headings, which a reader may reasonably not expect.
- **Option C — prompt for an explicit split at write time** (a product
  UI decision, not a data-transformation one), so newly written App
  `.kbhbrew` records carry the fields Web already draws a real
  distinction between.

Whichever option PRI 3B picks, it is an adapter decision about how one
product's legacy local field feeds a fixed wire shape — it must not
reopen or duplicate the wire shape itself.

### 5. Should "actual process used" become a real Core V1 field?

**Ratified: Option B — defer.** No half-defined process field is added
to V1. Existing App `process_profile_navn` remains product-local/legacy
evidence until separately designed.

- **Option A — add it now**, since both implementations already gesture
  at it (App has a name-only string; Web has none at all) and it fits
  naturally as a layer-3 actual.
- **Option B — defer it (recommended default absent an owner steer)**,
  consistent with `.kbhrecipe`'s own documented caution around its
  `prosess` field (`CORE_KBHRECIPE_V1.md` §13's KBHR-018 discussion) —
  a full process-profile-shaped actual is more design work than this
  discovery task should absorb.

**With all five resolved**, PRI 3A.2 (this ratification) completed the
concrete next implementation step: (a) this document is now
`Version: 1.0`/`Status: Active`; (b) the machine-readable JSON Schema
deferred in the old Section 7 is written, with contract fixtures
alongside it (`tests/fixtures/core/kbhbrew/`, mirroring
`tests/fixtures/legacy/`'s pattern); (c) PRI 3B (actual App `.kbhbrew`
implementation) remains its own, separately authorized issue — not
started here.

### Provenance implementation status (issue #22, Section 5 scope)

Core manifest provenance (`schema_version`/`data_version`/`checksum`
per dataset, `core/manifest.json`) is the schema's normative
`provenance.datasets` target (Section 5.12, Section 7). Whether Web can
*populate* it today is a separate, narrower question from whether the
contract/schema should *define* it — the contract does; **Web cannot
yet populate it without a build-pipeline change, and this round does
not add one.**

Checked this round: `web/data/{malt,humle,gjaer}.json` (the files
`scripts/generate_web_data.py` actually publishes and the only
ingredient data the browser has access to at snapshot time) carry no
`schema_version`/`data_version`/`checksum`/manifest-linked metadata of
any kind — plain `{id: {...entry fields...}}` maps, verified by reading
both the generator script and a live generated file. `core/manifest.json`
itself is not copied into `web/` at all. So
`byggBrewSnapshot()`/`_frysIngredienser()` in `web/js/brew_storage.js`
have no trustworthy, already-published value to read at snapshot time
— populating `provenance.datasets` from the browser today would mean
**fabricating** manifest-shaped values (e.g. hardcoding today's
`core/manifest.json` numbers into `brew_storage.js` by hand, which would
silently go stale the moment either file changes), which Section 5.12
and this document's own discipline explicitly forbid.

**Decision (per the issue's explicit fallback path): do not fabricate.**
`web/js/brew_storage.js`'s `byggBrewSnapshot()` is unchanged in this
round — it continues to write only the legacy `provenance.masterdata`
entry-count proxy, which remains valid, readable de-facto provenance on
every brew captured under it (Section 5.12), just not the V1 normative
target.

**Smallest follow-up needed before a Core-compliant Web writer can claim
full V1 provenance** (not built here, explicitly out of scope per the
issue's "do not expand into crawler/masterdata-pipeline work" guardrail):
`scripts/generate_web_data.py` would need to additionally publish the
relevant `core/manifest.json` dataset fields somewhere the browser can
fetch at snapshot time — e.g. a small generated `web/data/manifest.json`
mirroring the three datasets' `schema_version`/`data_version`/`checksum`,
or embedding the same fields as a sibling key inside each of
`malt.json`/`humle.json`/`gjaer.json`. Either is a real, if small,
publication/build change — the issue's own line for what this round
must not invent.

---

## 9. What this document (and PRI 3A.2) does not do

- Does not implement `.kbhbrew` in App — no new reader/writer/UI code
  is added anywhere (PRI 3B, separately authorized).
- Does not modify `web/README.md` or any Web file other than
  `web/js/brew_storage.js` (Section 2, the required unknown-field
  passthrough fix — the one Web change this ratification round makes).
- Does not migrate any existing App brew-log data or Web brew-history
  data.
- Does not touch `tests/fixtures/legacy/app/brew_log.json` or
  `tests/fixtures/legacy/web/{brew_store_v1,kbhbrew_v1}.json` — all
  three remain byte-identical, frozen compatibility evidence (verified
  by `tests/test_kbhbrew_schema_contract.py`'s legacy-fixture
  validation test, which reads them unchanged).
- Does not change `.kbhrecipe` in any way.
- Does not resolve custom-ingredient identity (PRI 4).
- Does not add a database/backend/cloud requirement — local-first is
  unchanged.
- Does not fold Brew Lab's interpretation activity into `actuals`, and
  does not collapse `sensing`/`learning` into one field.
- Does not fabricate Core manifest provenance in Web — see "Provenance
  implementation status" above for the exact, explicitly documented gap
  and its smallest follow-up.
- Does not touch `raw_data/unmatched_malt.json`.
