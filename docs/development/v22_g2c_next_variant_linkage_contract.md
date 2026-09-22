# V2.2 G2C — Next-variant linkage contract decision brief (issue #357)

*Part of Roadmap V2.2 [#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343)
Goal 2, following the case-selection prep [#354](https://github.com/Joludvig/kvernhaug-brygghus/issues/354)
and the reflection/hypothesis slice
[#355](https://github.com/Joludvig/kvernhaug-brygghus/issues/355) (PR #356).
This is a DECISION/PREP document, not an implementation record: it
audits current App/Core recipe and brew identity semantics, then
proposes one implementation-ready contract for how a finished brew can
point forward to the next recipe/variant that embodies its
`learning.nextTime` decision. No product file is changed to produce
this brief — the only new file is this document.*

**Status: DECISION BRIEF — awaiting owner/Chief authorization. A
recommended contract is stated below (§4); nothing in it is authorized
for implementation by this brief alone.**

---

## 1. Baseline

| Item | Value |
|---|---|
| Issue | [#357](https://github.com/Joludvig/kvernhaug-brygghus/issues/357) |
| Roadmap | [#343](https://github.com/Joludvig/kvernhaug-brygghus/issues/343) V2.2 Goal 2 |
| Predecessors | [#354](https://github.com/Joludvig/kvernhaug-brygghus/issues/354) (running case selection: Sommerglød v2 → future v3), [#355](https://github.com/Joludvig/kvernhaug-brygghus/issues/355)/PR [#356](https://github.com/Joludvig/kvernhaug-brygghus/pull/356) (`learning.hypothesis`, accepted on owner PC) |
| Governing contracts | [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md), [CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md](CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md) |
| Closest prior brief (structure precedent) | [phase3c_brew_data_handoff_contract_decision_brief.md](phase3c_brew_data_handoff_contract_decision_brief.md) |
| Branch | `agent/issue-357`, created from a fresh `git fetch origin` |
| `origin/master` at brief time | `815e6f5a8b4ec2dee046340b9968e4ffe15c8407` — matches the issue's stated base |
| Date | 2026-09-22 |
| Method | Direct source read of `modules/recipe.py`, `modules/recipe_storage.py`, `modules/kbh_import.py`, `modules/kbh_contract.py`, `modules/kbhbrew.py`, `modules/kbhbrew_ui.py`, `modules/kbhbrew_storage.py`, `ui/recipe_card.py`, `ui/sidebar.py`, `ui/kbhbrew_panel.py`, `ui/kbhbrew_history_panel.py`, `app.py`, `core/kbhbrew_v1.schema.json`, `docs/development/CORE_KBHBREW_V1.md`, `docs/development/CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md`, and `docs/brew-lab/history/sommerglod-v1-v2.md` (the running case's reconstructed evidence). No product code, recipe, or brew data was changed to produce this brief. |

---

## 2. Current source truth

### 2.1 App has no local recipe ID — only a sparse, portable `originRecipeId`

`modules/recipe.py:74-76` states directly: *"App har INGEN lokal
`recipeId` (§1.2 i kontrakten) — dette feltet er derfor App sin ENESTE
identitet mot et senere `.kbhrecipe`-import-dedup-sjekk."* Confirmed by
an exhaustive grep across `modules/recipe.py`/`recipe_storage.py`/
`kbh_contract.py`/`kbh_import.py`: zero local-identity fields exist.

Saved recipes are keyed by a **filename derived from the mutable
`name` field** (`modules/recipe_storage.py::generer_filnavn()`,
line 391-396) — not a stable ID. `hent_alle_oppskrifter()`
(line 717-734) documents that two files sharing one `name` silently
collapse to one in memory.

The one portable identity field that *does* exist,
`originRecipeId`, is minted only:
- on the first explicit "📦 Eksporter KBH-oppskrift" click
  (`modules/recipe_storage.py::sikre_origin_recipe_id()`, line 480-521,
  atomic, one-shot, never a background migration), or
- **freshly, on every "Lagre som ny kopi" duplication**
  (`ui/recipe_card.py:258`, `origin_recipe_id=str(uuid.uuid4())`) —
  deliberately breaking lineage, because `originRecipeId`'s only
  ratified job is import dedup, not versioning
  (`CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md` §3.5, line 400-408).

`CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md` §3.10 (line 484-496) already
considered and rejected a recipe-side lineage field, for lack of a
named scenario: *"unlike `.kbhbrew`'s `parentBrewId`, which was
reserved at ratification time for a specific named future scenario...
no analogous concrete scenario has been identified for recipes."*
**Issue #357 is now that named scenario for a *brew→recipe* forward
link — it does not require reopening the recipe-side "NOT NOW" decision
at all, because (§4 below) the link this issue needs lives entirely on
the `.kbhbrew` side, pointing at a recipe's already-existing
`originRecipeId`, never a new recipe-side field.**

`originRecipeId` **survives a plain rename** (App's rename path
overwrites/moves the file but the recipe dict's own fields, including
`originRecipeId`, are carried through unchanged — only "Lagre som ny
kopi" mints a fresh one, confirmed at `ui/recipe_card.py:189-268`). It
is **not** guaranteed present: a recipe that has never been exported
and never been created via "Lagre som ny kopi" has no `originRecipeId`
at all.

### 2.2 Recipe duplication has exactly one entry point today

`ui/recipe_card.py:247-268`, the **"💾 Lagre som ny kopi"** button, is
the only duplication mechanism in the App. It rebuilds the recipe
entirely from **current live session state**
(`_bygg_recipe_fra_session`, line 146-182), mints a fresh
`originRecipeId`, and saves with `bloker_ved_navnekollisjon=True`. It
duplicates *whatever is currently loaded/edited in the Oppskrift tab*
— it has no notion of starting from an arbitrary historical brew's
frozen snapshot.

### 2.3 `.kbhbrew.recipeId` is a frozen, filename-valued weak reference

Per `CORE_KBHBREW_V1.md` §5.4 (line 452-460): *"`recipeId` at the
brew's top level is always a **weak** reference for grouping/navigation
only; no calculation or display may depend on it resolving."*

Source-verified: `ui/kbhbrew_panel.py:193` passes
`st.session_state.get("_last_loaded_recipe_file")` — the **source
recipe's filename at brew-creation time** — as `recipe_id`.
`modules/kbhbrew.py:374` freezes it verbatim into `bygg_ny_brew()`; it
is never rewritten afterward (`oppdater_brew_lag()` never touches it).
Matching (`modules/kbhbrew_ui.py:150-161`,
`aktiv_brew_matcher_recipe()`) is exact-string-equality against the
*current* `_last_loaded_recipe_file` — so **renaming the source recipe
silently breaks this match for every existing brew**, even though nothing
about "the recipe" conceptually changed. `recipeId` is explicitly
forbidden from ever appearing in an exported `.kbhbrew` payload
(`modules/kbhbrew.py:56-63`, `_KJENTE_BREW_FELT`; confirmed absent by
construction in `brew_to_kbhbrew_payload()`, line 436-497) and is
force-dropped on import (`modules/kbhbrew_storage.py:289`,
`brew["recipeId"] = None`). **`recipeId` is therefore local-machine
scoped and rename-fragile — it cannot serve as any part of a portable
next-variant link.**

### 2.4 A brew's frozen snapshot already carries the source recipe's `originRecipeId` — when one existed

`modules/kbhbrew.py::bygg_ny_brew_snapshot()` (line 308-347) builds
`snapshot.recipe` via `recipe_to_kbhrecipe_payload(recipe)`
(`modules/kbh_contract.py:150`), which **does** copy `originRecipeId`
through when present (`modules/kbh_contract.py:230-232`). Because the
snapshot is an immutable deep copy (Section 5.5, proven by
`tests/test_kbhbrew_snapshot.py`'s mutation tests), **a brew's
`snapshot.recipe.originRecipeId` is permanently frozen at brew-creation
time — immune to any later rename, edit, or deletion of the live
recipe file.** This is already strictly more robust than `recipeId`
for backward identity, but it is **sparse**: it is `None`/absent
whenever the source recipe had never been exported or duplicated
before the brew was created. This sparseness is a real, pre-existing
gap in today's system, not something this brief's recommendation
introduces or needs to fully close.

### 2.5 `parentBrewId` is reserved for an unrelated, narrower scenario

`CORE_KBHBREW_V1.md` §5.3 (line 444-446): *"`parentBrewId` — reserved
for a future shared-batch concept. Always `null` in V1; no reader may
assign meaning to a non-null value yet."* The named scenario is *"future
shared batch, same wort, two fermenters"* (line 125) — a **sibling/split**
relationship between two brew *records* of the identical recipe and
batch event. A **successor/version** relationship between two different
*recipes* (this brew's outcome → a new recipe) is a different concept
entirely and **must not** be represented by giving `parentBrewId` a
second, unratified meaning.

### 2.6 Brew History has no recipe-navigation mechanism today

Full read of `ui/kbhbrew_history_panel.py` (423 lines) and
`modules/kbhbrew_history_ui.py`: the panel lets a user edit
`actuals`/`sensing`/`learning`/`status` on a selected brew
(`oppdater_brew_lag()`, `modules/kbhbrew_storage.py:206-241`, which
never writes `snapshot`, `recipeId`, or any new field) and read-only
compares planned vs. actual. **There is no button or mechanism to open
the source recipe, or to create a new recipe from a brew's snapshot.**
The App's only "active recipe" state is the sidebar's
`_last_loaded_recipe`/`_last_loaded_recipe_file`
(`ui/sidebar.py:115-201`), settable only by direct user interaction with
that one dropdown — nothing in Brew History or Bryggdag can set it
programmatically today.

### 2.7 `learning` is currently framed as same-recipe, not cross-recipe

`CORE_KBHBREW_V1.md` §5.9 (line 542-544): *"Layer 5 (`learning`) is
forward-looking payload for the **next brew of the same recipe**."*
`hypothesis` (added by #355) is free text only — *"never auto-filled,
never AI-generated, and carries no confidence score or cause
taxonomy"* — and, like `whatWorked`/`whatChanged`/`nextTime`, carries no
reference (ID, filename, or otherwise) to any other recipe. This
existing framing is exactly what issue #357 needs to extend, narrowly,
to also cover "the next brew of a **new, related** recipe."

### 2.8 Running case evidence (Sommerglød v2 → v3)

Per [docs/brew-lab/history/sommerglod-v1-v2.md](../brew-lab/history/sommerglod-v1-v2.md):
v2 (2026-07-12) raised smoke malt to 10%, but *"the smoke in
Sommerglød v2 [was] still too subtle for the stronger Kvernhaug smoke
signature desired in darker beers."* A plausible `hypothesis`/`nextTime`
pair for this case ("smoke read as too subtle at 10%" / "increase
Rauchmalz % for v3") is exactly the shape of decision this contract
must let the brewer carry forward into a v3 recipe — this brief does
not itself create, rename, or touch any Sommerglød data.

---

## 3. Answers to the issue's required questions

1. **What exact action should the user take from Brew History to
   create/open the next variant?** One new explicit action on a brew
   record, e.g. **"🌱 Opprett neste variant"**, enabled once
   `learning.nextTime` is non-empty (it is the decision text this
   action operationalizes). It starts the existing "duplicate recipe"
   flow (§2.2) seeded from the brew's own frozen snapshot rather than
   live session state (see §4.1). After the brewer saves the new
   recipe, a second, separate, explicit confirmation step on the
   *same* brew record ("link this reflection to a saved recipe") writes
   the new field described in §4.2. Two explicit steps, not one
   automatic jump — consistent with "the user must explicitly
   choose/create the next variant" and "do not infer... from
   `learning.hypothesis`."
2. **Start from the immutable snapshot, the live recipe, or another
   source?** **The immutable snapshot** (`brew.snapshot.recipe`), never
   the possibly-drifted live recipe file. History correctness requires
   that "the next variant of what I actually brewed" starts from
   exactly what was brewed — the live file may since have been edited
   for unrelated reasons, renamed, or deleted entirely (§2.6 confirms
   Brew History has no live-recipe dependency today), and using it
   would make the eventual "did the intended change help" comparison
   ambiguous about what actually changed.
3. **What identity/link fields are required?** Exactly one new
   optional `.kbhbrew` field: `learning.nextRecipeOriginId` (string).
   No recipe-side field is needed (§2.1).
4. **Can the link be represented with existing IDs safely?** The
   *target* of the link (a recipe's `originRecipeId`) already exists
   and is already portable/Core-level. The *pointer itself* has no
   existing home — `recipeId` is local/rename-fragile (§2.3) and
   `parentBrewId` is reserved for an unrelated scenario (§2.5) — so one
   new field is required, but it references only an existing ID space.
5. **What happens if the original live recipe was renamed/deleted?**
   Nothing breaks: the *backward* identity this contract relies on
   (`snapshot.recipe.originRecipeId`, when present) is already frozen
   and rename/delete-immune (§2.4). The *forward* pointer
   (`learning.nextRecipeOriginId`) references the **new** recipe, not
   the old one, so the old recipe's fate is irrelevant to it.
6. **What happens if the next recipe is later edited?** Nothing
   breaks. The pointer identifies the recipe by durable ID, not a
   frozen byte-for-byte state — ordinary iterative editing before that
   recipe is eventually brewed is expected and out of scope to prevent.
7. **How does the eventual next brew point back for evaluation?** No
   new back-pointer field is needed. When Sommerglød v3 is eventually
   brewed, its own new `.kbhbrew` record's
   `snapshot.recipe.originRecipeId` (§2.4, already existing behavior)
   will equal the same ID the *prior* brew's
   `learning.nextRecipeOriginId` points at. A later evaluation UI (out
   of this issue's scope) can join the two records on that shared ID —
   no experiment/statistics framework required.
8. **Smallest human acceptance flow (Sommerglød v2 → v3)?** See §6.

---

## 4. Recommended smallest KISS V1 contract

### 4.1 Source-of-copy rule: seed "next variant" from the brew's frozen snapshot

The "🌱 Opprett neste variant" action loads `brew.snapshot.recipe` (the
already-existing `.kbhrecipe`-shaped payload) into the Oppskrift tab as
a **new, unsaved draft**, through the same recipe-object construction
path App already uses for `.kbhrecipe` import (`modules/kbh_import.py`
— the snapshot's `recipe` is already shaped exactly like an imported
`.kbhrecipe` payload, per §2.4/§2.8's citation of
`recipe_to_kbhrecipe_payload`). This is deliberately the **import** path,
not the "Lagre som ny kopi" path (§2.2) directly, because the source is
a frozen snapshot object, not live session state — but it ends the same
way: on save, a fresh `originRecipeId` is minted (existing, unchanged
`sikre_origin_recipe_id()`/duplication-mint behavior, §2.1), and the
user is free to rename/edit before saving (e.g. rename to "Sommerglød
v3", raise Rauchmalz %).

### 4.2 One new, additive Core field: `learning.nextRecipeOriginId`

Same pattern as `hypothesis` (#355): additive, optional, same-major-
version, unknown-field-preservation-compatible.

- **Type**: `string` (a recipe's `originRecipeId`), or absent/`null`.
- **Meaning**: *"the `originRecipeId` of the recipe the brewer
  explicitly created/chose as the next variant embodying this brew's
  `learning.nextTime` decision."*
- **Set only** by an explicit brewer confirmation step in Brew History
  (§3, action 2) — never auto-filled, never inferred from `hypothesis`
  or `nextTime` text, matching the hard constraint against auto-applying
  a recipe change from `learning.hypothesis`.
- **Not a foreign-key guarantee**: like `recipeId` (§2.3), it is a weak
  reference — resolution may fail if the target recipe was later
  deleted locally, or was created on a different machine and never
  imported here. No calculation may depend on it resolving; a UI that
  cannot resolve it should say so plainly, never error.
- **Lives in Layer 5 (`learning`)**, not Layer 1 (identity/lifecycle) —
  it is a *decision artifact* (like `nextTime`), not a structural
  identity field, and does not touch `parentBrewId`/`recipeId`/
  `originBrewId` at all.

### 4.3 What this V1 contract deliberately does not do

- Does not add any recipe-side field (`parentRecipeId` or similar) —
  §2.1 confirms the link is fully expressible as one brew-side pointer
  into the existing recipe ID space.
- Does not repurpose `parentBrewId` (§2.5).
- Does not add a schema version bump — additive optional field only.
- Does not add confidence scores, a cause taxonomy, or any automatic
  causal diagnosis.
- Does not build an evaluation/comparison UI ("did it help") — §3
  question 7 shows that is a *derivable join*, not a new stored field,
  and is explicitly a later, separate slice.
- Does not build a Web UI for this slice (Web is out of scope for this
  App/Core-focused issue, exactly as #355 kept Web UI out of scope) —
  but see §6 for the one Web-side check that must still happen before
  or alongside implementation.
- Does not touch/rename/create any Sommerglød data — the case remains
  illustrative only, per the issue's own STOP list.

---

## 5. Alternatives considered

- **Reuse `parentBrewId` for this.** Rejected (§2.5) — it already has a
  ratified, narrower, unrelated meaning; overloading it would violate
  "no reader may assign meaning to a non-null value yet" outside that
  scenario and would make a future real shared-batch feature ambiguous
  against this one.
- **Add a recipe-side `parentRecipeId`/lineage field instead.**
  Rejected — `CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md` §3.10 already
  declined this for lack of a named scenario, and it is unnecessary
  here: the brew-side pointer alone fully answers "which recipe embodies
  my decision" without touching the recipe schema (which today has no
  machine-readable schema file at all, §2.1) or reopening that
  deferred decision.
- **Seed the next variant from the live recipe rather than the frozen
  snapshot.** Rejected in §3 (question 2) on history-correctness
  grounds — the live file may have drifted for unrelated reasons, or no
  longer exist.
- **Auto-create the next recipe from `learning.hypothesis`/`nextTime`
  text.** Rejected outright — explicitly forbidden by the issue's hard
  constraints ("Do not infer or auto-apply a recipe change from
  `learning.hypothesis`", "The user must explicitly choose/create the
  next variant").
- **Keep the link product-local (Streamlit `session_state`/local file
  path only), not portable Core state.** Rejected — the whole point is
  to survive across sessions/exports for a *later* evaluation, exactly
  the same reasoning that made `hypothesis`/`nextTime` Core `learning`
  fields rather than ephemeral UI state; a session-local link would be
  lost the moment the browser/session resets.

---

## 6. Smallest human acceptance flow + test matrix

**Human acceptance flow (Sommerglød v2 → v3, illustrative only, no
data created by this brief):**
1. Brewer opens Brew History, selects the Sommerglød v2 brew, fills in
   `learning.hypothesis` and `learning.nextTime` (already supported,
   #355/#356).
2. Clicks "🌱 Opprett neste variant" → Oppskrift tab opens with a new,
   unsaved draft seeded from `snapshot.recipe` (§4.1).
3. Brewer renames the draft (e.g. "Sommerglød v3"), raises smoke malt %
   per their `nextTime` decision, and saves — a new recipe file is
   created with a fresh `originRecipeId` (existing, unchanged
   mechanism).
4. Back on the same Sommerglød v2 brew record, brewer explicitly
   confirms the link (e.g. a picker over locally saved recipes that
   have an `originRecipeId`) → `learning.nextRecipeOriginId` is written.
5. Weeks later, brewing "Sommerglød v3" creates a new `.kbhbrew` record
   whose `snapshot.recipe.originRecipeId` matches the same ID — a later,
   separate evaluation UI can join the two records on it.

**Minimal files/surfaces likely touched by the implementation issue:**
- `core/kbhbrew_v1.schema.json` — add `learning.nextRecipeOriginId`.
- `docs/development/CORE_KBHBREW_V1.md` §5.9 — document the new field
  narrowly, alongside `hypothesis`.
- `modules/kbhbrew.py` — recognize/normalize/export/import
  `nextRecipeOriginId` in `_KJENTE_LEARNING_FELT`/`_bygg_learning_payload`,
  same pattern as `hypothesis`.
- `ui/kbhbrew_history_panel.py` — "🌱 Opprett neste variant" action +
  the explicit link-confirmation control.
- `ui/recipe_card.py` / `modules/kbh_import.py` — the snapshot-seeded
  "new draft" entry point (§4.1), reusing the existing import-shaped
  construction path rather than inventing a new one.
- `ui/sidebar.py` / `app.py` — whatever minimal tab-switch/state-seed
  mechanism is needed so "Opprett neste variant" actually lands the
  brewer in Oppskrift with the draft loaded (§2.6 confirms no such
  cross-tab mechanism exists today and will need a small, bounded
  addition).

**Test matrix (for the implementation issue):**
- Core schema accepts `learning.nextRecipeOriginId`; a document
  without it remains valid (fully optional).
- App normalize/import/export round-trips it; unknown-field passthrough
  is preserved when an older reader doesn't yet recognize it.
- Blank/unset is omitted, consistent with the other `learning.*` text
  fields.
- Renaming or deleting the *target* recipe after linking does not
  corrupt the source brew record; a UI resolving the link handles "not
  found locally" without erroring.
- Renaming the *source* recipe before/after the brew was created does
  not affect the new field at all (it doesn't reference the source
  recipe).
- `parentBrewId` remains `null`/untouched by every code path this
  feature adds.
- A focused JS contract regression test proves Web's existing
  `.kbhbrew` reader/writer round-trips `learning.nextRecipeOriginId`
  through its unknown-field passthrough without loss — the same "prove
  it, don't build a UI for it" check #355 did for `hypothesis`
  (`tests/testing.md` §"tests/ DOES cover web/**").

**Human QA contract:** an owner/Chief manual pass confirming the full
five-step flow above end-to-end on a real (non-Sommerglød, or an
explicitly owner-approved Sommerglød) recipe/brew pair, checking that:
the seeded draft matches the brewed snapshot exactly before any edits;
saving mints a fresh, non-colliding recipe file; the link survives an
export/import round trip of the `.kbhbrew` file; and no historical
brew/recipe data is mutated by any step except the one new field.

---

## 7. Hard non-goals (restated against this brief's own content)

- No implementation is authorized by this brief (§ "Status" above).
- No historical batch evidence was mutated to produce it (§1 Method).
- No missing observation was invented (§2.8 cites only
  `sommerglod-v1-v2.md`'s existing text).
- No plausible-sounding explanation was asserted as fact — §2.8's
  hypothesis/nextTime pair is offered explicitly as "a plausible... pair
  for this case," not a recorded decision.
- No broad experiment/statistics/AI framework is proposed — §4.3/§5
  reject every such expansion explicitly.
- `parentBrewId` is not repurposed anywhere in this document (§2.5,
  §4.3, §5).

---

## 8. Recommendation for one bounded implementation child issue

Authorize exactly one follow-up implementation issue scoped to §4 of
this brief (the `learning.nextRecipeOriginId` field + the two-step
Brew-History action + the snapshot-seeded draft entry point), with:
- a named real brew as its own acceptance case (owner's choice — reuse
  Sommerglød v2, or another brew, per the same "low reconstruction
  ambiguity" criterion #354 used);
- explicit evidence provenance (this brief's §2/§3, cited by section);
- the immutable-historical-truth boundary restated verbatim from this
  issue and #355/#356;
- one clear next-variant decision loop (§6's five-step flow) as its
  acceptance criteria;
- the Web round-trip regression test (§6) as a required, bounded test —
  not a Web UI.

---

## 9. Session notes

This brief is grounded entirely in direct reads of the source files
and governing docs cited throughout — no claim here rests on a prior
summary alone. No product code, recipe file, or brew record was
modified to produce it; this document is the only file this PR adds.
Python test suite was not run for this round since no product code
changed (docs-only diff, consistent with `.claude/rules/testing.md`'s
web-diff carve-out extended here to a docs-only diff — nothing in
`tests/` exercises this new file, and no existing test's behavior is
affected by adding it).
