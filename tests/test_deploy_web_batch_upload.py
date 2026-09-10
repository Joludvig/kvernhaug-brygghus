"""
scripts/deploy_web.ps1 -- regresjonstester for delta-sjekk og bolk-basert
FTPS-opplasting (issue #213).

BAKGRUNN: en owner-PC deploy mot frossen RELEASE_SHA d2afc6e traff et
deterministisk FTPS-tilkoblingstak -- scriptet lastet opp ÉN fil per
curl.exe-prosess (og dermed én ny FTPS-innlogging/TLS-håndtrykk per fil),
og serveren sluttet å svare (curl exit 56, CURLE_RECV_ERROR) rundt fil #51
av 85, identisk to ganger på rad. Fiksen:

1. En read-only HTTPS-delta-sjekk (steg 2b) FØR noen FTPS-tilkobling åpnes
   -- hopper over filer som allerede er byte-identiske med produksjon (kun
   faktiske avvik/manglende filer sendes til opplasting).
2. Filene som faktisk skal lastes opp samles i bolker (maks 10 filer) og
   lastes opp med ÉN curl.exe-prosess per bolk (url/-T-blokker adskilt med
   --next i samme -K configfil) -- reduserer et 85-filers full-sync-deploy
   fra 85 til maks 9 FTPS-tilkoblinger, komfortabelt under det observerte
   taket rundt ~50.
3. En bolk som feiler med en FORBIGÅENDE curl-avslutningskode (55/56/18 --
   send/motta/delvis-overføring-feil) reverifiseres FØRST mot produksjon
   over HTTPS (samme mekanisme som delta-sjekken) og reduseres til kun
   fortsatt avvikende/manglende/ikke-verifiserbare filer -- er ingen
   igjen, regnes bolken som vellykket uten noe nytt curl-forsøk; ellers
   prøves KUN de gjenværende filene på nytt, ÉN gang, etter en kort pause
   (Chief review, PR #216, blocker 2 -- exit 56 ble observert ETTER at
   filen faktisk hadde kommet frem, så et blindt retry av hele bolken
   ville lastet opp allerede-vellykkede filer på nytt). Ekte feil (67
   login denied, 9 tilgang nektet, 78 mangler sti, 35 TLS-håndtrykk)
   stopper deployen umiddelbart, uten retry -- akkurat som det
   eksisterende "stopp ved første feil"-prinsippet (Runde 22B.1).
4. Credential-linjen (`user = "..."`) gjentas EKSPLISITT i HVER
   --next-blokk i bolk-configen, ikke bare skrevet én gang først -- curl
   dokumenterer at --next nullstiller alle ikke-globale opsjoner, og
   `user = ...` er ikke global (Chief review, PR #216, blocker 1).

TESTSTRATEGI (samme begrunnelse som test_deploy_web_guard.py og
test_deploy_web_verify_retry.py): hele scriptet er Windows-orientert, og
selve den FØRSTE guarden (`Get-Command git.exe`) krever et bokstavelig
`git.exe`-navngitt binærfil som ikke finnes på denne Linux
pwsh-installasjonen -- en full `pwsh -File scripts/deploy_web.ps1`-kjøring
(med ekte FTP/HTTPS) er derfor utenfor denne sandkassen og forblir en
manuell/Windows-verifisering, akkurat som curl sin faktiske
FTPS-tilkoblingsgjenbruk på tvers av --next-adskilte overføringer (denne
fiksens kjerneantakelse, dokumentert curl-oppførsel) ikke kan bekreftes
empirisk her.

Det som DERIMOT faktisk kjøres her, med ekte pwsh-prosesser (ikke mocket):
1. `Test-ForbigaendeCurlFeil` og `Split-FilerIBolker` -- rene funksjoner,
   dot-sourcet direkte ut av den FAKTISKE scriptfilen, matet med
   syntetiske verdier.
2. `New-BolkOpplastingConfig` (dot-sourcet sammen med Get-CurlConfigEscaped,
   som den selv kaller for escaping) -- ren tekstbygging, verifisert mot
   eksakt forventet -K-configinnhold (url/-T-blokker, --next-adskillere,
   --ssl-reqd/--ftp-create-dirs per blokk, escaping av spesialtegn).
3. Et fullt PowerShell-parse-sjekk av HELE scriptfilen (ingen kjøring,
   kun `[System.Management.Automation.Language.Parser]::ParseFile`) --
   kritisk sikkerhetsnett siden selve den imperative opplastingsflyten
   ikke kan kjøres ende-til-ende i denne sandkassen.
4. Statiske kildetekst-/kontrakt-sjekker (samme stil som
   TestSourceWiring i de to andre deploy_web-testfilene) som beviser:
   delta-sjekken ligger etter DryRun sin exit 0 og før dependency-sjekken,
   bolk-opplastingen bruker --fail-early, det gamle per-fil curl-kallet er
   fjernet (ikke bare lagt til ved siden av), og alle fire eksisterende
   guards/produksjonsverifiseringen er urørt.

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


# ─── 1: Test-ForbigaendeCurlFeil (ekte funksjon, dot-sourcet, selvstendig) ─

class TestForbigaendeCurlFeil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Test-ForbigaendeCurlFeil")

    def test_transient_codes_are_true(self):
        for code in (55, 56, 18):
            with self.subTest(code=code):
                self.assertTrue(self._run(code))

    def test_hard_failure_codes_are_false(self):
        """67 (login denied), 9 (access denied), 78 (missing path), 35 (TLS
        handshake) must NEVER be treated as transient -- masking these would
        hide a real, reproducible failure behind an automatic retry."""
        for code in (67, 9, 78, 35, 0, 1, 99):
            with self.subTest(code=code):
                self.assertFalse(self._run(code))

    def _run(self, code):
        command = r"""
%s
$got = Test-ForbigaendeCurlFeil -ExitCode %d
if ($got) { "true" } else { "false" }
""" % (self.func_text, code)
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        return r.stdout.strip() == "true"


# ─── 2: Split-FilerIBolker (ekte funksjon, dot-sourcet) ────────────────────

class TestSplitFilerIBolker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Split-FilerIBolker")

    def test_empty_list_yields_no_chunks(self):
        self.assertEqual(self._run([], 10), [])

    def test_exact_multiple_splits_evenly(self):
        files = [f"f{i}" for i in range(20)]
        got = self._run(files, 10)
        self.assertEqual([len(c) for c in got], [10, 10])

    def test_remainder_forms_smaller_last_chunk(self):
        files = [f"f{i}" for i in range(23)]
        got = self._run(files, 10)
        self.assertEqual([len(c) for c in got], [10, 10, 3])

    def test_chunk_size_larger_than_list_yields_one_chunk(self):
        files = [f"f{i}" for i in range(5)]
        got = self._run(files, 10)
        self.assertEqual([len(c) for c in got], [5])

    def test_single_file_yields_one_chunk_of_one(self):
        got = self._run(["only.html"], 10)
        self.assertEqual(got, [["only.html"]])

    def test_order_is_preserved_within_and_across_chunks(self):
        files = [f"f{i}" for i in range(15)]
        got = self._run(files, 10)
        flattened = [x for chunk in got for x in chunk]
        self.assertEqual(flattened, files)

    def _run(self, files, chunk_size):
        files_json = json.dumps([{"rel": f} for f in files])
        command = r"""
%s
$files = '%s' | ConvertFrom-Json
$objs = @($files | ForEach-Object { [PSCustomObject]@{ rel = $_.rel } })
$got = @(Split-FilerIBolker -Filer $objs -BolkStorrelse %d)
$out = @($got | ForEach-Object { , @($_ | ForEach-Object { $_.rel }) })
ConvertTo-Json -InputObject $out -Depth 5 -Compress
""" % (self.func_text, files_json.replace("'", "''"), chunk_size)
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        out = r.stdout.strip()
        if not out:
            return []
        parsed = json.loads(out)
        if not parsed:
            return []
        if isinstance(parsed[0], str):
            return [parsed]
        return [([x] if isinstance(x, str) else x) for x in parsed]


# ─── 3: New-BolkOpplastingConfig (ekte funksjon + Get-CurlConfigEscaped) ───

class TestNewBolkOpplastingConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = (
            _extract_function(cls.script_text, "Get-CurlConfigEscaped")
            + _extract_function(cls.script_text, "New-BolkOpplastingConfig")
        )

    def test_single_file_block_structure(self):
        out = self._run("user = \"u:p\"", [{"rel": "index.html", "FullName": "/tmp/web/index.html"}], "ftp.example.com", "/www")
        self.assertTrue(out.startswith("user = \"u:p\"\n"))
        self.assertIn('url = "ftp://ftp.example.com/www/index.html"', out)
        self.assertIn("--ssl-reqd", out)
        self.assertIn("--ftp-create-dirs", out)
        self.assertIn('-T "/tmp/web/index.html"', out)
        self.assertNotIn("--next", out, "Ingen --next skal finnes med bare ÉN fil i bolken.")

    def test_multiple_files_separated_by_next_not_after_last(self):
        files = [
            {"rel": "a.html", "FullName": "/tmp/web/a.html"},
            {"rel": "b.html", "FullName": "/tmp/web/b.html"},
            {"rel": "c.html", "FullName": "/tmp/web/c.html"},
        ]
        out = self._run("user = \"u:p\"", files, "ftp.example.com", "/www")
        self.assertEqual(out.count("--next"), 2, "N filer skal ha nøyaktig N-1 --next-adskillere.")
        self.assertEqual(out.count("url = "), 3)
        self.assertEqual(out.count("--ssl-reqd"), 3, "--ssl-reqd skal gjentas EKSPLISITT for hver fil, ikke arves på tvers av --next.")
        self.assertEqual(out.count("--ftp-create-dirs"), 3)
        self.assertFalse(out.rstrip("\n").endswith("--next"), "Skal ikke ha en løs --next etter siste blokk.")
        idx_a = out.index("a.html")
        idx_b = out.index("b.html")
        idx_c = out.index("c.html")
        self.assertLess(idx_a, idx_b)
        self.assertLess(idx_b, idx_c)

    def test_credential_line_repeated_once_per_block_not_just_first(self):
        """curl documents that --next resets ALL non-global options -- `user
        = "..."` is not global, so without repeating it in every --next
        block, only transfer 1 in the batch would actually carry explicit
        FTPS credentials (Chief review, PR #216, blocker 1). Every block
        must carry its own credential line, immediately before its own
        `url =` line, in file order."""
        files = [
            {"rel": "a.html", "FullName": "/tmp/web/a.html"},
            {"rel": "b.html", "FullName": "/tmp/web/b.html"},
            {"rel": "c.html", "FullName": "/tmp/web/c.html"},
        ]
        out = self._run("user = \"u:p\"", files, "ftp.example.com", "/www")
        self.assertEqual(
            out.count('user = "u:p"'), 3,
            "Credential-linjen skal gjentas i HVER --next-blokk, ikke bare skrives én gang først.",
        )
        for block in out.split("--next"):
            self.assertRegex(
                block.strip(), r'^user = "u:p"\nurl = ',
                "Hver blokk skal starte med credential-linjen umiddelbart før sin egen url-linje.",
            )

    def test_special_characters_in_path_are_escaped(self):
        """A local path containing a backslash or double-quote must be
        escaped exactly like the credential line already is (Get-CurlConfigEscaped
        reused, not re-implemented) -- an unescaped quote would corrupt the
        -K config's own block boundaries."""
        files = [{"rel": "weird.html", "FullName": 'C:\\web\\weird "file".html'}]
        out = self._run("user = \"u:p\"", files, "ftp.example.com", "/www")
        self.assertIn('-T "C:\\\\web\\\\weird \\"file\\".html"', out)

    def _run(self, bruker_linje, files, ftp_host, remote_root):
        files_json = json.dumps(files)
        command = r"""
%s
$files = '%s' | ConvertFrom-Json
$objs = @($files | ForEach-Object { [PSCustomObject]@{ rel = $_.rel; FullName = $_.FullName } })
New-BolkOpplastingConfig -BrukerLinje '%s' -Filer $objs -FtpHost '%s' -RemoteRoot '%s'
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


# ─── 4: hele scriptet parser uten syntaksfeil ──────────────────────────────

class TestScriptParses(unittest.TestCase):
    """Kjører aldri den imperative flyten (krever git.exe/curl.exe/ekte
    FTPS+HTTPS, utenfor denne sandkassen) -- men PowerShell sin egen parser
    kan bekrefte at HELE filen (inkludert de nye seksjonene 2b/5c fra denne
    endringen) er syntaktisk gyldig, uten å kjøre noe av den."""

    def test_no_parse_errors(self):
        command = r"""
$errors = $null
$tokens = $null
[System.Management.Automation.Language.Parser]::ParseFile("%s", [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Output $_.ToString() }
    exit 1
}
exit 0
""" % _SCRIPT.replace("\\", "\\\\")
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"scripts/deploy_web.ps1 har parse-feil:\n{r.stdout}\n{r.stderr}")


# ─── 5: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_new_functions_present_exactly_once(self):
        for name in ("Test-ForbigaendeCurlFeil", "Split-FilerIBolker", "New-BolkOpplastingConfig"):
            self.assertEqual(self.text.count(f"function {name}"), 1, f"{name} skal defineres nøyaktig én gang.")

    def test_delta_check_after_dryrun_exit_and_before_dependency_check(self):
        idx_dryrun_exit = self.text.index('Write-Host "$($DeployFiles.Count) filer ville blitt lastet opp')
        idx_delta_check = self.text.index("Delta-sjekk: sammenligner")
        idx_dependency = self.text.index("# ─── 3. Dependency-sjekk")
        self.assertLess(idx_dryrun_exit, idx_delta_check, "Delta-sjekken skal ligge ETTER DryRun sin exit 0 (0-tilkoblinger-kontrakten).")
        self.assertLess(idx_delta_check, idx_dependency, "Delta-sjekken skal ligge FØR curl-dependency-sjekken.")

    def test_delta_check_reuses_existing_verification_function_not_a_duplicate(self):
        self.assertIn(
            "Invoke-DeployFileVerifisering -Rel $fc.rel -LocalPath $fc.FullName -BaseUrl $BaseUrl -TempDir $deltaTempDir",
            self.text,
        )
        self.assertIn("Get-VerifiseringsStierForRetry -Resultater $deltaResultater", self.text)

    def test_old_per_file_curl_invocation_removed(self):
        """The original one-curl-process-per-file loop must actually be GONE
        -- not merely superseded by dead code sitting alongside it."""
        self.assertNotIn(
            '& curl.exe -K $curlConfigPath --ssl-reqd --ftp-create-dirs --silent --show-error -T "$($f.FullName)" "$remoteUrl"',
            self.text,
        )

    def test_batch_upload_uses_fail_early(self):
        self.assertIn("--fail-early", self.text)

    def test_batch_retry_is_bounded_not_a_loop(self):
        """Exactly one bounded retry per chunk (first attempt + one retry),
        gated on Test-ForbigaendeCurlFeil -- never an open-ended while(true)
        polling loop for the chunk-level retry itself."""
        self.assertIn("$MaxBolkOpplastingsForsok = 2", self.text)
        self.assertIn("Test-ForbigaendeCurlFeil -ExitCode $sisteExitCode", self.text)

    def test_hard_failure_still_stops_immediately_no_retry(self):
        section_start = self.text.index("# ─── 5c. Bolk-basert opplasting")
        section_end = self.text.index("# ─── 6. Produksjonsverifisering", section_start)
        section = self.text[section_start:section_end]
        self.assertIn("erForbigaende) -or", section)

    def test_transient_failure_reverifies_before_retry_not_blind_reupload(self):
        """Chief review (PR #216, blocker 2): curl exit 56 was observed
        AFTER the file had already arrived, so blindly retrying the whole
        chunk would re-upload files that already succeeded. Before any
        retry attempt, the remaining chunk must be reverified over HTTPS
        (the same mechanism as the delta-check/production-verification) and
        reduced to only files still differing/missing/unverifiable."""
        section_start = self.text.index("# ─── 5c. Bolk-basert opplasting")
        section_end = self.text.index("# ─── 6. Produksjonsverifisering", section_start)
        section = self.text[section_start:section_end]
        self.assertIn(
            "Invoke-DeployFileVerifisering -Rel $f.rel -LocalPath $f.FullName -BaseUrl $BaseUrl -TempDir $bolkRetryTempDir",
            section,
            "Reverifisering før retry skal gjenbruke Invoke-DeployFileVerifisering, ikke en egen duplikatimplementasjon.",
        )
        self.assertIn(
            "Get-VerifiseringsStierForRetry -Resultater $bolkRetryResultater",
            section,
            "Reverifiseringsresultatet skal filtreres med samme rene utvelgelsesfunksjon som delta-sjekken/produksjonsverifiseringen bruker.",
        )
        idx_reverify = section.index("Get-VerifiseringsStierForRetry -Resultater $bolkRetryResultater")
        idx_retry_curl = section.rindex("& curl.exe -K $bolkConfigPath")
        self.assertLess(idx_retry_curl, idx_reverify, "Reverifiseringen skal skje ETTER det feilede curl-forsøket (og dermed FØR neste).")

    def test_fully_reverified_chunk_counts_as_success_without_reupload(self):
        """If reverification shows every remaining file already matches
        production, the chunk must be treated as successful -- no further
        curl invocation for files that already arrived (Chief review, PR
        #216, blocker 2)."""
        section_start = self.text.index("# ─── 5c. Bolk-basert opplasting")
        section_end = self.text.index("# ─── 6. Produksjonsverifisering", section_start)
        section = self.text[section_start:section_end]
        self.assertIn("$gjenstaendeFiler.Count -eq 0", section)
        idx_zero_check = section.index("$gjenstaendeFiler.Count -eq 0")
        idx_bolkok_true = section.index("$bolkOk = $true", idx_zero_check)
        idx_break = section.index("break", idx_bolkok_true)
        self.assertLess(idx_zero_check, idx_bolkok_true)
        self.assertLess(idx_bolkok_true, idx_break)

    def test_retry_uses_reduced_file_set_not_original_full_chunk(self):
        """The retried curl config must be built from the shrunk
        $gjenstaendeFiler set (survivors of reverification), not the
        original, unreduced $bolk -- otherwise the reverification step
        would compute a smaller set but never actually act on it."""
        section_start = self.text.index("# ─── 5c. Bolk-basert opplasting")
        section_end = self.text.index("# ─── 6. Produksjonsverifisering", section_start)
        section = self.text[section_start:section_end]
        self.assertIn(
            "New-BolkOpplastingConfig -BrukerLinje $configContent -Filer $gjenstaendeFiler -FtpHost $FtpHost -RemoteRoot $RemoteRoot",
            section,
        )
        self.assertNotIn(
            "New-BolkOpplastingConfig -BrukerLinje $configContent -Filer $bolk -FtpHost $FtpHost -RemoteRoot $RemoteRoot",
            section,
            "Bolk-configen skal bygges fra det (potensielt reduserte) $gjenstaendeFiler-settet, ikke ubetinget fra hele $bolk.",
        )

    def test_login_preflight_unchanged(self):
        for expected in (
            '& curl.exe -K $curlConfigPath --ssl-reqd --silent --show-error -o "NUL" "ftp://$FtpHost$RemoteRoot/"',
            'Write-Host "--- Preflight: verifiserer FTP-innlogging (read-only, 0 writes) ---"',
        ):
            self.assertIn(expected, self.text, f"Login-preflight kildetekst mangler/endret: {expected!r}")

    def test_existing_guards_untouched(self):
        for expected in (
            "& git fetch origin master --quiet",
            "if ($localHead -ne $originMasterRef) {",
            "git status --porcelain --ignored=matching -- web/",
            "function Get-UrentWebInnhold",
            '$ExcludeRelative = @("README.md", "CHANGELOG.md")',
        ):
            self.assertIn(expected, self.text, f"Eksisterende guard-kildetekst mangler/endret: {expected!r}")

    def test_production_verification_section_still_covers_all_deploy_files(self):
        """Section 6 must keep verifying the FULL $DeployFiles list (not
        just the files that were actually uploaded this run) -- files
        skipped by the delta-check were only proven correct seconds
        earlier, but the post-upload verification is the one authoritative
        final check and must not narrow its own scope."""
        idx_verify = self.text.index("--- Verifiserer produksjon: FAKTISK INNHOLD")
        section = self.text[idx_verify:]
        self.assertIn("foreach ($f in $DeployFiles) {", section)

    def test_base_url_defined_exactly_once(self):
        self.assertEqual(self.text.count('$BaseUrl = "https://kvernhaugbrygghus.no"'), 1)

    def test_no_merge_or_new_push_command_introduced(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("git push", self.text)


if __name__ == "__main__":
    unittest.main()
