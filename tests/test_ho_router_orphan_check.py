"""
Regresjonstester for .github/scripts/ho_router_orphan_check.py (issue #252).

Dekker acceptance-punktene fra issue #252 som lar seg uttrykke som ren,
GitHub-uavhengig logikk:
  - en nyere KBH_COS_LIVE_CHECKPOINT_V1-kommentar på mål-issuet UTEN en
    matchende, nyere KBH_COS_CHECKPOINT_PTR_V1-linje på #152 oppdages
    som foreldreløs (den faktiske 2026-09-13-hendelsen dette issuet
    beskriver);
  - et sjekkpunkt som MATCHER nyeste pointer regnes ikke som
    foreldreløst;
  - manglende pointer, manglende sjekkpunkt og et issue-mismatch mellom
    pointer og oppgitt mål-issue er alle fail-closed (foreldrelos=True),
    aldri en stille "alt er fint";
  - kun linje-ankrede, eksakte markører telles -- en kommentar som bare
    NEVNER/siterer markørformatet uten selve linjen teller ikke.

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import io
import json
import os
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "ho_router_orphan_check.py")


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_HROC = _last_modul(_SCRIPT, "ho_router_orphan_check")


def _pointer(issue, comment):
    return f"KBH_COS_CHECKPOINT_PTR_V1 issue={issue} comment={comment}"


def _sjekkpunkt(id_, ekstra=""):
    return {"id": id_, "body": f"KBH_COS_LIVE_CHECKPOINT_V1\n\n{ekstra}"}


class TestFinnNyestePointer(unittest.TestCase):
    def test_ingen_kommentarer_gir_none(self):
        self.assertIsNone(_HROC.finn_nyeste_pointer([]))
        self.assertIsNone(_HROC.finn_nyeste_pointer(None))

    def test_siste_gyldige_linje_vinner(self):
        kommentarer = [
            "noe annet\n" + _pointer(196, 111),
            "helt urelatert kommentar",
            _pointer(196, 222),
        ]
        self.assertEqual(_HROC.finn_nyeste_pointer(kommentarer), (196, 222))

    def test_feilformet_linje_telles_ikke(self):
        kommentarer = [
            "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=abc",  # ikke tall
            "> KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111 (sitert)",
            "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111 ekstra tekst",
        ]
        self.assertIsNone(_HROC.finn_nyeste_pointer(kommentarer))


class TestErSjekkpunktKommentar(unittest.TestCase):
    def test_eksakt_markor_gjenkjennes(self):
        self.assertTrue(_HROC.er_sjekkpunkt_kommentar("KBH_COS_LIVE_CHECKPOINT_V1\n\nresten..."))

    def test_omtale_uten_linje_teller_ikke(self):
        self.assertFalse(_HROC.er_sjekkpunkt_kommentar("se KBH_COS_LIVE_CHECKPOINT_V1 lenger opp"))

    def test_tom_body_teller_ikke(self):
        self.assertFalse(_HROC.er_sjekkpunkt_kommentar(None))
        self.assertFalse(_HROC.er_sjekkpunkt_kommentar(""))


class TestFinnForeldrelosSjekkpunkt(unittest.TestCase):
    def test_nyeste_sjekkpunkt_matcher_pointer_er_ikke_foreldrelos(self):
        foreldrelos, begrunnelse, pointer, sjekkpunkt_id = _HROC.finn_foreldrelos_sjekkpunkt(
            pointer_kommentarer=[_pointer(196, 5654816412)],
            mal_issue_nummer=196,
            mal_issue_kommentarer=[
                _sjekkpunkt(5648254902),
                _sjekkpunkt(5654816412),
            ],
        )
        self.assertFalse(foreldrelos)
        self.assertEqual(pointer, (196, 5654816412))
        self.assertEqual(sjekkpunkt_id, 5654816412)

    def test_nyere_sjekkpunkt_uten_matchende_pointer_er_foreldrelos(self):
        """Den faktiske issue #252-hendelsen: pointeren henger fortsatt på
        det gamle sjekkpunktet selv om et nyere allerede finnes på samme
        issue."""
        foreldrelos, begrunnelse, pointer, sjekkpunkt_id = _HROC.finn_foreldrelos_sjekkpunkt(
            pointer_kommentarer=[_pointer(196, 5648254902)],
            mal_issue_nummer=196,
            mal_issue_kommentarer=[
                _sjekkpunkt(5648254902),
                _sjekkpunkt(5654816412),
            ],
        )
        self.assertTrue(foreldrelos)
        self.assertIn("Foreldreløst sjekkpunkt", begrunnelse)
        self.assertEqual(pointer, (196, 5648254902))
        self.assertEqual(sjekkpunkt_id, 5654816412)

    def test_manglende_pointer_er_foreldrelos(self):
        foreldrelos, begrunnelse, pointer, sjekkpunkt_id = _HROC.finn_foreldrelos_sjekkpunkt(
            pointer_kommentarer=[],
            mal_issue_nummer=196,
            mal_issue_kommentarer=[_sjekkpunkt(111)],
        )
        self.assertTrue(foreldrelos)
        self.assertIsNone(pointer)

    def test_manglende_sjekkpunkt_er_foreldrelos(self):
        foreldrelos, begrunnelse, pointer, sjekkpunkt_id = _HROC.finn_foreldrelos_sjekkpunkt(
            pointer_kommentarer=[_pointer(196, 111)],
            mal_issue_nummer=196,
            mal_issue_kommentarer=[{"id": 111, "body": "vanlig kommentar, ingen markør"}],
        )
        self.assertTrue(foreldrelos)
        self.assertIsNone(sjekkpunkt_id)

    def test_pointer_mot_annet_issue_enn_oppgitt_mal_er_foreldrelos(self):
        foreldrelos, begrunnelse, pointer, sjekkpunkt_id = _HROC.finn_foreldrelos_sjekkpunkt(
            pointer_kommentarer=[_pointer(201, 111)],
            mal_issue_nummer=196,
            mal_issue_kommentarer=[_sjekkpunkt(111)],
        )
        self.assertTrue(foreldrelos)
        self.assertIn("mål-issuet", begrunnelse)
        self.assertEqual(pointer, (201, 111))


class TestCliMain(unittest.TestCase):
    def _kjor(self, payload):
        stdin = io.StringIO(json.dumps(payload))
        old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin = stdin
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            kode = _HROC.main(["ho_router_orphan_check.py"])
            return kode, sys.stdout.getvalue(), sys.stderr.getvalue()
        finally:
            sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr

    def test_exit_0_nar_ikke_foreldrelos(self):
        kode, ut, _ = self._kjor(
            {
                "pointer_comments": [_pointer(196, 111)],
                "target_issue": 196,
                "target_issue_comments": [_sjekkpunkt(111)],
            }
        )
        self.assertEqual(kode, 0)
        self.assertIn("orphan=false", ut)

    def test_exit_1_nar_foreldrelos(self):
        kode, ut, _ = self._kjor(
            {
                "pointer_comments": [_pointer(196, 111)],
                "target_issue": 196,
                "target_issue_comments": [_sjekkpunkt(111), _sjekkpunkt(222)],
            }
        )
        self.assertEqual(kode, 1)
        self.assertIn("orphan=true", ut)
        self.assertIn("newest_checkpoint_comment=222", ut)

    def test_exit_2_ved_ugyldig_json(self):
        old_stdin, old_stderr = sys.stdin, sys.stderr
        sys.stdin = io.StringIO("{ikke gyldig json")
        sys.stderr = io.StringIO()
        try:
            kode = _HROC.main(["ho_router_orphan_check.py"])
        finally:
            sys.stdin, sys.stderr = old_stdin, old_stderr
        self.assertEqual(kode, 2)


if __name__ == "__main__":
    unittest.main()
