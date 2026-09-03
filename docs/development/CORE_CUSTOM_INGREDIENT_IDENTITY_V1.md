# Core Custom-Ingredient Identity Contract V1 (PRI 4A)

Version: 1.0
Status: Active
Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) — this
document is the Core-owned normative contract for stable identity of
**user-defined (custom) ingredients**, a gap both
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §10 and
[CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §9 explicitly left open,
naming it "owned by a future PRI 4." This document is that PRI 4A.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## 1. Purpose and scope

Establishes one Core-wide, namespace-and-format contract for the
stable identity of user-defined malt, hops, yeast, and future
ingredient-like user entities — independent of which application
(App or Web) creates or stores them. This document is **contract-first
only**: it defines semantics and normative documentation. It does not
implement App or Web UI changes, does not migrate any existing user
data, and does not redesign `.kbhrecipe` or `.kbhbrew` (see Section 15).

**In scope:** the identity of an *ingredient definition* a user
creates — the same conceptual slot a canonical master ingredient ID
(`abbey`, `vienna`, `saflager_w3470`, …) occupies, but for
user-authored data instead of Core masterdata.

**Out of scope:** App's `pantry_item_id` (`modules/pantry.py:274`,
`str(uuid.uuid4())`) and any future equivalent — that is a *pantry row*
identity (which inventory entry is this), a different concept from
*ingredient* identity (which ingredient is this), exactly as `.kbhbrew`
already separates `brewId` (row identity) from ingredient references
inside its snapshot. This document governs the latter only.

## 2. Terms

- **Canonical master ID** — an ID Core assigns to an entry in
  `data/master_malt.json` / `master_humle_v2.json` / `master_gjaer_v2.json`
  (mirrored verbatim into `web/data/*.json` by
  `scripts/generate_web_data.py`). Today, always an unprefixed
  lowercase snake_case slug (`abbey`, `bohemian_pilsner_floor`,
  `lalvin_ec1118`).
- **Custom ingredient ID** — an ID identifying a user-defined
  ingredient that has no canonical master entry. This document's
  subject.
- **Legacy custom ID** — a custom ID already in the shape App or Web
  generate today (`custom_<uuid-hex12>`, `egen_malt_*`, `egen_humle_*`,
  `egen_pantry_<type>*`), predating this contract.

## 3. Canonical namespace and ID format

A new custom ingredient ID minted under this contract has the exact
form:

```
kbh-custom-<uuidv4>
```

where `<uuidv4>` is a lowercase, hyphenated, canonical-form RFC 4122
version-4 UUID. Full pattern:

```
^kbh-custom-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$
```

`kbh-custom-` is a single, Core-wide reserved prefix — not one prefix
per ingredient type. There is exactly one custom-ingredient ID
namespace, not a separate one per ingredient type or per storage
location (pantry vs. recipe). This is a deliberate change from Web's
current three separate namespaces (`egen_malt_*` / `egen_humle_*` /
`egen_pantry_<type>*`, see [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md)
§10 and `web/js/pantry.js:20-28`) — see Section 9 for how existing
data is treated.

## 4. Opacity — IDs carry no type semantics

A custom ingredient ID is **opaque**: it encodes no ingredient type
(malt/hops/yeast/future type) and no other semantic content. Which
ingredient type an ID refers to is always established by its
*structural position* — which field or array holds it (`malt[].id`,
`humle[].id`, `gjaerId`, a pantry item's `ingredient_type` field) —
never by parsing the ID string itself.

This is a deliberate contract choice, not a description of current
behavior: Web's existing `egen_malt_*`/`egen_humle_*`/`egen_pantry_<type>*`
prefixes do encode type today. A reader must never rely on that
encoding once this contract applies, because it creates a second,
redundant source of type truth that can drift from the structural
field it duplicates. App's existing `custom_<uuid>` already carries no
type information, so App's convention requires no semantic change
here.

## 5. Generation rules and character/case format

- Generated as `kbh-custom-` followed by a UUIDv4 produced by a
  cryptographically-strong source (`crypto.randomUUID()` in Web,
  `uuid.uuid4()` in Python/App — both already used elsewhere in this
  codebase: `web/js/pantry.js:130-135`, `modules/pantry.py:291-296`).
- Lowercase only, including all hex digits — no uppercase, no
  alternative UUID string formats (no braces, no `urn:uuid:` prefix).
- No timestamp, counter, or other non-random component. This closes a
  documented Web gap: `nyEgendefinertId()`
  (`web/js/app.js:149-152`) mixes `Date.now()` with an in-memory
  counter that resets on page reload, which guarantees only
  intra-session uniqueness, not the collision resistance a UUIDv4
  gives by construction.
- Every user-defined ingredient row — including custom yeast — must
  have a stable custom ID under this contract. This closes a second
  documented Web gap: today, custom yeast (`gjaerCustom`) has **no**
  generated ID at all (`web/js/app.js:1295`, `:1365-1374`); a future
  adapter implementing this contract must mint one, exactly as it does
  for custom malt/hops.

## 6. Uniqueness scope and collision rules

A custom ingredient ID is unique **within one user's local storage
scope** — not globally unique across devices or users, and not backed
by any central registry. This project is local-first (see
[KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) Section 1); no server-side
identity authority exists or is introduced by this document.

Because pantry-defined and recipe-embedded custom ingredients now
share one namespace (Section 3), a generator's collision check must
cover every local storage location that can hold a custom ingredient
ID (pantry, all stored recipes, all stored brews) — not just the
collection it is about to write into.

- **Generation-time collision** (vanishingly unlikely with UUIDv4, but
  a generator must handle it defensively): the generator must
  regenerate a fresh ID rather than silently overwrite existing data
  stored at that ID.
- **Import-time collision**: an imported file's custom ID string that
  already resolves to different existing local data is a **conflict**,
  never a silent merge or overwrite. The normative rule: on conflict,
  the importer mints a **fresh local ID** for the incoming row and
  never reuses the colliding imported ID — mirroring the existing
  reject-on-conflict precedent for `.kbhbrew`'s `brewId`/`originBrewId`
  dedup policy ([CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.3). The
  self-describing `custom`/`gjaerCustom` payload travels with the row
  regardless, so display/calculation is unaffected by the ID being
  reassigned.

## 7. Stability requirements across rename/edit/export/import

- A custom ingredient ID is minted **once**, at creation, and never
  regenerated by a later rename or edit of that same ingredient — this
  matches App's existing documented behavior
  (`modules/pantry.py:292-295`) and is now Core-normative for Web too.
- Export carries the ID verbatim, unchanged.
- Import: if the ID already resolves locally to the *same* logical
  ingredient (i.e. reimporting previously-exported data unchanged), a
  reader must recognize it as the existing entry, not create a
  duplicate. If it collides with *different* local data, Section 6's
  conflict rule applies. If it does not resolve locally at all, the
  self-describing `custom`/`gjaerCustom` sub-object (unchanged by this
  document, see Section 11) already lets a reader display and
  calculate with it without the ID resolving — existing behavior,
  confirmed by [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §10.

## 8. Relation between canonical master IDs and custom IDs

Canonical and custom IDs occupy **disjoint alphabets** by construction,
not by convention alone:

- A canonical master ID must never be assigned a value starting with
  any reserved custom-ID prefix (Section 9's full reserved list).
  Every canonical ID that exists today already satisfies this
  (`abbey`, `vienna`, … — confirmed against
  `data/master_malt.json`/`master_humle_v2.json`/`master_gjaer_v2.json`)
  and this document adds no new canonical IDs, so no rename is
  required.
- A custom ID must always start with a reserved prefix.

This gives any reader a string-prefix test as a defense-in-depth
discriminator between canonical and custom identity, independent of
context — useful in shapes (like a pantry item's `ingredient_id`) that
carry no sibling `custom` object to test presence of instead. It does
**not** replace the existing `.kbhrecipe`/`.kbhbrew` discriminator
(presence of a sibling `custom`/`gjaerCustom` object — Section 11),
which this document leaves untouched.

## 9. Backward compatibility — existing App `custom_<uuid>` and Web `egen_*` IDs

This document does not migrate or invalidate any already-stored ID.
Existing custom ingredient data remains fully valid, readable, and
displayable indefinitely under the existing passthrough guarantees
(Section 11) — nothing about already-stored data breaks.

This contract applies **prospectively**: only a custom ID minted
*after* App/Web adopt it (a future, separately authorized
implementation phase — see Section 10) uses the `kbh-custom-` format.
Existing legacy IDs are grandfathered permanently, and any reader
implementing this contract must treat all of the following prefixes as
equally meaning "this is a custom, non-canonical ID":

| Prefix | Source | Status |
|---|---|---|
| `kbh-custom-` | This contract (Section 3) | Canonical going forward |
| `custom_` | App (`modules/pantry.py:291-296`) | Grandfathered, permanently valid |
| `egen_` | Web, all three existing namespaces (`egen_malt_*`, `egen_humle_*`, `egen_pantry_<type>*`) | Grandfathered, permanently valid |

These three prefixes together are the complete reserved-prefix list
referenced in Section 8 — a canonical master ID must never start with
any of them, now or in the future.

## 10. Migration/adaptation strategy (contract level only)

No existing data is converted by this document. It records the
adaptation path for a future, separately authorized implementation
round:

- App's `_generer_custom_ingredient_id()` (`modules/pantry.py:291-296`)
  and Web's `nyEgendefinertId()` (`web/js/app.js:149-152`) and
  `nyPantryCustomId()`/`_genererId()` (`web/js/pantry.js:130-144`) are
  the exact functions a future implementation phase must change to
  emit `kbh-custom-<uuidv4>` for **newly created** custom ingredients
  only.
- Already-stored data is left exactly as-is — no batch rewrite, no
  forced re-save. A future lazy on-read normalization (rewriting a
  legacy ID to the new format the next time its record is saved) is
  explicitly **not** decided here; it is reserved for that later,
  separately authorized round.
- Web's custom-yeast ID gap (Section 5) and the collapse of Web's three
  namespaces into one (Section 3) are both required changes for that
  future phase, not implemented now.
- App/Web adapter code, migration timing, and UI are explicitly App/Web
  domain decisions (Section 13) — this document only fixes the target
  contract they must converge on.

## 11. Unknown-field/passthrough expectations relevant to `.kbhrecipe`/`.kbhbrew`

This document does not redesign `.kbhrecipe` or `.kbhbrew`. The
existing passthrough guarantees —
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §6 and
[CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.13 — already guarantee that
`id`/`custom`/`gjaerCustom` fields, in any ID format (legacy or the new
`kbh-custom-` form), survive a read → edit → save/export round-trip
unchanged, whether or not the reader recognizes the ID's prefix.
Identity-format recognition (Sections 3–9 above) is layered on top of
that existing guarantee, not a replacement for it: a reader that does
not recognize a well-formed custom ID's prefix must still preserve the
field via unknown-field passthrough, never strip or reject a row purely
because the ID's prefix is unrecognized.

App's current importer (`modules/kbh_import.py`) rejects an entire
`.kbhrecipe` payload outright if any row carries a `custom` object at
all (`KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT`,
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §13,
`tests/test_kbh_import.py:423-436`). That existing behavior is
unchanged by this document — no App/Web UI or import-acceptance change
is in scope here (Section 15).

## 12. Validation and error behavior for malformed or conflicting IDs

- A custom ID that matches neither the new-format pattern (Section 3)
  nor any grandfathered legacy prefix (Section 9) is **not** thereby
  forbidden by this document — the existing whitelist/passthrough
  rules already govern unrecognized data, and this document adds no
  new rejection rule on top of them. Such an ID simply gets no
  "this is custom" recognition from the Section 8 prefix test; where a
  sibling `custom`/`gjaerCustom` object is present, that existing
  discriminator still applies regardless.
- A **malformed** value in the `kbh-custom-` namespace itself (starts
  with `kbh-custom-` but the remainder is not a valid UUIDv4) must
  never be silently corrected, fuzzy-matched, or substituted — the same
  "no smart guessing" principle `.kbhrecipe` already states for
  unresolved ingredient IDs
  ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §11).
- **Generation-time** and **import-time** collisions: see Section 6.

## 13. Ownership boundaries — Core / App / Web

**Core owns** (this document): the reserved namespace prefix and ID
format (Section 3), the opacity decision (Section 4), generation rules
(Section 5), uniqueness scope and collision handling (Section 6),
stability requirements (Section 7), the canonical/custom disjointness
invariant (Section 8), and the reserved-prefix backward-compatibility
list (Section 9).

**App/Web own**: actually implementing generator functions against this
contract, deciding migration/adaptation timing for existing data
(Section 10), and any UI. Neither is changed by this document (Section
15).

## 14. Machine-readable schema

[core/ingredient_identity_v1.schema.json](../../core/ingredient_identity_v1.schema.json)
(JSON Schema, draft 2020-12) encodes Sections 3, 8, and 9 as
machine-checkable patterns: the new `kbh-custom-<uuidv4>` format, the
three grandfathered legacy prefixes, the combined
"recognized-as-custom" union, and a canonical-master-ID shape that
excludes all reserved prefixes. It validates identity *strings* only —
it does not extend `core/kbhbrew_v1.schema.json` or attempt a
`.kbhrecipe` schema (none exists yet, Section 15). Focused tests:
`tests/test_core_ingredient_identity_schema.py`.

## 15. What this document does not do

- Does not implement App or Web UI changes.
- Does not migrate any existing user data — every already-stored
  `custom_*`/`egen_*` ID remains valid and untouched (Section 9).
- Does not modify pantry behavior beyond documenting identity
  semantics — no code in `modules/pantry.py`, `ui/pantry_panel.py`, or
  `web/js/pantry.js` is changed.
- Does not redesign `.kbhrecipe` or `.kbhbrew` — the existing
  `custom`/`gjaerCustom` discriminator, passthrough rules, and import
  rejection behavior are all unchanged (Sections 11, 15).
- Does not change any canonical master ID.
- Does not touch crawler/import automation or `raw_data/*_raw.json`.
- Does not change Web deployment.
- Does not decide lazy on-read ID normalization — reserved for a future
  round (Section 10).
- Does not standardize `pantry_item_id` or any other row/record
  identity — only ingredient identity (Section 1).
