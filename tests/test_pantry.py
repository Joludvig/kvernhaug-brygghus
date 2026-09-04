"""
Enhetstester for modules/pantry.py — Supply Engine / Pantry V1 sin rene
Python-motor (ingen Streamlit, ingen UI). Dekker lagring, normalisering,
matching og mangelberegning.

Isolasjon: ALLE tester setter KVERNHAUG_PANTRY_DIR til en
tempfile.TemporaryDirectory() i setUp() og gjenoppretter/fjerner miljø-
variabelen i tearDown() — akkurat samme mønster (og samme begrunnelse) som
KVERNHAUG_RECIPES_DIR i modules/recipe_storage.py og
KVERNHAUG_WATER_SOURCES_FILE/KVERNHAUG_WATER_TARGETS_FILE i
modules/water_chemistry.py: miljøvariabelen leses FRISKT ved hvert kall
(se modules/pantry.py sin _pantry_mappe()), aldri frosset ved import.
Ingen test her leser eller skriver den ekte data/pantry.json.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import os
import re
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

import modules.pantry as pantry


class _PantryTestCase(unittest.TestCase):
    """Felles isolasjonsoppsett: KVERNHAUG_PANTRY_DIR peker på en fersk
    tempdir gjennom hele testmetoden."""

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


class Test1TomPantryOpprettesTrygt(_PantryTestCase):
    def test_last_pantry_returnerer_tom_struktur_naar_fil_mangler(self):
        filsti = os.path.join(self._tmpdir.name, "pantry.json")
        self.assertFalse(os.path.exists(filsti))

        data = pantry.last_pantry()

        self.assertEqual(data["items"], [])
        self.assertEqual(data["schema_version"], pantry.SCHEMA_VERSION)

    def test_last_pantry_skriver_ikke_til_disk_ved_en_ren_lesing(self):
        # Kritisk for at det å bare RENDRE lagerpanelet (uten at brukeren
        # har gjort noe ennå) aldri skal ha sideeffekten at en fil
        # opprettes — se modules/pantry.py sin last_pantry()-docstring for
        # bakgrunnen (en reell regresjon oppdaget da render_pantry_panel
        # ble koblet inn i app.py: eksisterende AppTest-er som rendrer hele
        # app.py, uten å bry seg om Pantry, begynte å skrive til den ekte
        # data/pantry.json).
        filsti = os.path.join(self._tmpdir.name, "pantry.json")
        pantry.last_pantry()
        pantry.last_pantry()
        self.assertFalse(os.path.exists(filsti), "last_pantry() skal ALDRI skrive til disk på egen hånd")

    def test_fil_opprettes_forst_naar_noe_faktisk_lagres(self):
        filsti = os.path.join(self._tmpdir.name, "pantry.json")
        data = pantry.last_pantry()
        pantry.lagre_pantry(data)
        self.assertTrue(os.path.exists(filsti), "Filen skal opprettes trygt så snart noe faktisk lagres")


class Test2LagreOgApneIgjen(_PantryTestCase):
    def test_rundtur_bevarer_innhold(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item(
            ingredient_type="malt", ingredient_id="weyermann_pilsner",
            name_snapshot="Weyermann Pilsner", quantity=5.0, unit="kg",
        )
        p["items"].append(item)
        pantry.lagre_pantry(p)

        gjenapnet = pantry.last_pantry()
        self.assertEqual(len(gjenapnet["items"]), 1)
        self.assertEqual(gjenapnet["items"][0]["ingredient_id"], "weyermann_pilsner")
        self.assertEqual(gjenapnet["items"][0]["base_quantity"], 5000.0)
        self.assertIsNotNone(gjenapnet["updated_at"])

    def test_lagring_er_atomisk_ingen_tmp_fil_ligger_igjen(self):
        pantry.lagre_pantry(pantry.last_pantry())
        filer = os.listdir(self._tmpdir.name)
        self.assertIn("pantry.json", filer)
        self.assertFalse(any(f.endswith(".tmp") for f in filer), f"Fant .tmp-fil(er): {filer}")


class Test3KorruptJsonOverskrivesIkke(_PantryTestCase):
    def test_ugyldig_json_gir_tydelig_feil_og_rorer_ikke_filen(self):
        filsti = os.path.join(self._tmpdir.name, "pantry.json")
        with open(filsti, "w", encoding="utf-8") as f:
            f.write("{ dette er ikke gyldig json ]")

        with self.assertRaises(pantry.PantryCorruptError):
            pantry.last_pantry()

        with open(filsti, encoding="utf-8") as f:
            innhold_etter = f.read()
        self.assertEqual(innhold_etter, "{ dette er ikke gyldig json ]", "Korrupt fil ble endret/overskrevet")


class Test4MaltKgKonverteresTilGram(_PantryTestCase):
    def test_kg_gir_gram(self):
        base_q, base_u = pantry.normaliser_mengde("malt", 5.0, "kg")
        self.assertEqual(base_q, 5000.0)
        self.assertEqual(base_u, "g")

    def test_gram_forblir_gram(self):
        base_q, base_u = pantry.normaliser_mengde("malt", 250.0, "g")
        self.assertEqual(base_q, 250.0)
        self.assertEqual(base_u, "g")

    def test_ukjent_enhet_for_malt_gir_feil(self):
        with self.assertRaises(ValueError):
            pantry.normaliser_mengde("malt", 1.0, "pakke")


class Test5HumleGramBeholdesKorrekt(_PantryTestCase):
    def test_humle_gram_uendret(self):
        base_q, base_u = pantry.normaliser_mengde("humle", 100.0, "g")
        self.assertEqual(base_q, 100.0)
        self.assertEqual(base_u, "g")

    def test_humle_kg_er_ugyldig_i_v1(self):
        with self.assertRaises(ValueError):
            pantry.normaliser_mengde("humle", 1.0, "kg")


class Test6GjaerPakkerSummeres(_PantryTestCase):
    def test_flere_gjaer_poster_summeres_i_pakker(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "gjaer", "safale_us_05", "US-05", 1.0, "pakke"))
        p["items"].append(pantry.opprett_pantry_item(
            "gjaer", "safale_us_05", "US-05", 2.0, "pakke"))
        sum_ = pantry.summer_beholdning_per_ingredient(p)
        self.assertEqual(sum_[("gjaer", "safale_us_05")], 3.0)

    def test_gjaer_desimal_pakkeantall_stottes(self):
        base_q, base_u = pantry.normaliser_mengde("gjaer", 1.5, "pakke")
        self.assertEqual(base_q, 1.5)
        self.assertEqual(base_u, "pakke")


class Test7FlerePosterAvSammeIngrediensSummeres(_PantryTestCase):
    def test_to_malt_lots_summeres(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Weyermann Pilsner", 3.0, "kg", lot_number="A"))
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Weyermann Pilsner", 2.0, "kg", lot_number="B"))
        sum_ = pantry.summer_beholdning_per_ingredient(p)
        self.assertEqual(sum_[("malt", "weyermann_pilsner")], 5000.0)


def _oppskrift(malts=None, hops=None, yeast="safale_us_05", gjaer_pakker_anbefalt=None):
    r = {
        "malts": malts or [], "hops": hops or [], "yeast": yeast,
    }
    if gjaer_pakker_anbefalt is not None:
        r["gjaer_pakker_anbefalt"] = gjaer_pakker_anbefalt
    return r


class Test8MatchingSkjerPaaIngredientId(_PantryTestCase):
    def test_ulik_navn_men_samme_id_matcher(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Et helt annet navn i lageret", 10.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        rader = pantry.beregn_mangler(recipe, p)
        malt_rad = next(r for r in rader if r["ingredient_type"] == "malt")
        self.assertEqual(malt_rad["status"], "nok")
        self.assertEqual(malt_rad["available_base"], 10000.0)

    def test_samme_navn_men_ulik_id_matcher_ikke(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "en_annen_id", "Weyermann Pilsner", 10.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        rader = pantry.beregn_mangler(recipe, p)
        malt_rad = next(r for r in rader if r["ingredient_type"] == "malt")
        self.assertEqual(malt_rad["available_base"], 0.0)
        self.assertEqual(malt_rad["status"], "mangler")


class Test9NavneendringIMasterdataBryterIkkeLagerpost(_PantryTestCase):
    def test_manglende_eller_endret_master_entry_paavirker_ikke_matching(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Weyermann Pilsner (opprinnelig navn)", 10.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])

        # Simulerer at masterdatabasen har fått nytt visningsnavn (eller at
        # oppføringen er fjernet helt — tom db) siden lagerposten ble opprettet.
        ny_malt_db = {"weyermann_pilsner": {"display_name": "Helt Nytt Navn"}}
        rader = pantry.beregn_mangler(recipe, p, malt_db=ny_malt_db)
        malt_rad = next(r for r in rader if r["ingredient_type"] == "malt")
        self.assertEqual(malt_rad["status"], "nok", "Matching skal fortsatt fungere via ID uavhengig av navn i masterdata")
        self.assertEqual(malt_rad["name"], "Helt Nytt Navn", "Visningsnavnet hentes fra dagens masterdata, ikke fra snapshotten")

        # Lagerpostens egen name_snapshot er uendret uansett.
        self.assertEqual(p["items"][0]["name_snapshot"], "Weyermann Pilsner (opprinnelig navn)")


class Test10NokLagerGirStatusNok(_PantryTestCase):
    def test_status_nok(self):
        self.assertEqual(pantry.vurder_tilgjengelighet(1000, 2000, "malt"), "nok")

    def test_status_nok_akkurat_pa_grensen_med_margin(self):
        # 1000 * 1.05 = 1050 -> 1050 er akkurat nok
        self.assertEqual(pantry.vurder_tilgjengelighet(1000, 1050, "malt"), "nok")


class Test11SikkerhetsmarginGirStatusKnapp(_PantryTestCase):
    def test_status_knapp_under_margin(self):
        # 1000 nødvendig, 5% margin -> trygt er 1050. 1020 er nok til å dekke
        # behovet, men ikke nok til å nå margin-grensen.
        self.assertEqual(pantry.vurder_tilgjengelighet(1000, 1020, "malt"), "knapp")

    def test_konfigurerbar_margin(self):
        egendefinert = {"malt": 0.20}
        # 1000 nødvendig, 20% margin -> trygt er 1200. 1100 er da "knapp".
        self.assertEqual(pantry.vurder_tilgjengelighet(1000, 1100, "malt", marginer=egendefinert), "knapp")
        self.assertEqual(pantry.vurder_tilgjengelighet(1000, 1250, "malt", marginer=egendefinert), "nok")


class Test12ReellMangelBeregnesKorrekt(_PantryTestCase):
    def test_missing_base_er_uten_margin(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 3.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        rad = pantry.beregn_mangler(recipe, p)[0]
        self.assertEqual(rad["required_base"], 5000.0)
        self.assertEqual(rad["available_base"], 3000.0)
        self.assertEqual(rad["missing_base"], 2000.0, "Faktisk minimumsmangel skal IKKE inkludere sikkerhetsmargin")
        self.assertEqual(rad["status"], "mangler")

    def test_recommended_base_inkluderer_margin_men_paavirker_ikke_missing_base(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        rad = pantry.beregn_mangler(recipe, p)[0]
        self.assertEqual(rad["missing_base"], 0.0)
        self.assertEqual(rad["recommended_base"], 5250.0, "5% sikkerhetsmargin på 5000 g")
        self.assertEqual(rad["recommendation_gap_base"], 250.0)
        self.assertEqual(rad["status"], "knapp")


class Test13ManglendeIdGirUkjentMatch(_PantryTestCase):
    def test_malt_uten_id_gir_ukjent_match(self):
        p = pantry.last_pantry()
        recipe = _oppskrift(malts=[{"navn": "Uidentifisert malt", "mengde": 2.0}])
        rad = pantry.beregn_mangler(recipe, p)[0]
        self.assertEqual(rad["status"], "ukjent_match")
        self.assertIsNone(rad["ingredient_id"])

    def test_gjaer_uten_pakkeantall_gir_ukjent_match(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "safale_us_05", "US-05", 3.0, "pakke"))
        recipe = _oppskrift(yeast="safale_us_05")  # ingen gjaer_pakker_anbefalt
        rad = next(r for r in pantry.beregn_mangler(recipe, p) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["status"], "ukjent_match")
        self.assertIsNone(rad["required_base"])
        self.assertEqual(rad["available_base"], 3.0, "Tilgjengelig mengde skal fortsatt vises selv om behovet er ukjent")

    def test_gjaer_med_eksplisitt_pakkeantall_beregnes_normalt(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "safale_us_05", "US-05", 1.0, "pakke"))
        recipe = _oppskrift(yeast="safale_us_05", gjaer_pakker_anbefalt=2.0)
        rad = next(r for r in pantry.beregn_mangler(recipe, p) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["status"], "mangler")
        self.assertEqual(rad["missing_base"], 1.0)


def _wiesn_oppskrift(yeast="saflager_w3470", og=1.0799906590000001, batch_size=20.0):
    """VIKTIG: dette er en SYNTETISK, selvkonsistent oppskrift til å teste
    selve KOBLINGEN (formel-wiring, None-fallback, ID-matching) — IKKE en
    påstand om at 20 L/denne OG-en er brukerens virkelige batchvolum for
    Wiesn-Märzen 1872. Se Test27EkteWiesn23LBatchGjaerberegning under for
    de FAKTISKE, verifiserte tallene fra den ekte, gjeldende 23 L-batchen
    (tests/fixtures/recipes/wiesn_marzen_1872_23l_batch.json) — en tidligere
    rapport feilaktig omtalte 20 L som om det var oppskriftens reelle volum,
    noe det aldri var (det var kun en tilfeldig testverdi her)."""
    return {
        "malts": [
            {"id": "weyermann_munich_1", "mengde": 0.7},
            {"id": "munich_ii", "mengde": 4.6},
            {"id": "vienna", "mengde": 1.8},
        ],
        "hops": [{"id": "tettnang", "gram": 88.0, "tid": 60}],
        "yeast": yeast,
        "batch_size": batch_size,
        "stats": {"og": og},
    }


_WIESN_GJAER_DB = {
    "saflager_w3470": {"display_name": "SafLager W-34/70", "gjaertype": "Lager"},
    "lalvin_ec1118": {"display_name": "Lalvin EC-1118", "gjaertype": "Spesialgjær"},
}


class Test26GjaerPakkeantallBrukerSammeFormelSomBryggedagsarket(_PantryTestCase):
    """Regresjon 2026-07-27: Smart Handleliste/Pantry viste 'Kan ikke
    matches sikkert' for gjær i den ekte Wiesn-oppskriften selv om
    bryggedagsarket allerede regnet ut et anbefalt pakkeantall (3 pakker
    W-34/70, se modules/brewday_calc.beregn_pakker) -- de to leste rett og
    slett aldri fra samme kilde. required_base for gjær beregnes nå med
    NØYAKTIG samme pitch-rate-formel som bryggedagsarket, i stedet for å
    alltid være None.

    NB: denne klassen bruker en SYNTETISK oppskrift (_wiesn_oppskrift()
    over) bare for å teste selve wiringen/kant­tilfellene. De tallene
    stemmer IKKE nødvendigvis med brukerens faktiske, gjeldende batch —
    se Test27EkteWiesn23LBatchGjaerberegning for den ekte, verifiserte
    23 L-batchen (OG 1.064)."""

    def test_wiesn_saflager_w3470_krever_tre_pakker(self):
        # Selvkonsistent, syntetisk verdi (IKKE brukerens ekte batchvolum
        # -- se Test27 under for det): OG=1.0799906590000001 ved 20 L er
        # bare den beregnede OG-en FOR DENNE TEST-OPPSKRIFTEN sin egen
        # malt-sammensetning (modules.calculations.beregn_og, 75%
        # effektivitet), brukt for å bekrefte at formelen faktisk kobles
        # riktig sammen -- bekreftet uavhengig med
        # modules.brewday_calc.beregn_pakker(og, 20.0, "lager") == 3.
        p = pantry.last_pantry()
        recipe = _wiesn_oppskrift()
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["required_base"], 3.0)
        self.assertEqual(rad["available_base"], 0.0)
        self.assertEqual(rad["missing_base"], 3.0)
        self.assertEqual(rad["status"], "mangler")

    def test_manglende_og_gir_ukjent_match_ikke_en_gjettet_pakke(self):
        p = pantry.last_pantry()
        recipe = _wiesn_oppskrift()
        recipe["stats"] = {}  # OG mangler
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertIsNone(rad["required_base"], "Manglende OG skal ALDRI føre til en gjettet '1 pakke'")
        self.assertEqual(rad["status"], "ukjent_match")

    def test_manglende_batch_size_gir_ukjent_match(self):
        p = pantry.last_pantry()
        recipe = _wiesn_oppskrift(batch_size=None)
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertIsNone(rad["required_base"], "Manglende batchvolum skal ALDRI føre til en gjettet '1 pakke'")
        self.assertEqual(rad["status"], "ukjent_match")

    def test_gjaer_som_ikke_finnes_i_databasen_gir_ukjent_match(self):
        p = pantry.last_pantry()
        recipe = _wiesn_oppskrift(yeast="finnes_ikke")
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertIsNone(rad["required_base"], "Uten gjærtype (ukjent gjær) skal det ikke gjettes en pakkemengde")
        self.assertEqual(rad["status"], "ukjent_match")

    def test_eksplisitt_gjaer_pakker_anbefalt_overstyrer_beregningen(self):
        p = pantry.last_pantry()
        recipe = _wiesn_oppskrift()
        recipe["gjaer_pakker_anbefalt"] = 5.0
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["required_base"], 5.0, "Et eksplisitt lagret felt skal alltid vinne over den beregnede formelen")

    def test_dobling_av_batch_dobler_gjaerbehovet(self):
        p = pantry.last_pantry()
        rad_20l = next(r for r in pantry.beregn_mangler(_wiesn_oppskrift(batch_size=20.0), p, gjaer_db=_WIESN_GJAER_DB)
                       if r["ingredient_type"] == "gjaer")
        rad_40l = next(r for r in pantry.beregn_mangler(_wiesn_oppskrift(batch_size=40.0), p, gjaer_db=_WIESN_GJAER_DB)
                       if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad_20l["required_base"], 3.0)
        self.assertEqual(rad_40l["required_base"], 6.0, "Doblet batchvolum (samme OG) skal doble anbefalt pakkeantall")

    def test_ec1118_matcher_ikke_mot_w3470_stabil_id_brukes_ved_matching(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "lalvin_ec1118", "Lalvin EC-1118", 5.0, "pakke"))
        recipe = _wiesn_oppskrift()  # trenger saflager_w3470
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["ingredient_id"], "saflager_w3470")
        self.assertEqual(rad["available_base"], 0.0,
                          "EC-1118 på lager skal IKKE dekke behovet for W-34/70 -- matching skjer på stabil ingredient_id, ikke type/navn")
        self.assertEqual(rad["status"], "mangler")

    def test_riktig_gjaer_pa_lager_dekker_behovet(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("gjaer", "saflager_w3470", "SafLager W-34/70", 5.0, "pakke"))
        p["items"].append(pantry.opprett_pantry_item("gjaer", "lalvin_ec1118", "Lalvin EC-1118", 5.0, "pakke"))
        recipe = _wiesn_oppskrift()
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=_WIESN_GJAER_DB) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["available_base"], 5.0, "Kun W-34/70-postene skal telles, EC-1118 skal ikke blandes inn")
        self.assertEqual(rad["status"], "nok")


_FIXTURES_MAPPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "recipes")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _last_ekte_23l_wiesn_fixture():
    """Leser den committede, saniterte kopien av brukerens FAKTISKE,
    gjeldende Wiesn-Märzen-batch (23 L — se recipes/kvernhaug_wiesn-
    märzen_1872_-_23l_batch.json, som denne fixturen er en sanitert kopi
    av: kun name/batch_size/malts/hops/yeast/stats, ingen bryggelogg/dato/
    notater). IKKE forveksle med tests/fixtures/recipes/wiesn_marzen_1872.json
    (den ELDRE 25 L-originalen denne 23 L-batchen ble skalert ned fra)."""
    with open(os.path.join(_FIXTURES_MAPPE, "wiesn_marzen_1872_23l_batch.json"), encoding="utf-8") as f:
        return json.load(f)


def _last_ekte_gjaer_db():
    with open(os.path.join(_REPO_ROOT, "data", "master_gjaer_v2.json"), encoding="utf-8") as f:
        return json.load(f)


class Test27EkteWiesn23LBatchGjaerberegning(_PantryTestCase):
    """Verifiserer eksplisitt, mot den ekte 23 L-batchen (ikke en syntetisk
    testoppskrift), at Pantry/Smart Handleliste og bryggedagsarket alltid
    er enige om gjærpakkeantallet — og at det faktisk er OPPSKRIFTENS EGET
    batch_size-felt (23 L) som brukes, ikke en skjult 20 L-fallback.

    Bakgrunn: en tidligere rapport fra denne fiksen omtalte oppskriften som
    '20 L', men det var kun en tilfeldig verdi i en test-testvert
    (tests/_pantry_full_flow_app.py sin daværende hardkodede
    batch_volum_input) -- ALDRI noe modules/pantry.py sin formel selv
    antok. Formelen er UENDRET av denne oppdagelsen; det som er nytt her
    er testdekningen mot de faktiske, riktige tallene."""

    def test_batch_size_23_og_1064_lager_gir_tre_pakker(self):
        recipe = _last_ekte_23l_wiesn_fixture()
        self.assertEqual(recipe["batch_size"], 23.0)
        self.assertAlmostEqual(recipe["stats"]["og"], 1.064, places=3)

        gjaer_db = _last_ekte_gjaer_db()
        self.assertEqual(gjaer_db["saflager_w3470"]["gjaertype"], "Lager")

        p = pantry.last_pantry()
        rad = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=gjaer_db) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad["required_base"], 3.0)

    def test_recipe_batch_size_feltet_er_det_som_faktisk_sendes_ikke_20l(self):
        """Beviser at det er recipe["batch_size"] -- IKKE en 20 L-fallback
        noe sted i kjeden -- som når frem til beregn_pakker(). Siden 20 L
        og 23 L begge (litt tilfeldig) gir 3 pakker for DENNE oppskriftens
        OG, brukes her et eget, syntetisk OG (1.048) der 20 L og 23 L
        beviselig gir ULIKE pakkeantall (2 mot 3) -- en ekte 20 L-fallback
        ville derfor blitt fanget opp av denne testen, selv om den ikke
        fanges opp av testen over."""
        recipe = _last_ekte_23l_wiesn_fixture()
        recipe["stats"] = {"og": 1.048}
        gjaer_db = _last_ekte_gjaer_db()
        p = pantry.last_pantry()

        recipe["batch_size"] = 23.0
        rad_23 = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=gjaer_db) if r["ingredient_type"] == "gjaer")
        recipe["batch_size"] = 20.0
        rad_20 = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=gjaer_db) if r["ingredient_type"] == "gjaer")

        self.assertEqual(rad_23["required_base"], 3.0)
        self.assertEqual(rad_20["required_base"], 2.0)
        self.assertNotEqual(
            rad_23["required_base"], rad_20["required_base"],
            "20 L og 23 L MÅ gi ulikt resultat her -- hvis dette noen gang blir likt igjen, "
            "er en skjult 20 L-fallback tilbake i koden",
        )

    def test_skalering_av_den_ekte_batchen_endrer_gjaerbehovet_over_en_terskel(self):
        recipe = _last_ekte_23l_wiesn_fixture()
        gjaer_db = _last_ekte_gjaer_db()
        p = pantry.last_pantry()

        rad_23l = next(r for r in pantry.beregn_mangler(recipe, p, gjaer_db=gjaer_db) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad_23l["required_base"], 3.0)

        # Dobler batchen akkurat slik "Skaler oppskrift" gjør det i appen
        # (malt/volum skaleres proporsjonalt -> OG uendret) -- 46 L krysser
        # en pakke-terskel (3 -> 6 pakker), ikke bare et marginalt skift.
        skalert = copy.deepcopy(recipe)
        skalert["batch_size"] = 46.0
        for m in skalert["malts"]:
            m["mengde"] *= 2.0
        rad_46l = next(r for r in pantry.beregn_mangler(skalert, p, gjaer_db=gjaer_db) if r["ingredient_type"] == "gjaer")
        self.assertEqual(rad_46l["required_base"], 6.0)
        self.assertGreater(rad_46l["required_base"], rad_23l["required_base"],
                            "Gjærbehovet skal faktisk øke ved skalering, ikke stå stille på et tilfeldig tall")

    def test_bryggedagsarket_og_pantry_er_alltid_enige_om_pakkeantall(self):
        """Kjører den EKTE modules.brewday_calc.lag_brewday_plan() (samme
        funksjon ui/brewday_panel.py bruker for bryggedagsarket) og den ekte
        modules.pantry.beregn_mangler()/modules.smart_shopping_list.beregn_handleliste()
        (Smart Handleliste) på NØYAKTIG samme 23 L-oppskrift, og bekrefter at
        alle tre viser samme pakkeantall -- de kan strukturelt ikke divergere
        siden de nå deler samme underliggende formel, men denne testen
        beviser det end-to-end i stedet for bare på formelnivå."""
        from modules.brewday_calc import lag_brewday_plan
        from modules.smart_shopping_list import beregn_handleliste

        recipe = _last_ekte_23l_wiesn_fixture()
        gjaer_db = _last_ekte_gjaer_db()
        with open(os.path.join(_REPO_ROOT, "data", "master_malt.json"), encoding="utf-8") as f:
            malt_db = json.load(f)
        with open(os.path.join(_REPO_ROOT, "data", "master_humle_v2.json"), encoding="utf-8") as f:
            humle_db = json.load(f)

        gjaer_info = gjaer_db[recipe["yeast"]]
        plan = lag_brewday_plan(
            malt_valg=recipe["malts"], humle_valg=recipe["hops"], gjaer_id=recipe["yeast"],
            gjaer_info=gjaer_info, og=recipe["stats"]["og"], batch_volum_l=recipe["batch_size"],
            humle_database=humle_db, malt_database=malt_db,
        )
        self.assertEqual(plan["pakker"], 3)

        p = pantry.last_pantry()
        pantry_rad = next(r for r in pantry.beregn_mangler(recipe, p, malt_db, humle_db, gjaer_db)
                           if r["ingredient_type"] == "gjaer")
        self.assertEqual(pantry_rad["required_base"], float(plan["pakker"]),
                          "Pantry skal vise NØYAKTIG samme pakkeantall som bryggedagsarket")

        handleliste = beregn_handleliste(recipe, p, malt_db, humle_db, gjaer_db)
        handleliste_rad = next(r for r in handleliste if r["ingredient_type"] == "gjaer")
        self.assertEqual(handleliste_rad["required_base"], float(plan["pakker"]))
        self.assertEqual(handleliste_rad["missing_base"], float(plan["pakker"]))
        self.assertEqual(handleliste_rad["suggested_purchase_quantity"], float(plan["pakker"]),
                          "Smart Handleliste skal foreslå kjøp av nøyaktig det samme pakkeantallet")
        self.assertEqual(handleliste_rad["status"], "kjop")


class Test14SkalertOppskriftGirNyMangelkalkyle(_PantryTestCase):
    def test_dobling_av_batch_dobler_behovet(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        original = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        skalert = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 10.0}])

        rad_original = pantry.beregn_mangler(original, p)[0]
        rad_skalert = pantry.beregn_mangler(skalert, p)[0]

        self.assertEqual(rad_original["required_base"], 5000.0)
        self.assertEqual(rad_skalert["required_base"], 10000.0)
        self.assertEqual(rad_original["status"], "knapp")
        self.assertEqual(rad_skalert["status"], "mangler")


class Test15OppskriftenMuteresIkke(_PantryTestCase):
    def test_beregn_mangler_endrer_ikke_recipe_dict(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        recipe = _oppskrift(
            malts=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            hops=[{"id": "citra", "gram": 20.0, "tid": 60}],
            yeast="safale_us_05",
        )
        original_kopi = json.loads(json.dumps(recipe))
        pantry.beregn_mangler(recipe, p)
        self.assertEqual(recipe, original_kopi, "beregn_mangler() skal aldri mutere oppskriften den leser fra")


class Test19UtloperSnartBeregnesKorrekt(_PantryTestCase):
    def test_dager_til_utlop(self):
        i_dag = date(2026, 7, 27)
        om_30_dager = (i_dag + timedelta(days=30)).isoformat()
        self.assertEqual(pantry.dager_til_utlop(om_30_dager, i_dag=i_dag), 30)

    def test_valider_pantry_flagger_utloper_snart_innen_60_dager(self):
        i_dag = date(2026, 7, 27)
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Pilsner", 1.0, "kg",
            best_before=(i_dag + timedelta(days=10)).isoformat(),
        ))
        varsler = pantry.valider_pantry(p, i_dag=i_dag)
        self.assertTrue(any(v["type"] == "utloper_snart" for v in varsler))

    def test_valider_pantry_flagger_ikke_utloper_snart_etter_60_dager(self):
        i_dag = date(2026, 7, 27)
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "malt", "weyermann_pilsner", "Pilsner", 1.0, "kg",
            best_before=(i_dag + timedelta(days=90)).isoformat(),
        ))
        varsler = pantry.valider_pantry(p, i_dag=i_dag)
        self.assertFalse(any(v["type"] in ("utloper_snart", "utgatt") for v in varsler))


class Test20UtgattDatoGirVarsel(_PantryTestCase):
    def test_utgatt_dato_flagges(self):
        i_dag = date(2026, 7, 27)
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item(
            "gjaer", "safale_us_05", "US-05", 1.0, "pakke",
            best_before=(i_dag - timedelta(days=5)).isoformat(),
        ))
        varsler = pantry.valider_pantry(p, i_dag=i_dag)
        self.assertTrue(any(v["type"] == "utgatt" for v in varsler))
        # Utgått gjær skal fortsatt telles i beholdningen (lagerinfo, ikke
        # automatisk kvalitetsdom) — se summer_beholdning_per_ingredient.
        sum_ = pantry.summer_beholdning_per_ingredient(p)
        self.assertEqual(sum_[("gjaer", "safale_us_05")], 1.0)


class TestValideringOvrigeVarsler(_PantryTestCase):
    def test_manglende_ingredient_id_flagges(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg")
        item["ingredient_id"] = None
        p["items"].append(item)
        varsler = pantry.valider_pantry(p)
        self.assertTrue(any(v["type"] == "manglende_ingredient_id" for v in varsler))

    def test_negativ_mengde_flagges(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg")
        item["quantity"] = -5.0
        p["items"].append(item)
        varsler = pantry.valider_pantry(p)
        self.assertTrue(any(v["type"] == "negativ_mengde" for v in varsler))

    def test_ukjent_enhet_flagges(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg")
        item["unit"] = "liter"
        p["items"].append(item)
        varsler = pantry.valider_pantry(p)
        self.assertTrue(any(v["type"] == "ukjent_enhet" for v in varsler))

    def test_duplikat_pantry_id_flagges(self):
        p = pantry.last_pantry()
        item1 = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg")
        item2 = pantry.opprett_pantry_item("malt", "munich_i", "Munich I", 1.0, "kg")
        item2["pantry_item_id"] = item1["pantry_item_id"]
        p["items"] = [item1, item2]
        varsler = pantry.valider_pantry(p)
        self.assertTrue(any(v["type"] == "duplikat_id" for v in varsler))


class TestCrudOperasjoner(_PantryTestCase):
    def test_oppdater_pantry_item_reberegner_base_quantity(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg")
        p["items"].append(item)
        pantry.oppdater_pantry_item(p, item["pantry_item_id"], quantity=2.0)
        self.assertEqual(p["items"][0]["quantity"], 2.0)
        self.assertEqual(p["items"][0]["base_quantity"], 2000.0)

    def test_oppdater_ukjent_id_gir_keyerror(self):
        p = pantry.last_pantry()
        with self.assertRaises(KeyError):
            pantry.oppdater_pantry_item(p, "finnes-ikke", quantity=1.0)

    def test_slett_pantry_item_fjerner_posten(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg")
        p["items"].append(item)
        p = pantry.slett_pantry_item(p, item["pantry_item_id"])
        self.assertEqual(p["items"], [])


class Test21TesterBrukerKunMidlertidigPantryMappe(_PantryTestCase):
    def test_ekte_data_pantry_json_er_urort(self):
        # Sammenligner INNHOLD før/etter (samme mønster som
        # tests/test_recipe_storage_isolation.py sin _snapshot() og
        # TestEktAppPyRenderingPaavirkerIkkeEksisterendePantry sin
        # sentinel-sammenligning) -- IKKE bare fravær av filen. En tidligere
        # versjon antok at data/pantry.json aldri legitimt finnes i et
        # utviklingsmiljø, noe som sluttet å stemme i det øyeblikket
        # brukeren fikk ekte, gjenopprettede lagerdata der (2026-07-27).
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ekte_fil = os.path.join(repo_root, "data", "pantry.json")

        def _les():
            if not os.path.exists(ekte_fil):
                return None
            with open(ekte_fil, encoding="utf-8") as f:
                return f.read()

        innhold_for = _les()
        for _ in range(3):
            p = pantry.last_pantry()
            p["items"].append(pantry.opprett_pantry_item(
                "malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
            pantry.lagre_pantry(p)
        innhold_etter = _les()

        self.assertEqual(
            innhold_for, innhold_etter,
            "Denne testen skal ALDRI endre den ekte data/pantry.json (verken opprette den fra "
            "ingenting eller endre en eksisterende fil) — KVERNHAUG_PANTRY_DIR-isolasjonen har "
            "sviktet hvis innholdet er endret",
        )


class Test23PantryDataCommittesIkke(unittest.TestCase):
    def test_gitignore_utelukker_data_pantry_json(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(repo_root, ".gitignore"), encoding="utf-8") as f:
            innhold = f.read()
        self.assertIn("data/pantry.json", innhold)


_KBH_CUSTOM_ID_MONSTER = re.compile(
    r"^kbh-custom-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class Test25EgendefinerteIngredienser(_PantryTestCase):
    """Egendefinerte ingredienser: brukeren velger malt/humle/gjær-bøtte,
    men ingrediensen er ikke i masterdatabasen. Krever navn, får en stabil
    kbh-custom-<uuidv4>-ID (Core custom-ingredient identity-kontrakten §3,
    docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md), redigeres/
    lagres normalt, og matches ALDRI automatisk mot en oppskrift siden ingen
    oppskrift kan referere en generert custom-ID."""

    def test_krever_ikke_tomt_navn(self):
        with self.assertRaises(ValueError):
            pantry.opprett_egendefinert_pantry_item("malt", "", 1.0, "kg")

    def test_krever_ikke_kun_whitespace_navn(self):
        with self.assertRaises(ValueError):
            pantry.opprett_egendefinert_pantry_item("humle", "   ", 100.0, "g")

    def test_far_stabil_custom_id_og_is_custom_flagg(self):
        item = pantry.opprett_egendefinert_pantry_item("malt", "Hjemmelaget honning", 1.0, "kg")
        self.assertRegex(item["ingredient_id"], _KBH_CUSTOM_ID_MONSTER)
        self.assertTrue(item["is_custom"])
        self.assertEqual(item["name_snapshot"], "Hjemmelaget honning")

    def test_vanlige_poster_har_is_custom_false(self):
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Weyermann Pilsner", 5.0, "kg")
        self.assertFalse(item["is_custom"])

    def test_respekterer_normal_enhetsvalidering_for_valgt_type(self):
        with self.assertRaises(ValueError):
            pantry.opprett_egendefinert_pantry_item("humle", "Egen humle", 1.0, "kg")

    def test_id_forblir_stabil_ved_omdoping(self):
        p = pantry.last_pantry()
        item = pantry.opprett_egendefinert_pantry_item("gjaer", "Gjenbruksgjær batch 1", 1.0, "pakke")
        p["items"].append(item)
        opprinnelig_id = item["ingredient_id"]

        pantry.oppdater_pantry_item(p, item["pantry_item_id"], name_snapshot="Gjenbruksgjær (omdøpt)")

        self.assertEqual(p["items"][0]["ingredient_id"], opprinnelig_id, "ingredient_id skal ALDRI endres av en redigering")
        self.assertEqual(p["items"][0]["name_snapshot"], "Gjenbruksgjær (omdøpt)")

    def test_to_egendefinerte_ingredienser_med_samme_navn_far_ulik_id(self):
        a = pantry.opprett_egendefinert_pantry_item("malt", "Restmalt", 1.0, "kg")
        b = pantry.opprett_egendefinert_pantry_item("malt", "Restmalt", 1.0, "kg")
        self.assertNotEqual(a["ingredient_id"], b["ingredient_id"])

    def test_tvunget_kollisjon_regenererer_i_stedet_for_a_gjenbruke(self):
        """Core-kontraktens §6: en generation-time-kollisjon skal ALDRI
        overskrive/gjenbruke en eksisterende ID -- generatoren skal mint en
        FRISK en i stedet. Simuleres ved å mocke uuid.uuid4() til å returnere
        samme (kolliderende) verdi to ganger før en unik tredje."""
        kolliderende_uuid = pantry.uuid.UUID("11111111-1111-4111-8111-111111111111")
        unik_uuid = pantry.uuid.UUID("22222222-2222-4222-8222-222222222222")
        eksisterende = {f"kbh-custom-{kolliderende_uuid}"}
        with mock.patch.object(pantry.uuid, "uuid4", side_effect=[kolliderende_uuid, kolliderende_uuid, unik_uuid]):
            ny_id = pantry._generer_custom_ingredient_id(eksisterende)
        self.assertEqual(ny_id, f"kbh-custom-{unik_uuid}")
        self.assertNotIn(ny_id, eksisterende)

    def test_kollisjonssjekk_dekker_eksisterende_ider_i_pantry(self):
        """opprett_egendefinert_pantry_item() sender pantry sine eksisterende
        ingredient_id-er videre til generatoren (Core-kontraktens §6:
        kollisjonssjekken må dekke enhver lokal lagringsplass som kan holde
        en custom-ID -- i dag kun pantry, se issue #48 sin AC 6)."""
        p = pantry.last_pantry()
        eksisterende_item = pantry.opprett_egendefinert_pantry_item("malt", "Restmalt", 1.0, "kg")
        p["items"].append(eksisterende_item)
        opptatt_id = eksisterende_item["ingredient_id"]

        with mock.patch.object(pantry.uuid, "uuid4", side_effect=[
            pantry.uuid.UUID(opptatt_id[len("kbh-custom-"):]),
            pantry.uuid.UUID("33333333-3333-4333-8333-333333333333"),
            pantry.uuid.UUID("44444444-4444-4444-8444-444444444444"),  # pantry_item_id
        ]):
            nytt_item = pantry.opprett_egendefinert_pantry_item("malt", "Restmalt 2", 1.0, "kg", pantry=p)

        self.assertNotEqual(nytt_item["ingredient_id"], opptatt_id)

    def test_legacy_custom_id_forblir_uendret_ved_vanlig_redigering(self):
        """En allerede lagret legacy custom_<uuid>-post (mintet FØR denne
        kontrakten) skal lastes og forbli uendret etter en normal redigering
        -- ALDRI migreres/normaliseres til det nye kbh-custom--formatet
        (Core-kontraktens §9 og §10: kun NYE ingredienser bruker det nye
        formatet, ingen migrering av eksisterende data)."""
        p = pantry.last_pantry()
        legacy_item = pantry.opprett_pantry_item(
            "malt", "custom_ab12cd34ef56", "Gammel egendefinert malt", 1.0, "kg", is_custom=True,
        )
        p["items"].append(legacy_item)

        pantry.oppdater_pantry_item(p, legacy_item["pantry_item_id"], name_snapshot="Gammel egendefinert malt (endret)")

        self.assertEqual(p["items"][0]["ingredient_id"], "custom_ab12cd34ef56")
        self.assertEqual(p["items"][0]["name_snapshot"], "Gammel egendefinert malt (endret)")

    def test_egendefinert_ingrediens_matcher_ikke_automatisk_mot_oppskrift(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_egendefinert_pantry_item(
            "malt", "Restmalt fra forrige brygg", 20.0, "kg"))
        # Oppskriften trenger en helt vanlig masterdatabase-malt -- den
        # egendefinerte posten skal IKKE telle med i "available_base" for
        # den, siden ID-ene aldri kan være like.
        recipe = _oppskrift(malts=[{"id": "weyermann_pilsner", "mengde": 5.0}])
        rad = pantry.beregn_mangler(recipe, p)[0]
        self.assertEqual(rad["available_base"], 0.0, "Egendefinert lagerpost skal ikke dekke behovet for en ekte oppskrift-ingrediens")
        self.assertEqual(rad["status"], "mangler")

    def test_egendefinert_post_summeres_for_seg_selv(self):
        p = pantry.last_pantry()
        item = pantry.opprett_egendefinert_pantry_item("humle", "Egendyrket humle", 50.0, "g")
        p["items"].append(item)
        sum_ = pantry.summer_beholdning_per_ingredient(p)
        self.assertEqual(sum_[("humle", item["ingredient_id"])], 50.0)

    def test_valider_pantry_krever_ikke_masterdata_for_egendefinert(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_egendefinert_pantry_item("gjaer", "Restgjær", 1.0, "pakke"))
        varsler = pantry.valider_pantry(p)
        self.assertFalse(
            any(v["type"] == "manglende_ingredient_id" for v in varsler),
            "En egendefinert post HAR en (generert) ingredient_id og skal ikke flagges som manglende",
        )


def _antall_backupfiler(mappe):
    return len([f for f in os.listdir(mappe) if ".backup_" in f])


class Test28PantryBackupOgGjenoppretting(_PantryTestCase):
    """Automatisk, rullerende backup FØR hver reell endring av en
    eksisterende pantry.json (oppdatering, sletting, hurtigjustering, full
    overskriving, import/migrering) — se lagre_pantry()/
    _rydd_gamle_pantry_backupfiler() i modules/pantry.py. Alle disse
    veiene går til slutt gjennom SAMME lagre_pantry()-kall, så det er det
    ENE kontrollpunktet backupen henger på."""

    def test_forste_lagring_uten_eksisterende_fil_lager_ingen_backup(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
        pantry.lagre_pantry(p)
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 0,
                          "Aller første lagring har ingenting å sikkerhetskopiere")

    def test_oppdatering_av_eksisterende_post_lager_backup(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg")
        p["items"].append(item)
        pantry.lagre_pantry(p)  # første lagring -- ingen backup ennå

        pantry.oppdater_pantry_item(p, item["pantry_item_id"], quantity=2.0)
        pantry.lagre_pantry(p)  # oppdatering av eksisterende fil -- SKAL lage backup
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1)

    def test_sletting_av_vare_lager_backup(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg")
        p["items"].append(item)
        pantry.lagre_pantry(p)

        p = pantry.slett_pantry_item(p, item["pantry_item_id"])
        pantry.lagre_pantry(p)
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1)

    def test_full_overskriving_lager_backup(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        pantry.lagre_pantry(p)

        helt_ny_data = {"schema_version": pantry.SCHEMA_VERSION, "updated_at": None, "items": []}
        pantry.lagre_pantry(helt_ny_data)
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1)

    def test_import_migrering_lager_backup(self):
        p = pantry.last_pantry()
        p["items"].append(pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 5.0, "kg"))
        pantry.lagre_pantry(p)

        forslag = pantry.forhandsvis_humlelager_migrering({"citra": 100.0})
        nytt = pantry.importer_humlelager_migrering(p, forslag)
        pantry.lagre_pantry(nytt)
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1)

    def test_rullering_beholder_kun_konfigurert_antall(self):
        p = pantry.last_pantry()
        pantry.lagre_pantry(p)  # første lagring -- ingen backup
        for i in range(5):
            p["items"] = [pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", float(i), "kg")]
            pantry.lagre_pantry(p, maks_backup_antall=3)
        # 5 lagringer over en eksisterende fil -> 5 backup-forsøk, men kun
        # de 3 NYESTE skal være igjen.
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 3)

    def test_maks_antall_0_betyr_behold_alt(self):
        p = pantry.last_pantry()
        pantry.lagre_pantry(p)
        for i in range(4):
            p["items"] = [pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", float(i), "kg")]
            pantry.lagre_pantry(p, maks_backup_antall=0)
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 4)

    def test_list_pantry_backups_nyest_forst(self):
        p = pantry.last_pantry()
        pantry.lagre_pantry(p)
        for i in range(3):
            p["items"] = [pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", float(i), "kg")]
            pantry.lagre_pantry(p, maks_backup_antall=0)

        backups = pantry.list_pantry_backups()
        self.assertEqual(len(backups), 3)
        stier_kronologisk = sorted(b["sti"] for b in backups)
        self.assertEqual([b["sti"] for b in backups], list(reversed(stier_kronologisk)),
                          "list_pantry_backups() skal returnere nyest først")

    def test_les_pantry_backup_innhold_matcher_det_som_ble_sikkerhetskopiert(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 7.0, "kg")
        p["items"].append(item)
        pantry.lagre_pantry(p)  # ingen backup ennå (første lagring)

        pantry.oppdater_pantry_item(p, item["pantry_item_id"], quantity=1.0)
        pantry.lagre_pantry(p)  # backup tas HER, med quantity=7.0 (tilstanden FØR denne endringen)

        backups = pantry.list_pantry_backups()
        self.assertEqual(len(backups), 1)
        innhold = pantry.les_pantry_backup_innhold(backups[0]["sti"])
        self.assertEqual(innhold["items"][0]["quantity"], 7.0,
                          "Backupen skal vise tilstanden FØR endringen, ikke etter")

    def test_les_pantry_backup_innhold_korrupt_fil_gir_tydelig_feil(self):
        korrupt_sti = os.path.join(self._tmpdir.name, "pantry.json.backup_20260101_000000_000000")
        with open(korrupt_sti, "w", encoding="utf-8") as f:
            f.write("{ ikke gyldig json ]")
        with self.assertRaises(pantry.PantryCorruptError):
            pantry.les_pantry_backup_innhold(korrupt_sti)

    def test_gjenopprett_fra_backup_returnerer_men_lagrer_ikke(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 7.0, "kg")
        p["items"].append(item)
        pantry.lagre_pantry(p)  # ingen backup ennå

        pantry.oppdater_pantry_item(p, item["pantry_item_id"], quantity=1.0)
        pantry.lagre_pantry(p)  # backup tas her (quantity=7.0)

        backup_sti = pantry.list_pantry_backups()[0]["sti"]
        gjenopprettet = pantry.gjenopprett_pantry_fra_backup(backup_sti)
        self.assertEqual(gjenopprettet["items"][0]["quantity"], 7.0)

        # Gjenoppretting skal IKKE lagre noe selv -- filen på disk er
        # fortsatt den siste lagrede tilstanden (quantity=1.0) helt til
        # kalleren eksplisitt kaller lagre_pantry() med resultatet.
        fortsatt_pa_disk = pantry.last_pantry()
        self.assertEqual(fortsatt_pa_disk["items"][0]["quantity"], 1.0)

    def test_gjenoppretting_er_selv_en_lagring_som_tar_ny_backup(self):
        p = pantry.last_pantry()
        item = pantry.opprett_pantry_item("malt", "weyermann_pilsner", "Pilsner", 7.0, "kg")
        p["items"].append(item)
        pantry.lagre_pantry(p)  # ingen backup ennå

        pantry.oppdater_pantry_item(p, item["pantry_item_id"], quantity=1.0)
        pantry.lagre_pantry(p)  # backup #1 (quantity=7.0)

        backup_sti = pantry.list_pantry_backups()[0]["sti"]
        gjenopprettet = pantry.gjenopprett_pantry_fra_backup(backup_sti)
        pantry.lagre_pantry(gjenopprettet)  # dette ER en lagring -> tar backup #2 (quantity=1.0)

        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 2)
        pa_disk = pantry.last_pantry()
        self.assertEqual(pa_disk["items"][0]["quantity"], 7.0, "Lageret skal nå reflektere den gjenopprettede tilstanden")


class Test24HumlelagerImportErEksplisitt(_PantryTestCase):
    def test_forhandsvisning_skriver_ingenting(self):
        filsti = os.path.join(self._tmpdir.name, "pantry.json")
        self.assertFalse(os.path.exists(filsti))

        gammelt_lager = {"citra": 150.0, "magnum": 50.0}
        forslag = pantry.forhandsvis_humlelager_migrering(gammelt_lager, humle_db={
            "citra": {"display_name": "Citra"}, "magnum": {"display_name": "Magnum"},
        })

        self.assertEqual(len(forslag), 2)
        self.assertFalse(os.path.exists(filsti), "Forhåndsvisning skal IKKE opprette/skrive pantry.json")

    def test_import_krever_eksplisitt_kall_og_skriver_ikke_selv(self):
        p = pantry.last_pantry()
        forslag = pantry.forhandsvis_humlelager_migrering({"citra": 150.0})
        nytt = pantry.importer_humlelager_migrering(p, forslag)

        self.assertEqual(len(nytt["items"]), 1)
        self.assertEqual(nytt["items"][0]["ingredient_id"], "citra")
        # importer_humlelager_migrering() lagrer IKKE selv -- kalleren må
        # eksplisitt kalle lagre_pantry() etterpå.
        gjenlest = pantry.last_pantry()
        self.assertEqual(gjenlest["items"], [], "Import skal ikke skrive til disk på egen hånd")

    def test_negativ_eller_ugyldig_gram_i_gammelt_lager_hoppes_over(self):
        forslag = pantry.forhandsvis_humlelager_migrering({"citra": -10.0, "magnum": "ikke_tall"})
        self.assertEqual(forslag, [])

    def test_last_pantry_importerer_aldri_automatisk(self):
        # Selv med en fantasi-fil til stede andre steder, skal last_pantry()
        # aldri selv gå og lete etter/importere det gamle humlelager-formatet.
        data = pantry.last_pantry()
        self.assertEqual(data["items"], [])


if __name__ == "__main__":
    unittest.main()
