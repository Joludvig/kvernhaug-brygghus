# Kvernhaug GitHub-first CoS Protocol

**Status:** Active proposal for review  
**Scope:** All Kvernhaug Chief-of-Staff chats  
**Purpose:** Prevent stale chat status from becoming project truth.

## 1. Core rule

Before a Kvernhaug CoS reports project status, roadmap, next step, completion state, merge state, deployment state, or an implementation fact that may have changed, it must refresh from GitHub.

Chat memory is useful context, but it is not authoritative when fresher repository evidence exists.

## 2. Authority by question

Use the source that owns the question:

1. **Architecture / semantics / ownership:** active governing contracts, locked charters, and explicit owner decisions.
2. **What is implemented:** current GitHub `master`.
3. **What is being worked on:** open GitHub Issues and their lifecycle/area labels.
4. **What change is proposed, tested, reviewed, or approved:** Pull Requests, exact PR head SHA, reviews, checks, and test reports.
5. **What is actually merged:** merged PR state plus resulting commit on `master`.
6. **Manual operational state not inferable from Git:** track it as a GitHub Issue and require explicit owner confirmation before closing it.
7. **Chat memory / previous CoS summaries:** context only; supersede when inconsistent with the sources above.

Do not silently blend an old chat status with newer GitHub evidence. State that the old status is stale/superseded and replace it.

## 3. Mandatory CoS refresh

Before giving a status or next-step answer, a CoS should inspect at minimum:

- current `master` HEAD;
- relevant open Issues for its project/area;
- lifecycle labels on active issues (`status:*` where used);
- relevant recent/open PRs and their exact head/merge state;
- governing contract/docs when the answer depends on architecture or wire semantics;
- any open manual-operation issue that can make `merged` differ from `live/deployed`.

For an active PR review, always re-fetch the PR immediately before consequential review/merge actions and anchor decisions to the exact current head SHA.

## 4. Existing area routing

Use the current repository labels where applicable:

- `area:core` — Core contracts, schemas, shared semantics, interoperability.
- `area:app` — Streamlit App (`app.py`, `modules/`, `ui/`) implementation/workflow.
- `area:web` — browser/static Web implementation and deployment-related Web work.
- `area:infra` — repository, tests, Agent Bridge, workflow/governance infrastructure.

An issue may legitimately have more than one area label when ownership crosses a contract/product boundary. Do not create extra labels just to mirror every chat unless there is actual repository work that benefits from them.

## 5. Lifecycle and Agent Bridge

The Agent Bridge lifecycle is defined in `docs/development/AGENT_WORKFLOW.md` and must not be duplicated or reinterpreted here.

For Chief review, the practical rule remains:

`status:review` -> Chief review of exact PR/head -> `status:approved` only after PASS -> explicit OWNER GO/NO-GO -> merge.

A PR review action alone is not assumed to update the Issue lifecycle label. Verify both separately.

## 6. Critical Web rule

**GitHub MERGED != Web DEPLOYED.**

For Kvernhaug Web, a merged Web change is not considered live until the required owner-side PC deployment/update step has been explicitly confirmed.

Therefore a CoS must distinguish at least:

- `MERGED` — code is on `master`;
- `DEPLOY PENDING` — merged, but owner PC deployment is not confirmed;
- `DEPLOYED / LIVE` — owner has confirmed the PC deployment/update completed.

Never infer `DEPLOYED` from a merged PR alone.

Manual deployment obligations should be represented by an open GitHub Issue (normally `area:web`) and closed only after owner confirmation.

## 7. No duplicate status ledgers

Do not create per-CoS static status files that repeat information already available from Git history, Issues, labels, or PRs.

If a fact cannot be derived from GitHub state — for example a manual PC deployment, an external dependency, or an explicit owner gate — track that fact as a small GitHub Issue instead of maintaining another parallel status document.

This protocol is the shared lookup rule; GitHub objects remain the live status data.

## 8. Cross-CoS handoff behavior

When one CoS hands work to another:

- link/reference the relevant Issue/PR rather than copying a large mutable status narrative;
- identify any locked owner decision or contract that constrains the work;
- identify manual gates that are still open;
- let the receiving CoS re-fetch GitHub rather than trusting the handoff as a permanent snapshot.

The receiving CoS should treat a handoff as a pointer to evidence, not as a substitute for checking the evidence.

## 9. Compact user trigger

The owner may use this command in any Kvernhaug CoS chat:

> **Sjekk GitHub og oppdater statusen din.**

Expected behavior:

1. Refresh the relevant repository state.
2. Compare it with the CoS's current remembered status.
3. Explicitly supersede stale information.
4. Report current status, open gates, and next step from fresh evidence.
5. Do not mutate or merge anything unless the owner separately authorizes that action.

## 10. Default conflict rule

If sources disagree:

- implementation state follows GitHub `master` / PR state;
- architecture and field semantics follow the active governing contract / locked owner decision;
- deployment/live state follows explicit operational confirmation;
- unresolved contradictions are surfaced for Chief/owner review, not guessed away.

This protocol does not give any CoS authority to rewrite contracts, migrate user data, broaden scope, or merge without the established owner gate.
