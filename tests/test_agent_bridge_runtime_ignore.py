"""
Kvernhaug Agent Bridge -- regresjonstester for branch-uavhengig
runtime-ignorering av `.agent_bridge_run/`
(.github/scripts/runtime_ignore.py, issue #333).

BAKGRUNN: issue #333s to gjenstående old-branch-kompatibilitetshull, begge
bevist på PR #328s eksakte, pre-#329-hode:

  1. `.agent_bridge_run/chief_review.md` (issue #329) og
     `.agent_bridge_run/AGENT_WORKFLOW.md` (denne issuen) skrives mens
     arbeidstreet står på DENNE klarerte master-checkouten, men
     changes-requested-banen bytter deretter arbeidstreet til en gammel
     feature-branch sitt eksakte reviewede hode. Den branchen kan predate
     `.agent_bridge_run/`-regelen i det sporede `.gitignore`-et og dermed
     IKKE ignorere katalogen i det hele tatt -- runtime-handoffen ville da
     stått ubeskyttet av branchens egen `.gitignore` etter byttet.
  2. Prompten pekte Claude på `docs/development/AGENT_WORKFLOW.md` uten å
     skille mellom DENNE klarerte kopien og en potensielt eldre kopi på den
     utsjekkede branchen -- se test_agent_bridge_changes_requested_context.py
     og claude-agent-bridge.yml for resten av #329/#331-kjeden dette bygger
     videre på.

Testene dekker:
  A. `beregn_ny_exclude_innhold` er ren, idempotent streng-logikk (ingen
     filsystem-/git-kall) -- legger til den ankrede linjen når den mangler,
     lar innholdet stå UENDRET når den allerede finnes, rører aldri annet
     innhold i filen.
  B. En EKTE, temporær Git-regresjon (issue #333s eget akseptansepunkt):
     et fixture-repo UTEN `.agent_bridge_run/` i noe SPORET `.gitignore`,
     `install`-CLI-en kjørt, runtime-filer opprettet, branch byttet, en bred
     `git add -A` kjørt -- og runtime-filene bevist å forbli usporet. Også:
     idempotens over to kjøringer, og at det sporede `.gitignore`-et aldri
     røres.
  C. Fail-closed når ignoreringen ikke kan bevises (kjørt utenfor et
     Git-repo).
  D. Statisk workflow-kildetekst-kontrakt: begge nye stegene finnes, kjører
     FØR `cr_context`/`cr_branch`/"Run Claude Code", er IKKE gatet til
     `status:changes-requested` (bevisst felles for begge trigger-etiketter),
     og prompten peker Claude på den stagede kontrakt-kopien -- aldri
     `docs/development/AGENT_WORKFLOW.md` direkte som eneste kilde. Ingen ny
     `--allowedTools`-overflate, ingen `git merge`/`gh pr merge`.

Ren stdlib-test (inkl. `subprocess`/`tempfile` for del B/C -- et ekte,
isolert temp-Git-repo, aldri dette repoets egen historikk). Kjøres av den
vanlige suiten (`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "runtime_ignore.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ri = _last_modul(_SCRIPT, "runtime_ignore")


def _les_workflow():
    with open(_WORKFLOW, encoding="utf-8") as f:
        return f.read()


def _steg_blokk(tekst, steg_id):
    """Rå YAML-tekst for steget med `id: <steg_id>`, fram til neste steg.
    Kommentarlinjer strippes -- samme mønster som
    test_agent_bridge_changes_requested_context.py::_steg_blokk."""
    m = re.search(
        r"\n      - name: [^\n]*\n(?:(?!\n      - name: ).)*?id: "
        + re.escape(steg_id)
        + r"\n(?:(?!\n      - name: ).)*",
        tekst,
        re.S,
    )
    assert m, f"fant ikke steg med id {steg_id!r} i workflowen"
    linjer = [l for l in m.group(0).splitlines() if not l.lstrip().startswith("#")]
    return "\n".join(linjer)


def _git(*args, cwd):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _skal_hoppe_over_git_tester():
    return shutil.which("git") is None


class TestBeregnNyExcludeInnhold(unittest.TestCase):
    """Akseptansepunkt A -- ren strenglogikk, ingen filsystem-/git-kall."""

    def test_a1_legger_til_naar_fil_er_tom(self):
        self.assertEqual(
            ri.beregn_ny_exclude_innhold(""),
            "/.agent_bridge_run/\n",
        )

    def test_a2_legger_til_bak_eksisterende_innhold(self):
        eksisterende = "# en kommentar\n*.tmp\n"
        ny = ri.beregn_ny_exclude_innhold(eksisterende)
        self.assertEqual(ny, "# en kommentar\n*.tmp\n/.agent_bridge_run/\n")

    def test_a3_normaliserer_manglende_avsluttende_linjeskift(self):
        ny = ri.beregn_ny_exclude_innhold("*.tmp")
        self.assertEqual(ny, "*.tmp\n/.agent_bridge_run/\n")

    def test_a4_idempotent_naar_linjen_allerede_finnes(self):
        eksisterende = "*.tmp\n/.agent_bridge_run/\n"
        self.assertEqual(ri.beregn_ny_exclude_innhold(eksisterende), eksisterende)

    def test_a5_gjenkjenner_linjen_uansett_posisjon(self):
        eksisterende = "/.agent_bridge_run/\n*.tmp\n"
        self.assertEqual(ri.beregn_ny_exclude_innhold(eksisterende), eksisterende)

    def test_a6_rorer_aldri_annet_innhold(self):
        eksisterende = "# uendret kommentar\nnode_modules/\n"
        ny = ri.beregn_ny_exclude_innhold(eksisterende)
        self.assertIn("# uendret kommentar\n", ny)
        self.assertIn("node_modules/\n", ny)

    def test_a7_dobbel_beregning_er_idempotent(self):
        forste = ri.beregn_ny_exclude_innhold("")
        andre = ri.beregn_ny_exclude_innhold(forste)
        self.assertEqual(forste, andre)


@unittest.skipIf(_skal_hoppe_over_git_tester(), "git er ikke tilgjengelig i dette miljøet")
class TestEktGitRegresjon(unittest.TestCase):
    """Akseptansepunkt B -- issue #333s eget krav: 'Include a real
    temporary-git regression test ... create a small repo/branch that
    lacks the .gitignore rule, use .git/info/exclude, create runtime
    files, switch branches, run git add -A, and prove runtime files stay
    unstaged.' Et isolert temp-repo, aldri dette repoets egen historikk."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="kbh_runtime_ignore_")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        _git("init", "-q", "-b", "master", cwd=self._tmp)
        _git("config", "user.email", "test@example.invalid", cwd=self._tmp)
        _git("config", "user.name", "KBH Test", cwd=self._tmp)
        # Fixture: en gammel branch UTEN `.agent_bridge_run/` i noe SPORET
        # `.gitignore` i det hele tatt -- akkurat PR #328s pre-#329-hode.
        with open(os.path.join(self._tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write("fixture repo\n")
        _git("add", "README.md", cwd=self._tmp)
        _git("commit", "-q", "-m", "initial", cwd=self._tmp)
        _git("branch", "old-feature", cwd=self._tmp)

    def _kjor_install(self):
        return subprocess.run(
            [sys.executable, _SCRIPT, "install"],
            cwd=self._tmp,
            capture_output=True,
            text=True,
        )

    def test_b1_install_lykkes_og_beviser_ignorering(self):
        resultat = self._kjor_install()
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("runtime_ignore_verified=true", resultat.stdout)

    def test_b2_skriver_kun_til_lokal_exclude_aldri_sporet_gitignore(self):
        self._kjor_install()
        exclude_sti = os.path.join(self._tmp, ".git", "info", "exclude")
        with open(exclude_sti, encoding="utf-8") as f:
            self.assertIn("/.agent_bridge_run/\n", f.read())
        self.assertFalse(
            os.path.exists(os.path.join(self._tmp, ".gitignore")),
            "install skal ALDRI opprette/røre et SPORET .gitignore",
        )

    def test_b3_idempotent_over_to_kjoringer(self):
        self._kjor_install()
        exclude_sti = os.path.join(self._tmp, ".git", "info", "exclude")
        with open(exclude_sti, encoding="utf-8") as f:
            forste_innhold = f.read()
        resultat = self._kjor_install()
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        with open(exclude_sti, encoding="utf-8") as f:
            andre_innhold = f.read()
        self.assertEqual(forste_innhold, andre_innhold)
        self.assertEqual(andre_innhold.count("/.agent_bridge_run/"), 1)

    def test_b4_runtime_filer_forblir_usporet_etter_branch_bytte_og_add_a(self):
        """Kjernescenariet: `.git/info/exclude` er per-klone metadata, IKKE
        del av noen branch sitt arbeidstre -- `git checkout` mellom to
        brancher endrer den aldri, så beskyttelsen holder uansett hvilken
        (gammel) branch som sjekkes ut etterpå."""
        self._kjor_install()

        agent_dir = os.path.join(self._tmp, ".agent_bridge_run")
        os.makedirs(agent_dir, exist_ok=True)
        with open(os.path.join(agent_dir, "chief_review.md"), "w", encoding="utf-8") as f:
            f.write("# Chief review\n")
        with open(os.path.join(agent_dir, "AGENT_WORKFLOW.md"), "w", encoding="utf-8") as f:
            f.write("# staged contract\n")

        # Byttet til fixture-branchen SOM MANGLER regelen i sitt sporede
        # .gitignore -- akkurat scenarioet issue #333 beskriver.
        _git("checkout", "-q", "old-feature", cwd=self._tmp)
        self.assertFalse(
            os.path.exists(os.path.join(self._tmp, ".gitignore")),
            "fixture-branchen skal fortsatt ikke ha noe sporet .gitignore",
        )

        _git("add", "-A", cwd=self._tmp)
        status = _git("status", "--porcelain", cwd=self._tmp).stdout
        self.assertNotIn(
            "chief_review.md",
            status,
            "runtime-filen ble staget av en bred 'git add -A' -- akkurat "
            "regresjonen issue #333 skal forhindre",
        )
        self.assertNotIn("AGENT_WORKFLOW.md", status)
        self.assertEqual(status.strip(), "", f"forventet INGEN staged/usporede endringer, fikk: {status!r}")

    def test_b5_check_ignore_bekrefter_kataloen_uavhengig_av_branch_gitignore(self):
        self._kjor_install()
        _git("checkout", "-q", "old-feature", cwd=self._tmp)
        probe = os.path.join(self._tmp, ".agent_bridge_run", "probe.txt")
        os.makedirs(os.path.dirname(probe), exist_ok=True)
        with open(probe, "w", encoding="utf-8") as f:
            f.write("")
        resultat = subprocess.run(
            ["git", "check-ignore", "-q", probe], cwd=self._tmp,
        )
        self.assertEqual(resultat.returncode, 0)


class TestFailClosed(unittest.TestCase):
    """Akseptansepunkt C -- ingen bevist ignorering, ingen "false"-antakelse."""

    @unittest.skipIf(_skal_hoppe_over_git_tester(), "git er ikke tilgjengelig i dette miljøet")
    def test_c1_feiler_lukket_utenfor_et_git_repo(self):
        tmp = tempfile.mkdtemp(prefix="kbh_runtime_ignore_no_git_")
        try:
            resultat = subprocess.run(
                [sys.executable, _SCRIPT, "install"],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
            self.assertEqual(resultat.returncode, 1)
            self.assertIn("runtime_ignore_verified=false", resultat.stdout)
            self.assertIn("reason=", resultat.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_c2_bevis_ignorert_feiler_lukket_naar_git_ikke_finnes(self):
        def _feilende_run(*args, **kwargs):
            raise FileNotFoundError("git ikke funnet")

        ekte_run = ri.subprocess.run
        ri.subprocess.run = _feilende_run
        try:
            with tempfile.TemporaryDirectory() as tmp:
                probe = os.path.join(tmp, ".agent_bridge_run", ".probe")
                bevist, begrunnelse = ri._bevis_ignorert(probe)
        finally:
            ri.subprocess.run = ekte_run
        self.assertFalse(bevist)
        self.assertIn("fail-closed", begrunnelse)


class TestWorkflowKobling(unittest.TestCase):
    """Akseptansepunkt D -- statisk kontrakt mot selve workflowen."""

    def setUp(self):
        self.tekst = _les_workflow()

    def test_d1_begge_stegene_finnes(self):
        for steg_id in ("runtime_ignore", "contract_stage"):
            with self.subTest(steg_id=steg_id):
                self.assertIn(f"id: {steg_id}\n", self.tekst)

    def test_d2_rekkefolge_for_cr_context_og_claude(self):
        i_ignore = self.tekst.index("id: runtime_ignore")
        i_stage = self.tekst.index("id: contract_stage")
        i_context = self.tekst.index("id: cr_context")
        i_branch = self.tekst.index("id: cr_branch")
        i_claude = self.tekst.index("id: claude")
        self.assertLess(i_ignore, i_stage, "ignoreringen MÅ installeres FØR kontrakten stages")
        self.assertLess(
            i_stage, i_context,
            "kontrakten MÅ stages FØR noen .agent_bridge_run/-fil skrives (cr_context)",
        )
        self.assertLess(
            i_context, i_branch,
            "begge de nye stegene MÅ skje FØR arbeidstreet byttes til det gamle hodet",
        )
        self.assertLess(i_branch, i_claude)

    def test_d2b_status_working_flyttes_for_runtime_oppsett(self):
        """Chief-review-fiks (PR #334, issue #333): lifecycle-transisjonen
        til `status:working` MÅ skje FØR de to runtime-oppsett-stegene
        (runtime_ignore, contract_stage) -- ellers kan et fail-closed
        runtime_ignore-/contract_stage-steg feile FØR issuen faktisk er
        flyttet til `status:working`, mens de generiske feilhåndterings-
        stegene lenger nede likevel unntaksfritt rapporterer 'Issue left
        at status:working', og på en changes-requested-runde ville det
        også latt den allerede konsumerte trigger-etiketten stå igjen.
        Låser hele rekkefølgen:
        Checkout -> Move to status:working -> runtime_ignore ->
        contract_stage -> cr_context -> ..."""
        i_checkout = self.tekst.index("fetch-depth: 0")
        i_status_working = self.tekst.index(
            "Move to status:working (exclusive lifecycle transition)"
        )
        i_ignore = self.tekst.index("id: runtime_ignore")
        i_stage = self.tekst.index("id: contract_stage")
        i_context = self.tekst.index("id: cr_context")
        self.assertLess(
            i_checkout, i_status_working,
            "den betrodde checkouten MÅ skje FØR lifecycle-transisjonen",
        )
        self.assertLess(
            i_status_working, i_ignore,
            "status:working MÅ settes FØR runtime_ignore -- ellers kan et "
            "fail-closed steg feile mens issuen fortsatt henger igjen på "
            "den utløsende status:ready/status:changes-requested-etiketten",
        )
        self.assertLess(i_ignore, i_stage)
        self.assertLess(i_stage, i_context)

    def test_d3_ignoreringen_kaller_den_pure_modulen(self):
        blokk = _steg_blokk(self.tekst, "runtime_ignore")
        self.assertIn("runtime_ignore.py install", blokk)
        self.assertIn('>> "$GITHUB_OUTPUT"', blokk)

    def test_d4_kontrakten_stages_fra_docs_til_agent_bridge_run(self):
        blokk = _steg_blokk(self.tekst, "contract_stage")
        self.assertIn("cp docs/development/AGENT_WORKFLOW.md .agent_bridge_run/AGENT_WORKFLOW.md", blokk)
        self.assertIn('echo "path=.agent_bridge_run/AGENT_WORKFLOW.md"', blokk)

    def test_d5_begge_stegene_er_ikke_gatet_til_changes_requested(self):
        """Bevisst felles for BEGGE trigger-etiketter -- se
        AGENT_WORKFLOW.md 'harmless common runtime setup'-tillatelsen."""
        for steg_id in ("runtime_ignore", "contract_stage"):
            with self.subTest(steg_id=steg_id):
                blokk = _steg_blokk(self.tekst, steg_id)
                self.assertNotIn("trigger_label", blokk)

    def test_d6_ingen_ny_merge_eller_master_push_overflate(self):
        for steg_id in ("runtime_ignore", "contract_stage"):
            blokk = _steg_blokk(self.tekst, steg_id)
            for forbudt in ("gh pr merge", "git merge", "git push", "git checkout", "git switch"):
                self.assertNotIn(forbudt, blokk, f"{forbudt!r} i steg {steg_id}")

    def test_d7_ingen_ny_allowedtools_overflate(self):
        allowed_tools_linje = re.search(r'--allowedTools "([^"]*)"', self.tekst)
        assert allowed_tools_linje
        for forbudt in ("runtime_ignore.py", "AGENT_WORKFLOW.md", "cp "):
            self.assertNotIn(
                forbudt, allowed_tools_linje.group(1),
                f"{forbudt!r} kjører som et workflow-jobbsteg, ikke gjennom Claudes --allowedTools",
            )

    def test_d8_prompten_peker_pa_den_stagede_kontrakten(self):
        i_prompt = self.tekst.index("prompt: |")
        prompt = self.tekst[i_prompt:]
        self.assertIn("`.agent_bridge_run/AGENT_WORKFLOW.md`", prompt)
        self.assertNotIn(
            "Agent Bridge (docs/development/AGENT_WORKFLOW.md",
            prompt,
            "prompten skal ikke lenger si at branchens EGEN "
            "docs/development/AGENT_WORKFLOW.md er den styrende kontrakten",
        )
        self.assertIn("historical", prompt.lower())

    def test_d9_chief_review_referansen_er_uendret(self):
        """Issue #329/#331s eksisterende .agent_bridge_run/chief_review.md
        -håndtering skal stå urørt av denne utvidelsen."""
        i_prompt = self.tekst.index("prompt: |")
        prompt = self.tekst[i_prompt:]
        self.assertIn("`.agent_bridge_run/chief_review.md`", prompt)


if __name__ == "__main__":
    unittest.main()
