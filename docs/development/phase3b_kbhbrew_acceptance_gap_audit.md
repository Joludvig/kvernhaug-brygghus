# Phase 3B — App `.kbhbrew` real-brew acceptance-gap audit (issue #269)

*Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3B "real brew acceptance". This is an AUDIT/PREP document, not a
feature-implementation record: it inspects the **current, already-shipped**
App `.kbhbrew` engine against Phase 3B's technical-readiness question — is
there a product-code blocker before App is used as the ongoing structured
brew-record copy for the next real brew (candidate: KBH Brew Lab / Eldsvenn
v1)? No product file was changed to produce this evidence — the only new
file is this document.*

**Status: AUTOMATED TECHNICAL LAYER — PASS. OWNER/real-brew evidence —
NOT STARTED (expected; out of this audit's scope). One adjacent, already-
implemented but unmerged safety net (PR #258) recommended, not required.**

---

## 1. Baseline

| Item | Value |
|---|---|
| Issue | [#269](https://github.com/Joludvig/kvernhaug-brygghus/issues/269) |
| Roadmap | [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3B |
| Ownership decision | [#253](https://github.com/Joludvig/kvernhaug-brygghus/issues/253) — App owns the current structured brew record for Phase 3B; Web is not a parallel live copy; Brew Lab owns observation/interpretation |
| Governing contract | [docs/development/CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) — `.kbhbrew` V1, Status: Active |
| Prior regression rounds audited here | [#257](https://github.com/Joludvig/kvernhaug-brygghus/issues/257) (merged PR #262) — fresh-session persistence, temporally separated OG→FG, cross-brew learning isolation; [#265](https://github.com/Joludvig/kvernhaug-brygghus/issues/265) (merged PR #268) — non-active/historical brew history-panel isolation |
| Branch | `agent/issue-269`, created from a fresh `git fetch origin` |
| `origin/master` at audit time | `5d3408bf15fa60737e160fa31e326b18f5e90e1f` (after merged PR #272, which fixed an unrelated PÅ JOBB bot-dispatch allowlist bug and re-armed this issue) |
| Date | 2026-09-15 |
| Method | Direct source read of every file under the App `.kbhbrew` engine (`modules/kbhbrew*.py`, `modules/kbhbrew_storage.py`, `ui/kbhbrew*.py`, `core/kbhbrew_v1.schema.json`), cross-checked against every `tests/test_kbhbrew_*.py` file and `git log` for the commits that introduced each behavior; no product code read from documentation summaries alone |

### 1.1 A note on stale documentation found during this audit

[CORE_KBHBREW_V1.md](CORE_KBHBREW_V1.md) §3/§6 still states *"No App-side
counterpart exists. Nothing under `modules/` references `"kbhbrew"`... App
has no `.kbhbrew` reader or writer today."* This was true when that document
was ratified (PRI 3A.2, issue #22, commit `dd71c7f`, 2026-09-02) but is now
**stale by roughly two weeks**: the App engine was implemented the very next
day (PRI 3B1, issue #24, commit `111b0a7`, 2026-09-03) and has been built out
continuously since (UI: issue #29, `f3528ba`/`66c2344`; Brew History actuals:
issue #83, `594e581`/`637db12`; sensing/learning: issue #87, `2bc525d`;
active-brew binding: issue #170, `9996794`; terminology/UX polish: issues
#237/#244/#248). This audit treats current master's code as authoritative
over that stale doc section, per this issue's own "Verification" instruction
("source-ground every conclusion against current master"). **Updating
CORE_KBHBREW_V1.md itself is out of this docs-only audit's bounded scope**
(the issue asks for a Phase 3B acceptance-gap audit, not a Core-contract
refresh) and is flagged below (§5) as a candidate small follow-up.

---

## 2. What is being audited

The App `.kbhbrew` engine, in full:

| File | Role |
|---|---|
| `modules/kbhbrew.py` (708 lines) | Pure engine: builds/freezes the snapshot, normalizes actuals/sensing/learning, builds/parses the file envelope, enforces unknown-field passthrough and the forbidden-derived-field export filter. No disk I/O, no Streamlit. |
| `modules/kbhbrew_storage.py` (293 lines) | Disk I/O only: `recipes/_kbhbrew/<brewId>.json`, one file per brew, atomic writes, manifest-provenance reading, import duplicate-origin detection. Deliberately separate namespace from legacy `recipes/_logs/`. |
| `modules/kbhbrew_ui.py` / `ui/kbhbrew_panel.py` | Brew-creation panel + import/export panel (under Bryggdag / 🔧 Verktøy). |
| `modules/kbhbrew_history_ui.py` / `ui/kbhbrew_history_panel.py` | Brew History panel: actuals/status editing, sensing/learning editing, plan-vs-actual display, non-active-brew selection. |
| `core/kbhbrew_v1.schema.json` (235 lines) | Machine-readable Core V1 schema; App's reader/writer is validated against it directly (`tests/test_kbhbrew_schema_contract.py`, `tests/test_kbhbrew_roundtrip.py`). |

This matches the five-layer model `CORE_KBHBREW_V1.md` §1 defines (identity/
lifecycle, frozen snapshot, actuals, sensing, learning) in full — not a
subset.

---

## 3. Proven Phase 3B technical behaviors (automated, source-grounded)

### 3.1 Five-layer engine, storage and schema conformance

- **Identity**: `brewId` (local), `originBrewId` (portable, defaults to
  `brewId`), `parentBrewId` (always `null`, reserved), `recipeId` (weak
  reference) — `modules/kbhbrew.py:350-382` (`bygg_ny_brew`). Verified by
  `tests/test_kbhbrew_storage_identity.py` (new brew's `originBrewId ==
  brewId`, `status == "active"`).
- **Frozen snapshot**: full-embed recipe + ingredients + equipment +
  predicted values + provenance, written once at creation
  (`modules/kbhbrew.py:308-347`, `_frys_ingredienser`/`_frys_predicted`/
  `_bygg_provenance`), immune to later mutation of the source objects
  (deep-copy proof: `tests/test_kbhbrew_snapshot.py`). `oppdater_brew_lag()`
  (`modules/kbhbrew_storage.py:206-243`) never touches `snapshot` — only
  `actuals`/`sensing`/`learning`/`status`/`brewedAt`.
- **Actuals/sensing/learning**: full normalizer + UI round trip
  (`modules/kbhbrew.py:389-433`/`536-609`; `ui/kbhbrew_history_panel.py`
  sensing/learning form at lines 219-276). Unknown-field passthrough is
  enforced at every layer including the file envelope
  (`_bygg_passthrough`/`_flett_inn_passthrough`).
- **Derived ABV is never stored as authoritative**:
  `FORBUDTE_ACTUALS_EKSPORTFELT = {"actual_abv", "abv", "actualAbv"}`
  (`modules/kbhbrew.py:87`) is stripped by the writer even if present via
  passthrough (`tests/test_kbhbrew_roundtrip.py::TestForbiddenActualAbvNeverEmitted`).
  Actual ABV shown to the user is always recomputed live
  (`modules/kbhbrew_history_ui.py::bygg_planlagt_vs_faktisk()`, calling the
  shared `modules/calculations.py::beregn_abv_fra_og_fg()` — the same
  engine the rest of the App uses, not a reimplemented formula).
- **Import/export with duplicate detection**: `eksporter_kbhbrew()` /
  `importer_kbhbrew()` (`modules/kbhbrew_storage.py:244-293`), UI-wired via
  `render_kbhbrew_import_panel()`/`render_kbhbrew_export_panel()`
  (`ui/kbhbrew_panel.py:241-360`). A fresh local `brewId` is always minted
  on import; an already-stored `originBrewId` is rejected as a duplicate,
  never silently merged (`tests/test_kbhbrew_import_export_apptest.py`).
- **Schema conformance is proven both directions**: App-native
  create→export round-trips validate against `core/kbhbrew_v1.schema.json`
  (`tests/test_kbhbrew_roundtrip.py::test_new_app_brew_export_validates_against_core_schema`),
  and the frozen legacy Web fixture
  (`tests/fixtures/legacy/web/kbhbrew_v1.json`) still validates unchanged
  (`tests/test_kbhbrew_schema_contract.py`).
- **Provenance**: the App engine already reads `core/manifest.json` per
  dataset (`modules/kbhbrew_storage.py:92-127`) and populates
  `provenance.datasets` — this is *ahead* of Web, which
  `CORE_KBHBREW_V1.md` §5.12/"Provenance implementation status" documents
  as unable to populate that field today without a build-pipeline change.
  This is a Web-side gap, not an App-side one, and out of this audit's
  App-scoped remit.

### 3.2 Issue #257 scope — fully covered, all three items

| #257 scope item | Test evidence |
|---|---|
| 1. Fresh-session reopen persistence | `tests/test_kbhbrew_history_panel_restart_apptest.py::TestFreshSessionReopenPersistence` — two genuinely independent `AppTest.from_file(...)` instances against the same on-disk store; OG saved in session 1 is read from disk (not inherited state) in session 2; reopening never creates a second brew. |
| 2. Temporally separated OG → FG updates | `tests/test_kbhbrew_history_panel_restart_apptest.py::TestTemporallySeparatedOgThenFgUpdatesAcrossFreshSessions` — OG saved in session 1, FG saved in session 2 without re-supplying OG; OG preserved, FG added, sensing/learning/snapshot untouched. |
| 3. Cross-brew learning isolation (shared `recipeId`) | `tests/test_kbhbrew_storage_identity.py::TestCrossBrewLearningIsolationForSharedRecipe` — two brews share a `recipeId`; updating `learning.nextTime` on one leaves the other's `learning`/`actuals`/frozen `snapshot` fully unchanged. |

### 3.3 Issue #265 scope — fully covered

`tests/test_kbhbrew_history_panel_apptest.py`, tests 22–25 (explicitly
headed for issue #265): current active-brew path unchanged with multiple
brews present; selecting a non-active brew mutates neither brew; editing
without saving writes nothing; saving the newly-selected (previously
non-active) brew updates only that brew and re-targets the shared
active-brew pointer exactly per the existing App A1 rule (issue #170) —
no new UX rule invented, matching that issue's explicit instruction.

### 3.4 Full regression baseline

Both `.kbhbrew`-focused (`python3 -m unittest discover -s tests -b -k
kbhbrew` → 239 tests, OK) and the full project suite were run for this
audit; see §6 for the exact result recorded at the end of this session.

---

## 4. Required distinctions (per this issue's "Required distinctions")

- **Automated technical proof** (§3 above): complete for the five-layer
  model, identity/snapshot/actuals/sensing/learning/status, import/export,
  fresh-session persistence, and non-active-brew isolation.
- **Owner/physical real-brew proof**: **not started.** No `.kbhbrew` data
  exists in this repository or working tree today — `recipes/` (including
  any `recipes/_kbhbrew/` brew files) is gitignored user data per
  `CLAUDE.md`, and a working-tree search at audit time found zero
  `*eldsvenn*` or `*.kbhbrew` files. This is expected and correct: real-brew
  evidence is owner/physical-brewing-session evidence, not something this
  audit can or should fabricate.
- **Brew Lab observation/sensory evidence**: out of scope for this audit —
  `sensing`/`learning` are wire-proven (§3.1) but their *interpretive
  meaning* remains Brew Lab's, per #253 and `CORE_KBHBREW_V1.md` §5.17.
- **Phase 3C App↔Web handoff/sync semantics**: intentionally untouched.
  Nothing in this audit treats `.kbhbrew` file import/export as "sync" —
  import/export is a manual file exchange with explicit duplicate rejection
  (§3.1), which is exactly the distinction Roadmap #101 Phase 3C is meant to
  formally define later, not a decision made here.

---

## 5. Remaining gaps, by category

### 5.1 Structured process observations intentionally outside current `.kbhbrew` support (by design, not defects)

These are **ratified Core V1 deferrals** (`CORE_KBHBREW_V1.md` §8), not
App-side omissions:

- `parentBrewId` (future shared-batch/multi-fermenter concept) — always
  `null`, reserved, no reader assigns it meaning (`modules/kbhbrew.py:373`).
- "Actual process used" (a full process-profile-shaped actual) — deferred
  (Owner decision #5); App's pre-existing `process_profile_navn` (legacy
  brew-log field, unrelated file) is not part of `.kbhbrew`.

Neither blocks Phase 3B real-brew acceptance — both were explicitly
evaluated and deferred by the owner before this audit, not discovered as
gaps now.

### 5.2 A genuinely open, but non-blocking, dual-truth risk (issue #256 / PR #258)

The **old per-recipe `📓 Bryggelogg`** (`ui/recipe_card.py`, backed by
`modules/recipe_storage.py`'s flat `recipes/_logs/` list — a wholly
separate storage namespace and data shape from `.kbhbrew`, see
`CORE_KBHBREW_V1.md` §3) remains fully writable today, with **no warning on
current master** that a recipe already has a `.kbhbrew` record. A user could
therefore log the same real brew twice, in two structurally incompatible
places, with nothing on-screen to prevent it.

This is already fully addressed at the code level: **PR #258** (issue #256,
"warn, don't hide") adds exactly this warning — `oppskrift_har_kbhbrew()`
(pure helper reusing the same recipe-identity rule as `aktiv_brew_matcher_recipe()`,
issue #170) plus one additive `st.warning(...)` in
`_render_brewday_result_panel()` — with its own dedicated AppTest coverage
(`tests/test_recipe_card_kbhbrew_warning.py`). **Verified at audit time**
(`gh pr view 258`): the PR is **OPEN**, head `b34236453a495faf06bc5171067a13bf74bf24a0`,
but **`mergeable: CONFLICTING` / `mergeStateStatus: DIRTY`** against current
master — it needs a rebase/refresh and fresh review before it can land. Per
this issue's explicit instruction, **this audit does not touch or duplicate
#256/PR #258** — it is recorded here purely as existing, relevant, unmerged
work directly bearing on "is there a remaining product-code blocker."

**Assessment: not a hard blocker.** The `.kbhbrew` engine itself functions
correctly and completely without this warning; an owner using only the
Bryggdag/`.kbhbrew` flow during a real brew (as #253 already establishes as
the intended path) is not obstructed by its absence. It is, however, the
single most relevant piece of already-built, already-tested, currently
unmerged safety work directly relevant to starting a real brew — refreshing
and merging it before or shortly after Eldsvenn begins is a reasonable,
low-risk recommendation, not a requirement.

### 5.3 Candidate further test-only regression slice (not implemented here)

`tests/test_kbhbrew_history_panel_restart_apptest.py` (issue #257) proves
fresh-session (independent second `AppTest.from_file(...)`) persistence for
**actuals (OG/FG) only** — explicitly scoped that way by #257 itself. Status,
sensing, and learning updates are proven to persist correctly to disk
(`tests/test_kbhbrew_storage_identity.py`, direct storage-layer round trip)
and to save correctly within one AppTest session
(`tests/test_kbhbrew_history_panel_apptest.py` tests 17-21), but — unlike
actuals — **not yet through a second, independent `AppTest` session the same
way #257 proved for OG/FG.** Given a real multi-week brew plausibly involves
saving a tasting judgment or `nextTime` note in a session that starts fresh
(days or weeks after the brew day), this is a real, narrow, bounded gap in
the same class #257 already closed for actuals — not a defect, a test-only
coverage slice.

**Recommended smallest bounded follow-up** (not implemented in this
docs-only audit, per its own instructions): one new test class in
`tests/test_kbhbrew_history_panel_restart_apptest.py`, mirroring
`TestFreshSessionReopenPersistence`, that saves `sensing.judgment`/
`learning.nextTime` in one `AppTest` session and confirms both are read back
from disk (not inherited state) via a second, independent `AppTest.from_file(...)`
instance against the same store. Risk class: low (test-only, mirrors an
already-established pattern); files: `tests/test_kbhbrew_history_panel_restart_apptest.py`,
harness `tests/fixtures/streamlit_harness/kbhbrew_history_harness.py` (reuse,
no change expected).

### 5.4 Documentation staleness (not a product gap)

`CORE_KBHBREW_V1.md` §3/§6 (see §1.1 above) should eventually be refreshed
to describe the now-complete App engine instead of its pre-issue-#24 state.
This is a docs-consistency note, not a Phase 3B acceptance blocker, and is
explicitly **not** performed in this audit (would be scope creep beyond
"audit/prep only").

---

## 6. Tests/checks run this session

- `python3 -m unittest discover -s tests -b -k kbhbrew` → **239 tests, OK**.
- Full project suite: `python3 -m unittest discover -s tests -b` → **2548
  tests, OK (53 skipped, pre-existing/unrelated), 0 failures/errors**.
- No product code was read, modified, or executed beyond running the
  existing test suite — this audit is read-only with respect to `modules/`,
  `ui/`, `core/`, and `web/`.

---

## 7. Overall

**Automated Phase 3B technical layer: PASS.** Every behavior Roadmap #101
Phase 3B's "real brew acceptance" technically depends on — one active
structured brew record bound to Brewday (App A1, issue #170), frozen
snapshot, actuals/sensing/learning/status capture, fresh-session disk
persistence, cross-brew isolation, non-active-brew history safety, and
`.kbhbrew` import/export with duplicate protection — is implemented and has
real, source-grounded, mostly AppTest-level (not merely unit-level)
regression coverage. **No product-code blocker exists** before using App as
the ongoing structured logging copy for the next real brew.

**Roadmap #101 Phase 3B itself is not being declared complete by this
document** — the owner/physical real-brew run (Eldsvenn v1 or equivalent)
is the actual acceptance test per Phase 3B's own definition ("use real
brewing as a running acceptance test"), and that run has not started. This
audit's PASS covers exactly what automation can prove about the technical
substrate that real brew will run on; it is not a substitute for the brew
itself. One non-blocking recommendation (§5.2, refresh/merge PR #258) and
one bounded candidate follow-up (§5.3) are recorded, not filed as new issues,
per this issue's explicit "do NOT create extra issues automatically"
instruction.
