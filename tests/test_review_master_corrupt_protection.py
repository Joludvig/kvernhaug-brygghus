"""
Tester for at ui/review_panel.py ALDRI overskriver en EKSISTERENDE
masterfil den ikke klarte å lese og validere.

Bakgrunn: _les_json() fanget tidligere ALLE feil (manglende fil, tom
fil, korrupt JSON, feil JSON-type, lesefeil) og returnerte stille
default-verdien {}. Siden review skriver DIREKTE til de aktive
masterdatabasene appen laster ved oppstart (se
ui/review_panel.py::MASTER_PATHS), betydde det at en korrupt eller
midlertidig uleselig masterfil kunne bli "gjenopprettet" som en TOM
master og deretter overskrevet med kun den ene nye/endrede
ingrediensen -- resten av databasen ville gått tapt (om enn
gjenopprettbar fra backup, se modules/master_data_io.py).

_les_master() erstatter _les_json() for selve masterfilene og skiller
tydelig mellom "filen finnes ikke ennå" (helt normalt, {} uten feil) og
en EKSISTERENDE fil som ikke kan leses/valideres (MasterLesefeil, ALDRI
stille erstattet med {}).

Bruker samme mønster som tests/test_review_master_id_collision.py: en
HELT ISOLERT tempfile.TemporaryDirectory() som fungerer som en fersk
prosjektrot (data/ + raw_data/), aldri de ekte masterfilene i data/.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import ui.review_panel as review_panel
from ui.review_panel import MasterLesefeil


def _last_json(sti):
    with open(sti, encoding="utf-8") as f:
        return json.load(f)


class _IsolertProsjektrotTestCase(unittest.TestCase):
    """Samme isolasjonsteknikk som tests/test_review_master_id_collision.py
    -- review_panel.py sine MASTER_PATHS/UNMATCHED_PATHS er relative
    stier ("data/...", "raw_data/...")."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)
        os.makedirs("data", exist_ok=True)
        os.makedirs("raw_data", exist_ok=True)

    def tearDown(self):
        os.chdir(self._gammel_cwd)
        self._tmpdir.cleanup()

    def _skriv_master_raw(self, kat, raw_tekst):
        with open(review_panel.MASTER_PATHS[kat], "w", encoding="utf-8") as f:
            f.write(raw_tekst)

    def _skriv_unmatched(self, kat, innhold):
        with open(review_panel.UNMATCHED_PATHS[kat], "w", encoding="utf-8") as f:
            json.dump(innhold, f, ensure_ascii=False, indent=2)

    def _les_master_bytes(self, kat):
        with open(review_panel.MASTER_PATHS[kat], "rb") as f:
            return f.read()

    def _unmatched_lengde(self, kat):
        return len(_last_json(review_panel.UNMATCHED_PATHS[kat]))


class TestManglendeMasterfilErIkkeEnFeil(_IsolertProsjektrotTestCase):
    """Motsatt kontrollcase: en masterfil som IKKE finnes ennå er helt
    normalt (masteren er bare ikke opprettet) og skal IKKE reise
    MasterLesefeil -- oppretting skal fungere som før."""

    def test_opprett_naar_masterfil_ikke_finnes_paa_disk(self):
        self.assertFalse(os.path.exists(review_panel.MASTER_PATHS["humle"]))
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])

        review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        master = _last_json(review_panel.MASTER_PATHS["humle"])
        self.assertEqual(master, {"splendour": {"display_name": "Splendour"}})
        self.assertEqual(self._unmatched_lengde("humle"), 0)


class TestTomMasterfilBlokkeres(_IsolertProsjektrotTestCase):
    def test_0_byte_masterfil_blokkerer_oppretting(self):
        self._skriv_master_raw("humle", "")
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])
        original = self._les_master_bytes("humle")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original)
        self.assertEqual(original, b"")
        self.assertEqual(self._unmatched_lengde("humle"), 1)

    def test_kun_whitespace_masterfil_blokkerer_oppretting(self):
        # En fil med kun mellomrom/linjeskift er heller ikke gyldig JSON --
        # samme kategori som en 0-byte-fil, ikke en "gyldig tom master".
        self._skriv_master_raw("malt", "   \n\n  ")
        self._skriv_unmatched("malt", [{"navn": "Nytt Malt", "butikk": "vestbrygg", "pris": 40.0}])
        original = self._les_master_bytes("malt")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("malt", "nytt_malt", {"display_name": "Nytt Malt"}, 0)

        self.assertEqual(self._les_master_bytes("malt"), original)
        self.assertEqual(self._unmatched_lengde("malt"), 1)


class TestKorruptJsonBlokkeres(_IsolertProsjektrotTestCase):
    def test_korrupt_json_blokkerer_oppretting(self):
        self._skriv_master_raw("humle", "{ikke gyldig json")
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])
        original = self._les_master_bytes("humle")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original)
        self.assertEqual(self._unmatched_lengde("humle"), 1)

    def test_korrupt_json_blokkerer_alias_tillegging(self):
        self._skriv_master_raw("gjaer", "{ dette er ikke json }}}")
        self._skriv_unmatched("gjaer", [{"navn": "Ny Gjær", "butikk": "vestbrygg", "pris": 59.0}])
        original = self._les_master_bytes("gjaer")

        with self.assertRaises(MasterLesefeil):
            review_panel._legg_til_alias_og_fjern(
                "gjaer", "safale_us05", {"navn": "Ny Gjær", "butikk": "vestbrygg", "pris": 59.0}, 0,
            )

        self.assertEqual(self._les_master_bytes("gjaer"), original)
        self.assertEqual(self._unmatched_lengde("gjaer"), 1)


class TestFeilJsonTypeBlokkeres(_IsolertProsjektrotTestCase):
    def test_json_liste_i_stedet_for_objekt_blokkerer_oppretting(self):
        self._skriv_master_raw("humle", json.dumps(["cascade_us", "citra_us"]))
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])
        original = self._les_master_bytes("humle")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original)
        self.assertEqual(self._unmatched_lengde("humle"), 1)

    def test_json_streng_i_stedet_for_objekt_blokkerer_oppretting(self):
        self._skriv_master_raw("malt", json.dumps("dette er bare en tekststreng"))
        self._skriv_unmatched("malt", [{"navn": "Nytt Malt", "butikk": "vestbrygg", "pris": 40.0}])
        original = self._les_master_bytes("malt")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("malt", "nytt_malt", {"display_name": "Nytt Malt"}, 0)

        self.assertEqual(self._les_master_bytes("malt"), original)
        self.assertEqual(self._unmatched_lengde("malt"), 1)

    def test_json_tall_i_stedet_for_objekt_blokkerer_alias_tillegging(self):
        self._skriv_master_raw("gjaer", "42")
        self._skriv_unmatched("gjaer", [{"navn": "Ny Gjær", "butikk": "vestbrygg", "pris": 59.0}])
        original = self._les_master_bytes("gjaer")

        with self.assertRaises(MasterLesefeil):
            review_panel._legg_til_alias_og_fjern(
                "gjaer", "safale_us05", {"navn": "Ny Gjær", "butikk": "vestbrygg", "pris": 59.0}, 0,
            )

        self.assertEqual(self._les_master_bytes("gjaer"), original)
        self.assertEqual(self._unmatched_lengde("gjaer"), 1)

    def test_json_null_i_stedet_for_objekt_blokkerer_oppretting(self):
        self._skriv_master_raw("humle", "null")
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])
        original = self._les_master_bytes("humle")

        with self.assertRaises(MasterLesefeil):
            review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original)
        self.assertEqual(self._unmatched_lengde("humle"), 1)


class TestAnnenLesefeilBlokkeres(_IsolertProsjektrotTestCase):
    def test_os_feil_ved_lesing_blokkerer_oppretting_uten_aa_skrive(self):
        self._skriv_master_raw("humle", json.dumps({"cascade_us": {"display_name": "Cascade"}}))
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])
        original = self._les_master_bytes("humle")

        ekte_open = open
        maal_sti = os.path.abspath(review_panel.MASTER_PATHS["humle"])

        def _feilende_open(sti, mode="r", *args, **kwargs):
            if os.path.abspath(sti) == maal_sti and mode == "r":
                raise OSError("simulert lesefeil (f.eks. rettighetsproblem)")
            return ekte_open(sti, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=_feilende_open):
            with self.assertRaises(MasterLesefeil):
                review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original)
        self.assertEqual(self._unmatched_lengde("humle"), 1)


class TestGyldigMasterFungererFortsattSomFoer(_IsolertProsjektrotTestCase):
    """Kontrollcase: en gyldig, lesbar master (inkludert en bevisst TOM
    {}) skal fortsatt fungere helt normalt -- denne herdingen skal ikke
    ha innsnevret det legitime tilfellet."""

    def test_gyldig_tom_master_tillater_oppretting(self):
        self._skriv_master_raw("humle", "{}")
        self._skriv_unmatched("humle", [{"navn": "Splendour", "butikk": "vestbrygg", "pris": 75.0}])

        review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        master = _last_json(review_panel.MASTER_PATHS["humle"])
        self.assertIn("splendour", master)
        self.assertEqual(self._unmatched_lengde("humle"), 0)


if __name__ == "__main__":
    unittest.main()
