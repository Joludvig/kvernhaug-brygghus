"""
Tester for målprofil-biblioteket (modules/water_chemistry.py) — lasting,
anbefaling, redigering, lagring, og at standardprofilene aldri muteres.

Bakgrunn: UI-et hadde til nå kun ÉN målprofil («Maltpreget tysk lager –
Kvernhaug»). Denne testen låser fast at biblioteket er utvidet med fire nye,
generelle profiler PLUSS «Egendefinert», UTEN å endre den eksisterende
profilen (og dermed heller ikke Wiesn-Märzen-oppskriftens lagrede
vannbehandling, som er en frossen SNAPSHOT tatt på lagringstidspunktet —
se modules/recipe.py).

Tester som skriver til disk bruker KVERNHAUG_WATER_TARGETS_FILE for
isolasjon — samme mønster og begrunnelse som i test_water_chemistry.py sin
Test20EgendefinerteProfilerMutererIkkeStandard.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

from modules.water_chemistry import (
    IONER, last_vannkilder, last_vannmaal, lagre_vannmaal, anbefal_vannmaal,
)

_FORVENTEDE_PROFILER = {
    "kvernhaug_maltpreget_tysk_lager", "lys_lager_pils", "balansert_ale",
    "mork_maltol_porter_stout", "humledrevet_ol", "egendefinert",
}

_ORIGINAL_WIESN_PROFIL = {
    "target_id": "kvernhaug_maltpreget_tysk_lager",
    "name": "Maltpreget tysk lager – Kvernhaug",
    "anbefalte_stiler": ["Historisk Wiesn-Märzen", "Märzen", "Festbier", "Vienna Lager", "Dunkel", "Bock"],
    "ca_min": 50, "ca_max": 65,
    "mg_min": 0, "mg_max": 8,
    "na_min": 0, "na_max": 20,
    "cl_min": 50, "cl_max": 70,
    "so4_min": 30, "so4_max": 45,
    "hco3_min": 25, "hco3_max": 60,
    "mash_ph_min": 5.30,
    "mash_ph_max": 5.40,
}


class Test1LastingAvMaalprofilBiblioteket(unittest.TestCase):
    """Ren lesing av DEN EKTE data/water_targets.json — ingen skriving."""

    def test_alle_seks_profiler_finnes(self):
        maal = last_vannmaal()
        self.assertEqual(set(maal.keys()), _FORVENTEDE_PROFILER)

    def test_hver_profil_har_alle_paakrevde_felter(self):
        maal = last_vannmaal()
        for target_id, profil in maal.items():
            for ion in IONER:
                self.assertIn(f"{ion}_min", profil, msg=f"{target_id} mangler {ion}_min")
                self.assertIn(f"{ion}_max", profil, msg=f"{target_id} mangler {ion}_max")
                self.assertIsInstance(profil[f"{ion}_min"], (int, float))
                self.assertIsInstance(profil[f"{ion}_max"], (int, float))
                self.assertLessEqual(profil[f"{ion}_min"], profil[f"{ion}_max"])
            self.assertIn("mash_ph_min", profil)
            self.assertIn("mash_ph_max", profil)
            self.assertLess(profil["mash_ph_min"], profil["mash_ph_max"])
            self.assertIn("name", profil)
            self.assertIn("anbefalte_stiler", profil)

    def test_eksisterende_wiesn_profil_er_helt_uendret(self):
        maal = last_vannmaal()
        profil = maal["kvernhaug_maltpreget_tysk_lager"]
        for key, forventet in _ORIGINAL_WIESN_PROFIL.items():
            self.assertEqual(profil[key], forventet, msg=f"Feltet {key} har endret seg!")

    def test_kildevann_og_maalprofil_er_tydelig_atskilt(self):
        # Jordalsvatnet skal ALDRI dukke opp som en målprofil, og ingen
        # målprofil-id skal dukke opp som en kildevannsprofil.
        kilder = last_vannkilder()
        maal = last_vannmaal()
        self.assertNotIn("jordalsvatnet_2025", maal)
        self.assertTrue(set(kilder.keys()).isdisjoint(set(maal.keys())))

    def test_egendefinert_anbefales_aldri_for_noen_stil(self):
        maal = last_vannmaal()
        self.assertEqual(maal["egendefinert"]["anbefalte_stiler"], [])

    def test_balansert_ale_har_ingen_egne_anbefalte_stiler(self):
        # Den er BEVISST fallback-profilen, ikke stilspesifikk (samme
        # mønster som "enkel_infusjon" i modules/process_profiles.py).
        maal = last_vannmaal()
        self.assertEqual(maal["balansert_ale"]["anbefalte_stiler"], [])


class Test2Anbefaling(unittest.TestCase):
    def setUp(self):
        self.maal = last_vannmaal()

    def test_lys_stil_anbefaler_lys_lager_pils(self):
        target_id, begrunnelse = anbefal_vannmaal("Tysk Pilsner", self.maal)
        self.assertEqual(target_id, "lys_lager_pils")
        self.assertTrue(begrunnelse)

    def test_mork_stil_anbefaler_mork_maltol(self):
        target_id, _ = anbefal_vannmaal("Stout", self.maal)
        self.assertEqual(target_id, "mork_maltol_porter_stout")

    def test_humlet_stil_anbefaler_humledrevet(self):
        target_id, _ = anbefal_vannmaal("IPA", self.maal)
        self.assertEqual(target_id, "humledrevet_ol")

    def test_wiesn_marzen_gir_fortsatt_kvernhaug_profilen(self):
        # Regresjon: den opprinnelige profilen skal fortsatt være den som
        # anbefales for stilen den alltid har vært knyttet til.
        target_id, _ = anbefal_vannmaal("Historisk Wiesn-Märzen", self.maal)
        self.assertEqual(target_id, "kvernhaug_maltpreget_tysk_lager")

    def test_ukjent_eller_tom_stil_faller_tilbake_til_balansert_ale(self):
        target_id, begrunnelse = anbefal_vannmaal("En helt oppdiktet stil", self.maal)
        self.assertEqual(target_id, "balansert_ale")
        self.assertTrue(begrunnelse)

        target_id2, _ = anbefal_vannmaal("", self.maal)
        self.assertEqual(target_id2, "balansert_ale")

        target_id3, _ = anbefal_vannmaal(None, self.maal)
        self.assertEqual(target_id3, "balansert_ale")

    def test_anbefaling_er_ren_funksjon_uten_sideeffekter(self):
        foer = {k: dict(v) for k, v in self.maal.items()}
        anbefal_vannmaal("IPA", self.maal)
        anbefal_vannmaal("Stout", self.maal)
        anbefal_vannmaal(None, self.maal)
        for k in foer:
            self.assertEqual(self.maal[k], foer[k], msg=f"anbefal_vannmaal muterte {k}!")

    def test_ingen_maalprofiler_gir_none(self):
        target_id, begrunnelse = anbefal_vannmaal("IPA", {})
        self.assertIsNone(target_id)
        self.assertTrue(begrunnelse)

    def test_default_leser_ekte_fil_naar_maalprofiler_utelates(self):
        # Uten eksplisitt maalprofiler-argument leses DEN EKTE
        # data/water_targets.json (ren lesing, ingen skriving).
        target_id, _ = anbefal_vannmaal("IPA")
        self.assertEqual(target_id, "humledrevet_ol")


class Test3RedigeringOgLagring(unittest.TestCase):
    """All skriving skjer i en ISOLERT fil — den EKTE
    data/water_targets.json skal forbli fysisk uendret gjennom hele
    testen (se tearDown)."""

    def setUp(self):
        self._gammel_env = os.environ.get("KVERNHAUG_WATER_TARGETS_FILE")
        self._ekte_snapshot = dict(last_vannmaal())

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_WATER_TARGETS_FILE", None)
        else:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = self._gammel_env
        self.assertEqual(
            dict(last_vannmaal()), self._ekte_snapshot,
            "Den EKTE data/water_targets.json ble endret under en isolert test!",
        )

    def test_redigering_av_lys_lager_pils_lagres_og_overlever_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = os.path.join(tmp, "water_targets.json")
            maal = last_vannmaal()  # tom -> faller ikke tilbake til ekte fil
            self.assertEqual(maal, {})

            # Simuler at brukeren har startet fra biblioteket (som om
            # UI-et hadde lastet det fra den ekte filen først) og redigerer.
            import json
            with open(os.path.join(_repo_root(), "data", "water_targets.json"), encoding="utf-8") as f:
                maal = json.load(f)

            maal["lys_lager_pils"]["ca_max"] = 55.0
            maal["lys_lager_pils"]["hco3_max"] = 30.0
            lagre_vannmaal(maal)

            lest_tilbake = last_vannmaal()
            self.assertEqual(lest_tilbake["lys_lager_pils"]["ca_max"], 55.0)
            self.assertEqual(lest_tilbake["lys_lager_pils"]["hco3_max"], 30.0)
            # Andre profiler i SAMME fil skal forbli uendret av redigeringen.
            self.assertEqual(lest_tilbake["balansert_ale"], maal["balansert_ale"])

    def test_egendefinert_bevarer_brukerens_egne_grenser(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = os.path.join(tmp, "water_targets.json")
            import json
            with open(os.path.join(_repo_root(), "data", "water_targets.json"), encoding="utf-8") as f:
                maal = json.load(f)

            maal["egendefinert"]["ca_min"] = 12.0
            maal["egendefinert"]["ca_max"] = 20.0
            maal["egendefinert"]["so4_min"] = 5.0
            maal["egendefinert"]["so4_max"] = 15.0
            lagre_vannmaal(maal)

            # En anbefaling for en helt annen stil (som IKKE peker på
            # "egendefinert") skal ALDRI påvirke hva som er lagret der.
            anbefal_vannmaal("IPA", last_vannmaal())
            anbefal_vannmaal("Stout", last_vannmaal())

            lest_tilbake = last_vannmaal()
            self.assertEqual(lest_tilbake["egendefinert"]["ca_min"], 12.0)
            self.assertEqual(lest_tilbake["egendefinert"]["ca_max"], 20.0)
            self.assertEqual(lest_tilbake["egendefinert"]["so4_min"], 5.0)
            self.assertEqual(lest_tilbake["egendefinert"]["so4_max"], 15.0)


class Test4StandardprofileneMutererIkke(unittest.TestCase):
    def test_last_vannmaal_returnerer_uavhengige_kopier_per_kall(self):
        maal_1 = last_vannmaal()
        maal_1["lys_lager_pils"]["ca_max"] = 9999.0
        maal_1["balansert_ale"]["anbefalte_stiler"].append("Noe oppdiktet")

        maal_2 = last_vannmaal()
        self.assertNotEqual(maal_2["lys_lager_pils"]["ca_max"], 9999.0)
        self.assertNotIn("Noe oppdiktet", maal_2["balansert_ale"]["anbefalte_stiler"])

    def test_redigering_av_en_profil_muterer_ikke_en_annen_i_samme_dict(self):
        maal = last_vannmaal()
        original_humledrevet = dict(maal["humledrevet_ol"])
        maal["lys_lager_pils"]["ca_max"] = 12345.0
        self.assertEqual(maal["humledrevet_ol"], original_humledrevet)


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    unittest.main()
