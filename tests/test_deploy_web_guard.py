"""
scripts/deploy_web.ps1 -- regresjonstester for web/-cleanliness-guarden
(issue #72).

BAKGRUNN: en read-only verifisering på current master fant at
deploy-scriptets eksisterende HEAD==origin/master-guard IKKE fanger
ukommittert/staget/untracked innhold under web/ -- scriptet laster opp
CURRENT WORKING-TREE-bytes og verifiserer produksjon mot akkurat de samme
lokale bytene, så post-upload SHA-verifiseringen kan strukturelt aldri
oppdage en ukommittert web/-endring den selv lastet opp. Fiksen legger til
en ny guard (steg 1c) FØR filer enumereres:
`git status --porcelain --ignored=matching -- web/`, fail-closed på
modifisert/staget/slettet/untracked innhold under web/, README.md/
CHANGELOG.md unntatt (samme eksklusjonsliste som selve opplastingen
bruker), urelaterte urene filer utenfor web/ upåvirket, kjører også under
-DryRun.

CHIEF REVIEW-FIKS (PR #73, runde 2): `git status --porcelain` (uten
--ignored) viser aldri gitignorerte filer i det hele tatt, mens
fillistingen i steg 2 (`Get-ChildItem -Recurse -File`) enumererer
filsystemet direkte og laster opp ALT under web/ uansett .gitignore. En
lokal, gitignorert (*.log/*.tmp) men deployable fil under web/ var derfor
usynlig for guarden mens den likevel ville blitt lastet opp. Fikset ved å
legge til `--ignored=matching` på det samme git-kallet.

TESTSTRATEGI (eksplisitt begrunnet, per issue #72s egen instruks om ikke å
late som Linux-dekning erstatter Windows-dekning): hele scriptet er
Windows-orientert -- selve den FØRSTE guarden (`Get-Command git.exe`) krever
et bokstavelig `git.exe`-navngitt binærfil, som ikke finnes på denne Linux
pwsh-installasjonen (empirisk bekreftet: NOTFOUND). En full
`pwsh -File scripts/deploy_web.ps1`-kjøring feiler derfor på det
eksisterende, urelaterte dependency-sjekket FØR den nye guarden i det hele
tatt nås -- ekte Windows-ende-til-ende-kjøring er utenfor denne
sandkassen og forblir en manuell/Windows-CI-verifisering.

Det som DERIMOT faktisk kjøres og verifiseres her, med ekte prosesser (ikke
mocket):
1. `Get-UrentWebInnhold` -- guardens rene beslutningsfunksjon (trukket ut
   til egen funksjon, samme mønster som de eksisterende
   Get-CurlConfigEscaped/Get-CurlFeilmelding-hjelperne) -- kjøres med en
   ekte `pwsh`-prosess, dot-sourcet direkte ut av den FAKTISKE
   scriptfilen (ikke en kopi/re-implementasjon), matet med syntetiske
   `git status --porcelain`-linjer som dekker alle påkrevde tilfeller,
   inkludert `!!`-linjer (gitignorert innhold).
2. Selve git-kallet guarden bruker,
   `git status --porcelain --ignored=matching -- web/`, kjøres med ekte
   `git` mot et ekte fixture-repo med urent innhold både i og utenfor
   web/ -- beviser at pathspec-avgrensningen faktisk holder urelaterte
   urene filer (f.eks. eierens egen raw_data/unmatched_malt.json) utenfor
   treffmengden, OG at en gitignorert (*.log/*.tmp) fil under web/ likevel
   dukker opp mens en tilsvarende ignorert fil utenfor web/ ikke gjør det.
3. Statiske kildetekst-/kontrakt-sjekker (samme stil som
   tests/test_agent_bridge_permission_config.py) beviser at guarden er
   riktig koblet inn: plassert etter den eksisterende HEAD-guarden og før
   fillisting, kjører ubetinget av -DryRun, bruker nøyaktig ett
   `git status --porcelain --ignored=matching -- web/`-kall (ingen
   overflødig `git diff`/`git ls-files`), gjenbruker $ExcludeRelative i
   stedet for å duplisere den, og at den eksisterende HEAD/origin-guardens
   egen logikk/meldinger er urørt.

Kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
Krever `pwsh` og `git` i PATH (begge bekreftet tilgjengelige i dette
repoets CI-miljø).
"""
import json
import os
import subprocess
import tempfile
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


def _run_git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} failed: {r.stderr}"
    return r.stdout


# ─── 1: Get-UrentWebInnhold (ekte funksjon, dot-sourcet fra faktisk fil) ────

_CASES = [
    ("clean", [], []),
    ("modified_unstaged", [" M web/index.html"], ["web/index.html"]),
    ("staged", ["M  web/index.html"], ["web/index.html"]),
    ("untracked", ["?? web/new.html"], ["web/new.html"]),
    ("deleted_unstaged", [" D web/index.html"], ["web/index.html"]),
    ("deleted_staged", ["D  web/index.html"], ["web/index.html"]),
    ("excluded_readme_dirty", [" M web/README.md"], []),
    ("excluded_changelog_staged", ["M  web/CHANGELOG.md"], []),
    (
        "mixed_with_exclusions",
        [" M web/index.html", "?? web/x.html", " M web/README.md"],
        ["web/index.html", "web/x.html"],
    ),
    ("staged_rename", ["R  web/old.html -> web/new.html"], ["web/new.html", "web/old.html"]),
    ("ignored_tmp", ["!! web/foo.tmp"], ["web/foo.tmp"]),
    ("ignored_log", ["!! web/sub/foo.log"], ["web/sub/foo.log"]),
]


class TestGetUrentWebInnhold(unittest.TestCase):
    """Kjører den faktiske Get-UrentWebInnhold-funksjonen (trukket ut av
    scripts/deploy_web.ps1 selv, ikke en kopi) mot syntetiske porcelain-
    linjer, gjennom en ekte pwsh-prosess."""

    @classmethod
    def setUpClass(cls):
        cls.script_text = _read_script()
        cls.assertIn2 = None
        if "function Get-UrentWebInnhold" not in cls.script_text:
            raise AssertionError("Get-UrentWebInnhold ikke funnet i scripts/deploy_web.ps1 -- kan ikke kjøre testene.")

    def test_cases(self):
        cases_json = json.dumps([{"name": n, "lines": lines, "expect": expect} for n, lines, expect in _CASES])
        command = r"""
$content = Get-Content -Raw -Encoding UTF8 "%s"
if ($content -notmatch '(?s)function Get-UrentWebInnhold \{.*?\n\}\n') {
    Write-Output '{"error":"function_not_found"}'
    exit 1
}
Invoke-Expression $matches[0]

$cases = '%s' | ConvertFrom-Json
$results = @()
foreach ($c in $cases) {
    $lines = @($c.lines)
    $exclude = @("README.md", "CHANGELOG.md")
    $got = @(Get-UrentWebInnhold -PorcelainLinjer $lines -EkskluderteWebRelativeStier $exclude)
    $results += [PSCustomObject]@{ name = $c.name; got = $got }
}
$results | ConvertTo-Json -Depth 5 -Compress
""" % (_SCRIPT.replace("\\", "\\\\"), cases_json.replace("'", "''"))

        r = _run_pwsh(command)
        self.assertEqual(r.returncode, 0, f"pwsh feilet: stdout={r.stdout!r} stderr={r.stderr!r}")
        parsed = json.loads(r.stdout)
        if isinstance(parsed, dict):
            parsed = [parsed]
        results_by_name = {}
        for entry in parsed:
            got = entry.get("got", [])
            if got is None:
                got = []
            if isinstance(got, str):
                got = [got]
            results_by_name[entry["name"]] = sorted(got)

        for name, _lines, expect in _CASES:
            with self.subTest(case=name):
                self.assertIn(name, results_by_name, f"Case '{name}' manglet i pwsh-output: {r.stdout}")
                self.assertEqual(results_by_name[name], sorted(expect))


# ─── 2: ekte `git status --porcelain --ignored=matching -- web/` ──────────

class TestGitPorcelainScoping(unittest.TestCase):
    """Bygger et ekte fixture-repo og kjører det EKSAKTE git-kallet guarden
    bruker, for å bevise at pathspec-avgrensningen til web/ faktisk holder
    urelaterte urene filer utenfor treffmengden -- uavhengig av pwsh -- og
    at --ignored=matching faktisk fanger en gitignorert (*.log/*.tmp) men
    deployable fil under web/ (Chief review, PR #73)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        _run_git(["init", "-q", "-b", "master"], self.repo)
        _run_git(["config", "user.email", "t@example.com"], self.repo)
        _run_git(["config", "user.name", "T"], self.repo)
        os.makedirs(os.path.join(self.repo, "web"))
        for rel, content in (
            (".gitignore", "*.log\n*.tmp\n"),
            ("web/index.html", "hello\n"),
            ("web/README.md", "docs\n"),
            ("other.txt", "outside\n"),
        ):
            path = os.path.join(self.repo, rel)
            with open(path, "w") as f:
                f.write(content)
        _run_git(["add", "-A"], self.repo)
        _run_git(["commit", "-q", "-m", "init"], self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def _porcelain(self):
        out = _run_git(["status", "--porcelain", "--ignored=matching", "--", "web/"], self.repo)
        return [l for l in out.splitlines() if l.strip()]

    def test_clean_repo_yields_no_porcelain_lines(self):
        self.assertEqual(self._porcelain(), [])

    def test_modified_tracked_web_file_appears(self):
        with open(os.path.join(self.repo, "web", "index.html"), "a") as f:
            f.write("more\n")
        lines = self._porcelain()
        self.assertTrue(any("index.html" in l for l in lines))

    def test_staged_web_file_appears(self):
        with open(os.path.join(self.repo, "web", "index.html"), "a") as f:
            f.write("more\n")
        _run_git(["add", "web/index.html"], self.repo)
        lines = self._porcelain()
        self.assertTrue(any(l.startswith("M") and "index.html" in l for l in lines))

    def test_untracked_web_file_appears(self):
        with open(os.path.join(self.repo, "web", "new.html"), "w") as f:
            f.write("new\n")
        lines = self._porcelain()
        self.assertTrue(any(l.startswith("??") and "new.html" in l for l in lines))

    def test_deleted_web_file_appears(self):
        os.remove(os.path.join(self.repo, "web", "index.html"))
        lines = self._porcelain()
        self.assertTrue(any("index.html" in l for l in lines))

    def test_ignored_tmp_file_under_web_appears(self):
        """Chief review, PR #73: a gitignored (*.tmp) file under web/ is
        deployable (the upload enumeration in step 2 walks the filesystem
        directly, ignoring .gitignore entirely) but was invisible to plain
        `git status --porcelain` -- --ignored=matching must surface it."""
        with open(os.path.join(self.repo, "web", "foo.tmp"), "w") as f:
            f.write("scratch\n")
        lines = self._porcelain()
        self.assertTrue(any(l.startswith("!!") and "foo.tmp" in l for l in lines))

    def test_ignored_log_file_under_web_appears(self):
        os.makedirs(os.path.join(self.repo, "web", "sub"))
        with open(os.path.join(self.repo, "web", "sub", "foo.log"), "w") as f:
            f.write("scratch\n")
        lines = self._porcelain()
        self.assertTrue(any(l.startswith("!!") and "foo.log" in l for l in lines))

    def test_ignored_file_outside_web_is_excluded(self):
        with open(os.path.join(self.repo, "outside.log"), "w") as f:
            f.write("scratch\n")
        lines = self._porcelain()
        self.assertFalse(any("outside.log" in l for l in lines))

    def test_unrelated_dirty_file_outside_web_is_excluded(self):
        with open(os.path.join(self.repo, "other.txt"), "a") as f:
            f.write("more outside\n")
        with open(os.path.join(self.repo, "web", "index.html"), "a") as f:
            f.write("also dirty\n")
        lines = self._porcelain()
        self.assertFalse(any("other.txt" in l for l in lines))
        self.assertTrue(any("index.html" in l for l in lines))


# ─── 3: statiske kildetekst-/kontrakt-sjekker ──────────────────────────────

class TestSourceWiring(unittest.TestCase):
    def setUp(self):
        self.text = _read_script()

    def test_new_guard_git_call_present_exactly_once(self):
        self.assertEqual(
            self.text.count("git status --porcelain --ignored=matching -- web/"), 1,
            "Forventer nøyaktig ett git status --porcelain --ignored=matching -- web/-kall.",
        )

    def test_guard_git_call_includes_ignored_matching(self):
        """Chief review, PR #73: uten --ignored=matching er en gitignorert
        (*.log/*.tmp) men deployable fil under web/ usynlig for
        `git status --porcelain` (ignorerte filer vises kun via output når
        --ignored er eksplisitt satt), selv om fillistingen i steg 2 laster
        den opp uansett."""
        self.assertIn("--ignored=matching", self.text)

    def test_no_redundant_git_diff_or_ls_files_introduced(self):
        self.assertNotIn("git diff", self.text)
        self.assertNotIn("git ls-files", self.text)

    def test_guard_placed_after_head_guard_and_before_file_listing(self):
        idx_head_guard_ok = self.text.index('Write-Host "Guard OK -- HEAD matcher origin/master')
        idx_new_guard = self.text.index("git status --porcelain --ignored=matching -- web/")
        idx_file_listing = self.text.index("$AllFiles = Get-ChildItem -Path $WebRoot -Recurse -File")
        self.assertLess(idx_head_guard_ok, idx_new_guard, "Ny guard skal komme etter HEAD-guarden.")
        self.assertLess(idx_new_guard, idx_file_listing, "Ny guard skal komme før fillisting/enumerering.")

    def test_new_guard_not_gated_behind_dryrun(self):
        start = self.text.index("# ─── 1c. Guard:")
        end = self.text.index("# ─── 2. Runtime-filliste")
        section = self.text[start:end]
        self.assertNotIn("-not $DryRun", section)
        self.assertNotIn("if ($DryRun)", section)

    def test_exclude_relative_defined_exactly_once(self):
        self.assertEqual(self.text.count('$ExcludeRelative = @("README.md", "CHANGELOG.md")'), 1)

    def test_guard_reuses_exclude_relative_not_a_duplicate_list(self):
        start = self.text.index("# ─── 1c. Guard:")
        end = self.text.index("# ─── 2. Runtime-filliste")
        section = self.text[start:end]
        self.assertIn("Get-UrentWebInnhold -PorcelainLinjer $porcelain -EkskluderteWebRelativeStier $ExcludeRelative", section)

    def test_head_guard_core_logic_and_messages_unchanged(self):
        for expected in (
            "& git fetch origin master --quiet",
            'Write-Error "git fetch origin master feilet',
            "if ($localHead -ne $originMasterRef) {",
            'Write-Host "STOPPER: denne checkouten matcher IKKE origin/master."',
            'Write-Error "Ingen filer ble lastet opp -- checkout matcher ikke origin/master."',
        ):
            self.assertIn(expected, self.text, f"HEAD-guardens forventede kildetekst mangler/endret: {expected!r}")

    def test_docs_mention_new_guard(self):
        self.assertIn("issue #72", self.text)

    def test_new_guard_uses_dependency_free_pure_function(self):
        self.assertIn("function Get-UrentWebInnhold", self.text)


if __name__ == "__main__":
    unittest.main()
