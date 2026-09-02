# Core `.kbhbrew` V1 Contract — Proposal (PRI 3A)

Version: 0.1 — **Proposal, not adopted**
Status: **Draft for owner review.** This document does not become the
governing Core contract until an explicit owner GO records it as
`Status: Active` (the same pattern
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) went through before it was
marked Active). Until then, `.kbhbrew` remains governed only by what
`web/js/brew_storage.js` actually does today — this document formalizes
and questions that behavior, it does not yet replace it.

Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) —
Core owns the shared wire contract; App/Web own their local storage,
UI, and user data (Section 1); Brew Lab owns the observation/
experiment/interpretation activity that happens *around* a brew record,
independent of which application's storage the record physically lives
in (Section 6). See also [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md)
(the sibling `.kbhrecipe` contract, whose conventions this document
follows where applicable) and [CORE_VERSIONING.md](CORE_VERSIONING.md) /
[CORE_STATUS_PROVENANCE.md](CORE_STATUS_PROVENANCE.md) (the general
Core version/provenance model this proposal reuses rather than
reinventing).

**This is PRI 3A: contract discovery/formalization.** It does not
implement `.kbhbrew` in App, does not change `web/js/brew_storage.js`,
does not migrate any user data, and does not decide PRI 4 (custom
ingredient identity). See Section 9, "What this document does not do."

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
  reads a **fixed, named set of fields** off the input object and
  writes nothing else — `actuals` accepts only `og`/`fg`/`volumeL`/
  `notes`; `sensing` only `judgment`/`flavorProfile`/`notes`; `learning`
  only `whatWorked`/`whatChanged`/`nextTime`. **There is no unknown-field
  passthrough anywhere in this file** — contrast with `.kbhrecipe`'s
  explicit `_kbhUkjenteFelt` passthrough container
  (`web/js/kbhrecipe.js`, documented in
  [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §6). Any field outside
  the named set, on any layer, top-level `brew` object included, is
  silently dropped on read, on import, and on every subsequent
  normalize-on-write. This is a real, load-bearing gap relative to the
  sibling contract — see Section 6 and the OWNER DECISION REQUIRED list
  (Section 8).
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
| Frozen ingredient master-data | `snapshot.ingredients.{malt,humle,gjaer}` — full referenced entries, not a hand-picked subset | *(none)* | Needs an explicit Core decision: embed full records vs. reference by id + pinned `data_version` | **OWNER DECISION REQUIRED** (Section 8 #1) |
| Frozen equipment profile | `snapshot.equipment` (or `null`) | *(none — App's `modules/equipment.py` profile is live/global, never frozen per brew)* | Core: optional frozen equipment snapshot | ADAPT |
| Frozen predicted values | `snapshot.predicted.{og,fg,abv,ibu,ebc,buGu,flavorProfile,style}` | *(none per brew — App's `stats`/`flavor_profile` live on the mutable recipe object instead, see §3)* | Core: frozen prediction snapshot, per `KBH_CORE_CONTRACT.md` §2's explicit exception for historical reproducibility | KEEP (concept), shape depends on OWNER DECISION #1 |
| Snapshot provenance | `snapshot.provenance.{engineVersion, recipeSchemaVersion, masterdata: {…count}, capturedAt}` | *(none)* | Core: needed for reproducibility. `core/manifest.json` already provides a stronger per-dataset foundation (`schema_version`, `data_version`, `checksum`) than Web's entry-count proxy; a Core-compliant writer should capture those manifest fields per referenced dataset. Web's entry-count proxy remains readable as legacy/de-facto provenance on brews already captured under it | ADAPT |
| Status | `status ∈ {active, done, discarded}`, freely reassignable metadata | *(none)* | KEEP | KEEP |
| Judgment | `sensing.judgment ∈ {yes, maybe, no}` | *(none)* | KEEP | KEEP |
| Measured actuals: OG/FG/volume | `actuals.{og, fg, volumeL}` (canonical SG points, liters) | `actual_og`, `actual_fg`, `actual_volume_l` (same canonical units, snake_case) | KEEP concept; naming/casing convergence is a product decision, not a wire-contract blocker | ADAPT |
| Actual ABV | **Never stored** — always `faktiskAbv()` from actuals | **Stored explicitly** (`actual_abv`, precomputed by the UI) | Wire contract only: never authoritative, always recomputable from `actuals.{og,fg}`, never required on write. Does not require App to change its local storage — App's cached copy is product-local and out of scope | **OWNER DECISION REQUIRED** (Section 8 #3) whether the wire schema omits the field entirely or allows it as optional/non-authoritative; App's local field is APP_ONLY either way |
| Actual process used | *(absent — Web's actuals has no process-used field at all)* | `process_profile_navn` (name string only, no full profile) | A genuinely new candidate Core field ("what was actually done"), not yet present on either side in a complete form | DEFER (needs its own design, same caution `.kbhrecipe`'s `prosess` field already required) |
| Measurement/observation notes | `actuals.notes` (measurement-adjacent) + `sensing.notes` (tasting-adjacent) — two distinct fields | `note` — a single merged field covering both | Core V1 wire shape: both `actuals.notes` and `sensing.notes`, optional and independent, matching Web (§5.8) — not an open wire question | KEEP (Web's two-field shape); App's single `note` → this shape is a deferred adapter/migration question, **OWNER DECISION REQUIRED** only for that mapping (Section 8 #4) |
| Sensory flavor profile | `sensing.flavorProfile` (numeric map, same axes as predicted) | *(none)* | KEEP | KEEP |
| Learning: whatWorked/whatChanged/nextTime | `learning.{whatWorked, whatChanged, nextTime}` | *(none)* | KEEP | KEEP |
| Timestamps | `createdAt` + `brewedAt` (both ISO 8601, distinct meanings) | `date` only (a single date; ambiguous whether it means "brew day" or "log entry day" — in practice always brew day) | Core: needs at least a "when brewed" timestamp; `createdAt` (record creation) vs. `brewedAt` (the actual brew day) is a real, useful distinction Web already draws | ADAPT |
| Unknown-field passthrough | **Absent.** All four normalizers whitelist fields and silently drop anything else | N/A (flat list; no schema-aware writer to lose data from) | `.kbhrecipe` already requires this ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §6); `.kbhbrew` currently provides no equivalent guarantee | **OWNER DECISION REQUIRED** (Section 8 #2) |
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
discardable, not as data loss. Section 8 #3 records the narrower,
still-open question this leaves: whether the wire schema should
tolerate an optional, explicitly non-authoritative `actual_abv` field
at all, or omit the concept from the wire entirely.

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

**Proposed, not yet implemented anywhere**: a Core-compliant
`.kbhbrew` reader/writer should preserve unknown fields on every layer,
the same way `.kbhrecipe` already does via its passthrough container
(`_kbhUkjenteFelt` / `_kbh_passthrough`). Today's Web implementation
does **not** do this (Section 2) — see Section 8 #2 for the explicit
owner decision on whether V1 requires closing this gap before being
called "Active," or defers it.

### 5.14 Import identity / duplicate/copy behavior

As Section 5.3: dedup on `originBrewId`, fresh `brewId` always minted
on import, explicit duplicate signal rather than silent re-creation or
silent overwrite/merge.

### 5.15 Forwards/backwards compatibility expectations

A reader that only understands `version: 1` must detect and reject
(never silently misinterpret) any other envelope `version`, mirroring
the existing `.kbhrecipe` pattern. Because today's Web normalizers
whitelist fields rather than preserving unknowns (§5.13), a *future*
additive V1.1 field would currently be silently dropped by today's Web
reader on any round-trip through it — this is a real, existing forward-
compatibility gap, not a hypothetical one, and is part of why passthrough
(Section 8 #2) matters even for a same-major-version evolution.

### 5.16 Validation: reject vs. normalize vs. preserve

- **Reject outright**: unsupported envelope `format`/`version`; a
  missing/invalid `brewId` or `status` on the top-level record; a
  missing/invalid snapshot (`recipe` object, `predicted` object).
- **Normalize**: numeric-ish actuals/sensing values coerced the way
  Web's `_tallEllerUndefined()`/`_tekstEllerUndefined()` already do
  (accept a parseable number/non-empty trimmed string, drop otherwise) —
  this is tolerant-input normalization, not silent semantic
  reinterpretation.
- **Preserve**: everything else — see §5.13 (proposed policy) and
  Section 8 #2 (open question on whether V1 requires it).

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
Yes, *in practice*, because Web today only ever writes fields already
in its own whitelist — so export→import→export reproduces the same
data. But this is a **coincidence of current behavior, not a structural
guarantee**: there is no forward-compatibility margin (§5.15), and any
field a future writer adds without also updating the four normalizer
functions would be silently dropped on the very next read.

**Can current Web `.kbhbrew` be treated as Core V1 as-is?**
Recommended: **yes, as the de facto V1 baseline**, with two explicit,
un-guessed caveats that keep this from being a blind rubber-stamp:

1. It currently provides no unknown-field passthrough guarantee
   (Section 8 #2) — calling it "Core V1, final" without deciding this
   would silently lock in a weaker guarantee than `.kbhrecipe` already
   has.
2. Its ingredient-embedding approach (full master-data copies, not
   id+version references) is a real architectural choice with
   tradeoffs neither this document nor the existing code has settled
   as a deliberate Core decision — it has simply never been questioned
   until this task (Section 8 #1).

Subject to those two being explicitly resolved by the owner, nothing
else in Web's current model needs to change to serve as Core V1: no
backwards-incompatible reader adaptation is required, and it should
**not** be treated as a mere "product-local pre-Core format" — it is
already the only implementation that satisfies the five-layer model,
the identity policy, and the derived-value discipline this document
recommends adopting.

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

## 7. Machine-readable schema — deferred, not built this round

The issue's own governing instruction is explicit: *"If, and only if,
the evidence supports a stable V1 shape without making unresolved
owner decisions, add a machine-readable schema... If a genuinely
architectural owner decision blocks a safe schema, do not guess."*

Section 8 lists two decisions (#1: ingredient embedding vs. reference;
#2: passthrough requirement) that directly determine the **shape** of
`snapshot.ingredients`/`snapshot.equipment` and of every layer's
tolerance for extra fields — a JSON Schema written before either is
resolved would either (a) hard-code today's Web shape as permanent
Core law without an owner having actually chosen it, or (b) need to be
rewritten the moment either decision lands. Neither outcome is
acceptable per the issue's own guardrail against silently making a new
irreversible product/ownership decision.

**No `.kbhbrew` JSON Schema is added in this PR.** This document itself
is the deliverable for PRI 3A's Section 3 (normative contract); a
machine-readable schema is proposed as the concrete next step once
Section 8's items are resolved (see Section 8's closing note).

---

## 8. Owner decisions required

### 1. Ingredient/equipment snapshot: embed full records, or reference by id + pinned version?

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
- **Recommendation for the owner's consideration** (not a decision
  made here): Option A, pragmatically, until Option B's prerequisite
  (a real historical masterdata archive) exists — but this is exactly
  the kind of "irreversible-ish wire format decision" this document
  must not make unilaterally.

### 2. Is unknown-field passthrough required for `.kbhbrew` V1?

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

- **Option A — add it now**, since both implementations already gesture
  at it (App has a name-only string; Web has none at all) and it fits
  naturally as a layer-3 actual.
- **Option B — defer it (recommended default absent an owner steer)**,
  consistent with `.kbhrecipe`'s own documented caution around its
  `prosess` field (`CORE_KBHRECIPE_V1.md` §13's KBHR-018 discussion) —
  a full process-profile-shaped actual is more design work than this
  discovery task should absorb.

**Once these are resolved**, the concrete next implementation step
(explicitly requested by the issue's acceptance criteria) is: (a) bump
this document to `Version: 1.0`/`Status: Active` reflecting the actual
decisions made, (b) write the machine-readable JSON Schema deferred in
Section 7, with contract fixtures alongside it (mirroring
`tests/fixtures/legacy/`'s pattern), and (c) only then scope PRI 3B
(actual App `.kbhbrew` implementation) as its own, separately
authorized issue.

---

## 9. What this document does not do

- Does not implement `.kbhbrew` in App — no new reader/writer/UI code
  is added anywhere.
- Does not modify `web/js/brew_storage.js`, `web/README.md`, or any
  other Web file.
- Does not migrate any existing App brew-log data or Web brew-history
  data.
- Does not touch `tests/fixtures/legacy/app/brew_log.json` or
  `tests/fixtures/legacy/web/{brew_store_v1,kbhbrew_v1}.json` — all
  three remain byte-identical, frozen compatibility evidence.
- Does not change `.kbhrecipe` in any way.
- Does not resolve custom-ingredient identity (PRI 4).
- Does not add a database/backend/cloud requirement — local-first is
  unchanged.
- Does not fold Brew Lab's interpretation activity into `actuals`, and
  does not collapse `sensing`/`learning` into one field.
- Does not add a machine-readable schema (Section 7) — deliberately
  deferred pending Section 8's owner decisions.
- Does not touch `raw_data/unmatched_malt.json`.
