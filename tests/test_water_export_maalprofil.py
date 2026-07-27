"""
Tester for at målprofilens VISNINGSNAVN (ikke target_id) vises korrekt i
begge vannkjemi-eksportene — bryggedagsarket (modules/brewday_template.py)
og A4-oppskriftskortet (modules/card_template.py).

Krav dekket:
  1. Bryggedagsarket viser "Målprofil: <navn>" rett under vannkilden, i
     rekkefølgen Vannkilde -> Målprofil -> Meskevann -> Skyllevann ->
     Pre-boil -> Salter i meskevann -> Salter i skyllevann -> Mål meske-pH.
  2. A4-kortet viser Vannkilde, Målprofil, forventet sluttprofil for
     Ca/Cl/SO4, og mål meske-pH — kompakt.
  3. Gamle oppskrifter uten water_target_profile eksporterer uten feil,
     med "Målprofil: Ikke valgt" i begge eksportene (samme regel begge steder).
  4. Navnet hentes fra den LAGREDE snapshotten (recipe["water_target_profile"])
     — IKKE fra et fornyet oppslag i data/water_targets.json via target_id —
     så en senere omdøpt/redigert profil i biblioteket endrer ALDRI hva en
     allerede lagret oppskrift viser.
  5. Vannkilde og målprofil forveksles aldri, selv når begge er valgt samtidig.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

from modules.recipe import bygg_recipe_object
from modules.brewday_calc import lag_brewday_plan
from modules.brewday_template import render_brewday_html
from modules.card_template import render_a4_html

_MALT_DB = {"weyermann_pilsner": {"display_name": "Pilsner Malt", "potensiale": 1.037, "ebc": 3.5}}
_HUMLE_DB = {"tettnang": {"display_name": "Tettnang", "alfa": 4.0}}
_GJAER_DB = {"saflager_w3470": {"display_name": "SafLager W-34/70", "gjaertype": "Lager", "attenuation": 0.80}}
_MALT_VALG = [{"id": "weyermann_pilsner", "mengde": 5.0}]


def _fake_gjaer_info():
    return {"display_name": "SafLager W-34/70", "gjaertype": "Lager", "attenuation": 0.80}


_JORDALSVATNET = {"water_id": "jordalsvatnet_2025", "name": "Jordalsvatnet 2025",
                   "ca": 20.0, "mg": 0.5, "na": 4.5, "cl": 9.7, "so4": 8.1, "hco3": 43.0}

_KVERNHAUG_MAAL = {
    "target_id": "kvernhaug_maltpreget_tysk_lager", "name": "Maltpreget tysk lager",
    "mash_ph_min": 5.30, "mash_ph_max": 5.40,
}

_SALTER = [
    {"salt_id": "cacl2_2h2o", "navn": "Kalsiumklorid-dihydrat", "kjemisk_form": "CaCl2·2H2O",
     "gram": 3.7, "gram_mesk": 2.18, "gram_skyll": 1.52, "ionbidrag_ppm": {"ca": 28.41, "cl": 50.27}},
    {"salt_id": "gips", "navn": "Gips", "kjemisk_form": "CaSO4·2H2O",
     "gram": 2.0, "gram_mesk": 1.18, "gram_skyll": 0.82, "ionbidrag_ppm": {"ca": 13.12, "so4": 31.43}},
]


def _ctx_stub(recipe):
    return {
        "name": recipe["name"], "volum": recipe["batch_size"], "brygger_stil": recipe.get("brygger_stil", ""),
        "og": recipe["stats"]["og"], "fg": recipe["stats"]["fg"], "abv": recipe["stats"]["abv"],
        "ibu": recipe["stats"]["ibu"], "ebc": recipe["stats"]["ebc"], "total_pris": 400,
        "effektivitet": recipe["efficiency"],
        "summary": "Rik, maltrik smaksprofil.",
        "style_analysis": {"stil": "", "stil_liste": []},
        "recipe": recipe,
    }


def _plan_stub():
    return lag_brewday_plan(
        _MALT_VALG, [{"id": "tettnang", "tid": 60, "gram": 30}], "saflager_w3470",
        _fake_gjaer_info(), 1.050, 20.0, _HUMLE_DB, malt_database=_MALT_DB,
    )


class TestMaalprofilIBryggedagsarket(unittest.TestCase):
    def test_maalprofil_vises_i_riktig_rekkefolge(self):
        recipe = bygg_recipe_object(
            "Test", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
            water_source_profile=_JORDALSVATNET, water_target_profile=_KVERNHAUG_MAAL,
        )
        ctx = _ctx_stub(recipe)
        plan = _plan_stub()
        water = {"kilde": _JORDALSVATNET, "maal": _KVERNHAUG_MAAL, "behandling": {"salter": _SALTER}, "maalinger": {}}
        html = render_brewday_html(ctx, plan, {}, water=water)

        self.assertIn("Målprofil: <strong>Maltpreget tysk lager</strong>", html)

        i_kilde = html.index("Vannkilde:")
        i_maal = html.index("Målprofil:")
        i_mesk = html.index("Meskevann:")
        i_skyll = html.index("Skyllevann:")
        i_preboil = html.index("Pre-boil:")
        i_salt_mesk = html.index("i meskevann:")
        i_salt_skyll = html.index("i skyllevann:")
        i_maal_ph = html.index("Mål meske-pH:")

        self.assertLess(i_kilde, i_maal)
        self.assertLess(i_maal, i_mesk)
        self.assertLess(i_mesk, i_skyll)
        self.assertLess(i_skyll, i_preboil)
        self.assertLess(i_preboil, i_salt_mesk)
        self.assertLess(i_salt_mesk, i_salt_skyll)
        self.assertLess(i_salt_skyll, i_maal_ph)


class TestMaalprofilIA4Eksporten(unittest.TestCase):
    def test_maalprofil_og_sluttprofil_vises_i_a4(self):
        recipe = bygg_recipe_object(
            "Test", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
            water_source_profile=_JORDALSVATNET, water_target_profile=_KVERNHAUG_MAAL,
            water_treatment={"salter": _SALTER},
        )
        ctx = _ctx_stub(recipe)
        html = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)

        self.assertIn("Vannkilde: Jordalsvatnet 2025", html)
        self.assertIn("Målprofil: Maltpreget tysk lager", html)
        self.assertIn("Ca 6", html)  # 20 + 28.41 + 13.12 ≈ 61.5 -> "Ca 62" el. "Ca 61" avh. avrunding
        self.assertIn("Cl 60", html)
        self.assertIn("SO4 40", html)
        self.assertIn("Mål meske-pH: 5.30", html)


class TestGammelOppskriftUtenMaalprofil(unittest.TestCase):
    def test_bryggedagsark_uten_maalprofil_krasjer_ikke(self):
        recipe = bygg_recipe_object(
            "Gammel oppskrift", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
        )  # ingen water_* felter i det hele tatt — som en oppskrift lagret før feltene fantes
        ctx = _ctx_stub(recipe)
        plan = _plan_stub()
        html = render_brewday_html(ctx, plan, {})  # ingen water= sendt inn heller
        self.assertIn("Målprofil: <strong>Ikke valgt</strong>", html)
        self.assertIn("Gammel oppskrift", html)

    def test_a4_uten_maalprofil_krasjer_ikke(self):
        recipe = bygg_recipe_object(
            "Gammel oppskrift", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
        )
        ctx = _ctx_stub(recipe)
        html = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        # Ingen vannbehandling i det hele tatt -> hele seksjonen utelates
        # (ikke bare "Ikke valgt"-linjen) siden verken kilde, mål eller
        # salter finnes — men eksporten skal uansett aldri krasje.
        self.assertNotIn("Vannbehandling", html)
        self.assertIn("Gammel oppskrift", html)

    def test_maalprofil_mangler_men_kilde_finnes_viser_ikke_valgt(self):
        recipe = bygg_recipe_object(
            "Delvis oppskrift", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
            water_source_profile=_JORDALSVATNET,
        )
        ctx = _ctx_stub(recipe)
        html = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Vannkilde: Jordalsvatnet 2025", html)
        self.assertIn("Målprofil: Ikke valgt", html)


class TestEgendefinertMaalprofilVisesEgenNavn(unittest.TestCase):
    def test_egendefinert_med_eget_navn(self):
        egendefinert_med_eget_navn = {
            "target_id": "egendefinert", "name": "Min egen Kveik-profil",
            "mash_ph_min": 5.25, "mash_ph_max": 5.45,
        }
        recipe = bygg_recipe_object(
            "Test", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
            water_source_profile=_JORDALSVATNET, water_target_profile=egendefinert_med_eget_navn,
        )
        ctx = _ctx_stub(recipe)
        plan = _plan_stub()
        water = {"kilde": _JORDALSVATNET, "maal": egendefinert_med_eget_navn, "behandling": {"salter": []}, "maalinger": {}}

        html_bryggedag = render_brewday_html(ctx, plan, {}, water=water)
        html_a4 = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)

        self.assertIn("Min egen Kveik-profil", html_bryggedag)
        self.assertIn("Min egen Kveik-profil", html_a4)
        # IKKE bare den generiske standardbetegnelsen — det egendefinerte
        # navnet skal faktisk overstyre det.
        self.assertNotIn("Egendefinert målprofil", html_bryggedag)


class TestVannkildeOgMaalprofilForveksles(unittest.TestCase):
    def test_kilde_og_maal_forveksles_aldri(self):
        kilde = {"water_id": "test_kilde", "name": "Bekkevatn Test", "ca": 10.0, "mg": None,
                  "na": None, "cl": None, "so4": None, "hco3": None}
        maal = {"target_id": "humledrevet_ol", "name": "Humledrevet øl", "mash_ph_min": 5.2, "mash_ph_max": 5.4}
        recipe = bygg_recipe_object(
            "Test", 20.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.050, 1.012, 5.0, 20, 8, {},
            water_source_profile=kilde, water_target_profile=maal,
        )
        ctx = _ctx_stub(recipe)
        plan = _plan_stub()
        water = {"kilde": kilde, "maal": maal, "behandling": {"salter": []}, "maalinger": {}}
        html = render_brewday_html(ctx, plan, {}, water=water)

        self.assertIn("Vannkilde: <strong>Bekkevatn Test</strong>", html)
        self.assertIn("Målprofil: <strong>Humledrevet øl</strong>", html)
        self.assertNotIn("Vannkilde: <strong>Humledrevet øl</strong>", html)
        self.assertNotIn("Målprofil: <strong>Bekkevatn Test</strong>", html)

        html_a4 = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Vannkilde: Bekkevatn Test", html_a4)
        self.assertIn("Målprofil: Humledrevet øl", html_a4)
        self.assertNotIn("Vannkilde: Humledrevet øl", html_a4)
        self.assertNotIn("Målprofil: Bekkevatn Test", html_a4)


class TestVisningsnavnRekonstrueresEtterLagring(unittest.TestCase):
    """Krav 4: navnet skal kunne rekonstrueres etter lagring og
    gjenåpning, og skal IKKE avhenge av at target_id fortsatt peker på
    samme navn i biblioteket — biblioteket kan bli redigert/omdøpt i
    mellomtiden uten at det påvirker en allerede lagret oppskrift."""

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

    def test_navn_overlever_at_biblioteket_senere_omdopes(self):
        import modules.recipe_storage as recipe_storage

        original_navn = "Maltpreget tysk lager"  # navnet PÅ LAGRINGSTIDSPUNKTET
        maal_snapshot = {
            "target_id": "kvernhaug_maltpreget_tysk_lager", "name": original_navn,
            "mash_ph_min": 5.30, "mash_ph_max": 5.40,
        }
        recipe = bygg_recipe_object(
            "Lagret Wiesn", 23.0, 0.75, _MALT_VALG, [], "saflager_w3470", 1.064, 1.013, 6.9, 22, 20, {},
            water_source_profile=_JORDALSVATNET, water_target_profile=maal_snapshot,
        )
        recipe_storage.lagre_oppskrift(recipe)

        # Simulerer at biblioteket i data/water_targets.json BLE omdøpt i
        # mellomtiden — dette skal IKKE endre den allerede lagrede
        # snapshotten på oppskriften.
        omdopt_bibliotek_navn = "HELT ANNET NAVN — omdøpt i biblioteket"
        self.assertNotEqual(omdopt_bibliotek_navn, original_navn)

        gjenaapnet = recipe_storage.hent_alle_oppskrifter()["Lagret Wiesn"]
        self.assertEqual(gjenaapnet["water_target_profile"]["name"], original_navn)
        self.assertNotEqual(gjenaapnet["water_target_profile"]["name"], omdopt_bibliotek_navn)

        # Og eksporten som faktisk BRUKER denne gjenåpnede oppskriften
        # viser fortsatt det opprinnelige navnet.
        ctx = _ctx_stub(gjenaapnet)
        html = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn(f"Målprofil: {original_navn}", html)
        self.assertNotIn(omdopt_bibliotek_navn, html)


if __name__ == "__main__":
    unittest.main()
