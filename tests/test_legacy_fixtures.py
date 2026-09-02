"""
Integritetstester for Core Stabilization Oppdrag 2B — Legacy Fixtures.

Beviser at fixturene under tests/fixtures/legacy/ faktisk gjør det de
påstår: parser som gyldig JSON, masterdata-/pantry-subsettene er
FROSSET PROVENANCE (verifisert mot eksplisitte forventede IDs/shapes
og faste SHA-256-hasher tatt ved capture-commit
3ed82cf42c8bb4b0c53e8c74b21c965e1699775a -- IKKE mot dagens levende
data/master_*.json/data/pantry.example.json, se
tests/fixtures/legacy/README.md "CAPTURE PROVENANCE"),
.kbhrecipe-fixturene matcher faktisk output fra dagens
modules/kbh_contract.py for tilsvarende syntetisk input, Web-
wrapperne bruker dagens eksisterende format/version-konstanter (lest
direkte fra web/js/*.js -- samme kildekontrakt-mønster som de andre
web-testene i denne mappen, siden miljøet ikke har noen JS-kjøretid),
og ingen fixture inneholder kjente, virkelige Kvernhaug-oppskriftsnavn.

VIKTIG: en fremtidig, legitim endring av data/master_*.json eller
data/pantry.example.json skal ALDRI gjøre disse testene røde. Testene
under sammenligner fixturene mot seg selv (hash) og mot hardkodede
forventninger, aldri mot en live kildefil.

Dette er BEVIS-tester for fixturene selv, ikke en ny valideringsmotor
for produksjonskoden -- se tests/fixtures/legacy/README.md.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import glob
import hashlib
import io
import json
import os
import unittest

from modules.recipe import bygg_recipe_object
from modules.kbh_contract import bygg_kbhrecipe_konvolutt

# Capture commit -- se tests/fixtures/legacy/README.md "CAPTURE PROVENANCE".
_CAPTURE_COMMIT = "3ed82cf42c8bb4b0c53e8c74b21c965e1699775a"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURE_ROOT = os.path.join(_ROOT, "tests", "fixtures", "legacy")

_APP_JS = os.path.join(_ROOT, "web", "js", "app.js")
_RECIPE_STORAGE_JS = os.path.join(_ROOT, "web", "js", "recipe_storage.js")
_BREW_STORAGE_JS = os.path.join(_ROOT, "web", "js", "brew_storage.js")
_PANTRY_JS = os.path.join(_ROOT, "web", "js", "pantry.js")

# Kjente, virkelige oppskriftsnavn/identifikatorer observert i private
# recipes/*.json under Oppdrag 2A -- skal ALDRI forekomme i noen fixture.
_KJENTE_PRIVATE_STRENGER = [
    "Eldsvenn",
    "Gamleguten",
    "Sommerglød",
    "Sommerglod",
    "Vardeldr",
    "Kvernhaug Wiesn-Märzen",
    "Wiesn-Märzen 1872",
]


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _last_json(sti):
    with io.open(sti, encoding="utf-8") as f:
        return json.load(f)


def _sha256(sti):
    with open(sti, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _alle_fixture_json_filer():
    return sorted(glob.glob(os.path.join(_FIXTURE_ROOT, "**", "*.json"), recursive=True))


class TestAlleFixturesParserSomJson(unittest.TestCase):
    """Krav 1: alle nye JSON-fixtures parser."""

    def test_alle_json_filer_parser(self):
        filer = _alle_fixture_json_filer()
        self.assertGreaterEqual(len(filer), 14, "Forventet minst 14 fixture-filer")
        for sti in filer:
            with self.subTest(fil=sti):
                _last_json(sti)  # kaster hvis ugyldig JSON


class TestMasterdataFixturerFrozenProvenance(unittest.TestCase):
    """Krav 2 (QA-korrigert): masterdata fixture IDs/entries er FROSSET
    PROVENANCE, verifisert mot eksplisitte forventede IDs og faste
    SHA-256-hasher tatt ved capture-commit -- ALDRI mot dagens levende
    data/master_*.json. En fremtidig, legitim Core-masteroppdatering
    skal ikke gjøre disse testene røde."""

    _FORVENTEDE_MALT_IDER = {
        "bohemian_pilsner_floor", "crystal_maple_carapils",
        "weyermann_pilsner", "vienna", "flaket_havre",
    }
    _FORVENTET_MALT_SHA256 = "1634ae503e66f8df5123f0ab713abe616da3a5c8385f8a775c55337cbafaeddd"

    _FORVENTEDE_HUMLE_IDER = {"amarillo", "comet", "east_kent_goldings", "tettnang"}
    _FORVENTET_HUMLE_SHA256 = "47ce1187b2e51c64df1aced5010755fb6138b347ceb3afe814619bf5063c7e61"

    _FORVENTEDE_GJAER_IDER = {"saflager_w3470", "wlp_810", "lalvin_ec1118", "lalbrew_diamond_lager"}
    _FORVENTET_GJAER_SHA256 = "54e8c5f84324a3af256ab9913e5df93598a948c36c2b0f59ed97a0dfe434f477"

    def test_malt_subset_har_forventede_ider_og_uendret_hash(self):
        sti = os.path.join(_FIXTURE_ROOT, "masterdata", "malt.json")
        subset = _last_json(sti)
        self.assertEqual(set(subset.keys()), self._FORVENTEDE_MALT_IDER)
        self.assertEqual(
            _sha256(sti), self._FORVENTET_MALT_SHA256,
            "malt.json sitt innhold har driftet siden capture -- fixturen "
            "skal IKKE oppdateres bare fordi canonical master endres, se README",
        )

    def test_humle_subset_har_forventede_ider_uendret_hash_og_dekker_verified_begge_veier(self):
        sti = os.path.join(_FIXTURE_ROOT, "masterdata", "humle.json")
        subset = _last_json(sti)
        self.assertEqual(set(subset.keys()), self._FORVENTEDE_HUMLE_IDER)
        self.assertEqual(_sha256(sti), self._FORVENTET_HUMLE_SHA256)
        verified_verdier = {v["verified"] for v in subset.values()}
        self.assertEqual(verified_verdier, {True, False}, "humle-subset må dekke både verified:true og :false")
        sources = {v["source"] for v in subset.values()}
        self.assertEqual(sources, {"master_seed_v0_1", "auto_added"}, "humle-subset må dekke begge observerte source-verdiene")
        # Ikke syntetisert "alfa" -- dagens master bruker kun alfa_typisk.
        for entry in subset.values():
            self.assertNotIn("alfa", entry)
            self.assertIn("alfa_typisk", entry)

    def test_gjaer_subset_har_forventede_ider_uendret_hash_og_dekker_manglende_felt(self):
        sti = os.path.join(_FIXTURE_ROOT, "masterdata", "gjaer.json")
        subset = _last_json(sti)
        self.assertEqual(set(subset.keys()), self._FORVENTEDE_GJAER_IDER)
        self.assertEqual(_sha256(sti), self._FORVENTET_GJAER_SHA256)
        mangler_verified = [k for k, v in subset.items() if "verified" not in v]
        self.assertTrue(mangler_verified, "gjaer-subset må dekke minst én entry uten verified")
        mangler_begge = [k for k in mangler_verified if "source" not in subset[k]]
        self.assertTrue(mangler_begge, "gjaer-subset må dekke minst én entry uten BÅDE verified og source (White Labs-mønsteret)")
        har_beskrivelse = [k for k, v in subset.items() if "beskrivelse" in v]
        self.assertTrue(har_beskrivelse, "gjaer-subset må dekke minst én entry med legacy beskrivelse-felt")

    def test_capture_commit_dokumentert_i_readme(self):
        readme = _les(os.path.join(_FIXTURE_ROOT, "README.md"))
        self.assertIn(_CAPTURE_COMMIT, readme)
        self.assertIn("IKKE", readme)  # regelen om at fixtures ikke oppdateres pga. master-endring


class TestAppRecipeFixturerHarLegacyShape(unittest.TestCase):
    """Krav 3: syntetiske App recipe-fixtures har dagens forventede
    legacy shape (modules/recipe.py::bygg_recipe_object())."""

    _FORVENTEDE_FELT = {
        "name", "batch_size", "efficiency", "brygger_stil", "malts", "hops",
        "yeast", "stats", "flavor_profile", "process_profile",
        "water_source_profile", "water_target_profile", "water_treatment",
        "water_measurements",
    }

    def test_minimal_har_alle_felt_men_valgfrie_er_null_default(self):
        r = _last_json(os.path.join(_FIXTURE_ROOT, "app", "recipe_minimal.json"))
        self.assertEqual(set(r.keys()), self._FORVENTEDE_FELT)
        self.assertEqual(r["brygger_stil"], "")
        self.assertIsNone(r["process_profile"])
        self.assertIsNone(r["water_source_profile"])
        self.assertIsNone(r["water_target_profile"])
        self.assertIsNone(r["water_treatment"])
        self.assertIsNone(r["water_measurements"])
        self.assertEqual(r["flavor_profile"], {})
        self.assertIn("og", r["stats"])

    def test_full_har_alle_valgfrie_blokker_utfylt(self):
        r = _last_json(os.path.join(_FIXTURE_ROOT, "app", "recipe_full.json"))
        self.assertEqual(set(r.keys()), self._FORVENTEDE_FELT)
        self.assertNotEqual(r["brygger_stil"], "")
        self.assertIsNotNone(r["process_profile"])
        self.assertIsNotNone(r["water_source_profile"])
        self.assertIsNotNone(r["water_target_profile"])
        self.assertIsNotNone(r["water_treatment"])
        self.assertIsNotNone(r["water_measurements"])
        self.assertTrue(len(r["flavor_profile"]) > 0)

    def test_ingen_id_felt_pa_native_app_oppskrift(self):
        # App sin native form har INGEN internt id-felt -- identitet er
        # filnavn/navn (se Oppdrag 2A punkt 4). Bevisst IKKE lagt til her.
        for navn in ("recipe_minimal.json", "recipe_full.json"):
            r = _last_json(os.path.join(_FIXTURE_ROOT, "app", navn))
            self.assertNotIn("recipeId", r)
            self.assertNotIn("id", r)

    def test_brew_log_er_flat_array_uten_wrapper_og_dekker_ad_hoc_felt(self):
        logg = _last_json(os.path.join(_FIXTURE_ROOT, "app", "brew_log.json"))
        self.assertIsInstance(logg, list)
        self.assertGreaterEqual(len(logg), 2)
        for entry in logg:
            for felt in ("date", "actual_volume_l", "actual_og", "actual_fg", "actual_abv", "note"):
                self.assertIn(felt, entry)
        med_prosess = [e for e in logg if "process_profile_navn" in e]
        uten_prosess = [e for e in logg if "process_profile_navn" not in e]
        self.assertTrue(med_prosess, "brew_log må dekke en entry MED process_profile_navn")
        self.assertTrue(uten_prosess, "brew_log må dekke en entry UTEN process_profile_navn")

    def test_pantry_v1_er_frosset_kopi_av_pantry_example_med_forventet_shape(self):
        # Krav (QA-korrigert punkt 2/3): pantry_v1.json er en FROSSET
        # Phase 0-fixture -- verifisert mot en fast SHA-256 tatt ved
        # capture, IKKE mot dagens levende data/pantry.example.json (som
        # kan endres av fremtidige, urelaterte runder uten at dette skal
        # gjøre fixturen ugyldig).
        sti = os.path.join(_FIXTURE_ROOT, "app", "pantry_v1.json")
        forventet_sha256 = "5030a9ff7b72848d9bf5515327f1d131512635751333dea13654d06aeb232588"
        self.assertEqual(
            _sha256(sti), forventet_sha256,
            "pantry_v1.json har driftet siden capture -- se README CAPTURE PROVENANCE",
        )
        pantry = _last_json(sti)
        self.assertEqual(pantry.get("schema_version"), 1)
        self.assertIn("items", pantry)
        self.assertIsInstance(pantry["items"], list)
        self.assertGreaterEqual(len(pantry["items"]), 1)
        typer = {i["ingredient_type"] for i in pantry["items"]}
        self.assertEqual(typer, {"malt", "humle", "gjaer"}, "pantry-eksempelet må dekke alle tre ingredienstyper")
        for item in pantry["items"]:
            for felt in ("pantry_item_id", "ingredient_id", "name_snapshot", "quantity", "unit", "base_quantity", "base_unit", "opened"):
                self.assertIn(felt, item)


class TestKbhrecipeFixturerMatcherFaktiskAdapter(unittest.TestCase):
    """Krav 4: kbhrecipe-fixtures matcher faktisk output fra dagens
    modules/kbh_contract.py for tilsvarende syntetiske input. Bygger
    NØYAKTIG samme input som ble brukt til å fryse fixturene, kjører
    den gjennom den ekte, uendrede produksjonsadapteren, og
    sammenligner mot den frosne filen."""

    _FROSSET_TIDSPUNKT = "2026-01-01T00:00:00.000000"

    def test_minimal_matcher_adapter_output(self):
        recipe = bygg_recipe_object(
            navn="Testbrygg Minimal (syntetisk fixture)",
            batch_size=20.0, efficiency=0.72,
            malts=[{"id": "weyermann_pilsner", "mengde": 4.0}],
            hops=[{"id": "tettnang", "gram": 30.0, "tid": 60}],
            yeast=None,
            og=1.048, fg=1.012, abv=4.7, ibu=18.0, ebc=9.0,
            flavor_profile={},
        )
        forventet = bygg_kbhrecipe_konvolutt(recipe, self._FROSSET_TIDSPUNKT)
        faktisk = _last_json(os.path.join(_FIXTURE_ROOT, "kbhrecipe", "minimal.json"))
        self.assertEqual(faktisk, forventet)

    def test_full_matcher_adapter_output(self):
        recipe = bygg_recipe_object(
            navn="Testbrygg Full (syntetisk fixture)",
            batch_size=23.0, efficiency=0.75,
            malts=[
                {"id": "bohemian_pilsner_floor", "mengde": 4.0},
                {"id": "vienna", "mengde": 1.5},
            ],
            hops=[
                {"id": "east_kent_goldings", "gram": 40.0, "tid": 60},
                {"id": "amarillo", "gram": 15.0, "tid": 10},
            ],
            yeast="lalbrew_diamond_lager",
            og=1.052, fg=1.011, abv=5.4, ibu=24.0, ebc=12.0,
            flavor_profile={"Maltfylde": 5.0, "Sitrus": 2.0, "Bitterhet": 3.0},
            brygger_stil="Testbryggerens egen stil (syntetisk)",
            process_profile={
                "process_id": "enkel_infusjon", "navn": "Enkel infusjon",
                "vanskelighetsgrad": "Lett",
                "mash_steps": [{"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"}],
                "sparge_method": "batch_sparge", "boil_minutes": 60,
                "decoction_steps": None, "reiterated_mash": None,
            },
            water_source_profile={"water_id": "__syntetisk_testkilde__", "ca": 20.0, "mg": 4.0},
            water_target_profile={"target_id": "__syntetisk_testmaal__", "ca_min": 50, "ca_max": 65},
            water_treatment={"vannkilde_id": None, "fordelingsmetode": "proporsjonal", "salter": [{"id": "gips", "gram": 4.0}]},
            water_measurements={"maalt_mash_ph": 5.3, "maaletidspunkt_min": 12, "malt_ved_romtemperatur": False, "syrer": []},
        )
        forventet = bygg_kbhrecipe_konvolutt(recipe, self._FROSSET_TIDSPUNKT)
        faktisk = _last_json(os.path.join(_FIXTURE_ROOT, "kbhrecipe", "full.json"))
        self.assertEqual(faktisk, forventet)
        self.assertIn("vann", faktisk["recipe"])
        self.assertEqual(
            set(faktisk["recipe"]["vann"].keys()),
            {"kilde", "maal", "behandling", "maalinger"},
        )

    def test_partial_water_fryser_faktisk_delvis_vann_adferd(self):
        recipe = bygg_recipe_object(
            navn="Testbrygg Partial Water (syntetisk fixture)",
            batch_size=20.0, efficiency=0.75,
            malts=[{"id": "weyermann_pilsner", "mengde": 4.0}],
            hops=[{"id": "tettnang", "gram": 30.0, "tid": 60}],
            yeast="saflager_w3470",
            og=1.048, fg=1.012, abv=4.7, ibu=18.0, ebc=9.0,
            flavor_profile={},
            water_measurements={"maalt_mash_ph": 5.3, "maaletidspunkt_min": 12, "malt_ved_romtemperatur": False, "syrer": []},
        )
        forventet = bygg_kbhrecipe_konvolutt(recipe, self._FROSSET_TIDSPUNKT)
        faktisk = _last_json(os.path.join(_FIXTURE_ROOT, "kbhrecipe", "partial_water.json"))
        self.assertEqual(faktisk, forventet)
        # Beviser _bygg_vann_blokk()-adferden: KUN maalinger er satt.
        self.assertEqual(set(faktisk["recipe"]["vann"].keys()), {"maalinger"})

    def test_stats_og_flavor_profile_aldri_i_output(self):
        for navn in ("minimal.json", "full.json", "partial_water.json"):
            faktisk = _last_json(os.path.join(_FIXTURE_ROOT, "kbhrecipe", navn))
            self.assertNotIn("stats", faktisk["recipe"])
            self.assertNotIn("flavor_profile", faktisk["recipe"])
            self.assertNotIn("recipeId", faktisk["recipe"])


class TestWebWrapperFixturerBrukerDagensKonstanter(unittest.TestCase):
    """Krav 5: Web wrapper-fixtures har dagens eksisterende
    format/version-konstanter. Miljøet har ingen JS-kjøretid (verifisert
    tidligere denne økten) -- leser derfor konstantene direkte fra
    kildekoden (samme source-contract-mønster som de andre web-testene
    i denne mappen) i stedet for å kjøre JS."""

    def test_recipe_store_v1_matcher_recipe_storage_js_konstanter(self):
        kilde = _les(_RECIPE_STORAGE_JS)
        self.assertIn('const OPPSKRIFT_STORE_FORMAT = "kbh-recipes";', kilde)
        self.assertIn("const OPPSKRIFT_STORE_VERSION = 1;", kilde)
        self.assertIn("const RECIPE_SCHEMA_VERSION = 1;", kilde)
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "recipe_store_v1.json"))
        self.assertEqual(fixture["format"], "kbh-recipes")
        self.assertEqual(fixture["version"], 1)
        self.assertGreaterEqual(len(fixture["items"]), 2)
        ids = [item["recipeId"] for item in fixture["items"]]
        self.assertEqual(len(ids), len(set(ids)), "recipeId må være unik per item")
        for item in fixture["items"]:
            self.assertEqual(item["recipe"]["recipeSchemaVersion"], 1)

    def test_recipe_store_v1_dekker_normal_og_custom_malt_humle_gjaer(self):
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "recipe_store_v1.json"))
        alle_malt = [m for item in fixture["items"] for m in item["recipe"]["malt"]]
        alle_humle = [h for item in fixture["items"] for h in item["recipe"]["humle"]]
        self.assertTrue(any("custom" not in m for m in alle_malt), "må dekke normal (biblioteks-)malt")
        self.assertTrue(any("custom" in m for m in alle_malt), "må dekke custom malt")
        self.assertTrue(any("custom" not in h for h in alle_humle), "må dekke normal (biblioteks-)humle")
        self.assertTrue(any("custom" in h for h in alle_humle), "må dekke custom humle")
        gjaer_ider = [item["recipe"]["gjaerId"] for item in fixture["items"]]
        gjaer_custom = [item["recipe"]["gjaerCustom"] for item in fixture["items"]]
        self.assertTrue(any(g for g in gjaer_ider), "må dekke biblioteksgjær (gjaerId)")
        self.assertTrue(any(g for g in gjaer_custom), "må dekke custom gjær (gjaerCustom)")
        self.assertTrue(
            all("lagretDato" in item["recipe"] for item in fixture["items"]),
            "lagretDato er en del av dagens faktiske web-payload (samleOppskrift()) og må være med",
        )

    def test_recipe_store_legacy_flat_gjenkjennes_av_migreringslogikken(self):
        kilde = _les(_RECIPE_STORAGE_JS)
        self.assertIn("parsed.format === undefined", kilde)
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "recipe_store_legacy_flat.json"))
        self.assertNotIn("format", fixture)
        self.assertIsInstance(fixture, dict)
        for navn, oppskrift in fixture.items():
            self.assertEqual(oppskrift.get("navn"), navn)

    def test_brew_store_v1_matcher_brew_storage_js_konstanter(self):
        kilde = _les(_BREW_STORAGE_JS)
        self.assertIn('const BREW_STORE_FORMAT = "kbh-brews";', kilde)
        self.assertIn("const BREW_STORE_VERSION = 1;", kilde)
        self.assertIn('const BREW_FIL_FORMAT = "kbhbrew";', kilde)
        self.assertIn("const BREW_FIL_VERSION = 1;", kilde)
        self.assertIn('const BREW_STATUSER = ["active", "done", "discarded"];', kilde)
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "brew_store_v1.json"))
        self.assertEqual(fixture["format"], "kbh-brews")
        self.assertEqual(fixture["version"], 1)
        statuser = {b["status"] for b in fixture["items"]}
        self.assertEqual(statuser, {"active", "done", "discarded"})
        self.assertTrue(any(b["recipeId"] is None for b in fixture["items"]), "må dekke recipeId:null")

    def test_brew_store_v1_dekker_provenance_engine_version_og_equipment(self):
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "brew_store_v1.json"))
        for brew in fixture["items"]:
            self.assertIn("engineVersion", brew["snapshot"]["provenance"])
            self.assertIn("recipeSchemaVersion", brew["snapshot"]["provenance"])
            self.assertIn("masterdata", brew["snapshot"]["provenance"])
        self.assertTrue(
            any(b["snapshot"]["equipment"] is not None for b in fixture["items"]),
            "må dekke et brygg med utfylt snapshot.equipment",
        )

    def test_brew_store_v1_custom_ingrediens_fryses_ikke_inn_i_ingredients(self):
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "brew_store_v1.json"))
        done = next(b for b in fixture["items"] if b["status"] == "done")
        custom_malt_ider = [m["id"] for m in done["snapshot"]["recipe"]["malt"] if "custom" in m]
        self.assertTrue(custom_malt_ider)
        for cid in custom_malt_ider:
            self.assertNotIn(cid, done["snapshot"]["ingredients"]["malt"])

    def test_kbhbrew_v1_har_dagens_faktiske_filform_uten_lokal_brewid(self):
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "kbhbrew_v1.json"))
        self.assertEqual(fixture["format"], "kbhbrew")
        self.assertEqual(fixture["version"], 1)
        self.assertIn("originBrewId", fixture["brew"])
        self.assertNotIn("brewId", fixture["brew"])
        for felt in ("snapshot", "actuals", "sensing", "learning"):
            self.assertIn(felt, fixture["brew"])

    def test_pantry_store_v1_matcher_pantry_js_konstanter(self):
        kilde = _les(_PANTRY_JS)
        self.assertIn('return { format: "kbh-pantry", version: PANTRY_VERSION, items: [] };', kilde)
        self.assertIn("const PANTRY_VERSION = 1;", kilde)
        fixture = _last_json(os.path.join(_FIXTURE_ROOT, "web", "pantry_store_v1.json"))
        self.assertEqual(fixture["format"], "kbh-pantry")
        self.assertEqual(fixture["version"], 1)
        har_custom = [i for i in fixture["items"] if "custom" in i]
        har_normal = [i for i in fixture["items"] if "custom" not in i]
        self.assertTrue(har_custom, "må dekke custom pantry-item")
        self.assertTrue(har_normal, "må dekke normal (master-linket) pantry-item")

    def test_web_fixture_dokumentasjon_sier_legacy_ikke_canonical(self):
        # Kravet om at brew/.kbhbrew-fixturene tydelig skal si LEGACY /
        # EXISTING WEB MODEL og ikke gjøre modellen canonical, håndheves
        # via README (ikke inline i selve JSON-payloaden -- en
        # dokumentasjonsnøkkel i selve wrapperen ville avveket fra
        # dagens faktiske {format,version,items}-form).
        readme = _les(os.path.join(_FIXTURE_ROOT, "README.md"))
        self.assertIn("LEGACY", readme.upper())
        self.assertIn("canonical", readme.lower())


class TestIngenPrivateBrukerdataIFixtures(unittest.TestCase):
    """Krav 6: ingen fixture inneholder åpenbare private
    Kvernhaug-oppskrifts-/brukerdata."""

    def test_ingen_kjente_private_strenger_i_noen_fixture(self):
        for sti in _alle_fixture_json_filer():
            tekst = _les(sti)
            for streng in _KJENTE_PRIVATE_STRENGER:
                self.assertNotIn(streng, tekst, f"{sti} inneholder kjent privat streng {streng!r}")

    def test_data_pantry_json_aldri_lest_privat_fil_kun_eksisterer_sjekk(self):
        # Den EKTE private data/pantry.json skal aldri leses av noen test
        # her (filen er gitignoret/brukerspesifikk og finnes kanskje ikke
        # i det hele tatt i et annet miljø) -- kun bekreft at fixturene
        # ikke tilfeldigvis har fått nettopp dette filnavnet.
        self.assertFalse(
            os.path.exists(os.path.join(_FIXTURE_ROOT, "app", "pantry.json")),
            "Skal hete pantry_v1.json (frosset fixture), ikke pantry.json",
        )

    def test_pantry_v1_er_frosset_kopi_ikke_data_pantry_example_selv(self):
        # data/pantry.example.json (QA-korrigert punkt 2): forblir det
        # LEVENDE eksempelet og skal IKKE endres av dette oppdraget.
        # tests/fixtures/legacy/app/pantry_v1.json er den FROSNE
        # Phase 0-fixturen -- egen fil, verifisert mot fast hash i
        # TestAppRecipeFixturerHarLegacyShape, ikke mot den levende filen.
        self.assertTrue(os.path.exists(os.path.join(_ROOT, "data", "pantry.example.json")))
        self.assertTrue(os.path.exists(os.path.join(_FIXTURE_ROOT, "app", "pantry_v1.json")))


class TestScopeGuardIngenUtilsiktedeNyeFixtureFiler(unittest.TestCase):
    """Bekrefter at oppdragets eksplisitte IKKE-OPPRETT-liste er
    overholdt (app_equipment.json, web_equipment_store.json,
    humle_lager-fixture)."""

    def test_ingen_equipment_eller_humle_lager_fixtures_opprettet(self):
        alle = [os.path.basename(p) for p in _alle_fixture_json_filer()]
        for forbudt in ("app_equipment.json", "web_equipment_store.json", "humle_lager.json"):
            self.assertNotIn(forbudt, alle)


if __name__ == "__main__":
    unittest.main()
