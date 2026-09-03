# Kvernhaug Agent Bridge V1

*Part of the Kvernhaug repo infrastructure. Governs the mechanics of
how Claude gets triggered from GitHub state — it does **not** govern
architecture/product decisions, which remain owned by the locked
charters/contracts (`KBH_CORE_CONTRACT.md` and friends) and by the
owner directly. See [../../CLAUDE.md](../../CLAUDE.md) for the wider
document system.*

## Goal

GitHub is the event/state bridge between Kvernhaug Chief (ChatGPT) and
Claude Code — the audit trail and handoff bus. This document defines
the label-driven state machine that lets an explicitly authorized
GitHub label change trigger a bounded Claude Code run, without the
owner having to paste a manual instruction each time, while keeping
merge to `master` an explicit, always-manual owner decision.

This is repository/agent infrastructure only. It does not change
App/Web/Core product behavior, and it does not grant Claude (or
anything else) permission to merge to `master` automatically.

## State machine

```
status:ready ──────────────┐
                            │
status:changes-requested ──┤──► status:working ──► status:review ──► status:approved ──► OWNER GO/NO-GO ──► merge
                            │         ▲                  │
                            │         └── (Chief review: CHANGES REQUESTED) ──┘
                            │
                       (owner re-applies status:changes-requested after reading a review)
```

Labels live on the **issue** that specifies the task — not on the PR
Claude opens against it (design decision, see below). The associated
PR is a normal PR: the Chief reviews it exactly as in every prior
round of this project (a PR review, `gh pr view --json reviews`,
etc.) — the label on the issue is only the *routing/state* signal for
the automation, not a substitute for reading the PR itself.

| Label | Who applies it | Meaning |
|---|---|---|
| `status:ready` | Owner | Issue is a bounded, authorized task; start a fresh Claude run. |
| `status:working` | Workflow (automatic) | A Claude run is currently executing for this issue. |
| `status:review` | Workflow (automatic, only on success **and** a passed deliverable check, V1.2) | Claude's run finished, and a real PR with a non-empty diff was independently verified to exist; ready for Chief review. |
| `status:changes-requested` | Owner, or the owner-authorized Chief Work task (V1, issue #31) acting through the connected owner GitHub identity, after reading a Chief review | Trigger Claude again to address *only* that review's CHANGES REQUESTED points. |
| `status:approved` | Owner, or the owner-authorized Chief Work task (V1, issue #31) acting through the connected owner GitHub identity, after a Chief PASS | Signals the PR is approved. **Never auto-merged** — merge is always a separate, manual owner action. |
| `agent:claude` | Owner | Routing label: marks an issue as one Claude should react to at all. Required on **every** trigger, alongside a status label. |
| `area:core` / `area:web` / `area:app` / `area:infra` | Owner (optional) | Informational scoping only — not read by the workflow. |

### Lifecycle labels are exclusive; routing/area labels are additive

The five `status:*` labels describe **one** state, so an issue must
never carry two of them at once. Every transition therefore *replaces*
the lifecycle label rather than adding to it:

- **The workflow** computes the complete new label set via
  [`.github/scripts/lifecycle_labels.py`](../../.github/scripts/lifecycle_labels.py)
  — every `status:*` label is dropped, exactly one is added, and
  `agent:claude`/`area:*`/anything else is preserved untouched — and
  `PUT`s that whole set. So a run always leaves exactly
  `status:working` while executing, and exactly `status:review` on
  success, even if the issue arrived carrying stale/multiple status
  labels.
- **The owner** — or, as of the Chief Work task (V1, issue #31), the
  owner-authorized Chief Work task acting through the connected owner
  GitHub identity — must follow the same rule manually for the two
  owner-driven transitions: applying `status:changes-requested` should
  *replace* `status:review`, and applying `status:approved` after a
  Chief PASS should *replace* `status:review` — not simply be added
  alongside it. (The workflow normalizes whatever it finds at the start
  of its next run, but between runs the labels are only as clean as
  whichever of the two leaves them.) This does not weaken the owner
  gate: the Work task acts through the owner's own connected GitHub
  identity, not a separate bot account, and the formal PR review itself
  must still be performed by an identity other than the PR's author —
  normal Bridge PRs are authored by `claude[bot]`, so a Chief review
  from the owner identity satisfies that independently.

Regression coverage: `tests/test_agent_bridge_labels.py` runs the full
`ready → working → review → changes-requested → working → review →
approved` loop through the transition function and asserts there is
exactly one lifecycle label after every single step, with
`agent:claude`/`area:*` surviving each one.

### Design decision: state lives on the issue

The issue text describing this state machine consistently frames it in
terms of "a bounded issue" moving through states, and every round of
this project so far (PRI 1/PRI 2/PRI 2C2/PRI 2C3) was driven by an
issue whose body was the task specification, with a PR created against
it. V1 keeps the *state* label on that same issue for the whole
lifecycle (including the review/changes-requested loop), rather than
splitting it across the issue and the PR. This keeps the trigger
surface to a single GitHub event type (`issues: labeled`) and avoids
the `pull_request`-event auth wrinkles noted below. If this proves too
coarse in practice (e.g. an issue spawning multiple PRs), that is a
V2 scope-change discussion, not a silent deviation.

## Trigger rules

Implemented in
[`.github/workflows/claude-agent-bridge.yml`](../../.github/workflows/claude-agent-bridge.yml).
The workflow fires on `issues: labeled` (plus a manual `workflow_dispatch`
for testing, see below) and only actually starts work when **all** of
the following hold:

1. The label just applied is exactly `status:ready` or
   `status:changes-requested` (not any other label — including
   unrelated additions/removals, which do not fire `labeled` for a
   different label at all).
2. **`agent:claude` was already present in the labels carried by that
   triggering event** (`github.event.issue.labels` — the event-time
   snapshot). See "Authorization is atomic with the trigger event"
   below.
3. The issue **still** carries `agent:claude` *and* that same trigger
   label when the guard actually executes (re-checked live via
   `gh issue view`).
4. The label was applied by the repository owner
   (`github.event.sender.login == github.repository_owner`), not a
   bot or any other actor.

If any of these fail, the workflow's `guard` job exits cleanly with no
side effects (no label changes, no Claude invocation, no comment).

The decision itself lives in
[`.github/scripts/trigger_guard.py`](../../.github/scripts/trigger_guard.py)
as one pure function, so every rule above is unit-tested without
touching GitHub (`tests/test_agent_bridge_trigger_guard.py`).

### Authorization is atomic with the trigger event (V1.1, issue #9)

**The bug this fixes (found on the first real bridge test, issue #8):**
V1 checked only the *live* labels at the moment the guard happened to
run. The owner applied `status:ready` a few seconds *before*
`agent:claude`; by the time the runner started, both labels existed, so
the guard accepted a `status:ready` event that had **not** been
authorized when it fired. (Execution then stopped safely at the
missing-credential preflight — no Claude work ran — but the
authorization itself was wrong.)

**The rule now:** a trigger event is authorized only if `agent:claude`
was present *in that event's own label snapshot*, **and** the live
state still holds. Adding `agent:claude` afterwards never retroactively
authorizes an older `status:*` event — that event stays permanently
unauthorized, and the owner must re-apply the status label to arm a
fresh, properly-ordered event.

**Safe arming order — always:**

1. Add (or keep) `agent:claude` on the issue.
2. *Only then* apply/replace the lifecycle state with `status:ready` or
   `status:changes-requested`.

The live re-check from V1 is unchanged and still runs alongside this —
it catches the *other* class of problem (an event that has since been
superseded or disarmed). `workflow_dispatch` keeps its V1 semantics: it
is already gated by GitHub to users with repo write access, so the
event-snapshot requirement does not apply to manual runs — only the
live state must be valid.

## Claude's allowed tools (V1.2, issue #12)

**The bug this fixes (found on the first real E2E bridge run, issue
#11):** workflow run `33646938966` finished `conclusion: success` —
guard OK, secret OK, OIDC OK, Claude GitHub App token OK, Claude Code
2.1.258 ran and returned `subtype: success` — but the repo afterward
showed **no new branch, no open PR, no issue/PR comment**, and the
requested deliverable file was never written. The same run recorded
`permission_denials_count: 14`. The root cause: the "Run Claude Code"
step passed **no `--allowedTools` at all**. Anthropic's own docs are
explicit on both halves of why that is fatal here:

- *"Run Arbitrary Bash Commands: By default, Claude cannot execute Bash
  commands unless explicitly allowed using the `allowed_tools`
  configuration."* (capabilities-and-limitations.md) — so every `git`/
  `gh` command the prompt asked for was denied.
- *"Claude does not automatically create pull requests… it commits
  code changes to a new branch and provides a link to the GitHub PR
  creation page in its response."* (security.md) — so even a
  successful Claude turn, on its own, was never going to produce an
  **open** PR; that always requires an explicit `gh pr create` call,
  which itself requires Bash access.

V1 then treated `conclusion: success` from the Claude action as "the
task is done" and moved the issue straight to `status:review`. That is
wrong for this state machine: a green process is a **necessary, never
sufficient**, condition. See "Deliverable verification gate" below for
the other half of this fix.

**The allowlist itself** (`claude_args: --allowedTools "..."` on the
"Run Claude Code" step) is the minimum explicit git/gh/test command set
this bounded workflow's two run types (`status:ready` fresh
implementation, `status:changes-requested` follow-up) actually need,
each scoped as tightly as the official permission-rule syntax allows
(`Bash(cmd *)` prefix rules where arguments genuinely vary per run;
exact, argument-free/argument-fixed rules where they don't):

| Rule | Why |
|---|---|
| `Bash(git fetch *)` | Start from current `origin/master`. |
| `Bash(git checkout *)` | Create/switch to the task's feature branch. |
| `Bash(git branch *)` | Inspect/name branches. |
| `Bash(git status *)` | Sanity-check working tree state (also matches bare `git status`). |
| `Bash(git diff *)` | Review its own changes before committing. |
| `Bash(git add *)` | Stage files. |
| `Bash(git commit *)` | Commit staged changes. |
| `Bash(git push -u origin <branch>)` / `Bash(git push origin <branch>)` | Push the feature branch — **exact match, no wildcard**, `<branch>` filled in per-run from the "Compute deterministic bridge branch name" step. See "Branch naming is deterministic and enforced" below. |
| `Bash(git log *)` | Inspect history/context. |
| `Bash(gh issue view *)` | Read the task issue. |
| `Bash(gh issue comment *)` | Post the required `SCOPE CHANGE` / "cannot identify PR" / final-outcome comments. |
| `Bash(gh pr create *)` | Actually open the PR — the step this bug was named for. |
| `Bash(gh pr view *)` | Read an existing PR (state, latest Chief review) for `changes-requested`. |
| `Bash(gh pr edit *)` | Update the PR description/report. |
| `Bash(gh pr comment *)` | Post the PR-side report. |
| `Bash(gh pr list *)` | Look up the PR associated with this run's fixed branch. |
| `Bash(pip install -r requirements.txt)` | Install project dependencies before running tests — **exact match, no wildcard**: this and only this invocation, deliberately not `pip install <anything>`. |
| `Bash(python3 -m unittest *)` | Run the project's test suite (full `discover -s tests -b` or a focused module). |

**Deliberately NOT granted**, as a defense-in-depth backstop to the
"never merge" rule the prompt also states in plain language:
`git merge`, `gh pr merge`, any `git push` outside the two exact
commands above (in particular: no wildcard on the destination, so no
refspec trick like `<branch>:master` can match either rule — see
"Branch naming is deterministic and enforced" below), and any unscoped
`gh api`/`git *`/arbitrary shell (no bare `Bash` or `Bash(*)` rule
exists here).

## Permission model: Bash allowlist + acceptEdits (V1.3, issue #15)

**The bug this fixes:** the first live E2E run (issue #14) got past the
V1.2 Bash allowlist cleanly — guard, auth, and branch creation all
worked — and then failed closed one step later: Claude reported `Write`
denied both inside the repo and in `/tmp`, so no file could be created
or edited at all. Root cause: `--allowedTools` never listed `Write`/
`Edit`, and this action's headless SDK has no interactive prompt
handler, so any permission request that falls through to `ask` is
denied by default with nothing to grant it.

**The fix:** `claude_args` on the "Run Claude Code" step now also
carries `--permission-mode acceptEdits`, verified against the official
tag-mode implementation at the exact `anthropics/claude-code-action@v1`
revision the failed run used
(`8251c103ac8c1d761882c86aba1412c7f583c844`) — which deliberately does
the same thing, and states explicitly *why*: `acceptEdits` allows file
edits inside `$GITHUB_WORKSPACE` (the checked-out repo) and denies
writes anywhere else on the runner, while listing `Write`/`Edit`
directly in `--allowedTools` would grant blanket write access to the
whole runner instead of scoping it to the workspace.

**The complete permission model, stated plainly:**

| Concern | Mechanism | Result |
|---|---|---|
| File edits inside `$GITHUB_WORKSPACE` | `--permission-mode acceptEdits` | Allowed |
| Writes anywhere else on the runner | `--permission-mode acceptEdits` (its denial side) | Denied |
| Bash commands | The explicit `--allowedTools` list above | Only the listed exact/prefix commands; everything else denied |
| Direct push to `master` | No wildcard destination in either push rule (V1.2) | Denied |
| `git merge` / `gh pr merge` | Not present in `--allowedTools` at all | Denied |

This does not change the Bash allowlist, the branch-scoped push rules,
or any other V1.2 control — it closes a separate, independent gap
(file writes) that V1.2 never addressed. Regression coverage:
[`tests/test_agent_bridge_permission_config.py`](../../tests/test_agent_bridge_permission_config.py),
which inspects the workflow's own source text (no PyYAML dependency —
none of this suite's other tests require one either) and proves:
`--permission-mode acceptEdits` is present on the Claude step;
`Write`/`Edit`/`MultiEdit` are not explicitly in `--allowedTools`; the
two branch-scoped exact push rules from V1.2 are unchanged and are the
*only* `git push` rules present; and no `git merge`, `gh pr merge`, bare
`Bash`, or `Bash(*)` rule has been introduced.

## Branch naming is deterministic and enforced (Chief review, PR #13)

**The bug this fixes:** the original V1.2 draft granted `Bash(git push
*)` — a wildcard that, despite the prompt's plain-language "never push
master" instruction, was **not actually enforced**. `git push origin
master`, or a refspec trick like `git push origin <branch>:master`,
textually matches that rule just as well as a legitimate feature-branch
push. Relying on model behavior for the one operation this bridge must
never allow is exactly the kind of gap issue #12 was written to close.

**The fix:** every bridge run for an issue uses **one fixed,
deterministic branch name for that issue's entire lifecycle** —
`agent/issue-<N>`, computed once by
[`.github/scripts/branch_policy.py`](../../.github/scripts/branch_policy.py)
(`agent_branch_navn`) and exposed as a step output
(`steps.branch.outputs.name`) that the "Run Claude Code" step, its
prompt, and the evidence-gathering steps all reference — never
recomputed or restated, so they cannot drift apart. `status:ready`
creates this branch from `origin/master`; every later
`status:changes-requested` round reuses the identical name.

That fixed name is then used for two independent things:

1. **Push permission** (`tillatte_push_kommandoer` in the same module)
   becomes two **exact-match** `--allowedTools` rules —
   `git push -u origin <branch>` and `git push origin <branch>` — for
   that literal string only. Since `<branch>` can never equal
   `"master"` (it is always `agent/issue-<N>` for an integer `N`), no
   refspec, flag, or destination variant of a master-push can ever be
   textually identical to either allowed command; an attempt is simply
   a different string and gets denied by construction, not by model
   obedience. Regression coverage:
   [`tests/test_agent_bridge_branch_policy.py`](../../tests/test_agent_bridge_branch_policy.py)
   `test_4_...`, which checks a battery of adversarial push strings
   (`git push origin master`, `git push origin HEAD:master`,
   `git push origin agent/issue-12:master`, `--force` variants, wrong
   issue's branch, …) against the two allowed strings and asserts none
   of them match.
2. **Deliverable association** (see below) looks the PR up by exact
   head-branch match instead of a text heuristic.

## Deliverable verification gate (V1.2, issue #12)

A successful "Run Claude Code" step is no longer sufficient by itself
to reach `status:review`. Two new steps run after it, only on
`success()`:

1. **Gather evidence** — **(Chief review fix, PR #13, blocker 2)**:
   the first version of this gate found candidate PRs via GitHub's
   issue timeline (`cross-referenced` events — the *"mentioned this
   issue in PR #Y"* signal), a text heuristic the `status:ready` prompt
   never actually forced Claude to satisfy, so a fully correct PR could
   still be rejected as "no deliverable" if its body happened not to
   contain a reference GitHub's own parser recognized. Fixed:
   `gh pr list --head <branch> --base master --state open --json …`
   (exact argument shape: `gh_pr_list_args` in `branch_policy.py`,
   tested in `test_agent_bridge_branch_policy.py` `test_6_...`) looks
   the PR up by the same fixed branch name from "Branch naming is
   deterministic and enforced" — exact string equality in GitHub's own
   PR index, with zero dependency on PR body/title content. `gh pr
   list --json` already returns the array in exactly the shape
   `deliverable_guard.py` expects (`number`, `state`, `baseRefName`,
   `headRefOid`, `additions`, `deletions`, `changedFiles`), so no
   per-PR loop or JSON assembly is needed.
2. **Decide** — [`.github/scripts/deliverable_guard.py`](../../.github/scripts/deliverable_guard.py),
   one pure function (`vurder_leveranse`), unit-tested in
   [`tests/test_agent_bridge_deliverable_guard.py`](../../tests/test_agent_bridge_deliverable_guard.py)
   without touching GitHub — unchanged by the PR #13 fix, since it only
   evaluates whatever PR list it's given, independent of how that list
   was gathered. Rules:
   - **`status:ready`**: the pre-run `before_head_sha` (see "Branch
     naming is deterministic and enforced" above and the "Capture
     pre-run PR state" step) must be **empty** — proof no PR already
     existed on this issue's fixed branch before this run started — and
     exactly one **open** PR against `master` must exist afterward, with
     a **non-empty diff** (`additions + deletions > 0` and
     `changedFiles > 0`). Zero candidates, more than one (ambiguous), a
     non-`master` base, an already-merged/closed PR, or (see below) a
     **non-empty `before_head_sha`** all fail the gate.
   - **`status:changes-requested`**: the same, single associated open
     PR — with its `number` matching the `before_pr_number` also
     captured by that step (see round 4 below) — **and** its
     `headRefOid` must differ from `before_head_sha`, proving new
     commits were actually pushed to *that same PR* this run — not
     merely that an open PR with a different HEAD exists on the branch.

   **Chief review fix (PR #13, round 3):** because the branch name is
   *deliberately* deterministic and reused across an issue's whole
   lifecycle (previous fix, above), a `status:ready` run could otherwise
   be fooled by a PR left over from an earlier failed/interrupted/manual
   run on the *same* branch — Claude does nothing useful, returns
   `success()`, and the post-run `gh pr list --head <branch>` finds the
   **old** PR, which already has a non-empty diff, and the gate would
   have approved it as if this run had produced it. `status:ready`
   means *"start a fresh run"* (see the label table above); a PR that
   existed *before* the run started can never be evidence of what *this*
   run delivered, regardless of its diff size or whether its HEAD
   happened to change during the run too. The fix is the single
   `before_head_sha` check above, reusing the same pre-run capture that
   already existed for `status:changes-requested` (`deliverable_guard.py`
   `vurder_leveranse`) — no new workflow step was needed. Regression
   coverage: `tests/test_agent_bridge_deliverable_guard.py`
   `test_3c`/`test_3d` (rejects both the same-HEAD and the
   HEAD-changed-anyway cases) and `test_11e` (the CLI contract).

   **Chief review fix (PR #13, round 4):** a changed `headRefOid` alone
   still didn't prove it was the *same* PR — the gate compared only the
   HEAD SHA of "whatever open PR the query finds now" against the
   before-value, never the PR's identity. Because `--allowedTools` still
   permits `gh pr edit`/`gh pr create`, a `status:changes-requested` run
   could in principle re-target the original PR's base away from
   `master` and open a **new** PR from the same branch — post-run
   `gh pr list --head <branch> --base master` would then find that new
   PR, with a HEAD SHA that differs from `before_head_sha` "by
   coincidence" (it's simply a different PR), and the gate would have
   approved it as "the same PR, new commits." Fixed: the "Capture
   pre-run PR state" step now captures `before_pr_number` from the exact
   same `gh pr list` query, and the gate requires **both** — unchanged
   PR number (identity) **and** changed HEAD SHA (progress) — rejecting
   with a specific reason if the number differs, or if no
   `before_pr_number` was captured at all. Regression coverage:
   `test_9c` (same PR, changed HEAD → pass, the review's explicit
   happy-path requirement), `test_9d` (different PR number, changed HEAD
   → reject, the review's explicit core requirement), `test_9e`/`test_9f`
   (missing `before_pr_number` rejects; string/int PR-number comparison
   doesn't false-negative), and `test_11f`/`test_11g` (the CLI contract).

If the gate passes, the existing "Move to status:review" step runs
exactly as before. If Claude's step succeeded but the gate fails, a
**new** step posts a comment explaining exactly why (the gate's
`reason`, e.g. "no open PR found" or "HEAD SHA unchanged") and leaves
the issue at `status:working` — deliberately not a new lifecycle label
(per the issue's own instruction not to invent one unless necessary),
but a distinguishable message from a hard failure. A genuine step
failure (`failure()`) is unaffected and still goes through the
pre-existing generic failure path.

This is a fail-closed design: the default, on any ambiguity or missing
evidence, is to **not** advance the issue.

**Testability boundary, stated plainly:** the exact `gh pr list --head
<branch> --base master --state open --json …` argument shape is
unit-tested (`gh_pr_list_args` in `branch_policy.py`), and the decision
function it feeds is unit-tested against synthetic PR data — but
whether that live `gh` call actually returns Claude's real PR on a real
run can only be proven by an actual E2E bridge run, the same honest
limit noted for `workflow_dispatch` testing elsewhere in this document.
What changed with the PR #13 fix is *what* that live call depends on:
exact head-branch equality in GitHub's own PR index, not a natural-
language heuristic — strictly more reliable by construction, not merely
by assumption.

## Chief-ready PR signal (V1, issue #32)

**Why this exists:** official ChatGPT Work supports event-triggered/
webhook GitHub tasks for supported **pull-request activity**, including
PR comments — but not issue-label events, which is what this Bridge's
authoritative state machine runs on. Issue #31 (parent) tracks wiring
the native Work-side task to that PR signal; this section documents
only the repo-side half: the smallest possible adapter, entirely inside
this workflow, with no custom webhook server, no OpenAI API call from
Actions, and no second Chief runtime.

**What it does:** once, and only once, the "Move to status:review"
step above has actually succeeded, the workflow refetches **live**
GitHub state (not anything cached from before the Claude step ran) and
verifies all of: the Issue still carries `status:review` and no other
lifecycle label; exactly one PR is open against `master` on the
issue's deterministic branch (`agent/issue-<N>`, see "Branch naming is
deterministic and enforced"); and that PR's current head SHA. If, and
only if, all of that still holds, it posts **one top-level comment** on
that PR containing a reserved, versioned marker:

```
KBH_CHIEF_REVIEW_READY_V1 issue=<N> head=<40-char-sha>
```

The decision and marker construction live in one pure, dependency-free
helper, [`.github/scripts/chief_ready_signal.py`](../../.github/scripts/chief_ready_signal.py)
(unit-tested in
[`tests/test_agent_bridge_chief_ready_signal.py`](../../tests/test_agent_bridge_chief_ready_signal.py)),
called from three new workflow steps ("Refetch live state for
Chief-ready signal", "Decide Chief-ready signal", "Post Chief-ready
signal comment") that run entirely **after** the Claude step, with the
workflow's own token — not through `anthropics/claude-code-action`, not
in `--allowedTools`. No new Claude trigger surface is introduced by
this feature at all.

**Ordering:** `status:review` first, signal second — enforced by the
new steps being gated on `steps.deliverable.outputs.ok == 'true'` (the
same deliverable-PASS gate from above) and running after the "Move to
status:review" step (`id: promote`) in step order, so the marker can
never be posted before the Issue is actually live at `status:review`.

**Idempotency / head semantics:** before posting, the workflow fetches
the target PR's existing top-level comments and the helper checks them
for an *exact*, line-anchored match of the reserved marker for the same
`(issue, head)` pair — malformed or near-match text never counts (wrong
version, wrong case, missing spacing, a short SHA, or the marker
embedded mid-line all fail the match on purpose). If found, posting is
skipped as a no-op, not an error. A later `status:changes-requested`
round produces a **new** head SHA, which is deliberately *not* treated
as a duplicate, so re-review wakes correctly.

**What the signal is (and is not):** the comment exists **solely** to
wake the native ChatGPT Work event task — it is never authoritative.
The Work task, and Chief, must always refetch live Issue/PR/head state
before reviewing anything; the comment is a nudge, not a source of
truth. The existing **hourly Chief watch remains the fallback** path if
this event signal is ever missed or fails to fire. **Merge remains an
owner-only action** regardless — nothing about this signal changes the
"Owner merge gate" below.

**Failure semantics:** if signal emission fails *after* `status:review`
has already been set, the Issue is **not** rolled back and nothing is
merged — a dedicated step (distinct from the generic failure step,
which is scoped away from this case via `steps.promote.outcome`) posts
a clear failure comment and leaves the Issue at `status:review`, so the
hourly Chief watch can still recover it. "Fails" here is not limited to
a `gh pr comment` API error: a **fail-closed rejection** — the helper
finding, on live refetch, that the signal contract no longer holds
(Issue no longer exclusively `status:review`, no single open PR on the
deterministic branch, or a missing head SHA) — exits the "Decide
Chief-ready signal" step non-zero on purpose (Chief review, PR #34),
so the same dedicated failure step runs instead of the job finishing
green with neither a marker nor a report. An **exact duplicate**
marker for the same `(issue, head)` pair is the one case that is
*not* a failure — the helper exits zero and the run is a normal,
idempotent no-op.

## Work-side Chief task (V1, issue #31)

**Why this exists:** the repo-side half above (issue #32) only gets a
wake-up signal as far as a PR comment; something on the Chief/ChatGPT
side still has to receive that event and actually act. Official ChatGPT
Work supports event-triggered/webhook GitHub tasks for supported
pull-request activity, including PR comments — so issue #31 wires a
standalone Work task to that signal instead of building any custom
webhook server, OpenAI API call from Actions, or second Chief runtime.
This section records only the **live configuration** of that Work-side
task; it does not change anything in this repository's own workflow
code.

**Live configuration:**

- **Task name:** `Kvernhaug Chief Event Review` — a standalone Work
  task, separate from the existing hourly `Kvernhaug Approval Watch`.
- **Trigger:** event-only, scoped to repository-scoped PR activity in
  `Joludvig/kvernhaug-brygghus` as a candidate wake-up — not issue-label
  events (Work does not support those) and not any other repository.
  The triggering event itself supplies only the repository and a
  candidate PR number; it does not need to be a PR comment, and any
  other event family delivered by the configured repository-scoped PR
  trigger (`opened`, `ready_for_review`, `closed`, plus enabled PR
  comments) is a harmless candidate, since the task never derives
  authorization from the event payload — only from what it
  independently refetches, below.
- **What wakes it:** the task refetches the candidate PR's **live**
  top-level comments and derives authorization solely from that fetch —
  exactly one applicable current-head marker must be discovered and
  validated there:
  ```
  KBH_CHIEF_REVIEW_READY_V1 issue=<N> head=<40-char-lowercase-sha>
  ```
  A candidate event with no such marker in the PR's live comments (e.g.
  a non-comment PR event, or a comment that isn't this marker) is not an
  error — it is simply not a review trigger, and the task takes no
  action.
- **The marker is wake-up only, never authoritative.** Exactly as
  stated above for the signal itself, the Work task must refetch
  **live** Issue/PR/base(`master`)/deterministic-branch
  (`agent/issue-<N>`)/current-head state **at least twice** before
  taking any action: once on waking, to discover and validate the
  exactly-one applicable marker from the PR's live top-level comments
  and confirm its `(issue, head)` pair still reflects live reality, and
  again **immediately before** any mutating action (posting the review,
  applying a lifecycle label) — never acting on the triggering event's
  payload alone, and never on a fetch that has gone stale between the
  wake-up and the mutation.
- **Idempotency:** a duplicate marker, or a review request for a head
  SHA the task has already reviewed, is a no-op — mirroring the
  idempotent handling of the marker itself on the repo side.
- **Blockers (CHANGES REQUESTED):** when a Chief review finds blocking
  issues that need another Claude pass and no owner decision, the Work
  task submits a formal GitHub `REQUEST_CHANGES` review on the PR
  **and** applies `status:changes-requested` as the issue's sole,
  exclusive lifecycle label (replacing `status:review`, per "Lifecycle
  labels are exclusive" above) — acting through the connected owner
  GitHub identity, as recorded in the label table and lifecycle
  paragraph above.
- **PASS:** the Work task submits a formal GitHub `APPROVE` review on
  the PR **and** applies `status:approved` as the issue's sole,
  exclusive lifecycle label, and separately notifies the owner with a
  GO/NO-GO prompt — approval alone never authorizes a merge.
- **Manual/owner-only gates:** anything requiring a PC-side action,
  deploy, credential, permission change, or a `SCOPE CHANGE` comment
  from Claude is never resolved by the Work task itself — it notifies
  the owner instead and takes no mutating GitHub action beyond that
  notification.
- **What the Work task never does:** push to any branch, merge, edit an
  issue body, or close an issue automatically — identical restrictions
  to every other actor in this Bridge (see "Owner merge gate" below).
- **Fallback unchanged:** the existing hourly `Kvernhaug Approval Watch`
  task remains active and is the fallback path if this event-triggered
  task is ever missed, delayed, or fails to fire — exactly as the
  repo-side signal above already treats it.
- **`MERGED != DEPLOYED` remains in force:** an `APPROVE` review and
  `status:approved` label are review-stage signals only; they say
  nothing about deploy state, and nothing in this task changes that.

**This issue is the controlled E2E fixture for #31.** The
Claude-authored documentation PR this issue itself produces is the real
end-to-end test: E2E success requires, in order, that the Bridge moves
this issue to `status:review`; that it emits the real
`KBH_CHIEF_REVIEW_READY_V1` marker for this PR's exact head SHA; that
the Work task above wakes on that PR's activity, refetches live state,
discovers and validates that exact marker from the PR's live top-level
comments, and submits a formal `APPROVE` review for that exact head;
that this issue then moves to
`status:approved`; and that the owner receives a GO/NO-GO notification
— with **no merge** at any point. Those outcomes are external
GitHub/Work observations, not something this documentation itself can
assert; nothing in this PR claims E2E PASS.

## Scope-change rule

Once a Claude run starts, the triggering issue's body is the run's
**immutable task specification** for that run. Discovering that the
task needs more than the issue describes is not license to expand
silently — the run must post a `SCOPE CHANGE` comment describing
exactly what's needed and why, and stop for an explicit owner
decision, exactly as this project's manual sessions have already done
throughout PRI 1/PRI 2 (e.g. the CALC-002 rounding decision, the
process-profile losslessness decision on PR #5).

## Test/report expectations

Each Claude run follows the same discipline established manually
across this project's prior rounds — nothing new is invented here,
V1 just automates the handoff:

- Fetch and start from current `origin/master` in a fresh branch
  (never the owner's local checkout).
- Run the tests the issue requests, and report the exact commands and
  results.
- Push the branch, create or update the PR (never push to `master`
  directly, never merge).
- The PR report states: branch/head SHA, files changed, exact
  behavior implemented, tests/results, assumptions, and any
  unresolved questions — matching the "Deliverable" section format
  every issue in this project has specified explicitly.
- For a `status:changes-requested` run: address **only** the points
  from the most recent Chief review, report which were addressed and
  how, and leave everything else in the PR untouched.

## Owner merge gate

`status:approved` is a **label**, not a merge. Nothing in this
workflow — nor any prompt given to Claude — ever runs `gh pr merge` or
pushes to `master`. Merge is, and remains, a separate, explicit action
the owner takes themselves (via the GitHub UI or `gh pr merge`,
outside this automation entirely).

## Anti-loop / idempotency behavior

Several independent layers, deliberately redundant:

1. **Actor guard**: only a label applied by the human owner
   (`sender.login == repository_owner`, `sender.type != Bot`) can
   start a run. Every label change *this workflow itself* makes is
   performed by the workflow's own token/actor — never the owner's
   login — so it can never satisfy this condition and re-trigger
   itself.
2. **No comment trigger**: V1 has no `issue_comment` trigger at all,
   so there is no AI↔AI comment-reaction surface in the first place.
3. **GITHUB_TOKEN workflow-triggering suppression**: GitHub does not
   run *other* workflows in response to label/PR/push events performed
   with the default `GITHUB_TOKEN` (a platform-level protection, not
   something this workflow has to implement itself) — a further,
   independent backstop on top of guard 1.
4. **Live re-verification**: the `guard` job re-fetches the issue's
   *current* labels via the API before doing anything, rather than
   trusting the webhook payload — a trigger that has already been
   superseded by an earlier/concurrent run (labels no longer show
   `agent:claude` + a trigger status label) is skipped.
5. **Concurrency group**: `concurrency: group:
   claude-agent-bridge-<issue number>` with `cancel-in-progress: false`
   ensures at most one run per issue is ever executing; a second
   trigger for the same issue queues behind the first rather than
   running in parallel, and by the time it starts, guard 4 will
   usually find nothing left to do.
6. **Immediate status:working flip**: the very first mutating step
   moves the issue out of the triggering label and into
   `status:working`, shrinking the window in which a second trigger
   could fire for the same state to begin with.

## Required secrets and apps

**Not yet configured in this repository as of this PR** (verified: `gh
api repos/:owner/:repo/actions/secrets` currently returns zero
secrets). The workflow is a complete, reviewable scaffold.

To make this live, the **owner** must, in the GitHub UI (none of this
is something Claude or this workflow can do on its own — both require
interactive, owner-authenticated consent):

1. **Install the official Claude GitHub App** — <https://github.com/apps/claude>
   — on this repository. This is what lets `anthropics/claude-code-action`
   comment, push, and open PRs as the `claude[bot]` identity.
2. **Add the credential secret** (Settings → Secrets and variables →
   Actions → New repository secret). **Owner decision for V1 (made,
   not open): `CLAUDE_CODE_OAUTH_TOKEN`** — generated locally with
   `claude setup-token` — so the bridge draws on the existing Claude
   subscription rather than separate per-token API billing.
   `ANTHROPIC_API_KEY` (an `sk-ant-...` key, billed per-token via the
   API) remains fully supported by the workflow as a fallback/alternative
   if that ever becomes preferable; the workflow accepts either and
   requires only one.

   (A third option, Workload Identity Federation — no static key at
   all, short-lived tokens exchanged via GitHub's OIDC — exists for
   later hardening but requires additional Anthropic Console
   configuration; out of scope for V1's scaffold.)

Nothing in this PR contains, invents, or requires committing an actual
secret or token value — and no token value belongs in GitHub issue/PR
text either.

### Workflow permissions

The workflow grants `contents: write`, `pull-requests: write`,
`issues: write` **and `id-token: write`**. The last one is not
optional here: this workflow uses the action's *default Claude GitHub
App authentication* (it deliberately does not pass a custom
`github_token`), and Anthropic's FAQ states that path requires
`id-token: write` — "The OIDC token is required in order for the
Claude GitHub app to function." Without it, a run fails during
GitHub App/OIDC authentication even with a valid Anthropic
credential.

### What the preflight can and cannot check

The workflow's preflight step checks **only** whether one of the two
credential secrets is present, and if not, comments on the issue
naming exactly that and stops — leaving the triggering label in place
so the run can simply be retried once configured.

It **cannot** verify that the Claude GitHub App is actually installed.
If the secret exists but the App is missing, the run proceeds, the
Claude step itself fails, and the generic failure path handles it: the
issue stays at `status:working` and a failure comment points at the
workflow-run logs. Read that failure as "check the App installation
too", not just "check the secret".

## Manual / dry-run test path

`workflow_dispatch` (Actions tab → "Claude Agent Bridge" → "Run
workflow") accepts an `issue_number` and a `dry_run` boolean
(**defaults to `true`**). With `dry_run: true`, the workflow runs the
full guard/live-label-check logic and prints exactly what it *would*
do, without changing any label or invoking Claude — safe to run at any
time, against any real issue, with zero side effects and zero API
cost. Set `dry_run: false` to actually execute (still gated by the
same secret/App requirements above).

## Labels

Created in this repository as part of this PR (`gh label create`,
non-destructive, listed here for reference):
`agent:claude`, `status:ready`, `status:working`, `status:review`,
`status:changes-requested`, `status:approved`, `area:core`,
`area:web`, `area:app`, `area:infra`.

## What this document does not do

- Does not add an OpenAI API bot, custom server, MCP broker, A2A
  server, Sóti runtime, or any other agent backend — the Chief/ChatGPT
  side of the bridge is configured separately, through supported
  ChatGPT/connected-GitHub capabilities, outside this repository.
- Does not change what a Chief review actually checks, nor any
  App/Web/Core product behavior.
- Does not implement automatic merging, ever.
- Does not replace GitHub as the audit trail.
