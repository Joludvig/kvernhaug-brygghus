# Phase 3C — technical completion audit (issue #291)

*Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3C ("brew-data handoff contract"). This is a docs-only, read-only
audit — no App/Web/Core product behavior, schema, or version is changed
by this document. It supersedes no prior decision; it confirms what is
now true on current `master` after the handoff implementation pieces
landed.*

## 0. Baseline

| Item | Value |
|---|---|
| Issue | [#291](https://github.com/Joludvig/kvernhaug-brygghus/issues/291) |
| Roadmap | [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3C |
| `origin/master` at audit time | `1227cb0` (queue baseline was `a817de6`; one unrelated merge, #295/`test(kbhbrew): fresh-session restart coverage`, landed in between — no Phase 3C file touched) |
| Inputs audited | [phase3c_brew_data_handoff_contract_decision_brief.md](phase3c_brew_data_handoff_contract_decision_brief.md) (#270/PR #274); [CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md](CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md) (#276/PR #279, ratified #281/PR #282); Web `.kbhbrew` UI (#275/PR #277); App `originRecipeId` (#283/PR #286); Web `originRecipeId` (#284/PR #287); cross-surface handoff test (#288/PR #292); malformed-origin fix (#293, commit `7345809`); [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md); [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md); [#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253) (Phase 3B ownership decision); [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3C's own 5-bullet definition. |
| Method | Direct source read of `modules/kbh_contract.py`, `modules/kbh_import.py`, `modules/recipe_storage.py`, `web/js/kbhrecipe.js`, `web/js/recipe_storage.js`, `web/js/brygg_page.js`, `web/js/brew_storage.js`, plus the governing Core docs above — not documentation summaries alone. Every claim below is grounded in a current file:line citation or a rerun test result, not carried forward from the decision brief's own (now nine-day-old) source read. |
| Tests run this session | `python3 -m unittest tests.test_kbh_contract tests.test_kbh_import tests.test_kbh_import_apply tests.test_kbhrecipe_origin_identity tests.test_kbh_passthrough tests.test_kbhbrew_storage_identity tests.test_kbhbrew_schema_contract tests.test_kbhbrew_roundtrip -b` — 232 tests, OK. Full suite: `python3 -m unittest discover -s tests -b` — 2597 tests, OK (53 skipped, pre-existing). JS contract tests (`tests/js/test_kbhrecipe_contract.js`, `tests/js/test_kbhbrew_contract.js`) were **not** re-executed in this Bridge sandbox — `node <file>` is outside `--allowedTools` here, the same documented constraint PR #287 hit; their last-known-green state is CI evidence from PR #286/#287/#292/#293, not re-verified by this audit. |

---

## 1. Verdict: **TECHNICAL PASS**

Phase 3C's own definition (issue #101, `## 3C — brew-data handoff
contract`) asks for exactly five things to be *defined* before this
may be called anything more than manual file exchange:

> ownership/current copy; export/import semantics; duplicate/origin
> behavior; safe continuation; conflict expectations. No cloud/backend
> is implied by this phase.

All five are now defined **and implemented**, source-grounded on
current `master`, for both formats Phase 3C actually governs
(`.kbhrecipe`, `.kbhbrew`). No cloud/backend/account mechanism exists
anywhere in the touched code (confirmed by the same grep the decision
brief ran, repeated in §2 below). This audit found **no product
blocker** to calling Phase 3C technically complete at the scope the
roadmap itself defines.

Two caveats keep this a *technical* pass rather than an unqualified
"done, nothing left":

1. Two pre-existing doc-staleness findings from the decision brief
   (§9 there) are **still unfixed** on current master (§5 below) — a
   small, bounded, already-described follow-up, not a blocker.
2. This audit found one **new, previously unflagged** staleness item:
   `CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md`'s own header still reads as
   an unratified preflight (§5.3 below) — also small and bounded, not
   a blocker, and does not affect the *active* contract text
   (`CORE_KBHRECIPE_V1.md`), which is correct.

Neither caveat changes any product behavior, contract correctness, or
test result — both are pure documentation freshness gaps.

---

## 2. Proven behavior (source-grounded, current master)

### 2.1 Ownership / current copy

[#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253)
(APPROVED 2026-09-13) remains the only ownership *decision record*,
scoped explicitly to Phase 3B ("App owns the current structured brew
record... Web = no parallel live logging copy in Phase 3B"). Nothing
in the code enforces this — a user remains free to use either
surface's engine. What Phase 3C's implementation work changed is
**capability symmetry**, not ownership policy:

- `.kbhrecipe`: already symmetric before this round (both surfaces
  have full import/export UI) — unchanged.
- `.kbhbrew`: was asymmetric (Web's file-portability layer had zero UI
  callers) — now closed. `web/js/brygg_page.js:439`
  (`byggKbhBrewInnhold(brew)`, wired to an "Eksporter" button) and
  `web/js/brygg_page.js:491` (`importerBrygg(_ventendeImportBrew)`,
  wired to the import-preview confirm flow) confirm the file layer
  now has real UI callers, closing the gap the decision brief
  documented in its §3.1.

A **general**, Phase-3C-scoped ownership decision (analogous to #253
but covering ongoing logging beyond the Phase 3B acceptance run) was
explicitly *not* made by any of the implementation issues and remains
a separate, later owner call — this is a manual gate, not a technical
gap (§4).

### 2.2 Export/import semantics

Both formats share one consistent, now fully-implemented pattern on
both surfaces: envelope shape (`{format, version, exportedAt,
generator, payload}`), explicit-field-whitelist writers, and
preview-before-confirm import UX everywhere import exists. Confirmed
this session:

- `.kbhrecipe`: `modules/kbh_contract.py:42` and
  `modules/kbh_import.py:55` both list `originRecipeId` as a known V1
  field (no longer generic passthrough); `web/js/kbhrecipe.js:70`
  mirrors this on Web.
- `.kbhbrew`: unchanged since the decision brief — App
  (`ui/kbhbrew_panel.py`) and Web (`web/js/brew_storage.js`, now UI-wired
  per §2.1) both implement create/import/export.

### 2.3 Duplicate/origin behavior

This is the section with the most new work since the decision brief,
and the one this audit checked most carefully:

- **`.kbhbrew`**: unchanged, already-ratified three-tier identity
  (`brewId`/`originBrewId`/`parentBrewId`), exact-match duplicate
  rejection on both surfaces — confirmed still green
  (`tests.test_kbhbrew_storage_identity`,
  `tests.test_kbhbrew_schema_contract`, `tests.test_kbhbrew_roundtrip`,
  74 combined tests, this session).
- **`.kbhrecipe`**: the gap the decision brief flagged (§3.3/§3.4 —
  "no origin identity concept at all") is now closed, mirroring
  `.kbhbrew`'s pattern exactly per the ratified
  [CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md](CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md):
  - App mints `originRecipeId` on first explicit export
    (`modules/recipe_storage.py::sikre_origin_recipe_id()`,
    `modules/recipe_storage.py:484-519`) and on save-as-new
    (`ui/recipe_card.py`, per PR #286's Chief-review fix); Web mints at
    first save (`web/js/recipe_storage.js:277-295`,
    `lagreOppskriftIStore()`).
  - `recipeId` remains local-only and forbidden from export on both
    surfaces, unchanged.
  - Exact-string-equality duplicate detection rejects a second import
    with no write, on both surfaces: `modules/recipe_storage.py:546`
    (`finnes_oppskrift_med_origin`), `web/js/recipe_storage.js:250-252`
    (`finnesOppskriftMedOrigin`).
  - Missing/empty/non-string origin is legacy-compatible "no dedup
    signal," never a rejection — this was the one **genuine product
    defect** found and fixed in this exact lineage: PR #292's
    regression test (issue #288) proved Web's
    `_normaliserOppskriftForImport()` let a non-string origin (e.g.
    `12345`) survive unchanged instead of being stripped; issue
    #293/commit `7345809` fixed it (`web/js/kbhrecipe.js`, +10 lines)
    and is now merged on current master. This is exactly the kind of
    defect this audit was watching for, and it is **already resolved**,
    not an open gap.
  - Save-as-new/fork mints a fresh, distinct origin immediately (not
    deferred to a later export) on both surfaces — the one Chief-review
    fix each of PR #286 and PR #287 required, both merged.

### 2.4 Safe continuation on another surface

No new mechanism was needed or added — the decision brief's §3.5
finding stands and was not touched by this round: `.kbhbrew` import
always mints a fresh local `brewId`, and recipe identity is
never portable, so an imported brew's `recipeId` essentially never
coincidentally binds to the wrong locally-active recipe. `.kbhrecipe`'s
new origin identity (§2.3) gives continuation a real signal
("you already have a copy of this") that did not exist at decision-brief
time, strictly improving this property, not just documenting it.

### 2.5 Conflict expectations

Unchanged from the decision brief's finding, and still accurate: no
live sync channel exists anywhere in the audited code (confirmed by
re-running the same grep for a cloud/backend/shared-storage mechanism
this session — zero hits outside local `data/`/`localStorage`/file I/O).
Every import creates an independent local fork; a git-merge-style
conflict cannot occur mechanically. Two copies edited independently
after a handoff silently diverge with no live warning — this remains
true and is an explicit, roadmap-level non-goal to solve (§101: "no
automatic conflict resolver"), not a defect.

---

## 3. Remaining automated gaps

- The Web/App cross-surface `.kbhbrew` round-trip and the
  `.kbhrecipe` cross-surface origin round-trip both have dedicated,
  merged test coverage (`tests/playwright/12-kbhbrew-import-export.spec.js`;
  `tests/test_kbh_import.py`'s and
  `tests/test_kbhrecipe_origin_identity.py`'s additions from PR #292;
  `tests/js/test_kbhrecipe_contract.js`'s 11-case origin suite) — no
  further automated gap was found in this audit's own re-run of the
  closest Python suites (§0) or read of the JS/Playwright specs.
- This Bridge sandbox cannot execute `node`/`npx` directly (only exact
  git/gh/pip/unittest/generator commands are in `--allowedTools`), so
  the JS contract tests and Playwright gate were verified by reading
  their source and the prior PRs' recorded CI-green results, not
  re-executed here. This is a sandbox constraint on *this audit run*,
  not a gap in the project's own CI (`CI Test Gate` and `Playwright
  Critical Browser Gate` both run these automatically on every PR per
  `.claude/rules/testing.md`).

## 4. Remaining OWNER/manual gates

- A **general, Phase-3C-scoped ownership decision** — "which surface
  owns ongoing brew logging" beyond the Phase 3B acceptance run's
  App-only scope — was explicitly deferred by every implementation
  issue in this lineage (decision brief §3.8/§6, restated, not
  reopened, by #281's ratification) and remains a separate, later
  owner call. Not required for Phase 3C's own technical definition
  (§101's five bullets, §1 above), but real product policy the owner
  will eventually want to state explicitly.
- Divergence *visibility* (§2.5) — surfacing "you already have a copy
  of this, imported/edited on `<date>`" using the new `originRecipeId`/
  `originBrewId` signals — is possible now that the identifiers exist,
  but nothing today builds that UI. This is optional future work, not
  a Phase 3C requirement; the roadmap's own "no automatic conflict
  resolver" non-goal does not require it either.
- Real cross-machine handoff exercise (an actual `.kbhrecipe`/`.kbhbrew`
  file physically moved between App and a different browser/device by
  the owner) remains owner/real-use evidence this audit cannot itself
  produce — the automated coverage (§3) proves the *contract*, not a
  literal cross-machine file transfer.

## 5. Documentation staleness found

### 5.1 Already flagged, still unfixed (decision brief §2/§9 — not new)

- `CORE_KBHBREW_V1.md` lines 197-199: *"No App-side counterpart
  exists... App has no `.kbhbrew` reader or writer today."* Still
  present verbatim on current master; App's `.kbhbrew` engine has
  existed since PRI 3B (issue #24).
- `CORE_KBHRECIPE_V1.md` lines 232-233 and 376-378: *"Not yet wired
  into a Streamlit import UI... that is PRI 2C3."* Still present
  verbatim on current master; PRI 2C3 shipped this UI long ago
  (commit `18093dc`).

Both were explicitly recorded as a "small, bounded, separately-scoped
follow-up — not performed here" by the decision brief, twice now
(§2 and §9 there). They remain exactly that: recorded, not fixed,
not a Phase 3C blocker.

### 5.2 New finding — `CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md`'s own status header is now stale

Line 3-4 of that document still reads:

> Status: **DECISION preflight — one recommended contract stated
> below; not authorized for implementation by this document alone.**
> Awaiting owner/Chief review.

This is no longer accurate. Since that text was written the contract
has been: ratified into the active `.kbhrecipe` V1 precisification
(#281/PR #282, which explicitly instructed treating PR #279's merge as
ratification); fully implemented on App (#283/PR #286) and Web
(#284/PR #287); had one real defect found and fixed against it (#293);
and cross-surface tested against it (#288/PR #292). The document's
*normative content* is correct and is exactly what `CORE_KBHRECIPE_V1.md`
now points to (`CORE_KBHRECIPE_V1.md:135`, `:259`) — only its own
top-of-file status banner was never updated to say so. A reader who
opens this file cold (as this audit itself did) would reasonably
conclude the contract inside it is still an unadopted proposal, which
is materially misleading relative to current master. This is a genuine,
previously-unflagged staleness item — small and bounded (a header/status
line rewrite, not a content change), not a Phase 3C blocker, and not
fixed in this docs-only audit round to keep this PR's diff to exactly
one new file, per this issue's own "docs/prep only" hard guard.

### 5.3 "Sync" boundary — verified, no violation found

Re-ran the same check the decision brief performed (§3.9 there): every
use of the word "sync"/"synk" across the governing docs audited in
this round is either (a) the "Project synchronization" sense (#101 §A,
about GitHub/local/Vault/production commit state — an unrelated,
correctly-scoped use) or (b) an explicit statement that brew-data
"sync" does *not* yet apply and would require a live channel, a
divergence-detection mechanism, a conflict-resolution policy, and a
shared clock — none of which exist. No PR title/body, commit message,
or doc line reviewed in this audit calls the current `.kbhrecipe`/
`.kbhbrew` file-exchange contract "sync." The boundary #101 sets
("File exchange must not be described as synchronization until that
contract exists") is still honored on current master.

---

## 6. Non-goals / what remains manual by design

Unchanged from the decision brief §3.8/§4.3/§10, restated because
nothing in this round's implementation altered any of it:

- No live channel, no cloud/backend/account mechanism exists anywhere
  touched by this lineage — confirmed again in this audit.
- No automatic conflict resolver, no shared clock, no divergence
  detection *after* a successful import (only *at* a second import
  attempt) — all explicitly out of scope for Phase 3C and unchanged.
- The export action, the file transfer itself, the import
  confirm-step, which surface is "the" logging copy going forward, and
  retiring/marking-stale an original copy after continuation all
  remain manual, explicit user/owner actions on both surfaces today.
- No `.kbhrecipe`/`.kbhbrew` schema/version bump was introduced by any
  issue in this lineage — `originRecipeId` shipped as an optional V1
  field addition, per #281's own hard guard.

## 7. Genuine blocker requiring a later bounded issue

**None found.** The one real product defect this lineage's own process
surfaced (§2.3, malformed `originRecipeId` on Web import) was already
caught by a TEST-only issue (#288), fixed by a dedicated FAST issue
(#293), and is merged on current master — this audit re-confirms it is
closed, not open. If the owner wants the two still-stale doc sections
(§5.1) and the one newly-found stale status header (§5.2) refreshed,
that is one small, bounded, docs-only follow-up (three header/section
edits across two files) — not a blocker to calling Phase 3C technically
complete at the scope §101 itself defines.

---

## 8. What this audit explicitly does not do

Mirrors issue #291's own hard guards:

- No App/Web/Core product behavior change.
- No schema/version change.
- No cloud/backend/account architecture.
- No automatic merge/conflict resolver.
- Does not call file exchange "sync" (confirmed compliant, §5.3; does
  not itself broaden anything).
- No deploy.
- Does not touch parked #98/#100/#233/#241 or owner-private data.
- Does not fix the doc staleness it found (§5) — recorded per this
  issue's own "describe precisely but do not implement" instruction.
