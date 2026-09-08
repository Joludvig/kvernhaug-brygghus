# Web W5 — Brew completion contract: decision brief (issue #131)

*Part of KBDP, preparation for #101 Phase 1 / W5 / B04. Builds directly on the
merged preflight, [web_w5_brew_completion_preflight.md](web_w5_brew_completion_preflight.md)
(issue #118) — that document is the evidence base; this one turns its §6
alternatives into a scoped decision brief with a recommendation. See
[../../CLAUDE.md](../../CLAUDE.md) for the wider document system.*

**Status: docs-only decision brief. No `web/**` file is touched by this
issue, and W5 is NOT implemented here.** All code references below were
re-verified directly against the current `master` source
(`web/js/brew_storage.js`, `web/js/brygg_page.js`) at the time of writing —
every line number the preflight cited still matches exactly (`bryggFase()`
at `brew_storage.js:611-619`, the `ferdige`/`aktive` filter at
`brygg_page.js:403-404`, the "Avslutt" button wiring at
`brygg_page.js:266-278`, `_byggFerdigRad()` at `brygg_page.js:322-360`) —
so nothing here is contradicted by drift since the preflight was written.

The recommendation in §3 is **a recommendation for Chief, not a decision**.
Everything downstream of it (§5-§9) describes what implementing that
recommendation would look like, so Chief can evaluate the option against a
concrete plan rather than an abstract label — it is not authorization to
build it.

---

## 1. The problem in one paragraph

`status` (`active`/`done`/`discarded`) and `bryggFase()` (derived from which
fields are filled in: `bryggedag → gjaering → smaking → ferdig`, or
`forkastet`) are two independent axes. The "Avslutt" button is visible and
clickable as soon as `fase === "smaking"` — i.e. *before* the user has given
a `sensing.judgment` — and sets `status:"done"` unconditionally. The
"Ferdige brygg" list requires **both** `bryggFase(b) === "ferdig"` **and**
`b.status === "done"` (`brygg_page.js:403`). So a brew the user explicitly
ended can sit indefinitely under "Under arbeid", still showing the tasting
question and a re-clickable "Avslutt" button, with no visible sign the user
already completed it. Roadmap #101 names this exact gap as W5/B04: *"Finished
must agree with list placement and explicit completion action."*

## 2. Option comparison table

These map directly onto the preflight's §6 alternatives, renamed to match
this issue's three required option families:

| Option | Preflight name | One-line mechanism |
|---|---|---|
| **A — status-driven history placement** | Alternative A (recommended there) | `ferdige` filter in `visLogg()` uses **only** `b.status === "done"`; drop the `bryggFase(b) === "ferdig"` clause. |
| **B — requiring judgment before completion** | Alternative B | Remove/hide the "Avslutt" button while `fase === "smaking"`; only show it once `fase === "ferdig"` (i.e. after a judgment is recorded). |
| **C — explicit "done but not yet judged" handling** | Alternative C | Keep the current AND-gate (`bryggFase(b) === "ferdig" && b.status === "done"`) untouched, but surface a persistent, visible notice on a `status:"done"` brew that is still sitting in "Under arbeid" because judgment is missing. |

All three preserve the preflight's stated core principle: `status` remains
free, unenforced metadata (`brew_storage.js:25`, `:103-106`) — none of them
introduce a hard state machine with enforced transitions.

## 3. Dimension-by-dimension comparison

| Dimension | A — status-driven placement | B — require judgment first | C — explicit done-but-unjudged notice |
|---|---|---|---|
| **Exact code paths affected** | `brygg_page.js:403` (`ferdige` filter, one clause removed) | `brygg_page.js:198-278` (split the current `fase === "smaking" \|\| fase === "ferdig"` branch so the "Avslutt" button/handler at 266-278 only renders under `fase === "ferdig"`) | `brygg_page.js:403` unchanged; new conditional block in `_byggKort()` (`fase === "smaking"` branch, ~184-197) rendering a notice when `brew.status === "done"`; possibly a small CSS class for the notice |
| **User-facing behavior in normal flow** | Clicking "Avslutt" at any point (with or without judgment) moves the brew to "Ferdige brygg" immediately | User cannot click "Avslutt" until a judgment (`yes`/`maybe`/`no`) is recorded — the "avslutt without tasting" path is removed entirely | Clicking "Avslutt" without judgment leaves the brew in "Under arbeid" exactly as today, but now with a persistent banner explaining why |
| **Effect on "Under arbeid" vs "Ferdige brygg"** | Placement now agrees with the explicit action (`status:"done"`) in 100% of cases, regardless of judgment state | Placement continues to agree with `bryggFase() === "ferdig"` as today — the AND-gate becomes redundant (`status:"done"` and `fase === "ferdig"` become equivalent by construction) but is harmless to leave in place | No behavior change to either list; only what the "Under arbeid" card communicates changes |
| **Effect on frozen snapshot** | None — `snapshot` is never touched by any option (`opprettBrygg`/`oppdaterBrygg` never mutate it, `brew_storage.js:466-515`) | None | None |
| **Effect on "Next time" loop** | None — `sisteErfaringForOppskrift()` already reads `learning.nextTime` independently of `status`/`fase` (`brew_storage.js:588-601`); no option changes that function | None | None |
| **Effect on reopen/resume** | "Gjenåpne" (`brygg_page.js:345-351`) sets `status:"active"` regardless of judgment already today; unaffected by any option | Unaffected — reopening a `ferdig` brew still lands back in the smaking-equivalent view since `fase` is re-derived from `actuals`/`sensing`, not `status` | Unaffected; the notice simply stops rendering once `status` changes away from `"done"` |
| **Compatibility with incomplete-but-valid brew records** | Fully compatible — a `status:"done"` brew with sparse `actuals`/`sensing` renders via `_byggFerdigRad()`, which already tolerates a missing judgment badge (hides `.brygg-dom-merke`, `brygg_page.js:338-344`) and a missing OG/FG shows as `"–"` (`_fmtSg`) | Fully compatible, but changes what "valid" means at the point of completion — a brew can no longer become `status:"done"` without a judgment, which is a narrower definition of "valid to finish" than the data model otherwise allows | Fully compatible — no data-shape change at all |
| **Compatibility with latent `.kbhbrew` import** | The known import fallback (`importerBrygg()` defaults an unrecognized/missing `status` to `"done"`, `brew_storage.js:774`, preflight §5 finding 5) becomes **immediately user-visible**: any imported file lacking `status` lands directly in "Ferdige brygg" even with empty `actuals`/`sensing` — same underlying gap as finding 1, now reachable via a second path once import UI ships. Not a regression *introduced* by Option A, but Option A stops masking it | Same import fallback stays masked today (no import UI exists, §2.8) but would, if import UI ever ships, still let a file bypass "require judgment" by arriving pre-labeled `status:"done"` without ever going through the button — Option B's guarantee only holds for the UI path, not the data layer | The notice logic could double as the import-path fix for free (same `status:"done"` + no-judgment condition), but only if the import UI is ever built — currently moot since no import UI exists |
| **W3 save-state coupling** | None found — `startBrygging()`/`oppdaterBrygg()` never touch `AKTIV_KLADD_NOKKEL` or any save-state function (preflight §8); no option changes this | None | None |
| **Migration/backward-compat risk** | None — no stored-data shape changes; existing `status:"done"` brews already lacking a judgment (if any exist in real user data from before this fix) immediately surface in "Ferdige brygg" on next load, which is the intended fix, not a migration | None — existing `status:"done", fase:"smaking"` brews (if any exist) remain in "Under arbeid" forever unless the user re-opens and re-completes them through the new gated flow; this is a case Option B does **not** self-heal | None — existing affected brews get a `status:"done"` notice going forward, same self-healing profile as A but without moving them out of "Under arbeid" |
| **Implementation complexity** | Lowest — one boolean clause removed from one filter expression, no new i18n keys, no new markup | Medium — restructure a conditional branch that currently handles two `fase` values together; must decide what an already-`status:"done"`-but-still-`smaking` brew (pre-existing edge case, or a race) should show once the button is gone from that branch | Medium — new conditional render path, new i18n string(s) (NO+EN pair per `.claude/rules/web.md`), new CSS treatment, needs its own visual regression check |
| **Testability** | Easiest to verify: one Playwright case (A1 below) covers the fix directly; `_byggFerdigRad()`'s existing missing-judgment tolerance needs no new test, only confirmation it still holds | Requires testing both the removed-button state and confirming no other path can still produce a judgment-less `status:"done"` brew (there is: the import fallback, see row above) | Requires testing notice presence/absence across all four `status`×judgment combinations, plus NO/EN parity for the new string(s) |

## 4. Recommendation

**Option A — status-driven history placement** — unchanged from the
preflight's own §6 recommendation, now re-confirmed against the fuller
dimension set above.

**Why, tied directly to #101's wording** ("Finished must agree with list
placement and explicit completion action. Preserve frozen snapshot and
'Next time' loop."):

- Option A makes list placement a direct, unconditional function of the
  explicit completion action (clicking "Avslutt" → `status:"done"` →
  appears in "Ferdige brygg"). That is the literal reading of "must agree
  with... explicit completion action" — placement no longer depends on a
  *second*, independent signal (`judgment`) the roadmap sentence never
  mentions.
- Option C also preserves the roadmap wording's *letter* (it doesn't change
  placement logic) but not its *substance* — the disagreement between
  action and placement still exists after Option C, it is merely explained
  to the user instead of resolved. That fails "must agree."
- Option B achieves agreement too, but by narrowing what "explicit
  completion action" is allowed to mean — it removes the pre-existing
  "finish this brew without recording a taste judgment" path entirely. The
  preflight (§6) already flags this as a real, possibly intentional
  affordance ("the user may have good reasons to finish without ever
  wanting to judge flavor — e.g. a batch they never tasted"), so removing
  it is a larger, less certain product change than the roadmap sentence
  requires.
- Both frozen-snapshot and "Next time" are unaffected by any option (§3),
  so Option A's compatibility here is not a distinguishing factor — it is
  simply confirmed, not threatened.
- Option A is also the lowest-complexity, most directly testable change of
  the three (§3, last two rows), which matters given #101's broader
  "smallest contract" framing for W5.

**The one real cost of Option A**, stated plainly rather than glossed over:
it makes the `.kbhbrew` import fallback bug (preflight §5 finding 5) newly
*reachable* in principle, once import UI ships — a `status:"done"` file
with no `actuals`/`sensing` would appear in "Ferdige brygg" immediately
instead of being masked by the AND-gate. This is not a reason to prefer
Option C or B (neither actually closes that data-layer gap either, per the
row above — B only closes the *button* path, not the *import* path); it is
a reason to fix the import fallback in the same round that ever wires up
import UI, not to treat Option A as introducing a new bug. Since no import
UI exists today (confirmed unchanged, preflight §2.8), this has zero
observable effect until then.

## 5. Exact implementation touchpoints (for a future W5 round — not built here)

- **`web/js/brygg_page.js:403`** — the one required change:
  ```js
  const ferdige = alle.filter((b) => bryggFase(b) === "ferdig" && b.status === "done");
  ```
  becomes
  ```js
  const ferdige = alle.filter((b) => b.status === "done");
  ```
  (`aktive` at line 404, defined as "everything not in `ferdige`", needs no
  separate edit — it already follows from `ferdige` by construction.)
- **`web/js/brygg_page.js:322-360`** (`_byggFerdigRad()`) — verify only,
  likely no change: already tolerates a missing `sensing.judgment` (hides
  `.brygg-dom-merke`, lines 338-344) and missing `actuals.og`/`fg` (renders
  `"–"` via `_fmtSg`, line 330). A brew reaching "Ferdige brygg" via Option
  A with `fase` still `"bryggedag"`/`"gjaering"`/`"smaking"` is a genuinely
  new reachable state for this row template (today only `fase === "ferdig"`
  brews ever reach it) and should be spot-checked in browser, not assumed
  safe from static reading alone.
- **`web/js/brew_storage.js`** — `bryggFase()` itself (lines 611-619)
  requires **no change**; it continues to correctly describe derived data
  state, independent of list placement. (Preflight §7 already noted this.)
- **`web/js/i18n.js`** — no new keys required for Option A itself, since no
  new UI text is introduced.
- **`web/js/app.js`** — no touchpoint; `startBrygging()`/
  `visForrigeErfaring()` are unaffected (preflight §5 point 3 / §7).
- **`web/js/custom_ingredient_id.js`** — no touchpoint; its only brew-data
  dependency (`alleBrygg()` for collision checks) is unaffected by list
  *filtering* logic.

## 6. Explicit non-goals for W5 under this recommendation

- **Does not** touch `startBrygging()`'s lack of a duplicate-`active`-brew
  warning (preflight §5 point 2 / §10 question 4) — an open, separate
  question the preflight explicitly flagged as possibly out of scope for
  W5; this brief does not resolve it either.
- **Does not** change when "Next time" becomes visible in the builder
  (preflight §5 point 3) — already independent of `status`/`fase` today,
  and Option A does not touch `sisteErfaringForOppskrift()`.
- **Does not** fix the `.kbhbrew` import `status:"done"` fallback
  (`brew_storage.js:774`, preflight §5 finding 5) — no import UI exists to
  make this observable yet (§2.8); tracked as a required companion fix
  *whenever* import UI is later built, not part of this W5 round.
- **Does not** introduce a hard completion state machine or enforce field
  completeness before `status:"done"` is settable — preserves the explicit
  "an incomplete brew is a valid brew" design principle (preflight §6,
  `brew_storage.js:25`/`:103-106`).
- **Does not** implement anything — this document, like the preflight
  before it, changes no file under `web/**`.

## 7. Acceptance criteria (for a future implementation round)

1. Clicking "Avslutt" from `fase:"smaking"` (no judgment given) moves the
   brew to "Ferdige brygg" immediately, in the same page render.
2. Clicking "Avslutt" from `fase:"ferdig"` (judgment already given) behaves
   exactly as today — no regression.
3. A "Ferdige brygg" row for a brew with no `sensing.judgment` renders
   without the judgment badge and without a layout break (verifies
   `_byggFerdigRad()`'s existing tolerance actually holds in-browser for
   this newly-reachable combination).
4. A "Ferdige brygg" row for a brew with missing `actuals.og`/`fg` (reached
   only if judgment-less completion is itself reached from `fase:"bryggedag"`
   or `"gjaering"` — confirm whether the UI can produce this at all, since
   today "Avslutt" only renders under `fase === "smaking" || "ferdig"`, both
   of which already guarantee `og`/`fg` are set by `bryggFase()`'s own
   precedence) renders `"–"` placeholders, not `NaN`/`undefined`.
5. "Gjenåpne" on a brew completed via this new path returns it to "Under
   arbeid" exactly as any other reopened brew, re-deriving `fase` from
   `actuals`/`sensing` as before.
6. A discarded brew never appears in "Ferdige brygg" under Option A. This is
   **not** because of `bryggFase()`'s "forkastet" precedence — under Option
   A the `ferdige` filter is `b.status === "done"` only (§5) and no longer
   calls `bryggFase()` at all, so that precedence does not participate in
   this decision. The actual mechanism: the discard handler
   (`brygg_page.js:309`) calls `oppdaterBrygg(brew.brewId, { status:
   "discarded" })`, which overwrites the brew's `status` field in place
   (`brew_storage.js:503`) — a brew holds exactly one *current* `status`
   value, never a history of prior values — so a discarded brew's `status`
   is `"discarded"`, which fails the `=== "done"` check directly. (`
   bryggFase()` still independently returns `"forkastet"` for such a brew,
   used elsewhere — e.g. the "Under arbeid" card label — but that return
   value is not consulted by the `ferdige` filter under Option A.) Where
   this criterion says "regardless of status history", it means: regardless
   of what the brew's status was *before* being discarded — a brew never
   holds a stale `"done"` value alongside a current `"discarded"` one, since
   `oppdaterBrygg()` always overwrites the single current field — not that
   any historical marker is tracked or consulted.
7. Frozen `snapshot` is provably unchanged before/after (still not
   mutable by any code path touched).
8. "Next time" visibility in the builder is unaffected — a brew's
   `learning.nextTime` still surfaces in `visForrigeErfaring()` under the
   exact same conditions as before this change.
9. Zero raw i18n keys / `"undefined"` strings introduced (expected, since
   no new keys are needed for Option A) — regression-checked, not merely
   assumed.
10. Zero console/network errors across the scenarios above, in both
    Chromium and Firefox (existing baseline, `web-full-regression` skill).

## 8. Browser cases (manual Playwright sweep — no automated E2E exists in `tests/`, per `.claude/rules/testing.md`)

These extend the preflight's §9 acceptance matrix (A1-A9), scoped to what
Option A specifically needs verified, not the full W5 surface:

| # | Scenario | Expected outcome under Option A |
|---|---|---|
| B1 | Click "Avslutt" from `fase:"smaking"`, no judgment given | Brew appears in "Ferdige brygg" immediately; disappears from "Under arbeid" |
| B2 | Give judgment, then click "Avslutt" (normal order) | Unchanged from current behavior — appears in "Ferdige brygg" with judgment badge |
| B3 | Complete without judgment (B1), then "Gjenåpne", then give judgment, then "Avslutt" again | Ends in "Ferdige brygg" with judgment badge now shown; no duplicate row |
| B4 | Complete without judgment (B1); inspect the "Ferdige brygg" row visually | No badge shown, no layout break, OG/FG/ABV shown normally (both were already required to reach `fase:"smaking"`) |
| B5 | Discard a brew that already has `status:"done"` (if reachable via UI at all — confirm reachability first, per preflight §9 A4) | Still shown as `forkastet` in "Under arbeid", never in "Ferdige brygg" — because the discard action overwrites `status` to `"discarded"` (`brygg_page.js:309`), which fails the `ferdige` filter's `b.status === "done"` check directly (see acceptance criterion 6); confirms the brew's prior `"done"` value is not still readable anywhere the filter checks |
| B5b | Complete a brew via "Avslutt" (B1) so it appears in "Ferdige brygg", then discard it from "Ferdige brygg"/"Under arbeid" (whichever the UI allows once `status:"done"`) | Brew disappears from "Ferdige brygg" immediately and shows as `forkastet`; regression proof that a `"done"` → `"discarded"` transition removes the brew from the finished list under Option A, not just that a never-completed brew stays out of it |
| B6 | Run B1-B4 in both NO and EN | Identical behavior and text both languages; 0 raw keys |
| B7 | Repeat B1-B6 at 390×844 and 768×1024 viewports | No layout break, no horizontal overflow |
| B8 | Full scenario set B1-B7 | 0 console/network errors, both Chromium and Firefox |

## 9. Automated/static test opportunities

- **`bryggFase()` itself** is a pure function in `brew_storage.js` and is,
  in principle, executable coverage territory for
  `tests/web_js_runtime.py`'s Node-based harness (see
  `tests/test_web_js_brew_storage.py`) — but that harness is **currently
  fully blocked**: `run_web_js()` refuses to shell out to `node` at all,
  pending a separate, explicitly-reviewed Bridge Bash-permission change
  (Chief review, PR #53; every test in that module is `@unittest.skip`-ped
  today). Option A does not change `bryggFase()`, so this blocker is
  unaffected either way, but it means a future W5 implementation round
  **cannot** currently add executed-JS unit coverage for the changed
  `ferdige` filter itself.
- **The `ferdige`/`aktive` filter logic** (`brygg_page.js:403-404`) is
  DOM-coupled (`document.getElementById`) inside `visLogg()`, unlike the
  pure `brew_storage.js` layer — even once the Node-harness blocker above
  is lifted, this specific filter would need either extraction into a
  DOM-free helper (a real, if small, refactor beyond this option's stated
  scope) or a browser-level (Playwright) check to exercise directly. Under
  today's constraints, §8's manual Playwright sweep is the only available
  verification path for this specific change.
- **i18n symmetry**: Option A introduces zero new `data-i18n-*` keys, so
  `tests/test_generate_web_i18n_pages.py` needs no new assertions and
  requires no re-run beyond the standard `.claude/rules/web.md` regression
  discipline for any `web/**` diff. (Option C, by contrast, would require
  new keys and would need this suite exercised as part of that work.)
- **Static verification available now, without touching code**: the line
  numbers and existing tolerances cited throughout this document (§3, §5)
  were confirmed by direct `grep`/read against current `master` as part of
  producing this brief — a future implementation round can diff against
  those exact anchors to detect drift before starting.

## 10. Unresolved product questions that still require Chief choice

1. **Is Option A actually the right contract**, or does Chief prefer B/C
   for reasons this brief's evidence doesn't capture (e.g. a product
   preference that a brew should never be "finished" without a recorded
   taste judgment, which would favor B despite its larger scope)? This
   brief recommends but does not decide.
2. **Is the `.kbhbrew` import fallback** (`brew_storage.js:774`, §6 above)
   in scope for *this* W5 round at all, given it has zero observable effect
   today (no import UI exists), or should it be explicitly deferred to
   whichever future round adds import UI? Not answered here — flagged as
   the one real trade-off Option A surfaces.
3. **Is B04 confirmed to be exactly preflight §5 finding 1** (the
   judgment-less "Avslutt" gap)? Neither the preflight nor this brief can
   confirm this against an actual audit text — no local "B04" reference
   exists anywhere in the repo (preflight §5, re-confirmed unchanged here).
4. Carried over unresolved from the preflight, still open: should
   `startBrygging()` warn on an existing `active` brew for the same recipe
   (§5 point 2)? Should "Next time" visibility for a not-yet-`done` brew be
   reconsidered (§5 point 3)? Both are independent of which completion
   option is chosen and are not re-litigated here.
5. **Timing**: should the fix in §5 land as its own minimal PR (one-line
   filter change, per §3's complexity comparison), or bundled with other
   W5-adjacent B04 follow-ups? A scoping choice for whoever picks up
   implementation, not something this analysis-only brief should decide.
