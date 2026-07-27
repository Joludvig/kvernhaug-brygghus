"""
Regresjonstest: solveren (foreslaa_salter) og UI-et (ui/water_panel.py) skal
ALDRI rapportere en målprofil som fullt oppnådd når HCO3, Mg, Na eller et
annet ion fortsatt ligger utenfor målområdet etter at kun CaCl2·2H2O og
gips er brukt — se modules/water_chemistry.py sin vurder_maaloppnaelse().

Bakgrunn (rapportert av bruker): med Jordalsvatnet 2025 (HCO3 ≈ 43 mg/L)
kan verken "Lys lager og pils" (HCO3-mål 0–25) eller "Mørk maltøl –
porter/stout" (HCO3-mål 80–150) løses med bare de to saltene solveren
tilbyr — HCO3 er hverken i CaCl2·2H2O eller gips sin ionfraksjon. Dette må
vises som en tydelig, eksplisitt tre-delt status: full_match / delvis_match
/ uoppnaelig_med_valgte_salter — aldri antydet som "løst".

Ingen automatisk syre-/fortynnings-/RO-/natron-dosering implementeres her
— kun tydeligere klassifisering og tekst rundt det eksisterende
2-salt-forslaget.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.water_chemistry import (
    last_vannkilder, last_vannmaal, foreslaa_salter, beregn_sluttprofil,
    vurder_maaloppnaelse,
)

_JORDALSVATNET = {"ca": 20.0, "mg": 0.5, "na": 4.5, "cl": 9.7, "so4": 8.1, "hco3": 43.0}

_KVERNHAUG_MAAL = {
    "ca_min": 50, "ca_max": 65, "mg_min": 0, "mg_max": 8, "na_min": 0, "na_max": 20,
    "cl_min": 50, "cl_max": 70, "so4_min": 30, "so4_max": 45, "hco3_min": 25, "hco3_max": 60,
}


def _ekte_maalprofiler():
    return last_vannmaal()


class TestUoppnaeligMedValgteSalterJordalsvatnet(unittest.TestCase):
    """De to konkrete eksemplene rapportert av bruker."""

    def test_lys_lager_pils_hco3_over_maal_er_uoppnaaelig(self):
        maal = _ekte_maalprofiler()["lys_lager_pils"]
        self.assertLess(maal["hco3_max"], _JORDALSVATNET["hco3"])  # 25 < 43 — forutsetning

        forslag, forklaring = foreslaa_salter(_JORDALSVATNET, maal, 20.0)
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, forslag, 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, maal, forslag)

        self.assertEqual(vurdering["status"], "uoppnaelig_med_valgte_salter")
        hco3_avvik = next(a for a in vurdering["avvik"] if a["ion"] == "hco3")
        self.assertEqual(hco3_avvik["status"], "over")
        self.assertFalse(hco3_avvik["kan_justeres_med_valgte_salter"])
        # Solverens EGEN forklaringstekst må navngi HCO3 eksplisitt — den
        # skal ALDRI late som forslaget løser hele målprofilen.
        self.assertIn("HCO3", forklaring)
        self.assertIn("IKKE", forklaring)

    def test_mork_maltol_hco3_under_maal_er_uoppnaaelig(self):
        maal = _ekte_maalprofiler()["mork_maltol_porter_stout"]
        self.assertGreater(maal["hco3_min"], _JORDALSVATNET["hco3"])  # 80 > 43 — forutsetning

        forslag, forklaring = foreslaa_salter(_JORDALSVATNET, maal, 20.0)
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, forslag, 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, maal, forslag)

        self.assertEqual(vurdering["status"], "uoppnaelig_med_valgte_salter")
        hco3_avvik = next(a for a in vurdering["avvik"] if a["ion"] == "hco3")
        self.assertEqual(hco3_avvik["status"], "under")
        self.assertFalse(hco3_avvik["kan_justeres_med_valgte_salter"])
        self.assertIn("HCO3", forklaring)
        self.assertIn("IKKE", forklaring)

    def test_ingen_automatisk_korreksjon_foreslas_for_hco3(self):
        # Solveren skal IKKE ha begynt å foreslå natron/syre/fortynning for
        # å dekke HCO3 — kun de to opprinnelige saltene (eller ingen).
        maal = _ekte_maalprofiler()["mork_maltol_porter_stout"]
        forslag, _ = foreslaa_salter(_JORDALSVATNET, maal, 20.0)
        salt_ider = {s["salt_id"] for s in forslag}
        self.assertTrue(salt_ider.issubset({"cacl2_2h2o", "gips"}))
        self.assertNotIn("natron", salt_ider)
        self.assertNotIn("kalsiumkarbonat", salt_ider)


class TestFullMatchRegresjon(unittest.TestCase):
    """Regresjon: kontrollscenarioet (Wiesn-Märzen) skal fortsatt
    klassifiseres som fullt oppnådd — denne nye klassifiseringen skal
    IKKE gjøre et tidligere fungerende scenario til et falskt avvik."""

    def test_wiesn_scenario_er_full_match(self):
        maal = _ekte_maalprofiler()["kvernhaug_maltpreget_tysk_lager"]
        forslag, forklaring = foreslaa_salter(_JORDALSVATNET, maal, 35.5)
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, forslag, 35.5)
        vurdering = vurder_maaloppnaelse(sluttprofil, maal, forslag)

        self.assertEqual(vurdering["status"], "full_match")
        self.assertEqual(vurdering["avvik"], [])
        self.assertNotIn("IKKE", forklaring)


class TestDelvisMatch(unittest.TestCase):
    """Et ion som ER blant de valgte saltenes ionfraksjoner, men som ikke
    (ennå) er justert helt inn i målområdet, skal klassifiseres som
    "delvis_match" — forskjellig fra "uoppnaelig", fordi mer av det
    samme saltet i prinsippet kan løse det. Målprofilen under er bevisst
    vidåpen for alle andre ioner enn SO4, slik at KUN SO4 er utenfor og
    testen isolerer akkurat det skillet den skal bevise."""

    _KUN_SO4_MAAL = {
        "ca_min": 0, "ca_max": 1000, "mg_min": 0, "mg_max": 1000, "na_min": 0, "na_max": 1000,
        "cl_min": 0, "cl_max": 1000, "so4_min": 30, "so4_max": 45, "hco3_min": 0, "hco3_max": 1000,
    }

    def test_utilstrekkelig_gips_gir_delvis_match_ikke_uoppnaaelig(self):
        # Et bevisst FOR LITE gips-tilsetning — SO4 havner fortsatt under
        # målet, men gips ER i bruk og PÅVIRKER SO4, så avviket er
        # løsbart (bare øk mengden), ikke fundamentalt uoppnåelig.
        salter = [{"salt_id": "gips", "gram": 0.05, "renhet": 1.0}]
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, salter, 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, self._KUN_SO4_MAAL, salter)

        self.assertEqual(vurdering["status"], "delvis_match")
        so4_avvik = next(a for a in vurdering["avvik"] if a["ion"] == "so4")
        self.assertEqual(so4_avvik["status"], "under")
        self.assertTrue(so4_avvik["kan_justeres_med_valgte_salter"])

    def test_ion_utenfor_men_ikke_i_bruk_gir_uoppnaaelig_ikke_delvis(self):
        # Samme underskudd på SO4, men INGEN salt som påvirker SO4 er
        # faktisk valgt (kun CaCl2, som ikke rører SO4) — da er det
        # "uoppnaelig_med_valgte_salter", ikke "delvis_match".
        salter = [{"salt_id": "cacl2_2h2o", "gram": 1.0, "renhet": 1.0}]
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, salter, 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, self._KUN_SO4_MAAL, salter)

        self.assertEqual(vurdering["status"], "uoppnaelig_med_valgte_salter")
        so4_avvik = next(a for a in vurdering["avvik"] if a["ion"] == "so4")
        self.assertFalse(so4_avvik["kan_justeres_med_valgte_salter"])


class TestAlleredeOverMaksIKildevann(unittest.TestCase):
    """Salter kan bare TILSETTE ioner — et ion som allerede er over maks i
    kildevannet ALENE er uoppnåelig uansett hvilke(t) salt som er valgt,
    fordi ingen tilgjengelig handling kan senke det."""

    def test_kildevann_over_maks_er_uoppnaaelig_selv_med_riktig_salt_valgt(self):
        hoyt_cl_kildevann = {"ca": 20.0, "mg": 0.5, "na": 4.5, "cl": 300.0, "so4": 8.1, "hco3": 43.0}
        salter = [{"salt_id": "cacl2_2h2o", "gram": 0.5, "renhet": 1.0}]  # cl ER i bruk
        sluttprofil = beregn_sluttprofil(hoyt_cl_kildevann, salter, 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, _KVERNHAUG_MAAL, salter)

        self.assertEqual(vurdering["status"], "uoppnaelig_med_valgte_salter")
        cl_avvik = next(a for a in vurdering["avvik"] if a["ion"] == "cl")
        self.assertEqual(cl_avvik["status"], "over")
        self.assertFalse(cl_avvik["kan_justeres_med_valgte_salter"])


class TestUkjentOgTomInput(unittest.TestCase):
    def test_ingen_maalprofil_gir_ukjent_status(self):
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, [], 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, None, [])
        self.assertEqual(vurdering["status"], "ukjent")
        self.assertEqual(vurdering["avvik"], [])

    def test_ingen_salter_i_bruk_klassifiserer_korrekt(self):
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, [], 20.0)
        vurdering = vurder_maaloppnaelse(sluttprofil, _KVERNHAUG_MAAL, None)
        # Uten noen salter i bruk kan INGEN avvik justeres.
        self.assertIn(vurdering["status"], ("uoppnaelig_med_valgte_salter", "full_match"))
        for a in vurdering["avvik"]:
            self.assertFalse(a["kan_justeres_med_valgte_salter"])


if __name__ == "__main__":
    unittest.main()
