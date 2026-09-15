# Core `.kbhrecipe` Origin Identity — Decision Preflight (issue #276)

Status: **DECISION preflight — one recommended contract stated below;
not authorized for implementation by this document alone.** Awaiting
owner/Chief review. If accepted, a separate, later round updates
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) (§3, §7) to reference this
document exactly as it already references
[CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md](CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md)
(§10) — not performed here.

Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0, Core
domain). Precisifies a gap
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §14 explicitly leaves open
("Does not implement `recipeId`/`originRecipeId` end-to-end identity"),
using [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.3's already-ratified
`brewId`/`originBrewId` split as the implementation precedent this
document reuses, per the issue's own instruction not to invent a second
identity system.

Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3C. Core-owned follow-up from merged Phase 3C decision brief
[#270](https://github.com/Joludvig/kvernhaug-brygghus/issues/270) / PR
[#274](https://github.com/Joludvig/kvernhaug-brygghus/pull/274)
(`docs/development/phase3c_brew_data_handoff_contract_decision_brief.md`
§4.2, Recommendation B), which proposed adding `originRecipeId` but
explicitly deferred the full contract design to this issue. This
document also corrects one imprecision in that brief — see §3.9.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## 0. Baseline

| Item | Value |
|---|---|
| Issue | [#276](https://github.com/Joludvig/kvernhaug-brygghus/issues/276) |
| `origin/master` at start of this task | `12c374ab224a40e4789baf2176f1624c05557c71` |
| Branch | `agent/issue-276` |
| Date | 2026-09-15 |
| Method | Direct source read of `modules/kbh_contract.py`, `modules/kbh_import.py`, `modules/recipe.py`, `modules/recipe_storage.py`, `ui/recipe_card.py`, `modules/kbhbrew.py`, `modules/kbhbrew_storage.py`, `web/js/kbhrecipe.js`, `web/js/recipe_storage.js`, `web/js/app.js`, `web/js/brew_storage.js`, plus the three governing docs ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md), [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md), [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md) §6–§7) and all three legacy `.kbhrecipe` fixtures. No product file, fixture, or schema was changed to produce this document. |

---

## 1. Current source truth

### 1.1 This is a documented-but-never-implemented gap, not a new idea

The **superseded but back-compat-respected** legacy contract already
named this concept, before `.kbhbrew` existed:
[KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md) §6–§7 (2026-08-15)
already specifies two distinct identifiers — "Local identity —
`recipeId`" and "Historical link — `originRecipeId`" — with a minting
rule for App ("Streamlit may hold an internal `recipe_id`. If it is
missing: a `uuid4` is generated; it is written atomically back to that
one recipe file only; this happens only on an explicit, user-triggered
export; it never happens as a background migration") and a purpose
statement for `originRecipeId` ("linking a recipe to a later brew,"
"tracing experience back to the correct recipe," "preserving identity
across file movement between systems"). [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md)
(the *active* precisification) never precisified this part and says so
explicitly in its own §14. A repo-wide grep for `originRecipeId` across
`modules/` and `web/js/` returns **zero hits** (confirmed again this
session) — the concept was written down twice (V1 §7, the phase3c
brief) and built zero times. This document's job is to finally
precisify it, using `.kbhbrew`'s production-proven implementation of
the *same conceptual split* as the concrete blueprint V1 §7 lacked in
2026-08-15 — not to invent a new pattern.

### 1.2 `recipeId` today — pure local identity, asymmetric between App and Web

- **Web has a `recipeId`.** Minted by `_genererRecipeId()`
  (`web/js/recipe_storage.js:52`) the first time a recipe is saved to
  the local store (`web/js/recipe_storage.js:126`); lives in the store
  wrapper (`{recipeId, recipe}`, `recipe_storage.js:106`), **not**
  inside the `recipe` payload itself; explicitly stripped before
  writing a `.kbhrecipe` file (`recipe_storage.js:90`,
  `web/js/kbhrecipe.js:206-221`, comment: *"En recipeId er LOKAL
  identitet, aldri global. Den skrives derfor aldri [til fil]"*).
- **App has no `recipeId` concept at all.** Confirmed: zero hits for
  `recipe_id`/`recipeId` anywhere under `modules/recipe.py`,
  `modules/recipe_storage.py`, `modules/kbh_contract.py`,
  `modules/kbh_import.py`. App identifies a recipe purely by its
  filename (`modules/recipe_storage.py::generer_filnavn()`), which is
  a storage-layer convenience, not an identity field carried inside the
  data — the exact same asymmetry [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md)
  §3 already documented for App's brew log ("addressed only by the
  recipe's name... not itself a stable identity"). V1 §6's own text
  ("Streamlit may hold an internal `recipe_id`") describes a mechanism
  that was **written but never built** — it is available, unused
  precedent for §4.1 below, not a description of current App behavior.
- Both sides agree `recipeId` must never appear in an exported file:
  App `modules/kbh_contract.py:50`
  (`_FORBUDT_I_PASSTHROUGH_VED_REEKSPORT`) and
  `modules/kbh_import.py:64` (`_FORBUDTE_PAYLOAD_FELT`); Web
  `web/js/kbhrecipe.js` `KBHRECIPE_FORBUDTE_FELT` (line 68), enforced
  at both export (line 153) and import (lines 221/227/229, explicit
  `delete o.recipeId`). [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §7
  is unchanged by this document.

### 1.3 `.kbhbrew`'s `originBrewId` — the precedent, precisely

Full lifecycle, both sides, confirmed field-for-field identical:

- **Creation** defaults origin to the fresh local id:
  App `modules/kbhbrew.py:372` (`"originBrewId": brew_id`, inside
  `bygg_ny_brew()`); Web `web/js/brew_storage.js:475`
  (`originBrewId: brewId`, inside `opprettBrygg()`).
- **Import always mints a fresh local id and preserves the file's
  origin verbatim.** App `modules/kbhbrew.py:665-667` validates
  `originBrewId` is a non-empty string and **rejects the whole import**
  if not (`KATEGORI_INVALID_BREW`); the reader never includes `brewId`/
  `recipeId` in its output at all (comment, `kbhbrew.py:626-630`,
  "import as new"). The actual local id is minted by
  `modules/kbhbrew_storage.py:286` (`f"brew-{uuid.uuid4()}"`), never by
  the reader. Web mirrors this at `web/js/brew_storage.js:751-773`,
  with one difference noted in §3.8 below.
- **Duplicate detection**: exact string-equality scan of every locally
  stored brew's `originBrewId` against the incoming value. App:
  `modules/kbhbrew_storage.py:154-157`
  (`finnes_brew_med_origin`) → checked *before* minting
  (`kbhbrew_storage.py:283-284`), returns
  `{"ok": False, "duplicate": True, "originBrewId": origin}`, nothing
  written. Web: `web/js/brew_storage.js:751-755`, returns
  `{ok: false, duplikat: true, ...}`. Neither side attempts to
  distinguish "duplicate with identical content" from "duplicate with
  different content" — **any** match is rejected outright, never a
  silent merge or overwrite (§1.5 below).
- **No update path ever touches `originBrewId` after creation.** App
  `modules/kbhbrew_storage.py:206-241` (`oppdater_brew_lag()`) only
  ever writes `actuals`/`sensing`/`learning`/`status`/`brewedAt`. Web's
  `oppdaterBrygg()` spreads `...forrige` without overriding
  `originBrewId`. It is fixed for the life of the record.
- **No "copy"/"duplicate brew" feature exists anywhere** (App or Web) —
  confirmed by a broad grep for "kopier"/"duplicate"/"clone"/"lagre som
  ny" restricted to brew code; the only `clone`-adjacent hits are
  unrelated DOM template cloning. So `.kbhbrew` offers **no direct
  precedent** for §3.5's "copy/save-as-new" question below — that
  question must be answered fresh for `.kbhrecipe`, using Web's
  existing recipe-side "save as new" feature (§1.4) as the closest real
  precedent instead.

### 1.4 An existing "save as new" feature already exists for recipes — and already resets local identity

- **Web**: `lagreSomVariant()` (issue #106, `web/js/app.js:1683-1704`)
  — line 1692: `lagreOppskriftIStore(oppskrift, null); // null tvinger
  frem en FERSK recipeId`. Web's own existing "save as new" precedent
  **always** mints a fresh local `recipeId` for the copy; it never
  preserves the source recipe's local identity.
- **App**: `ui/recipe_card.py:212-226`, "💾 Lagre som ny kopi" →
  `lagre_oppskrift(ny_recipe, kilde_filnavn=None,
  bloker_ved_navnekollisjon=True)`. Since App has no `recipeId` at all
  (§1.2), there is nothing on this axis to reset today — the button's
  entire effect on identity is "no known source filename."

This is the correct precedent for §3.5, not `.kbhbrew` (§1.3's last
bullet) — because `.kbhrecipe` already has a live "save as new" feature
and `.kbhbrew` does not.

### 1.5 Malformed/conflicting-origin validation — exact, and asymmetric between App and Web

- The only type/shape check either side performs on `originBrewId` is a
  shared "non-empty string" test — App's `_ikke_tom_streng()`
  (`modules/kbhbrew.py:104-105`: `isinstance(v, str) and v.strip() !=
  ""`), applied identically to `createdAt` etc.; Web's inline
  equivalent (`brew_storage.js:752`:
  `typeof filBrew.originBrewId === "string" && filBrew.originBrewId`).
  Neither side has a dedicated `originBrewId`-specific validator (Web's
  `_gyldigBrew()`, `brew_storage.js:225-230`, checks `brewId`/`status`/
  `snapshot`, not `originBrewId`).
- **App rejects a missing/invalid `originBrewId` outright** at both
  import (`kbhbrew.py:665-667`) and export
  (`kbhbrew.py:456-458`, raises `ValueError`) — because `.kbhbrew` V1
  has **no legacy wrapperless fallback** to accommodate
  ([CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.2): every `.kbhbrew`
  file that has ever existed already carries a valid `originBrewId`, so
  a missing one can only mean a malformed/hand-edited file, safe to
  reject.
- **Web is more permissive on read**: `origin || _genererBrewId()`
  (`brew_storage.js:773`) silently mints a fresh id if the incoming
  value is missing/invalid, rather than rejecting the import. This is
  a real, small App/Web divergence in `.kbhbrew` itself, not something
  this document invents.
- **No "same origin, different content" reconciliation exists
  anywhere.** The duplicate check is a flat string-equality scan; a
  match is always a full-stop rejection, never a diff/merge attempt.
  This absence-of-a-feature is itself the precedent §3.4/§3.8 reuse.

### 1.6 Zero parent/lineage prior art for recipes

Grepping `parent|lineage|forelder` across `modules/` and `web/js/`
returns only `.kbhbrew`'s own `parentBrewId` (reserved, always `null`,
no V1 semantics — [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.3). No
`parentRecipeId`, no lineage concept, and no product requirement for
one exists anywhere in this codebase today. See §3.10.

### 1.7 Today's passthrough would silently swallow a stray `originRecipeId`

Neither engine's known-field list (App:
`modules/kbh_contract.py:39-42` write-side,
`modules/kbh_import.py:52-55` read-side; Web:
`KBHRECIPE_KJENTE_FELT`, `kbhrecipe.js:59-63`) or forbidden-field list
(§1.2 above) currently mentions `originRecipeId` at all. Concretely,
this means: **today**, a hand-crafted `.kbhrecipe` file that already
happens to carry an `originRecipeId` key would be silently captured
into generic passthrough (App's `_kbh_passthrough`, Web's
`_kbhUkjenteFelt`) and round-tripped opaquely, with zero recognition as
identity. This is not a bug to fix by this document (it is correct,
conservative behavior for a genuinely unknown field) — it is the exact
gap §4/§6 below closes: promoting `originRecipeId` out of generic
passthrough into a first-class, actively-owned optional field is the
concrete code change a future implementation round must make.

### 1.8 Legacy fixtures confirmed clean

`tests/fixtures/legacy/kbhrecipe/{full,minimal,partial_water}.json` —
grepped for `recipeId`/`origin`: **zero matches in all three.** No
existing fixture already carries anything resembling `originRecipeId`;
nothing here needs reconciling with a pre-existing value.

---

## 2. Options and tradeoffs

### 2.1 Should `.kbhrecipe` gain a portable origin field, and does it require a version bump?

- **Option A — additive optional payload field, no version change
  (recommended, §3).** `originRecipeId` joins
  [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §3's "Optional known V1
  fields" list, exactly like `brygger`/`bryggeri`/`gjaerId` already do.
  Envelope `version` stays `1`; `recipeSchemaVersion` stays `1`. This
  is the same category of change `.kbhbrew` already made once without
  a version bump (adding required unknown-field passthrough,
  [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.13/Section 8 #2) and is
  explicitly the category [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md)'s
  own header already allows ("This document does not introduce
  `.kbhrecipe` V2 — `.kbhrecipe` remains `version: 1`").
- **Option B — a new `.kbhrecipe` V2 envelope.** Rejected: nothing
  about this addition changes the shape of any *existing* required or
  optional field, breaks no existing reader (a reader that doesn't know
  the field simply doesn't recognize it — no different from any other
  optional field today), and requires no reinterpretation of
  `recipeSchemaVersion`. A V2 would be proportionate to a breaking
  reshape, which this is not.

**Answer to the issue's explicit question: V1 can gain this field
compatibly. A V2 is not required, and this document does not propose
one.**

### 2.2 Where does the field live — envelope or payload?

- **Option A — inside the `recipe` payload (recommended).** Mirrors
  `.kbhbrew`'s own placement: `originBrewId` lives on the `brew` object
  (the payload), not the `{format, version, exportedAt, generator,
  brew}` envelope. A payload-level field also survives extraction the
  same way `recipeSchemaVersion` already must
  ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §9: "travels *inside*
  the payload... so it survives extraction into a `.kbhrecipe` file or
  a future `.kbhbrew` snapshot on its own").
- **Option B — envelope-level field.** Rejected: the envelope already
  has a fixed, narrow, non-recipe-specific shape
  (`format`/`version`/`exportedAt`/`generator`); nothing else recipe-
  identity-shaped lives there today, and putting it there would also
  need to be re-derived if a recipe payload is ever embedded elsewhere
  (e.g. inside a future `.kbhbrew` snapshot's `recipe` field) the same
  way `recipeSchemaVersion` already is.

### 2.3 What should App's origin-minting mechanism be, given App has no `recipeId` to default from?

- **Option A — reuse V1 §6's already-specified, never-built mechanism
  (recommended, §3.2).** [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md)
  §6 already specifies, for App: mint a `uuid4` if missing, write it
  back atomically to that one recipe file only, only on an explicit
  user-triggered export, never as a background migration. This
  document reuses that exact mechanism for `originRecipeId`'s App-side
  default, since it is the closest already-authorized precedent and
  §1.2 confirms it was specified but never implemented — reusing it
  costs nothing new to invent.
- **Option B — invent a new App-side default rule.** Rejected: no
  reason exists to design something new when an already-normative,
  unimplemented mechanism fits exactly and needs no adaptation.

### 2.4 Copy/"save as new" — reset or preserve `originRecipeId`?

- **Option A — reset (recommended, §3.5).** "Save as new"/"Lagre som
  variant" mints a fresh `originRecipeId`, exactly as Web's existing
  `lagreSomVariant()` already resets local `recipeId` (§1.4). Rationale:
  `originRecipeId`'s *only* job is import-time dedup detection
  (§3.4). If a deliberate fork kept the source's `originRecipeId`, a
  later export of that fork would collide with the original recipe's
  origin on any future import — exactly the false "duplicate" this
  document exists to prevent for the *genuine* duplicate case,
  triggered instead by an action whose entire point was to create an
  intentionally independent copy.
- **Option B — preserve.** Rejected: contradicts the field's own
  purpose (§2.4 Option A) and has no supporting precedent — `.kbhbrew`
  has no "copy" feature to draw an analogy from (§1.3), and Web's own
  existing "save as new" behavior already resets the sibling local-
  identity field for the same underlying reason.

### 2.5 Missing/malformed `originRecipeId` on import — reject (like `.kbhbrew`) or tolerate (diverge)?

- **Option A — tolerate: treat as "no dedup signal available," proceed
  as new (recommended, §3.6/§3.8).** `.kbhbrew` can safely reject a
  missing origin because it has no legacy corpus without one
  (§1.5) — that precondition does **not** hold for `.kbhrecipe`: every
  `.kbhrecipe` file exported before this contract lands, including all
  three frozen legacy fixtures (§1.8), lacks `originRecipeId` by
  construction, and must keep importing successfully forever (§6).
- **Option B — reject, mirroring `.kbhbrew`'s strict reader exactly.**
  Rejected: would break every existing `.kbhrecipe` file and fixture on
  import the moment this contract lands, directly contradicting
  backward compatibility (§6) and the issue's own required point
  ("backwards compatibility with every current V1 file").

---

## 3. Recommended contract

### 3.1 Field definition

A new **optional** field on the `.kbhrecipe` V1 payload (§2.2 Option
A):

```
originRecipeId: string   (optional on read; required in a
                           canonical writer's output once
                           this contract is implemented)
```

`recipeId` is completely unchanged: still each surface's pure local
storage identity, still minted locally (Web only — App has none, §1.2),
still unconditionally forbidden from ever appearing in an exported file
([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §7, untouched by this
document).

### 3.2 Creation / default-minting rule

- **Web**: `originRecipeId` defaults to the recipe's existing local
  `recipeId` at first save, exactly mirroring `.kbhbrew`'s
  `originBrewId: brewId` default (`brew_storage.js:475`). Stored inside
  `item.recipe.originRecipeId` (the payload sub-object
  `recipe_storage.js` already stores per item), not the store wrapper —
  consistent with §2.2's "payload, not local metadata" placement.
- **App**: has no local id to default from (§1.2), so it uses V1 §6's
  already-specified, never-implemented mechanism (§2.3 Option A): mint
  a fresh UUID for `originRecipeId` **only** if the recipe's saved file
  does not already have one, write it back atomically to that one
  recipe file, **only** on an explicit, user-triggered export action —
  never as a background migration, never on mere load/edit.
- Once minted (either side), `originRecipeId` is persisted with the
  recipe's own stored data and never re-minted by a later plain
  edit/re-save — mirroring `.kbhbrew`'s "no update path ever touches
  `originBrewId`" rule (§1.3).

### 3.3 Export rule

A canonical `.kbhrecipe` writer includes `originRecipeId` in every
export once the recipe has one (i.e., after the first export under
this contract). `recipeId` continues to never appear (§7, unchanged).

### 3.4 Import / duplicate-detection rule

On import, scan every locally stored recipe's `originRecipeId` against
the incoming file's value using **exact string equality** — identical
mechanism to `.kbhbrew`'s `finnes_brew_med_origin` (§1.3):

- **Match found** → explicit duplicate result
  (`{ok: false, duplicate: true, originRecipeId: <value>}` /
  `{duplikat: true}`, mirroring `.kbhbrew`'s existing shape exactly).
  Import is refused; nothing is written. Never a silent second copy,
  never an automatic merge/overwrite — matching `.kbhbrew`'s posture
  and closing the exact gap phase3c brief §3.4 documented as live.
- **No match, and the incoming value is present** → import proceeds as
  a new local recipe, carrying the imported `originRecipeId` forward
  unchanged (the imported recipe's own origin travels with it, exactly
  as `.kbhbrew` preserves an imported brew's origin, §1.3).
- **Missing / empty / non-string `originRecipeId`** (a pre-existing
  legacy file, or a malformed value) → treated as "no dedup signal
  available." Import proceeds as new, exactly as it does today (no
  regression for any file that predates this field) — the deliberate,
  justified divergence from `.kbhbrew`'s stricter reader (§2.5).
- **No "same origin, different content" reconciliation** — any match is
  a full-stop duplicate rejection regardless of whether the content
  actually differs, mirroring `.kbhbrew`'s identical simplicity
  (§1.5). No field-level diff/merge is introduced.

### 3.5 Copy / "save as new" semantics

"Save as new" (Web: `lagreSomVariant()`, `web/js/app.js:1683-1704`;
App: "💾 Lagre som ny kopi," `ui/recipe_card.py:212-226`) mints a
**fresh** `originRecipeId` for the new copy, in addition to whatever it
already resets on the local-identity axis (Web already resets local
`recipeId`, §1.4; App gains this behavior new, since it had no
identity to reset before). A plain edit-and-re-save of the *same*
recipe (not "save as new") leaves `originRecipeId` unchanged.

### 3.6 Imported-recipe-already-exists-locally behavior

Covered by §3.4's duplicate rule directly — this is the exact scenario
that rule exists for. No additional mechanism is needed.

### 3.7 Unknown-field passthrough / promotion out of generic passthrough

`originRecipeId` moves from "generic unknown field, silently
passed-through" (§1.7, today's actual behavior) to a first-class,
actively-recognized optional field in both engines' known-field lists
— the same fix already applied once for `.kbhbrew` when Web's
normalizers gained explicit passthrough handling
([CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §5.13). Every other unknown
field's passthrough behavior is completely unchanged by this document.

### 3.8 Malformed / conflicting origin handling

- Non-string or empty-string `originRecipeId` on import: never
  rejects the whole import (§2.5/§3.4) — treated as absent.
- `originRecipeId` colliding with a *different* local recipe's origin:
  always the duplicate-rejection path (§3.4), never a silent
  overwrite, never a merge attempt — no exception for "looks like the
  same content."
- No writer ever accepts an externally-supplied `originRecipeId`
  override on a plain edit (§3.2's last bullet) — the only two ways
  `originRecipeId` is ever set are "mint at first export" (§3.2) and
  "carry forward from an imported file" (§3.4).
- **This document deliberately does not adopt `.kbhbrew`'s
  reject-on-missing-origin reader policy** (§1.5's App behavior) for
  `.kbhrecipe` — see §2.5 for why that asymmetry is required, not an
  oversight.

### 3.9 App/Web adapter implications — and a correction to the phase3c brief

The phase3c brief's Recommendation B acceptance criterion 3 states
"Both App and Web mint `originRecipeId = recipeId`" — **this is
imprecise for App**, which has no `recipeId` field at all (§1.2,
confirmed by source read this session, not merely repeated from the
brief). §3.2 above states the corrected, source-grounded per-surface
mechanism. This correction does not change the brief's Recommendation
B *decision* to add `originRecipeId` — only the exact App-side
mechanism, which this document now specifies precisely for the first
time.

Concrete touchpoints for a future implementation issue (none built
here):

**App**: `modules/kbh_contract.py` (writer: add `originRecipeId` to
the optional-known-field set; implement the §3.2 first-export minting
rule); `modules/kbh_import.py` (reader: recognize `originRecipeId`
instead of routing it to `_kbh_passthrough`; §3.4's duplicate check);
`modules/kbh_import_apply.py` (wire the duplicate result into the
apply path); `modules/recipe.py` / `modules/recipe_storage.py` (native
`originRecipeId` field on the stored recipe object; a local scan across
every stored recipe file for §3.4's duplicate lookup); `ui/sidebar.py`
(surface the duplicate result in the existing import expander, per
[CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §13's "Not yet wired into
a Streamlit import UI" note — now stale per phase3c brief §2, since the
UI already exists); `ui/recipe_card.py` ("Lagre som ny kopi" must mint
a fresh `originRecipeId`, §3.5).

**Web**: `web/js/kbhrecipe.js` (`KBHRECIPE_KJENTE_FELT`/
`KBHRECIPE_EKSPORTERBARE_FELT`: add `originRecipeId`; §3.4's duplicate
check, mirroring `web/js/brew_storage.js`'s `importerBrygg()` shape);
`web/js/recipe_storage.js` (persist `originRecipeId` inside
`item.recipe`; §3.2's default-at-first-save rule; a duplicate scan
across `alleOppskrifter()`); `web/js/app.js` (`lagreSomVariant()`,
§3.5, must also reset `originRecipeId`); `web/importer.html` /
`web/index.html` (surface the duplicate result in the existing import
UI, mirroring the "already imported" messaging pattern
[Recommendation A](phase3c_brew_data_handoff_contract_decision_brief.md#41-recommendation-a--wire-webs-already-built-kbhbrew-file-layer-to-a-ui)
will need once it ships).

### 3.10 Parent/lineage concept — NOT NOW

No `parentRecipeId` or equivalent lineage field is added. §1.6
confirms zero current prior art or product requirement for one
anywhere in this codebase — unlike `.kbhbrew`'s `parentBrewId`, which
was reserved at ratification time for a specific named future scenario
("shared batch, same wort, two fermenters"), no analogous concrete
scenario has been identified for recipes. Per the issue's own
instruction ("prefer NOT NOW unless evidence requires it"), this
document does not speculatively reserve a field for it either — a
future document may add one if and when a real need is identified,
following the same additive-field discipline this document itself
establishes (§2.1).

---

## 4. Exact wire/schema implications

- Envelope: unchanged. `{format: "kbhrecipe", version: 1, exportedAt,
  generator, recipe: {...}}` — no new envelope field, no version bump.
- Payload (`recipe`): one new optional field, `originRecipeId`
  (string), joining [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §3's
  "Optional known V1 fields" list. `recipeSchemaVersion` (§9 there)
  stays `1` — this is an additive field, not a shape-breaking change to
  the payload's required structure.
- §7's forbidden-field list is **unchanged** — `originRecipeId` is
  explicitly not added to it (the opposite: it is required-on-write /
  optional-on-read, §3.1).
- No machine-readable schema exists for `.kbhrecipe` today (confirmed:
  `core/` contains `kbhbrew_v1.schema.json` but no `.kbhrecipe`
  equivalent) — this document does not create one. If a future round
  writes `core/kbhrecipe_v1.schema.json`, `originRecipeId` should
  appear there as an optional string field, following
  `core/kbhbrew_v1.schema.json`'s existing pattern for `originBrewId`
  (optional at the schema level, since a local-only record may not
  have exported yet).

---

## 5. Backwards-compatibility statement

Every `.kbhrecipe` file that exists today — including all three frozen
legacy fixtures (§1.8), and every recipe currently stored on any user's
App installation or Web browser — lacks `originRecipeId` and **must
remain fully readable, forever**, not merely during a transition
window. §3.4's explicit rule ("missing → no dedup signal available,
import proceeds as new") is this guarantee's precise mechanism, not an
incidental side effect: a missing `originRecipeId` is never treated as
an error, never rejected, and never fabricated by a reader on someone
else's behalf. This document's own recommendation (§2.5 Option A) was
chosen specifically because `.kbhbrew`'s stricter reader policy would
have broken this guarantee (§2.5 Option B). No existing fixture,
`recipeSchemaVersion`, or envelope `version` value changes meaning as a
result of this document.

---

## 6. App/Web implementation touchpoints

See §3.9 for the complete file-level list (App and Web). Test
touchpoints for a future implementation round: `tests/test_kbh_contract.py`,
`tests/test_kbh_import.py`, `tests/test_kbh_import_apply.py`,
`tests/test_kbh_import_ui_apptest.py`, `tests/test_web_js_kbhrecipe.py`
— each extended with §3.2/§3.4/§3.5/§3.8 coverage; a new JS contract
test mirroring `tests/js/test_kbhbrew_contract.js`'s round-trip pattern
would be the natural home for `originRecipeId`'s Web-side coverage. No
test file is created or modified by this document itself (docs-only
round, §8).

---

## 7. Acceptance / fixture / test matrix (for the later implementation issue)

1. `originRecipeId` recognized as a known, optional payload field on
   both App and Web readers/writers (§3.1/§3.7) — no longer routed to
   generic passthrough.
2. `recipeId` remains forbidden from export, unchanged
   ([CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) §7 untouched, §3.1).
3. A genuinely new, never-before-exported recipe mints `originRecipeId`
   per §3.2's per-surface rule (Web: `= recipeId` at first save; App:
   fresh UUID at first export, written back atomically) — verified
   separately for each surface, not assumed identical (§3.9's
   correction).
4. An imported recipe's `originRecipeId` survives further local
   edits/re-export unchanged (§3.2's "never re-minted by a later
   edit"), mirroring `.kbhbrew`'s existing `originBrewId` lifecycle
   test pattern (`tests/test_kbhbrew_storage_identity.py`).
5. "Save as new" (Web `lagreSomVariant()`, App "Lagre som ny kopi")
   always mints a **fresh** `originRecipeId` for the copy, never
   inherits the source's (§3.5) — this is a **new**, deliberately
   different acceptance point than the phase3c brief's original
   criterion 3, which did not address copy semantics.
6. Re-importing a `.kbhrecipe` file whose `originRecipeId` already
   exists locally is rejected as an explicit duplicate on both App and
   Web, mirroring `.kbhbrew`'s `{ok:false, duplicate:true}` /
   `{duplikat:true}` result shape exactly (§3.4).
7. Every existing legacy fixture
   (`tests/fixtures/legacy/kbhrecipe/*.json`, §1.8) — and any file
   lacking `originRecipeId` generally — remains importable, treated as
   "no dedup signal available," never rejected (§3.4/§5). This is the
   single most important regression test this contract requires.
8. A `.kbhrecipe` file carrying a well-formed, non-colliding
   `originRecipeId` round-trips it unchanged through read → edit →
   save/export on both surfaces.
9. A malformed `originRecipeId` (non-string, or a bare empty string)
   never crashes or rejects the whole import — treated identically to
   "missing" (§3.8).
10. Full Python suite (`python3 -m unittest discover -s tests -b`) plus
    `tests/test_generate_web_i18n_pages.py` (if any Web copy changes
    are needed for UI-facing duplicate messaging) pass, per
    `.claude/rules/testing.md`.

---

## 8. Migration / non-migration policy

**No migration is performed or proposed.** No existing recipe file, on
either App's local disk store or Web's `localStorage`, is rewritten by
this document or by adopting this contract. `originRecipeId` is minted
**lazily, on-demand, only at the next explicit user-triggered export**
(§3.2) — exactly the mechanism [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md)
§6 already specified for App's never-built `recipe_id` ("this happens
only on an explicit, user-triggered export... it never happens as a
background migration"), reused verbatim for `originRecipeId`. There is
no batch rewrite of `recipes/*.json`, no forced re-save prompt, and no
schema migration for `recipeSchemaVersion` or the envelope `version`.
A recipe that is never re-exported after this contract lands simply
never gains an `originRecipeId` — this is an accepted, permanent
steady state, not a temporary gap requiring cleanup.

---

## 9. What this document does not do

- Does not implement any App/Web product code, UI, or test —
  docs-only, per the issue's own hard guard. This document is the only
  file this PR adds.
- Does not modify [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md),
  [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md), or
  [KBH_CORE_CONTRACT_V1.md](KBH_CORE_CONTRACT_V1.md) — precisifying
  [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md) to formally reference
  this document is explicitly deferred to a later, separately
  authorized round (matching header).
- Does not migrate any existing App or Web recipe data (§8).
- Does not touch `tests/fixtures/legacy/kbhrecipe/*.json` or any other
  fixture/schema file — all three remain byte-identical (§1.8/§5).
- Does not add a `core/kbhrecipe_v1.schema.json` (§4) — none exists
  today, and creating one is explicitly separate follow-up work.
- Does not add a `parentRecipeId`/lineage field (§3.10).
- Does not add conflict resolution, live sync, or any cloud/backend/
  account mechanism — matching the phase3c brief's own hard non-goal
  and Roadmap #101's "no automatic conflict resolver."
- Does not decide Phase 3C ownership in general (App vs. Web as "the"
  logging copy) — unrelated to this document's scope, and unaffected
  by it either way.
- Does not implement, wire, or touch Recommendation A (Web's
  `.kbhbrew` file UI) — a fully independent recommendation from the
  same phase3c brief, already merged separately as PR #275/#277.
- Does not touch parked #98/#100/#233/#241 or owner-private data
  (`raw_data/unmatched_malt.json` untouched).
- Does not merge or deploy anything.

---

## 10. Session notes

- Every claim above is grounded in a direct read of the cited source
  file this session, including a targeted re-verification of the
  phase3c brief's own Recommendation B claims (§3.9 found one
  imprecision, corrected here) rather than treating that brief as
  authoritative without re-checking. `pip install -r requirements.txt`
  was run to confirm the test environment installs cleanly; no test
  was run against product code since none was changed, and no test
  file was touched by this document.
