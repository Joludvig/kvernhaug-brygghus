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
| `Bash(git checkout -b <branch> origin/master)` / `Bash(git checkout <branch>)` | Create the task's feature branch (`status:ready`), or re-land on it if something moves `HEAD` mid-run — **exact match, no wildcard** (narrowed from `Bash(git checkout *)` by issue #329, once the wrapper took over branch checkout on the changes-requested path; see "Deterministic changes-requested handoff (V1.9, issue #329)" below). |
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
| `Bash(gh pr view *)` | Read an existing PR's state. (Since issue #329 the changes-requested round no longer uses this to *discover* the PR or the Chief review — both arrive verified; see below.) |
| `Bash(gh pr edit *)` | Update the PR description/report. |
| `Bash(gh pr comment *)` | Post the PR-side report. |
| `Bash(gh pr list *)` | Look up the PR associated with this run's fixed branch. |
| `Bash(pip install -r requirements.txt)` | Install project dependencies before running tests — **exact match, no wildcard**: this and only this invocation, deliberately not `pip install <anything>`. |
| `Bash(python3 -m unittest *)` | Run the project's test suite (full `discover -s tests -b` or a focused module). |
| `Bash(python3 scripts/generate_web_i18n_pages.py)` | Run the repository's canonical Web NO/EN generator entry point for bounded Web work (issue #154) — **exact match, no wildcard**: this and only this invocation, deliberately not `Bash(python3 *)` or `Bash(python3 scripts/*)`. See "Canonical Web i18n generator permission (V1.4, issue #154)" below for why. |
| `Bash(python3 .github/scripts/ho_router_check.py pointer)` / `Bash(python3 .github/scripts/ho_router_check.py verify)` | Run the HO router freshness/orphan check (issue #252) — **two exact matches, no wildcard**: only these two literal invocations. See "HO router freshness check (V1.6, issue #252)" below. |

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

## Canonical Web i18n generator permission (V1.4, issue #154)

**The bug this fixes:** #146's two Bridge rounds (PR #149) needed to
regenerate the Web NO/EN pages as part of a bounded Web task, and
correctly *refused* to hand-edit `web/en/**` or smuggle a write through
`python3 -m unittest` — because `.claude/rules/web.md` requires
generated EN pages to come only from the repository's canonical
generator, `python3 scripts/generate_web_i18n_pages.py`, never a manual
edit. But that exact command was never in `--allowedTools` at all (the
only Python grant was `Bash(python3 -m unittest *)`, issue #12), so
there was structurally no compliant way for a Bridge round to produce
that regeneration — a correct refusal, but a dead end for any future
Web round that legitimately needs it.

**The fix:** exactly one additional `--allowedTools` entry —
`Bash(python3 scripts/generate_web_i18n_pages.py)` — an **exact-match,
argument-free** rule, the same pattern already used for
`Bash(pip install -r requirements.txt)` (V1.2). No wildcard is
introduced anywhere: not `Bash(python3 *)` (which would grant arbitrary
Python execution), not `Bash(python3 scripts/*)` (which would grant
every other script under `scripts/`, several of which write outside
`web/**` or touch data files this Bridge must never touch), and not a
bare `Bash` rule. This is strictly additive to the V1.2/V1.3 model
above — it does not change `--permission-mode acceptEdits`, the
branch-scoped push rules, the absence of `git merge`/`gh pr merge`, or
any other existing control.

**Why this is safe to add:** the generator is read-only with respect to
task/recipe/pantry data (it only ever reads `web/no/**` and writes
`web/en/**` plus `sitemap.xml`/`robots.txt`, per
[web/README.md](../../web/README.md)) and is already the codebase's own
required mechanism for producing those files — the rule grants Claude
exactly the same generator invocation a human web round would run
locally, nothing more. `--permission-mode acceptEdits` still governs
*where* any resulting file writes may land (inside
`$GITHUB_WORKSPACE` only), so this rule only ever widens *which command*
may run, not *where* it may write.

Regression coverage:
[`tests/test_agent_bridge_permission_config.py`](../../tests/test_agent_bridge_permission_config.py)
additionally proves: the exact generator rule is present; there is
exactly one such rule (no near-duplicate variants); no broader
`python3 *`, `python3 scripts/*`, bare `Bash`, or `Bash(*)` permission
has been introduced alongside it; the two branch-scoped push rules,
the absence of `git merge`/`gh pr merge`, `--permission-mode
acceptEdits`, and the absence of `Write`/`Edit`/`MultiEdit` from
`--allowedTools` are all unchanged by this addition.

**Non-goals (explicitly out of scope for issue #154):** this change
grants *permission* only — it does not itself regenerate any Web
pages, change generator behavior, or touch any Web/App/Core product
file. Whether/when a Bridge round actually invokes the generator for a
real Web task remains a separate, task-scoped decision for that round's
own issue (e.g. a future round of #146), governed by the same
`.claude/rules/web.md` requirement that generated pages must come from
this exact command.

## Bounded Node/Playwright permission pack (V1.5, issue #201)

**The bug this fixes:** issue #200's first Bridge run (workflow run
`34447715101`) required bounded Playwright browser-gate dependency
bootstrap and focused verification. The Claude step itself completed
(`conclusion: success`, 46 turns) but reported
`permission_denials_count: 2`, and post-run evidence found no open PR
on `agent/issue-200` and no such branch pushed to the remote at all —
the same class of dead end V1.2 (issue #12) already fixed once for
git/gh, just recurring here for Node/npm/Playwright, which
`--allowedTools` never covered at all: the list before this change only
granted git, gh, `pip install -r requirements.txt`,
`python3 -m unittest`, and the exact Web i18n generator invocation
(V1.4) — no Node/npm/npx command of any kind.

**The fix:** exactly the bounded permission pack issue #201 specifies,
nine additional `--allowedTools` rules, each scoped as tightly as the
official permission-rule syntax allows — eight are EXACT (argument-free
or argument-fixed) matches, and only one is a prefix rule, reserved for
the one command whose arguments genuinely vary per run:

| Rule | Why |
|---|---|
| `Bash(node --version)` | Verify the Node runtime is present before anything else. |
| `Bash(npm --version)` | Verify npm is present. |
| `Bash(npm install --save-dev @playwright/test)` | Install the Playwright test package as a dev dependency — exact match, no wildcard, so no other package can be installed through this rule. |
| `Bash(npm install --ignore-scripts)` | Install project dependencies from `package.json` without running arbitrary install-time scripts. |
| `Bash(npm ci --ignore-scripts)` | Clean, lockfile-exact install without arbitrary install-time scripts, for a reproducible CI-style bootstrap. |
| `Bash(npx playwright --version)` | Verify the installed Playwright CLI. |
| `Bash(npx playwright install chromium firefox)` | Install the two named browser engines — exact match, no wildcard, so no other Playwright subcommand or browser (e.g. `webkit`) is granted through this rule. |
| `Bash(npx playwright install --with-deps chromium firefox)` | Same install, with OS-level browser dependencies, for a runner that needs them — likewise exact match. |
| `Bash(npx playwright test *)` | Run Playwright test specs — the one command whose arguments (which spec file, which project/browser) genuinely vary per run, so this is the pack's only prefix rule. |

Every entry in the issue's proposed pack was kept — none was found
demonstrably unnecessary for #200's bounded scope, so none was omitted.

**Deliberately NOT granted**, for the same defense-in-depth reason as
every other rule in this document: `Bash(npm *)`, `Bash(npx *)`, a
generic `Bash(node *)`, any `curl`/`wget`/`sudo` rule, and (unchanged
from V1.2/V1.3) any `git push` outside the two exact branch-scoped
commands, `git merge`, `gh pr merge`, or a bare `Bash`/`Bash(*)` rule.

**What this issue does not do:** it grants *permission* only — no
Playwright/product implementation from #200 is performed here, no
Web/App/Core product file is touched, and no lifecycle, Draft→Ready,
deliverable-guard, or Chief-ready mechanism (all documented elsewhere in
this file) is changed. `--permission-mode acceptEdits`, the two
branch-scoped exact push rules, the absence of `git merge`/`gh pr
merge`, and every existing Python/i18n `--allowedTools` entry are all
unchanged by this addition. Once merged, #200 is re-triggered from a
fresh `status:ready` round to actually use this pack.

Regression coverage:
[`tests/test_agent_bridge_permission_config.py`](../../tests/test_agent_bridge_permission_config.py)
additionally proves: every one of the nine Node/Playwright rules above
is present exactly once; no broader `npm *`, `npx *`, `node *`, bare
`Bash`, `curl`, `wget`, or `sudo` permission is introduced; the two
branch-scoped exact push rules remain the only `git push` grants;
`git merge`/`gh pr merge` remain absent; `--permission-mode acceptEdits`
is unchanged; and the existing Python/i18n permissions (V1.2/V1.4) are
unchanged.

## HO router freshness check (V1.6, issue #252)

**The bug this fixes:** unlike every other governance decision in this
document (trigger authorization, deliverable verification, Draft/Ready
transition, Chief-ready signal, GO/NO-GO notification — each a pure,
unit-tested Python function), the HO router chain described in "HO
policy — local and GitHub jobs" below (`#152` → newest valid
`KBH_COS_CHECKPOINT_PTR_V1` → target `KBH_COS_LIVE_CHECKPOINT_V1`) was
verified by prose alone ("read it back", "verify publication") — no
code actually proved the pointer named the *newest* valid checkpoint.
Issue #252's documented incident: a newer valid checkpoint existed on
issue #196 (comment `5648280519`) while #152's newest pointer still
targeted an older one (comment `5648254902`) — routed HO was silently
stale until a human noticed and manually repaired it (comment
`5654816841` → `5654816412`).

**The fix:** one new pure, dependency-free module,
[`.github/scripts/ho_router_check.py`](../../.github/scripts/ho_router_check.py)
(`sjekk_router`, `nyeste_gyldig_pointer`, `gyldige_sjekkpunkt_id_er`),
following the exact same pattern as every sibling module in
`.github/scripts/` — enhanced-tested without touching GitHub, in
[`tests/test_agent_bridge_ho_router_check.py`](../../tests/test_agent_bridge_ho_router_check.py),
which includes issue #252's own exact historical comment IDs as a
regression case (`test_3b_orphan_gjenskaper_issue_252s_eksakte_hendelse`).
It does not replace the HO policy or introduce a parallel handover
store — it is the concrete, fail-closed implementation of the policy's
own step 5 ("Immediately before publication, refetch the route, target
and affected live facts... read it back... resolve the new pointer to
verify publication"), callable in two phases:

1. `ho_router_check.py pointer` — given #152's comments, resolves the
   newest valid pointer line (line-anchored, exact-format match; a
   quoted example, a mid-line mention, or a near-miss variant never
   counts — same immunity `chief_ready_signal.py`'s marker already has).
   Tells the caller which issue's comments to fetch next.
2. `ho_router_check.py verify` — given BOTH #152's comments and the
   target issue's comments (both freshly fetched), re-resolves the
   pointer itself (never trusts phase 1's cached result) and checks it
   against every valid checkpoint comment on the target issue. Exit 0
   only on `status=OK` (the pointer names the newest valid checkpoint);
   `status=ORPHAN` (a newer valid checkpoint exists but the pointer
   still targets an older one — issue #252's exact failure mode),
   `NO_POINTER`, `INVALID_TARGET`, or `POINTER_ISSUE_MISMATCH` all exit
   1, fail-closed.

Local Claude can run this unconditionally (no `--allowedTools`
restriction applies locally). Bridge Claude gained the two exact,
argument-fixed `--allowedTools` entries needed to run both phases (see
the allowed-tools table above) — no wildcard, nothing beyond these two
literal invocations. The HO policy's step 6 (`HO UPDATED: YES/NO`) now
requires a `verify` exit-0/`status=OK` result as the evidence for `YES`
on any run that actually published a checkpoint+pointer pair — see "HO
policy — local and GitHub jobs" below and the updated Bridge prompt in
`claude-agent-bridge.yml`.

**What this does not do:** it does not touch `#152`'s STATIC content,
does not change the checkpoint/pointer *format* (same markers, same
router contract), does not add a scheduled workflow or any new trigger
surface, does not enable automatic deployment/merge/arming of any
issue, and does not change Core/App/Web/Brew Lab product code. It is a
read-only verification tool; publishing itself is still the existing
`gh issue comment` mechanism the policy already describes, unchanged.

## Robust branch setup and missing-deliverable diagnosis (V1.7, issue #259)

**The bug this fixes:** issue #257 failed twice in the same distinctive
way -- the "Run Claude Code" step itself completed with `conclusion:
success`, the run's own record showed `permission_denials_count=1`, and
no `agent/issue-257` branch ever existed afterward, so the deliverable
gate (correctly) left the issue at `status:working`. The leading
hypothesis: `--allowedTools` permitted `Bash(git checkout *)` but not
`Bash(git switch *)`, and Claude Code commonly reaches for the modern
`git switch -c <branch>` form for branch creation even when a prompt
suggests `git checkout -b` -- so the very first branch-setup command of
the run was silently denied, Claude (correctly) refused to commit
directly on `master`, and the run exited cleanly with analysis but no
deliverable.

**The fix has two independent halves, matching the issue's own two
preferred options -- this repo chose the narrower one (add the missing
permission) rather than relocating branch ownership into the wrapper,
since the narrower change closes the exact observed gap without
restructuring who creates the branch:**

1. **Two new, branch-scoped, wildcard-free `--allowedTools` entries** --
   `Bash(git switch -c <branch> origin/master)` and
   `Bash(git switch <branch>)`, built by a new function,
   `.github/scripts/branch_policy.py`'s `tillatte_switch_kommandoer`,
   following the **exact same pattern** as `tillatte_push_kommandoer`
   (V1.2/PR #13): since `<branch>` is always `agent/issue-<N>` for an
   integer `N` (never `"master"`), no variant of either string can ever
   be textually identical to a command that switches to or creates a
   local branch literally named `master` -- denied by construction, not
   by model obedience, exactly like the push rules. Regression coverage:
   `tests/test_agent_bridge_branch_policy.py` (`test_4c`-`test_4f`,
   mirroring `test_2`-`test_4b` for the push rules) and
   `tests/test_agent_bridge_permission_config.py` (`test_9a`-`test_9f`,
   mirroring the V1.5/V1.6 sections: both exact rules present once each,
   no broader `Bash(git switch *)` variant, and the full V1.2-V1.6
   contract -- branch-scoped push rules, absence of `git merge`/`gh pr
   merge`, `--permission-mode acceptEdits`, absence of `Write`/`Edit`/
   `MultiEdit`, existing Python/i18n/Node/Playwright/HO-router rules --
   unchanged). The "Run Claude Code" prompt text is updated to mention
   `git switch -c <branch> origin/master` / `git switch <branch>` as
   accepted alternatives to `git checkout -b`/`git checkout <branch>`
   for both trigger labels, so the prompt and the allowlist agree on
   what is actually permitted.
2. **Improved no-deliverable diagnostics (scope item 5):** when the
   deliverable gate rejects a run, the report previously carried only
   `deliverable_guard.py`'s generic reason ("no open PR found", etc.),
   which does not distinguish a permission-denied branch-setup command
   (issue #257's fingerprint) from any other cause, including a
   deliberate Claude decision to stop. A new step, "Check remote branch
   existence for missing-deliverable diagnosis", runs only when the
   deliverable gate has just failed, using the workflow's own token
   (never Claude's `--allowedTools`, and never the Claude transcript
   itself -- no "unsafe full-output logging" is introduced) to check one
   independent fact: whether the issue's deterministic branch
   (`agent/issue-<N>`) exists on `origin` at all. A new pure,
   dependency-free module, `.github/scripts/branch_setup_diagnosis.py`
   (`diagnoser_manglende_leveranse`, unit-tested in
   `tests/test_agent_bridge_branch_setup_diagnosis.py`), turns that fact
   plus the trigger label and pre-run PR state into one of a small,
   fixed set of diagnoses:
   - `status:ready`, no remote branch at all: `branch_never_pushed` --
     issue #257's exact fingerprint, and a **strong, consistent
     indicator** of a likely permission-denied branch-setup step -- see
     "Chief review fixes (PR #261)" below for exactly how that indicator
     is now worded.
   - `status:ready`, remote branch exists: `branch_pushed_no_pr` --
     branch setup succeeded, so the missing deliverable is a later-stage
     issue (no PR opened, or a decision to stop), not a branch-setup
     permission problem.
   - `status:changes-requested`: the branch/PR is expected to already
     exist from a *prior* round (the Draft handoff already requires it),
     so mere branch existence proves nothing about *this* run's own
     branch access -- these branches report `no_new_commits` or
     `missing_prior_state` instead, and never `branch_never_pushed`.
   The "Report missing deliverable" comment now includes this diagnosis
   and its reason alongside the existing `deliverable_guard.py` reason.

**Chief review fixes (PR #261):** the review of this issue's first round
found two bounded problems, both fixed on the same branch/PR before
merge, scope held to exactly these two points:

1. **BLOCKER -- unreliable evidence source.** The "Check remote branch
   existence" step originally used `git ls-remote --heads origin
   <branch>`, which resolves its Git remote credentials however the "Run
   Claude Code" step happened to leave them. `anthropics/claude-code-
   action` installs a temporary GitHub App token for that step and
   revokes it again in its own post-step, so depending on leftover Git
   credential state made this diagnostic unreliable in exactly the
   failure path (a rejected branch-setup step) it exists to help
   diagnose. **Fixed:** the step now uses `gh api
   "repos/$REPO/branches/$BRANCH"`, authenticated purely by this job's
   own `GH_TOKEN` (`${{ github.token }}`, the same job-level workflow
   token every other step in this job already uses for `gh issue`/`gh
   pr` calls) -- entirely independent of anything Claude's step did to
   Git's credential helper. Fail-closed behavior is preserved in the
   same direction as before: any non-2xx response from `gh api` (a
   genuine "branch not found", or any other API error) still resolves to
   `remote_branch_exists=false`, so the step can never silently report
   "the branch exists" when the check itself couldn't confirm that.
   Regression coverage: `tests/test_agent_bridge_branch_setup_diagnosis.py`
   `TestBranchCheckStepUsesWorkflowToken` inspects the step's own `run:`
   body and proves it calls `gh api "repos/$REPO/branches/$BRANCH"`, uses
   no `git ls-remote`/`origin` remote at all, and still defaults to
   `remote_branch_exists=false` (no bare `|| true` that would hide a real
   `gh` failure behind a false "branch exists").
2. **ACCURACY -- overclaimed causation.** Branch absence alone cannot
   prove the cause was a permission denial, and cannot prove it was
   *not* a deliberate Claude decision to make no changes -- a conscious
   no-op that never even attempted to create the branch would leave
   **exactly the same** observable fingerprint as a denied branch-setup
   command. The original wording asserted the "not a deliberate choice"
   half as if it were established fact. **Fixed:**
   `branch_setup_diagnosis.py`'s `branch_never_pushed` reason (and the
   module's docstring) now explicitly frames the diagnosis as a strong,
   consistent *indicator*, never a *proof*, and states in plain language
   that it cannot rule out a deliberate Claude no-op unless independent
   evidence (e.g. an explicit permission denial visible in the run's own
   logs) actually identifies the cause. The diagnosis code
   (`branch_never_pushed`) itself is unchanged -- only the certainty of
   the causal claim in its accompanying reason text. Regression coverage:
   `tests/test_agent_bridge_branch_setup_diagnosis.py`
   `test_1b_branch_never_pushed_er_indikator_ikke_bevis` (replacing the
   round-1 test that asserted the old, overclaiming phrase) proves the
   reason text says "IKKE et bevis" ("NOT proof"), calls itself an
   "indikator", and explicitly names the "bevisst Claude-valg" (deliberate
   Claude choice) alternative it "kan ikke skille" (cannot distinguish)
   from.

**What this does not change:** the branch-scoped push rules (`git push
-u origin <branch>` / `git push origin <branch>`), the absence of `git
merge`/`gh pr merge`, `--permission-mode acceptEdits`, the fixed
deterministic branch-naming rule itself, the deliverable gate's own
pass/fail decision (`deliverable_guard.py` is untouched -- the new
diagnosis step only explains an existing rejection, it never overrides
one), and no owner/anti-loop authorization control from any earlier
section. No `Bash(git switch *)` wildcard was introduced. Per the
issue's own instruction, issue #257 can only be retried once this fix is
Chief-reviewed/merged.

## PÅ JOBB sequential queue (issue #260)

**Why this exists:** every trigger documented above starts from one
bounded issue the owner labels by hand. Issue #260 asks for a safe way
to pre-arm several already-bounded, already-authorized issues at once
for unattended work while the owner is away/asleep ("PÅ JOBB"), so
throughput increases without allowing autonomous merge/deploy or
parallel scope collisions. This section is purely additive: it adds one
new workflow, [`.github/workflows/pa-jobb-queue.yml`](../../.github/workflows/pa-jobb-queue.yml),
and one new pure module,
[`.github/scripts/queue_dispatch.py`](../../.github/scripts/queue_dispatch.py)
(unit-tested in
[`tests/test_agent_bridge_queue_dispatch.py`](../../tests/test_agent_bridge_queue_dispatch.py)) —
it does not change `claude-agent-bridge.yml`, `trigger_guard.py`,
`lifecycle_labels.py`, or `deliverable_guard.py` in any way. Every
safety property already established for a single bounded run (the
state machine, the deliverable gate, the owner merge gate, Draft →
Ready, the Bash allowlist) applies completely unchanged to a queue-
started run — the queue only ever decides *when* to call the existing,
unmodified `workflow_dispatch` entry point.

### Model: two new, additive labels

Neither label is part of the exclusive `status:*` lifecycle
(`lifecycle_labels.py`'s `LIVSSYKLUS_ETIKETTER`) — both are purely
additive, like `agent:claude`/`area:*`, and survive every lifecycle
transition untouched:

| Label | Who applies it | Meaning |
|---|---|---|
| `queue:pa-jobb` | Owner | Marks this issue as a PÅ JOBB queue item. Requires `agent:claude` to already be present — the same pre-authorization gate every other trigger in this document uses; `queue:pa-jobb` without `agent:claude` is not a queue item at all (`queue_dispatch.py`'s `er_ko_element`). |
| `queue:priority` | Owner | Optional. Moves a queued item to the FRONT of the queue (ahead of plain queued items, still FIFO by issue number among other `queue:priority` items). This is the reordering mechanism — see "Add / remove / reorder" below. |

### How a queue item's state is read

The queue never invents a parallel state of its own. It reads the
*same* `status:*` label every other part of this document already
uses, and classifies it into exactly one of three buckets
(`queue_dispatch.py`'s `elementets_tilstand`):

| `status:*` label | Bucket | Meaning for the queue |
|---|---|---|
| *(none)* | `ikke_startet` | Waiting in the queue, eligible to be picked next. |
| `status:ready` | `aktiv` | Just armed by the dispatcher (see below) and about to be, or already, picked up by `claude-agent-bridge.yml`. |
| `status:working` | `aktiv` | A Bridge run is genuinely executing — **or** a prior run's deliverable gate rejected it and left it here (fail-closed by design, "What this fixes" in "Deliverable verification gate" above) — either way, the queue cannot tell the two apart from the label alone, and must not advance past it. |
| `status:changes-requested` | `aktiv` | This item needs *another* Claude round before it can be considered done — the issue's own "Proposed queue model" is explicit that this state pauses the queue, not just `status:working`. |
| `status:review` | `ferdig` | Chief review is now in charge of this item; never blocks the next queue item. |
| `status:approved` | `ferdig` | Same — awaiting the owner's manual merge; never blocks the next queue item. |

**One queued item "aktiv" pauses the whole queue**, regardless of how
many other `ikke_startet` items are waiting — this is the literal
implementation of "at most one queued Claude implementation task is
active at a time by default" and "a failed/no-deliverable task must
STOP queue progression... default = fail closed." There is no
"safe-to-skip" override in this implementation; the safe, explicit way
to un-stick a queue item that will never resolve on its own is to
remove `queue:pa-jobb` from it (see below) — the queue then simply
treats it as not-a-queue-item and moves on to the next one on the very
next trigger.

### Dispatcher workflow

[`pa-jobb-queue.yml`](../../.github/workflows/pa-jobb-queue.yml) fires
on three triggers:

- `issues: labeled` scoped to exactly the `queue:pa-jobb` label —
  covers "owner arms a fresh item while the queue is idle." This is a
  human/PAT-authored label event, so it fires normally (unlike a label
  PUT performed by a workflow's own `GITHUB_TOKEN`, which GitHub
  deliberately does not cascade into further `issues: labeled` runs —
  see "Anti-loop / idempotency behavior" above, guard 3).
- `workflow_run` on completion of the `Claude Agent Bridge` workflow —
  covers "the previously active item just left `status:working`" (to
  `status:review`, `status:approved`, or back to `status:working` on
  failure). `workflow_run` is the correct cross-workflow wake-up here
  specifically *because* it does not depend on which token performed
  the upstream label change — it fires on the run's completion event
  itself, independent of guard 3 above.
- `workflow_dispatch` — manual resume, e.g. after the owner fixes or
  removes a stuck item, or reorders the queue with `queue:priority`.

On every trigger, the job re-fetches the *live* `queue:pa-jobb` issue
list (`gh issue list --label queue:pa-jobb --state open`, never the
webhook payload) and feeds it to `queue_dispatch.py`, which returns
either "no dispatch" (with a reason logged) or exactly one issue
number. If, and only if, an issue number is returned, the workflow:

1. **Arms it** — sets `status:ready`, reusing the *existing*
   `lifecycle_labels.py status:ready | gh api --method PUT ...`
   mechanism verbatim (the identical command `claude-agent-bridge.yml`
   itself already uses for `status:working`/`status:review`). No new
   label-transition logic exists anywhere in this feature.
2. **Starts the Bridge** — `gh workflow run claude-agent-bridge.yml -f
   issue_number=<N> -f dry_run=false`. This is the `workflow_dispatch`
   path issue #260 itself asked for ("preferably via its
   `workflow_dispatch` path rather than faking an owner-applied label
   event") — it depends only on the live `agent:claude` +
   `status:ready` state this step just established, exactly like any
   manual `workflow_dispatch` test run described elsewhere in this
   document; it does **not** depend on, or attempt to fake, the
   owner-sender check that gates `issues: labeled` (`trigger_guard.py`
   `vurder_trigger`'s `workflow_dispatch` branch already treats live
   state as sufficient, independent of `sender.login`).

### Safety / idempotency

- **One writer, one active run**: a single, repo-wide `concurrency:
  group: pa-jobb-queue` (not per-issue — the queue is one shared
  sequential resource) ensures at most one dispatcher evaluation runs
  at a time, so two near-simultaneous triggers can never both observe
  "queue idle" and both arm a winner.
- **`status:ready` counts as active, not "not started"**: even if the
  concurrency group were somehow bypassed, a second evaluation that
  runs moments after the first armed an item will see that item's new
  `status:ready` label and treat it as `aktiv` — fail-closed, not
  fail-open. This is the queue's own answer to "duplicate event -> no
  duplicate Claude run"; `claude-agent-bridge.yml`'s own concurrency
  group and live re-check (guards 4–5, "Anti-loop / idempotency
  behavior") independently cover the same property for the run it then
  starts.
- **No merge/deploy path exists**: this workflow never carries
  `contents: write` or a merge/deploy permission, never calls `gh pr
  merge`/`git merge`/`git push`, and is not part of any deploy
  mechanism (`scripts/deploy_web.ps1` remains the only, owner-run,
  interactive deploy path — untouched by this issue). Its only mutating
  calls are one `gh api --method PUT .../labels` (via the existing,
  unchanged `lifecycle_labels.py`) and one `gh workflow run` against
  `claude-agent-bridge.yml`'s own `workflow_dispatch` input, which is
  itself bounded by that workflow's unchanged guard/deliverable/owner-
  merge-gate chain.
- **Only pre-authorized bounded issues may enter the queue**:
  `queue:pa-jobb` alone is not enough — `er_ko_element` requires
  `agent:claude` too, the same owner-only authorization gate every
  other trigger in this document already requires.
- **Does not change roadmap priority by itself**: the dispatcher only
  ever selects among issues the owner has *already* labeled
  `queue:pa-jobb`; it never adds that label to anything on its own.

### Chief review fixes (PR #263): repo-wide Bridge activity guard

**BLOCKER found on this issue's first round:** the queue's own "aktiv"
check above only reads the `status:*` label of `queue:pa-jobb` issues
themselves. But `claude-agent-bridge.yml` uses **per-issue**
`concurrency` (`claude-agent-bridge-<issue_number>`), not one global
lane — so a perfectly normal, non-queued Bridge run on issue A could
execute **concurrently** with a queued run this dispatcher starts on
issue B. The new `workflow_run` trigger made this worse: completion of
*any* Bridge run wakes the queue, while the dispatcher's `gh issue
list --label queue:pa-jobb` snapshot structurally cannot see, or block
on, an issue that never carried that label at all. This directly
contradicted issue #260's "avoid parallel scope collisions" goal and the
original PR/docs claim that two Bridge runs could never run at once.

**The fix:** a new step, "Fetch repo-wide Claude Agent Bridge activity"
in `pa-jobb-queue.yml`, queries GitHub's own Actions run state for the
`claude-agent-bridge.yml` workflow directly —
`gh api repos/<repo>/actions/workflows/claude-agent-bridge.yml/runs`,
filtered to non-`completed` runs — entirely independent of any issue
label, so it catches a currently executing run whether or not it
belongs to a queue item. That evidence is passed to
`queue_dispatch.py` via the `AKTIVE_BRO_KJORINGER` environment
variable (JSON array of `{"status": ...}` run objects); the pure
function `har_aktiv_bro_kjoring()` pauses the queue on **any** such
repo-wide activity — checked *before* it even looks at the
`queue:pa-jobb` issues' own `status:*` labels. The parameter is
optional and defaults to "no known repo-wide activity", so every
pre-existing call site/behavior is unchanged. No new permission is
required: this job's existing `actions: write` scope (needed for the
`gh workflow run` call) already includes read access to the Actions
API.

**BLOCKER found on this issue's second round:** the first-round
`har_aktiv_bro_kjoring()` matched status against a hardcoded list of
known non-terminal statuses (`in_progress`, `queued`, `requested`,
`waiting`, `pending`) and treated an unknown or missing `status` field
as **not** active — fail-*open* on unexpected evidence, even though the
workflow step already pre-filters `AKTIVE_BRO_KJORINGER` to
`status != "completed"`, so anything reaching the function at all is
already proof of a non-completed run.

**The fix:** the classification is inverted. `"completed"` (constant
`FULLFORT_KJORINGSSTATUS`) is now the *only* status treated as not
active; any other value — a known non-terminal status, an
unknown/future one, or a missing/empty `status` field — counts as
active and pauses the queue. `AKTIVE_KJORINGSSTATUSER` is kept only as
documentation/test enumeration of known non-terminal statuses; it no
longer gates the classification itself.

Regression coverage (`tests/test_agent_bridge_queue_dispatch.py`):
`TestHarAktivBroKjoring` (every known non-terminal status recognized;
`test_ukjent_status_telles_som_aktiv_fail_closed` and
`test_manglende_status_felt_telles_som_aktiv_fail_closed` prove unknown
and missing/empty `status` values now count as active);
`TestVelgNeste.test_11_repo_vid_ikke_ko_bro_kjoring_pauser_koen` (a
non-queued issue's active Bridge run pauses a queue whose own items are
otherwise idle — the round-1 blocker's scenario);
`test_12_repo_vid_aktivitet_borte_lar_koen_fortsette` (once that
activity is gone/absent, the next queued item dispatches again);
`test_12b_...bakoverkompatibel` (omitting the parameter entirely is
unchanged); `test_12c_...` (an empty queue still reports "empty", not
"paused", even with repo-wide activity present — no point pausing
nothing); `test_13_ukjent_eller_manglende_status_pauser_koen_fail_closed`
(the round-2 blocker's scenario at the `velg_neste()` level); and
`TestCliKontrakt`'s `test_cli_aktiv_bro_kjoring_*` series proves the
same at the CLI/env-var boundary the workflow actually uses.

**What this does not change:** the existing queue-internal "aktiv"
check (still the *other* independent layer catching a queued item's own
`status:ready`/`status:working`/`status:changes-requested`), the
`pa-jobb-queue` concurrency group, the arming/dispatch mechanism, any
`claude-agent-bridge.yml` guard/deliverable/owner-merge-gate behavior,
or any merge/deploy path (still none).

### Add / remove / reorder — the owner/Chief-facing operations

- **Add**: apply `agent:claude` (if not already present) and then
  `queue:pa-jobb` to a bounded, ready-to-run issue — same safe-arming
  order already documented above ("Safe arming order — always") for
  `agent:claude` relative to any status label.
- **Remove**: remove `queue:pa-jobb` from the issue. `queue_dispatch.py`
  stops counting it immediately on the next dispatcher run — this is
  also the mechanism for un-sticking a queue that is paused on an item
  that will never resolve on its own (see "fail closed" above).
- **Reorder**: apply `queue:priority` to any `ikke_startet` item to
  move it to the front of the queue, ahead of plain queued items
  (still FIFO by issue number among other `queue:priority` items, and
  FIFO by issue number among the remaining plain items). Removing
  `queue:priority` returns an item to plain FIFO ordering. There is no
  other reordering primitive (GitHub issues have no native manual
  ordering field); this two-tier scheme was chosen as the smallest
  mechanism that satisfies "reorder" without inventing a numeric
  position label per issue.
- **Pause / resume**: pausing is implicit and automatic — any `aktiv`
  queue item pauses everything behind it, as described above; nothing
  is deleted or forgotten while paused. Resuming is likewise automatic
  once the active item reaches `status:review`/`status:approved` (the
  next `workflow_run` completion trigger picks the next item up) — or
  can be forced immediately with a manual `workflow_dispatch` run of
  `pa-jobb-queue.yml` once the blocking condition is actually resolved
  (e.g. after the owner removes a stuck item's `queue:pa-jobb` label,
  or after `status:changes-requested` work completes and the issue
  reaches `status:review` again).

### Acceptance test coverage (issue #260)

All ten of the issue's acceptance tests are covered by pure,
GitHub-free unit tests in `tests/test_agent_bridge_queue_dispatch.py`
(numbered to match): (1) empty queue → no dispatch; (2) one eligible
item → exactly one selection; (3) multiple items → only the first;
(4)/(6) an active/`status:working`/`status:changes-requested` item →
the queue pauses, the second item does not start; (5) the first item
reaching `status:review`/`status:approved` → the next may start; (7) a
duplicate evaluation of the same live snapshot → no duplicate
selection (the armed item shows as `status:ready`, i.e. `aktiv`); (8) a
non-queued issue (missing `queue:pa-jobb` or missing `agent:claude`) →
ignored; (10) the dispatch path is driven entirely by live
`gh issue list` state on every run, never a cached/webhook snapshot.
Acceptance test 9 ("no merge/deploy path exists") is an absence-of-code
proof rather than a unit test — see "Safety / idempotency" above.

### First real queue candidates

Per the issue's own instruction, this infrastructure does **not**
itself arm #257, further Phase 3B prep/regression work, or any other
issue into the queue — that remains a separate, explicit owner
decision after this issue's own PR is reviewed, exactly as issue #260
specifies. `#98`/`#100`/`#233`/`#241` remain explicitly not to be
auto-enqueued.

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

## Deterministic Chief-ready retry signal (V1, issue #40) — SUPERSEDED

**Superseded by issue #44** ("PR Draft/Ready-for-review lifecycle wake
mechanism", below): the 900-second sleep + retry-comment mechanism this
section describes has been **removed** from
`.github/workflows/claude-agent-bridge.yml` and
`.github/scripts/chief_retry_signal.py` no longer exists. This section
is kept verbatim as the historical incident record and evidence (per
issue #44's own instruction not to rewrite the #42/#43 failure
evidence) — it does **not** describe current workflow behavior. See "PR
Draft/Ready-for-review lifecycle wake mechanism (V1, issue #44)" below
for what replaced it and why.

**The bug this addresses:** the real production retry for issue #38 /
PR #39 exposed a gap the controlled E2E (issue #31/#32) had not
caught. Exact evidence, read directly from PR #39's own comment/review
timestamps:

| Time (UTC) | Event |
|---|---|
| 16:41:56 | Round-1 `KBH_CHIEF_REVIEW_READY_V1` marker posted (head `c6b9954a...`). |
| 16:45:05 | Chief's formal `CHANGES_REQUESTED` review submitted -- the Work task woke correctly and reviewed within ~3 minutes. |
| 16:51:47 | Claude's own PR follow-up report comment (round 2, new head `0bcfc583...`). |
| 16:52:07 | Round-2 marker posted -- only **~20 seconds** after the report comment above, and only **~10.5 minutes** after the round-1 task invocation started. No automatic re-review was observed for this head. |

**Root cause, stated honestly:** the round-2 marker is textually
identical in structure to the round-1 marker that worked, and the
repo-side emission logic (`chief_ready_signal.py`) behaved correctly
in both rounds -- the marker was posted, for the right head, after
`status:review` was confirmed live, exactly per contract. The gap is
therefore on the Work/ChatGPT side: either (a) Work's event delivery
coalesces/debounces PR-comment activity that arrives in a tight burst
on the same PR (the round-2 marker landed 20s after Claude's own
report comment), or (b) Work enforces some per-PR cooldown after a
recent task invocation (the round-2 marker landed ~10.5 minutes after
the round-1 invocation started). **Both remain hypotheses** -- Work's
internal event/debounce configuration is an external SaaS surface with
no API or log this repository/agent can inspect, so which one (or
whether it's something else entirely) is the actual cause is not
verifiable from here, only from Work's own side, which is owned and
configured by the owner outside this repo. Per the issue's own
instruction, this is documented as a hypothesis backed by the evidence
above, not presented as a proven root cause.

**The fix, chosen to be correct under either hypothesis without
guessing which one is real:** a bounded, one-shot, deterministic retry
wake-up, implemented entirely as new workflow steps plus one new pure
helper -- no webhook server/broker, no polling loop, no change to the
existing V1 signal's behavior:

1. After the existing "Post Chief-ready signal comment" step (issue
   #32, unchanged), a new **"Wait for Chief reaction window"** step
   sleeps a fixed **900 seconds (15 minutes)** -- chosen with a
   documented margin over the ~10.5-minute gap observed in the PR #39
   evidence above, not asserted as a verified-sufficient number. Only
   runs when this run's own signal step actually posted a *fresh*
   marker (`steps.signal.outputs.post == 'true'`); a duplicate
   (pre-existing marker) is that earlier run's own responsibility.
2. **"Refetch live state for Chief-ready retry"** re-fetches the
   issue's live labels, the PR's live state/comments, and (new) the
   PR's live **reviews** -- never anything cached from before the
   wait.
3. **"Decide Chief-ready retry signal"** calls the new pure helper
   [`.github/scripts/chief_retry_signal.py`](../../.github/scripts/chief_retry_signal.py)
   (`vurder_retry`, unit-tested in
   [`tests/test_agent_bridge_chief_retry_signal.py`](../../tests/test_agent_bridge_chief_retry_signal.py)),
   which posts a retry **only if all of** hold on the fresh refetch:
   the issue is still exclusively `status:review`; exactly one open PR
   still exists on the deterministic branch; that PR's live head SHA
   is still the exact head the original marker signaled (a newer round
   hasn't already superseded it); the original marker appears
   **exactly once** among the PR's comments (0 is an unexpected state,
   >=2 means a retry already happened -- both reject, capping this at
   **at most one retry per head**); and no formal GitHub review
   (`APPROVED`/`CHANGES_REQUESTED`) already exists for that exact head
   (if one does, Chief already reacted -- a retry would be redundant
   noise, not a fix).
4. **"Post Chief-ready retry signal comment"** posts, only if step 3
   said so, a **second** comment carrying the exact same reserved
   marker line (unchanged format, unchanged version string) as an
   isolated, later PR-activity event -- temporally separated from
   whatever burst may have caused the original miss, addressing both
   the coalescing and cooldown hypotheses the same way.

**Why this preserves every existing guardrail:**
- **Marker format**: byte-identical `KBH_CHIEF_REVIEW_READY_V1
  issue=<N> head=<sha>` line, reusing the same construction logic
  (duplicated, not imported, matching every other `.github/scripts`
  module's independence convention -- checked against
  `chief_ready_signal.py`'s copy by
  `tests/test_agent_bridge_chief_retry_signal.py`).
- **Wake-up only, never authoritative**: the retry comment says so
  explicitly, same as the original.
- **Idempotency**: capped at exactly one retry attempt per `(issue,
  head)` by the exact-count check in step 3 above; Work's own
  idempotent handling of a review request for an already-reviewed head
  (AGENT_WORKFLOW.md, "Work-side Chief task") covers the remaining
  case where a retry marker somehow reaches Work *after* it already
  reviewed via some other path.
- **No polling replacement**: this is one bounded `sleep` plus a
  single re-check, not a recurring loop -- the hourly `Kvernhaug
  Approval Watch` is completely untouched and remains the ultimate
  fallback if even the retry is missed.
- **No new autonomy**: no auto-merge, no direct `master` push (the
  new steps use the same workflow token as the existing signal steps,
  never Claude's `--allowedTools`), no issue-body mutation, no owner
  bypass -- the new steps only ever post one PR comment.
- **No product behavior touched**: changes are confined to
  `.github/workflows/claude-agent-bridge.yml` and the new
  `.github/scripts/chief_retry_signal.py`.
- **"no retry needed" is not alarm-worthy**: unlike the original
  signal's fail-closed rejection (a real anomaly once `status:review`
  is live), `chief_retry_signal.py` always exits 0 -- most rejection
  reasons here (a review already exists, a newer round already
  superseded this head) mean the system worked as intended, so no new
  failure-comment path was added for this case; genuine step failures
  (e.g. a `gh` API error) still fall through to the existing "Report
  Chief-ready signal emission failure" step exactly as before.

**Testability boundary, stated plainly, exactly as for the original
signal:** the retry decision logic and the workflow's step wiring are
unit- and source-tested without touching GitHub. Whether 900 seconds
is actually long enough to clear whatever Work-side behavior caused
the PR #39 miss can only be confirmed by a real, controlled re-review
E2E on a live issue -- acceptance criterion 4 for this issue -- which
happens outside this run's control, the same honest limit already
noted for `workflow_dispatch` and the original Chief-ready signal
above. Nothing in this change claims that E2E has already passed.

## PR Draft/Ready-for-review lifecycle wake mechanism (V1, issue #44)

**Why this replaces the section above:** issue #42/#43 proved, with
concrete timestamp evidence, that the issue #40 retry mechanism
(another top-level PR *comment*, temporally isolated from the first)
still did not reliably wake the native ChatGPT Work event task for a
round-2+ re-review -- see the preserved evidence in "Deterministic
Chief-ready retry signal (V1, issue #40) — SUPERSEDED" above. Every
wake attempt tried so far (the original marker, the 15-minute retry
marker) used the *same* GitHub event family: a PR top-level comment.
Issue #44's premise is that the unreliability may be inherent to that
event family under Work's own (unobservable) event-coalescing/cooldown
behavior, so the fix uses a **structurally different** GitHub event
family instead of trying a third comment-based variant: the PR's own
`ready_for_review` state transition.

**Preferred lifecycle (issue #44, "Target design"):**

1. Chief reviews an exact head and submits a formal `CHANGES_REQUESTED`
   review.
2. The owner (or the owner-authorized Work task) applies
   `status:changes-requested` to the issue, exactly as the existing
   state machine already requires (see "State machine" above) -- this
   is the trigger that starts the next bridge run.
3. **New in this run:** right after "Capture pre-run PR state" and
   *before* "Run Claude Code", the bridge converts the issue's existing,
   deterministic PR (`agent/issue-N`) to **Draft** --
   `.github/scripts/pr_draft_handoff.py` (`vurder_draft`, unit-tested in
   `tests/test_agent_bridge_pr_draft_handoff.py`) decides this using
   only the pre-run PR state the "Capture pre-run PR state" step
   already captured (no extra GitHub call): only for a
   `status:changes-requested` trigger, only when an existing PR was
   found, and only when it isn't already Draft (idempotent no-op
   otherwise). This *attempt* decision alone is deliberately never
   alarming -- it always exits 0, because a missed/skipped Draft
   conversion attempt must never all by itself block Claude's actual fix
   work. **Immediately after the attempt, a second, FAIL-CLOSED step
   verifies the outcome** -- see "Draft is a verified prerequisite, not
   a best-effort attempt (Chief review, PR #45)" below.
4. Claude fixes the same deterministic branch/PR exactly as before (no
   change to "Run Claude Code" or its `--allowedTools`) and the issue
   returns to `status:review` exactly as before (deliverable gate,
   `status:review` promotion, Chief-ready marker -- all **unchanged**).
5. As the final successful handoff action -- *after* the existing
   Chief-ready marker step (`chief_ready_signal.py`, issue #32) has
   itself succeeded (posted a fresh marker, or found the exact same
   marker already present) -- the bridge refetches **live** state again
   and converts the PR from Draft back to **Ready for review**.
   `.github/scripts/pr_ready_handoff.py` (`vurder_ready`, unit-tested in
   `tests/test_agent_bridge_pr_ready_handoff.py`) makes this decision;
   see "Fail-closed conditions" below.
6. It is this `ready_for_review` **state-transition event** -- not
   another PR comment -- that the native ChatGPT Work task wakes on for
   round 2+, per its already-documented trigger configuration (see
   "Work-side Chief task (V1, issue #31)" above: the Live configuration
   already lists `ready_for_review` as one of the accepted event
   families in the repository-scoped PR trigger). **No new Work-side
   configuration change is asserted as required by this change** --
   this is inferred from the already-documented live configuration, not
   independently re-verified against Work's actual current settings
   (an external SaaS surface with no inspectable API from this repo, the
   same honest limit noted throughout this document); the owner should
   confirm this still holds before relying on it for a live re-review
   E2E (acceptance criterion 6, issue #44).

**Round 1 / initial-review safety (issue #44 requirement) -- SUPERSEDED
by issue #62:** this paragraph is kept verbatim as the historical
record of issue #44's original round-1 design; it no longer describes
current behavior -- see "Round 1 also uses the Draft -> Ready lifecycle
(V1, issue #62)" below for what replaced it and why. Originally: a
fresh `status:ready` run's `gh pr create` always opened the PR
**Ready** (never Draft) -- so step 3 above never ran for `status:ready`
at all (`pr_draft_handoff.py` rejects any trigger label other than
`status:changes-requested`). Round 1's Chief wake relied solely on
GitHub's `opened` PR event (already an accepted event family per the
issue #31 Work-side configuration) plus the unchanged Chief-ready
marker. `pr_ready_handoff.py` ran identically on **every** successful
round, round 1 included, but found `isDraft == false` already and
treated that as a non-alarming `already_ready` no-op -- no
special-casing was needed to keep round 1 safe, and no accidental
Ready->Ready mutation occurred.

**Draft is a verified prerequisite, not a best-effort attempt (Chief
review, PR #45):** the first version of step 3 above stopped at the
attempt -- `pr_draft_handoff.py`'s `vurder_draft` deliberately exits 0
on every rejection (empty pre-run PR state, ambiguous lookup, already
Draft, …), and "Run Claude Code" was never gated on the outcome. Chief's
review of PR #45 found this fail-**open**: if the pre-run PR lookup was
empty, ambiguous, stale, or simply couldn't prove `isDraft`, the run
still continued, Claude could still push a new head, and the round
could still finish with the PR **still Ready** -- at which point
`pr_ready_handoff.py` reads that as the harmless `already_ready`
no-op it's designed to be for round 1, and never emits a
`ready_for_review` event at all. That is exactly the missed re-review
issue #44 exists to prevent, just relocated one step earlier.

**The fix:** two new workflow steps run between "Convert PR to Draft
for changes-requested handoff" and "Run Claude Code":

1. **"Refetch live state for Draft verification"** re-fetches the PR's
   live `number`/`state`/`baseRefName`/`headRefName`/`isDraft` for the
   issue's deterministic branch -- never the pre-run capture from
   "Capture pre-run PR state", which by this point may already be
   stale (the conversion attempt itself just ran).
2. **"Verify PR Draft state before Claude run"** calls the new pure
   function `verifiser_draft` (same module, `pr_draft_handoff.py`,
   unit-tested alongside `vurder_draft`) on that fresh refetch. Unlike
   `vurder_draft`, this is **fail-closed**: it exits 0 only when Draft
   is not required at all (`status:ready`) or is positively confirmed
   -- exactly one open PR against `master` on the deterministic branch,
   whose number matches `before_pr_number` (the same identity check
   `pr_ready_handoff.py` already applies for AC#4, so a same-branch PR
   swap can't be mistaken for the original), **and** whose live
   `isDraft` is `true`. Any other outcome -- missing/ambiguous PR, an
   identity mismatch, or `isDraft == false` -- exits 1.

Because this step's `if:` condition contains no `success()`/`failure()`/
`always()` call, GitHub Actions implicitly requires the job to still be
successful for it to run at all, and its own non-zero exit in turn
fails the job for every step after it that doesn't opt back in with one
of those functions -- which includes "Run Claude Code". **A
`status:changes-requested` round whose Draft state cannot be positively
verified on a fresh refetch therefore never invokes Claude at all**,
closing the fail-open gap structurally rather than relying on the
decision function's caller to remember to check an output. A dedicated
"Report Draft-verification failure -- Claude did not run this round"
step (gated on `steps.draft_verify.outcome == 'failure'`) posts a clear
comment and leaves the Issue at `status:working`, exactly as it already
was; the existing generic "Report failure" step is scoped to exclude
this case (`steps.draft_verify.outcome != 'failure'`) so the two never
double-report the same failure. `status:ready` and an already-verified
Draft PR remain exactly as non-alarming as before this fix -- only a
genuinely unproven Draft state for a changes-requested round is new
behavior. Regression coverage:
`tests/test_agent_bridge_pr_draft_handoff.py` (`TestVerifiserDraft`,
`TestCliVerifyFailClosed`, and the extended `TestWorkflowKildetekst`
checks for step ordering/gating, the `decide`/`verify` CLI-mode split,
and the two failure-report steps' mutual exclusivity).

**Round 2 (Chief review, PR #45): identity/Draft alone still don't
prove it's the same head.** The fix above verified PR *identity*
(number matches `before_pr_number`) and live `isDraft`, but never
compared the fresh `headRefOid` against `before_head_sha` -- so a push
(or any other head movement) between the "Capture pre-run PR state"
step and "Refetch live state for Draft verification" could pass both
checks while actually describing a **different** head than the one the
prerequisite was supposed to cover. "Refetch live state for Draft
verification" now also forwards `before_head_sha` (from the same
pre-run capture) into the JSON `verifiser_draft` reads, and
`verifiser_draft` requires the fresh `headRefOid` to equal it exactly
for `status:changes-requested` -- rejecting fail-closed on either a
mismatch or a missing head, on either side. `status:ready` behavior is
unchanged (the check is skipped entirely, same as before). Regression
coverage: `tests/test_agent_bridge_pr_draft_handoff.py` `test_7i`
(missing `before_head_sha`), `test_7j` (changed head despite matching
identity/Draft), `test_7k` (missing live `headRefOid`), the CLI-level
`test_8g`/`test_8h`, and `test_6o` (workflow wiring: the refetch step
actually forwards `before_head_sha`).

**Round 3 (Chief review, PR #45): "already Ready" was fail-open for a
changes-requested round.** Rounds 1-2 above made the **pre-Claude**
Draft handoff fail-closed, but the **post-Claude** ready gate
(`pr_ready_handoff.vurder_ready`) still treated *every* live
`isDraft == false` as the same harmless `already_ready` no-op --
correct for `status:ready` (which never goes through Draft at all, see
"Round 1 / initial-review safety" above), but not for
`status:changes-requested`: the PR could be correctly verified Draft
before Claude ran and then be externally/prematurely undrafted before
this final gate executed, and the gate would silently accept that as
`already_ready`, emit no `ready_for_review` transition, and lose
exactly the re-review wake issue #44 exists to guarantee -- with no
observable failure at all. The fix makes the final gate
**trigger-aware**: `vurder_ready` now also takes the run's
`trigger_label`. For any trigger other than exactly
`status:changes-requested` (i.e. `status:ready`), "already Ready"
remains unconditionally safe, unchanged from before. For
`status:changes-requested`, "already Ready" is safe **only** when a
new, separate, reserved marker --
`KBH_PR_READY_TRANSITION_DONE_V1 issue=<N> head=<sha>` (same
line-anchored, exact-version/exact-40-hex-SHA grammar as the existing
`KBH_CHIEF_REVIEW_READY_V1` marker, but a distinct version string so
the two can never be confused with each other) -- already exists for
this exact `(issue, head)` pair among the PR's comments, proving that
**this mechanism itself**, not something external, already performed
the transition for this exact head (the intended case: a re-run of
this same workflow step after the transition already succeeded).
Without that marker, "already Ready" in a `status:changes-requested`
round is now a **genuine, fail-closed rejection** instead of a silent
no-op. The marker is posted by a **new** workflow step, "Post PR
ready-transition-done marker", which runs only immediately *after*
`gh pr ready` itself has actually succeeded (`steps.transition.outcome
== 'success'`) -- so it can never be posted for a head that this run
did not really transition. `pr_ready_handoff.py`'s CLI now accepts an
optional output-file argument (same pattern as
`chief_ready_signal.py`'s comment-file argument) that it writes the
built marker text to, only when `set_ready=true`, for that new step to
post via `gh pr comment`. Regression coverage:
`tests/test_agent_bridge_pr_ready_handoff.py`
(`TestChangesRequestedReadyFailOpen`, `TestByggReadyDoneMarker`, the
extended `TestCliExitKode` marker-file-writing tests, and the extended
`TestWorkflowKildetekst` checks for the new step's gating/ordering and
the refetch step's `trigger_label` wiring).

**Fail-closed conditions (issue #44, acceptance criterion 3) --** the
Draft -> Ready transition (step 5 above) is rejected, on a **fresh**
refetch of live state, if **any** of the following hold (see
`pr_ready_handoff.vurder_ready`):

- The signaled head-SHA (from the Chief-ready marker step) or the issue
  number is missing.
- The issue is not (or no longer) exclusively `status:review`.
- There is not exactly one open PR against `master` on the issue's
  deterministic branch (wrong branch/base, or ambiguous).
- The PR's **live** head-SHA no longer matches the signaled head
  (stale -- a newer round has already superseded it).
- The reserved `KBH_CHIEF_REVIEW_READY_V1` marker for this exact
  `(issue, head)` does not appear **exactly once** among the PR's
  top-level comments (0 = missing marker, ≥2 = a conflicting/duplicate
  marker).
- A formal GitHub review (`APPROVED`/`CHANGES_REQUESTED`) already
  exists for this exact head -- Chief has already reacted; a transition
  would only trigger a redundant/confusing re-review.
- (Round 3, `status:changes-requested` only) the PR is already Ready
  but no `KBH_PR_READY_TRANSITION_DONE_V1` marker for this exact
  `(issue, head)` proves this mechanism performed that transition.

A failed deliverable validation can never even reach this gate at all
-- structurally impossible, since these workflow steps are gated on
`steps.deliverable.outputs.ok == 'true'`, exactly like the existing
Chief-ready marker steps.

Any of the conditions above makes `vurder_ready` exit 1 (the same
fail-closed exit-code contract as `chief_ready_signal.py`), which fails
the "Decide PR ready-for-review transition" step and runs a dedicated
"Report PR ready-for-review transition failure" step -- `status:review`
is **never** rolled back and nothing is merged; the hourly Chief watch
(and, for a first-round PR, the existing `opened`-event wake) remain
the fallback paths, exactly as issue #32's own failure semantics
already establish. This new failure-report step is deliberately
distinct from the existing "Report Chief-ready signal emission
failure" step (which is now scoped to `steps.signal.outcome ==
'failure'` specifically), so a rejection is never misattributed to the
wrong stage.

**Round 5 fix (PR #45, Chief review):** the "Decide PR ready-for-review
transition" step above only ever *decides* whether to transition --
that decision succeeding (`ready_decide` step outcome `success`,
`set_ready=true`) says nothing about whether the actual mutation
afterward, `gh pr ready` in the "Transition PR to Ready for review"
step, itself then succeeds. Before this fix, a failure there (e.g. a
transient GitHub API error) fell through every existing report step
unreported: the generic failure step is excluded because
`steps.promote.outcome == 'success'`, and the dedicated "Report PR
ready-for-review transition failure" step above requires
`steps.ready_decide.outcome == 'failure'`, which is false here --
`ready_decide` itself succeeded. Two new, distinctly-scoped failure
reports close this:
- "Report PR ready-for-review transition command failure", scoped to
  `steps.transition.outcome == 'failure'` -- the actual `gh pr ready`
  call itself failing, as distinct from the decision that preceded it.
- "Report PR ready-transition-done marker post failure", scoped to
  `steps.marker_post.outcome == 'failure'` (the "Post PR
  ready-transition-done marker" step was given an explicit `id:
  marker_post` for this) -- by the time this step runs, `gh pr ready`
  has already succeeded, so the real `ready_for_review` wake this
  feature exists to produce has already fired; a failure here only
  means the `KBH_PR_READY_TRANSITION_DONE_V1` proof marker itself
  never got posted, which could make a *later*
  `status:changes-requested` round on this exact head unable to prove
  via that marker that this mechanism already performed the
  transition (see the "already Ready" fail-closed condition above) --
  worth its own distinct report rather than silence, even though it is
  lower severity than the transition command itself failing.

Both new steps require `steps.promote.outcome == 'success'` (so the
generic failure step, already excluded by that same condition, never
double-reports) and are each scoped to the opposite step's outcome
being *not* `'failure'` by construction (`steps.transition.outcome ==
'failure'` can never be true at the same time as
`steps.ready_decide.outcome == 'failure'`, since `ready_decide` must
have succeeded -- i.e. output `set_ready=true` -- for the "Transition
PR to Ready for review" step to run at all), so neither can be
misattributed to an existing step. Regression coverage:
`tests/test_agent_bridge_pr_ready_handoff.py`
`TestWorkflowKildetekst.test_marker_post_steget_har_id`,
`test_transition_kommando_failure_steg_finnes_og_er_scoped_riktig`,
`test_transition_kommando_failure_steg_kan_ikke_forveksles_med_ready_decide_steget`,
`test_marker_post_failure_steg_finnes_og_er_scoped_riktig`,
`test_marker_post_failure_steg_kan_ikke_forveksles_med_transition_kommando_steget`,
`test_nye_failure_stegene_kommer_etter_sine_respektive_kildesteg`, and
`test_generisk_failure_steg_ekskluderer_ikke_pa_de_nye_stegene_direkte`.

**No duplicate review/lifecycle mutation for an exact head (issue #44,
acceptance criterion 4):** a PR that is already Ready -- because this
is round 1 (unconditionally safe), or because a previous run already
completed the transition for this exact head and left the
`KBH_PR_READY_TRANSITION_DONE_V1` proof marker behind (round 3, see
above) -- falls into the non-alarming `already_ready` no-op branch;
`gh pr ready` is never called a second time for the same head. An
already-Ready `status:changes-requested` PR **without** that proof is,
since round 3, no longer treated as idempotent at all -- it is a
genuine rejection instead, precisely because there is no such
duplicate-mutation risk to guard against (nothing was transitioned by
this mechanism yet). Conversely, `pr_draft_handoff.py`'s "already
Draft" check gives the same idempotency on the Draft side.

**No loops (issue #44 requirement):** neither transition adds a new
Claude-trigger surface -- both run entirely with the workflow's own
token, outside `--allowedTools`/`Run Claude Code`, exactly like the
existing Chief-ready marker steps (see "Anti-loop / idempotency
behavior" below, unchanged). A `ready_for_review` event is PR activity,
not an issue-label event, so it cannot itself satisfy this bridge's own
`issues: labeled` trigger condition -- there is no path by which either
transition could cause this workflow to re-invoke itself.

**What was removed:** the issue #40 mechanism's four workflow steps
("Wait for Chief reaction window", "Refetch live state for Chief-ready
retry", "Decide Chief-ready retry signal", "Post Chief-ready retry
signal comment") and `.github/scripts/chief_retry_signal.py` /
`tests/test_agent_bridge_chief_retry_signal.py` no longer exist. This
is a deliberate replacement, not a silent regression -- issue #44's own
"Purpose" and "Do not add another comment retry loop as the primary
solution" instruct exactly this. The 15-minute sleep this removes was
also a fixed cost on every successful bridge run; it no longer applies.

**Testability boundary, stated plainly, exactly as for every other
mechanism in this document:** the fail-closed decision logic and the
workflow's step wiring are unit- and source-tested without touching
GitHub (`tests/test_agent_bridge_pr_draft_handoff.py`,
`tests/test_agent_bridge_pr_ready_handoff.py`). Whether the native Work
task, in practice, actually wakes reliably on a live `ready_for_review`
event -- the entire premise of this change -- can only be confirmed by
a real, controlled re-review E2E on a live issue (acceptance criterion
7, issue #44), which happens outside this run's control, the same
honest limit already noted for `workflow_dispatch` and every prior
Chief-ready signal iteration above. Nothing in this change claims that
E2E has already passed.

## Deterministic changes-requested handoff (V1.9, issue #329)

**The bug this fixes.** Agent Bridge run `35399093833` (issue #327 / PR
#328) passed **every** existing gate — the triggering label was
`status:changes-requested`, `agent:claude` was present both at event time
and live, the sender was the repo owner, the workflow explicitly reported
the trigger as authorized, it found the existing PR, captured the correct
pre-run head `6699b63b039b7cefc086fceb65b01eb48adc3542`, set the PR back
to Draft and passed the issue #44 Draft verification. The Claude step then
finished `conclusion: success` with `permission_denials_count: 11`,
**no new commit**, an unchanged PR head, and the deliverable gate correctly
reporting `no_new_commits` — so the issue fail-closed at `status:working`.

The trigger was never the defect. **The handoff was.** On this path the
wrapper handed Claude almost no verified work context and made it
rediscover everything through `gh`/`git` calls before it could start on
Chief's actual review:

1. `actions/checkout@v4` on an `issues` event lands on the default ref
   (run `35399093833` records `head_branch: master`), and the prompt told
   Claude to fetch and check out the work branch itself — so **branch
   discovery was Claude's first job** in a round that is supposed to be
   about fixing a review.
2. The prompt told Claude to find the PR with `gh pr view` / `gh pr list`,
   even though the wrapper had already captured its exact number and head
   two steps earlier and re-verified both.
3. The prompt told Claude to *"read the latest Chief review on that PR"*.
   Nothing verified that such a review existed, that it was
   `CHANGES_REQUESTED`, that its author was the repo owner, or that it
   applied to the exact head being worked on. **The review object is the
   entire work order for the round, and it was the one thing never bound
   into the handoff.**
4. Every rediscovery call is a permission surface. 11 denials over 50 turns
   with zero commits is the signature of a run that spent its budget on
   discovery it should never have had to do.

### The contract

For `status:changes-requested`, **before** "Run Claude Code" is allowed to
start, the wrapper must prove the whole work context and then prepare the
branch itself. Four steps, in this order, all after the issue #44 Draft
verification:

| Step (`id`) | What it does |
|---|---|
| `cr_state` | Fetches live state: the open PRs on the deterministic branch, and the PR's reviews **from the GitHub reviews API**. Everything is written straight to files and assembled with `jq --slurpfile`. |
| `cr_context` | The decision: `.github/scripts/changes_requested_context.py verify` (`bygg_kontekst`). Fail-closed `exit 1` on any unproven condition, which stops the job before Claude. On success it writes the verified review to `.agent_bridge_run/chief_review.md`. |
| `cr_verifier_stage` (issue #331) | Copies `.github/scripts/changes_requested_context.py` from the **current, trusted master/workflow checkout** to a runner-owned temp path (`$RUNNER_TEMP`, never inside the repo tree) — while `HEAD` is still on master, strictly before the next step switches it. See "Checkout-verifier trust root (V1.9.1, issue #331)" below. |
| `cr_branch` | Fetches the existing agent branch and `git checkout -B "$BRANCH" "$EXPECTED_HEAD"` — the exact head the verified review applies to. No `reset --hard`, no `clean`, no `rebase`, no `--force`. |
| `cr_checkout` | The proof: the **staged** copy from `cr_verifier_stage`, run as `checkout-verify` (`verifiser_lokalt_hode`) — local `HEAD` must equal the verified pre-run head and local branch must be the deterministic branch. Fail-closed `exit 1`, including when the staged copy is missing or empty. |

`status:ready` is deliberately untouched: `cr_context` returns a
non-alarming *"not required"* for any other trigger label (the same pattern
`verifiser_draft` already uses), and `cr_branch`/`cr_checkout` are gated on
`needs.guard.outputs.trigger_label == 'status:changes-requested'`.

### Fail-closed conditions

No Claude run may start unless **all** of these are proven. Any one of them
rejects the round:

- no open PR on the deterministic branch;
- more than one candidate PR (ambiguous delivery association);
- an open PR exists but its `base` is not `master` or its `head` is not the
  deterministic branch;
- the pre-run PR number/head capture is missing, or the head is not a full
  40-character SHA;
- the PR's identity changed between the pre-run capture and the fresh
  refetch;
- the PR's fresh head no longer equals the captured pre-run head;
- the PR is not still `isDraft == true` at this fresh refetch (`false` and a
  missing field are rejected identically);
- there is no review from the authorized Chief identity (repo owner);
- the owner has no *decision* review at all;
- the owner's **latest decision** review is not `CHANGES_REQUESTED`;
- that review's `commit_id` is not the exact current head;
- that review's body is empty.

**Why Draft is re-proved here (Chief review fix, PR #330).** The issue #44
Draft gate (`pr_draft_handoff.py::verifiser_draft`) runs *before* these #329
steps. Identity and exact head alone do not prove the PR is still Draft, so
a PR that flips to Ready in between would pass this gate and Claude would
run anyway. `pr_ready_handoff.py` would afterwards see an already-Ready PR
(`already_ready`), skip the Draft → Ready transition and emit no
`ready_for_review` event — leaving the round without the lifecycle
transition that records it was actually delivered. Draft is therefore an
equal precondition here, re-proved on the fresh refetch.

> **Automatic Chief is disabled (canonical #152, 2026-09-19).**
> Chief/ChatGPT does **not** run review automatically. Chief review is
> **owner-invoked in chat** (for example GREEN, or an explicit review
> request). The Claude bot / Agent Bridge is the only AI worker intended to
> run automatically; normal CI workflows remain automatic as usual.
>
> The Draft → Ready transition and the Chief-ready markers **stay** — they
> are lifecycle evidence and future-compatible plumbing — but they are
> **not** an active unattended Chief execution path, and `ready_for_review`
> does **not** by itself trigger a Chief/ChatGPT review today. Read every
> "wake signal" description elsewhere in this document (issues #32, #40,
> #44, #62) as describing that retained plumbing, not a currently active
> automatic reviewer. The Draft requirement above therefore exists to keep
> the lifecycle chain correct and auditable, not because the transition
> wakes anyone.

**Staleness semantics.** A `CHANGES_REQUESTED` is a valid work order only
while it is Chief's **most recent decision**. Decision states are
`APPROVED`, `CHANGES_REQUESTED` and `DISMISSED`; a newer `APPROVED` (Chief
passed it after all) or a newer `DISMISSED` (the review was withdrawn)
makes an older `CHANGES_REQUESTED` stale and the round is rejected —
better no run than a run against a revoked work order. `COMMENTED` and
`PENDING` are **not** decisions and never make a valid review stale, so an
ordinary follow-up comment from the owner does not block the round.

**PR comments, comment markers and Claude-generated summaries are never an
accepted substitute for the review object.** Only the reviews API counts.

### Transporting the review text

A review body is human-written free text: backticks, quotes, `$(...)`,
YAML-looking lines, arbitrary newlines. It therefore never passes through
shell quoting, `$GITHUB_OUTPUT` or a `${{ }}` interpolation. Python writes
it verbatim to `.agent_bridge_run/chief_review.md` (git-ignored, so a broad
`git add -A` can never commit it), and the prompt points Claude at that
path. Every `reason=` line the module writes to `$GITHUB_OUTPUT` is
deliberately a single line containing no review content.
`tests/test_agent_bridge_changes_requested_context.py` proves this with a
hostile body containing command substitutions, backticks, a fake `EOF`, a
fake injected workflow step and a `set-output` payload.

### What Claude is told

On a changes-requested round the prompt now states plainly that the
workflow has already done the discovery, and gives Claude the verified
issue number, PR number, branch, exact head, and the on-disk review path.
The instruction is unambiguous: **the review is Chief's work order** —
address only its points, do not perform your own re-review, do not expand
scope, do not touch unrelated code, run the focused tests plus the required
suite, commit, push the *same* deterministic branch, never merge, never
deploy, and never commit or edit `.agent_bridge_run/`.

### Permission surface

Because the wrapper now owns branch discovery and checkout, the **broad
checkout wildcard** `Bash(git checkout *)` is **narrowed** to the two exact,
branch-scoped strings from
`.github/scripts/branch_policy.py::tillatte_checkout_kommandoer`, mirroring
the existing push and switch rules. `status:ready` keeps exactly what it
needs (branch creation); a changes-requested round already starts on the
right branch. This only reduces the surface — nothing previously forbidden
becomes allowed, and no new tool, wildcard or bot allowance is introduced.

**Scope of that claim (Chief review fix, PR #330).** This removes the broad
*checkout* wildcard only. It is **not** true that it removes the last git
wildcard from the allowlist: several broad, non-destructive git rules are
deliberately retained and are out of scope for issue #329 —
`Bash(git fetch *)`, `Bash(git branch *)`, `Bash(git status *)`,
`Bash(git diff *)`, `Bash(git add *)`, `Bash(git commit *)` and
`Bash(git log *)`. See the allowlist table in "Claude's allowed tools
(V1.2, issue #12)" above for each one's rationale.

### Preserved unchanged

Owner/event authorization, the `agent:claude` requirement, lifecycle
exclusivity, the Draft handoff, exact branch policy, branch-scoped push,
absence of `git merge` / `gh pr merge`, `deliverable_guard`, the exact-head
change requirement, the Draft → Ready mechanism, the Chief-ready signal
plumbing, and the owner GO / merge governance all behave exactly as before.
Issue #329 changes none of that machinery — and, per the note above, the
Chief-ready/Draft → Ready plumbing is retained as lifecycle evidence, not as
an automatic reviewer.

### Honest limit

Everything above is proven by pure unit/regression tests and static
workflow-contract tests without touching GitHub
(`tests/test_agent_bridge_changes_requested_context.py`, plus the branch
policy and permission-config contracts). Whether the repaired route
actually carries a live round end to end can only be shown by a real
controlled changes-requested E2E — issue #327 is deliberately reserved as
that proof case. Nothing here claims that E2E has already passed.

## Checkout-verifier trust root (V1.9.1, issue #331)

**The bug this fixes.** The exact E2E retry issue #327's docstring above
describes as "deliberately reserved as that proof case" was actually
attempted (owner-authorized retry on PR #328's pre-#329 head,
`6699b63b039b7cefc086fceb65b01eb48adc3542`) and failed *before* Claude
started — not because any trigger/PR/review gate was wrong, but because
`cr_checkout` ran `python3 .github/scripts/changes_requested_context.py
checkout-verify` **from the repo working tree**, one step *after*
`cr_branch` had already switched that same tree to the old feature head.
`.github/scripts/changes_requested_context.py` was only added by #329/#330
itself, so it simply did not exist on PR #328's older head at that point —
the file had disappeared from the workspace between `cr_context` (still on
master) and `cr_checkout` (now on the old head), and the step failed
closed for the wrong reason: a missing trusted tool, not a real review-gate
rejection.

**The fix.** A new step, `cr_verifier_stage`, copies
`.github/scripts/changes_requested_context.py` from the **current, trusted
master/workflow checkout** to a runner-owned temp path (`$RUNNER_TEMP`,
outside the repo working tree) immediately after `cr_context` and — this
ordering is the whole fix — strictly **before** `cr_branch` switches the
tree to the old feature head. `cr_checkout` then runs that staged copy
(`steps.cr_verifier_stage.outputs.path`, exposed as `$STAGED_VERIFIER`),
never the copy sitting in the checked-out feature branch's own
`.github/scripts/`. The old feature branch cannot substitute a different
verifier merely by changing what its own working tree contains, because
the trusted copy no longer lives there by the time it matters. A missing or
empty staged file is itself a fail-closed rejection (`exit 1` before any
`checkout-verify` call), matching the exit-code contract every other gate
on this path already uses.

**What this does not change.** The decision logic inside
`changes_requested_context.py` (`bygg_kontekst`, `verifiser_lokalt_hode`)
is untouched — this is purely a trust-root/ordering fix for *which copy of
the script runs*, not a change to what it decides. `cr_state`/`cr_context`
(PR/review verification) and `cr_branch` (branch checkout to the exact
verified head) are unchanged. Every exact-head/Draft/owner-review gate
described above still applies identically. No `--allowedTools` permission
was broadened — `cr_verifier_stage`'s `cp` runs inside the workflow's own
job step, not through Claude's Bash allowlist, and `status:ready` is
untouched (the new step is scoped to
`needs.guard.outputs.trigger_label == 'status:changes-requested'`, same as
`cr_branch`/`cr_checkout`). Issue #327 / PR #328 themselves are not
touched or retriggered by this fix.

Regression coverage:
`tests/test_agent_bridge_changes_requested_context.py`'s
`TestWorkflowKobling` proves `cr_verifier_stage` exists, runs strictly
between `cr_context` and `cr_branch`, is scoped to
`status:changes-requested`, and that `cr_checkout` invokes the staged path
(never `.github/scripts/changes_requested_context.py checkout-verify`
directly) and fails closed when the staged file is missing/empty.

## Runtime handoff is branch-independent (V1.9.2, issue #333)

**The bug this fixes.** Issue #331 (above) closed the checkout-verifier
trust-root gap, but left two adjacent old-branch compatibility gaps, both
proven on PR #328's exact pre-#329 head
(`6699b63b039b7cefc086fceb65b01eb48adc3542`):

1. `.agent_bridge_run/chief_review.md` (issue #329) is written while the
   working tree is still on the current, trusted master checkout, but the
   `cr_branch` step (above) then switches that same tree to the old
   feature branch's exact reviewed head. Current master ignores
   `.agent_bridge_run/` via the tracked `.gitignore` — but a branch old
   enough to predate that entry does not, so after the switch the runtime
   handoff is no longer protected by the checked-out branch's own ignore
   rules at all. The prompt said it was git-ignored and must never be
   committed, but nothing actually proved that on an old branch.
2. The prompt pointed Claude at `docs/development/AGENT_WORKFLOW.md`
   unconditionally. On the current branch that is the current, trusted
   contract — but after the same old-branch checkout, that path instead
   resolves to whatever `docs/development/AGENT_WORKFLOW.md` read as
   *on that old branch*, which can predate sections this very prompt
   depends on (the #329 handoff contract, the canonical #152 manual-Chief
   policy). An old branch could therefore silently replace the contract
   Claude is told to obey with stale repository history.

**The fix, two small additions, both run immediately after the "Checkout"
step and strictly before any `.agent_bridge_run/` file is written or any
branch is switched — unconditionally, for both trigger labels (harmless
common runtime setup: `status:ready` never revisits an old branch, so
this is a no-op in effect for that path, just proven rather than
assumed):**

1. **`runtime_ignore` step** — `.github/scripts/runtime_ignore.py install`
   idempotently adds an anchored `/.agent_bridge_run/` line to **local Git
   metadata** (`.git/info/exclude`), never the tracked `.gitignore`.
   `.git/info/exclude` is untracked, per-clone state that `git checkout`/
   `git switch` never touches, regardless of which branch is checked out
   afterward — so the protection no longer depends on what any given
   branch's own `.gitignore` happens to contain. The step then *proves*
   the protection with `git check-ignore` against a probe path under
   `.agent_bridge_run/`; a missing/failed proof fails closed (`exit 1`)
   before Claude ever runs, the same exit-code contract every other gate
   on this path already uses. Pure decision logic
   (`beregn_ny_exclude_innhold`, the idempotent line-insertion) is
   separated from the git proof (`_bevis_ignorert`) so the former is
   trivially unit-testable without touching git at all.
2. **`contract_stage` step** — copies the *current*, trusted
   `docs/development/AGENT_WORKFLOW.md` to
   `.agent_bridge_run/AGENT_WORKFLOW.md`, the same trust-root pattern
   `cr_verifier_stage` (issue #331) already uses for the checkout
   verifier: stage from the checkout that is trusted *now*, before
   anything switches it. The "Run Claude Code" prompt is updated
   throughout to point at this staged copy as the one governing
   contract — never at `docs/development/AGENT_WORKFLOW.md` read from
   whatever branch happens to be checked out — and explicitly tells
   Claude that branch's own copy, if present, is historical/project
   context only, never the governing Bridge contract.

**Preserved unchanged.** Every #329/#331 trust property: exact PR
identity, exact head SHA, fresh Draft proof, the formal Chief
`CHANGES_REQUESTED` review gate, the staged checkout-verifier's own path
and ordering, deterministic existing-branch checkout, branch-scoped push,
and fail-closed behavior throughout. Neither new step touches
`--allowedTools` — both run as ordinary workflow job steps (`cp`/a plain
Python script), exactly like `cr_verifier_stage`'s `cp`, never through
Claude's Bash allowlist — so no permission is broadened. `status:ready`
remains behaviorally unchanged in every way that matters: it gains the
same two harmless steps, but neither one changes what that path does
(there is no old branch to protect against or replace a contract from —
`status:ready` creates its branch fresh from this same trusted
`origin/master`, so the staged contract copy is byte-identical to what
it would have read directly). Issue #327 / PR #328 are not touched or
retriggered by this fix.

Regression coverage:
[`tests/test_agent_bridge_runtime_ignore.py`](../../tests/test_agent_bridge_runtime_ignore.py)
— pure idempotent-insertion unit tests; a real temporary-git regression
(a fixture repo/branch with no `.agent_bridge_run/` entry in any tracked
`.gitignore`, `.git/info/exclude` installed, runtime files created,
branch switched, a broad `git add -A` run, and the runtime files proven
to stay unstaged, plus proof the tracked `.gitignore` is never touched
and the install is idempotent across repeated runs); fail-closed proof
when the git proof cannot be established; and a static workflow-contract
suite proving both new steps exist, run in the required order (before
`cr_context`/`cr_branch`/"Run Claude Code"), are **not** scoped to
`status:changes-requested`, introduce no `--allowedTools` entry and no
`git merge`/`gh pr merge`/push/checkout/switch surface, and that the
prompt points at the staged contract path rather than the unqualified
`docs/development/AGENT_WORKFLOW.md` reference this fix removes.

## Chief review handoff byte-proof (V1.9.3, issue #346)

**The bug this investigates.** Issue #344 / PR #345 (created after V1.9/
V1.9.1/V1.9.2 above were already merged to master) got THREE
owner-authorized `status:changes-requested` retries in a row, each of
which passed every gate documented above — authorized trigger, correct
PR/exact head, a genuine owner `CHANGES_REQUESTED` review (the third one
an explicit "DETERMINISTIC NO-OP RECOVERY" review that named one file and
three literal required edits, and explicitly forbade concluding no change
was needed) — and each of which finished the Claude step with
`conclusion: success`, yet produced **zero commits, zero issue comments,
and zero PR comments**. Not even a "review already satisfied" or
"cannot address in scope" report, which the prompt explicitly asks for
when a review point cannot be addressed.

The wrapper's own review-selection logic (`bygg_kontekst`/
`_nyeste_beslutning`) was re-audited against PR #345's actual three
review IDs — including two independent `CHANGES_REQUESTED` reviews on
the exact same head — and found correct; this is now a permanent
regression (`test_ii_gjenskaper_issue_346s_pr_345_hendelse` in
`tests/test_agent_bridge_changes_requested_context.py`), so review
selection itself was **not** the defect. The live GitHub Actions
transcripts for the three failed runs were not retrievable to identify
the true root cause directly, so this fix does not claim to have found
one. What it does close is a real, previously unproven gap: **nothing
proved that the staged handoff file (`.agent_bridge_run/chief_review.md`,
written by `cr_context` while the tree was still on master) still
contained exactly the verified bytes by the time Claude's turn actually
started**, after `cr_branch` (V1.9) had switched the working tree to the
old feature branch's exact head. A lost, emptied, or altered handoff file
at that point would produce **precisely** the same observable
fingerprint as "Claude read the correct review and chose, on its own, to
make no changes" — the two failure classes were indistinguishable after
the fact.

**The fix.** `changes_requested_context.py` gains a third CLI mode,
`verify-handoff` (`verifiser_review_handoff`), plus a `review_body_sha256`/
`review_body_bytes` pair of new `verify`-mode outputs (the sha256/length
of exactly what was written to `chief_review.md`). A new workflow step,
`cr_handoff_proof`, runs immediately after `cr_checkout` and strictly
before "Run Claude Code" — using the same trust-root pattern issue #331
already established (the **staged** copy of the script, never the copy
sitting in the checked-out feature branch's own `.github/scripts/`): it
re-hashes the staged handoff file and fails closed, `exit 1`, if the file
is missing, empty, or its sha256 no longer matches what `cr_context`
computed when it wrote the file. This turns a possible silent handoff
loss into a loud, diagnosable rejection instead of an unexplained
zero-commit, zero-comment success. A dedicated failure-report comment
(mirroring the existing Draft-verification failure report) explains this
specific rejection distinctly from the generic failure path.

Separately, the existing "Report missing deliverable" comment (V1.2/V1.7)
now also carries, for a `status:changes-requested` `no_new_commits`
round, the exact verified work order this run was proven to have
received — review id, author, exact head, and the handoff's own sha256 —
so a human/Chief reading a future no-op report can immediately see which
review body Claude was proven to have been handed, without reconstructing
that from the review history by head SHA.

**What this does not change.** The decision logic in `bygg_kontekst`/
`_nyeste_beslutning`/`velg_review` (review selection, exact-head binding,
staleness semantics) is untouched and was independently re-verified
against issue #346's own real incident data as a permanent regression.
`cr_state`/`cr_context`/`cr_verifier_stage`/`cr_branch`/`cr_checkout`
(V1.9/V1.9.1) are unchanged. No `--allowedTools` permission is
broadened — `cr_handoff_proof` runs as an ordinary workflow job step
(the staged Python script), never through Claude's Bash allowlist, and
`status:ready` is untouched (`verifiser_review_handoff` returns a
non-alarming "not required" for any other trigger label, and the new
step is scoped to `needs.guard.outputs.trigger_label ==
'status:changes-requested'`, same as `cr_branch`/`cr_checkout`). The
deliverable guard's own pass/fail decision (`deliverable_guard.py`) is
untouched.

**Honest limit.** This fix is evidence-based hardening and observability,
not a confirmed root-cause fix — the exact mechanism by which the three
PR #345 rounds produced zero output could not be established from source/
tests alone in this investigation. If a future `status:changes-requested`
round ever fails this new `cr_handoff_proof` gate, that is now, for the
first time, positive proof the handoff itself was the cause; if the gate
keeps passing while a round still produces no commits, that instead
points at Claude's own turn (its actual conversation/tool-use transcript,
not obtainable from this repository's tests) as the next place to look —
a distinction issue #346's incident could not make before this fix. A
bounded, owner-authorized live retry of #344 (once this fix merges) is
the next real test of whether the underlying failure recurs.

Regression coverage: `tests/test_agent_bridge_changes_requested_context.py`
— `TestReviewHandoffVerifisering` (pure unit tests for
`verifiser_review_handoff`: correct-hash accepted, missing file, empty
file, content changed between write and read, missing expected hash, and
`status:ready` non-alarming no-op), CLI contract tests for the new
`verify-handoff` mode, `test_ii_gjenskaper_issue_346s_pr_345_hendelse`
(the exact three-review, same-head regression against PR #345's real
review IDs), and `TestWorkflowKobling` additions proving `cr_handoff_proof`
exists, runs strictly after `cr_checkout` and before `Run Claude Code`,
is scoped to `status:changes-requested`, invokes the **staged** verifier
copy (never the feature branch's own file) in `verify-handoff` mode, and
fails closed on a missing/empty staged file.

## Permission-denial diagnostics (V1.10, issue #348)

**The bug this investigates.** The V1.9.3 controlled retry described above
(Agent Bridge run #749, against PR #345's exact pre-run head) finished the
"Run Claude Code" step with `conclusion: success` — 23 turns, ~290s,
~$0.535, `is_error: false` — yet PR #345's HEAD still did not move, and the
run's own process-level record separately showed
`permission_denials_count: 2`. As with issue #346's incident, this
repository's tooling could not retrieve the live Actions run's raw
execution transcript for run #749 to identify exactly which two tool calls
were denied — the same retrieval limit already documented above ("The live
GitHub Actions transcripts for the three failed runs were not retrievable
to identify the true root cause directly"). This investigation therefore
does **not** claim to have identified run #749's two specific denials; per
the issue's own acceptance criteria, it instead closes the other half —
**nothing in this workflow captured that information anywhere
durable/repo-visible even when it *is* available**, so every prior
incident of this exact shape (issue #11: 14 denials; issue #200/#201: 2
denials; issue #257: 1 denial; this one: 2 denials) was diagnosed after the
fact, by a human opening the raw Actions log by hand, never by the
workflow itself.

**Audit performed (per the issue's "Required investigation").**
`.github/workflows/claude-agent-bridge.yml`'s "Run Claude Code" step
(`id: claude`) never referenced any `steps.claude.outputs.*` value
anywhere else in the file before this fix — the action's own execution
data was invoked but never consumed. No project `.claude/settings.json`
exists in this repository, so `--permission-mode acceptEdits` (V1.3) is
the only permission control in effect for file writes; nothing in this
repo could plausibly have denied the one docs-file edit item 5 of the
issue asks about. Item 4 (a narrowly missing Bash command) could not be
confirmed or ruled out without the actual denied command strings — this
fix deliberately does **not** guess and widen `--allowedTools`
speculatively, per the issue's own "Fix principles" ("prefer exact/narrow
permission additions only when a specific denied operation proves they are
required"); any such change is deferred to whenever a live occurrence
actually proves one is needed.

**The fix.** A new pure, dependency-free module,
[`.github/scripts/permission_denial_diagnostics.py`](../../.github/scripts/permission_denial_diagnostics.py)
(`les_meldinger`, `finn_tillatelses_avslag`, `formater_sammendrag`,
`formater_markdown`), reads `anthropics/claude-code-action`'s
`execution_file` output (Claude Code's own `tool_use`/`tool_result`
message format) and extracts **only** each denied tool call's name, a
short single-line excerpt of that one call's own input, and the denial
message itself — never any other part of the transcript, cost, session id
or prompt content. A new workflow step, "Capture Claude permission-denial
diagnostics (issue #348)" (`id: denials`), runs immediately after "Run
Claude Code" with `always()` (so it runs on both success and failure,
whenever the Claude step itself was not skipped) and writes a durable
report to the run's `$GITHUB_STEP_SUMMARY`, plus two new
`steps.denials.outputs` (`denial_count`, `denial_summary`) that the
existing "Report missing deliverable" and "Report failure" comments (V1.2/
V1.7/V1.9.3) now embed directly in their issue comment when the count is
non-zero — so the *next* occurrence of this failure shape surfaces its
denied tool calls in a repo-visible issue comment, not only in the raw
Actions log.

**Honest limit on the underlying assumption.** This round had no network
access available to independently re-verify `execution_file`'s exact
existence/format against `anthropics/claude-code-action`'s own
documentation — the module's parsing logic is built from the well-known
Claude Code `tool_use`/`tool_result` message shape (confirmed indirectly,
in this very investigation, by a live `permission_denial` message
observed when this session's own web-search/web-fetch tools were denied:
`"Claude requested permissions to use <Tool>, but you haven't granted it
yet."` — the same phrasing pattern the module's regex matches), but is
**deliberately defensive**: a missing `execution_file` output, an empty
file, or an unexpected format never raises or fails the step — it only
ever yields a clear `available=false` / "unavailable" report. This can
never regress branch/push/deliverable/Draft/HO behavior, since the new
step reads only an already-produced file already on disk via the
workflow's own Python call (never through Claude's `--allowedTools`, no
new Bash permission), independent of every other gate. Whether
`execution_file` actually resolves to a usable log — and whether the
denial patterns this module looks for match this action's real output —
is proven or disproven by the *next* real occurrence, exactly like V1.9.3's
own honest-limit framing above.

**What this does not change.** No `--allowedTools` permission is
broadened; `--permission-mode acceptEdits` is unchanged;
`deliverable_guard.py`, `branch_setup_diagnosis.py` and the V1.9/V1.9.1/
V1.9.2/V1.9.3 changes-requested handoff chain are untouched — this is a
strictly additive observability step, scoped to run alongside them, never
gating any of their decisions. Per the issue's own instruction, issue #344
is **not** retried as part of this issue.

**Post-merge #344 retry instructions (per the issue's acceptance
criterion 5, corrected per Chief review on PR #349 blocker 3).** Live
issue #344 currently carries only `status:changes-requested` and
`area:app` — `agent:claude` was intentionally removed when #344 was
disarmed, so it is **not** already present, and no instruction here may
claim otherwise. Once this PR is Chief-reviewed and merged to `master`,
the safe re-arming order for #344 is:

1. Ensure/remove any conflicting lifecycle trigger first, so that adding
   the agent label by itself cannot trigger a run.
2. Add `agent:claude` to issue #344.
3. Only then (re-)apply `status:changes-requested` to issue #344, to
   retry PR #345 against its then-current head.

If the same failure shape
recurs, the new "Capture Claude permission-denial diagnostics" step will
either (a) surface the exact denied tool name(s)/input(s) in the "Report
missing deliverable"/"Report failure" comment and step summary — turning
this into a confirmed, actionable root cause for the first time — or (b)
report `available=false`, which itself is new, durable evidence that
`execution_file` is not the right signal and the diagnostic mechanism
needs a different data source, to be investigated in a follow-up issue.

Regression coverage:
[`tests/test_agent_bridge_permission_denial_diagnostics.py`](../../tests/test_agent_bridge_permission_denial_diagnostics.py)
— pure unit tests for `les_meldinger` (missing path, missing file, empty
file, JSON-array and JSONL formats, malformed lines skipped, unexpected
JSON shapes), `finn_tillatelses_avslag` (denial found with correct
tool/input, a clean `tool_result` produces no denial, an orphaned
`tool_use_id` falls back to "ukjent verktøy" rather than crashing, benign
text never matches), `formater_sammendrag`/`formater_markdown` (always
single-line for the comment-safe summary, truncation never raises), a CLI
contract suite proving `available`/`denial_count`/`denial_summary` are
always emitted and the step never fails regardless of input, and
`TestWorkflowWiring`, which inspects the workflow's own source text and
proves: the new step exists and calls the new script; it reads
`steps.claude.outputs.execution_file`; it runs with `always()`, not just
`success()`; no new `Bash(...)` rule was added to `--allowedTools` for it;
and the two report steps reference its `denial_count`/`denial_summary`
outputs.

## Round 1 also uses the Draft -> Ready lifecycle (V1, issue #62)

**The problem this fixes:** issue #44 (above) gave `status:changes-requested`
re-review a reliable wake-up via a real GitHub `ready_for_review` event.
`status:ready` (round 1) never went through that mechanism at all --
`gh pr create` opened the PR **Ready** immediately, so round 1's Chief
wake depended entirely on GitHub's `opened` PR event and the
Chief-ready comment marker (issue #32). Observed on issue #58 / PR #61:
the PR was created Ready, the `KBH_CHIEF_REVIEW_READY_V1` marker was
posted at 19:05, and no native Chief review appeared until the hourly
`Kvernhaug Approval Watch` fallback picked it up later -- i.e. the same
class of missed-wake risk issue #44 had already fixed for round 2+, just
never closed for round 1.

**The fix, chosen to be the smallest change that reuses issue #44's
already-proven mechanism instead of building a second one:** a fresh
`status:ready` PR is now opened as **Draft** --
`gh pr create --draft`, a one-word change to the `status:ready` branch
of the Claude prompt in `claude-agent-bridge.yml` (`Run Claude Code`
step) -- instead of Ready. Every other step in the Draft/Ready-for-review
pipeline (issue #44) is already trigger-label-agnostic about the
**mutation** itself: `pr_ready_handoff.py`'s ordinary transition path
only ever checks the PR's live `isDraft` flag, never the trigger label,
so a Draft round-1 PR flows through the exact same
deliverable-gate -> Chief-ready-marker -> refetch -> `gh pr ready`
sequence a changes-requested round already uses, producing a real
`ready_for_review` event for round 1 too. **No new workflow steps, no
new script module, and no `--allowedTools`/permission-model change**
were needed for this -- `gh pr create --draft` is just a different
argument to the already-allowed `Bash(gh pr create *)` rule.

`pr_draft_handoff.py` (the *pre-Claude* Draft conversion for an
*existing* PR) is intentionally untouched: it still only ever fires for
`status:changes-requested`, because a fresh `status:ready` run has no PR
to convert yet when that step runs -- Claude creates one, directly as
Draft, later in the same job. Its docstring is updated to explain the
new reason `status:ready` is out of its scope (issue #62), not to change
its behavior.

**Preserving fail-closed behavior (scope requirement 5) required one
substantive code change, not just a prompt tweak:** before this fix,
`pr_ready_handoff.py`'s "PR is already Ready (not Draft)" branch treated
*any* trigger label other than `status:changes-requested` as an
unconditionally safe `already_ready` no-op -- correct when round 1 could
never legitimately be Draft in the first place, but a **latent fail-open
gap** once round 1 also creates a Draft PR: if a round-1 PR were
externally/prematurely un-drafted before this gate ran, it would have
been silently accepted as "the safe round-1 case" without ever having
performed a real transition -- exactly the class of bug Chief's PR #45
review already fixed for `status:changes-requested` (requiring a
`KBH_PR_READY_TRANSITION_DONE_V1` proof marker), just left open for the
other label. The fix generalizes that same requirement to **every**
trigger label (`vurder_ready` in `pr_ready_handoff.py` no longer
branches on `trigger_label` for this check at all): "already Ready" is
now a safe idempotent no-op only when a `KBH_PR_READY_TRANSITION_DONE_V1`
marker proves this mechanism itself performed the transition for that
exact `(issue, head)` pair, regardless of which label triggered the run.
`trigger_label` remains in the function signature and the workflow's
JSON payload (unchanged wiring, no need to touch the "Refetch live state
for PR ready-for-review transition" step) but no longer gates this
decision.

**What was verified, and how (issue #62 scope item 6):**
- First-round PR: Draft -> Ready -> one review-ready signal/event path --
  `tests/test_agent_bridge_pr_ready_handoff.py`
  `TestRunde1BrukerSammeOvergangSomChangesRequested` (a Draft round-1 PR
  transitions normally) plus the `TestRunde1DraftPromptIssue62`
  workflow-source checks (`gh pr create --draft` present in the
  `status:ready` prompt branch, absent from the `status:changes-requested`
  branch, no new workflow steps, no `--allowedTools` expansion).
- Re-review path still works: every existing `TestChangesRequestedReadyFailOpen`
  / `TestVurderReadyFailClosed` / `TestVurderReadyGodkjenner` case is
  unchanged and still passes -- the changes-requested branch's own logic
  and its already-required proof marker were not touched.
- No duplicate transition on retries: the generalized "already Ready"
  check is exactly the existing `KBH_PR_READY_TRANSITION_DONE_V1`
  idempotency mechanism (issue #44/PR #45), now applied uniformly --
  `gh pr ready` is still never called twice for the same head, for
  either trigger label.
- No auto-merge or scope expansion: `TestRunde1DraftPromptIssue62.test_allowedtools_utvides_ikke`
  asserts the `--allowedTools` string is unchanged apart from `gh pr
  create`'s existing wildcard rule, and that no `gh pr merge`/`git
  merge`/`Write`/`Edit` rule was introduced; the pre-existing
  `TestWorkflowKildetekst` suite (unchanged) continues to assert no
  merge command anywhere in the new-to-issue-#44 steps this change
  reuses.

**Files changed:** `.github/workflows/claude-agent-bridge.yml` (the
`status:ready` prompt bullet, plus updated inline comments that had
described the pre-#62 "round 1 is always Ready" behavior as fact),
`.github/scripts/pr_ready_handoff.py` (`vurder_ready`'s "already Ready"
branch generalized, docstrings updated), `.github/scripts/pr_draft_handoff.py`
(docstring only), `tests/test_agent_bridge_pr_ready_handoff.py` (updated
+ new tests above), this document.

**Testability boundary, stated plainly, exactly as for every other
mechanism in this document:** the fail-closed decision logic and the
workflow's step wiring are unit- and source-tested without touching
GitHub. Whether a live round-1 PR created as Draft actually produces a
`ready_for_review` event the native Work task reliably wakes on -- the
entire premise of both this change and issue #44's -- can only be
confirmed by a real, controlled round-1 E2E on a live issue, the same
honest limit already noted for every prior Chief-ready signal iteration
above. Nothing in this change claims that E2E has already passed.

## Owner GO/NO-GO notification (V1, issue #66)

**The problem this fixes:** the "Work-side Chief task" section above
already documents that, on a Chief PASS, the native Work task
"separately notifies the owner with a GO/NO-GO prompt" -- but issue #66
recorded a concrete case where the lifecycle machinery worked exactly
as designed (issue #59 / PR #64 reached exact-head Chief `APPROVED` on
2026-09-04, `status:approved` applied correctly) and the owner still
received no clear, user-facing "GO?" prompt. This is the same class of
gap already fixed once before for the *Chief review* wake path (issues
#32/#40/#44: a notification that exists only on an external, un-
inspectable SaaS surface is not reliable enough alone) -- here it
recurs one step later, for the *owner's own* merge decision.

**The fix, deliberately reusing the same shape as the Chief-ready
signal instead of inventing a new mechanism:** a second, independent
repo-side notification, entirely additive to everything above --
`guard`/`execute` (the Claude-invoking path) are completely untouched,
and so is the existing hourly `Kvernhaug Approval Watch` and the
event-Chief task itself (requirement 6). Two new jobs in
`claude-agent-bridge.yml`, gated on the **same** `issues: labeled`
trigger this workflow already listens to, but for a **different**
label:

1. **`notify_guard`** decides whether a `status:approved` labeling
   event is authorized to wake the notify path at all --
   [`.github/scripts/approved_notify_guard.py`](../../.github/scripts/approved_notify_guard.py)
   (`vurder_notify_trigger`, unit-tested in
   [`tests/test_agent_bridge_approved_notify_guard.py`](../../tests/test_agent_bridge_approved_notify_guard.py))
   is a **deliberately duplicated**, single-label sibling of
   `trigger_guard.py` -- same event-time-plus-live authorization
   discipline (issue #9/V1.1: `agent:claude` must have been present in
   the *triggering event's own* label snapshot, not just live), same
   owner-only/non-Bot actor guard, same anti-loop reasoning (every
   label mutation this workflow itself makes uses its own token/actor,
   never the owner's login, so it can never satisfy this check and
   re-trigger itself). It is **not** a reuse of `trigger_guard.py`
   itself: that module's `TRIGGER_ETIKETTER` also gates the
   Claude-invoking `execute` job, and adding `status:approved` to it
   would have made an approval event start a Claude run -- exactly what
   this feature must never do (requirement 8, "No product changes").
2. **`notify`** (`needs: notify_guard`) runs only when the guard above
   authorized it. It refetches **live** issue labels, the single open
   PR on the issue's deterministic branch (`agent/issue-<N>`, same
   `branch_policy.py` formula every other job already uses), that PR's
   live reviews, and the issue's own existing comments -- never
   anything cached from before this job started, the same "Ordering /
   race safety" discipline as `chief_ready_signal.py`. The decision
   itself is one pure, dependency-free function,
   [`.github/scripts/go_notify_signal.py`](../../.github/scripts/go_notify_signal.py)
   (`vurder_go_notify`, unit-tested in
   [`tests/test_agent_bridge_go_notify_signal.py`](../../tests/test_agent_bridge_go_notify_signal.py)).

**Before presenting GO readiness (issue #66, requirement 3), all of the
following must hold on that fresh refetch -- fail-closed on any
ambiguity, exactly like every other decision module in this document:**

- The PR is open **and unmerged** -- GitHub's own `OPEN`/`CLOSED`/
  `MERGED` PR states are mutually exclusive, so requiring `state ==
  "OPEN"` on the exactly-one PR found on the deterministic branch
  proves both halves of this requirement in one check.
- The PR's **live** head SHA (`headRefOid`), not anything captured
  earlier in any other job.
- A formal GitHub review with state `APPROVED` exists for **that exact
  head** -- the same `commit.oid`-anchored check `pr_ready_handoff.py`
  already uses for its own CHANGES_REQUESTED/APPROVED detection, so an
  approval left over from an older head (superseded by a later push)
  never counts.
- The issue carries `status:approved` as its **sole** lifecycle label
  on refetch (the same `LIVSSYKLUS_ETIKETTER` exclusivity check every
  other signal module in this document performs).
- **No unresolved manual gate** -- this repository defines no manual
  "blocking" label or mechanism beyond the lifecycle labels themselves,
  so the exclusivity check above **is** the entirety of this
  requirement; stated explicitly here (rather than left implicit) so a
  future manual-gate mechanism cannot silently bypass this notification
  without a documentation update catching it.

**Idempotency / staleness (requirements 4 and 5):** the notification is
a single **issue** comment (not a PR comment -- this is an owner-facing
notice, and every other owner-facing Bridge message in this workflow
already posts to the issue, which is also where the lifecycle state
itself lives) containing a reserved, line-anchored marker:

```
KBH_GO_READY_V1 issue=<N> head=<40-char-sha>
```

`go_notify_signal.py` searches the issue's own existing comments for an
*exact* match of this marker for the same `(issue, head)` pair before
posting -- a duplicate is a no-op, not an error (mirroring
`chief_ready_signal.py`'s idempotency exactly). A **new** head (the PR
picked up a further round after the notification already fired -- e.g.
a subsequent `status:changes-requested`/re-approval cycle) is
deliberately **not** treated as a duplicate: the old GO readiness is
implicitly stale (a different head can never match the old marker's
`head=` value), so a fresh notification is posted for the new head
without any separate "staleness" bookkeeping being required.

**Failure semantics:** a fail-closed rejection (`post=false` and
`duplicate=false` -- e.g. no `APPROVED` review yet exists for the exact
live head) exits the "Decide GO/NO-GO notification" step non-zero, so a
dedicated report step posts a clear comment on the issue explaining why
no notification was sent, rather than the job finishing green with
neither a notification nor a report -- the same exit-code contract as
`chief_ready_signal.py`/`pr_ready_handoff.py`. No label is ever changed
and nothing is ever merged by this path.

**What this notification is (and is not):** exactly like the
Chief-ready marker, it is a wake-up/prompt **only** -- never
authoritative and never a merge action. `gh pr merge`/`git merge` do
not appear anywhere in the `notify_guard`/`notify` jobs (regression
coverage:
[`tests/test_agent_bridge_go_notify_workflow.py`](../../tests/test_agent_bridge_go_notify_workflow.py)),
and neither job invokes `anthropics/claude-code-action` or touches
`--allowedTools` -- no new Claude trigger surface is introduced by this
feature at all. The existing hourly `Kvernhaug Approval Watch` and the
event-Chief task remain completely unchanged and are the fallback paths
if this notification is ever missed.

**Testability boundary, stated plainly, exactly as for every other
mechanism in this document:** the fail-closed decision logic and the
guard's authorization logic are unit-tested without touching GitHub,
and the workflow's own source text is checked for the wiring
guarantees above (new jobs present and correctly gated, independent of
`guard`/`execute`, no new Claude trigger surface, no merge command).
Whether a live `status:approved` labeling event actually produces a
visible, timely issue comment in practice can only be confirmed by a
real, controlled E2E on a live issue -- the same honest limit already
noted for every prior signal/transition mechanism in this document.
Nothing in this change claims that E2E has already passed.

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

## HO policy — local and GitHub jobs

This is the single HO maintenance policy for local Claude jobs and both
Bridge trigger paths. `CLAUDE.md` and the Bridge prompt reference this
section; do not copy a second policy into individual prompts. It governs
operational handover only, not product scope, merge/deploy authorization,
or the existing deliverable/Chief-review gates.

### Canonical structure and compatibility

Read [#152](https://github.com/Joludvig/kvernhaug-brygghus/issues/152)
**and its comments**, not just its body. The existing
[HO ROUTER CONTRACT V1](https://github.com/Joludvig/kvernhaug-brygghus/issues/152#issuecomment-5615617899)
is already the routing contract; this policy does not introduce a format.

- Preserve `<!-- KBH_HO_STATIC_START -->` / `<!-- KBH_HO_STATIC_END -->`
  and their content. Never change STATIC, curated governance, charters or
  contracts without explicit authorization for that change and the
  underlying versioned decision. Routine HO maintenance is no such grant.
- Preserve `<!-- KBH_HO_AUTO_START -->` / `<!-- KBH_HO_AUTO_END -->`.
  The body AUTO block is a legacy operational snapshot. Under the router
  contract, advance the routed ROLLING checkpoint, **not the body as well**.
  No routine job rewrites the body, its timestamps or its maintenance text.
- Read all #152 comments and select the newest valid standalone line
  `KBH_COS_CHECKPOINT_PTR_V1 issue=<positive integer> comment=<positive integer>`.
  Fetch that exact comment on that issue in this repository and require
  the standalone marker `KBH_COS_LIVE_CHECKPOINT_V1`. Quoted examples and
  unmarked status comments are not replacement pointers. A missing,
  inaccessible or ambiguous route means defer the write and report the
  problem; never silently fall back to writing the old AUTO block.
- Read the checkpoint, then refresh live master, relevant issues/labels,
  PR heads, reviews/checks, merge state and production evidence. Precedence:
  live evidence > routed checkpoint > stale operational body/comments.
  Newer unmarked comments may contain evidence or unresolved gates to
  reconcile with live state; do not discard them or promote them merely
  because they are newer. Snapshot age alone proves nothing about freshness.

### One writer, final post-verification step

1. Establish one repository-wide HO writer at a time before publishing:
   the executing local Claude or Bridge Claude, never both. Record the
   current writer in the existing task/control issue or task assignment;
   a WIP exception allowing parallel implementation does not allow parallel
   HO writes. Prep/read lanes and the Chief consume/report evidence; they do
   not duplicate that job's HO write. A later verified review, merge or
   deploy is a new material event, handled serially under this same policy.
   If another local job, Bridge run or legacy scheduled HO updater owns
   the writer role, or ownership cannot be established, defer to it in
   the existing task report. Per-issue Bridge concurrency does **not**
   serialize #152 across issues or local sessions; a fresh read is not a
   lock. Do not publish concurrently or add a second writer/workflow/hook.
2. Finish the bounded work and required verification first, including
   reading the latest applicable review/check results. After any authorized
   commit/push/PR delivery, refetch the actual issue/PR/head. HO maintenance
   is the job's **last state-changing task step before its final report**.
   At a blocked stop, finish available verification and record only the
   verified blocker, never success. Missing CI, Chief review, owner-PC or
   production checks stay explicitly pending.
   For Bridge Claude, the wrapper's independent deliverable check,
   `status:review`, Chief-ready signal and Draft-to-Ready transition occur
   **after** the Claude step: record them as pending, not completed or
   approved. The wrapper remains their sole owner and does not write HO.
3. Compare substantive operational truth with the current checkpoint.
   Write only if a fresh Chief's next action or understanding materially
   changes: completed bounded work, authoritative implementation/review
   state, an active lane, blocker, dependency, owner gate, parking decision
   or next step. No write for a rerun, timestamp refresh, rewording or facts
   already represented. HO maintenance itself is not another material event.
4. Prepare a compact **replacement snapshot**, using the existing checkpoint
   marker. Replace stale transient facts; do not append a run log, duplicate
   task reports or carry superseded statuses forward. Retain every unresolved
   gate, dependency and deliberately parked item, including other lanes;
   remove one only with explicit resolution evidence. Unknown is not resolved.
   Include what is done, current authoritative state, blockers/gates and next
   steps, with exact issue/PR references and full relevant SHAs. Distinguish
   PR head, master/merge SHA and production/release SHA. Uncommitted local
   work must be described as uncommitted, not implemented on master.
   For Web, **MERGED is not DEPLOYED/LIVE**: retain the last evidenced
   production revision (or unknown) until explicit owner FTP, independent
   byte verification and live smoke support the same release SHA. Link that
   evidence; CI, local browser checks and deploy-harness changes do not prove
   production. Never close/relabel/merge/deploy/start work to tidy HO.
5. Immediately before publication, refetch the route, target and affected
   live facts. If they changed, reconcile and repeat the material-change
   check; if writer ownership is uncertain, defer. Publish the replacement
   checkpoint on the existing operative issue or the bounded task issue,
   read it back, then append the existing standalone pointer line to #152
   using the **returned comment ID**. Read back #152 and resolve the new
   pointer to verify publication. Historical comments stay for audit;
   the new pointer replaces the active snapshot, not its retained gates.
   Never post a pointer before its target exists or append history to the
   active snapshot. Use existing `gh issue view` / `gh issue comment`
   capabilities (or equivalent authorized tools); no broader permission is
   granted here. On retry/uncertain response, refetch first: reuse an already
   published equivalent checkpoint, repair only a missing pointer if still
   current, and do nothing if already routed. A partial/failed publication
   must be reported; do not blindly post duplicates or overwrite newer work.
   **(V1.6, issue #252) "Read back #152 and resolve the new pointer to
   verify publication" is now a concrete, fail-closed check, not prose
   alone:** after appending the pointer, run
   `python3 .github/scripts/ho_router_check.py verify` with fresh #152
   comments as `pointer_comments`, the checkpoint issue's fresh comments
   as `target_comments`, and its number as `target_issue`. Only treat
   publication as verified on exit 0 / `status=OK`. Any other status
   (`ORPHAN`, `NO_POINTER`, `INVALID_TARGET`, `POINTER_ISSUE_MISMATCH`)
   means the publish did not verifiably land — report it as a
   failed/deferred publication per step 6, never as success. See "HO
   router freshness check (V1.6, issue #252)" above.
6. Final report: `HO UPDATED: YES` only after read-back confirms the routed
   checkpoint **and** (V1.6) `ho_router_check.py verify` exited 0 with
   `status=OK`, plus its link and one sentence describing the change.
   Otherwise `HO UPDATED: NO` with the reason: no material change, another
   writer, missing access/route, orphaned/unverified pointer, or
   failed/deferred publication. Include any pending material delta in the
   existing task report for the designated writer; do not create a
   competing handover file/comment format.

### Migration and rollout

Older instructions to "update HO/AUTO", "refresh #152", "append a handover"
or "always update HO when done" invoke the material-change check and the
existing router above, not an unconditional body rewrite or extra writer.
Instructions to wait until a chat is full do not postpone a material change.
Legacy Vault handovers, `PROJECT_STATUS_*`, snapshots and chat summaries
remain reference/history under their own scope; do not mirror operational
HO into them. Durable decision promotion remains deliberate, separately
authorized work; it is not permission to edit STATIC in this final step.
An explicit task-specific prohibition on HO writes still applies: report
the delta and defer. Do not reinterpret a legacy task to expand its scope.

**Owner rollout gate before merge/activation:** confirm that any external
ChatGPT/Chief scheduled HO writer or old prompt that rewrites #152 has been
disabled or made read-only for HO, and assign the single writer across all
lanes. Repo inspection cannot prove external scheduler state. Already-running
jobs retain their starting instructions: let them finish or stop them before
switching writers; a merge does not update an in-flight prompt. Review the
first material update through target + pointer read-back before wider use.
No schema migration, marker rename, historical-comment deletion, trigger,
permission expansion, extra Claude invocation or scheduler is needed.
This HO/workflow change is outside #199's optional docs-merge-preauthorized
pilot; normal exact-head Chief review and the applicable owner merge gate
still apply. Do not modify live #152 merely to announce this policy change.

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

`queue:pa-jobb` and `queue:priority` (issue #260, see "PÅ JOBB
sequential queue" above) follow the same non-destructive `gh label
create` pattern, but were **not** created by this PR itself — Bridge
Claude's own `--allowedTools` set (see above) does not include `gh
label create`/`gh label list`, by the same defense-in-depth principle
as every other command deliberately left off that list. The owner (or
Chief, via the connected identity) must run, once:
```
gh label create "queue:pa-jobb" --color 0E8A16 --description "PÅ JOBB queue item (issue #260)"
gh label create "queue:priority" --color 5319E7 --description "PÅ JOBB queue reorder: move to front (issue #260)"
```
before either label can be applied to an issue — GitHub's label-set API
rejects a name that doesn't already exist as a label object in the
repository. Until then, `pa-jobb-queue.yml` still runs safely on every
trigger; it simply always finds an empty queue (`gh issue list --label
queue:pa-jobb` returns nothing for a label that doesn't exist yet) and
takes no action.

## What this document does not do

- Does not add an OpenAI API bot, custom server, MCP broker, A2A
  server, Sóti runtime, or any other agent backend — the Chief/ChatGPT
  side of the bridge is configured separately, through supported
  ChatGPT/connected-GitHub capabilities, outside this repository.
- Does not change what a Chief review actually checks, nor any
  App/Web/Core product behavior.
- Does not implement automatic merging, ever.
- Does not replace GitHub as the audit trail.
