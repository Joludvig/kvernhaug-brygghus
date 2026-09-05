"""
Regresjonstest for .gitattributes sin linjeslutt-policy (issue #55).

Bakgrunn: Windows-checkouts brukte historisk `core.autocrlf=true` uten
noen styrende .gitattributes, slik at committede LF-bytes kunne
materialisere seg som CRLF på disk og knekke sjekksum-styrte fixtures
(tests/fixtures/legacy/**, se test_legacy_fixtures.py) uten at selve
innholdet var endret. `* text=auto eol=lf` tvinger LF i arbeidskatalogen
uansett plattform/lokal autocrlf-innstilling; committede bytes er
upåvirket.

Denne testen sjekker selve den committede policy-teksten (ingen
git-tilstand mutert) og at policyen faktisk dekker alle ekte binærfiler
i repoet i dag -- en fremtidig ny binærfiltype uten et `binary`-direktiv
ville ellers blitt stille linjeslutt-normalisert (og korrumpert) av
`* text=auto eol=lf`.

Ren stdlib-test (pluss ett `git ls-files`-kall for å hente den ekte
filisten) -- ingen GitHub-/Claude Code-avhengighet.
"""
import fnmatch
import os
import subprocess
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GITATTRIBUTES = os.path.join(_REPO_ROOT, ".gitattributes")

# Utvidelser som er ekte binærdata i dette repoet (bekreftet ved
# innholdsinspeksjon, se issue #55-undersøkelsen) -- .gitattributes MÅ
# markere hver av disse som `binary`, ellers vil `* text=auto eol=lf`
# forsøke å linjeslutt-normalisere dem.
_KJENTE_BINAERE_UTVIDELSER = (".png", ".jpg", ".webp", ".ico")


def _les_gitattributes_linjer():
    with open(_GITATTRIBUTES, encoding="utf-8") as f:
        return [
            linje.strip()
            for linje in f.read().splitlines()
            if linje.strip() and not linje.strip().startswith("#")
        ]


def _git_ls_files():
    res = subprocess.run(
        ["git", "-C", _REPO_ROOT, "ls-files"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return [linje for linje in res.stdout.splitlines() if linje.strip()]


class TestGitattributesFinnesOgHarGlobalLfPolicy(unittest.TestCase):
    def setUp(self):
        self.linjer = _les_gitattributes_linjer()

    def test_fil_finnes(self):
        self.assertTrue(os.path.isfile(_GITATTRIBUTES), ".gitattributes mangler i repo-roten")

    def test_global_text_auto_eol_lf_er_satt(self):
        self.assertIn(
            "* text=auto eol=lf", self.linjer,
            "Global `* text=auto eol=lf`-policy mangler -- uten den kan "
            "Windows-checkouts fortsatt materialisere CRLF for tekstfiler",
        )

    def test_kjente_binaere_utvidelser_er_eksplisitt_markert_binary(self):
        for utvidelse in _KJENTE_BINAERE_UTVIDELSER:
            with self.subTest(utvidelse=utvidelse):
                self.assertIn(
                    f"*{utvidelse} binary", self.linjer,
                    f"*{utvidelse} er ikke markert `binary` -- risikerer "
                    "linjeslutt-korrupsjon av ekte binærdata",
                )


class TestAlleEkteBinaerfilerIRepoetErDekket(unittest.TestCase):
    """Fanger en FREMTIDIG ny binærfiltype (f.eks. .woff/.gif) som legges
    til uten et tilsvarende `binary`-direktiv i .gitattributes."""

    def test_hver_sporet_fil_med_kjent_binaer_utvidelse_har_binary_direktiv(self):
        linjer = _les_gitattributes_linjer()
        binary_mønstre = {
            l.rsplit(" binary", 1)[0] for l in linjer if l.endswith(" binary")
        }
        sporede_filer = _git_ls_files()
        udekkede = []
        for sti in sporede_filer:
            _, utvidelse = os.path.splitext(sti)
            if utvidelse.lower() not in _KJENTE_BINAERE_UTVIDELSER:
                continue
            navn = os.path.basename(sti)
            if not any(fnmatch.fnmatch(navn, mønster) for mønster in binary_mønstre):
                udekkede.append(sti)
        self.assertEqual(
            udekkede, [],
            f"Sporede filer med kjent binær utvidelse mangler et "
            f"dekkende `binary`-direktiv i .gitattributes: {udekkede}",
        )


if __name__ == "__main__":
    unittest.main()
