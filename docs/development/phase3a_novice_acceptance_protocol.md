# Phase 3A — Novice Learner/Master acceptance protocol (issue #278)

*Part of Roadmap V2.1 [#101](https://github.com/Joludvig/kvernhaug-brygghus/issues/101)
Phase 3 "Acceptance / Prove It", item 3A. This is a PREP/docs document only —
no `web/**` product file is touched to produce it. It defines the smallest
practical, repeatable protocol the **owner** runs, by hand, to decide whether
the Web Learner experience can be called novice-ready. It does not perform or
fake that human gate itself.*

## 0. Source audit and relationship to prior evidence

Grounded against current `master` at the time of writing (source read, not
assumed): `web/js/app.js` (`settModus()`, `initModus()`,
`_lukkModusForstegang()`), `web/index.html` (mode dialog `#modus-forstegang`,
hamburger-menu toggle `.sidemeny-modus-knapp`, save button `#lagre-knapp` and
status line `#lagre-status`, `#start-brygging-knapp`, the `.mester-only`
elements, the Learner guidance panel `#stil-veiledning-auto`), and the
existing Playwright coverage in `tests/playwright/02-mode-dialog.spec.js`,
`04-mode-preservation.spec.js` and `11-phase3a-learner-master-acceptance.spec.js`.

[`docs/development/phase3a_learner_master_acceptance.md`](phase3a_learner_master_acceptance.md)
(issue #250) already delivered **`AUTOMATED 3A: PASS`** for every part of
Phase 3A that automation can prove — the same-recipe Learner/Master task, a
full L→M→L→M persistence cycle, a genuine Master-only advanced-control
witness (hop grams from target IBU), NO+EN, desktop+mobile, zero console
errors — against content independently verified to be byte-identical to what
is live in production. That document's own §8 drafted a first script for the
one thing automation explicitly cannot prove: a real novice using Learner
mode with no oral coaching. **This document supersedes that draft (§8) as the
canonical, repeatable protocol** — it keeps its core task statement (still
accurate against current source) but restructures it to satisfy issue #278's
full 12-point specification, adds explicit decision rules, an evidence
template, and folds the owner's mechanical L→M→L→M/Master-control
confirmation into the same one sitting so the whole gate is a single
20–30 minute session rather than two separate efforts.

**Non-duplication**: this protocol deliberately does not ask the tester to
re-verify anything the Critical Browser Gate already proves mechanically
(exact field byte-preservation across mode hops, `.mester-only` CSS
visibility, zero console errors) — that is CI's job, re-run on every PR. The
human protocol instead targets what only a person can judge: whether a
first-time user *discovers* the right thing unaided, and whether the
mechanical behavior *feels* trustworthy when watched, not just when
asserted in code.

## 1. What this protocol is, and is not

- This is a **discoverability and trust judgment gate**, run by/with one real
  person, not a test script. It targets Roadmap #101 Phase 3A's own explicit
  requirement: "at least one real novice using Learner without oral coaching
  before claiming novice-ready."
- **Automated tests cannot satisfy this gate, by construction.** A Playwright
  script always knows the correct selector, the correct order of steps, and
  never experiences genuine confusion — it can prove the product *behaves*
  correctly, never that a first-time human *understands* it unaided. No
  amount of additional browser-gate coverage substitutes for this session.
- This protocol is **not** a usability research program. One useful session
  is enough to clear the initial novice-ready gate (matching issue #250's own
  scoping) — it is not a survey, not A/B testing, and not a market study.
- This protocol is **not** authorization to change Web product behavior. It
  only decides whether the *current, already-shipped* product clears the
  gate, and if not, routes the gap to the right kind of follow-up (§9).

## 2. Participant criteria

- **Familiarity with Kvernhaug Brygghus specifically: must be none or
  minimal.** Anyone who has already used the product, watched a demo of it,
  or been walked through it does not qualify — this is what makes the gate
  meaningful.
- **Homebrewing familiarity: any level is acceptable.** Record it
  (none/low/medium/high) as context, not as a pass/fail filter — the product
  is meant to work for a beginner brewer, not only an experienced one, but
  Phase 3A does not require testing every experience tier separately.
- One participant is sufficient for this round (Roadmap #101 does not ask
  for a panel). If the owner wants stronger evidence later, that is a
  separate, explicitly scoped follow-up round — not a requirement here.

## 3. Environment and device assumptions

- **Required**: one desktop or laptop browser session (any of Chrome,
  Firefox, Edge, Safari), Norwegian UI, on the live product
  (`https://kvernhaugbrygghus.no`) or an equivalent up-to-date local build —
  whichever the owner can hand the participant with the least friction.
  Desktop is required because it is the lowest-friction environment to
  observe someone in real time; it is not a claim that mobile doesn't matter.
- **Optional, not required for this round**: a mobile/touch device repeat.
  The existing automated matrix already exercises 390×844 mechanically
  (layout, overflow, console errors) in both browsers — see
  `phase3a_learner_master_acceptance.md` §3/§4 — so a human mobile repeat is
  a valuable but separate follow-up, not a blocker to a first novice-ready
  verdict on desktop.
- **English UI**: not required for this session at all — see §7.
- The tester (owner or delegate) needs a way to observe the participant's
  screen and actions in real time (in person or screen-share) and to take
  notes without interrupting. No recording/analytics tooling is required or
  introduced by this protocol.

## 4. Before you start: permitted framing vs. prohibited coaching

**The tester may say, once, before starting:**

> "I'd like you to try building a beer recipe in this tool. I'll read you one
> instruction, and then I'm just going to watch — I won't be able to help or
> explain anything while you work, but I can repeat the instruction if you
> forget it. There's no wrong way to do this; I'm testing the tool, not you."

That framing sentence, and the task statement itself (§5.1), may be repeated
verbatim on request. **Nothing else may be added or hinted, at any point
during the task**, specifically:

- No pointing at, naming, or describing the purpose of any button, field, or
  label.
- No correcting a wrong click, a skipped field, or a misunderstood word.
- No confirming or denying whether the participant is "doing it right."
- No mentioning that a Master/advanced mode exists, unless the participant
  discovers and asks about it themselves — in which case the tester may
  answer factually ("yes, there's an advanced mode, but let's stick to this
  one for now") without demonstrating it.
- No reading result numbers (OG/IBU/EBC/ABV) aloud or interpreting them for
  the participant.

If the participant becomes fully stuck (not merely hesitant) for more than
roughly two minutes with no progress, the tester may repeat the task
statement verbatim once more, then let the session continue or end it as an
abandonment (§8/§9) — never supply the missing action itself.

## 5. Part A — the novice task (Learner mode only)

### 5.1 Exact task statement

Read aloud or handed over verbatim (Norwegian is the default and sufficient
language for this gate — see §7):

> "Lag en enkel øloppskrift med malt, humle og gjær. Forsøk å forstå hva
> systemet forteller deg underveis, lagre oppskriften, og gjør den klar til
> å brygges."

The participant starts from the **blank/opening state** of the recipe
builder (`web/index.html`) — a fresh browser profile or cleared
`localStorage`, so the first-visit mode dialog (`#modus-forstegang`) actually
appears. The task is complete once the participant reaches a **meaningful
saved/brew-ready result**: a recipe with malt, hop and yeast entered, saved
explicitly, with "🪓 Start brygging" clicked — mirroring the exact
representative task already used for the automated pass (§2 of
`phase3a_learner_master_acceptance.md`), so the human and automated evidence
describe the same product surface.

### 5.2 Rule for this part

- **Learner mode only.** If the first-visit dialog appears, the participant
  chooses for themselves — the tester does not steer the choice, but if they
  pick "⚙️ Bryggmester" (Master) by themselves, let it stand and record it as
  a finding (§8/§9) rather than intervening; do not restart them into
  Learner. If they pick "🎓 Bryggelærling" (Learner), continue as normal.
- No oral coaching, per §4.

### 5.3 Learner-mode checkpoints that must be discoverable without help

Record each of these as observed / not observed / observed with difficulty:

1. **Mode choice itself** — participant makes *some* deliberate choice at
   the first-visit dialog, not a confused dismiss/Escape.
2. **Ingredient entry** — finds and uses the malt, hop, and yeast
   selection/search controls without asking "how do I add X."
3. **Learner guidance is noticed** — the auto style-match guidance panel
   (`#stil-veiledning-auto`) renders live text once real ingredients are
   entered; record whether the participant visibly reads/reacts to it (a
   pause, a comment, a re-read) versus never looking at it at all.
4. **Save/draft state is understood** — the participant notices the
   `#lagre-status` line changes and, unprompted, clicks "💾 Lagre oppskrift"
   before considering the task done, rather than assuming the recipe is
   already saved.
5. **Brew-ready action is found** — the participant locates and clicks
   "🪓 Start brygging" unprompted, understanding it as "make this ready to
   brew" from its own label/icon, not because the tester pointed at it.

## 6. Part B — owner mechanical follow-through (same sitting, right after)

Immediately after Part A ends (success or abandonment), the **tester**
(not the novice) performs a short mechanical confirmation using the
participant's own saved recipe if one exists, or a fresh equivalent recipe
of the tester's own if the participant did not reach a saved state. This is
a **sanity confirmation tied to real, just-produced state**, not a re-proof
of what CI already covers exhaustively (§0) — keep it brief.

### 6.1 L→M→L→M persistence check

- From the current mode, open the hamburger menu and switch mode
  (`.sidemeny-modus-knapp[data-modus="mester"]` / `="laerling"`) four times
  in sequence (L→M→L→M or M→L→M→L, matching wherever the session currently
  is), confirming after each hop that the recipe name, ingredient values,
  and the `#lagre-status` line are unchanged from before that hop.
- Record: PASS if all four hops preserve state with no visible flash of
  wrong/blank data; otherwise record exactly what changed and at which hop.

### 6.2 At least one Master-only advanced-control check

- In Master mode, exercise one genuine advanced control — the hop
  target-IBU → grams recalculation (the "Mål-IBU" input and "Beregn mengde"
  button on a hop row, inside `.humle-maal-ibu-rad.mester-only`) is the
  recommended one, matching the control already exercised in the automated
  pass.
- Confirm the produced value is visible, plausible, and (per §6.1) survives
  a further mode hop back to Learner and Master again.
- Record: PASS if the control works and its result persists; otherwise
  record what happened.

## 7. NO/EN handling

Per Roadmap #101 and issue #278: **do not require two separate novice
participants** for this gate. Norwegian is the default and sufficient
language for the one required novice session, because:

- The task statement, guidance panel, and save/brew controls are the same
  underlying mechanism in both languages (`web/js/i18n.js` supplies the
  strings; `settModus()`/`localStorage` logic is language-independent).
- The automated pass already exercises an equivalent English trust-critical
  subset (mode status text, guidance panel non-raw-key rendering, one L→M→L
  round trip) across all four browser/viewport combinations — see
  `phase3a_learner_master_acceptance.md` §3.

If the owner later wants an English-speaking novice session as additional
evidence (e.g. because a real English-speaking user is available), it is a
welcome supplementary data point using this same protocol's §5 task
statement (EN variant below) — but it is not required to declare this gate
passed.

> EN task statement (only if used): "Build a simple beer recipe with malt,
> hops, and yeast. Try to understand what the system tells you along the
> way, save the recipe, and get it ready to brew."

## 8. Evidence capture template

| Field | Value |
|---|---|
| Date | |
| Tester (owner or delegate) | |
| Participant homebrewing familiarity (none/low/medium/high) | |
| Participant familiarity with Kvernhaug Brygghus (must be none/minimal) | |
| Language used | NO (default) / EN |
| Device/browser | |
| Start time | |
| End time (or abandonment time) | |
| Mode chosen at first-visit dialog | Learner / Master / unclear-dismiss |
| §5.3.1 mode choice | observed / not observed / observed with difficulty |
| §5.3.2 ingredient entry | observed / not observed / observed with difficulty |
| §5.3.3 guidance panel noticed | observed / not observed / observed with difficulty |
| §5.3.4 save/draft state understood | observed / not observed / observed with difficulty |
| §5.3.5 brew-ready action found | observed / not observed / observed with difficulty |
| Task completed (reached Start brygging with a real recipe) | YES / NO |
| Times participant asked the tester anything | |
| Major confusion points (fields/words/controls, verbatim if possible) | |
| Unexpected dead ends | |
| §6.1 L→M→L→M persistence (owner check) | PASS / FAIL + detail |
| §6.2 Master-only control check (owner check) | PASS / FAIL + detail |
| Screenshots/notes (optional) | |
| Tester free-text notes | |
| **Result** | **PASS / CONDITIONAL PASS / FAIL** |

## 9. Decision rules

- **PASS** — the participant completed the task (reached "Start brygging"
  with a plausible recipe) without oral coaching, all five Learner
  checkpoints (§5.3) were at least "observed" (difficulty is acceptable, a
  fully missed checkpoint is not), and both owner mechanical checks (§6)
  passed. Roadmap #101 Phase 3A's novice requirement is cleared.
- **CONDITIONAL PASS** — the participant completed the task without
  coaching and both §6 checks passed, but one Learner checkpoint (§5.3) was
  missed or required the one-time task-statement repeat under real
  difficulty (not just a quick self-correction). Novice-ready may be claimed
  for the core loop, with the specific missed checkpoint filed as a
  follow-up (§10) — do not claim "novice-ready" without naming the gap in
  the same report.
- **FAIL** — the participant abandoned the task, could not save or reach
  "Start brygging" without the tester breaking the no-coaching rule, two or
  more Learner checkpoints were missed, or either §6 mechanical check
  failed. Do not claim novice-ready. File the specific failure(s) as
  follow-up (§10) before attempting another session.
- A session invalidated by a participant who turns out not to meet §2
  (already familiar with the product) or by a tester who breaks the
  no-coaching rule (§4) is **inconclusive**, not a FAIL — repeat with a
  fresh, qualifying participant/tester instead of counting it against the
  product.

## 10. Follow-up routing

Route every recorded gap from §8/§9 into exactly one bucket, so it reaches
the right kind of fix rather than becoming a vague "novice test found
issues" note:

- **UX bug** — the control exists and is positioned/labeled as intended by
  the current design, but behaves incorrectly (wrong value, broken
  persistence, layout failure, console error). File as a normal bounded
  issue against the relevant Web area; this is implementation work.
- **Content/guidance gap** — the mechanism works correctly, but the
  participant did not understand *what to do* or *what a result meant*
  (e.g. did not read/trust the guidance panel, did not understand a label's
  wording, did not know the save badge meant unsaved work). File as a
  content/copy/guidance issue (candidate for Roadmap #101's own "B07
  Learner guidance" line or a similar wording-only fix) — this is text and
  placement work, not calculation logic.
- **Non-blocking preference** — the participant expressed a stylistic
  opinion or minor friction that did not prevent task completion or cause
  genuine confusion (e.g. "I would have expected this button to be a
  different color"). Record it in the evidence template for future
  reference; do not file it as an issue on its own, and do not let it block
  a PASS/CONDITIONAL PASS verdict.

When in doubt between UX bug and content/guidance gap, prefer content/
guidance gap unless the observed behavior actually diverges from what the
code is supposed to do — most Learner-mode confusion in a mature product is
a wording/discoverability question, not a broken control, and misrouting it
as a "bug" invites an unnecessary code change instead of a copy fix.

## 11. Timing budget

The full session (§4 framing, §5 novice task, §6 owner follow-through, §8
write-up) is designed to fit in roughly 20–30 minutes: the task itself
(§5) typically takes a first-time user 10–15 minutes; the owner's mechanical
follow-through (§6) takes under 5 minutes since it reuses the just-created
recipe; recording the evidence template (§8) takes the remainder. If a
session is running dramatically longer than this without reaching a natural
stopping point, treat it as heading toward FAIL/abandonment (§9) rather than
extending scope into a larger usability study.
