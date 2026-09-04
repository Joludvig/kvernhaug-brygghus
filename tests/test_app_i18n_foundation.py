"""
Fokuserte tester for App NO/EN i18n-fundamentet (issue #58, APP PRI 6):

    modules/i18n.py -- ren nøkkel-/interpolasjons-/fallback-logikk, ingen
                        Streamlit-avhengighet (kjøres uten Streamlit-kontekst).
    ui/i18n.py       -- Streamlit-halvdelen (st.session_state-språkvalg +
                        språkvelger-widget), verifisert her via den EKTE
                        app.py (samme mønster som test_real_app_process_flow.py)
                        gjennom den representative skiven denne runden
                        konverterte: sidebaren (navigasjon) og hovedfanene
                        (layout).

Dekker eksplisitt de fire punktene issue #58 sitt "Scope" punkt 6 krever:
    1. begge språk løser kjente nøkler,
    2. en manglende/ugyldig nøkkel feiler synlig, ikke stille,
    3. interpolasjon virker,
    4. valgt visningsspråk endrer ALDRI lagret/beregnet oppskriftsdata.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.i18n import SPRAK_DEFAULT, SPRAK_LISTE, TEKSTER, t as ren_t
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

# Nøkler som faktisk brukes i den konverterte skiven (app.py sine fanenavn
# og ui/sidebar.py) -- se modules/i18n.py sin TEKSTER.
_KJENTE_NOKLER = [
    "tabs.oppskrift", "tabs.innkjop", "tabs.bryggdag", "tabs.verktoy",
    "sprak.valger.label", "sprak.valger.no", "sprak.valger.en",
    "sidebar.demo_advarsel", "sidebar.tittel", "sidebar.velg_brygg_label",
    "sidebar.velg_placeholder", "sidebar.ingen_lagret", "sidebar.lastet_ok",
]

# Nøkler der no/en BEVISST er ulik tekst (ekskluderer f.eks.
# sprak.valger.no/en, som viser samme flagg-navn på begge språk).
_NOKLER_MED_FORVENTET_ULIK_TEKST = [
    "tabs.oppskrift", "tabs.innkjop", "tabs.bryggdag", "tabs.verktoy",
    "sprak.valger.label", "sidebar.demo_advarsel", "sidebar.tittel",
    "sidebar.velg_brygg_label", "sidebar.velg_placeholder", "sidebar.ingen_lagret",
    "sidebar.lastet_ok",
]


def _er_manglende_nokkel_markor(tekst):
    return isinstance(tekst, str) and tekst.startswith("??") and tekst.endswith("??") and len(tekst) > 4


class TestModulesI18nPure(unittest.TestCase):
    """modules/i18n.py sin t() -- ingen Streamlit-kontekst nødvendig."""

    def test_no_en_nokkelsymmetri(self):
        self.assertEqual(
            set(TEKSTER["no"].keys()), set(TEKSTER["en"].keys()),
            "TEKSTER['no'] og TEKSTER['en'] har ulike nøkkelsett -- brutt symmetri",
        )

    def test_begge_sprak_slaar_opp_alle_kjente_nokler(self):
        for nokkel in _KJENTE_NOKLER:
            for sprak in SPRAK_LISTE:
                tekst = ren_t(nokkel, sprak)
                self.assertTrue(tekst, f"{nokkel}/{sprak} ga en tom/falsy tekst")
                self.assertFalse(
                    _er_manglende_nokkel_markor(tekst),
                    f"{nokkel}/{sprak} ga en manglende-nøkkel-markør: {tekst!r}",
                )

    def test_no_og_en_gir_faktisk_ulik_tekst_for_representative_nokler(self):
        for nokkel in _NOKLER_MED_FORVENTET_ULIK_TEKST:
            self.assertNotEqual(
                ren_t(nokkel, "no"), ren_t(nokkel, "en"),
                f"{nokkel} er identisk på no/en -- sannsynlig glemt oversettelse",
            )

    def test_manglende_nokkel_feiler_synlig_ikke_med_exception(self):
        for sprak in list(SPRAK_LISTE) + ["fr", "", None]:
            tekst = ren_t("dette.finnes.aldri.i.noen.sprak", sprak)
            self.assertEqual(tekst, "??dette.finnes.aldri.i.noen.sprak??")

    def test_ugyldig_sprakkode_faller_tilbake_til_default_for_kjent_nokkel(self):
        for ugyldig in ["fr", "", None, "NO", "En"]:
            self.assertEqual(
                ren_t("tabs.oppskrift", ugyldig), ren_t("tabs.oppskrift", SPRAK_DEFAULT),
                f"sprak={ugyldig!r} falt ikke tilbake til default for en kjent nøkkel",
            )

    def test_interpolasjon_fyller_parameter_i_begge_sprak(self):
        for sprak in SPRAK_LISTE:
            tekst = ren_t("sidebar.lastet_ok", sprak, navn="Kvernhaug Testbrygg")
            self.assertIn("Kvernhaug Testbrygg", tekst)
            self.assertNotIn("{navn}", tekst)

    def test_manglende_interpolasjonsparameter_krasjer_ikke(self):
        # Ingen navn= gitt -- plassholderen skal stå urørt, ALDRI en KeyError.
        tekst = ren_t("sidebar.lastet_ok", "no")
        self.assertIn("{navn}", tekst)

    def test_ekstra_ubrukt_interpolasjonsparameter_krasjer_ikke(self):
        tekst = ren_t("tabs.oppskrift", "no", ubrukt_param="noe")
        self.assertEqual(tekst, ren_t("tabs.oppskrift", "no"))


class TestAppI18nIntegrasjon(unittest.TestCase):
    """Kjører den EKTE app.py via AppTest (samme mønster som
    test_real_app_process_flow.py) gjennom den konverterte skiven --
    sidebar (navigasjon) + fanenavn (layout) + selectbox/radio (widgets)
    -- og beviser at et språkbytte ALDRI rører lagret/beregnet
    oppskriftsdata (issue #58, Scope punkt 6, siste kulepunkt)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            "E2E I18n Testbrygg", 20.0, 0.72,
            [{"id": "weyermann_pilsner", "mengde": 4.5}],
            [{"id": "magnum", "gram": 20, "tid": 60}],
            "safale_us_05", 1.048, 1.011, 4.9, 22, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_sprakbytte_oversetter_ui_uten_a_endre_lagret_eller_beregnet_data(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        # Default er norsk, og sidebar-teksten er faktisk oversatt.
        self.assertEqual(at.session_state["sprak"], "no")
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").label,
            "Velg et brygg fra harddisken:",
        )

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E I18n Testbrygg").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        malt_for = json.dumps(at.session_state["valgt_malt"], sort_keys=True)
        humle_for = json.dumps(at.session_state["valgt_humle"], sort_keys=True)
        gjaer_for = at.session_state["valgt_gjaer_id"]
        navn_for = at.session_state["gjeldende_navn"]
        batch_for = at.session_state["batch_volum_input"]

        # Selve språkbyttet -- den nye, representative widgeten denne
        # runden legger til.
        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved språkbytte: {at.exception}")

        self.assertEqual(at.session_state["sprak"], "en")
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").label,
            "Choose a brew from disk:",
        )

        # Kjernepåstanden: oppskriftsdata (det som faktisk lagres/brukes
        # til beregning) er BYTE-IDENTISK før og etter språkbyttet.
        self.assertEqual(json.dumps(at.session_state["valgt_malt"], sort_keys=True), malt_for)
        self.assertEqual(json.dumps(at.session_state["valgt_humle"], sort_keys=True), humle_for)
        self.assertEqual(at.session_state["valgt_gjaer_id"], gjaer_for)
        self.assertEqual(at.session_state["gjeldende_navn"], navn_for)
        self.assertEqual(at.session_state["batch_volum_input"], batch_for)

        # Ingen synlig "manglende nøkkel"-markør noe sted i den fullt
        # rendrede appen (ville bevist en glemt/feilstavet nøkkel i den
        # konverterte skiven).
        alle_tekster = (
            [w.value for w in at.markdown]
            + [w.value for w in at.warning]
            + [w.value for w in at.info]
            + [w.value for w in at.success]
        )
        for tekst in alle_tekster:
            self.assertFalse(
                _er_manglende_nokkel_markor(tekst),
                f"Fant en synlig manglende-i18n-nøkkel i rendret UI: {tekst!r}",
            )

    def test_sprak_bytte_med_plassholder_valgt_endrer_ikke_widgetverdi(self):
        """Regresjon for sentinel-fiksen i ui/sidebar.py: plassholderen i
        oppskrift-selectboksen er en språknøytral sentinel (ikke selve
        visningsteksten), nettopp slik at et språkbytte mens plassholderen
        står valgt aldri gir en `key`-bundet widgetverdi som ikke lenger
        finnes i den nye, oversatte `options`-listen."""
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        # Plassholderen er default -- ingen lagret oppskrift er valgt ennå.
        self.assertNotIn("_last_loaded_recipe", at.session_state)

        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved språkbytte: {at.exception}")
        self.assertNotIn("_last_loaded_recipe", at.session_state)

        # Selectboksen må fortsatt fungere normalt etter bytte (widgeten
        # ble ikke "fanget" i en ugyldig verdi av det oversatte alternativet).
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E I18n Testbrygg").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting etter språkbytte: {at.exception}")
        self.assertEqual(at.session_state["_last_loaded_recipe"], "E2E I18n Testbrygg")


if __name__ == "__main__":
    unittest.main()
