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
| `status:review` | Workflow (automatic, only on success) | Claude's run finished; a PR exists and is ready for Chief review. |
| `status:changes-requested` | Owner (after reading a Chief review) | Trigger Claude again to address *only* that review's CHANGES REQUESTED points. |
| `status:approved` | Owner (after a Chief PASS) | Signals the PR is approved. **Never auto-merged** — merge is always a separate, manual owner action. |
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
- **The owner** must follow the same rule manually for the two
  owner-driven transitions: applying `status:changes-requested` should
  *replace* `status:review`, and applying `status:approved` after a
  Chief PASS should *replace* `status:review` — not simply be added
  alongside it. (The workflow normalizes whatever it finds at the start
  of its next run, but between runs the labels are only as clean as the
  owner leaves them.)

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
