"""
Kvernhaug Agent Bridge V1.3 -- regresjonstester for permission-modellen
på "Run Claude Code"-steget (.github/workflows/claude-agent-bridge.yml,
issue #15).

BAKGRUNN (funnet på den første ekte E2E-kjøringen som kom forbi V1.2,
issue #14): workflow-kjøring 33667544306 trigget korrekt, autentiserte,
opprettet `agent/issue-14` lokalt -- og feilet lukket fordi Claude ikke
fikk skrive den etterspurte filen i det hele tatt (`Write` avvist både
i repoet og i `/tmp`). V1.2 ga en eksplisitt `--allowedTools`-liste for
Bash/git/gh, men ingen `--permission-mode` -- og uten den har den
headless SDK-en ingen prompt-handler, så enhver tilgang som havner på
"ask" avvises automatisk. Den offisielle tag-mode-implementasjonen
(verifisert mot den eksakte revisjonen som kjørte,
`8251c103ac8c1d761882c86aba1412c7f583c844`) legger med hensikt ALDRI
`Write`/`Edit` i `--allowedTools` -- den bruker i stedet
`--permission-mode acceptEdits`, som tillater filredigering INNENFOR
`$GITHUB_WORKSPACE` og fortsatt nekter skriving utenfor.

Denne testen inspiserer selve workflow-KILDETEKSTEN (ikke kjørt YAML --
ren streng-/regex-basert, stdlib-only, ingen PyYAML-avhengighet, siden
det ikke er en eksisterende suite-avhengighet i requirements.txt) og
beviser kontrakten issue #15 krevde:
- `--permission-mode acceptEdits` er satt på Claude-steget,
- `Write`/`Edit`/`MultiEdit` er IKKE eksplisitt gitt i --allowedTools,
- de branch-avgrensede eksakte push-reglene fra V1.2 (PR #13) er intakte,
- ingen `gh pr merge`, `git merge`, ubegrenset `git push *`, eller bar
  Bash-tillatelse er introdusert.

Kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests`).
"""
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")

_FORVENTEDE_PUSH_REGLER = (
    "Bash(git push -u origin ${{ steps.branch.outputs.name }})",
    "Bash(git push origin ${{ steps.branch.outputs.name }})",
)


def _les_workflow():
    with open(_WORKFLOW, encoding="utf-8") as f:
        return f.read()


def _run_claude_code_steg(tekst):
    """Returnerer kildeteksten for nøyaktig "Run Claude Code"-steget --
    fra dets `- name:`-linje til (men ikke med) neste steg på samme
    innrykksnivå, eller filslutt."""
    match = re.search(
        r"^([ \t]*)- name: Run Claude Code\n(.*?)(?=^\1- name:|\Z)",
        tekst, re.MULTILINE | re.DOTALL,
    )
    assert match, "Fant ikke 'Run Claude Code'-steget i workflowen -- testen forutsetter dette eksakte navnet."
    return match.group(0)


def _allowed_tools_liste(steg_tekst):
    match = re.search(r'--allowedTools "([^"]*)"', steg_tekst)
    assert match, "Fant ingen --allowedTools i 'Run Claude Code'-steget."
    return [entry.strip() for entry in match.group(1).split(",")]


class TestPermissionConfig(unittest.TestCase):
    def setUp(self):
        self.tekst = _les_workflow()
        self.steg = _run_claude_code_steg(self.tekst)
        self.verktoy = _allowed_tools_liste(self.steg)
        # Defensiv sanity-sjekk: en ødelagt regex som stille returnerer
        # en tom/triviell liste skulle gjort resten av testene meningsløse.
        self.assertGreaterEqual(len(self.verktoy), 15, "Uventet kort --allowedTools-liste -- sjekk regex-utpakkingen.")

    # ─── 1: selve V1.3-fiksen ────────────────────────────────────────────

    def test_1_permission_mode_acceptedits_er_satt_pa_claude_steget(self):
        self.assertIn("--permission-mode acceptEdits", self.steg)

    def test_1b_permission_mode_star_ikke_utenfor_claude_steget(self):
        # Sjekker at extraction-regexen faktisk fant STEGETS egen
        # --permission-mode, ikke en tilfeldig linje andre steder i filen.
        self.assertEqual(self.steg.count("--permission-mode"), 1)

    # ─── 2: Write/Edit/MultiEdit fortsatt IKKE eksplisitt gitt ──────────

    def test_2_write_edit_multiedit_ikke_eksplisitt_i_allowedtools(self):
        for verktoysnavn in ("Write", "Edit", "MultiEdit"):
            self.assertNotIn(
                verktoysnavn, self.verktoy,
                f"{verktoysnavn} skal ikke stå eksplisitt i --allowedTools -- "
                "acceptEdits dekker filredigering i $GITHUB_WORKSPACE alene.",
            )

    # ─── 3: branch-avgrensede push-regler (V1.2, PR #13) er intakte ─────

    def test_3_branch_scoped_push_regler_er_intakte(self):
        for regel in _FORVENTEDE_PUSH_REGLER:
            self.assertIn(regel, self.verktoy)

    def test_3b_ingen_andre_git_push_regler_enn_de_to_forventede(self):
        push_regler = [v for v in self.verktoy if v.startswith("Bash(git push")]
        self.assertEqual(
            sorted(push_regler), sorted(_FORVENTEDE_PUSH_REGLER),
            "Nøyaktig de to branch-avgrensede push-reglene skal finnes -- ingen flere, ingen færre.",
        )

    # ─── 4: ingen bred/farlig tilgang introdusert ────────────────────────

    def test_4_ingen_bar_bash_eller_bash_wildcard(self):
        for forbudt in ("Bash", "Bash(*)"):
            self.assertNotIn(forbudt, self.verktoy)

    def test_4b_ingen_ubegrenset_git_push_wildcard(self):
        self.assertNotIn("Bash(git push *)", self.verktoy)

    def test_4c_ingen_git_merge_kommando(self):
        for verktoysnavn in self.verktoy:
            self.assertFalse(
                verktoysnavn.startswith("Bash(git merge"),
                f"git merge skal aldri være tillatt: {verktoysnavn!r}",
            )

    def test_4d_ingen_gh_pr_merge_kommando(self):
        for verktoysnavn in self.verktoy:
            self.assertFalse(
                verktoysnavn.startswith("Bash(gh pr merge"),
                f"gh pr merge skal aldri være tillatt: {verktoysnavn!r}",
            )


if __name__ == "__main__":
    unittest.main()
