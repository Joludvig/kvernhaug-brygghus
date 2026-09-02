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
2. The issue **currently** carries `agent:claude` (re-checked live via
   `gh issue view`, not just trusted from the webhook payload).
3. The label was applied by the repository owner
   (`github.event.sender.login == github.repository_owner`), not a
   bot or any other actor.

If any of these fail, the workflow's `guard` job exits cleanly with no
side effects (no label changes, no Claude invocation, no comment).

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
secrets). The workflow is a complete, reviewable scaffold; it will
fail fast with a clear comment on the issue (rather than a cryptic
Actions error) if triggered before these are set up, and will leave
the triggering label in place so the run can simply be retried once
configured.

To make this live, the **owner** must, in the GitHub UI (none of this
is something Claude or this workflow can do on its own — both require
interactive, owner-authenticated consent):

1. **Install the official Claude GitHub App** — <https://github.com/apps/claude>
   — on this repository. This is what lets `anthropics/claude-code-action`
   comment, push, and open PRs as the `claude[bot]` identity.
2. **Add exactly one** of the following as a repository secret
   (Settings → Secrets and variables → Actions → New repository secret)
   — **this is a cost/product decision for the owner, not something
   this PR decides**:
   - `ANTHROPIC_API_KEY` — an Anthropic API key (`sk-ant-...`),
     billed per-token via the API. Simplest, most direct option.
   - `CLAUDE_CODE_OAUTH_TOKEN` — a token from `claude setup-token`,
     for owners with an existing Claude Pro/Max subscription (uses
     subscription usage instead of separate API billing).

   (A third option, Workload Identity Federation — no static key at
   all, short-lived tokens exchanged via GitHub's OIDC — exists for
   later hardening but requires additional Anthropic Console
   configuration; out of scope for V1's scaffold.)

Nothing in this PR contains, invents, or requires committing an actual
secret value.

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
