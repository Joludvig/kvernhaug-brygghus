"""
Kvernhaug Agent Bridge V1.3/V1.4/V1.5 -- regresjonstester for
permission-modellen på "Run Claude Code"-steget
(.github/workflows/claude-agent-bridge.yml, issue #15 / issue #154 /
issue #201).

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

V1.4 (issue #154) utvider samme suite til å bevise at det eksakte,
argumentfrie generator-kallet `Bash(python3 scripts/generate_web_i18n_pages.py)`
er lagt til -- nøyaktig én gang, uten noen bredere `python3 *`/
`python3 scripts/*`-variant, og uten at noe av det V1.2/V1.3 allerede
beviste (branch-avgrensede push-regler, fravær av `git merge`/`gh pr
merge`, `--permission-mode acceptEdits`, fravær av `Write`/`Edit`/
`MultiEdit`) har endret seg.

V1.5 (issue #201) utvider samme suite igjen: #200s første Bridge-kjøring
(34447715101) fullførte Claude-steget men rapporterte
`permission_denials_count: 2` og produserte verken branch eller PR,
fordi `--allowedTools` aldri inneholdt noen Node/npm/Playwright-kommando
i det hele tatt. Denne bolken beviser at den eksakte, avgrensede pakken
issue #201 spesifiserer -- ni regler, åtte eksakte/argument-faste og én
prefiks-regel avgrenset til `npx playwright test` -- er lagt til
nøyaktig én gang hver, uten noen bredere `npm *`/`npx *`/`node *`-variant
og uten `curl`/`wget`/`sudo`, og uten at noe av det V1.2/V1.3/V1.4
allerede beviste (branch-avgrensede push-regler, fravær av `git merge`/
`gh pr merge`, `--permission-mode acceptEdits`, fravær av `Write`/
`Edit`/`MultiEdit`, de eksisterende Python/i18n-reglene) har endret seg.

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

_GENERATOR_REGEL = "Bash(python3 scripts/generate_web_i18n_pages.py)"

_NODE_PLAYWRIGHT_REGLER = (
    "Bash(node --version)",
    "Bash(npm --version)",
    "Bash(npm install --save-dev @playwright/test)",
    "Bash(npm install --ignore-scripts)",
    "Bash(npm ci --ignore-scripts)",
    "Bash(npx playwright --version)",
    "Bash(npx playwright install chromium firefox)",
    "Bash(npx playwright install --with-deps chromium firefox)",
    "Bash(npx playwright test *)",
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

    # ─── 5 (V1.4, issue #154): kanonisk Web i18n-generator, eksakt og alene ──

    def test_5a_generator_regelen_finnes_eksakt(self):
        self.assertIn(
            _GENERATOR_REGEL, self.verktoy,
            "Den eksakte generator-regelen mangler i --allowedTools (issue #154).",
        )

    def test_5b_generator_regelen_forekommer_noyaktig_en_gang(self):
        self.assertEqual(
            self.verktoy.count(_GENERATOR_REGEL), 1,
            "Generator-regelen skal forekomme nøyaktig én gang -- ingen duplikater.",
        )

    def test_5c_ingen_bredere_python3_variant_introdusert(self):
        forbudte = (
            "Bash(python3 *)",
            "Bash(python3 scripts/*)",
            "Bash(python3 scripts/generate_web_i18n_pages.py *)",
            "Bash(python3 scripts/generate_web_i18n_pages.py*)",
        )
        for forbudt in forbudte:
            self.assertNotIn(
                forbudt, self.verktoy,
                f"Bredere Python-tilgang enn den eksakte generator-regelen skal ikke finnes: {forbudt!r}",
            )

    def test_5d_kun_to_python3_regler_totalt(self):
        # Nøyaktig `python3 -m unittest *` (V1.2) og den nye eksakte
        # generator-regelen (V1.4) -- ingen tredje/bredere Python-inngang.
        python3_regler = [v for v in self.verktoy if "python3" in v]
        self.assertEqual(
            sorted(python3_regler),
            sorted(["Bash(python3 -m unittest *)", _GENERATOR_REGEL]),
        )

    # ─── 6 (V1.4, issue #154): resten av V1.2/V1.3-kontrakten er uendret ────

    def test_6_eksisterende_kontrakt_star_ved_lag_etter_generator_tillegget(self):
        # Gjentar kravene 4-7 fra issue #154 eksplisitt i denne bolken, slik
        # at en fremtidig lesning av testfilen ser at generator-tillegget
        # ikke svekket noe av det V1.2/V1.3 allerede beviste.
        for regel in _FORVENTEDE_PUSH_REGLER:
            self.assertIn(regel, self.verktoy)
        push_regler = [v for v in self.verktoy if v.startswith("Bash(git push")]
        self.assertEqual(sorted(push_regler), sorted(_FORVENTEDE_PUSH_REGLER))
        for verktoysnavn in self.verktoy:
            self.assertFalse(verktoysnavn.startswith("Bash(git merge"))
            self.assertFalse(verktoysnavn.startswith("Bash(gh pr merge"))
        self.assertIn("--permission-mode acceptEdits", self.steg)
        for verktoysnavn in ("Write", "Edit", "MultiEdit"):
            self.assertNotIn(verktoysnavn, self.verktoy)

    # ─── 7 (V1.5, issue #201): bundet Node/Playwright-pakke ──────────────

    def test_7a_alle_node_playwright_reglene_finnes_eksakt(self):
        for regel in _NODE_PLAYWRIGHT_REGLER:
            self.assertIn(
                regel, self.verktoy,
                f"Node/Playwright-regelen mangler i --allowedTools (issue #201): {regel!r}",
            )

    def test_7b_hver_node_playwright_regel_forekommer_noyaktig_en_gang(self):
        for regel in _NODE_PLAYWRIGHT_REGLER:
            self.assertEqual(
                self.verktoy.count(regel), 1,
                f"Regelen skal forekomme nøyaktig én gang -- ingen duplikater: {regel!r}",
            )

    def test_7c_ingen_bredere_npm_npx_node_variant_introdusert(self):
        forbudte = (
            "Bash(npm *)",
            "Bash(npx *)",
            "Bash(node *)",
            "Bash(npm install *)",
            "Bash(npx playwright *)",
            "Bash(npx playwright install *)",
        )
        for forbudt in forbudte:
            self.assertNotIn(
                forbudt, self.verktoy,
                f"Bredere Node/npm/Playwright-tilgang enn den bundne pakken skal ikke finnes: {forbudt!r}",
            )

    def test_7d_ingen_curl_wget_sudo_introdusert(self):
        for verktoysnavn in self.verktoy:
            for forbudt_prefiks in ("Bash(curl", "Bash(wget", "Bash(sudo"):
                self.assertFalse(
                    verktoysnavn.startswith(forbudt_prefiks),
                    f"{forbudt_prefiks} skal aldri være tillatt: {verktoysnavn!r}",
                )

    def test_7e_kun_en_prefiks_regel_i_pakken_resten_er_eksakte(self):
        # Kun `npx playwright test *` skal ha wildcard -- de åtte andre
        # er eksakte/argument-faste strenger uten `*`.
        wildcard_regler = [r for r in _NODE_PLAYWRIGHT_REGLER if r.endswith("*)")]
        self.assertEqual(wildcard_regler, ["Bash(npx playwright test *)"])

    def test_7f_eksisterende_kontrakt_star_ved_lag_etter_node_playwright_tillegget(self):
        # Gjentar kravene fra issue #201 (punkt 3, 5, 6) eksplisitt, slik at
        # en fremtidig lesning av testfilen ser at V1.5-tillegget ikke
        # svekket noe av det V1.2/V1.3/V1.4 allerede beviste.
        for regel in _FORVENTEDE_PUSH_REGLER:
            self.assertIn(regel, self.verktoy)
        push_regler = [v for v in self.verktoy if v.startswith("Bash(git push")]
        self.assertEqual(sorted(push_regler), sorted(_FORVENTEDE_PUSH_REGLER))
        for verktoysnavn in self.verktoy:
            self.assertFalse(verktoysnavn.startswith("Bash(git merge"))
            self.assertFalse(verktoysnavn.startswith("Bash(gh pr merge"))
        self.assertIn("--permission-mode acceptEdits", self.steg)
        for verktoysnavn in ("Write", "Edit", "MultiEdit"):
            self.assertNotIn(verktoysnavn, self.verktoy)
        self.assertIn(_GENERATOR_REGEL, self.verktoy)
        self.assertEqual(self.verktoy.count(_GENERATOR_REGEL), 1)
        python3_regler = [v for v in self.verktoy if "python3" in v]
        self.assertEqual(
            sorted(python3_regler),
            sorted(["Bash(python3 -m unittest *)", _GENERATOR_REGEL]),
        )


if __name__ == "__main__":
    unittest.main()
