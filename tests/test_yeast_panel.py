"""
V2.2 G3K (issue #384) — regresjonstester for Gjæringstemperatur
Learn -> Plan-broen i ui/yeast_panel.py, se docs/development/
v22_g3j_fermentation_learn_plan_contract.md.

Speiler EKSAKT samme mønster som TestLaerBroMeskingBridge i
tests/test_process_panel.py (issue #352) for selve broen, pluss egne
tester for det nye, valgfrie planlagte gjæringstemperatur-feltet og dets
rene resolver-funksjon.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.i18n import t as _t
from modules.recipe import bygg_recipe_object, resolve_fermentation_temp_target_c
from bryggeskole.pilot_fermentation import PilotContentError, read_pilot_file, render_chunk

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_yeast_panel_app.py")


def _ny_at():
    at = AppTest.from_file(_APP)
    at.run()
    return at


def _finn_laer_bro(at, sprak="no"):
    tittel = _t("gjaering.laer_bro.tittel", sprak)
    treff = [e for e in at.expander if e.label == tittel]
    assert len(treff) == 1, f"Fant ikke akkurat én Learn->Plan-bro med label={tittel!r}: {[e.label for e in at.expander]}"
    return treff[0]


class TestLaerBroGjaeringBridge(unittest.TestCase):
    """§4/§9.2/§10.1 i kontrakten: kollapset som standard, viser
    CHUNK-FERM-A/B/C uendret i NO/EN, feiler lukket ved ugyldig
    pilotinnhold."""

    def test_broen_finnes_og_er_kollapset_som_standard(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        self.assertFalse(bro.proto.expanded)

    def test_broen_viser_chunk_ferm_a_b_c_uendret_paa_norsk(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        tekster = [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]
        pilot = read_pilot_file()
        chunker = {c["id"]: c for c in pilot["chunks"]}
        forventet = [
            render_chunk(chunker["CHUNK-FERM-A"], "no")["text"],
            render_chunk(chunker["CHUNK-FERM-B"], "no")["text"],
            render_chunk(chunker["CHUNK-FERM-C"], "no")["text"],
        ]
        self.assertEqual(tekster, forventet)

    def test_broen_viser_chunk_ferm_a_b_c_uendret_paa_engelsk(self):
        at = AppTest.from_file(_APP)
        at.session_state["sprak"] = "en"
        at.run()
        bro = _finn_laer_bro(at, sprak="en")
        tekster = [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]
        pilot = read_pilot_file()
        chunker = {c["id"]: c for c in pilot["chunks"]}
        forventet = [
            render_chunk(chunker["CHUNK-FERM-A"], "en")["text"],
            render_chunk(chunker["CHUNK-FERM-B"], "en")["text"],
            render_chunk(chunker["CHUNK-FERM-C"], "en")["text"],
        ]
        self.assertEqual(tekster, forventet)

    def test_ugyldig_pilotinnhold_krasjer_ikke_oppskrift_fanen(self):
        with mock.patch(
            "ui.yeast_panel._pilot_gjaring.read_pilot_file",
            side_effect=PilotContentError(["ugyldig innhold"]),
        ):
            at = _ny_at()
        self.assertFalse(at.exception, f"Panelet skal aldri krasje ved ugyldig pilotinnhold: {at.exception}")
        bro = _finn_laer_bro(at)
        feilmeldinger = " ".join(e.value for e in at.error)
        self.assertIn("Kunne ikke laste leksjonsinnholdet akkurat nå.", feilmeldinger)
        markdown_barn = [c for c in bro.children.values() if type(c).__name__ == "Markdown"]
        self.assertEqual(markdown_barn, [], "Ingen chunk-tekst skal rendres når pilotinnholdet er ugyldig.")


class TestPlanlagtGjaeringstemperaturFelt(unittest.TestCase):
    """§5/§8 i kontrakten: feltet starter tomt/None, eksponerer ingen
    bryggefaglig min/max, og oppdaterer session_state ved bruk."""

    def test_feltet_er_tomt_som_standard_i_en_helt_ny_sesjon(self):
        at = _ny_at()
        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        widget = at.number_input(key="gjaering_temp_maal_c")
        self.assertIsNone(widget.value)

    def test_feltet_har_ingen_bryggefaglig_min_eller_max(self):
        # Ingen bryggefaglig grenseverdi skal håndheves (§5/§8 i
        # kontrakten) -- en verdi langt utenfor enhver rimelig gjærings-
        # temperatur skal godtas uendret, ikke klippes til et
        # "fasit"-intervall.
        at = _ny_at()
        at.number_input(key="gjaering_temp_maal_c").set_value(-99.0).run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], -99.0)
        at.number_input(key="gjaering_temp_maal_c").set_value(999.0).run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 999.0)

    def test_a_sette_feltet_oppdaterer_session_state(self):
        at = _ny_at()
        at.number_input(key="gjaering_temp_maal_c").set_value(18.5).run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 18.5)

    def test_broen_ligger_over_temperaturfeltet(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        felt = at.number_input(key="gjaering_temp_maal_c")
        hoved = at.main
        indeks_bro = min(i for i, n in hoved.children.items() if n is bro)
        indeks_felt = min(i for i, n in hoved.children.items() if n is felt)
        self.assertLess(indeks_bro, indeks_felt)


class TestResolveFermentationTempTargetC(unittest.TestCase):
    """Ren policy-funksjon (modules/recipe.py) — kun type-/finitthets-
    hygiene, ingen bryggefaglig gyldighetssjekk (§5 i kontrakten)."""

    def test_gyldig_float_beholdes(self):
        self.assertEqual(resolve_fermentation_temp_target_c(18.5), 18.5)

    def test_gyldig_int_konverteres_til_float(self):
        self.assertEqual(resolve_fermentation_temp_target_c(20), 20.0)
        self.assertIsInstance(resolve_fermentation_temp_target_c(20), float)

    def test_negativ_verdi_beholdes_ingen_brewing_range(self):
        # Ingen bryggefaglig min/max håndheves her -- se docs/development/
        # v22_g3j_fermentation_learn_plan_contract.md §5.
        self.assertEqual(resolve_fermentation_temp_target_c(-5.0), -5.0)

    def test_none_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(None))

    def test_manglende_felt_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(None))

    def test_bool_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(True))
        self.assertIsNone(resolve_fermentation_temp_target_c(False))

    def test_streng_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c("18.5"))

    def test_liste_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c([18.5]))

    def test_nan_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(float("nan")))

    def test_positiv_uendelig_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(float("inf")))

    def test_negativ_uendelig_gir_none(self):
        self.assertIsNone(resolve_fermentation_temp_target_c(float("-inf")))


class TestByggRecipeObjectFermentationTempTargetC(unittest.TestCase):
    """§5 i kontrakten: nytt, valgfritt Recipe Object-felt, lagret
    ubetinget (samme mønster som water_*-feltene)."""

    def _oppskrift(self, **kwargs):
        return bygg_recipe_object(
            navn="Test", batch_size=20.0, efficiency=0.75,
            malts=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            hops=[{"id": "east_kent_goldings", "gram": 20.0, "tid": 60}],
            yeast="safale_us_05",
            og=1.050, fg=1.010, abv=5.2, ibu=20, ebc=8, flavor_profile={},
            **kwargs,
        )

    def test_standardverdi_er_none(self):
        recipe = self._oppskrift()
        self.assertIn("fermentation_temp_target_c", recipe)
        self.assertIsNone(recipe["fermentation_temp_target_c"])

    def test_oppgitt_float_lagres_ubetinget(self):
        recipe = self._oppskrift(fermentation_temp_target_c=18.5)
        self.assertEqual(recipe["fermentation_temp_target_c"], 18.5)


if __name__ == "__main__":
    unittest.main()
