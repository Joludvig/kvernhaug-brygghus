"""
scripts/deploy_web.ps1 -- regresjonstester for login-preflighten (steg 5b)
i owner-gate testmodus mot et FERSKT, ikke-eksisterende isolert testmål
(issue #213, Chief review, PR #216, runde 7).

BAKGRUNN (owner-PC-gate reprodusert på eksakt hode
b71984adc3486970d3af78798301b462f1f2e72b): login-preflighten listet
tidligere ALLTID selve -RemoteRoot for å bekrefte at innloggingen fungerer
-- curl må cd'e inn i mappen for å liste den, noe som krever at mappen
allerede finnes på serveren. Owner-gate testmodus target derimot typisk et
FERSKT isolert testmål (f.eks. "/www-owner-gate-test") som ikke finnes før
selve opplastingen oppretter det via --ftp-create-dirs (se
New-BolkOpplastingConfig) -- preflighten feilet derfor deterministisk:

  curl: (9) Server denied you to change to the given directory
  FTP-innlogging feilet. Ingen filer ble lastet opp.

FIKSEN (denne filen tester): i owner-gate testmodus lister preflighten i
stedet -RemoteRoot sin FORELDER-mappe (for standardeksempelet
"/www-owner-gate-test" er det FTP-kontoens rot "/"), som alltid er
tilgjengelig uavhengig av om selve testmålet finnes ennå. Den nye rene
beslutningsfunksjonen Get-OwnerGatePreflightSti styrer dette. Normal deploy
(uten -OwnerGateTestSha) er HELT uendret -- lister fortsatt nøyaktig
-RemoteRoot, som alltid eksisterer (/www).

Dette endrer INGENTING ved hva som faktisk valideres for ugyldige
credentials/tilgang -- preflighten sjekker fortsatt curl sin exit-kode
akkurat som før (samme feilkoder, f.eks. 530 for feil credentials) --
kun HVILKEN mappe som listes.

TESTSTRATEGI (samme begrunnelse som de andre deploy_web-testfilene): hele
scriptets imperative flyt er Windows-orientert og krever
git.exe/curl.exe/ekte FTPS -- utenfor denne sandkassen, og forblir en
manuell/Windows owner-gate-verifisering. Det som DERIMOT faktisk kjøres
her, med ekte pwsh-prosesser (ikke mocket):

1. `Get-OwnerGatePreflightSti` -- ren beslutningsfunksjon, dot-sourcet
   direkte ut av den FAKTISKE scriptfilen, matet med syntetiske
   -RemoteRoot-verdier (inkludert nøyaktig det observerte
   "/www-owner-gate-test"-tilfellet, en nestet sti, og edge-caset der
   -RemoteRoot selv er "/").
2. Statiske kildetekst-/kontrakt-sjekker som beviser: preflight-kallet
   bruker $preflightSti (aldri lenger ubetinget $RemoteRoot direkte); at
   preflightens exit-kode-sjekk (fail-closed ved curl-feil) er uendret;
   og at $preflightSti beregnes FØR selve curl-kallet.

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


# ─── 1: Get-OwnerGatePreflightSti (ekte funksjon, dot-sourcet) ─────────────

class TestGetOwnerGatePreflightSti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.func_text = _extract_function(cls.script_text, "Get-OwnerGatePreflightSti")

    def test_normal_mode_returns_remote_root_unchanged(self):
        """Normal deploy (uten -OwnerGateTestSha) er HELT uendret -- lister
        fortsatt nøyaktig -RemoteRoot, akkurat som før denne fiksen."""
        self.assertEqual(self._run("/www", False), "/www")

    def test_owner_gate_single_segment_target_resolves_to_account_root(self):
        """Det EKSAKTE observerte tilfellet: -RemoteRoot "/www-owner-gate-test"
        (et fersk, ikke-eksisterende testmål) skal preflighte mot FTP-
        kontoens rot "/", som alltid er tilgjengelig."""
        self.assertEqual(self._run("/www-owner-gate-test", True), "/")

    def test_owner_gate_nested_target_resolves_to_parent(self):
        self.assertEqual(self._run("/foo/bar", True), "/foo")

    def test_owner_gate_target_with_trailing_slash_resolves_to_parent(self):
        self.assertEqual(self._run("/www-owner-gate-test/", True), "/")

    def test_owner_gate_root_itself_resolves_to_root(self):
        """Edge case: dersom -RemoteRoot selv er "/" (aldri en reell
        owner-gate-konfigurasjon, men funksjonen skal likevel ikke krasje
        eller returnere noe tomt/ugyldig)."""
        self.assertEqual(self._run("/", True), "/")

    def test_owner_gate_production_target_still_resolves_to_root(self):
        """Dersom owner-gate bevisst target normal produksjon
        (-OwnerGateAllowProductionTarget, -RemoteRoot "/www"), skal
        preflighten fortsatt liste roten, ikke /www selv -- /www eksisterer
        riktignok alltid i praksis, men funksjonen skal ikke skille
        spesialtilfeller basert på hvilken sti det er, kun på modus."""
        self.assertEqual(self._run("/www", True), "/")

    def _run(self, remote_root, is_owner_gate_test):
        command = r"""
%s
Get-OwnerGatePreflightSti -RemoteRoot '%s' -IsOwnerGateTest $%s
""" % (
            self.func_text,
            remote_root.replace("'", "''"),
            "true" if is_owner_gate_test else "false",
        )
        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        return r.stdout.strip()


# ─── 2: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_function_defined_exactly_once(self):
        self.assertEqual(self.text.count("function Get-OwnerGatePreflightSti"), 1)

    def test_preflight_sti_computed_before_curl_call(self):
        idx_compute = self.text.index(
            "$preflightSti = Get-OwnerGatePreflightSti -RemoteRoot $RemoteRoot -IsOwnerGateTest $isOwnerGateTest"
        )
        idx_curl = self.text.index(
            '& curl.exe -K $curlConfigPath --ssl-reqd --silent --show-error -o "NUL" "ftp://$FtpHost$preflightSti/"'
        )
        self.assertLess(idx_compute, idx_curl, "$preflightSti må beregnes FØR curl-kallet som bruker den.")

    def test_preflight_never_references_bare_remote_root_url_anymore(self):
        self.assertNotIn(
            '"ftp://$FtpHost$RemoteRoot/"', self.text,
            "Preflighten skal aldri lenger liste $RemoteRoot direkte -- kun via $preflightSti (Get-OwnerGatePreflightSti).",
        )

    def test_preflight_exit_code_check_unchanged(self):
        """Fail-closed-oppførselen ved ugyldige credentials/tilgang (curl
        exit != 0, f.eks. 530) er UENDRET -- kun HVILKEN mappe som listes
        er fikset, ikke selve feil-håndteringen."""
        for expected in (
            "$preflightExit = $LASTEXITCODE",
            "if ($preflightExit -ne 0) {",
            'Write-Host "FTP-innlogging feilet. Ingen filer ble lastet opp."',
            "$exitCode = 1",
        ):
            self.assertIn(expected, self.text, f"Preflight-feilhåndtering mangler/endret: {expected!r}")

    def test_normal_deploy_ftp_create_dirs_still_present_for_actual_upload(self):
        """Selve opplastingen (ikke preflighten) oppretter fortsatt et
        fersk owner-gate-testmål via --ftp-create-dirs -- preflight-fiksen
        over erstatter IKKE denne mekanismen, den unngår bare å kreve at
        mappen allerede finnes FØR opplastingen får sjansen til å opprette
        den."""
        self.assertIn("--ftp-create-dirs", self.text)

    def test_no_merge_or_new_push_command_introduced(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("git push", self.text)


if __name__ == "__main__":
    unittest.main()
