# Phase 3A — Learner/Master browser acceptance (issue #250)

*Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3 "Acceptance / Prove It". This is an ACCEPTANCE/PREP document, not a
feature-implementation record: it proves (or would disprove) that the
**current, already-shipped** Web Learner/Master ("Bryggelærling"/
"Bryggmester") contract satisfies Roadmap #101's Phase 3A criteria. No
`web/**` product file was changed to produce this evidence — the only new
files are this document and the new Playwright spec
[`tests/playwright/11-phase3a-learner-master-acceptance.spec.js`](../../tests/playwright/11-phase3a-learner-master-acceptance.spec.js).*

**Status: AUTOMATED 3A: PASS. Human novice gate: PENDING — requires a real
novice.** See §7/§8.

---

## 1. Baseline

| Item | Value |
|---|---|
| Issue | [#250](https://github.com/Joludvig/kvernhaug-brygghus/issues/250) |
| Roadmap | [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101) Phase 3A |
| Governance | [#199](https://github.com/Joludvig/kvernhaug-brygghus/issues/199) Production Workflow V2 |
| Branch | `acceptance/phase-3a-learner-master`, created from a fresh `git fetch origin` |
| `origin/master` at start | `18ac6f6c509b755d51522c474b5ba7f49a6a458a` (matches the SHA #250 recorded at creation) |
| Date | 2026-09-13 |
| Target environment (automated) | Local static file server (`http.server`) serving the checked-out `web/` tree, via the existing Playwright Critical Browser Gate config (`playwright.config.js`, issue #200) — **never production**, per that config's own stated intent |
| Target environment (production revision check only) | `https://kvernhaugbrygghus.no` (read-only content fetch, no state changed) |
| Browsers exercised | Chromium (`@playwright/test` bundled build) + Firefox (`@playwright/test` bundled build), via the 4 existing `projects` in `playwright.config.js` |

### 1.1 Production revision — three separate facts, not conflated

An earlier revision of this document conflated three genuinely different
concepts — current source SHA, Web source-tree equivalence, and actual
deployed/frozen production release — under a single "production ==
`origin/master`" conclusion. Corrected per Chief review (PR #251, review
5191289817). The three facts, kept separate:

**(a) Current source/master SHA:** `18ac6f6c509b755d51522c474b5ba7f49a6a458a`
(fresh `git fetch origin`, unchanged since this branch was created).

**(b) Last actually deployed + independently verified Web release SHA:**
no authoritative deployment log or version marker exists that names one.
What was found instead, by inspecting existing release-prep records:

- `docs/development/web_release_checklist_astra_audit_3.md` (commit
  `557ac08`, issue [#232](https://github.com/Joludvig/kvernhaug-brygghus/issues/232),
  "WEB RELEASE PREP — freeze `7aa076a` for Astra Audit #3") proposed
  freezing `RELEASE_SHA=7aa076a2210e4bf745f5c814db2ea924797b4227` and gave
  an owner-PC command sequence (`deploy_web.ps1 -ReleaseSha`) plus a
  4-item evidence checklist. That file only exists on the unmerged remote
  branch `origin/agent/issue-232` — it never landed on `master` — and its
  own evidence checklist is **unchecked as committed**.
- Issue #232 itself is **closed as "not planned"** on GitHub, with no
  comment recording that the `-ReleaseSha 7aa076a` deploy was actually run
  or verified. So the GitHub issue trail does **not** confirm `7aa076a`
  was the deployed SHA — it only shows it was prepared as a candidate.
- The retained release worktree `D:\Development\kbh-release-7aa076a`
  (pinned to `7aa076a`, clean, no extra files) is consistent with step 2a
  of that checklist having been carried out, but a worktree existing only
  proves *that step*, not that the real FTP deploy (step 2c) followed.

**Conclusion for (b): no document/issue trail authoritatively names a
deployed RELEASE_SHA.** Given `scripts/deploy_web.ps1` publishes no
discoverable release marker on the live site itself, the only way to
establish what is actually deployed *right now* is direct, independent,
read-only measurement — done next.

**(c) Does current master's `web/` tree differ from what's actually live?**
Answered empirically this session with a full canonical-file byte
verification, not the earlier four-file spot check alone:

- Enumerated every file under the working tree's `web/` directory (the
  exact set `deploy_web.ps1` uploads — `Get-ChildItem -Recurse -File`,
  no exclusions): **87 files**.
- Fetched each one's corresponding path directly from
  `https://kvernhaugbrygghus.no/<path>` over plain read-only HTTPS (no
  credentials, no FTP, no state changed) and byte-compared it against the
  local working tree.

  **Result: TOTAL 87 / IDENTICAL 85 / DIFFERING 0 / MISSING 2.**

  The 2 "missing" (HTTP 404) are `web/CHANGELOG.md` and `web/README.md` —
  repo-internal developer docs, not product/UI files; the production
  static-file server does not serve `.md` paths (nothing under the app's
  own navigation ever links to them). **Every one of the 85 files that are
  actually part of the served product is byte-identical.** Zero
  differences, zero unexplained missing files.
- `git diff 7aa076a..18ac6f6 -- web/` → **empty**. `git diff
  499a69f..18ac6f6 -- web/` → **empty**. `7aa076a` is confirmed an
  ancestor of `origin/master`. So current master's `web/` tree, `7aa076a`'s
  `web/` tree, and `499a69f`'s `web/` tree are all one and the same content.

**Conclusion: production is currently serving `web/` content byte-identical
to current master (`18ac6f6`)'s `web/` tree, proven directly (85/85
servable files, 0 differing) rather than inferred from git history alone.**
Because that same content is also identical to `7aa076a` and `499a69f`'s
`web/` tree, production is content-equivalent to the release-prep
candidate from issue #232 as well — **but this is established by today's
direct measurement, not by treating issue #232 as proof that `7aa076a` was
actually deployed.** Precise statement to use going forward: *"Current
repository master is `18ac6f6`. No authoritative log confirms which exact
SHA was last deployed by commit hash, but a fresh, full, read-only
production byte verification (85/85 servable files identical) confirms the
live site's content is, right now, identical to current master's `web/`
tree — and therefore also to `7aa076a`'s, since `web/` has had zero
commits between them."* This does not mean the App-only portions of master
were deployed (Web has no App/Core coupling) — only `web/` is claimed here.

A future Phase 3A-style check must repeat this content verification rather
than reuse this conclusion, since any subsequent `web/**` merge without a
new deploy would immediately invalidate it.

### 1.2 Source revision actually tested

The automated matrix below (§3) runs against the **local working tree at
`origin/master` (`18ac6f6`)**, served locally — i.e. exactly the content
verified in §1.1(c) to already be live in production. No `web/**` file was
modified for this acceptance pass.

---

## 2. Representative task

One recipe, built once per test run, in both Learner and Master, following
Roadmap #101's Phase 3A representative-task requirement and #250's 14-step
minimum flow:

| Recipe field | Value |
|---|---|
| Name | `KBH 3A Acceptance` (deterministic synthetic name, isolated per-test browser context/localStorage — never touches real user data) |
| Batch volume | 20 L (product default; explicitly re-set and verified, not merely accepted) |
| Malt | Pilsner Malt (Weyermann, `weyermann_pilsner`), 5 kg |
| Hop | Cascade (`cascade`), default 10 g / 60 min (alpha auto-filled 9.5 %) |
| Yeast | SafAle US-05 (Fermentis, `safale_us_05`) |
| Calculated outputs observed | OG, FG, ABV, IBU, EBC (all diverge from their zero-recipe defaults once the above is entered) |
| Save/preserve action | explicit "💾 Lagre oppskrift" click (not autosave-only) |
| Master-only advanced-control witness | hop-grams-from-target-IBU recalculation ("Mål-IBU" input + "Beregn mengde" button on the hop row) — a genuine calculation control, not a cosmetic one |
| Plan→brew continuation | "🪓 Start brygging" click, which freezes the recipe into a new local brew (`kvernhaug_web_brygg` in `localStorage`) — the flow stops there; no further brew-lifecycle step (measuring, tasting, learning) is exercised, per #250's "do not mutate more of the brew lifecycle than necessary" |
| Mode sequence | Learner → Master → Learner → Master (full four-hop cycle, not just one round trip) |

---

## 3. Automated matrix

Executed via `npx playwright test tests/playwright/11-phase3a-learner-master-acceptance.spec.js`, which — like every other spec in `tests/playwright/` — automatically runs against all 4 `projects` already defined in `playwright.config.js` (issue #200's own required matrix, reused rather than reinvented).

| Browser | Viewport | Language | Mode sequence | Result |
|---|---|---|---|---|
| Chromium | 1280×900 (desktop) | NO | L→M→L→M + full 14-step task | PASS |
| Chromium | 390×844 (mobile) | NO | L→M→L→M + full 14-step task | PASS |
| Firefox | 1280×900 (desktop) | NO | L→M→L→M + full 14-step task | PASS |
| Firefox | 390×844 (mobile) | NO | L→M→L→M + full 14-step task | PASS |
| Chromium | 1280×900 (desktop) | EN | L→M→L (trust-critical subset) | PASS |
| Chromium | 390×844 (mobile) | EN | L→M→L (trust-critical subset) | PASS |
| Firefox | 1280×900 (desktop) | EN | L→M→L (trust-critical subset) | PASS |
| Firefox | 390×844 (mobile) | EN | L→M→L (trust-critical subset) | PASS |

8/8 passed (`npx playwright test tests/playwright/11-phase3a-learner-master-acceptance.spec.js`, all 4 projects, 28.8s).

**Why EN gets a smaller sequence, not the full matrix again:** per #250's own
"do not create an unnecessary full Cartesian test explosion... a smaller but
equivalent proof [is acceptable]" — the EN test proves the trust-critical
subset (mode status text is real, correctly-localized copy; the auto
style-match guidance panel renders real, non-raw-key English text; one
L→M→L round trip preserves the recipe and the just-produced Master-only
value; no console/page errors) without repeating the full 14-step build a
second time in a second language, since the underlying mode/persistence
*mechanism* (`settModus()`, `localStorage`) is language-independent and
already fully proven by the NO run.

Full existing Playwright Critical Browser Gate (all 11 spec files, all 4
projects) also re-run in full to confirm zero regression from the new spec:
**172/172 passed**, 2.2 minutes.

---

## 4. Contract results

| Contract item | Result | Evidence |
|---|---|---|
| Same representative task, Learner and Master | PASS | Recipe built once; both modes exercised against the identical recipe state (§2, §5) |
| Learner guidance is instruction, not a toggle | PASS (bounded — see §6.1) | Auto style-match panel (`#stil-veiledning-auto`) renders non-empty, non-raw-key text tied to the live recipe once real malt/hop/yeast are present; verified in NO and EN |
| Master advanced controls | PASS | `.malt-pct`, `.humle-maal-ibu-rad`, `#skaler-rad`, `.stil-alternativer` (nearby styles), `#stil-manuell-resultat` all confirmed hidden in Learner / visible in Master; the target-IBU→grams control was actually exercised, not just shown |
| L→M persistence | PASS | Recipe/save-state snapshot (name, volume, malt qty+id, hop grams, yeast, OG, save badge) asserted byte-identical before/after |
| M→L persistence | PASS | Same snapshot fields, plus the Master-only-produced hop-gram value, survive the hop back to Learner |
| Second L→M persistence | PASS | Full four-hop L→M→L→M cycle completed; hop-gram value and recipe identity still correct on the fourth hop |
| Recipe save/draft orientation | PASS | Badge correctly cycles `Kladd — ikke lagret` → `Lagret` (on explicit save) → `Endret siden lagring` (once the Master-only control changes real recipe content post-save) — and stays `Endret siden lagring` through every subsequent mode hop, never silently reverting to "saved" or resetting to an unsaved draft |
| Plan→brew continuation | PASS | "Start brygging" produces exactly one `kvernhaug_web_brygg` entry whose frozen snapshot recipe name matches; no deeper brew-lifecycle action attempted |
| NO | PASS | Full 14-step flow, 4-project matrix |
| EN | PASS | Trust-critical subset, 4-project matrix (see rationale above) |
| Mobile layout | PASS | 390×844 (Chromium + Firefox): task completes; no horizontal overflow (`scrollWidth - clientWidth ≤ 1px` asserted at end of flow) |
| Console/runtime errors | PASS | Zero console/page errors collected (`collectErrors` helper) across all 8 executions |
| Accessibility spot-check | PASS | Recipe-name field, malt/hop/yeast comboboxes, save button, and start-brewing button all resolve by real accessible name (`getByRole`/`aria-label`), not merely by visual position |

---

## 5. What was proven about the mode-switch contract specifically

`web/js/app.js::settModus()` is documented in its own source comment as a
pure CSS-class toggle ("rører aldri oppskriftsdata, kun CSS-klasse på
body"). This acceptance pass adds, on top of the already-existing
`04-mode-preservation.spec.js` (one L→M→L round trip, one field, one
`.mester-only` element):

- a full **L→M→L→M** cycle (four hops, not two);
- an explicit **Master-only advanced-control witness** (hop-grams-from-
  target-IBU) whose *produced value* is proven to survive every hop, not
  just static pre-existing field values;
- **five** distinct `.mester-only` surfaces checked for visibility
  (malt %, hop target-IBU row, recipe scaling, nearby-styles list, manual
  style-match detail card), not one;
- the **save/draft-state badge** surviving the cycle correctly, including
  the "changed since saved" transition triggered by the Master-only edit;
- the **guidance panel** (`#stil-veiledning-auto`) re-rendering without
  going stale/blank across the four hops;
- the same properties re-checked in **English**.

---

## 6. Scoped limitations (honestly recorded, not hidden)

### 6.1 The per-field deviation-tips wording branch was not forced at runtime

`web/js/veiledning.js`'s `_feltTipsTekst()` has one branch whose *wording*
genuinely differs between modes — e.g. the OG tip says `"mer malt"` in
Learner but `"mer malt eller høyere brygghuseffektivitet"` in Master — but
it only fires when a field's deviation from the matched BJCP style is
`"tydelig"` (≥ the same 0.5-normalized threshold `style.js` calls
"critical"). The representative recipe in this acceptance pass was chosen
to be realistic (a plausible pilsner), not engineered against a specific
style's numeric range to force that branch — #250 explicitly says "do not
invent controls or data simply to make automation easier," and constructing
an artificial recipe purely to hit one wording branch would have been
exactly that.

This was instead **verified by source read** (quoted in the spec's own
header comment): the branch exists, is keyed on the same `erMester` flag
already proven live-re-rendered by this pass's mode-switch assertions, and
only ever adds Master-only vocabulary — it does not remove or shorten
Learner text. The defensive assertion actually run (`veiledningLearner`
must never contain "brygghuseffektivitet") is real coverage against a
regression that would leak that vocabulary into Learner mode's *default*
("all within range") text; it does not exercise the deviation-branch text
itself. **This is a real, bounded gap, not a hidden one** — recommended
follow-up: a future issue could add one additional synthetic recipe/style
pairing chosen specifically to force a "tydelig" deviation, purely to widen
this one assertion. Not required for Phase 3A PASS as scoped by #250's own
12 acceptance criteria (none of which name this specific branch).

### 6.2 No live production version marker

`scripts/deploy_web.ps1` has no mechanism to publish a discoverable
release marker on `https://kvernhaugbrygghus.no` itself, and no GitHub
issue trail authoritatively names the exact deployed RELEASE_SHA by commit
hash (§1.1(b) — issue #232's freeze-`7aa076a` prep was closed "not
planned", checklist unchecked). Determining "what's actually live"
required an ad hoc full-tree content verification this session (§1.1(c):
87 files enumerated, 85 servable ones fetched and byte-compared), not a
repeatable one-command check. This is a process/tooling observation, not a
Web *product* defect, and is recorded here rather than filed as a new
issue (no GitHub write access this session — see §9). Recommended bounded
follow-up for a future issue: a tiny static `web/version.json` (or an HTML
comment in `index.html`) written at deploy time from the release SHA,
verified post-upload exactly like every other deployed file already is —
this would also let issue-level release-prep records (like #232) actually
be closed with attached proof of completion instead of ambiguously
"not planned".

---

## 7. Findings

**No Web product defect was discovered in this acceptance pass.** Every
contract item in §4 passed against the currently deployed revision (§1.1).
The two items above (§6.1, §6.2) are recorded as scoped limitations /
process observations, not defects, and are not blockers to `AUTOMATED 3A:
PASS`.

---

## 8. Human novice gate — PENDING, script prepared (not executed)

Per #250 and Roadmap #101 item 5, **at least one real novice must use
Learner mode with no oral coaching before any "novice-ready" claim.** This
was NOT performed in this session (automation cannot substitute for it, and
#250 explicitly forbids claiming novice-ready without it). What follows was
the first prepared script and observation sheet for this gate.

**Superseded (issue #278):** the canonical, repeatable protocol for this gate
is now
[`docs/development/phase3a_novice_acceptance_protocol.md`](phase3a_novice_acceptance_protocol.md) —
it keeps this section's task statement (still accurate against current
source) but adds participant/environment criteria, explicit
PASS/CONDITIONAL PASS/FAIL rules, an evidence template, and folds in the
owner's own L→M→L→M/Master-control mechanical confirmation. Run that
document, not this section, for any future novice session.

### 8.1 Participant requirements

- Homebrewing familiarity: any level is fine, record it (low/medium/high).
- Familiarity with Kvernhaug Brygghus specifically: **must be none/minimal**
  — this is what makes the gate meaningful. Someone who has already seen
  the product is not a valid novice for this gate.

### 8.2 Task statement (read aloud or handed over verbatim — NO does not vary)

> "Lag en enkel øloppskrift med malt, humle og gjær. Forsøk å forstå hva
> systemet forteller deg underveis, lagre oppskriften, og gjør den klar til
> å brygges."
>
> (EN, if the participant is more comfortable in English: "Build a simple
> beer recipe with malt, hops, and yeast. Try to understand what the system
> tells you along the way, save the recipe, and get it ready to brew.")

### 8.3 Rules for the tester (owner or delegate)

- **Learner mode only** — do not switch the participant into Master, and
  do not explain that Master exists unless they discover it themselves.
- **No oral coaching.** Do not point at buttons, do not explain what a
  field means, do not correct a wrong click.
- The task statement may be **repeated verbatim** if asked, but not
  rephrased, expanded, or hinted.
- Record, but do not resolve, every question the participant asks aloud.
- Record hesitation, backtracking, and any control/word they visibly
  misunderstand (e.g. asks "what does OG mean" out loud, or hovers/clicks
  without acting).
- Record whether they understand the saved/draft state (do they notice the
  `Kladd — ikke lagret` / `Lagret` badge? do they click "Lagre oppskrift"
  unprompted, or need to be told the task isn't done without it?).
- Record whether they reach and use "🪓 Start brygging" unprompted.
- Record completion (they clicked Start brygging with a plausible recipe)
  or abandonment (they gave up, or declared themselves "done" without
  reaching it).

### 8.4 Observation sheet

| Field | Value |
|---|---|
| Date/time | |
| Participant homebrewing familiarity (low/medium/high) | |
| Participant familiarity with Kvernhaug Brygghus (must be none/minimal) | |
| Start time | |
| Finish time (or abandonment time) | |
| Completed (reached Start brygging with a real recipe): YES/NO | |
| Requested-help count (times they asked the tester anything) | |
| Major confusion points (which fields/words/controls) | |
| Trust/state confusion (did they understand saved vs. draft vs. changed?) | |
| Unexpected dead ends (got stuck, unclear how to proceed) | |
| Tester notes (free text) | |
| Result: PASS / FAIL / INCONCLUSIVE | |

**One useful novice session is enough for the initial novice-ready gate**
per #250 — this is not a survey/research program.

---

## 9. Shared HO delta (prepared, not applied)

`gh` CLI / GitHub write access was unavailable in this session (confirmed:
not on `PATH`, no `gh.exe` found on disk). No issue was created for §6.2 as
a result. **`HO UPDATED: NO` — missing GitHub write access.**

Pending HO delta for the owner/Chief to apply once write access exists:

> Phase 2 (App Brewday Stabilization V1) is complete; A4-1
> (batch/brewer metadata) remains DEFERRED/NO CURRENT REQUIREMENT — current
> App exposes no start-brew batch/brewer fields to preserve, so there is
> nothing to carry across a mode/session boundary yet. Phase 3A automated
> acceptance for Learner/Master (issue #250) is **PASS** against the
> currently-live Web content (verified via a full read-only production
> byte check, 85/85 servable files identical — not assumed from
> `origin/master` or from an unconfirmed release-prep issue) — see
> `docs/development/phase3a_learner_master_acceptance.md`. The human novice
> gate required before any "novice-ready" claim is **PENDING** (script
> prepared, not yet run with a real participant). No new product defect was
> found; two bounded scope notes were recorded (deviation-tips wording
> branch untested at runtime; no live production version marker) as
> candidate small follow-up issues, not filed (no GitHub write access this
> session). Phase 3B and 3C remain not started and are not authorized by
> this issue.

---

## 10. Overall

**`AUTOMATED 3A: PASS`** — every one of #250's 12 acceptance criteria that
automation can prove was proven, against content independently verified —
via a full 85-file read-only production byte check, not an assumption —
to already be live in production, with zero new Web product defects found
and
zero regressions in the existing 172-test Critical Browser Gate or the
230+54 relevant Python Web/i18n unit tests. The two recorded scope notes
(§6) are bounded and do not block this result.

**Roadmap #101 Phase 3A itself is NOT being declared complete** — the human
novice gate (§8) is real, required, and still `PENDING`. This document's
PASS covers exactly what #250 asked automation to prove; it is not a
substitute for the novice session.
