"""
Tester for modules/master_data_io.py -- den delte atomisk skriving +
backup-hjelperen som modules/store_matcher.py (skanning/matching) og
ui/review_panel.py (manuell review-godkjenning) nå begge bruker for
ALL skriving til masterdatabasene (master_malt.json, master_humle_v2.json,
master_gjaer_v2.json).

Bruker utelukkende tempfile.TemporaryDirectory() -- rører aldri de ekte,
committede masterdatafilene i data/.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

from modules.master_data_io import (
    skriv_master_json_atomisk,
    backup_master_fil,
    MASTER_BACKUP_MAKS_ANTALL,
)


class TestSkrivMasterJsonAtomisk(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._filsti = os.path.join(self._tmpdir.name, "master_test.json")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_forste_skriving_lager_ingen_backup(self):
        skriv_master_json_atomisk(self._filsti, {"a": 1})
        filer = os.listdir(self._tmpdir.name)
        self.assertEqual(filer, ["master_test.json"])

    def test_ingen_tmp_fil_ligger_igjen_etter_skriving(self):
        skriv_master_json_atomisk(self._filsti, {"a": 1})
        skriv_master_json_atomisk(self._filsti, {"a": 2})
        filer = os.listdir(self._tmpdir.name)
        self.assertFalse(any(".tmp_" in f for f in filer))

    def test_overskriving_tar_backup_av_forrige_versjon(self):
        skriv_master_json_atomisk(self._filsti, {"a": 1})
        skriv_master_json_atomisk(self._filsti, {"a": 2})

        backupfiler = [f for f in os.listdir(self._tmpdir.name) if "backup_" in f]
        self.assertEqual(len(backupfiler), 1)
        with open(os.path.join(self._tmpdir.name, backupfiler[0]), encoding="utf-8") as f:
            backup_innhold = json.load(f)
        self.assertEqual(backup_innhold, {"a": 1}, "Backupen skal inneholde DEN GAMLE versjonen")

        with open(self._filsti, encoding="utf-8") as f:
            gjeldende = json.load(f)
        self.assertEqual(gjeldende, {"a": 2}, "Selve filen skal ha DEN NYE versjonen")

    def test_backup_av_ikke_eksisterende_fil_er_no_op(self):
        self.assertIsNone(backup_master_fil(self._filsti))

    def test_backup_ryddes_til_maks_antall(self):
        for i in range(MASTER_BACKUP_MAKS_ANTALL + 5):
            skriv_master_json_atomisk(self._filsti, {"i": i})
        backupfiler = [f for f in os.listdir(self._tmpdir.name) if "backup_" in f]
        self.assertEqual(len(backupfiler), MASTER_BACKUP_MAKS_ANTALL)


if __name__ == "__main__":
    unittest.main()
