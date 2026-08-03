"""
Enhetstester for modules/smart_shopping_list.py — Smart Handleliste V1 sin
rene Python-beregningsmodul (ingen Streamlit, ingen UI).

Isolasjon: alle tester som bruker Pantry setter KVERNHAUG_PANTRY_DIR til en
tempfile.TemporaryDirectory() — samme mønster som tests/test_pantry.py.
Ingen test her leser eller skriver den ekte data/pantry.json eller
data/humle_lager.json.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import os
import tempfile
import unittest

import modules.pantry as pantry
import modules.smart_shopping_list as ssl
import modules.malt_packaging as malt_packaging


class _ShoppingListTestCase(unittest.TestCase):
    def setUp(self):
        self._gammel_env = os.environ.get("KVERNHAUG_PANTRY_DIR")
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["KVERNHAUG_PANTRY_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_PANTRY_DIR", None)
        else:
            os.environ["KVERNHAUG_PANTRY_DIR"] = self._gammel_env
        self._tmpdir.cleanup()


def _oppskrift(malts=None, hops=None, yeast=None):
    return {"malts": malts or [], "hops": hops or [], "yeast": yeast}


def _rad(handleliste, ingredient_type, ingredient_id):
    return next(r for r in handleliste if r["ingredient_type"] == ingredient_type and r["ingredient_id"] == ingredient_id)


_MALT_DB = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "butikk_match": {
    "olbrygging": {"pris": 40.0, "url": "https://example.test/pilsner"},
}}}
_HUMLE_DB = {"citra": {"display_name": "Citra", "butikk_match": {
    "olbrygging": {"pris": 90.0, "pakke_gram": 100.0, "url": "https://example.test/citra"},
}}}
_GJAER_DB = {"safale_us_05": {"display_name": "US-05", "butikk_match": {
    "olbrygging": {"pris": 55.0, "url": "https://example.test/us05"},
}}}


class Test1FullLagerGirTomHandleliste(_ShoppingListTestCase):
    def test_nok_lager_gir_ingen_kjop_rader(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 10.0, "kg"))
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 200.0, "g"))
        p["items"].append(pantry.opprett_pantry_item("gjaer", "safale_us_05", "US-05", 2.0, "pakke"))
        recipe = _oppskrift(
            malts=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            hops=[{"id": "citra", "gram": 20.0, "tid": 60}],
        )
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        sammendrag = ssl.oppsummer_handleliste(handleliste)
        self.assertEqual(sammendrag["antall_ma_kjopes"], 0)
        for rad in handleliste:
            if rad["ingredient_type"] != "gjaer":  # gjær er alltid ukjent_match i V1 uten pakkeantall
                self.assertEqual(rad["status"], "nok")


class Test2DelvisMaltbeholdningGirKorrektFaktiskMangel(_ShoppingListTestCase):
    def test_faktisk_mangel(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB)
        rad = _rad(handleliste, "malt", "weyermann_pilsner")
        self.assertEqual(rad["required_base"], 4230.0)
        self.assertEqual(rad["available_base"], 1000.0)
        self.assertEqual(rad["missing_base"], 3230.0)
        self.assertEqual(rad["status"], "kjop")


class Test3MaltKjopsforslagAvrundesTilPakningsstorrelse(_ShoppingListTestCase):
    def test_uten_registrert_pakningsstorrelse_foreslas_eksakt_mengde(self):
        # Dagens virkelighet: malt har ingen pakke_kg i masterdata ->
        # eksakt foreslått mengde, ikke avrundet.
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB)
        rad = _rad(handleliste, "malt", "weyermann_pilsner")
        self.assertFalse(rad["package_size_known"])
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 3.23, places=2)
        self.assertEqual(rad["purchase_unit"], "kg")

    def test_med_registrert_pakningsstorrelse_avrundes_kjopsforslaget(self):
        malt_db_med_pakke = {"weyermann_pilsner": {"display_name": "Pilsner", "butikk_match": {
            "olbrygging": {"pris": 40.0, "pakke_kg": 1.0, "url": "x"},
        }}}
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        handleliste = ssl.beregn_handleliste(recipe, p, malt_db_med_pakke)
        rad = _rad(handleliste, "malt", "weyermann_pilsner")

        self.assertTrue(rad["package_size_known"])
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 4.0, places=2)
        self.assertEqual(rad["missing_base"], 3230.0, "Selve mangelen skal IKKE avrundes")
        self.assertAlmostEqual(rad["expected_remainder_base"], 770.0, places=1)


class Test4HumlemangelBeregnesFraPantry(_ShoppingListTestCase):
    def test_humlemangel(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 30.0, "g"))
        recipe = _oppskrift(hops=[{"id": "citra", "gram": 88.0, "tid": 60}])
        handleliste = ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB)
        rad = _rad(handleliste, "humle", "citra")
        self.assertEqual(rad["required_base"], 88.0)
        self.assertEqual(rad["available_base"], 30.0)
        self.assertEqual(rad["missing_base"], 58.0)
        # pakke_gram=100 -> avrundes opp til 100g
        self.assertEqual(rad["suggested_purchase_quantity"], 100.0)
        self.assertTrue(rad["package_size_known"])
        self.assertEqual(rad["status"], "kjop")


class Test5GjaerRundesOppTilHelePakker(_ShoppingListTestCase):
    def test_gjaer_avrunding(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "safale_us_05", "US-05", 0.5, "pakke"))
        recipe = _oppskrift(yeast="safale_us_05")
        recipe["gjaer_pakker_anbefalt"] = 2.3
        handleliste = ssl.beregn_handleliste(recipe, p, gjaer_db=_GJAER_DB)
        rad = _rad(handleliste, "gjaer", "safale_us_05")
        self.assertAlmostEqual(rad["missing_base"], 1.8, places=6)  # faktisk mangel, ikke avrundet
        self.assertEqual(rad["suggested_purchase_quantity"], 2.0)  # opp til hele pakker
        self.assertEqual(rad["purchase_unit"], "pakke")


class Test6FaktiskMangelOgForeslattKjopHoldesAdskilt(_ShoppingListTestCase):
    def test_to_separate_felt(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 0.0, "g"))
        recipe = _oppskrift(hops=[{"id": "citra", "gram": 45.0, "tid": 60}])
        handleliste = ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB)
        rad = _rad(handleliste, "humle", "citra")
        self.assertNotEqual(rad["missing_base"], rad["suggested_purchase_quantity"],
                             "45g mangel skal avrundes til 100g kjøp -- de skal ikke være like")
        self.assertEqual(rad["missing_base"], 45.0)
        self.assertEqual(rad["suggested_purchase_quantity"], 100.0)


class Test7ForventetRestBeregnesKorrekt(_ShoppingListTestCase):
    def test_forventet_rest(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 30.0, "g"))
        recipe = _oppskrift(hops=[{"id": "citra", "gram": 88.0, "tid": 60}])
        handleliste = ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB)
        rad = _rad(handleliste, "humle", "citra")
        # 30 (på lager) + 100 (kjøp) - 88 (trenger) = 42
        self.assertEqual(rad["expected_remainder_base"], 42.0)


class Test8FlerePantryposterSummeres(_ShoppingListTestCase):
    def test_flere_malt_lots_summeres(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg", lot_number="A"))
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 2.0, "kg", lot_number="B"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB)
        rad = _rad(handleliste, "malt", "weyermann_pilsner")
        self.assertEqual(rad["available_base"], 3000.0)
        self.assertEqual(rad["missing_base"], 2000.0)


class Test9UkjentIdGirUkjentMatch(_ShoppingListTestCase):
    def test_manglende_id(self):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"navn": "Uidentifisert malt", "mengde": 2.0}])
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB)
        rad = handleliste[0]
        self.assertEqual(rad["status"], "ukjent_match")
        self.assertIsNone(rad["suggested_purchase_quantity"])
        self.assertIsNone(rad["purchase_unit"])
        self.assertEqual(rad["supplier_options"], [])

    def test_gjaer_uten_pakkeantall_gir_ukjent_match(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "safale_us_05", "US-05", 1.0, "pakke"))
        recipe = _oppskrift(yeast="safale_us_05")  # ingen gjaer_pakker_anbefalt
        handleliste = ssl.beregn_handleliste(recipe, p, gjaer_db=_GJAER_DB)
        rad = _rad(handleliste, "gjaer", "safale_us_05")
        self.assertEqual(rad["status"], "ukjent_match")


class Test10OppskriftenMuteresIkke(_ShoppingListTestCase):
    def test_recipe_uendret(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(
            malts=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            hops=[{"id": "citra", "gram": 20.0, "tid": 60}],
            yeast="safale_us_05",
        )
        original = json.loads(json.dumps(recipe))
        ssl.beregn_handleliste(recipe, p, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertEqual(recipe, original)


class Test11PantryMuteresIkke(_ShoppingListTestCase):
    def test_pantry_uendret(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        original = copy.deepcopy(p)
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        ssl.beregn_handleliste(recipe, p, _MALT_DB)
        self.assertEqual(p, original)


class Test12SkaleringOppdatererHandlelistenLive(_ShoppingListTestCase):
    def test_skalert_oppskrift_gir_nytt_behov(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        original = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        skalert = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 10.0}])

        rad_original = _rad(ssl.beregn_handleliste(original, p, _MALT_DB), "malt", "weyermann_pilsner")
        rad_skalert = _rad(ssl.beregn_handleliste(skalert, p, _MALT_DB), "malt", "weyermann_pilsner")

        self.assertEqual(rad_original["status"], "nok")
        self.assertEqual(rad_skalert["status"], "kjop")
        self.assertEqual(rad_skalert["required_base"], 10000.0)


class Test13GammeltHumlelagerPaavirkerIkkeResultatet(_ShoppingListTestCase):
    def test_smart_shopping_list_importerer_ikke_humle_lager(self):
        # Sjekker selve import-SETNINGENE (AST), ikke modulens forklarende
        # docstring (som bevisst NEVNER data/humle_lager.json i løpende
        # tekst for å forklare hvorfor den ikke brukes).
        import ast
        import inspect
        tre = ast.parse(inspect.getsource(ssl))
        importerte_moduler = [
            node.module for node in ast.walk(tre) if isinstance(node, ast.ImportFrom)
        ] + [
            alias.name for node in ast.walk(tre) if isinstance(node, ast.Import) for alias in node.names
        ]
        self.assertFalse(
            any(m and "humle_lager" in m for m in importerte_moduler),
            f"Fant en import av humle_lager: {importerte_moduler}",
        )
        self.assertFalse(hasattr(ssl, "les_lager"), "smart_shopping_list skal ikke ha importert humle_lager sine funksjoner")

    def test_endring_i_gammelt_lager_paavirker_ikke_resultatet(self):
        from unittest.mock import patch
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 30.0, "g"))
        recipe = _oppskrift(hops=[{"id": "citra", "gram": 88.0, "tid": 60}])

        uten_patch = ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB)
        with patch("modules.humle_lager.les_lager", return_value={"citra": 100000.0}):
            med_patch = ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB)

        self.assertEqual(uten_patch, med_patch, "Smart Handleliste skal være helt upåvirket av humle_lager-data")


class Test14PrisManglerHaandteresUtenKrasj(_ShoppingListTestCase):
    def test_tom_butikk_match_gir_fallback_uten_krasj(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "ukjent_malt", "Ukjent", 0.0, "kg"))
        p["items"].append(pantry.opprett_pantry_item("humle", "ukjent_humle", "Ukjent", 0.0, "g"))
        p["items"].append(pantry.opprett_pantry_item("gjaer", "ukjent_gjaer", "Ukjent", 0.0, "pakke"))
        recipe = _oppskrift(
            malts=[{"id": "ukjent_malt", "mengde": 1.0}],
            hops=[{"id": "ukjent_humle", "gram": 20.0, "tid": 60}],
            yeast="ukjent_gjaer",
        )
        recipe["gjaer_pakker_anbefalt"] = 1.0
        handleliste = ssl.beregn_handleliste(recipe, p, malt_db={}, humle_db={}, gjaer_db={})

        malt_rad = _rad(handleliste, "malt", "ukjent_malt")
        humle_rad = _rad(handleliste, "humle", "ukjent_humle")
        gjaer_rad = _rad(handleliste, "gjaer", "ukjent_gjaer")

        self.assertTrue(malt_rad["cost_is_estimate"])
        self.assertTrue(humle_rad["cost_is_estimate"])
        self.assertTrue(gjaer_rad["cost_is_estimate"])
        self.assertGreater(malt_rad["estimated_cost"], 0)
        self.assertGreater(humle_rad["estimated_cost"], 0)
        self.assertGreater(gjaer_rad["estimated_cost"], 0)


class TestOppsummerHandleliste(_ShoppingListTestCase):
    def test_sammendrag_teller_riktig(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(
            malts=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            hops=[{"id": "citra", "gram": 20.0, "tid": 60}],
        )
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB, _HUMLE_DB)
        sammendrag = ssl.oppsummer_handleliste(handleliste)
        self.assertEqual(sammendrag["antall_ma_kjopes"], 2)  # malt (mangel) + humle (0 på lager)
        self.assertGreater(sammendrag["estimert_totalkostnad"], 0)

    def test_ukjent_match_telles_separat_fra_kjop(self):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"navn": "Uidentifisert", "mengde": 1.0}])
        handleliste = ssl.beregn_handleliste(recipe, p, _MALT_DB)
        sammendrag = ssl.oppsummer_handleliste(handleliste)
        self.assertEqual(sammendrag["antall_usikre_matcher"], 1)
        self.assertEqual(sammendrag["antall_ma_kjopes"], 0)


class TestEnhetskontrakt(_ShoppingListTestCase):
    """Krav 1 (Kvernhaug-oppryddingen 2026-07-27): *_base-felt er ALLTID i
    Pantry sin basisenhet (gram for malt/humle, pakker for gjær),
    suggested_purchase_quantity er ALLTID i purchase_unit (en
    menneskevennlig innkjøpsenhet: kg for malt, g for humle, pakker for
    gjær) — de to skal ALDRI blandes eller forveksles."""

    def test_malt_eksempelet_fra_spesifikasjonen(self):
        # Det eksakte tallgrunnlaget fra oppgaven: 3230 g reell mangel,
        # 1 kg-pakning -> 4.0 kg foreslått kjøp (IKKE 4000).
        malt_db_med_pakke = {"weyermann_pilsner": {"display_name": "Pilsner", "butikk_match": {
            "olbrygging": {"pris": 40.0, "pakke_kg": 1.0, "url": "x"},
        }}}
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        rad = _rad(ssl.beregn_handleliste(recipe, p, malt_db_med_pakke), "malt", "weyermann_pilsner")

        self.assertEqual(rad["required_base"], 4230.0)
        self.assertEqual(rad["available_base"], 1000.0)
        self.assertEqual(rad["missing_base"], 3230.0)
        self.assertEqual(rad["base_unit"], "g")

        self.assertEqual(rad["purchase_unit"], "kg")
        self.assertEqual(rad["suggested_purchase_quantity"], 4.0)
        # Den eksplisitte forvekslingen kravet advarer mot: 4 kg skal ALDRI
        # representeres som suggested_purchase_quantity=4000 (det ville
        # vært 1000x for mye malt, siden purchase_unit="kg").
        self.assertNotEqual(
            rad["suggested_purchase_quantity"], 4000,
            "suggested_purchase_quantity=4000 med purchase_unit='kg' ville betydd 4000 kg, ikke 4 kg",
        )
        self.assertAlmostEqual(rad["expected_remainder_base"], 770.0, places=2)

    def test_missing_base_er_alltid_i_gram_uavhengig_av_kjopsenhet(self):
        # missing_base skal ALDRI konverteres til purchase_unit -- den er
        # og blir i base_unit (gram), uansett hva suggested_purchase_quantity
        # er uttrykt i.
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        rad = _rad(ssl.beregn_handleliste(recipe, p, _MALT_DB), "malt", "weyermann_pilsner")
        self.assertEqual(rad["base_unit"], "g")
        self.assertEqual(rad["missing_base"], 3230.0, "missing_base skal være i gram, ikke i kg (3.23)")

    def test_gjaer_purchase_unit_er_pakke_ikke_g_eller_kg(self):
        p = pantry.last_pantry()
        recipe = _oppskrift(yeast="safale_us_05")
        recipe["gjaer_pakker_anbefalt"] = 2.0
        rad = _rad(ssl.beregn_handleliste(recipe, p, gjaer_db=_GJAER_DB), "gjaer", "safale_us_05")
        self.assertEqual(rad["base_unit"], "pakke")
        self.assertEqual(rad["purchase_unit"], "pakke")
        self.assertEqual(rad["suggested_purchase_quantity"], 2.0)

    def test_humle_base_og_purchase_unit_er_begge_gram_men_uavhengig_avrundet(self):
        # Humle er spesialtilfellet der base_unit OG purchase_unit begge er
        # "g" -- men suggested_purchase_quantity er likevel IKKE det samme
        # tallet som missing_base når det finnes en pakningsstørrelse å
        # runde opp til.
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "citra", "Citra", 0.0, "g"))
        recipe = _oppskrift(hops=[{"id": "citra", "gram": 45.0, "tid": 60}])
        rad = _rad(ssl.beregn_handleliste(recipe, p, humle_db=_HUMLE_DB), "humle", "citra")
        self.assertEqual(rad["base_unit"], "g")
        self.assertEqual(rad["purchase_unit"], "g")
        self.assertEqual(rad["missing_base"], 45.0)
        self.assertEqual(rad["suggested_purchase_quantity"], 100.0, "Skal rundes opp til pakke_gram, ikke være lik missing_base")


class TestKnappBevaresSomAdvisory(_ShoppingListTestCase):
    """Krav 2: Pantry sitt "knapp"-signal skal IKKE kastes bort når det
    kollapses til handlelistens "nok"-status."""

    def _knapp_scenario(self):
        # 4.23 kg nødvendig, 5% margin -> trygt er 4.4415 kg. 4.25 kg
        # dekker behovet, men ikke margin-grensen -> Pantry-status "knapp".
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 4.25, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        return _rad(ssl.beregn_handleliste(recipe, p, _MALT_DB), "malt", "weyermann_pilsner")

    def test_knapp_lager_gir_ingen_kjopslinje(self):
        rad = self._knapp_scenario()
        self.assertEqual(rad["status"], "nok", "Knapp skal IKKE kreve kjøp")
        self.assertEqual(rad["missing_base"], 0.0)
        self.assertEqual(rad["suggested_purchase_quantity"], 0.0)

    def test_knapp_informasjon_bevares(self):
        rad = self._knapp_scenario()
        self.assertEqual(rad["pantry_status"], "knapp")
        self.assertIsNotNone(rad["advisory"])
        self.assertIn("sikkerhetsmargin", rad["advisory"].lower())

    def test_ren_nok_har_ingen_advisory(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 10.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        rad = _rad(ssl.beregn_handleliste(recipe, p, _MALT_DB), "malt", "weyermann_pilsner")
        self.assertEqual(rad["pantry_status"], "nok")
        self.assertIsNone(rad["advisory"])

    def test_kostnad_pavirkes_ikke_av_knapp(self):
        rad = self._knapp_scenario()
        self.assertEqual(rad["estimated_cost"], 0.0)
        self.assertFalse(rad["cost_is_estimate"])

    def test_knapp_telles_ikke_blant_ma_kjopes_i_sammendrag(self):
        rad = self._knapp_scenario()
        sammendrag = ssl.oppsummer_handleliste([rad])
        self.assertEqual(sammendrag["antall_ma_kjopes"], 0)
        self.assertEqual(sammendrag["estimert_totalkostnad"], 0.0)

    def test_mangler_og_ukjent_match_har_egen_pantry_status(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 4.23}])
        mangler_rad = _rad(ssl.beregn_handleliste(recipe, p, _MALT_DB), "malt", "weyermann_pilsner")
        self.assertEqual(mangler_rad["status"], "kjop")
        self.assertEqual(mangler_rad["pantry_status"], "mangler")
        self.assertIsNone(mangler_rad["advisory"])

        ukjent_recipe = _oppskrift(malts=[{"navn": "Uidentifisert", "mengde": 1.0}])
        ukjent_rad = ssl.beregn_handleliste(ukjent_recipe, p, _MALT_DB)[0]
        self.assertEqual(ukjent_rad["pantry_status"], "ukjent_match")
        self.assertIsNone(ukjent_rad["advisory"])


_WIESN_GJAER_DB = {
    "saflager_w3470": {"display_name": "SafLager W-34/70", "gjaertype": "Lager", "butikk_match": {
        "olbrygging": {"pris": 45.0, "url": "https://example.test/w3470"},
    }},
    "lalvin_ec1118": {"display_name": "Lalvin EC-1118", "gjaertype": "Spesialgjær"},
}


def _wiesn_oppskrift():
    """Samme sammensetning som tests/fixtures/recipes/wiesn_marzen_1872.json,
    men med 'stats'/'batch_size' fylt ut slik den ekte, kjørende appen gjør
    (se tests/test_pantry.py sin _wiesn_oppskrift() for hvordan OG-tallet
    1.0799906590000001 er utledet: modules.calculations.beregn_og for denne
    malt-sammensetningen ved 20 L/75% effektivitet)."""
    return {
        "malts": [
            {"id": "weyermann_munich_1", "mengde": 0.7},
            {"id": "munich_ii", "mengde": 4.6},
            {"id": "vienna", "mengde": 1.8},
        ],
        "hops": [{"id": "tettnang", "gram": 88.0, "tid": 60}],
        "yeast": "saflager_w3470",
        "batch_size": 20.0,
        "stats": {"og": 1.0799906590000001},
    }


class TestGjaerPakkeantallFraOppskriftBrukesIHandlelisten(_ShoppingListTestCase):
    """Regresjon 2026-07-27: Smart Handleliste viste 'Kan ikke matches
    sikkert' for gjær i den ekte Wiesn-oppskriften, selv om bryggedagsarket
    allerede hadde et kjent anbefalt pakkeantall (3 pakker W-34/70) for
    nøyaktig samme oppskrift. modules.pantry.beregn_mangler() beregner nå
    dette selv (se modules/pantry.py::_beregn_gjaer_pakker_anbefalt), og
    Smart Handleliste arver det uendret siden den kun bygger videre på
    beregn_mangler()."""

    def test_ingen_gjaer_pa_lager_gir_eksakt_kjopsforslag(self):
        p = pantry.last_pantry()  # tomt lager -- ingen W-34/70 registrert
        handleliste = ssl.beregn_handleliste(_wiesn_oppskrift(), p, gjaer_db=_WIESN_GJAER_DB)
        rad = _rad(handleliste, "gjaer", "saflager_w3470")

        self.assertEqual(rad["required_base"], 3.0)
        self.assertEqual(rad["available_base"], 0.0)
        self.assertEqual(rad["missing_base"], 3.0)
        self.assertEqual(rad["suggested_purchase_quantity"], 3.0)
        self.assertEqual(rad["purchase_unit"], "pakke")
        self.assertEqual(rad["status"], "kjop")

    def test_ec1118_pa_lager_dekker_ikke_w3470_behovet(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "lalvin_ec1118", "Lalvin EC-1118", 10.0, "pakke"))
        rad = _rad(ssl.beregn_handleliste(_wiesn_oppskrift(), p, gjaer_db=_WIESN_GJAER_DB), "gjaer", "saflager_w3470")
        self.assertEqual(rad["available_base"], 0.0, "EC-1118 skal ikke matches mot W-34/70 -- ulik stabil ingredient_id")
        self.assertEqual(rad["status"], "kjop")
        self.assertEqual(rad["missing_base"], 3.0)


_FIXTURES_MAPPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "recipes")


def _last_wiesn_23l_fixture():
    """Den ekte, committede, sanitiserte 23 L-fixturen (se
    tests/fixtures/recipes/wiesn_marzen_1872_23l_batch.json) -- IKKE den
    private, ekte oppskriftsfilen i recipes/. Munich I/II/Vienna sine
    mengder her (0.644/4.232/1.656 kg) er nøyaktig de tallene oppgaven
    bruker som "mangler" når Pantry er tom (644/4232/1656 g)."""
    with open(os.path.join(_FIXTURES_MAPPE, "wiesn_marzen_1872_23l_batch.json"), encoding="utf-8") as f:
        return json.load(f)


# Malt-varianter oppgaven selv beskriver (100 g og 1 kg, "hel" -- Munich
# I/II og Vienna er i den ekte masterdatabasen registrert med
# knust_tilgjengelig=false, altså kun tilgjengelig hel). Dette er en
# TEST-LOKAL, syntetisk databasekopi -- ingen ekte masterdata endres for
# denne testen.
_WIESN_MALT_DB_MED_VARIANTER = {
    m_id: {
        "display_name": m_id,
        "butikk_match": {
            "olbrygging": {
                "varianter": [
                    {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 25.0},
                    {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
                ],
            },
        },
    }
    for m_id in ("weyermann_munich_1", "munich_ii", "vienna")
}

_WIESN_HUMLE_DB = {
    "tettnang": {"display_name": "Tettnang", "alfa_typisk": 3.1, "butikk_match": {
        "olbrygging": {"pris": 79.0, "pakke_gram": 100.0, "url": "https://example.test/tettnang"},
    }},
}


class TestMaltPakningsforslagWiesn23L(_ShoppingListTestCase):
    """Krav 7 + 8: med Munich I/II/Vienna sine ekte mangelbeløp fra den
    committede 23 L-fixturen (644/4232/1656 g) og kun 100 g/1 kg
    tilgjengelig, skal minst-overkjøp-kandidaten være nøyaktig 700 g /
    4300 g / 1700 g -- og Smart Handleliste skal videreformidle dette som
    et kg-kjøpsforslag pluss en full pakningsforslag-struktur for UI-et."""

    def _handleliste(self, malt_prioritet=malt_packaging.PRIORITET_MINST_OVERKJOP):
        p = pantry.last_pantry()  # tomt lager -- hele oppskriftens behov mangler
        recipe = _last_wiesn_23l_fixture()
        return ssl.beregn_handleliste(
            recipe, p, malt_db=_WIESN_MALT_DB_MED_VARIANTER, humle_db=_WIESN_HUMLE_DB,
            malt_prioritet=malt_prioritet,
        )

    def test_munich_i_missing_base_er_644g_og_kjop_er_700g(self):
        rad = _rad(self._handleliste(), "malt", "weyermann_munich_1")
        self.assertEqual(rad["missing_base"], 644.0)
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 0.7, places=6)
        self.assertEqual(rad["purchase_unit"], "kg")

    def test_munich_ii_missing_base_er_4232g_og_kjop_er_4300g(self):
        rad = _rad(self._handleliste(), "malt", "munich_ii")
        self.assertEqual(rad["missing_base"], 4232.0)
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 4.3, places=6)

    def test_vienna_missing_base_er_1656g_og_kjop_er_1700g(self):
        rad = _rad(self._handleliste(), "malt", "vienna")
        self.assertEqual(rad["missing_base"], 1656.0)
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 1.7, places=6)

    def test_malt_pakningsforslag_struktur_er_med_i_raden(self):
        rad = _rad(self._handleliste(), "malt", "munich_ii")
        forslag = rad["malt_pakningsforslag"]
        self.assertIsNotNone(forslag)
        anbefalt = forslag["anbefalt_kombinasjon"]
        pakninger = {p["pakningsstorrelse_gram"]: p["antall"] for p in anbefalt["antall_pakninger"]}
        self.assertEqual(pakninger, {1000: 4, 100: 3})
        self.assertGreater(anbefalt["total_pris"], 0)
        self.assertEqual(rad["estimated_cost"], anbefalt["total_pris"])

    def test_handlelisten_leser_pris_og_mengde_fra_kjopsresultatet_ikke_pa_nytt(self):
        # Steg B: suggested_purchase_quantity/estimated_cost skal komme fra
        # SAMME kjopsresultat-objekt malt_packaging.py produserer -- ikke en
        # uavhengig nyberegning i smart_shopping_list.py.
        rad = _rad(self._handleliste(), "malt", "munich_ii")
        kjopsresultat = rad["malt_pakningsforslag"]["kjopsresultat"]
        self.assertEqual(rad["estimated_cost"], kjopsresultat["pris"])
        self.assertAlmostEqual(rad["suggested_purchase_quantity"] * 1000.0, kjopsresultat["mottatt_mengde"], places=6)

    def test_faktisk_mangel_holdes_adskilt_fra_kjopsmengde_for_alle_tre_malt(self):
        handleliste = self._handleliste()
        for m_id, forventet_mangel in (
            ("weyermann_munich_1", 644.0), ("munich_ii", 4232.0), ("vienna", 1656.0),
        ):
            rad = _rad(handleliste, "malt", m_id)
            self.assertEqual(rad["missing_base"], forventet_mangel)
            self.assertNotEqual(rad["missing_base"], rad["suggested_purchase_quantity"] * 1000.0)

    def test_billigst_prioritet_kan_gi_annet_forslag_enn_minst_overkjop(self):
        # Munich II: 5000 g (5x1kg) er billigere totalt enn 4300 g
        # (4x1kg+3x100g) med disse variantprisene (se
        # tests/test_malt_packaging.py sitt tilsvarende regnestykke) --
        # "billigst" skal derfor kunne gi et ANNET forslag enn
        # "minst_overkjop" for nøyaktig samme oppskrift/lager.
        minst_overkjop = _rad(self._handleliste(malt_prioritet=malt_packaging.PRIORITET_MINST_OVERKJOP),
                               "malt", "munich_ii")
        billigst = _rad(self._handleliste(malt_prioritet=malt_packaging.PRIORITET_BILLIGST),
                         "malt", "munich_ii")
        self.assertNotEqual(minst_overkjop["suggested_purchase_quantity"], billigst["suggested_purchase_quantity"])
        self.assertAlmostEqual(billigst["suggested_purchase_quantity"], 5.0, places=6)

    def test_recipe_og_pantry_muteres_ikke(self):
        p = pantry.last_pantry()
        recipe = _last_wiesn_23l_fixture()
        recipe_original = json.loads(json.dumps(recipe))
        pantry_original = copy.deepcopy(p)
        ssl.beregn_handleliste(recipe, p, malt_db=_WIESN_MALT_DB_MED_VARIANTER, humle_db=_WIESN_HUMLE_DB)
        self.assertEqual(recipe, recipe_original)
        self.assertEqual(p, pantry_original)


class TestSteg_CRestberegningFraKjopsresultat(_ShoppingListTestCase):
    """Steg C: expected_remainder_base for pakket-malt skal alltid være
    identisk med max(0, available_base + kjopsresultat["mottatt_mengde"]
    - required_base) -- aldri påvirket av pris eller av HVORDAN
    mottatt_mengde ble sammensatt (bestilling-strukturen)."""

    def _handleliste_for(self, malt_db, missing_kg, tilgjengelig_kg=0.0):
        p = pantry.last_pantry()
        if tilgjengelig_kg:
            p["items"].append(pantry.opprett_pantry_item("malt", "test_malt", "Test Malt", tilgjengelig_kg, "kg"))
        recipe = _oppskrift(malts=[{"id": "test_malt", "mengde": missing_kg + tilgjengelig_kg}])
        return ssl.beregn_handleliste(recipe, p, malt_db=malt_db)

    def test_1_behov_123kg_mottatt_2kg_gir_rest_077kg_pa_tomt_lager(self):
        malt_db = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 40.0}],
        }}}}
        handleliste = self._handleliste_for(malt_db, missing_kg=1.23)
        rad = _rad(handleliste, "malt", "test_malt")
        kjopsresultat = rad["malt_pakningsforslag"]["kjopsresultat"]

        self.assertEqual(rad["missing_base"], 1230.0)
        self.assertEqual(kjopsresultat["mottatt_mengde"], 2000.0)
        self.assertEqual(rad["expected_remainder_base"], 770.0)  # 0 + 2000 - 1230

    def test_2_eksisterende_pantry_bruker_available_pluss_mottatt_minus_required(self):
        malt_db = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 40.0}],
        }}}}
        # 300 g på lager, oppskrift trenger 1800 g totalt -> mangel 1500 g
        # -> pakkeforslag runder opp til 2 x 1000 g = 2000 g mottatt.
        handleliste = self._handleliste_for(malt_db, missing_kg=1.5, tilgjengelig_kg=0.3)
        rad = _rad(handleliste, "malt", "test_malt")

        self.assertEqual(rad["available_base"], 300.0)
        self.assertEqual(rad["missing_base"], 1500.0)
        self.assertEqual(rad["malt_pakningsforslag"]["kjopsresultat"]["mottatt_mengde"], 2000.0)
        self.assertEqual(rad["expected_remainder_base"], 500.0)  # 300 + 2000 - 1800

    def test_3_prisendring_pavirker_ikke_restberegningen(self):
        billig = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 10.0}],
        }}}}
        dyr = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 90.0}],
        }}}}
        rad_billig = _rad(self._handleliste_for(billig, missing_kg=1.23), "malt", "test_malt")
        rad_dyr = _rad(self._handleliste_for(dyr, missing_kg=1.23), "malt", "test_malt")

        self.assertNotEqual(rad_billig["estimated_cost"], rad_dyr["estimated_cost"])
        self.assertEqual(rad_billig["expected_remainder_base"], rad_dyr["expected_remainder_base"])

    def test_4_ulik_bestillingsstruktur_samme_mottatt_mengde_gir_samme_rest(self):
        # To helt ulike pakningsoppsett som begge lander på 2000 g totalt
        # for et behov på 1230 g -- ett via 2x1000g, ett via 1x2000g.
        to_stk_1kg = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 40.0}],
        }}}}
        en_stk_2kg = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {
            "varianter": [{"pakningsstorrelse_gram": 2000, "malttype": "hel", "pris": 75.0}],
        }}}}

        rad_a = _rad(self._handleliste_for(to_stk_1kg, missing_kg=1.23), "malt", "test_malt")
        rad_b = _rad(self._handleliste_for(en_stk_2kg, missing_kg=1.23), "malt", "test_malt")

        self.assertNotEqual(
            rad_a["malt_pakningsforslag"]["kjopsresultat"]["bestilling"],
            rad_b["malt_pakningsforslag"]["kjopsresultat"]["bestilling"],
        )
        self.assertEqual(
            rad_a["malt_pakningsforslag"]["kjopsresultat"]["mottatt_mengde"],
            rad_b["malt_pakningsforslag"]["kjopsresultat"]["mottatt_mengde"],
        )
        self.assertEqual(rad_a["expected_remainder_base"], rad_b["expected_remainder_base"])


class TestMaltformStyrerKombinasjonsvalg(_ShoppingListTestCase):
    """Krav 6: maltform-innstillingen skal styre hvilken maltype et
    kjøpsforslag hentes fra, og en enkelt kombinasjon skal aldri blande hel
    og knust."""

    _MALT_DB_HEL_OG_KNUST = {
        "weyermann_munich_1": {"display_name": "Munich I", "butikk_match": {"olbrygging": {"varianter": [
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0},
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 7.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 42.0},
        ]}}},
    }

    def _rad_for_maltform(self, maltform):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"id": "weyermann_munich_1", "mengde": 0.644}])
        handleliste = ssl.beregn_handleliste(recipe, p, malt_db=self._MALT_DB_HEL_OG_KNUST, maltform=maltform)
        return _rad(handleliste, "malt", "weyermann_munich_1")

    def test_maltform_knust_gir_knust_forslag(self):
        rad = self._rad_for_maltform(malt_packaging.MALTFORM_KNUST)
        self.assertEqual(rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["malttype"], "knust")

    def test_maltform_hel_gir_hel_forslag(self):
        rad = self._rad_for_maltform(malt_packaging.MALTFORM_HEL)
        self.assertEqual(rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["malttype"], "hel")

    def test_ingen_kombinasjon_blander_hel_og_knust(self):
        rad = self._rad_for_maltform(malt_packaging.MALTFORM_INGEN_PREFERANSE)
        forslag = rad["malt_pakningsforslag"]
        alle = [forslag["anbefalt_kombinasjon"]] + forslag["alternative_kombinasjoner"]
        for kombinasjon in alle:
            self.assertIn(kombinasjon["malttype"], ("hel", "knust"))


class TestTettnangLitenManglAlternativ(_ShoppingListTestCase):
    """Krav 9: oppskriften trenger 81 g Tettnang, Pantry har 80 g -- en
    mangel på kun 1 g. Handlelisten skal fortsatt vise et ORDINÆRT
    kjøpsforslag (rundet til 100 g-pakke), men i TILLEGG et informativt
    alternativ ("bruk det du har") med den faktiske IBU-konsekvensen --
    ALDRI en automatisk oppskriftsendring."""

    def _rad_tettnang(self, tettnang_pa_lager=80.0):
        p = pantry.last_pantry()
        if tettnang_pa_lager:
            p["items"].append(pantry.opprett_pantry_item("humle", "tettnang", "Tettnang", tettnang_pa_lager, "g"))
        recipe = _last_wiesn_23l_fixture()
        handleliste = ssl.beregn_handleliste(recipe, p, humle_db=_WIESN_HUMLE_DB)
        return _rad(handleliste, "humle", "tettnang")

    def test_faktisk_mangel_er_1g(self):
        rad = self._rad_tettnang()
        self.assertEqual(rad["missing_base"], 1.0)
        self.assertEqual(rad["required_base"], 81.0)
        self.assertEqual(rad["available_base"], 80.0)

    def test_ordinaert_kjopsforslag_er_fortsatt_100g_pakke(self):
        rad = self._rad_tettnang()
        self.assertEqual(rad["status"], "kjop")
        self.assertEqual(rad["suggested_purchase_quantity"], 100.0)

    def test_liten_mangel_alternativ_viser_riktig_ibu(self):
        rad = self._rad_tettnang()
        alt = rad["liten_mangel_alternativ"]
        self.assertIsNotNone(alt)
        self.assertEqual(alt["bruk_gram"], 80.0)
        self.assertAlmostEqual(alt["ibu_original"], 22.2, places=1)
        self.assertAlmostEqual(alt["ibu_alternativ"], 21.9, places=1)
        self.assertIn("80", alt["tekst"])
        self.assertIn("21.9", alt["tekst"].replace(",", "."))

    def test_alternativ_forsvinner_ikke_stille_uten_a_vaere_der_naar_mangelen_er_stor(self):
        # Regresjonsvern mot at terskelen ved en feil blir for grov: en
        # STOR mangel (helt tomt lager, 81 g) skal IKKE trigge "liten
        # mangel"-alternativet -- her er hele mengden reell mangel, ikke en
        # ørliten justering.
        rad = self._rad_tettnang(tettnang_pa_lager=0.0)
        self.assertIsNone(rad["liten_mangel_alternativ"])

    def test_ingen_automatisk_oppskriftsendring(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("humle", "tettnang", "Tettnang", 80.0, "g"))
        recipe = _last_wiesn_23l_fixture()
        recipe_original = json.loads(json.dumps(recipe))
        ssl.beregn_handleliste(recipe, p, humle_db=_WIESN_HUMLE_DB)
        self.assertEqual(recipe, recipe_original, "beregn_handleliste skal ALDRI endre den faktiske oppskriften")


_MALT_DB_VESTBRYGG_KNUST = {
    "test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {"varianter": [
        {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0},
        {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 45.0},
    ]}}},
}


class TestStegF3EksaktMalKnustVestbrygg(_ShoppingListTestCase):
    """Steg F3: eksakt_mal_knust=True i beregn_handleliste()/beregn av rad
    for malt. Brukerens eget eksempel: behov 1,23 kg, tomt Pantry -> kjøp
    1×1kg+3×100g (1300 g) hos Vestbrygg (knust), pris 69 kr, men
    mottatt_mengde (og dermed expected_remainder_base) skal reflektere det
    EKSAKTE behovet (1,23 kg), ikke SKU-summen."""

    def _handleliste(self, eksakt_mal_knust, maltform=malt_packaging.MALTFORM_KNUST,
                      butikk="Vestbrygg", malt_db=None, mengde_kg=1.23):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"id": "test_malt", "mengde": mengde_kg}])
        return ssl.beregn_handleliste(
            recipe, p, malt_db=malt_db or _MALT_DB_VESTBRYGG_KNUST, butikk=butikk,
            maltform=maltform, eksakt_mal_knust=eksakt_mal_knust,
        )

    def test_1_eksakt_mal_gir_riktig_pris_mottatt_mengde_og_null_rest(self):
        rad = _rad(self._handleliste(eksakt_mal_knust=True), "malt", "test_malt")
        self.assertEqual(rad["missing_base"], 1230.0)
        self.assertEqual(rad["available_base"], 0.0)
        self.assertEqual(rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["total_gram"], 1300.0)
        self.assertEqual(rad["estimated_cost"], 69.0)
        self.assertAlmostEqual(rad["suggested_purchase_quantity"] * 1000.0, 1230.0, places=6)
        self.assertAlmostEqual(rad["expected_remainder_base"], 0.0, places=6,
                                msg="Tomt Pantry + eksakt mål skal gi nøyaktig 0 g forventet rest")

    def test_2_uten_eksakt_mal_gir_sku_sum_og_70g_rest(self):
        rad = _rad(self._handleliste(eksakt_mal_knust=False), "malt", "test_malt")
        self.assertAlmostEqual(rad["suggested_purchase_quantity"] * 1000.0, 1300.0, places=6)
        self.assertAlmostEqual(rad["expected_remainder_base"], 70.0, places=6)

    def test_3_pris_identisk_med_og_uten_eksakt_mal_men_rest_ulik(self):
        med = _rad(self._handleliste(eksakt_mal_knust=True), "malt", "test_malt")
        uten = _rad(self._handleliste(eksakt_mal_knust=False), "malt", "test_malt")
        self.assertEqual(med["estimated_cost"], uten["estimated_cost"])
        self.assertNotEqual(med["expected_remainder_base"], uten["expected_remainder_base"])

    def test_4_bestilling_beholder_strukturert_sku_liste(self):
        rad = _rad(self._handleliste(eksakt_mal_knust=True), "malt", "test_malt")
        pakninger = rad["malt_pakningsforslag"]["kjopsresultat"]["bestilling"]["pakninger"]
        self.assertEqual(
            {(p["pakningsstorrelse_gram"], p["antall"]) for p in pakninger},
            {(1000.0, 1), (100.0, 3)},
        )

    def test_5_bestilling_uttrykker_eksakt_onsket_mengde_separat(self):
        rad = _rad(self._handleliste(eksakt_mal_knust=True), "malt", "test_malt")
        bestilling = rad["malt_pakningsforslag"]["kjopsresultat"]["bestilling"]
        self.assertEqual(bestilling["eksakt_onsket_mengde_gram"], 1230.0)

    def test_6_hel_malt_far_ikke_eksakt_mal_selv_om_flagget_er_paa(self):
        malt_db_hel = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {"varianter": [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
        ]}}}}
        rad = _rad(self._handleliste(
            eksakt_mal_knust=True, maltform=malt_packaging.MALTFORM_HEL, malt_db=malt_db_hel,
        ), "malt", "test_malt")
        self.assertIsInstance(rad["malt_pakningsforslag"]["kjopsresultat"]["bestilling"], list)
        self.assertAlmostEqual(
            rad["suggested_purchase_quantity"] * 1000.0,
            rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["total_gram"], places=6,
        )

    def test_7_olbrygging_far_ikke_eksakt_mal_selv_om_flagget_er_paa(self):
        malt_db_ol = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"olbrygging": {"varianter": [
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 45.0},
        ]}}}}
        rad = _rad(self._handleliste(
            eksakt_mal_knust=True, butikk="Ølbrygging.no", malt_db=malt_db_ol,
        ), "malt", "test_malt")
        self.assertIsInstance(rad["malt_pakningsforslag"]["kjopsresultat"]["bestilling"], list)
        self.assertAlmostEqual(rad["suggested_purchase_quantity"] * 1000.0, 1300.0, places=6)

    def test_8_humle_og_gjaer_uendret_av_eksakt_mal_knust_flagget(self):
        recipe = _oppskrift(
            malts=[{"id": "test_malt", "mengde": 1.23}],
            hops=[{"id": "citra", "gram": 20.0, "tid": 60}],
            yeast="safale_us_05",
        )
        p = pantry.last_pantry()
        med = ssl.beregn_handleliste(
            recipe, p, malt_db=_MALT_DB_VESTBRYGG_KNUST, humle_db=_HUMLE_DB, gjaer_db=_GJAER_DB,
            butikk="Vestbrygg", maltform=malt_packaging.MALTFORM_KNUST, eksakt_mal_knust=True,
        )
        uten = ssl.beregn_handleliste(
            recipe, p, malt_db=_MALT_DB_VESTBRYGG_KNUST, humle_db=_HUMLE_DB, gjaer_db=_GJAER_DB,
            butikk="Vestbrygg", maltform=malt_packaging.MALTFORM_KNUST, eksakt_mal_knust=False,
        )
        for type in ("humle", "gjaer"):
            rad_med = next(r for r in med if r["ingredient_type"] == type)
            rad_uten = next(r for r in uten if r["ingredient_type"] == type)
            self.assertEqual(rad_med, rad_uten)

    def test_9_utsolgt_variant_brukes_ikke_i_eksakt_mal_handleliste(self):
        malt_db = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {"varianter": [
            {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 1.0, "lagerstatus": "utsolgt"},
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0, "lagerstatus": "pa_lager"},
        ]}}}}
        rad = _rad(self._handleliste(eksakt_mal_knust=True, malt_db=malt_db, mengde_kg=0.3), "malt", "test_malt")
        storrelser = {p["pakningsstorrelse_gram"] for p in rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["antall_pakninger"]}
        self.assertEqual(storrelser, {100.0})

    def test_10_ukjent_lagerstatus_fungerer_som_for_i_eksakt_mal_handleliste(self):
        malt_db = {"test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {"varianter": [
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0, "lagerstatus": "ukjent"},
            {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 45.0, "lagerstatus": "ukjent"},
        ]}}}}
        rad = _rad(self._handleliste(eksakt_mal_knust=True, malt_db=malt_db), "malt", "test_malt")
        self.assertAlmostEqual(rad["expected_remainder_base"], 0.0, places=6)

    def test_11_manglende_varianter_gir_konservativ_fallback(self):
        malt_db_uten_varianter = {"test_malt": {"display_name": "Test Malt", "butikk_match": {
            "vestbrygg": {"pris": 40.0, "url": "https://vestbrygg.no/test"},
        }}}
        rad = _rad(self._handleliste(eksakt_mal_knust=True, malt_db=malt_db_uten_varianter), "malt", "test_malt")
        self.assertIsNone(rad["malt_pakningsforslag"])
        # Ingen pakke_kg registrert heller -> eksakt-mengde-forslaget (dagens
        # eksisterende, konservative fallback) brukes uendret:
        self.assertAlmostEqual(rad["suggested_purchase_quantity"], 1.23, places=2)
        # Sluttkontroll: dette er den LEGACY/manglende-variantdata-stien,
        # ikke "variantdata finnes, men alt utsolgt" -- de to skal ALDRI
        # forveksles (se TestStegF3SluttkontrollAlleRelevanteVarianterUtsolgt).
        self.assertFalse(rad["malt_ingen_relevant_variant"])
        self.assertIsNotNone(rad["estimated_cost"])


class TestStegF3SluttkontrollAlleRelevanteVarianterUtsolgt(_ShoppingListTestCase):
    """Sluttkontroll (Steg F3, andre runde): variantdata som FAKTISK FINNES,
    men der ALLE varianter for ønsket maltform er eksplisitt "utsolgt", skal
    ALDRI forveksles med "ingen variantdata i det hele tatt". Før denne
    rettelsen falt koden i dette tilfellet tilbake til det flate
    butikk_match-prisfeltet og presenterte et tilsynelatende kjøpbart
    tilbud (fast pris, cost_is_estimate=False) selv om ingen registrert
    SKU for den ønskede maltformen faktisk var tilgjengelig."""

    _MALT_DB_ALLE_UTSOLGT = {
        "test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {
            "pris": 40.0, "url": "https://vestbrygg.no/x",
            "varianter": [
                {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 45.0, "lagerstatus": "utsolgt"},
                {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0, "lagerstatus": "utsolgt"},
            ],
        }}},
    }
    _MALT_DB_EN_UTSOLGT_EN_PA_LAGER = {
        "test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {
            "pris": 40.0, "url": "https://vestbrygg.no/x",
            "varianter": [
                {"pakningsstorrelse_gram": 1000, "malttype": "knust", "pris": 45.0, "lagerstatus": "utsolgt"},
                {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0, "lagerstatus": "pa_lager"},
            ],
        }}},
    }
    _MALT_DB_UTEN_VARIANTDATA = {
        "test_malt": {"display_name": "Test Malt", "butikk_match": {"vestbrygg": {
            "pris": 40.0, "url": "https://vestbrygg.no/x",
        }}},
    }

    def _rad(self, malt_db, eksakt_mal_knust=False, mengde_kg=1.23):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"id": "test_malt", "mengde": mengde_kg}])
        handleliste = ssl.beregn_handleliste(
            recipe, p, malt_db=malt_db, butikk="Vestbrygg",
            maltform=malt_packaging.MALTFORM_KNUST, eksakt_mal_knust=eksakt_mal_knust,
        )
        return _rad(handleliste, "malt", "test_malt")

    def test_manglende_variantdata_beholder_legacy_flat_fallback(self):
        rad = self._rad(self._MALT_DB_UTEN_VARIANTDATA)
        self.assertFalse(rad["malt_ingen_relevant_variant"])
        self.assertEqual(rad["estimated_cost"], round(1.23 * 40.0, 1))
        self.assertFalse(rad["cost_is_estimate"])  # registrert flat pris, ikke gjettet
        self.assertIsNone(rad["advisory"])

    def test_alle_relevante_varianter_utsolgt_gir_ikke_falskt_kjopsforslag(self):
        rad = self._rad(self._MALT_DB_ALLE_UTSOLGT)
        self.assertIsNone(rad["malt_pakningsforslag"])
        self.assertTrue(rad["malt_ingen_relevant_variant"])
        self.assertIsNone(rad["estimated_cost"])
        self.assertTrue(rad["cost_is_estimate"])
        self.assertIsNotNone(rad["advisory"])
        self.assertFalse(rad["package_size_known"])
        # Fortsatt en reell mangel som må kjøpes -- status endres ikke, kun
        # kostnadstallet/paknings-signalet blir ærlig usikkert:
        self.assertEqual(rad["status"], "kjop")

    def test_eksakt_mal_kan_ikke_vises_som_gjennomforbart_naar_alt_utsolgt(self):
        rad = self._rad(self._MALT_DB_ALLE_UTSOLGT, eksakt_mal_knust=True)
        # Ingen malt_pakningsforslag i det hele tatt -> UI-ets
        # _render_malt_pakningsforslag()/_render_eksakt_mal_instruks() har
        # ingenting å rendre, og kan derfor aldri vise eksakt-mål som
        # gjennomførbart her:
        self.assertIsNone(rad["malt_pakningsforslag"])
        self.assertTrue(rad["malt_ingen_relevant_variant"])

    def test_en_utsolgt_en_pa_lager_bruker_kun_den_tilgjengelige(self):
        rad = self._rad(self._MALT_DB_EN_UTSOLGT_EN_PA_LAGER, mengde_kg=0.3)
        self.assertFalse(rad["malt_ingen_relevant_variant"])
        self.assertIsNotNone(rad["malt_pakningsforslag"])
        storrelser = {
            p["pakningsstorrelse_gram"]
            for p in rad["malt_pakningsforslag"]["anbefalt_kombinasjon"]["antall_pakninger"]
        }
        self.assertEqual(storrelser, {100.0})

    def test_advisory_pa_kjop_rad_krever_ikke_vis_alt(self):
        # Selve UI-gatingen er fikset i ui/smart_shopping_list_panel.py --
        # her bekreftes forutsetningen på domenenivå: advisory-teksten
        # finnes på raden uansett, uavhengig av UI-ets "vis alt"-valg
        # (som kun er en visningsdetalj, ikke noe domenelaget kjenner til).
        rad = self._rad(self._MALT_DB_ALLE_UTSOLGT)
        self.assertEqual(rad["status"], "kjop")
        self.assertIsNotNone(rad["advisory"])


if __name__ == "__main__":
    unittest.main()
