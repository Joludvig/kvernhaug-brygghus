"""
Ende-til-ende-regresjonstest for hele den faktiske appflyten:

    sidebar (last oppskrift) -> recipe_context -> process_panel
        -> lag_brewday_plan() -> brewday_template (eksport)

Bakgrunn: en tidligere runde rettet en bug i ui/process_panel.py der
panelet ikke oppdaget at EN ANNEN oppskrift var blitt aktiv (satt av
ui/sidebar.py direkte i session_state), og dermed kunne overskrive en
nettopp lastet prosessprofil med en blanding av gammel/ny meskeplan.

Isolerte tester av process_panel.py alene (tests/test_process_panel.py)
beviste at panelets EGEN logikk var korrekt, men brukeren rapporterte at
feilen fortsatt viste seg i den virkelige appflyten. Dette modulet
bruker AppTest på en realistisk testvert (tests/_full_flow_app.py) som
kjører de EKTE modulene (ui/sidebar.py, modules/recipe_context.py,
ui/process_panel.py, modules/brewday_calc.py, modules/brewday_template.py)
i nøyaktig samme rekkefølge som app.py, og logger alle mellomledd:

    1. st.session_state["aktiv_prosessprofil"]  (via _debug_aktiv_prosessprofil_etter_panel)
    2. ctx["recipe"]["process_profile"]         (via _debug_ctx_process_profile)
    3. process_profile sendt til lag_brewday_plan() (via _debug_process_profile_til_plan)
    4. ferdig brewday_plan                      (via _debug_plan)
    5. eksportert HTML                          (via _debug_export_html)

Fant den GENUINE gjenværende hybrid-kilden: process_panel.py resynket
riktig fra st.session_state["aktiv_prosessprofil"] ved lasting, MEN
stolte blindt på HVA SOM HELST som lå der for en "kjent" standardprofil
(f.eks. process_id="hochkurz") — inkludert en profil som i
utgangspunktet var korrupt/hybrid FRA FØR (en allerede aktiv, "poisonet"
session_state fra før forrige fiks, eller en lagret oppskriftsfil skrevet
av en eldre, buggy app-versjon). Siden Streamlit session_state overlever
både hot-reload (kode endres, sesjonen består) og i praksis også en
oppskriftsfil på disk overlever en full restart, kunne den gamle
hybriden vises på nytt selv etter at selve VALG-flyten var rettet.

Løsningen: for enhver STANDARDPROFIL (alt unntatt "egendefinert") bygges
mash_steps ALLTID på nytt fra hent_standardprofil() sin rene mal — aldri
fra en lagret/allerede-aktiv profils egne (potensielt korrupte) steg. Kun
"egendefinert" (der frie steg er selve poenget) beholder lagrede steg
uendret.

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

from modules.process_profiles import hent_standardprofil
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_full_flow_app.py")


def _last_db(navn):
    with open(os.path.join(_REPO_ROOT, "data", navn), encoding="utf-8") as f:
        return json.load(f)


_GJAER_DB = _last_db("master_gjaer_v2.json")
_GJAER_ID = next(k for k in _GJAER_DB if not k.startswith("_"))


class _EndeTilEndeTestCase(unittest.TestCase):
    """Isolerer hver test i sin egen midlertidige recipes-mappe (via
    KVERNHAUG_RECIPES_DIR — se modules/recipe_storage.py), slik at testene
    aldri leser eller skriver til de ekte, lagrede oppskriftene i
    recipes/. Nødvendig fordi streamlit.testing.v1.AppTest re-importerer
    modultreet friskt per kjøring, så en enkel
    `modules.recipe_storage.MAPPE = tmpdir`-monkeypatch overlever ikke."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _lagre_oppskrift(self, navn, process_profile):
        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            navn, 23.0, 0.75, [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            _GJAER_ID, 1.050, 1.012, 5.0, 25, 8, {},
            process_profile=process_profile,
        )
        recipe_storage.lagre_oppskrift(recipe)

    def _ny_at(self):
        at = AppTest.from_file(_APP)
        at.run()
        return at


class TestFullFlowEnkelInfusjonTilHochkurz(_EndeTilEndeTestCase):
    """Krav 1-8: last en oppskrift som er lagret med Enkel infusjon, velg
    Hochkurz inne i appen, og verifiser at ALLE ledd i kjeden fram til
    ferdig eksportert HTML viser nøyaktig 63/40, 70/30, 77/10 — aldri en
    rest av 66/60 eller 78/5."""

    def test_full_kjede_fra_lasting_til_eksport(self):
        self._lagre_oppskrift("E2E Enkel Infusjon", hent_standardprofil("enkel_infusjon"))
        at = self._ny_at()

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Enkel Infusjon").run()
        self.assertEqual(at.session_state["_last_loaded_recipe"], "E2E Enkel Infusjon")
        # Umiddelbart etter lasting (før noe valg er gjort i selve
        # appen): aktiv_prosessprofil skal være nøyaktig Enkel infusjon.
        aktiv_ved_lasting = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv_ved_lasting["navn"], "Enkel infusjon")
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in aktiv_ved_lasting["mash_steps"]],
            [(66.0, 60), (78.0, 5)],
        )

        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()

        forventet = [(63.0, 40), (70.0, 30), (77.0, 10)]

        # 1) st.session_state["aktiv_prosessprofil"]
        aktiv = at.session_state["_debug_aktiv_prosessprofil_etter_panel"]
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual([(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]], forventet)

        # 2) ctx["recipe"]["process_profile"] — bygges FØR prosesspanelet
        #    kjører (kjent, dokumentert ett-rerun-etterslep), men skal
        #    ALDRI være en hybrid — kun ev. ett steg "bak".
        ctx_profil = at.session_state["_debug_ctx_process_profile"]
        for s in ctx_profil["mash_steps"]:
            self.assertIn(
                (s["temperatur"], s["varighet"]),
                [(66.0, 60), (78.0, 5)],
                "ctx-profilen inneholdt et steg som IKKE hører til noen ordentlig profil (hybrid).",
            )

        # 3) process_profile sendt til lag_brewday_plan()
        til_plan = at.session_state["_debug_process_profile_til_plan"]
        self.assertEqual(til_plan["navn"], "Hochkurz (stegmesk)")
        self.assertEqual([(s["temperatur"], s["varighet"]) for s in til_plan["mash_steps"]], forventet)

        # 4) ferdig brewday_plan
        plan = at.session_state["_debug_plan"]
        self.assertEqual(plan["prosess_profil"]["navn"], "Hochkurz (stegmesk)")
        self.assertEqual([(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]], forventet)

        # 5) eksportert HTML — den faktiske bryggedagsark-eksporten.
        html = at.session_state["_debug_export_html"]
        self.assertIn("Bryggemåte: Hochkurz (stegmesk)", html)
        self.assertIn("63.0°C", html)
        self.assertIn("40 min", html)
        self.assertIn("70.0°C", html)
        self.assertIn("30 min", html)
        self.assertIn("77.0°C", html)
        self.assertIn("10 min", html)
        self.assertNotIn("66.0°C", html)
        self.assertNotIn("78.0°C", html)
        self.assertNotIn("66°C", html)
        self.assertNotIn("78°C", html)


class TestFullFlowKorruptLagretProfilHelbredes(_EndeTilEndeTestCase):
    """Krav 8: en oppskrift lagret (av en eldre/buggy app-versjon, eller
    ved direkte filredigering) med en profil som PÅSTÅR å være Hochkurz
    men bærer en hybrid meskeplan, skal ALDRI eksporteres som-is — den
    skal helbredes til den ekte Hochkurz-malen ved lasting."""

    def test_korrupt_lagret_hochkurz_profil_gir_ren_eksport(self):
        korrupt_profil = {
            "process_id": "hochkurz", "navn": "Hochkurz (stegmesk)",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"},
                {"temperatur": 78.0, "varighet": 5,  "stegtype": "mashout",  "kommentar": "Mashout"},
                {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout",  "kommentar": "Mashout"},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 20, "brukernotater": "",
        }
        self._lagre_oppskrift("E2E Korrupt Hochkurz", korrupt_profil)
        at = self._ny_at()

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Korrupt Hochkurz").run()

        html = at.session_state["_debug_export_html"]
        self.assertIn("63.0°C", html)
        self.assertIn("70.0°C", html)
        self.assertIn("77.0°C", html)
        self.assertNotIn("66.0°C", html)
        self.assertNotIn("78.0°C", html)

        plan = at.session_state["_debug_plan"]
        self.assertEqual(
            [(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]],
            [(63.0, 40), (70.0, 30), (77.0, 10)],
        )


if __name__ == "__main__":
    unittest.main()
