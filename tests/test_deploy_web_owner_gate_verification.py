"""
scripts/deploy_web.ps1 -- regresjonstester for owner-gate testmodus sin
FTPS-baserte verifisering mot det ISOLERTE testmålet (issue #213, Chief
review, PR #216, runde 5).

BAKGRUNN: owner-gate testmodus (-OwnerGateTestSha, se
tests/test_deploy_web_owner_gate.py) lot en PR-head kjøre den ekte bolk-
/retry-FTPS-implementasjonen mot en isolert -RemoteRoot FØR merge. Men
Chief-review (PR #216, runde 5) påviste at BEVISET selv var hult: steg 2b
(delta-sjekken) og steg 6 (produksjonsverifiseringen) brukte begge
$BaseUrl = "https://kvernhaugbrygghus.no" -- dvs. NORMAL PRODUKSJON --
uansett hvilken -RemoteRoot som faktisk ble target. Siden denne
utvidelsen av deploy_web.ps1 ikke selv endrer web/, matcher produksjon
allerede alle 85 filene -- delta-sjekken ville derfor stille hoppet over
ALLE filene FØR én eneste FTPS-tilkobling til teststien i det hele tatt
ble åpnet, og sluttverifiseringen ville "bekreftet" produksjonens bytes,
ikke testmålets.

FIKSEN (denne filen tester):
1. Delta-sjekken (steg 2b) hopper UBETINGET over i owner-gate testmodus --
   ALLE filer sendes til FTPS-opplasting, uansett hva produksjon
   inneholder. Den nye rene beslutningsfunksjonen
   Get-OwnerGateDeltaSjekkBeslutning styrer dette, uavhengig av nettverk.
2. Reverifisering FØR et bolk-retry-forsøk (steg 5c) bruker FTPS mot det
   faktiske -RemoteRoot-testmålet (Invoke-DeployFileVerifiseringFtps) i
   owner-gate testmodus, ikke lenger HTTPS mot produksjon.
3. Sluttverifiseringen (steg 6) laster i owner-gate testmodus ned HVER
   fil på nytt over FTPS fra det faktiske -RemoteRoot-testmålet (bolkvis,
   Invoke-DeployBolkVerifiseringFtps, for å unngå å åpne én FTPS-
   tilkobling per fil for et sett som kan være alle 85) -- ikke HTTPS mot
   produksjon. Smoke-sjekken (HTTP 200 på produksjonens root/en) hoppes
   også over, siden den kun sier noe om normal produksjon.
4. Normal deploy (uten -OwnerGateTestSha) er HELT uendret -- fortsatt
   utelukkende HTTPS mot $BaseUrl, dekket av de eksisterende testene i
   test_deploy_web_batch_upload.py og test_deploy_web_verify_retry.py
   (kjørt uendret av denne endringen).

TESTSTRATEGI (samme begrunnelse som de fire andre deploy_web-testfilene):
hele scriptets imperative flyt er Windows-orientert og krever
git.exe/curl.exe/ekte FTPS -- utenfor denne sandkassen, og forblir en
manuell/Windows owner-gate-verifisering. Det som DERIMOT faktisk kjøres
her, med ekte pwsh-prosesser (ikke mocket):

1. `Get-OwnerGateDeltaSjekkBeslutning` -- ren beslutningsfunksjon,
   dot-sourcet direkte ut av den FAKTISKE scriptfilen.
2. `New-BolkNedlastingConfig` (dot-sourcet sammen med
   Get-CurlConfigEscaped) -- ren tekstbygging, FTPS-nedlastingsmotstykket
   til New-BolkOpplastingConfig, verifisert mot eksakt forventet
   -K-configinnhold.
3. Statiske kildetekst-/kontrakt-sjekker som beviser: delta-utvelgelsen
   i owner-gate-grenen aldri konsulterer $BaseUrl/produksjon (kravet fra
   Chief-reviewen -- "delta-utvelgelsen må ikke kunne nullstille
   testsettet basert på live produksjon"); steg 5c og steg 6 bruker
   FTPS-variantene i owner-gate-grenen; normal (else-)grenen i alle tre
   stegene er BYTE-IDENTISK uendret og fortsatt utelukkende HTTPS.

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


# ─── 1: Get-OwnerGateDeltaSjekkBeslutning (ekte funksjon, dot-sourcet) ─────

class TestGetOwnerGateDeltaSjekkBeslutning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Get-OwnerGateDeltaSjekkBeslutning")

    def test_owner_gate_always_skips_delta_regardless_of_any_production_state(self):
        """Requirement (Chief review, PR #216, runde 5): delta-utvelgelsen
        må ikke kunne nullstille testsettet basert på live produksjon. Denne
        funksjonen tar IKKE produksjonstilstand som input i det hele tatt --
        beviser derfor i seg selv at avgjørelsen aldri kan avhenge av hva
        produksjon faktisk inneholder når -OwnerGateTestSha er satt."""
        result = self._run(is_owner_gate_test=True)
        self.assertTrue(result["skipDelta"])
        self.assertIn("owner-gate", result["reason"].lower())

    def test_normal_deploy_does_not_skip_delta(self):
        result = self._run(is_owner_gate_test=False)
        self.assertFalse(result["skipDelta"])
        self.assertEqual(result["reason"], "")

    def _run(self, is_owner_gate_test):
        command = r"""
%s
$result = Get-OwnerGateDeltaSjekkBeslutning -IsOwnerGateTest $%s
[PSCustomObject]@{ skipDelta = $result.skipDelta; reason = $result.reason } | ConvertTo-Json -Compress
""" % (self.func_text, "true" if is_owner_gate_test else "false")
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        return json.loads(r.stdout.strip())


# ─── 2: New-BolkNedlastingConfig (ekte funksjon + Get-CurlConfigEscaped) ───

class TestNewBolkNedlastingConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = (
            _extract_function(cls.script_text, "Get-CurlConfigEscaped")
            + _extract_function(cls.script_text, "New-BolkNedlastingConfig")
        )

    def test_single_file_block_structure(self):
        out = self._run("user = \"u:p\"", [{"rel": "index.html", "TempFile": "/tmp/dl/f1"}], "ftp.example.com", "/www-owner-gate-test")
        self.assertTrue(out.startswith("user = \"u:p\"\n"))
        self.assertIn('url = "ftp://ftp.example.com/www-owner-gate-test/index.html"', out)
        self.assertIn("--ssl-reqd", out)
        self.assertIn('-o "/tmp/dl/f1"', out)
        self.assertNotIn("-T ", out, "Nedlasting skal bruke -o (GET), aldri -T (PUT/opplasting).")
        self.assertNotIn("--ftp-create-dirs", out, "Nedlasting oppretter ingen mapper -- kun opplasting trenger --ftp-create-dirs.")
        self.assertNotIn("--next", out, "Ingen --next skal finnes med bare ÉN fil i bolken.")

    def test_multiple_files_separated_by_next_with_credential_repeated(self):
        files = [
            {"rel": "a.html", "TempFile": "/tmp/dl/a"},
            {"rel": "b.html", "TempFile": "/tmp/dl/b"},
            {"rel": "c.html", "TempFile": "/tmp/dl/c"},
        ]
        out = self._run("user = \"u:p\"", files, "ftp.example.com", "/www-owner-gate-test")
        self.assertEqual(out.count("--next"), 2, "N filer skal ha nøyaktig N-1 --next-adskillere.")
        self.assertEqual(out.count("url = "), 3)
        self.assertEqual(out.count("--ssl-reqd"), 3, "--ssl-reqd skal gjentas EKSPLISITT for hver fil, ikke arves på tvers av --next.")
        self.assertEqual(
            out.count('user = "u:p"'), 3,
            "Credential-linjen skal gjentas i HVER --next-blokk (samme curl --next-semantikk som opplastingen).",
        )
        for block in out.split("--next"):
            self.assertRegex(block.strip(), r'^user = "u:p"\nurl = ')

    def test_special_characters_in_temp_path_are_escaped(self):
        files = [{"rel": "weird.html", "TempFile": 'C:\\tmp\\weird "file".tmp'}]
        out = self._run("user = \"u:p\"", files, "ftp.example.com", "/www-owner-gate-test")
        self.assertIn('-o "C:\\\\tmp\\\\weird \\"file\\".tmp"', out)

    def _run(self, bruker_linje, files, ftp_host, remote_root):
        files_json = json.dumps(files)
        command = r"""
%s
$files = '%s' | ConvertFrom-Json
$objs = @($files | ForEach-Object { [PSCustomObject]@{ rel = $_.rel; TempFile = $_.TempFile } })
New-BolkNedlastingConfig -BrukerLinje '%s' -Filer $objs -FtpHost '%s' -RemoteRoot '%s'
""" % (
            self.func_text,
            files_json.replace("'", "''"),
            bruker_linje.replace("'", "''"),
            ftp_host.replace("'", "''"),
            remote_root.replace("'", "''"),
        )
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        return r.stdout


# ─── 3: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_new_functions_present_exactly_once(self):
        for name in (
            "Get-OwnerGateDeltaSjekkBeslutning",
            "New-BolkNedlastingConfig",
            "Invoke-DeployFileVerifiseringFtps",
            "Invoke-DeployBolkVerifiseringFtps",
        ):
            self.assertEqual(self.text.count(f"function {name}"), 1, f"{name} skal defineres nøyaktig én gang.")

    def test_delta_selection_never_references_production_baseurl_when_skipped(self):
        """Chief-krav (PR #216, runde 5): delta-utvelgelsen må ikke kunne
        nullstille testsettet basert på live produksjon. Beviser dette
        statisk: mellom `if ($deltaBeslutning.skipDelta) {` og dens egen
        lukkende `}` (owner-gate-grenen) finnes verken $BaseUrl,
        Invoke-DeployFileVerifisering eller Get-VerifiseringsStierForRetry
        -- $FilesToUpload settes direkte til hele $DeltaKandidatFiler, uten
        noen sammenligning mot produksjon i det hele tatt."""
        idx_if = self.text.index("if ($deltaBeslutning.skipDelta) {")
        idx_else = self.text.index("else {", idx_if)
        section = self.text[idx_if:idx_else]
        self.assertIn("$FilesToUpload = $DeltaKandidatFiler", section)
        self.assertIn("$SkippedCount = 0", section)
        self.assertNotIn("$BaseUrl", section)
        self.assertNotIn("Invoke-DeployFileVerifisering", section)
        self.assertNotIn("Get-VerifiseringsStierForRetry", section)

    def test_delta_check_still_https_and_unchanged_in_normal_mode(self):
        """The non-owner-gate branch (else) must remain byte-identical to
        the pre-existing delta-check mechanism."""
        idx_else = self.text.index("else {", self.text.index("if ($deltaBeslutning.skipDelta) {"))
        idx_dependency = self.text.index("# ─── 3. Dependency-sjekk")
        section = self.text[idx_else:idx_dependency]
        self.assertIn(
            "Invoke-DeployFileVerifisering -Rel $fc.rel -LocalPath $fc.FullName -BaseUrl $BaseUrl -TempDir $deltaTempDir",
            section,
        )
        self.assertIn("Get-VerifiseringsStierForRetry -Resultater $deltaResultater", section)

    def test_bolk_retry_reverification_uses_ftps_in_owner_gate_mode(self):
        section_start = self.text.index("# ─── 5c. Bolk-basert opplasting")
        section_end = self.text.index("# ─── 6. Produksjonsverifisering", section_start)
        section = self.text[section_start:section_end]
        self.assertIn(
            "Invoke-DeployFileVerifiseringFtps -Rel $f.rel -LocalPath $f.FullName -CurlConfigPath $curlConfigPath -FtpHost $FtpHost -RemoteRoot $RemoteRoot -TempDir $bolkRetryTempDir",
            section,
        )
        # Den eksisterende HTTPS-reverifiseringen (normal-modus) må fortsatt
        # ligge urørt i else-grenen ved siden av.
        self.assertIn(
            "Invoke-DeployFileVerifisering -Rel $f.rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $bolkRetryTempDir",
            section,
        )

    def test_step6_smoke_check_skipped_in_owner_gate_mode(self):
        section_start = self.text.index("# ─── 6. Produksjonsverifisering")
        idx_if = self.text.index("if ($isOwnerGateTest) {", section_start)
        idx_smoke_https = self.text.index("Verifiserer produksjon: rask HTTP-svar-sjekk")
        self.assertLess(idx_if, idx_smoke_https, "Smoke-sjekken skal ligge i else-grenen av en owner-gate-sjekk.")
        idx_owner_gate_skip_msg = self.text.index("Owner-gate testmodus: hopper over smoke-sjekken")
        self.assertLess(idx_if, idx_owner_gate_skip_msg)
        self.assertLess(idx_owner_gate_skip_msg, idx_smoke_https)

    def test_step6_content_verification_uses_bolk_ftps_against_remoteroot_in_owner_gate_mode(self):
        idx_step6 = self.text.index("# ─── 6. Produksjonsverifisering")
        idx_owner_gate_header = self.text.index("Verifiserer owner-gate testmål", idx_step6)
        idx_normal_header = self.text.index("--- Verifiserer produksjon: FAKTISK INNHOLD", idx_step6)
        self.assertLess(idx_owner_gate_header, idx_normal_header, "Owner-gate-grenen skal komme FØR normal-grenen (if/else).")
        section = self.text[idx_owner_gate_header:idx_normal_header]
        self.assertIn(
            "Invoke-DeployBolkVerifiseringFtps -Filer $DeltaKandidatFiler -BrukerLinje $configContent -FtpHost $FtpHost -RemoteRoot $RemoteRoot",
            section,
        )
        self.assertIn("Invoke-DeployFileVerifiseringFtps -Rel $fc.rel", section)
        self.assertNotIn("$BaseUrl", section, "Owner-gate-verifiseringen skal aldri konsultere produksjons-$BaseUrl.")

    def test_step6_normal_mode_still_uses_https_baseurl_unchanged(self):
        idx_normal_header = self.text.index("--- Verifiserer produksjon: FAKTISK INNHOLD")
        idx_mismatches = self.text.index("$mismatches = @($sluttResultat")
        section = self.text[idx_normal_header:idx_mismatches]
        self.assertEqual(section.count("Invoke-DeployFileVerifisering -Rel"), 2)
        self.assertIn("-BaseUrl $BaseUrl", section)

    def test_owner_gate_verification_covers_full_deploy_file_set(self):
        """Same requirement as normal mode (test_deploy_web_batch_upload.py):
        the post-upload verification must cover the FULL file list, not
        just files actually re-uploaded this run."""
        idx_step6 = self.text.index("# ─── 6. Produksjonsverifisering")
        idx_normal_header = self.text.index("--- Verifiserer produksjon: FAKTISK INNHOLD", idx_step6)
        section = self.text[idx_step6:idx_normal_header]
        self.assertIn("-Filer $DeltaKandidatFiler", section)

    def test_bolk_download_config_reuses_split_filer_i_bolker(self):
        func_text = _extract_function(self.text, "Invoke-DeployBolkVerifiseringFtps")
        self.assertIn("Split-FilerIBolker -Filer $Filer -BolkStorrelse $BolkStorrelse", func_text)

    def test_no_merge_or_new_push_command_introduced(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("git push", self.text)


if __name__ == "__main__":
    unittest.main()
