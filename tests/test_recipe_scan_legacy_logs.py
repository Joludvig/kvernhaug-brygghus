"""
Tester for at _skann_oppskriftsfiler() hopper stille over gyldige
legacy-loggarrayer i oppskriftsmappens rot (issue #392), men fortsatt
advarer om faktisk ugyldige/ukjente filer.

Bruker UTELUKKENDE tempfile.TemporaryDirectory() -- aldri ekte recipes/.
"""
import json
import os
import tempfile
import unittest

import modules.recipe_storage as recipe_storage


class TestSkannLegacyLogger(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mappe = self._tmp.name

    def _skriv(self, navn, innhold, raa=False):
        with open(os.path.join(self.mappe, navn), "w", encoding="utf-8") as f:
            f.write(innhold if raa else json.dumps(innhold))

    def _skann(self):
        return recipe_storage._skann_oppskriftsfiler(self.mappe)

    def test_gyldig_oppskrift_returneres(self):
        self._skriv("a.json", {"name": "A"})
        with self.assertNoLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [("a.json", {"name": "A"})])

    def test_legacy_logg_hoppes_over_uten_warning(self):
        self._skriv("a_logg.json", [{"dato": "2025-01-01"}, {"dato": "2025-02-01"}])
        with self.assertNoLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [])

    def test_ugyldig_json_advarer(self):
        self._skriv("x.json", "{ikke json", raa=True)
        with self.assertLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [])

    def test_dict_uten_name_advarer(self):
        self._skriv("x.json", {"foo": 1})
        with self.assertLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [])

    def test_array_med_ikke_objekter_advarer(self):
        self._skriv("x.json", [{"a": 1}, 5])
        with self.assertLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [])

    def test_oppskrift_med_logg_suffiks_er_fortsatt_oppskrift(self):
        self._skriv("brygg_logg.json", {"name": "Brygg Logg"})
        with self.assertNoLogs(recipe_storage._log, level="WARNING"):
            self.assertEqual(self._skann(), [("brygg_logg.json", {"name": "Brygg Logg"})])

    def test_kallere_beholder_semantikk(self):
        self._skriv("a.json", {"name": "A"})
        self._skriv("b.json", {"name": "A"})
        self._skriv("c.json", {"name": "C"})
        self._skriv("c_logg.json", [{"x": 1}])
        with self.assertNoLogs(recipe_storage._log, level="WARNING"):
            alle = recipe_storage.hent_alle_oppskrifter(self.mappe)
            kart = recipe_storage.hent_oppskrift_filnavn_kart(self.mappe)
            dup = recipe_storage.finn_duplikate_oppskrift_navn(self.mappe)
        self.assertEqual(set(alle), {"A", "C"})
        self.assertEqual(kart["C"], "c.json")
        self.assertEqual(dup, [{"navn": "A", "filer": ["a.json", "b.json"]}])
        self.assertTrue(os.path.exists(os.path.join(self.mappe, "c_logg.json")))


if __name__ == "__main__":
    unittest.main()
