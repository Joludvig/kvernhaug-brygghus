"""
Regresjonstest for Steg F9C: bekrefter at scripts/scrape_malt_only.py
og scripts/scrape_malt.py faktisk KAN importere modules.store_scraper
når de kjøres direkte som fil (py -3 scripts/<navn>.py) fra repo-roten.

Bakgrunn (Steg F9B): en ekte, levende kjøring av
`py -3 scripts/scrape_malt_only.py` feilet umiddelbart med
`ModuleNotFoundError: No module named 'modules'`, FØR noen
nettverkstilgang. Rotårsaken: direkte scriptkjøring setter
`sys.path[0]` til scriptets EGEN katalog (scripts/), ikke repo-roten
og ikke gjeldende arbeidsmappe — så `modules/`, som ligger i
repo-roten, ble aldri funnet.

En tidligere runpy-basert test (Steg F9A) fanget IKKE dette, fordi den
kjørte i en testprosess der (a) `modules.store_scraper` allerede lå i
`sys.modules` fra en tidligere import i samme prosess, og (b) prosessens
egen `sys.path[0]` uansett var repo-roten (via `-m unittest`), ikke
scripts/. Testene her unngår begge disse maskeringene ved å starte en
HELT FERSK Python-subprosess og eksplisitt fjerne repo-roten fra
`sys.path` før scriptet kjøres — for så å bekrefte at scriptets EGEN
bootstrap (REPO_ROOT-innsetting i sys.path) er det som faktisk gjør
importen mulig.

Testene bruker `runpy.run_path(..., run_name="ikke_main")` (IKKE
"__main__"), slik at `if __name__ == "__main__":`-vakten aldri
utløses — ingen HTTP-kall, ingen filskriving.
"""
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _kjor_isolert_importkontroll(script_navn, forventet_funksjon):
    """
    Starter en helt fersk, isolert Python-subprosess der `sys.path` er
    begrenset til stdlib + scripts/-katalogen (akkurat slik det faktisk
    ser ut ved `py -3 scripts/<script_navn>`), og kjører scriptfilen med
    runpy under et navn som IKKE er "__main__". Returnerer
    (returncode, stdout, stderr).
    """
    script_path = SCRIPTS_DIR / script_navn
    probe = f"""
import sys, runpy

# Fjern tom cwd-oppføring og repo-roten fra sys.path FØR runpy, slik at
# dette er en genuint fersk simulering av direkte scriptkjøring — ikke
# en testprosess som allerede har repo-roten (eller modules.store_scraper)
# tilgjengelig fra før.
sys.path = [p for p in sys.path if p not in ("", {str(REPO_ROOT)!r})]
if {str(SCRIPTS_DIR)!r} not in sys.path:
    sys.path.insert(0, {str(SCRIPTS_DIR)!r})

assert "modules" not in sys.modules, "modules var uventet allerede importert"

ns = runpy.run_path({str(script_path)!r}, run_name="ikke_main")

assert {forventet_funksjon!r} in ns, "forventet funksjon mangler i navnerommet"
assert "main" in ns, "main() mangler i navnerommet"
print("IMPORT_OK")
"""
    return subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


class TestScrapeMaltOnlyDirekteImport(unittest.TestCase):
    def test_direkte_scriptkjoring_kan_importere_modules(self):
        resultat = _kjor_isolert_importkontroll("scrape_malt_only.py", "kjor_malt_skanning")
        self.assertEqual(resultat.returncode, 0, msg=resultat.stderr)
        self.assertIn("IMPORT_OK", resultat.stdout)


class TestScrapeMaltLegacyDirekteImport(unittest.TestCase):
    def test_direkte_scriptkjoring_kan_importere_modules(self):
        resultat = _kjor_isolert_importkontroll("scrape_malt.py", "kjor_full_skanning")
        self.assertEqual(resultat.returncode, 0, msg=resultat.stderr)
        self.assertIn("IMPORT_OK", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
