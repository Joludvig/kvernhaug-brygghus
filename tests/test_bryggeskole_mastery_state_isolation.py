"""
Testhygiene: Bryggeskole-testene skal ALDRI lese eller skrive den ekte,
lokale data/bryggeskole_mastery_state.json.

Integrert offline-QA fant at en kjøring av tests.test_ui_bryggeskole_panel
endret mtime (og innhold, Q-MASH-001) på den ekte filen i worktreet: fire
testklasser arvet unittest.TestCase direkte i stedet for
_MedIsolertTilstand, og bryggeskole.mastery_store.default_state_path()
falt da tilbake til produksjonsstien «data/». Filen er gitignored, så
git status alene avslører det ikke -- denne modulen sjekker derfor hash
og mtime direkte.

Produksjonskoden er uendret: isolasjonen bruker den eksisterende
KVERNHAUG_BRYGGESKOLE_STATE_DIR-sømmen.

Kjøres med:
    python3 -m unittest tests.test_bryggeskole_mastery_state_isolation -v
"""
import hashlib
import inspect
import logging
import os
import subprocess
import sys
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import tests.test_ui_bryggeskole_panel as panel_tester
from bryggeskole.mastery_store import (
    _STATE_DIR_ENV,
    _STATE_FILENAME,
    default_state_path,
    neutral_state_document,
    read_mastery_state,
)
from bryggeskole.pilot_mashing import read_pilot_file as les_mesking_pilot

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EKTE_FIL = os.path.join(_REPO_ROOT, "data", _STATE_FILENAME)

# Klassene som tidligere lakk til den ekte filen (to skrev, to leste).
_TIDLIGERE_LEKKENDE = (
    "TestNavigasjonsknapperErKompakteIssue398",
    "TestQuizTypografiIssue401",
    "TestSvaralternativKontrastEtterSvarIssue401",
    "TestSkoleoversiktGridResponsivIssue394",
)

# Subprosess-tester som isolerer via et eget env-dict med tempdir.
_SUBPROSESS_ISOLERT = ("TestDemoModeIngenSkriving", "TestReachableSomToppniva")


def _fingeravtrykk(sti):
    if not os.path.exists(sti):
        return None
    with open(sti, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return digest, os.stat(sti).st_mtime_ns


class TestProduksjonsstiErUendret(unittest.TestCase):
    def test_standardsti_uten_env_er_data_mappen(self):
        gammel = os.environ.pop(_STATE_DIR_ENV, None)
        try:
            self.assertEqual(default_state_path(), os.path.join("data", "bryggeskole_mastery_state.json"))
        finally:
            if gammel is not None:
                os.environ[_STATE_DIR_ENV] = gammel

    def test_env_navnet_er_uendret(self):
        self.assertEqual(_STATE_DIR_ENV, "KVERNHAUG_BRYGGESKOLE_STATE_DIR")


class TestAlleTilstandsberorendeKlasserErIsolert(unittest.TestCase):
    def test_apptest_og_mastery_klasser_arver_isolert_base(self):
        uisolerte = []
        for navn, klasse in vars(panel_tester).items():
            if not (inspect.isclass(klasse) and issubclass(klasse, unittest.TestCase)):
                continue
            kilde = inspect.getsource(klasse)
            if not any(m in kilde for m in ("AppTest.from_file", "read_mastery_state", "write_mastery_state", "_ny_apptest")):
                continue
            if issubclass(klasse, panel_tester._MedIsolertTilstand):
                continue
            if navn in _SUBPROSESS_ISOLERT and "env[_STATE_DIR_ENV] = tmp" in kilde:
                continue
            uisolerte.append(navn)
        self.assertEqual(uisolerte, [], "Disse klassene kan nå den ekte mastery-filen")

    def test_tidligere_lekkende_klasser_er_na_isolert(self):
        for navn in _TIDLIGERE_LEKKENDE:
            self.assertTrue(issubclass(getattr(panel_tester, navn), panel_tester._MedIsolertTilstand), navn)


class TestTempTilstandSkrivesLesesOgLekkerIkke(panel_tester._MedIsolertTilstand):
    def _svar_forste_mesking_sporsmal(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        fasit = panel_tester._korrekt_svar_ider(les_mesking_pilot())
        self._besvar_sporsmal(at, 0, 1, fasit[0])

    def test_tilstand_skrives_og_leses_i_tempmappen(self):
        sti = default_state_path()
        self.assertEqual(os.path.dirname(os.path.abspath(sti)), os.path.abspath(self._tmpdir.name))
        self.assertNotEqual(os.path.abspath(sti), os.path.abspath(_EKTE_FIL))
        self.assertFalse(os.path.exists(sti))

        self._svar_forste_mesking_sporsmal()

        self.assertTrue(os.path.exists(sti), "mastery skal faktisk skrives i tempmappen")
        tilstand = read_mastery_state()
        self.assertIn("Q-MASH-001", tilstand["answered_questions"])
        self.assertTrue(tilstand["concepts"])

    def test_ingen_lekkasje_mellom_tester(self):
        self._svar_forste_mesking_sporsmal()
        forste_tmp = self._tmpdir.name
        self.assertNotEqual(read_mastery_state(), neutral_state_document())

        # Simulerer neste test: ny setUp gir en fersk, tom tempmappe.
        self.tearDown()
        self.setUp()
        self.assertNotEqual(self._tmpdir.name, forste_tmp)
        self.assertEqual(os.listdir(self._tmpdir.name), [])
        self.assertEqual(read_mastery_state(), neutral_state_document())


class TestEkteMasteryFilBerorErIkke(unittest.TestCase):
    def test_tidligere_lekkende_klasser_endrer_ikke_ekte_fil(self):
        # Kjøres i en egen prosess UTEN env-variabelen, slik at det er
        # klassenes egen isolasjon som testes -- ikke et ytre miljø.
        env = dict(os.environ)
        env.pop(_STATE_DIR_ENV, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        mal = [f"tests.test_ui_bryggeskole_panel.{navn}" for navn in _TIDLIGERE_LEKKENDE]

        for_ = _fingeravtrykk(_EKTE_FIL)
        resultat = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", *mal],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        etter = _fingeravtrykk(_EKTE_FIL)

        self.assertEqual(resultat.returncode, 0, resultat.stderr[-3000:])
        self.assertEqual(etter, for_, "ekte data/bryggeskole_mastery_state.json ble endret (hash/mtime)")


if __name__ == "__main__":
    unittest.main()
