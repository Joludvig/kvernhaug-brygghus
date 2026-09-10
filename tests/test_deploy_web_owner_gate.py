"""
scripts/deploy_web.ps1 -- regresjonstester for owner-gate testmodus
(-OwnerGateTestSha), issue #213 (Chief review, PR #216, owner-gate blocker).

BAKGRUNN: den ekte Windows/Domeneshop-FTPS bolk-/retry-implementasjonen
(issue #213) kunne ikke owner-PC-verifiseres FØR merge, fordi den
eksisterende HEAD==origin/master-guarden (issue #28) korrekt hard-stopper
enhver checkout som ikke er nøyaktig origin/master -- og en PR-head er per
definisjon IKKE origin/master før merge. Chief krevde en SNEVER,
eksplisitt owner-gate-unntaksvei som:

1. lar normal deploy (uten -OwnerGateTestSha) forbli helt uendret --
   fortsatt kun HEAD == origin/master;
2. krever en eksplisitt oppgitt, full 40-tegns forventet SHA, og
   fail-closed avviser enhver mismatch mot lokal HEAD;
3. (utenfor -DryRun) også bekrefter FERSK at origin/<gjeldende branch>
   samsvarer med samme SHA, slik at testkjøringen er bundet til
   PR-branchens faktiske pushede head, ikke bare en lokal commit;
4. nekter å target normal produksjon (/www) uten et eksplisitt
   -OwnerGateAllowProductionTarget, slik at en owner-gate-test aldri ved
   et uhell skriver ureviewede PR-bytes til den faktiske live-siden.

TESTSTRATEGI (samme begrunnelse som de tre andre deploy_web-testfilene):
hele scriptets imperative flyt er Windows-orientert og kan ikke kjøres
ende-til-ende her (krever git.exe/curl.exe/ekte FTPS). Det som DERIMOT
faktisk kjøres, med ekte pwsh-prosesser (ikke mocket):

1. `Test-OwnerGateForutsetninger` og `Test-OwnerGateMaalErTrygt` -- rene
   beslutningsfunksjoner, dot-sourcet direkte ut av den FAKTISKE
   scriptfilen, matet med syntetiske verdier.
2. Statiske kildetekst-/kontrakt-sjekker (samme stil som TestSourceWiring
   i de tre andre deploy_web-testfilene) som beviser: normal-guardens
   eksisterende meldinger/logikk er BYTE-IDENTISK uendret og fortsatt tas
   i else-grenen; owner-gate-testmodus er en tydelig avgrenset if-gren;
   mål-guarden kjøres FØR git-guarden; og ingen `git push`/`gh pr merge`
   er introdusert.

Kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
Krever `pwsh` i PATH.
"""
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


# ─── 1: Test-OwnerGateForutsetninger (ekte funksjon, dot-sourcet) ──────────

class TestOwnerGateForutsetninger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Test-OwnerGateForutsetninger")

    def test_invalid_sha_format_rejected(self):
        for bad_sha in ("", "not-a-sha", _VALID_SHA_A[:39], _VALID_SHA_A + "a", "zzzz"):
            with self.subTest(bad_sha=bad_sha):
                result = self._run(
                    expected_sha=bad_sha, local_head=_VALID_SHA_A,
                    origin_ref=_VALID_SHA_A, origin_fresh=True,
                )
                self.assertFalse(result["ok"])

    def test_head_mismatch_rejected(self):
        result = self._run(
            expected_sha=_VALID_SHA_A, local_head=_VALID_SHA_B,
            origin_ref=_VALID_SHA_A, origin_fresh=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("HEAD", result["reason"])

    def test_head_match_case_insensitive(self):
        result = self._run(
            expected_sha=_VALID_SHA_A.upper(), local_head=_VALID_SHA_A,
            origin_ref=_VALID_SHA_A, origin_fresh=True,
        )
        self.assertTrue(result["ok"])

    def test_dryrun_skips_origin_check_but_still_requires_head_match(self):
        """Under -DryRun the guard never fetches (0-network contract) -- the
        caller passes OriginBranchRefKjentFersk=$false, and this must be
        accepted as a (weaker, explicitly-labelled) pass rather than a
        forced failure, exactly mirroring the existing HEAD guard's own
        -DryRun caveat."""
        result = self._run(
            expected_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            origin_ref=None, origin_fresh=False,
        )
        self.assertTrue(result["ok"])
        self.assertIn("DryRun", result["reason"])

    def test_fresh_check_requires_origin_branch_match(self):
        result = self._run(
            expected_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            origin_ref=_VALID_SHA_B, origin_fresh=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("origin/", result["reason"])

    def test_fresh_check_missing_origin_ref_rejected(self):
        """The origin branch not resolving at all (e.g. never pushed) must
        fail closed, not be treated as vacuously satisfied."""
        result = self._run(
            expected_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            origin_ref="", origin_fresh=True,
        )
        self.assertFalse(result["ok"])

    def test_fresh_check_all_match_passes(self):
        result = self._run(
            expected_sha=_VALID_SHA_A, local_head=_VALID_SHA_A,
            origin_ref=_VALID_SHA_A, origin_fresh=True,
        )
        self.assertTrue(result["ok"])

    def _run(self, expected_sha, local_head, origin_ref, origin_fresh):
        origin_ref_arg = "$null" if origin_ref is None else f"'{origin_ref}'"
        command = r"""
%s
$result = Test-OwnerGateForutsetninger -ExpectedSha '%s' -LocalHead '%s' -OriginBranchNavn 'agent/issue-213' -OriginBranchRef %s -OriginBranchRefKjentFersk $%s
[PSCustomObject]@{ ok = $result.ok; reason = $result.reason } | ConvertTo-Json -Compress
""" % (
            self.func_text,
            expected_sha.replace("'", "''"),
            local_head.replace("'", "''"),
            origin_ref_arg,
            "true" if origin_fresh else "false",
        )
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        import json
        return json.loads(r.stdout.strip())


# ─── 2: Test-OwnerGateMaalErTrygt (ekte funksjon, dot-sourcet) ─────────────

class TestOwnerGateMaalErTrygt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Test-OwnerGateMaalErTrygt")

    def test_default_production_target_rejected_without_explicit_allow(self):
        result = self._run(remote_root="/www", standard="/www", allow=False)
        self.assertFalse(result["ok"])

    def test_default_production_target_allowed_with_explicit_flag(self):
        result = self._run(remote_root="/www", standard="/www", allow=True)
        self.assertTrue(result["ok"])

    def test_isolated_test_target_allowed_without_flag(self):
        result = self._run(remote_root="/www-owner-gate-test", standard="/www", allow=False)
        self.assertTrue(result["ok"])

    def _run(self, remote_root, standard, allow):
        command = r"""
%s
$result = Test-OwnerGateMaalErTrygt -RemoteRoot '%s' -StandardRemoteRoot '%s' -AllowProductionTarget $%s
[PSCustomObject]@{ ok = $result.ok; reason = $result.reason } | ConvertTo-Json -Compress
""" % (
            self.func_text,
            remote_root.replace("'", "''"),
            standard.replace("'", "''"),
            "true" if allow else "false",
        )
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        import json
        return json.loads(r.stdout.strip())


# ─── 3: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_new_functions_and_params_present_exactly_once(self):
        for needle in (
            "function Test-OwnerGateForutsetninger",
            "function Test-OwnerGateMaalErTrygt",
            "[string]$OwnerGateTestSha,",
            "[switch]$OwnerGateAllowProductionTarget",
        ):
            self.assertEqual(self.text.count(needle), 1, f"{needle!r} skal finnes nøyaktig én gang.")

    def test_normal_head_guard_messages_byte_identical_and_present(self):
        """The pre-existing HEAD==origin/master guard's exact source text
        (assertion regression from tests/test_deploy_web_guard.py) must
        survive completely unchanged -- owner-gate must be an ADDITIONAL
        branch, never a rewrite of the normal path."""
        for expected in (
            "& git fetch origin master --quiet",
            'Write-Error "git fetch origin master feilet',
            "if ($localHead -ne $originMasterRef) {",
            'Write-Host "STOPPER: denne checkouten matcher IKKE origin/master."',
            'Write-Error "Ingen filer ble lastet opp -- checkout matcher ikke origin/master."',
            'Write-Host "Guard OK -- HEAD matcher origin/master ($localHead)."',
        ):
            self.assertIn(expected, self.text, f"Normal-guardens forventede kildetekst mangler/endret: {expected!r}")

    def test_owner_gate_is_a_branch_not_a_replacement(self):
        """The normal-guard block must be reachable only via the `else`
        branch of an `if ($isOwnerGateTest)` -- proving owner-gate mode can
        never silently apply to a plain, unflagged invocation."""
        idx_if = self.text.index("if ($isOwnerGateTest) {")
        idx_else = self.text.index("else {", idx_if)
        idx_normal_fetch = self.text.index("& git fetch origin master --quiet")
        self.assertLess(idx_if, idx_else)
        self.assertLess(idx_else, idx_normal_fetch, "Normalguardens git-fetch skal ligge i else-grenen, etter owner-gate-grenen.")

    def test_owner_gate_flag_derived_from_ownergatetestsha_only(self):
        self.assertIn(
            "$isOwnerGateTest = -not [string]::IsNullOrWhiteSpace($OwnerGateTestSha)",
            self.text,
        )

    def test_target_guard_runs_before_git_head_guard(self):
        idx_target_guard = self.text.index("Test-OwnerGateMaalErTrygt -RemoteRoot $RemoteRoot")
        idx_head_guard_section = self.text.index("# ─── 1b. Guard: nekt å deploye fra en checkout")
        self.assertLess(idx_target_guard, idx_head_guard_section, "Mål-guarden skal kjøres FØR git-HEAD-guarden (fail fast, ingen git-kall for en allerede avvist target).")

    def test_target_guard_gated_behind_owner_gate_flag(self):
        idx_target_guard = self.text.index("Test-OwnerGateMaalErTrygt -RemoteRoot $RemoteRoot")
        idx_if_owner_gate = self.text.rindex("if ($isOwnerGateTest) {", 0, idx_target_guard)
        section_between = self.text[idx_if_owner_gate:idx_target_guard]
        self.assertNotIn("\n}\n", section_between, "Mål-guardens kall skal ligge INNI owner-gate if-blokken, ikke etter at den er lukket.")

    def test_owner_gate_uses_full_sha_regex(self):
        self.assertIn(r"'^[0-9a-fA-F]{40}$'", self.text)

    def test_owner_gate_fresh_check_uses_current_branch_not_hardcoded_issue_branch(self):
        """The origin-branch binding must be derived from the actual current
        checkout's branch name (git rev-parse --abbrev-ref HEAD), not a
        hardcoded 'agent/issue-213' literal -- this owner-gate mechanism is
        reusable by any future PR branch, not single-issue-scoped."""
        self.assertIn('(& git rev-parse --abbrev-ref HEAD).Trim()', self.text)
        self.assertNotIn('"agent/issue-213"', self.text)

    def test_owner_gate_skips_fetch_under_dryrun(self):
        idx_owner_gate = self.text.index("if ($isOwnerGateTest) {")
        idx_else = self.text.index("else {", idx_owner_gate)
        section = self.text[idx_owner_gate:idx_else]
        self.assertIn("if (-not $DryRun) {", section)
        self.assertIn("git fetch origin $localBranch --quiet", section)

    def test_no_merge_or_push_command_introduced(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("git push", self.text)

    def test_docs_mention_owner_gate(self):
        self.assertIn("OWNER-GATE TESTMODUS", self.text)
        self.assertIn(".PARAMETER OwnerGateTestSha", self.text)
        self.assertIn(".PARAMETER OwnerGateAllowProductionTarget", self.text)


if __name__ == "__main__":
    unittest.main()
