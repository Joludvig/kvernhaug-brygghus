---
name: release-checkpoint
description: Run the Kvernhaug Brygghus end-of-round checkpoint procedure - full validation, optional Project Snapshot, and the structured sluttrapport - before a commit is proposed. Use when the user asks for a checkpoint, a milestone snapshot, or to wrap up a round before committing. Not for routine intermediate progress updates mid-task.
---

# Release checkpoint

Encodes WORKFLOW.md's Fase 8-10 as one procedure, so it doesn't need to be
re-derived from prose every time. Full phase detail:
[WORKFLOW.md](../../../docs/development/WORKFLOW.md).

## 1. Full validation (always, regardless of scope)

- Full Python suite: `py -3 -m unittest discover -s tests -b` — required at
  every checkpoint, even for a web/-only round (per
  [`.claude/rules/testing.md`](../../rules/testing.md), intermediate rounds
  can skip this, but the final checkpoint never does).
- If the round touched `web/**`: run the `web-full-regression` skill.
- `git status --short` and `git diff --stat` — confirm the diff only
  contains intended files, nothing unrelated bundled in.

## 2. Project Snapshot — ask first, don't assume

Only propose a snapshot for: a new major module, an architecture change, a
major milestone, or an explicit user request. If one of those applies:
**stop and ask the user before creating it** — do not proceed with the
snapshot or the rest of checkpoint until they answer.

If confirmed: copy `docs/snapshots/TEMPLATE.md` to
`docs/snapshots/YYYY-MM-DD_<short-slug>.md`, fill every field with
freshly-verified information (re-run the test suite, check git status
directly — never reuse old numbers uncritically), add the row to
`docs/snapshots/README.md`'s chronological index. Never edit an existing
snapshot afterward — a new need means a new snapshot.

## 3. Documentation sync

Check (update only what's actually affected, explain what wasn't):
`README.md`, `docs/ROADMAP.md`, newest `docs/PROJECT_STATUS_*.md`,
`docs/MASTER_DATA_FLOW.md` (only if scraper/masterdata dataflow changed),
`web/README.md` (only if `web/**` architecture changed — round-by-round
narrative goes in `web/CHANGELOG.md`, not README).

## 4. Git — never commit/push automatically

Show changed files, why, and a proposed commit message. Wait for explicit
approval. Never `--amend`, never `--no-verify`, never `git add -A`. See the
always-loaded rules in [`CLAUDE.md`](../../../CLAUDE.md) for the protected
file list.

## 5. Sluttrapport format

```markdown
# Oppsummering

Hva ble gjort? Hva ble forbedret? Hva påvirkes?

Ble dokumentasjon oppdatert?
Ble tester kjørt?
Ble teknisk gjeld redusert?

Anbefales backup/snapshot?
Er prosjektet klart for commit?
Er prosjektet klart for push?

Eventuelle anbefalinger.
```
