"""
scripts/deploy_web.ps1 -- regresjonstester for frossen release-SHA-modus
(-ReleaseSha), issue #223 (Production Workflow V2 #199 adopsjonssteg 7).

BAKGRUNN: #199 krever at 2-4 fullførte LOW/MEDIUM Web-fikser normalt samles
i én release/deploy/live-smoke-syklus, og at predeploy, FTP-opplasting,
innholdsverifisering og live-smoke ALLE refererer til ÉN eksplisitt frosset
`RELEASE_SHA`, selv om `master` beveger seg videre etterpå. Den
eksisterende HEAD==origin/master-guarden (issue #28) gjør det umulig å
faithfully deploye en allerede merget, men nå "gammel", release-SHA etter
at senere commits har landet på master -- den ville blitt avvist identisk
med en faktisk feil checkout.

-ReleaseSha åpner en eksplisitt, fail-closed unntaksvei for NORMAL
produksjon (aldri owner-gate-testmodus, issue #213, som forblir en
strukturelt separat modus): i stedet for HEAD == origin/master krever den
at (1) HEAD er nøyaktig den oppgitte SHA-en, (2) SHA-en faktisk finnes som
en commit etter fersk `git fetch origin master`, og (3) SHA-en er en
ancestor av (eller lik) fersk origin/master. Krever ALDRI at SHA-en er lik
CURRENT origin/master -- en eldre, allerede merget release forblir
deploybar etter at master har beveget seg videre.

TESTSTRATEGI (samme begrunnelse som de fire andre deploy_web-testfilene):
hele scriptets imperative flyt er Windows-orientert og kan ikke kjøres
ende-til-ende her (krever git.exe/curl.exe/ekte FTPS). Det som DERIMOT
faktisk kjøres, med ekte pwsh-prosesser (ikke mocket):

1. `Test-ReleaseShaForutsetninger` -- ren beslutningsfunksjon, dot-sourcet
   direkte ut av den FAKTISKE scriptfilen, matet med syntetiske verdier.
2. Statiske kildetekst-/kontrakt-sjekker (samme stil som TestSourceWiring i
   de fire andre deploy_web-testfilene) som beviser: normal-guardens og
   owner-gate-guardens eksisterende meldinger/logikk er uendret; -ReleaseSha
   er en tydelig avgrenset `elseif`-gren; -ReleaseSha og -OwnerGateTestSha
   er gjensidig utelukkende FØR noe git-kall; RELEASE_SHA skrives ut
   konsekvent; og ingen `git merge`/`gh pr merge` er introdusert.

Kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
Krever `pwsh` i PATH.
"""
import json
import os
import re
import subprocess
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "deploy_web.ps1")

_VALID_SHA_A = "a" * 40
_VALID_SHA_B = "b" * 40


def _read_script():
    with open(_SCRIPT, encoding="utf-8-sig") as f:
        return f.read()


def _run_pwsh(command, cwd=None):
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, cwd=cwd or _REPO_ROOT,
    )


def _extract_function(script_text, name):
    match = re.search(r"(?s)function %s \{.*?\n\}\n" % re.escape(name), script_text)
    if not match:
        raise AssertionError(f"{name} ikke funnet i scripts/deploy_web.ps1 -- kan ikke kjøre testene.")
    return match.group(0)


# ─── 1: Test-ReleaseShaForutsetninger (ekte funksjon, dot-sourcet) ─────────

class TestReleaseShaForutsetninger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Test-ReleaseShaForutsetninger")

    def test_invalid_sha_format_rejected(self):
        for bad_sha in ("", "not-a-sha", _VALID_SHA_A[:39], _VALID_SHA_A + "a", "zzzz"):
            with self.subTest(bad_sha=bad_sha):
                result = self._run(
                    release_sha=bad_sha, local_head=_VALID_SHA_A,
                    commit_verified=True, is_ancestor=True, origin_fresh=True,
                )
                self.assertFalse(result["ok"])

    def test_head_mismatch_rejected(self):
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_B,
            commit_verified=True, is_ancestor=True, origin_fresh=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("HEAD", result["reason"])

    def test_head_match_case_insensitive(self):
        result = self._run(
            release_sha=_VALID_SHA_A.upper(), local_head=_VALID_SHA_A,
            commit_verified=True, is_ancestor=True, origin_fresh=True,
        )
        self.assertTrue(result["ok"])

    def test_dryrun_skips_fresh_checks_but_still_requires_head_match(self):
        """Under -DryRun the guard never fetches (0-network contract) -- the
        caller passes OriginMasterKjentFersk=$false, and this must be
        accepted as a (weaker, explicitly-labelled) pass, exactly mirroring
        the existing HEAD guard's and owner-gate guard's own -DryRun
        caveats -- never a forced failure just because ancestry could not be
        confirmed fresh."""
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            commit_verified=False, is_ancestor=False, origin_fresh=False,
        )
        self.assertTrue(result["ok"])
        self.assertIn("DryRun", result["reason"])

    def test_dryrun_still_rejects_head_mismatch(self):
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_B,
            commit_verified=False, is_ancestor=False, origin_fresh=False,
        )
        self.assertFalse(result["ok"])

    def test_fresh_check_missing_commit_rejected(self):
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            commit_verified=False, is_ancestor=False, origin_fresh=True,
        )
        self.assertFalse(result["ok"])

    def test_fresh_check_non_ancestor_rejected(self):
        """A real commit that exists but was never merged into master (e.g.
        an unmerged feature-branch commit) must be rejected -- only already
        merged content may be deployed as a frozen release."""
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            commit_verified=True, is_ancestor=False, origin_fresh=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("ancestor", result["reason"])

    def test_fresh_check_ancestor_of_master_passes(self):
        """The core acceptance case: an older, already-merged SHA remains
        deployable even though it is not equal to current origin/master --
        only ancestry is required, never equality."""
        result = self._run(
            release_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            commit_verified=True, is_ancestor=True, origin_fresh=True,
        )
        self.assertTrue(result["ok"])

    def _run(self, release_sha, local_head, commit_verified, is_ancestor, origin_fresh):
        command = r"""
%s
$result = Test-ReleaseShaForutsetninger -ReleaseSha '%s' -LocalHead '%s' -CommitVerifisertEtterFetch $%s -ErAncestorAvOriginMaster $%s -OriginMasterKjentFersk $%s
[PSCustomObject]@{ ok = $result.ok; reason = $result.reason } | ConvertTo-Json -Compress
""" % (
            self.func_text,
            release_sha.replace("'", "''"),
            local_head.replace("'", "''"),
            "true" if commit_verified else "false",
            "true" if is_ancestor else "false",
            "true" if origin_fresh else "false",
        )
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        return json.loads(r.stdout.strip())


# ─── 2: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_new_function_and_param_present_exactly_once(self):
        for needle in (
            "function Test-ReleaseShaForutsetninger",
            "$isReleaseShaMode = -not [string]::IsNullOrWhiteSpace($ReleaseSha)",
        ):
            self.assertEqual(self.text.count(needle), 1, f"{needle!r} skal finnes nøyaktig én gang.")
        self.assertIn("\n    [string]$ReleaseSha,\n    [string]$OwnerGateTestSha,\n", self.text)

    def test_release_sha_and_owner_gate_are_mutually_exclusive_before_any_git_call(self):
        idx_mutex_check = self.text.index("if ($isReleaseShaMode -and $isOwnerGateTest) {")
        idx_first_git_call = self.text.index("Get-Command git.exe")
        self.assertLess(idx_mutex_check, idx_first_git_call, "Gjensidig-utelukkende-sjekken skal kjøre FØR noe git-kall.")
        section = self.text[idx_mutex_check:idx_mutex_check + 600]
        self.assertIn("exit 1", section)

    def test_mutex_guard_runs_before_owner_gate_target_guard(self):
        idx_mutex = self.text.index("if ($isReleaseShaMode -and $isOwnerGateTest) {")
        idx_owner_gate_target_guard = self.text.index("# ─── 1a2. Guard: owner-gate testmodus kan ikke stille target produksjon")
        self.assertLess(idx_mutex, idx_owner_gate_target_guard)

    def test_release_sha_branch_is_elseif_not_replacement(self):
        """The release-SHA branch must be reachable only as an `elseif` of
        `if ($isOwnerGateTest)`, with the pre-existing plain `else` (normal
        HEAD==origin/master path) still present and last -- proving
        release-SHA mode can never silently apply to an unflagged
        invocation, and the normal path is never removed, only joined by a
        third option."""
        idx_if_owner_gate = self.text.index("if ($isOwnerGateTest) {")
        idx_elseif_release = self.text.index("elseif ($isReleaseShaMode) {", idx_if_owner_gate)
        idx_else_normal = self.text.index("else {", idx_elseif_release)
        idx_normal_fetch = self.text.index("& git fetch origin master --quiet", idx_else_normal)
        self.assertLess(idx_if_owner_gate, idx_elseif_release)
        self.assertLess(idx_elseif_release, idx_else_normal)
        self.assertLess(idx_else_normal, idx_normal_fetch)

    def test_normal_head_guard_messages_byte_identical_and_present(self):
        """The pre-existing HEAD==origin/master guard's exact source text
        (assertion regression from tests/test_deploy_web_guard.py and
        tests/test_deploy_web_owner_gate.py) must survive completely
        unchanged -- release-SHA mode must be an ADDITIONAL branch, never a
        rewrite of the normal path."""
        for expected in (
            "& git fetch origin master --quiet",
            'Write-Error "git fetch origin master feilet',
            "if ($localHead -ne $originMasterRef) {",
            'Write-Host "STOPPER: denne checkouten matcher IKKE origin/master."',
            'Write-Error "Ingen filer ble lastet opp -- checkout matcher ikke origin/master."',
            'Write-Host "Guard OK -- HEAD matcher origin/master ($localHead)."',
        ):
            self.assertIn(expected, self.text, f"Normal-guardens forventede kildetekst mangler/endret: {expected!r}")

    def test_owner_gate_guard_messages_byte_identical_and_present(self):
        """Same non-regression proof for the owner-gate branch (issue #213)
        -- release-SHA mode must not have touched it."""
        for expected in (
            "Test-OwnerGateForutsetninger -ExpectedSha $OwnerGateTestSha",
            'Write-Host "Owner-gate OK -- $($forutsetning.reason)"',
            'Write-Host "ADVARSEL: owner-gate testmodus er aktiv -- dette er IKKE en normal produksjonsdeploy."',
        ):
            self.assertIn(expected, self.text, f"Owner-gate-guardens forventede kildetekst mangler/endret: {expected!r}")

    def test_release_sha_uses_full_sha_regex(self):
        func_text = _extract_function(self.text, "Test-ReleaseShaForutsetninger")
        self.assertIn(r"'^[0-9a-fA-F]{40}$'", func_text)

    def test_release_sha_never_compares_against_current_origin_master_equality(self):
        """Core acceptance requirement: -ReleaseSha must NOT require
        equality with current origin/master (only ancestry) -- an older,
        already-merged SHA must remain deployable after master advances.
        The decision function must therefore never reference
        $originMasterRef (the exact-equality variable the normal HEAD guard
        uses) at all."""
        func_text = _extract_function(self.text, "Test-ReleaseShaForutsetninger")
        self.assertNotIn("originMasterRef", func_text)
        self.assertNotIn("-eq $ReleaseSha", self.text[self.text.index("elseif ($isReleaseShaMode)"):self.text.index("else {", self.text.index("elseif ($isReleaseShaMode)"))])

    def test_release_sha_checks_ancestor_via_merge_base(self):
        section_start = self.text.index("elseif ($isReleaseShaMode) {")
        section_end = self.text.index("else {", section_start)
        section = self.text[section_start:section_end]
        self.assertIn("git merge-base --is-ancestor $ReleaseSha origin/master", section)
        self.assertIn("git cat-file -e", section)
        self.assertIn("git fetch origin master --quiet", section)

    def test_release_sha_skips_fetch_under_dryrun(self):
        section_start = self.text.index("elseif ($isReleaseShaMode) {")
        section_end = self.text.index("else {", section_start)
        section = self.text[section_start:section_end]
        idx_dryrun_check = section.index("if (-not $DryRun) {")
        idx_fetch = section.index("git fetch origin master --quiet")
        self.assertLess(idx_dryrun_check, idx_fetch, "Fetch skal ligge inni `if (-not $DryRun)` -- 0-nettverkstilkoblinger-kontrakten under -DryRun.")

    def test_release_sha_printed_in_source_block_prompt_and_final_summary(self):
        for expected in (
            'Write-Host "RELEASE_SHA: $ReleaseSha (frossen release -- se .DESCRIPTION/web/README.md)"',
            "$releaseShaPromptSuffix = if ($isReleaseShaMode) { \" [RELEASE_SHA: $ReleaseSha]\" } else { \"\" }",
            "$releaseShaVerifiseringSuffix = if ($isReleaseShaMode) { \" (RELEASE_SHA: $ReleaseSha)\" } else { \"\" }",
        ):
            self.assertIn(expected, self.text, f"RELEASE_SHA-visning mangler/endret: {expected!r}")

    def test_no_new_merge_or_master_push_introduced(self):
        """Defense-in-depth non-regression: -ReleaseSha must never introduce
        a merge or a push to master -- it only changes which comparison
        gates a normal, already-existing manual upload flow. `git
        merge-base` (a read-only ancestry query, not a merge) is the one
        expected/intentional `git merge*` occurrence."""
        merge_occurrences = [m.start() for m in re.finditer(r"git merge", self.text)]
        for idx in merge_occurrences:
            self.assertEqual(
                self.text[idx:idx + len("git merge-base")], "git merge-base",
                "Uventet 'git merge'-forekomst som ikke er 'git merge-base'.",
            )
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("push origin master", self.text)
