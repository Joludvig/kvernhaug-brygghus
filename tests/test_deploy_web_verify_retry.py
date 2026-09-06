"""
scripts/deploy_web.ps1 -- regresjonstester for det bounded retry-forsøket i
produksjonsverifiseringen (steg 6), pluss den utvidede avviks-loggingen
(issue #81).

BAKGRUNN: produksjon er siden bekreftet korrekt (85/85 filer matcher
master), men rotårsaken til den TIDLIGERE verifiseringsfeilen er ukjent --
ingen cache-antakelse presenteres som årsak her (issue #81s eget krav).
Formålet med denne endringen er utelukkende bedre diagnose/robusthet ved en
FREMTIDIG uoverensstemmelse, uten å svekke noen eksisterende guard:

1. Ved avvik logges nå filsti, forventet (lokal) sjekksum og mottatt
   (produksjons-) sjekksum eksplisitt.
2. Kun de FEILEDE sjekkene fra første pass prøves på nytt, én gang, etter en
   kort avgrenset pause (`Start-Sleep`) -- ikke en løkke.
3. Hvert retry-forsøk bruker en FERSK HTTP-hentning (samme
   `Invoke-DeployFileVerifisering`-funksjon som første pass, kalt på nytt --
   aldri gjenbruk av forrige nedlastede fil).
4. Alle eksisterende guards (stale-checkout, urent web/, autoritativ
   repo-sti, selve post-upload-verifiseringen) er urørt.
5. Suksess krever fortsatt at ALLE deployable filer matcher eksakt --
   sammenslåingslogikken kan aldri konvertere et uløst avvik til suksess
   med mindre retry-passets egne ferske bytes faktisk matcher.

TESTSTRATEGI (samme begrunnelse som test_deploy_web_guard.py): hele
scriptet er Windows-orientert og den aller første guarden krever et
bokstavelig `git.exe`-navngitt binærfil som ikke finnes på denne Linux
pwsh-installasjonen -- en full `pwsh -File scripts/deploy_web.ps1`-kjøring
(med ekte FTP/HTTPS) er derfor utenfor denne sandkassen og forblir en
manuell/Windows-verifisering. Det som DERIMOT faktisk kjøres her, med ekte
pwsh-prosesser (ikke mocket):

1. `Get-VerifiseringsStierForRetry` og `Merge-VerifiseringsResultat` --
   scriptets rene beslutningsfunksjoner for retry-utvelgelse og
   sammenslåing -- dot-sourcet direkte ut av den FAKTISKE scriptfilen,
   matet med syntetiske resultatobjekter.
2. Statiske kildetekst-/kontrakt-sjekker (samme stil som
   TestSourceWiring i test_deploy_web_guard.py) som beviser: nøyaktig ett
   `Start-Sleep`-kall i verifiseringsseksjonen (ett avgrenset retry, ikke
   en løkke), retry-passet gjenbruker samme
   `Invoke-DeployFileVerifisering`-funksjon som første pass (fersk
   HTTP-hentning garantert av konstruksjon, ikke av at noen husker å ikke
   gjenbruke en fil), sluttresultatet (mismatches/unverifiable) beregnes
   fra det SAMMENSLÅTTE resultatet -- ikke fra første pass alene -- og at
   alle fire eksisterende guards' kildetekst/meldinger er uendret.

Kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
Krever `pwsh` og `git` i PATH.
"""
import json
import os
import re
import subprocess
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "deploy_web.ps1")


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


# ─── 1: Get-VerifiseringsStierForRetry (ekte funksjon, dot-sourcet) ────────

class TestGetVerifiseringsStierForRetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Get-VerifiseringsStierForRetry")

    def test_all_ok_yields_no_retry(self):
        results = [
            {"rel": "web/index.html", "ok": True, "reason": "ok"},
            {"rel": "web/style.css", "ok": True, "reason": "ok"},
        ]
        got = self._run(results)
        self.assertEqual(got, [])

    def test_mismatch_and_unverifiable_both_selected(self):
        results = [
            {"rel": "web/a.html", "ok": True, "reason": "ok"},
            {"rel": "web/b.html", "ok": False, "reason": "mismatch"},
            {"rel": "web/c.html", "ok": False, "reason": "unverifiable"},
        ]
        got = self._run(results)
        self.assertEqual(sorted(got), ["web/b.html", "web/c.html"])

    def test_ok_files_never_selected_for_retry(self):
        results = [{"rel": f"web/f{i}.html", "ok": True, "reason": "ok"} for i in range(5)]
        results.append({"rel": "web/bad.html", "ok": False, "reason": "mismatch"})
        got = self._run(results)
        self.assertEqual(got, ["web/bad.html"])

    def _run(self, results):
        results_json = json.dumps(results)
        command = r"""
%s
$results = '%s' | ConvertFrom-Json
$objs = @($results | ForEach-Object { [PSCustomObject]@{ rel = $_.rel; ok = $_.ok; reason = $_.reason } })
$got = @(Get-VerifiseringsStierForRetry -Resultater $objs)
$got | ConvertTo-Json -Compress
""" % (self.func_text, results_json.replace("'", "''"))
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        out = r.stdout.strip()
        if not out:
            return []
        parsed = json.loads(out)
        if isinstance(parsed, str):
            return [parsed]
        return list(parsed)


# ─── 2: Merge-VerifiseringsResultat (ekte funksjon, dot-sourcet) ───────────

class TestMergeVerifiseringsResultat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Merge-VerifiseringsResultat")

    def test_no_retry_returns_forste_unchanged(self):
        forste = [{"rel": "web/a.html", "ok": True, "reason": "ok"}]
        got = self._run(forste, [])
        self.assertEqual(got, [{"rel": "web/a.html", "ok": True, "reason": "ok"}])

    def test_retry_success_overrides_forste_failure(self):
        """A file that failed pass 1 but matches on retry must be reported
        as ok in the final result -- proves a transient glitch can resolve."""
        forste = [{"rel": "web/a.html", "ok": False, "reason": "mismatch"}]
        retry = [{"rel": "web/a.html", "ok": True, "reason": "ok"}]
        got = self._run(forste, retry)
        self.assertEqual(got, [{"rel": "web/a.html", "ok": True, "reason": "ok"}])

    def test_retry_still_failing_stays_failing(self):
        """A genuine, reproducible mismatch must never be converted to
        success just because a retry was attempted (issue #81, req 6)."""
        forste = [{"rel": "web/a.html", "ok": False, "reason": "mismatch"}]
        retry = [{"rel": "web/a.html", "ok": False, "reason": "mismatch"}]
        got = self._run(forste, retry)
        self.assertEqual(got, [{"rel": "web/a.html", "ok": False, "reason": "mismatch"}])

    def test_file_never_retried_is_untouched(self):
        """A file that was ok in pass 1 (and therefore never selected for
        retry) must keep its original result even though other files were
        retried."""
        forste = [
            {"rel": "web/ok.html", "ok": True, "reason": "ok"},
            {"rel": "web/bad.html", "ok": False, "reason": "mismatch"},
        ]
        retry = [{"rel": "web/bad.html", "ok": True, "reason": "ok"}]
        got = self._run(forste, retry)
        by_rel = {g["rel"]: g for g in got}
        self.assertEqual(by_rel["web/ok.html"]["reason"], "ok")
        self.assertEqual(by_rel["web/bad.html"]["reason"], "ok")

    def _run(self, forste, retry):
        forste_json = json.dumps(forste)
        retry_json = json.dumps(retry)
        command = r"""
%s
function ToObjs($arr) { @($arr | ForEach-Object { [PSCustomObject]@{ rel = $_.rel; ok = $_.ok; reason = $_.reason } }) }
$forste = ToObjs ('%s' | ConvertFrom-Json)
$retryRaw = '%s' | ConvertFrom-Json
$retry = @()
if ($retryRaw) { $retry = ToObjs $retryRaw }
$got = @(Merge-VerifiseringsResultat -Forste $forste -Retry $retry)
$got | Select-Object rel, ok, reason | ConvertTo-Json -Compress
""" % (self.func_text, forste_json.replace("'", "''"), retry_json.replace("'", "''"))
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        parsed = json.loads(r.stdout.strip())
        if isinstance(parsed, dict):
            parsed = [parsed]
        return parsed


# ─── 3: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def _verify_section(self):
        start = self.text.index("--- Verifiserer produksjon: FAKTISK INNHOLD")
        return self.text[start:]

    def test_new_pure_functions_present(self):
        self.assertIn("function Get-VerifiseringsStierForRetry", self.text)
        self.assertIn("function Merge-VerifiseringsResultat", self.text)
        self.assertIn("function Invoke-DeployFileVerifisering", self.text)

    def test_exactly_one_bounded_retry_not_a_loop(self):
        """Requirement 2: retry only the failed checks, once, after a short
        bounded pause -- not an open-ended/polling loop."""
        section = self._verify_section()
        self.assertEqual(section.count("Start-Sleep"), 1, "Forventer nøyaktig ett Start-Sleep-kall (ett avgrenset retry-forsøk).")
        self.assertNotIn("while (", section)
        self.assertNotIn("do {", section)

    def test_retry_pause_is_short_and_documented(self):
        self.assertIn("$RetryPauseSekunder = 5", self.text)
        self.assertIn("issue #81", self.text)

    def test_retry_reuses_same_fetch_function_as_first_pass(self):
        """Requirement 3: every retry must use a fresh HTTP fetch -- proven
        here by both passes calling the exact same function (which does a
        brand-new Invoke-WebRequest per call), not two divergent code
        paths where the retry one might reuse cached bytes."""
        section = self._verify_section()
        self.assertEqual(
            section.count("Invoke-DeployFileVerifisering -Rel"), 2,
            "Forventer nøyaktig to kall til Invoke-DeployFileVerifisering (første pass + retry-pass).",
        )

    def test_final_outcome_computed_from_merged_result_not_first_pass_alone(self):
        section = self._verify_section()
        idx_merge = section.index("Merge-VerifiseringsResultat")
        idx_mismatches = section.index("$mismatches = @($sluttResultat")
        idx_unverifiable = section.index("$unverifiable = @($sluttResultat")
        self.assertLess(idx_merge, idx_mismatches)
        self.assertLess(idx_merge, idx_unverifiable)
        self.assertNotIn("$forstePass | Where-Object", section)

    def test_mismatch_logging_includes_expected_and_received_checksum(self):
        """Requirement 1: file path, expected checksum, received checksum."""
        section = self._verify_section()
        self.assertIn("forventet sjekksum (lokal kilde)", section)
        self.assertIn("mottatt sjekksum (produksjon)", section)
        self.assertIn("$Resultat.localHash", section)
        self.assertIn("$Resultat.remoteHash", section)
        self.assertIn("$m.localHash", section)
        self.assertIn("$m.remoteHash", section)

    def test_success_still_requires_all_files_to_match(self):
        self.assertIn('$mismatches.Count -gt 0 -or $unverifiable.Count -gt 0', self.text)
        self.assertIn("alle $($DeployFiles.Count) filer bekreftet byte-for-byte identiske", self.text)

    def test_no_cache_busting_assumption_introduced(self):
        """Out of scope: no cache assumption presented as root cause."""
        lowered = self.text.lower()
        self.assertNotIn("cache-bust", lowered)
        self.assertNotIn("no-cache", lowered)
        self.assertNotIn("cachebust", lowered)

    def test_no_merge_or_new_push_command_introduced(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("git push", self.text)

    def test_existing_guards_untouched(self):
        for expected in (
            "& git fetch origin master --quiet",
            'Write-Error "git fetch origin master feilet',
            "if ($localHead -ne $originMasterRef) {",
            'Write-Host "STOPPER: denne checkouten matcher IKKE origin/master."',
            "git status --porcelain --ignored=matching -- web/",
            "function Get-UrentWebInnhold",
            '$ExcludeRelative = @("README.md", "CHANGELOG.md")',
        ):
            self.assertIn(expected, self.text, f"Eksisterende guard-kildetekst mangler/endret: {expected!r}")

    def test_smoke_check_before_content_verification_unchanged(self):
        self.assertIn('"https://kvernhaugbrygghus.no/"', self.text)
        self.assertIn('"https://kvernhaugbrygghus.no/en/"', self.text)
        idx_smoke = self.text.index("Verifiserer produksjon: rask HTTP-svar-sjekk")
        idx_content = self.text.index("Verifiserer produksjon: FAKTISK INNHOLD")
        self.assertLess(idx_smoke, idx_content)


if __name__ == "__main__":
    unittest.main()
