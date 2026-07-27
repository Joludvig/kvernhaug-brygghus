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
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

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
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ekte_fil = os.path.join(repo_root, "data", "pantry.json")
        for _ in range(3):
            p = pantry.last_pantry()
            p["items"].append(pantry.opprett_pantry_item(
                "malt", "weyermann_pilsner", "Pilsner", 1.0, "kg"))
            pantry.lagre_pantry(p)
        self.assertFalse(
            os.path.exists(ekte_fil),
            "Denne testen skal ALDRI skrive til den ekte data/pantry.json — "
            "KVERNHAUG_PANTRY_DIR-isolasjonen har sviktet hvis filen nå finnes",
        )


class Test23PantryDataCommittesIkke(unittest.TestCase):
    def test_gitignore_utelukker_data_pantry_json(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(repo_root, ".gitignore"), encoding="utf-8") as f:
            innhold = f.read()
        self.assertIn("data/pantry.json", innhold)


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
