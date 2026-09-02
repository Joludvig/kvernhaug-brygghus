# Agent Bridge V1.2 — Live E2E Validation Record

*Audit record only. Does not change bridge behavior, App/Web/Core
product behavior, or any locked contract. See
[AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) for the full state machine and
permission model this record validates.*

## Purpose

Second real end-to-end validation of the Kvernhaug Agent Bridge, run
after the V1.2 fail-closed fixes from PR #13 (deliverable verification
gate, deterministic branch naming, exact-match push permissions). This
record documents that the full automated bridge path — label trigger
through to an open, reviewable PR — was exercised live against a real
GitHub repository and real GitHub Actions run, not merely covered by
unit tests.

## Issue

This validation is tracked entirely on **issue #14**
(`INFRA TEST — Agent Bridge V1.2 live E2E validation`). The issue body
is this run's task specification; this document is that task's sole
deliverable, as instructed.

## Trigger

The run was triggered through **Agent Bridge V1.2** — the `status:ready`
label applied by the repository owner, guarded by
[`trigger_guard.py`](../../.github/scripts/trigger_guard.py) (atomic
`agent:claude` + trigger-label authorization, live re-check, owner-only
actor check).

An earlier attempt at this same issue failed closed: the "Run Claude
Code" step succeeded, but file-write access inside the workspace was
denied, so no file was ever created and no PR was opened — exactly the
fail-closed behavior the deliverable gate is designed to produce on a
missing deliverable. That gap was root-caused and fixed separately as
Agent Bridge V1.3 (PR #16, `--permission-mode acceptEdits` — see
[AGENT_WORKFLOW.md](AGENT_WORKFLOW.md#permission-model-bash-allowlist--acceptedits-v13-issue-15)).
This document is produced by the retry run against issue #14 after that
fix landed on `master`, confirming workspace file edits now succeed
while every V1.2 fail-closed control (Bash allowlist, deterministic
branch, deliverable gate) remains in force unchanged.

## Expected lifecycle

```
status:ready -> status:working -> status:review
```

- `status:ready` (owner-applied) authorizes and starts this run.
- The workflow's first mutating step flips the issue to `status:working`
  immediately, before any Claude execution.
- On a successful run **and** a passed deliverable-verification gate
  (an open PR against `master`, on this issue's fixed branch, with a
  non-empty diff), the workflow moves the issue to `status:review`.
- `status:approved` and merge are separate, later, owner-only actions
  and are out of scope for this record.

## Branch

Per "Branch naming is deterministic and enforced"
([AGENT_WORKFLOW.md](AGENT_WORKFLOW.md#branch-naming-is-deterministic-and-enforced-chief-review-pr-13)),
this issue's entire lifecycle uses one fixed, deterministic branch name,
computed once from the issue number: **`agent/issue-14`**. Both this
run's push (`git push -u origin agent/issue-14`) and the deliverable
gate's PR lookup (`gh pr list --head agent/issue-14 --base master`) use
this exact string — never restated or recomputed — so a master-push
refspec or a different branch can never satisfy either check.

## Owner merge gate

`status:approved` is a **label**, not a merge. This run does not call
`gh pr merge`, does not push to `master`, and does not merge anything.
Merge to `master` remains a separate, explicit, manual action the
repository owner takes themselves, outside this automation entirely —
unchanged by this validation.

## Secrets and tokens

This record contains no secrets, tokens, or credential values, and
none are required to read or reproduce it. Credential configuration
(`CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY`) is documented, without
values, in [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md#required-secrets-and-apps).

## Scope

Infra/docs only. No App/Web/Core product behavior is touched by this
run; this file is the only change.
