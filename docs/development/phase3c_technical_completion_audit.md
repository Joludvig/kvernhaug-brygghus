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
| `origin/master` at audit time | `a9df524` (refreshed from this audit's original `1227cb0` baseline per Chief review round 2 on this PR; one more merge landed in between, #296/issue #290, `docs(core): correct stale App-counterpart claims in CORE_KBHBREW_V1.md`, which fixes the first of §5.1's two originally-still-unfixed findings — the queue baseline was `a817de6`) |
| Inputs audited | [phase3c_brew_data_handoff_contract_decision_brief.md](phase3c_brew_data_handoff_contract_decision_brief.md) (#270/PR #274); [CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md](CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md) (#276/PR #279, ratified #281/PR #282); Web `.kbhbrew` UI (#275/PR #277); App `originRecipeId` (#283/PR #286); Web `originRecipeId` (#284/PR #287); cross-surface handoff test (#288/PR #292); malformed-origin fix (#293, commit `7345809`); `CORE_KBHBREW_V1.md` staleness fix (#296/issue #290, merged `a9df524`); [CORE_KBHRECIPE_V1.md](CORE_KBHRECIPE_V1.md); [CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md); [#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253) (Phase 3B ownership decision); [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3C's own 5-bullet definition. |
| Method | Direct source read of `modules/kbh_contract.py`, `modules/kbh_import.py`, `modules/recipe_storage.py`, `web/js/kbhrecipe.js`, `web/js/recipe_storage.js`, `web/js/brygg_page.js`, `web/js/brew_storage.js`, plus the governing Core docs above — not documentation summaries alone. Every claim below is grounded in a current file:line citation or a rerun test result, not carried forward from the decision brief's own (now nine-day-old) source read. |
| Tests run this session | `python3 -m unittest tests.test_kbh_contract tests.test_kbh_import tests.test_kbh_import_apply tests.test_kbhrecipe_origin_identity tests.test_kbh_passthrough tests.test_kbhbrew_storage_identity tests.test_kbhbrew_schema_contract tests.test_kbhbrew_roundtrip -b` — 232 tests, OK. Full suite: `python3 -m unittest discover -s tests -b` — 2597 tests, OK (53 skipped, pre-existing). JS contract tests (`tests/js/test_kbhrecipe_contract.js`, `tests/js/test_kbhbrew_contract.js`) were **not** re-executed in this Bridge sandbox — `node <file>` is outside `--allowedTools` here, the same documented constraint PR #287 hit; their last-known-green state is CI evidence from PR #286/#287/#292/#293, not re-verified by this audit. |

---

## 1. Verdict: **TECHNICAL PARTIAL**

*(Revised from an initial TECHNICAL PASS after Chief review on this
PR flagged an internal contradiction — see "Revision note" below.)*

Phase 3C's own definition (issue #101, `## 3C — brew-data handoff
contract`) asks for exactly five things to be *defined* before this
may be called anything more than manual file exchange:

> ownership/current copy; export/import semantics; duplicate/origin
> behavior; safe continuation; conflict expectations. No cloud/backend
> is implied by this phase.

Four of the five are now defined **and implemented**, source-grounded
on current `master`, for both formats Phase 3C actually governs
(`.kbhrecipe`, `.kbhbrew`): export/import semantics (§2.2),
duplicate/origin behavior (§2.3), safe continuation (§2.4), and
conflict expectations (§2.5). No cloud/backend/account mechanism
exists anywhere in the touched code (confirmed by the same grep the
decision brief ran, repeated in §2 below).

The fifth — **ownership/current copy** — is only partially settled.
[#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253)
decided ownership for the Phase 3B real-brew acceptance run only, and
says so in its own text (its "Phase 3C boundary" section: *"Phase 3C
will separately define App↔Web handoff semantics, including:
ownership/current copy..."*). No later issue in this lineage made that
separate, general Phase-3C-scoped ownership decision (§2.1, §4). What
Phase 3C's implementation work actually delivered for this bullet is
**capability symmetry** (both surfaces can now export/import both
formats) and a **duplicate/origin signal** (§2.3) a user can act on —
real, useful, source-grounded progress — but not the *policy decision*
the roadmap's own bullet asks for. Calling that "defined" would not be
source-grounded against #253's own text, so this audit does not do so.

This is why the verdict is **TECHNICAL PARTIAL**, not PASS: four of
the five Phase 3C bullets are fully closed; the fifth has strong
supporting mechanism but no decision record. It is not a product
defect — nothing is broken, and no test fails — it is an open owner
decision, structurally the same kind of gap #253 itself was written to
close for Phase 3B. See §7 for the precise, bounded follow-up this
implies.

Two further caveats, unchanged in substance from the initial pass but
refreshed against master's advance to `a9df524` (§0), remain:

1. Of the two pre-existing doc-staleness findings from the decision
   brief (§9 there), one is now **fixed and merged** on current master
   (#296/issue #290 fixed `CORE_KBHBREW_V1.md`'s "No App-side
   counterpart exists" claim) and one remains **still unfixed**
   (`CORE_KBHRECIPE_V1.md`'s "Not yet wired into a Streamlit import
   UI... PRI 2C3" claim) — a small, bounded, already-described
   follow-up, not a blocker (§5.1 below).
2. This audit found one **new, previously unflagged** staleness item:
   `CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md`'s own header still reads as
   an unratified preflight (§5.2 below) — also small and bounded, not
   a blocker, and does not affect the *active* contract text
   (`CORE_KBHRECIPE_V1.md`), which is correct.

Neither caveat changes any product behavior, contract correctness, or
test result — both are pure documentation freshness gaps.

---

## 2. Proven behavior (source-grounded, current master)

### 2.1 Ownership / current copy — **not fully defined** (the reason for PARTIAL)

[#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253)
(APPROVED 2026-09-13) remains the only ownership *decision record*,
and it scopes itself explicitly to Phase 3B: *"For Phase 3B real-brew
acceptance, the App owns the current structured brew record / running
logging copy... Web = no parallel live logging copy in Phase 3B."*
#253 does not stop there — its own "Phase 3C boundary" section states
in plain language that this question is deliberately left open for
Phase 3C to answer separately: *"Phase 3C will separately define
App↔Web handoff semantics, including: ownership/current copy..."* No
later issue in this lineage (#270/#274, #275/#277, #276/#281, #283/
#286, #284/#287, #288/#292, #293) made that separate, general
Phase-3C-scoped ownership decision. Nothing in the code enforces any
ownership policy either way — a user remains free to use either
surface's engine as "the" current copy.

What Phase 3C's implementation work actually changed is **capability
symmetry**, not ownership policy:

- `.kbhrecipe`: already symmetric before this round (both surfaces
  have full import/export UI) — unchanged.
- `.kbhbrew`: was asymmetric (Web's file-portability layer had zero UI
  callers) — now closed. `web/js/brygg_page.js:439`
  (`byggKbhBrewInnhold(brew)`, wired to an "Eksporter" button) and
  `web/js/brygg_page.js:491` (`importerBrygg(_ventendeImportBrew)`,
  wired to the import-preview confirm flow) confirm the file layer
  now has real UI callers, closing the gap the decision brief
  documented in its §3.1.

Capability symmetry is real, useful progress, and it is what makes
safe continuation (§2.4) and duplicate/origin detection (§2.3) work on
both surfaces. But the roadmap's own bullet asks for ownership/current
copy to be *defined*, and #253 explicitly did not define it beyond
Phase 3B — so this bullet is not closed, and the general,
Phase-3C-scoped ownership decision remains a separate, later owner
call (§4, §7).

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
  owner call. This is not optional polish: it is the one Phase 3C
  bullet (§101's five bullets, §1/§2.1 above) this audit found not yet
  defined, and it is the reason this audit's verdict is TECHNICAL
  PARTIAL rather than PASS. See §7 for the precise, bounded follow-up
  this implies.
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

### 5.1 Already flagged (decision brief §2/§9 — not new): one now fixed, one still open

- `CORE_KBHBREW_V1.md` lines 197-199 (as read at this audit's original
  baseline, `1227cb0`): *"No App-side counterpart exists... App has no
  `.kbhbrew` reader or writer today."* **Now fixed and merged** —
  #296/issue #290 (`docs(core): correct stale App-counterpart claims
  in CORE_KBHBREW_V1.md`, merged to master as `a9df524`) replaced this
  claim with a source-grounded description of App's current
  `.kbhbrew` engine (that document's Section 2/3), and separately
  corrected a related Web-UI-caller staleness Chief flagged on that
  PR's own review round. Re-read directly against current master
  (`a9df524`) for this round: the stale sentence is gone.
- `CORE_KBHRECIPE_V1.md` lines 232-233 and 376-378: *"Not yet wired
  into a Streamlit import UI... that is PRI 2C3."* **Still present
  verbatim** on current master (`a9df524`); PRI 2C3 shipped this UI
  long ago (commit `18093dc`). Unaffected by #296 (that PR only
  touched `CORE_KBHBREW_V1.md`).

Both were explicitly recorded as a "small, bounded, separately-scoped
follow-up — not performed here" by the decision brief, twice
(§2 and §9 there). One has since been fixed by a dedicated follow-up
issue in this same lineage (#290); the other remains recorded, not
fixed, not a Phase 3C blocker.

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

**No product/code blocker found.** The one real product defect this
lineage's own process surfaced (§2.3, malformed `originRecipeId` on
Web import) was already caught by a TEST-only issue (#288), fixed by a
dedicated FAST issue (#293), and is merged on current master — this
audit re-confirms it is closed, not open.

What *is* still open is a **decision**, not a defect: the general,
Phase-3C-scoped ownership/current-copy call (§2.1, §4) that #253 itself
deferred to Phase 3C and that no later issue in this lineage made. The
precise, bounded follow-up this audit recommends — describing it per
this issue's own instruction, not implementing or filing it here — is
a single DECISION-type issue, structurally identical to #253 itself:
state which surface owns the current/ongoing logging copy once Phase
3B's acceptance run ends (or state explicitly that no single-owner
policy is required going forward and manual dual-surface use is
accepted), record it as a durable decision, and no more. That decision
alone — no code change — would close the one Phase 3C bullet (§101)
this audit found undefined and would let a follow-up audit call Phase
3C a full TECHNICAL PASS.

Separately, if the owner wants the one still-stale doc section (§5.1 —
`CORE_KBHRECIPE_V1.md`'s PRI 2C3 claim; `CORE_KBHBREW_V1.md`'s
counterpart claim was already fixed by #296/issue #290 during this
PR's review) and the one newly-found stale status header (§5.2)
refreshed, that is one small, bounded, docs-only follow-up (two
header/section edits across two files) — independent of the ownership
decision above, and not a blocker either way.

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

## 9. Revision note (Chief review, PR #297)

This audit's first version verdicted **TECHNICAL PASS** while its own
§2.1/§4 already stated that a general Phase-3C ownership/current-copy
decision had not been made — an internal contradiction Chief review
caught on exact head `a9a0ca7`. Reconciling it required checking which
side was accurate rather than picking one by default: #253's own text
(its "Phase 3C boundary" section) explicitly defers the general
ownership question to Phase 3C, so it cannot also be read as having
answered it. That makes §2.1/§4's finding the correct one, and the
verdict the part that needed to change. Fixed by downgrading the
verdict to **TECHNICAL PARTIAL** and reworking §1/§2.1/§4/§7 so the
document is internally consistent: four of five Phase 3C bullets
closed, the fifth (ownership/current copy) open pending one bounded
owner decision, described but not filed in §7. No other section
(§2.2–§2.5, §3, §5, §6, §8, §0) needed a content change — only §1's
verdict and its cross-references to §2.1/§4/§7 were inconsistent with
the audit's own evidence.

## 10. Revision note 2 (Chief review round 2, PR #297)

Between this audit's round-1 fix (§9) and Chief's round-2 review,
master advanced from `1227cb0` to `a9df524` via PR #296/issue #290,
which fixed the first of §5.1's two "already flagged, still unfixed"
findings (`CORE_KBHBREW_V1.md`'s stale "No App-side counterpart
exists" claim) — a fix this audit's own §7 had itself recommended as
exactly the kind of small, bounded, docs-only follow-up worth doing.
Chief flagged (round 2, head `c4f2fab`) that this audit still
described that finding as open, making it stale relative to current
master. Fixed by re-reading `CORE_KBHBREW_V1.md` directly against
`a9df524` (confirmed the stale sentence is gone) and updating §0's
baseline row, §1's caveat list, §5.1, and §7 to state the first
finding as fixed/merged, while leaving the second finding
(`CORE_KBHRECIPE_V1.md`'s PRI 2C3 claim, unaffected by #296), the
TECHNICAL PARTIAL verdict, the ownership/current-copy gap (§2.1/§4),
and every other finding, source citation, and test result unchanged —
per Chief's own instruction to keep the verdict stable "unless the
refreshed source evidence materially says otherwise," which it does
not.
