# Phase 3C — App↔Web brew-data handoff contract decision brief (issue #270)

*Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3C "brew-data handoff contract". This is a DECISION/PREP document,
not an implementation record: it audits current `.kbhrecipe`/`.kbhbrew`
import/export/storage/origin/identity behavior in App and Web, then
proposes one implementation-ready V1 contract for owner review. No
product file is changed to produce this brief — the only new file is
this document.*

**Status: DECISION BRIEF — awaiting owner review. A recommended V1
contract is stated below (§4); nothing in it is authorized for
implementation by this brief alone.**

---

## 1. Baseline

| Item | Value |
|---|---|
| Issue | [#270](https://github.com/Joludvig/kvernhaug-brygghus/issues/270) |
| Roadmap | [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3C |
| Prior decision consumed | [#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253) — App owns the current structured brew record for Phase 3B; Web is not a parallel live copy; Brew Lab owns observation/interpretation. This brief does not reopen #253 — it defines the *contract* Phase 3C needs before a Phase-3C-scoped ownership decision, analogous to #253, can be made safely. |
| Related audit | [phase3b_kbhbrew_acceptance_gap_audit.md](phase3b_kbhbrew_acceptance_gap_audit.md) (issue #269) — confirmed App's `.kbhbrew` engine is production-complete; this brief builds on that finding for the Web side and the `.kbhrecipe`/`.kbhbrew` handoff question specifically. |
| Governing contracts | [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md), [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) |
| Branch | `agent/issue-270`, created from a fresh `git fetch origin` |
| `origin/master` at brief time | `3294fa0a7e718c687376ed020455baa8d92f5c8f` (after merged PR #273/#272) |
| Date | 2026-09-15 |
| Method | Direct source read of App's `.kbhbrew`/`.kbhrecipe` engines (`modules/kbhbrew*.py`, `modules/kbh_contract.py`, `modules/kbh_import*.py`), Web's equivalents (`web/js/brew_storage.js`, `web/js/kbhrecipe.js`), and every UI wiring file on both sides (`ui/kbhbrew_panel.py`, `ui/sidebar.py`, `ui/recipe_card.py`, `web/bryggelogg.html`, `web/importer.html`, `web/index.html`, `web/js/brygg_page.js`, `web/js/app.js`), cross-checked against the two governing Core contract docs, `docs/ROADMAP.md`, `docs/development/KBH_CORE_CONTRACT.md`, and issue #253. No product code was changed; no recipe/brew fixture was touched beyond read-only inspection. |

---

## 2. Stale documentation found during this audit — flagged, not fixed here

Both governing Core docs contain sections that are now inaccurate
relative to current master, discovered while establishing ground truth
for this brief:

- **`CORE_KBHBREW_V1.md` §3/§6**: *"No App-side counterpart exists...
  App has no `.kbhbrew` reader or writer today."* Stale since PRI 3B
  (issue #24, commit `111b0a7`, 2026-09-03) — already flagged once by
  [phase3b_kbhbrew_acceptance_gap_audit.md](phase3b_kbhbrew_acceptance_gap_audit.md)
  §1.1; repeated here because this brief also relies on the current,
  not the documented, App behavior.
- **`CORE_KBHRECIPE_V1.md` §13/§14**: *"Not yet wired into a Streamlit
  import UI (no file uploader, no import preview, no save-on-import) —
  that is PRI 2C3."* Stale since PRI 2C3 shipped (commit `18093dc`,
  *"feat(core): add safe .kbhrecipe import UI to Streamlit App"*, merged
  via PR #5) — not previously flagged anywhere in the docs tree, found
  fresh in this audit.

This brief treats current master's source as authoritative over both
stale sections (file:line citations throughout §3), the same precedent
`phase3b_kbhbrew_acceptance_gap_audit.md` §1.1 already set. Refreshing
both Core docs is recorded as a small, bounded follow-up (§9) — not
performed here, to keep this docs-only brief inside its own "decision/
prep only" scope.

---

## 3. Current behavior, mapped to the issue's required points

### 3.1 Ownership / which copy is current

Issue #253 (APPROVED 2026-09-13) is a decision *record*, not a
technical lock: nothing in the code enforces "App is current" — a user
remains free to use either surface's engine independently. What the
code *does* already determine, as of this audit:

- **`.kbhrecipe`**: fully symmetric. Both App and Web have a complete,
  production-wired import UI (file upload → parse → preview → explicit
  confirm) and export UI (download button). Either surface can be "the"
  current copy of a recipe with no functional handicap on either side.
- **`.kbhbrew`**: asymmetric in one specific, narrow way. Web's
  `.kbhbrew` **local-storage engine is fully production-wired** —
  creating a brew from the recipe builder (`web/js/app.js:1799`,
  `opprettBrygg()`), and editing actuals/sensing/learning/status/delete
  from `web/bryggelogg.html` (`web/js/brygg_page.js:225-367`,
  `oppdaterBrygg()`/`slettBrygg()`) — all work today, matching App's
  brew-history UI feature-for-feature. What is **not** wired anywhere in
  `web/*.html`/`web/js/*.js` is the **file-portability layer**:
  `byggKbhBrewInnhold()` (export), `parseKbhBrewInnhold()`/
  `importerBrygg()` (import) have zero callers outside
  `web/js/brew_storage.js` itself — confirmed by an exhaustive grep
  across every Web HTML/JS file. App, by contrast, has this exact layer
  fully wired: `ui/kbhbrew_panel.py:148-360` (`render_kbhbrew_create_panel`/
  `render_kbhbrew_import_panel`/`render_kbhbrew_export_panel`, the last
  two backed by a real `st.file_uploader`).
- **Practical consequence**: a Web brew can live and be fully edited on
  Web, but **cannot leave Web as a file today** — and a `.kbhbrew` file
  (e.g. one App already produced) **cannot be brought into Web** either.
  Since Phase 3C is specifically about *handoff between surfaces*, this
  is the single most concrete, already-observable gap this brief found.

### 3.2 Export/import semantics

- Both formats already share one consistent pattern worth preserving,
  not re-inventing: the same envelope shape
  (`{format, version, exportedAt, generator, payload}`), the same
  explicit-field-whitelist writer rule (never spread a whole live object
  into the file — CORE_KBHRECIPE_V1.md §5, CORE_KBHBREW_V1.md §5.2), and
  the same "import always previews before it commits" UX on every
  surface that has import wired at all.
- `.kbhrecipe`: App `ui/sidebar.py:284-373` (import, file uploader at
  `:291-294`) + `ui/recipe_card.py:362-378` (export). Web
  `web/importer.html:96-98` and `web/index.html:267` (two independent
  import entry points) + the same page's "📄 Lagre oppskriftsfil" button
  (export).
- `.kbhbrew`: App `ui/kbhbrew_panel.py:148-360` (all three: create,
  import, export). Web: engine complete
  (`web/js/brew_storage.js:677-763`), UI absent (§3.1).

### 3.3 Stable recipe/brew identity and origin handling

- **`.kbhbrew` already has a three-tier identity model**, ratified
  (CORE_KBHBREW_V1.md §5.3) and implemented **identically** on both
  sides: `brewId` (local, minted fresh on creation/import, never
  adopted from an imported file), `originBrewId` (portable, defaults to
  `brewId`, travels with export, is the duplicate-detection key),
  `parentBrewId` (reserved, always `null`). `recipeId` is present only
  as a weak, non-authoritative navigation reference. Confirmed
  field-for-field identical constant lists:
  `modules/kbhbrew.py:60-63` (`"brewId", "originBrewId", "parentBrewId",
  "recipeId", "status", ...`) vs. `web/js/brew_storage.js:68`
  (`["brewId", "recipeId", "parentBrewId", "originBrewId", "status",
  ...]`).
- **`.kbhrecipe` has no equivalent origin-identity concept at all**, on
  either side. `recipeId` is each surface's own pure local storage
  identity — explicitly **forbidden** from ever appearing in an exported
  file (CORE_KBHRECIPE_V1.md §7: *"a shareable `.kbhrecipe` must never
  contain the receiving/sending system's local identity"*) — and is
  unconditionally stripped/dropped on import, on both App
  (`modules/kbh_import.py:64`, `_FORBUDTE_PAYLOAD_FELT = {"recipeId",
  "stats", "flavor_profile"}`) and Web (`web/js/kbhrecipe.js:206-221`).
  A repo-wide grep for `originRecipeId` across `modules/` and `web/js/`
  returned **zero hits**, confirmed this session.
- **Consequence**: a `.kbhrecipe` file, once exported, carries no
  portable signal that would let a future import recognize "this is the
  same recipe I already have." `.kbhbrew` deliberately solved exactly
  this problem (`originBrewId`); `.kbhrecipe` never did. This is a
  contract-shape gap between the two formats, present identically on
  both App and Web — not an App-vs-Web divergence.

### 3.4 Duplicate handling

- **`.kbhbrew`**: explicit, already implemented, identical on both
  sides. Import checks the incoming file's `originBrewId` against every
  locally stored brew (App: `modules/kbhbrew_storage.py:154-157`,
  `finnes_brew_med_origin`, checked at `:283-284` *after* validation, so
  an invalid file can never masquerade as a false duplicate; Web:
  `web/js/brew_storage.js:751-754`). A match is rejected outright
  (`{"ok": False, "duplicate": True}` / `{duplikat:true}`) — never a
  silent merge, never an automatic overwrite.
- **`.kbhrecipe`**: **no duplicate handling exists at all, on either
  side**, because there is no origin identity to check against (§3.3).
  Re-importing the identical `.kbhrecipe` file twice silently produces
  two independent local recipes with the same name and content. This is
  a real, already-live gap today, not a hypothetical Phase 3C risk.

### 3.5 Safe continuation on another surface

- **`.kbhbrew`**: already has a safe mechanism for the one risk that
  matters most — a continued/imported brew silently attaching itself to
  the wrong locally-active recipe. Import always mints a fresh local
  `brewId` and the App A1 active-brew binding
  (`aktiv_brew_matcher_recipe()`, `modules/kbhbrew_ui.py:149-161` —
  `brew.get("recipeId") == recipe_id`, wired via
  `_sinkroniser_aktiv_brew_mot_oppskrift()`,
  `ui/kbhbrew_panel.py:122-145`) re-validates the imported brew's
  `recipeId` against the currently loaded recipe's own identity before
  ever treating it as "the active brew." Because recipe identity is
  itself always App-local/filename-based and never portable (§3.3), an
  imported brew's `recipeId` will essentially never coincidentally match
  a local recipe — so this binding already, structurally, prevents a
  continued brew from silently misattaching. **No new mechanism is
  needed for this specific risk**; Recommendation A (§4.1) only needs to
  wire Web to the *file* layer, the identity/binding logic underneath is
  already correct.
- **`.kbhrecipe`**: because there is no origin identity, "continuing" a
  recipe today means: export, import as a brand-new local recipe, then
  manually re-point any in-progress logging at the new copy. This works,
  but has no guardrail today against the user forgetting the original
  copy still exists (§3.4's gap, restated from the continuation angle).

### 3.6 Conflict expectations when both copies have changed

No live sync exists on either side, so a git-merge-style conflict
(two divergent edits to *one shared* record) cannot occur mechanically —
every import always creates an independent local fork, never a merge.
What *can* happen, and is not currently made visible anywhere: a user
edits on Surface A, exports, imports to Surface B, then keeps editing
Surface A too — the two copies now silently diverge with no product
surface telling the user this happened. For `.kbhrecipe` there is not
even a shared identifier to *detect* this with (§3.3); for `.kbhbrew`
the shared `originBrewId` exists and *could* support a future "you
already have a copy of this brew, imported on `<date>`" notice, but
nothing surfaces that today — the duplicate check only fires again at
a *second* import attempt, not continuously. Roadmap #101 and this
issue both make "no automatic conflict resolver" a hard non-goal; the
only currently-safe posture is that **the user is the conflict
resolver**, and the product's job is limited to making divergence
*detectable* (via origin identity), never to *reconciling* it.

### 3.7 Read-only/history vs active/current brew behavior

`.kbhbrew`'s `status` field (`active`/`done`/`discarded`, freely
reassignable metadata, CORE_KBHBREW_V1.md §5.10) plus App's A1
active-brew binding (issue #170) already distinguish "the brew
currently receiving new measurements" from "historical," and this is
regression-tested today
(`tests/test_kbhbrew_history_panel_apptest.py` tests 22–25, confirmed
by the phase3b audit doc §3.3: selecting a non-active/historical brew
never mutates it or the currently-active one). `.kbhrecipe` has no
equivalent concept, and none is proposed here — a recipe is a plan, not
history; `.kbhbrew`'s frozen `snapshot` layer is already the
authoritative "what did the recipe look like when this brew started"
record (CORE_KBHBREW_V1.md §5.4/§5.5). This section documents that the
mechanism a Phase 3C contract would lean on for "is this copy live or
historical" already exists for brews and needs no new design.

### 3.8 What must remain manual in V1

Everything, already true today, and recommended to stay true:

- The export action (explicit user click on both formats/surfaces).
- The file transfer itself (however the user moves the file between
  machines/browsers — outside this product's concern).
- The import action, always with an explicit preview-then-confirm step
  (already true for every import surface that exists today).
- The decision of which surface is "the" logging copy going forward —
  #253's own decision was manual/owner-made and scoped to Phase 3B only;
  this brief does not propose automating an equivalent decision for
  Phase 3C.
- Retiring or marking-stale the original copy after a successful
  continuation — no mechanism anywhere in this brief proposes doing this
  automatically.

### 3.9 What would be required before this may honestly be called "sync"

Per Roadmap #101 (*"File exchange must not be described as
synchronization until that contract exists"*) and this brief's own
findings, real sync would require, at minimum — none of which exists
today and none of which this brief designs or proposes building:

- A live channel between App and Web (today: none — local-first, no
  backend/cloud, no shared storage of any kind).
- A canonical way to detect that two *independently* stored copies
  (already forked apart by any import) refer to the same real-world
  entity **and** have since diverged — today this only half-exists:
  `.kbhbrew`'s `originBrewId` supports *detection at import time*, but
  `.kbhrecipe` has no such identifier at all (§3.3), and neither format
  detects divergence *after* a successful import, only at the moment of
  a second import attempt (§3.6).
- An explicit conflict-resolution policy (last-write-wins, manual merge
  UI, field-level merge, etc.) — explicitly a hard non-goal of this
  phase and this issue.
- A shared clock/version concept, to establish "which edit happened
  later" across two offline-first local stores that share no clock
  today.

Neither of this brief's two recommendations (§4) attempts any of the
above. Both stay inside "manual file exchange with explicit
duplicate/origin handling" — exactly the pattern `.kbhbrew` already
implements — extended narrowly to close the one concrete gap found
(`.kbhrecipe`'s missing origin identity) and the one concrete capability
gap found (Web's missing `.kbhbrew` file UI).

---

## 4. Recommended smallest KISS V1 contract

Two independent recommendations, ordered by how much new logic each
requires. Either can ship alone as its own smaller follow-up issue;
neither depends on the other.

### 4.1 Recommendation A — wire Web's already-built `.kbhbrew` file layer to a UI

Web's `.kbhbrew` reader/writer (`web/js/brew_storage.js`) already fully
implements the ratified Core V1 contract — passthrough, identity,
duplicate detection, verified matching App's implementation field-for-
field (§3.3/§3.4). The only missing piece is UI: an import file-input +
an export/download action on `web/bryggelogg.html`, wired through
`web/js/brygg_page.js`, calling the **existing**
`importerBrygg()`/`byggKbhBrewInnhold()` functions — the same shape
Web's own `.kbhrecipe` import surface (`web/importer.html`) already
uses. This closes §3.1's asymmetry (App can already exchange `.kbhbrew`
files; Web cannot) without touching the wire contract, the identity
model, or any product data.

### 4.2 Recommendation B — extend `.kbhrecipe` with the origin-identity + duplicate-detection pattern `.kbhbrew` already ratified

Add `originRecipeId` to `.kbhrecipe` V1, mirroring the pattern already
proven in production for `.kbhbrew`:

- `recipeId` stays each surface's pure local storage identity,
  unchanged — still minted locally, still forbidden from export
  (CORE_KBHRECIPE_V1.md §7 untouched).
- `originRecipeId` is new: defaults to `recipeId` at creation, travels
  with export, is the duplicate-detection key on import — the exact
  same split `.kbhbrew` already draws between `brewId` and
  `originBrewId`.
- Import behavior changes, on both App and Web, from "always
  unconditionally new" to "check `originRecipeId` against every locally
  stored recipe; on a match, report an explicit duplicate (mirroring
  `.kbhbrew`'s `{duplicate:true}`/`{duplikat:true}` shape) instead of
  silently creating a second copy."

This directly closes §3.4's live gap (silent duplicate recipes on
re-import) and gives §3.5/§3.6 a shared identifier to eventually build
"you already have a copy of this" visibility on top of, without
deciding that UI now. This is explicitly **reuse** of `.kbhbrew`'s
already-ratified, already-implemented, already-tested identity/dedup
pattern — not a new identity system, per this issue's own "Required
analysis" instruction ("do not invent a second identity system").

### 4.3 What this V1 contract deliberately does not do

- Does not implement either recommendation (this is a decision brief;
  implementation is separate, later, per-recommendation issue work).
- Does not change `.kbhbrew`'s already-ratified identity/passthrough/
  duplicate model in any way — Recommendation A only adds UI around it;
  Recommendation B *copies* its pattern for `.kbhrecipe`, never modifies
  `.kbhbrew` itself.
- Does not add conflict resolution, live sync, or any
  cloud/backend/account mechanism (unchanged hard non-goal).
- Does not decide which surface owns ongoing Phase 3C logging in
  general — that remains a narrower, later, possibly per-brew owner
  decision, following the same pattern issue #253 set for Phase 3B.
- Does not change any Core/App/Web/Brew Lab product code, and does not
  touch `.kbhrecipe`/`.kbhbrew` files or fixtures beyond the read-only
  inspection already performed for this brief.

---

## 5. Alternatives considered

### For Recommendation A (Web `.kbhbrew` file UI)

- **Do nothing / leave Web's `.kbhbrew` file layer UI-less.** Rejected
  as the default: it leaves Web structurally unable to participate in
  Phase 3C handoff as either a sending or receiving surface, contra
  Roadmap #101's own "App↔Web" framing of this phase.
- **Build a new Web brew-file UI from scratch instead of reusing
  `brew_storage.js`.** Rejected: `brew_storage.js` is the *original*
  implementation the whole Core `.kbhbrew` V1 contract was modeled on
  (CORE_KBHBREW_V1.md §6: *"should not be treated as a mere...
  pre-Core format — it was already, and remains, the only
  implementation that satisfies the five-layer model"*); rebuilding it
  would violate "reuse existing contracts/helpers" (this issue's
  "Required analysis").

### For Recommendation B (`.kbhrecipe` origin identity)

- **Do nothing / accept the asymmetry with `.kbhbrew` permanently.**
  Considered and rejected for the same reason CORE_KBHBREW_V1.md's own
  Section 8 #2 "Option C" (accepting the equivalent asymmetry the other
  direction, permanently) was rejected there: the concrete cost (silent
  duplicate recipes) is already observable today, not merely
  theoretical.
- **Full recipe versioning/conflict resolution instead of simple
  origin-id dedup.** Rejected as over-scoped for V1 — this is exactly
  the "no automatic conflict resolver" hard non-goal; origin-id dedup
  only *detects and rejects* a duplicate at import time, it never
  attempts to merge or resolve anything.
- **Reuse `recipeId` itself as the dedup key instead of adding
  `originRecipeId`.** Rejected: `recipeId` is explicitly forbidden from
  ever appearing in an exported file (CORE_KBHRECIPE_V1.md §7) —
  reusing it as the dedup key would require either violating that rule
  or relaxing it. `.kbhbrew` already solved exactly this tension by
  keeping `brewId` strictly local and adding a separate portable
  `originBrewId`; mirroring that existing split is the smaller,
  already-precedented change.

---

## 6. Trade-offs

- **Recommendation A** cost: Web needs new UI markup/i18n strings (NO/EN
  via the canonical generator, `.claude/rules/web.md`) and Playwright
  coverage per `.claude/rules/testing.md`; benefit: closes a real,
  user-visible capability gap with effectively no wire-contract risk —
  the engine underneath is already correct and covered by
  `tests/js/test_kbhbrew_contract.js`.
- **Recommendation B** cost: touches the `.kbhrecipe` wire contract
  itself (CORE_KBHRECIPE_V1.md requires "explicit review and a version
  increment" per its own header) and both App's and Web's import paths;
  benefit: closes a live data-integrity gap (duplicate recipes) using a
  pattern already proven safe in production by `.kbhbrew`.
- The two recommendations are independent; shipping only one still
  measurably improves Phase 3C readiness, and shipping both is not
  required to close either gap.
- Neither recommendation touches brew-data ownership — issue #253's
  Phase 3B decision stands completely untouched; a fresh,
  Phase-3C-scoped ownership decision (analogous to #253 but covering
  Phase 3C's broader App↔Web scope) remains a separate, later owner
  call this brief does not make.

---

## 7. Acceptance criteria (for whichever follow-up issue implements this)

### Recommendation A

1. A Web user can select and import a `.kbhbrew` file via
   `web/bryggelogg.html`, with an explicit preview-then-confirm step,
   mirroring the existing `.kbhrecipe` import UX pattern
   (`web/importer.html`).
2. A Web user can export a brew from `web/bryggelogg.html` as a
   `.kbhbrew` file, byte-shape-identical to what `byggKbhBrewInnhold()`
   already produces today (no wire-contract change).
3. Importing a `.kbhbrew` file whose `originBrewId` already exists in
   the Web store is rejected with a visible, explicit "already
   imported" message — reusing `importerBrygg()`'s existing
   `{duplikat:true}` result, not a new check.
4. A `.kbhbrew` file produced by App's exporter
   (`modules/kbhbrew_storage.py::eksporter_kbhbrew`) imports cleanly
   into Web via the new UI, and vice versa — a real cross-surface
   round-trip test, not just same-surface.
5. NO + EN parity via the canonical i18n generator
   (`python3 scripts/generate_web_i18n_pages.py`); Playwright coverage
   added per `.claude/rules/testing.md`.

### Recommendation B

1. `originRecipeId` is added to `.kbhrecipe` V1
   (`CORE_KBHRECIPE_V1.md` version increment + explicit review, per its
   own header).
2. `recipeId` remains forbidden from export, unchanged
   (`CORE_KBHRECIPE_V1.md` §7 untouched).
3. Both App and Web mint `originRecipeId = recipeId` for a genuinely
   new, never-before-exported recipe, and preserve an imported file's
   own `originRecipeId` unchanged across further local edits/re-export
   — mirroring `.kbhbrew`'s existing `originBrewId` lifecycle exactly.
4. Re-importing a `.kbhrecipe` file whose `originRecipeId` already
   exists locally is rejected as an explicit duplicate on both App and
   Web, mirroring `.kbhbrew`'s `{ok:false, duplicate:true}` /
   `{duplikat:true}` result shape.
5. Existing `.kbhrecipe` fixtures without `originRecipeId`
   (`tests/fixtures/legacy/kbhrecipe/*.json`) remain readable — a
   missing `originRecipeId` on import is treated as "no dedup signal
   available" (import proceeds as new), never rejected outright, so
   every `.kbhrecipe` file that predates this field stays compatible.
6. `tests/test_kbh_import.py`, `tests/test_kbh_contract.py`,
   `tests/test_web_js_kbhrecipe.py` extended with duplicate-detection
   coverage; full Python suite plus
   `tests/test_generate_web_i18n_pages.py` (if any Web copy changes)
   pass.

---

## 8. Likely implementation touchpoints (for a later issue — not built here)

### Recommendation A

- `web/bryggelogg.html` — new import/export UI markup.
- `web/js/brygg_page.js` — wire `importerBrygg()`/`byggKbhBrewInnhold()`
  to the new UI.
- `web/js/brew_storage.js` — likely unchanged (engine already complete);
  confirm no gap once a real UI exercises the file path end-to-end for
  the first time.
- Web i18n source strings (`web/no/**`) + canonical regeneration
  (`python3 scripts/generate_web_i18n_pages.py`) for `web/en/**`.
- `tests/playwright/**` — new spec(s) for the import/export flow, per
  `.claude/rules/testing.md`.

### Recommendation B

- `docs/development/CORE_KBHRECIPE_V1.md` — version increment, a new
  "origin identity" section, an updated §7 (only `recipeId` stays
  forbidden; `originRecipeId` explicitly permitted/required).
- App: `modules/kbh_contract.py` (writer), `modules/kbh_import.py`
  (reader + duplicate check), `modules/kbh_import_apply.py`
  (apply-side duplicate handling), `modules/recipe.py`/
  `modules/recipe_storage.py` (native `originRecipeId` field + local
  duplicate lookup), `ui/sidebar.py` (surface the duplicate result in
  the existing import expander).
- Web: `web/js/kbhrecipe.js` (writer/reader + duplicate check, mirroring
  `web/js/brew_storage.js`'s existing `originBrewId` pattern),
  `web/js/recipe_storage.js` (native field + local duplicate lookup),
  `web/importer.html`/`web/index.html` (surface the duplicate result).
- Tests: `tests/test_kbh_contract.py`, `tests/test_kbh_import.py`,
  `tests/test_kbh_import_apply.py`, `tests/test_kbh_import_ui_apptest.py`,
  `tests/test_web_js_kbhrecipe.py`, plus a JS contract test mirroring
  `tests/js/test_kbhbrew_contract.js`.

---

## 9. Documentation staleness — recorded, not fixed here

Following the same "flag, don't fix in a docs-only round" precedent
`phase3b_kbhbrew_acceptance_gap_audit.md` §5.4 already set:

- `CORE_KBHBREW_V1.md` §3/§6 ("No App-side counterpart exists") — stale
  since PRI 3B (issue #24).
- `CORE_KBHRECIPE_V1.md` §13/§14 ("Not yet wired into a Streamlit import
  UI — that is PRI 2C3") — stale since PRI 2C3 landed (commit
  `18093dc`).

Refreshing both is a small, bounded, separately-scoped follow-up — not
performed here, to keep this brief inside "decision/prep only," matching
this issue's own explicit scope and the phase3b audit's identical
precedent.

---

## 10. What this brief explicitly does not do

Mirrors issue #270's own "Hard non-goals," restated against this
brief's actual content:

- No product implementation (§4.3, §7, §8 describe *future* work only).
- No Core/schema change — Recommendation B *proposes* a future
  `.kbhrecipe` schema addition; this PR does not modify
  `CORE_KBHRECIPE_V1.md` or any schema file.
- No cloud/backend/account design.
- No automatic conflict resolver (§3.6/§3.9).
- No deploy.
- No merge.
- No changes to `.kbhrecipe`/`.kbhbrew` files or fixtures beyond the
  read-only inspection already performed.
- Does not touch parked #98/#100/#233/#241.
- Does not decide Phase 3C ownership in general — only documents what a
  future ownership decision (analogous to #253) would need in place
  first (§3.9).

---

## 11. Session notes

- No product code was read from documentation summaries alone — every
  claim above is grounded in a direct read of the cited source file.
- `pip install -r requirements.txt` was run to confirm the test
  environment installs cleanly; no test was run against product code
  since none was changed, and no test file was touched by this brief.
- This document is the only file this PR adds or changes.
