# Web B07 — Resolution decision (Learner guidance vs hidden content)

*Decision brief only. Produced against issue #147, itself part of #101 Phase 1
Web Stabilization. Builds on
[`web_b07_learner_guidance_triage.md`](web_b07_learner_guidance_triage.md)
(the source-proven contradiction inventory) — this document does not repeat
that inventory's evidence, it extends it with the source verification issue
#147 explicitly required, evaluates options A/B/C, and recommends one product
contract. No `web/**` product file, i18n string, CSS rule, or JS logic is
touched by this document. Authoritative master when opened:
`d522a21de711a288220abe281f6f0cfa8808d816`; revalidated against current
master `b722811a7e04def9ae98baa95acaa78e6d0cbac4` per Chief's
changes-requested follow-up (see "Revalidation" note in §1) — no premise
below changed.*

## 1. Current source truth

Confirms the triage doc's three findings still hold verbatim against current
`master`, and adds the source verification issue #147 required beyond the
triage's own scope:

- **Revalidation (Chief changes-requested follow-up, this round)** —
  `git diff d522a21..b722811 -- web/js/app.js web/js/veiledning.js
  web/js/i18n.js web/css/style.css web/index.html` is empty: none of the
  five source files this brief cites (or their line numbers below) changed
  between the master this brief was originally opened against and current
  master. The only `web/**` change in that range
  (`web/js/brygg_page.js`, brew-log tasting-slider label IDs, #150) touches
  an unrelated page/feature (`brygg_page.js` renders the post-brew tasting
  log, not the style-analysis/guidance panel this brief covers) and shares
  no function, container, or i18n key with anything cited below. Every
  source claim, line citation, and the Option A recommendation in this
  document therefore stand unchanged; no premise was disproven.

- **`.mester-only` visibility mechanism** — unchanged from the triage doc:
  `body.modus-laerling .mester-only { display: none !important; }`
  (`web/css/style.css:1651-1658`), toggled by `settModus()`
  (`web/js/app.js:337-346`).

- **Exact call chain on mode-button click (verified, not previously
  confirmed)** — `initModus()` (`web/js/app.js:355-381`) attaches one listener
  per `.modus-knapp`:
  ```js
  knapp.addEventListener("click", () => {
    settModus(knapp.dataset.modus);
    _lukkModusForstegang();
  });
  ```
  `settModus()` itself (`app.js:337-346`) only: toggles the
  `modus-laerling`/`modus-mester` body classes, updates each button's
  `aria-pressed`, and rewrites `#sidemeny-modus-status`. **It does not call
  `renderStilPanel()`, `renderStilManuell()`, or `beregnOgVisResultat()` —
  confirmed by grepping every call site of those three functions
  (`web/js/app.js:981,1355,1379,1399,1838`): none is inside `settModus()`,
  `initModus()`, or the click listener above.**

- **Learner → Master → Learner re-render (triage doc's acceptance case 4,
  explicitly left "not yet confirmed either way" — now confirmed):** a live
  mode switch does **not** re-render the style/guidance panel at all. Whatever
  guidance text (including the three contradictions) was last computed by
  `beregnOgVisResultat()` (ingredient/recipe changes) or by the
  `kvernhaug:sprakendret` listener's `_rerenderAlleEnhetsfelt()` call
  (`app.js:1970`, which "ends itself with a `beregnOgVisResultat()` call" per
  its own comment, `app.js:1969`) stays on screen unchanged through a mode
  switch. This is a **real, independent gap**, not a hypothetical: a user who
  switches Master → Learner mid-session, without also touching any
  ingredient field afterward, keeps seeing whatever guidance text was visible
  in Master mode — including a "see nearby styles below" clause that is now
  contradictory again, just via a different path (stale text) than findings
  #1/#2 (mode-blind generation). Any fix to #1/#2/#3 that only changes *what*
  gets generated, without also making mode switches re-render, reintroduces
  the same class of bug through this second path.

- **`veiledning.js` DOM-independence (verified)** — read `web/js/veiledning.js`
  in full: no reference to `document`/`window` anywhere in the file; every
  function takes explicit parameters (`stilEntry`, `stilNavn`, `feltAvvik`,
  …) and returns data/strings, matching its own header comment and
  `.claude/rules/web.md`'s DOM-independence convention for shared logic. A
  mode-aware fix inside this file must therefore take mode as an **explicit
  parameter**, threaded in from `app.js` (which already reads
  `document.body.classList.contains("modus-mester")` at `app.js:1934` — an
  established idiom, not a new one) — never read `document.body` from
  `veiledning.js` itself.

- **Hidden containers/fields and collateral effects (verified, new detail
  beyond the triage doc)** — the "Nearby styles" `.mester-only` block
  (`web/index.html:346-352`) is not merely a list of style names. It renders
  via `_stilKortHtml()` (`app.js:1289-1309`), which for each candidate style
  shows: a numeric **match score as a percentage** (`s.score`, e.g. `"78%"`),
  an optional "not official BJCP style" badge, and a `<details>` disclosure
  listing **specific missing/wanted sensory characteristics**
  (`s.mangler`/`s.onsket_sensorisk`, e.g. "❌ needs more caramel sweetness").
  This is a materially more technical artifact than "a list of style names" —
  it exposes the style-matching engine's internal scoring and gap analysis.
  The same `.mester-only` wrapper also contains `#bu-gu-tekst` (the BU:GU
  balance ratio, `app.js:1358`), a second advanced brewing metric bundled
  into the identical hidden block. Exposing this block to Learner mode is
  therefore not a small disclosure — it surfaces two distinct advanced/
  technical artifacts (percentage-scored style comparison, BU:GU ratio), not
  just descriptive style names. `#effektivitet` (finding #3's target,
  `web/index.html:189-191`) is a plain numeric brewhouse-efficiency percentage
  input — a standard advanced-homebrewing concept, consistent with everything
  else already gated `.mester-only` on that page. Exposing either has no
  layout-breaking effect (both already render correctly in Master mode today
  — this is a visibility question, not a fresh layout problem) but does have
  a **content-complexity** effect: Learner mode's whole design premise
  (progressive complexity) means whatever gets exposed here becomes
  permanently part of the "first thing a brand-new brewer sees," not an
  opt-in advanced view.

- **`_stilKortHtml`/`renderStilPanel`/`renderStilManuell` already cache-guard
  cheaply** — `renderStilPanel()` returns early if `!sisteStilAnalyse ||
  !sisteBeregning` (`app.js:1332-1333`), and both functions re-render purely
  from already-computed, module-level cached state (`sisteStilAnalyse`,
  `sisteBeregning`) — no recomputation of the underlying style match. Calling
  either again (e.g., from the mode-switch handler) is cheap and safe by
  construction, exactly the same guard pattern the language-switch listener
  already relies on.

## 2. Options A/B/C — pros/cons

**A. Learner-safe guidance** (suppress/rewrite the guidance clauses that
point at hidden content, keep the content itself hidden):
- Pros: preserves the existing, deliberate progressive-complexity design
  (advanced scoring/percentage/BU:GU content stays Master-only); smallest
  surface-area change (i18n text + a mode flag threaded through 3-4
  functions); no new layout/UX risk since nothing newly renders; symmetric
  and easy to keep NO/EN in sync (new keys follow the exact same key-pair
  pattern already used throughout `i18n.js`).
- Cons: requires new Learner-specific wording (a genuine content-writing
  task, not code-only, as the triage doc already noted); slightly increases
  branching inside `veiledning.js`'s otherwise flat string tables; the
  half-actionable OG tip (finding #3) needs the most surgical rewrite of the
  three (splitting a two-clause phrase, not just appending/omitting a
  trailing sentence).

**B. Expose the referenced content in Learner mode** (drop `.mester-only`
from "Nearby styles" and/or `#effektivitet`):
- Pros: zero new wording needed; resolves the contradiction by making the
  existing guidance text simply true again; no new mode-branching logic in
  `veiledning.js`/`app.js`.
- Cons: per the new evidence in §1, this is not a cosmetic disclosure — it
  permanently adds percentage-based style scoring, technical sensory
  gap-analysis bullets, and/or the BU:GU ratio and brewhouse-efficiency
  input to every first-time Learner's default view, contradicting the
  progressive-complexity premise Learner mode exists for (Roadmap V2.1
  product-role framing: Web's Learner mode is meant to reduce, not
  redistribute, initial complexity); would need its own, separate product
  sign-off on "should `.mester-only` cover less than it does today," which
  is a materially bigger and more consequential decision than fixing three
  contradictory sentences; does **not** by itself fix the stale-text gap in
  §1 (a user could still switch mode without triggering a re-render, though
  the consequence would be more benign once the content is Learner-visible
  either way).

**C. A deliberate mixed policy** (e.g., expose "Nearby styles" but keep
efficiency advanced and rewrite only that tip) — the triage doc's own
sketch:
- Pros: matches the triage's "higher-frequency, fully-blocking case gets B,
  half-actionable case gets A" framing.
- Cons: the new evidence in §1 undercuts the premise this sketch relied on —
  "Nearby styles" is not merely a lower-stakes disclosure than the efficiency
  field, it is *more* technical (percentage score + gap-analysis bullets +
  BU:GU ratio, three distinct advanced artifacts in one block) than a single
  numeric input field. A mixed policy here would expose the *more* technical
  content while keeping the *less* technical content hidden — backwards
  from what the "expose the lower-risk one" framing intended once the actual
  content is inspected, not just its label ("a list of styles" undersold what
  the block actually renders).

## 3. Recommended product contract

**Option A, applied uniformly to all three findings — not the mixed A/B
split the triage doc sketched.** Keep `.mester-only` exactly as-is (no
container/field newly exposed to Learner mode for either "Nearby styles" or
`#effektivitet`); make all three guidance clauses mode-aware so a
Learner-mode reader is never told to look at content that isn't on their
screen. This also requires closing the independent stale-text gap found in
§1: mode switches must re-render the affected guidance, not just future
guidance-generation calls.

## 4. Rationale tied to Kvernhaug Web/Learner goals

- Learner mode's whole reason to exist is progressive complexity — hiding
  percentage-based style scoring, sensory gap-analysis bullets, a BU:GU
  ratio, and a brewhouse-efficiency percentage from a brand-new brewer's
  default view is a deliberate, still-valid product choice, not incidental;
  nothing in this analysis found a reason that choice has gone stale.
- The actual defect is narrower and cheaper to fix correctly than "should
  Learner mode see more": three call sites generate text that assumes
  content is visible when it structurally isn't. Fixing the text to match
  reality (Option A) resolves the contradiction with no change to what
  Learner mode's complexity boundary actually is.
- Exposing either artifact (Option B/C) would be the kind of `.mester-only`
  scope change the triage doc itself flagged as needing to happen "once,
  deliberately" (§"Smallest bounded future fix", Option B paragraph) rather
  than as a side effect of fixing three sentences — B07 is scoped to fix the
  contradiction, not to relitigate what Learner mode hides.
- Discoverability is preserved, not reduced: a Learner-mode reader who wants
  the "Nearby styles"/efficiency detail can already reach it by switching to
  Master mode via the existing hamburger-menu control (`initModus()`) — the
  fix removes a broken promise, it does not remove a path to the content.

## 5. Exact implementation touchpoints

- `web/js/i18n.js` — split three existing keys into a Learner-safe base plus
  a Master-only suffix/variant (see §6 for exact text). New keys must follow
  the file's existing NO/EN key-pair structure so
  `tests/test_generate_web_i18n_pages.py`'s key-symmetry checks keep passing.
- `web/js/veiledning.js`:
  - `_feltNivaOgSetning(felt, avvik, stilNavn)` → add an explicit `erMester`
    (boolean) parameter; only the `og` branch's tip lookup needs to change
    (see §6 — `ibu`/`ebc`/`fg`/`abv` tips name no hidden target, per the
    triage doc's own "Checked and cleared" section, and are unaffected).
  - `_byggSamletOppsummering(feltAvvik, stilNavn)` → add the same explicit
    `erMester` parameter; append the "Nearby styles" clause only when true.
  - `byggStilVeiledning(stilEntry, stilNavn)` → add the same parameter and
    thread it to both functions above (its only two callees).
  - No function in this file reads `document` — the parameter must be
    computed by the caller (`app.js`) and passed in, preserving the file's
    DOM-independence convention.
- `web/js/app.js`:
  - `renderStilPanel()` (`app.js:1331-1380`) — compute
    `document.body.classList.contains("modus-mester")` once (matching the
    existing idiom at `app.js:1934`), pass it into `byggStilVeiledning()` at
    both call sites (`_renderVeiledning`, line 1355 via the auto path, and
    the `Kreativt Brygg` / `stilanalyse.ingenTreff` branch at lines
    1346-1349), and into the OG-tip lookup path.
  - `renderStilManuell()` (`app.js:1382-1400`) — same flag, same threading,
    for the manual-style path's call into `_renderVeiledning`/
    `byggStilVeiledning`.
  - `_renderVeiledning(container, stilEntry, stilNavn)` (`app.js:1314-1329`)
    — add the same explicit parameter and forward it to
    `byggStilVeiledning()`.
  - **Mode-switch re-render fix (§1, §7)** — `initModus()`'s `.modus-knapp`
    click listener (`app.js:374-379`) must call `renderStilPanel()` (which
    already internally calls `renderStilManuell()`, `app.js:1379`) after
    `settModus()`, guarded by nothing extra — `renderStilPanel()` already
    no-ops safely when no analysis exists yet (`app.js:1332-1333`).

## 6. Exact NO/EN text variants needed

**Finding #1 — `stilanalyse.ingenTreff`** splits into a Learner-safe base and
a Master-only suffix (`headlineInfo.textContent = t(base) + (erMester ?
t(suffix) : "")`):

| Key | NO | EN |
|---|---|---|
| `stilanalyse.ingenTreffBase` | "Ingen stil i biblioteket treffer godt nok ennå — juster ingrediensene." | "No style in the library matches closely enough yet — adjust the ingredients." |
| `stilanalyse.ingenTreffNaerliggende` | " Eller se nærliggende stiler under." | " Or see nearby styles below." |

**Finding #2 — `veiledning.samlet`** splits the same way inside
`_byggSamletOppsummering`:

| Key | NO | EN |
|---|---|---|
| `veiledning.samletBase` | "Oppskriften din er {adjektiver} enn typisk for {stil}." | "Your recipe is {adjektiver} than typical for {stil}." |
| `veiledning.samletNaerliggende` | " Se «Nærliggende stiler» under for et konkret alternativ som kan passe bedre." | " See «Nearby styles» below for a concrete alternative that might fit better." |

**Finding #3 — `_FELT_TIPS[spraak].og`** (`web/js/veiledning.js:32,39`)
changes shape from a flat string to an `{ alltid, mester }` pair — the only
field in `_FELT_TIPS` that needs this, since `ibu`/`ebc`/`fg`/`abv` name no
hidden target (confirmed by the triage doc's "Checked and cleared" section
and unchanged by this decision):

| | NO `alltid` (Learner + Master) | NO `mester` (Master only) |
|---|---|---|
| `og.under` | "mer malt" | "mer malt eller høyere brygghuseffektivitet" |
| `og.over` | "mindre malt" | "mindre malt eller lavere brygghuseffektivitet" |

| | EN `alltid` (Learner + Master) | EN `mester` (Master only) |
|---|---|---|
| `og.under` | "more malt" | "more malt or higher brewhouse efficiency" |
| `og.over` | "less malt" | "less malt or lower brewhouse efficiency" |

`_feltNivaOgSetning` selects `_FELT_TIPS[spraak].og[avvik.retning].mester`
when `erMester` is true, else `.alltid`; every other field keeps its current
flat-string lookup unchanged. The wrapping `veiledning.tips` key
(`" Tips: {tips} vil trekke oppskriften nærmere stilen."` /
`" Tip: {tips} will bring the recipe closer to the style."`) is unchanged —
only the `{tips}` value it interpolates varies by mode.

## 7. Mode-switch/rerender contract

- **Definition of correctness:** at every point in time, whatever guidance
  text is on screen must be consistent with the content currently reachable
  in the active mode — no sentence may reference content that is hidden at
  the moment it is read.
- **Mechanism:** guidance text is regenerated, not just newly *computed
  correctly*, on every event that can change either (a) the underlying
  style-match data or (b) the active mode. (a) is already covered —
  `beregnOgVisResultat()` → `renderStilPanel()` on every recipe change. (b)
  is the gap this decision closes: the `.modus-knapp` click listener must
  also call `renderStilPanel()` (§5), so a live Learner ↔ Master switch
  immediately regenerates the guidance text using the now-current mode, with
  no reload and no stale sentence persisting from before the switch.
  Language switching already satisfies this transitively today (confirmed in
  §1 — `_rerenderAlleEnhetsfelt()` ends with `beregnOgVisResultat()`) and
  needs no change.
- **No new state needed:** mode is read synchronously from
  `document.body.classList` at render time (the existing idiom,
  `app.js:1934`) — no caching, no separate "last known mode" variable to
  keep in sync.

## 8. Bounded acceptance matrix for future implementation

| # | Scenario | Expected result |
|---|---|---|
| 1 | Learner mode, recipe scores `Kreativt Brygg` (no style match) | Headline text omits "see nearby styles below"; reads as a complete, grammatical sentence ending after "adjust the ingredients." |
| 2 | Master mode, same recipe | Headline text is unchanged from current production wording (base + "see nearby styles below" suffix). |
| 3 | Learner mode, ≥2 of `{og, ebc, ibu, fg}` deviate from the matched/selected style | Summary sentence omits the "See «Nearby styles» below" clause; reads naturally without it. |
| 4 | Master mode, same conditions | Summary sentence is unchanged from current production wording. |
| 5 | Learner mode, OG deviates "tydelig"/clearly | Tip reads "more malt" only (no efficiency clause); the sentence remains grammatical as a single-option tip, not a dangling "or". |
| 6 | Master mode, same conditions | Tip is unchanged from current production wording ("more malt or higher brewhouse efficiency"). |
| 7 | Start in Master mode with an existing analysis showing "Nearby styles" guidance text, switch to Learner mode (no reload, no ingredient edit) | Guidance text immediately updates to the Learner-safe wording (scenarios 1/3/5) — no stale Master-mode clause remains visible. |
| 8 | Start in Learner mode with an existing analysis, switch to Master mode (no reload, no ingredient edit) | Guidance text immediately updates to the Master wording (scenarios 2/4/6) — the reader can now act on it, and the previously-hidden content it names is simultaneously visible. |
| 9 | Both NO and EN, every scenario above | Wording reads naturally in both languages, not just structurally key-symmetric (existing `tests/test_generate_web_i18n_pages.py` guards key symmetry only; wording needs a human bilingual read at implementation time, per the triage doc's own acceptance sketch). |
| 10 | `ibu`/`ebc`/`fg`/`abv` tips, either mode | Unchanged in both modes — none of these name a hidden target (confirmed, §1/triage doc), so none should gain new mode-branching. |

## 9. Regression/test/browser plan

- **Static/unit:** run `python3 -m unittest tests.test_generate_web_i18n_pages
  -b` after adding the new i18n keys — guards NO/EN key symmetry structurally
  (per `.claude/rules/testing.md`); does not, and cannot, verify wording
  quality or in-page conditional rendering (no existing `tests/` coverage
  targets `veiledning.js`'s generated text content, confirmed by the triage
  doc — this decision does not change that boundary).
- **Manual bilingual read:** both NO and EN wording for all six new/changed
  keys (§6), in context, before merge — same discipline as every prior
  content round.
- **Browser sweep (functional, not decided here, but required before the
  future implementation PR's checkpoint per `web-full-regression`):**
  exercise acceptance matrix rows 1-8 above live — in particular rows 7/8,
  the mode-switch re-render, since no static test can substitute for
  watching the DOM update on a real click — across the same
  viewport/browser matrix `web-full-regression` already covers, confirming
  0 console/page errors and no layout regression from the (harmless, but
  unverified until checked) extra `renderStilPanel()` call now firing on
  every mode-button click.
- **Screen-reader spot check (triage doc's own open item, still open here):**
  whether anything (e.g., an `aria-live` region) announces the guidance
  sentence changing when a mode switch now triggers a live re-render —
  previously moot (nothing re-rendered on mode switch at all), now relevant
  precisely because this decision introduces that re-render.

## 10. Explicit non-goals

- No `.mester-only` visibility change — "Nearby styles," `#bu-gu-tekst`,
  `#effektivitet`, and `#stil-manuell-resultat` all remain exactly as hidden
  in Learner mode as they are today.
- No change to `ibu`/`ebc`/`fg`/`abv` tip wording or logic — confirmed clean
  by both the triage doc and this decision.
- No change to the style-matching engine (`web/js/style.js`) or its scoring —
  this is a presentation-layer fix only, identical to the triage doc's own
  framing ("the numbers/ranking in style.js are UNCHANGED by this layer,"
  `veiledning.js:1-4`).
- No new static regression guard is committed by this decision (the triage
  doc's acceptance-case #6 sketch — a DOM-parsing test cross-referencing
  `.mester-only` containers against guidance text — remains a "considered,
  not built" idea; building it is a separate scope decision for whoever
  implements this, not assumed here).
- No handbook (`web/hjelp/**`) changes — out of scope, per the triage doc's
  own B08 boundary.
- App/Core/Bryggeskole, `#116`/`#98`/`#100`, W5, deploy, owner data, and
  `raw_data/unmatched_malt.json` — untouched, per issue #147's scope guard.

## 11. One implementation issue, not a split

**One bounded implementation issue.** The three findings share a single root
cause (mode-blind text generation) and the mode-switch re-render fix (§7) is
not separable from the text fix — landing the text change without the
re-render fix reintroduces staleness through the path documented in §1, and
landing the re-render fix without the text change makes the contradiction
*more* immediately visible (a mode switch would now promptly reveal the
stale sentence instead of leaving it to chance). The total diff is bounded
and localized to three files (`web/js/i18n.js`, `web/js/veiledning.js`,
`web/js/app.js`) plus the existing i18n-symmetry test — well within a single
round, consistent with how B06's own batches were still sized as
one-issue-per-batch despite touching multiple call sites.

---

*No `web/**` product file was edited to produce this decision. Analysis
only, per issue #147's own scope guard.*
