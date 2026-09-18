# Web release checklist — freeze `7aa076a` for Astra Audit #3

*Release-prep record only (issue #232). Does not change product code or
deployment scripts. No deploy performed here — deploy is always an
owner-PC, manual action per [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) and
[../../scripts/deploy_web.ps1](../../scripts/deploy_web.ps1).*

```
RELEASE_SHA=7aa076a2210e4bf745f5c814db2ea924797b4227
```

## 1. Verification performed for this release-prep round

- **SHA identity**: `7aa076a2210e4bf745f5c814db2ea924797b4227` is an
  existing commit and is exactly `origin/master`'s current HEAD (Merge PR
  #231, "combobox listbox Tab-order fix", on top of Merge PR #229,
  "help-method-card anchor scroll-margin fix"). Confirmed via
  `git rev-parse origin/master` after a fresh `git fetch origin`.
- **`web/` diff vs. last verified production release**
  (`cedff7c6f9e13ea72015600f96cb361829ee499f`): exactly two files, seven
  lines total —
  - `web/css/style.css` (+1 line): `scroll-margin-top` added to
    `.hjelp-metode-kort` (issue #188 / PR #229).
  - `web/js/combobox.js` (+6 lines): explicit `tabindex="-1"` authored on
    the combobox listbox (issue #230 / PR #231).
  No other `web/` file drifted between the two SHAs — this is exactly the
  two known post-Audit-2 fixes named in the issue, nothing else.
- **Blockers**: none found. The existing `-ReleaseSha` flag on
  `scripts/deploy_web.ps1` (issue #223, Production Workflow V2 #199) is
  built for precisely this scenario (deploy an already-merged, frozen
  commit even after `master` has moved further — it hasn't here, but the
  mechanism doesn't require equality with current `origin/master`, only
  ancestry). No script change is needed or made.

## 2. Owner-PC command sequence

Run from a location that already has a clone of this repo (any existing
checkout — the worktree below is created *from* it, not in place of it).

### 2a. Dedicated release worktree pinned to the frozen SHA

```powershell
git fetch origin master
git worktree add ..\kvernhaug-brygghus-release-7aa076a 7aa076a2210e4bf745f5c814db2ea924797b4227
cd ..\kvernhaug-brygghus-release-7aa076a

# Must print exactly 7aa076a2210e4bf745f5c814db2ea924797b4227:
git rev-parse HEAD

# Must be clean (deploy_web.ps1's own web/-cleanliness guard, issue #72,
# will otherwise refuse to run regardless):
git status
```

### 2b. Preflight (dry run, no network/FTP)

```powershell
.\scripts\deploy_web.ps1 -ReleaseSha "7aa076a2210e4bf745f5c814db2ea924797b4227" -DryRun
```

Confirms the file list and guard state without any FTP/HTTPS call. Expect
the guard messages to report the worktree HEAD matches `-ReleaseSha`; the
ancestor-of-`origin/master` check itself is *not* verified fresh under
`-DryRun` (documented limitation of the flag, unchanged by this release) —
run the real deploy below for the fully fresh guard.

### 2c. Real deploy

```powershell
.\scripts\deploy_web.ps1 -ReleaseSha "7aa076a2210e4bf745f5c814db2ea924797b4227"
```

Prompts interactively for FTP credentials (never store/pass them
non-interactively). This single invocation already performs, in order:
login preflight, a delta-check against current production (expected to
upload only `web/css/style.css` and `web/js/combobox.js` — everything
else on production should already byte-match this `RELEASE_SHA`), the
batched FTPS upload, and — with no extra command needed — the
byte-for-byte SHA-256 re-download-and-compare verification of **every**
deployed file over HTTPS (`INNHOLDSVERIFISERING`, built into the script).
There is no separate byte-verification script to invoke.

### 2d. Byte-for-byte verification

Already covered by step 2c — the script's own post-upload step does this
for every deployed file. No additional command is needed or exists for
this repo. Confirm the script's final summary reports all files verified
`ok` (no `mismatch`/`unverifiable` entries) before proceeding.

## 3. Bounded live-smoke plan (NO/EN + #188 + #230)

Smallest set that exercises both fixes on both languages, four checks
total:

| # | Fix | Language | URL | What to check |
|---|---|---|---|---|
| 1 | #188 (scroll-margin) | NO | `https://kvernhaugbrygghus.no/hjelp/bryggemetoder.html#biab` | Loading the URL directly (or clicking an in-page anchor link to `#biab`) scrolls the "BIAB" `.hjelp-metode-kort` card fully below the sticky compact-nav header — no part of the card hidden underneath it. |
| 2 | #188 (scroll-margin) | EN | `https://kvernhaugbrygghus.no/en/hjelp/bryggemetoder.html#biab` | Same check, English page (identical filename under `en/hjelp/`). |
| 3 | #230 (combobox Tab order) | NO | `https://kvernhaugbrygghus.no/` (malt/humle combobox) or `https://kvernhaugbrygghus.no/pantry.html` | Open the combobox listbox (type to filter), then press `Tab` from the input — focus must move directly to the next real control on the page, never landing on the listbox itself. |
| 4 | #230 (combobox Tab order) | EN | `https://kvernhaugbrygghus.no/en/` or `https://kvernhaugbrygghus.no/en/pantry.html` | Same check, English page. |

Automated equivalents already exist and passed pre-merge against the PR
head (not against production — per `.claude/rules/testing.md` the
Playwright gate always serves the checked-out head locally):
`tests/playwright/09-b11-metode-kort-scroll-margin.spec.js` (#188) and
`tests/playwright/10-a2-04-combobox-tab-order.spec.js` (#230). The four
manual checks above are what actually proves the *deployed* production
bytes behave the same way — `MERGED != DEPLOYED` (see
[web/README.md](../../web/README.md) "Web Release Batch") until this
live-smoke plan is run and passes.

## 4. Evidence needed before Astra Audit #3

- [ ] Step 2a–2c run to completion on the owner PC, from a worktree whose
      `git rev-parse HEAD` was confirmed to equal `7aa076a2210e4bf745f5c814db2ea924797b4227`.
- [ ] `deploy_web.ps1`'s own final verification summary: all uploaded/
      checked files `ok`, zero `mismatch`/`unverifiable`.
- [ ] All four live-smoke checks in section 3 passed against
      `https://kvernhaugbrygghus.no`.
- [ ] No other production regression observed incidentally during the
      smoke pass.

With all four boxes checked, this `RELEASE_SHA` is verified live and
ready to cite as evidence for Astra Audit #3.
