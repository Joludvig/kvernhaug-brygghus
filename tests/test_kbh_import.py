"""
PRI 2C1 -- tester for modules/kbh_import.py, App sin rene
`.kbhrecipe` V1-leser (speilbildet av tests/test_kbh_contract.py, som
tester writeren). Ren Python, ingen Streamlit, ingen disk-I/O, ingen
session_state.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import os
import unittest

from modules.kbh_import import (
    parse_kbhrecipe_json,
    UgyldigKbhrecipeForImport,
    KATEGORI_INVALID_JSON,
    KATEGORI_INVALID_ENVELOPE,
    KATEGORI_UNSUPPORTED_VERSION,
    KATEGORI_UNSUPPORTED_RECIPE_SCHEMA,
    KATEGORI_INVALID_PAYLOAD,
    KATEGORI_UNKNOWN_INGREDIENT_IDS,
    KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT,
    KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE,
    KATEGORI_UNSUPPORTED_PROCESS,
)
from modules.recipe import bygg_recipe_object
from modules.kbh_contract import recipe_to_kbhrecipe_payload, bygg_kbhrecipe_konvolutt
from modules.process_profiles import hent_standardprofil, bygg_egendefinert_profil

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES_DIR = os.path.join(_REPO_ROOT, "tests", "fixtures", "legacy", "kbhrecipe")

# ─── Masterdata ─────────────────────────────────────────────────────────
# Reelle master-databaser (samme mønster som tests/test_process_profiles.py)
# for fixture-baserte tester og roundtrip -- fixturenes ID-er er ekte,
# eksisterende oppføringer, verifisert direkte mot filene (se
# PRI 2C1-rapporten). En liten, egen ad hoc-database for de synteiske
# payload-testene under, slik at de ikke er avhengige av at ekte
# masterdata forblir uendret over tid.


def _last_ekte_db(filnavn):
    with open(os.path.join(_REPO_ROOT, "data", filnavn), encoding="utf-8") as f:
        return json.load(f)


_EKTE_MALT_DB = _last_ekte_db("master_malt.json")
_EKTE_HUMLE_DB = _last_ekte_db("master_humle_v2.json")
_EKTE_GJAER_DB = _last_ekte_db("master_gjaer_v2.json")

_MALT_DB = {"weyermann_pilsner": {}, "vienna": {}}
_HUMLE_DB = {"east_kent_goldings": {}, "magnum": {}}
_GJAER_DB = {"safale_us_05": {}}


def _last_fixture(navn):
    with open(os.path.join(_FIXTURES_DIR, f"{navn}.json"), encoding="utf-8") as f:
        return f.read()


def _payload(**overrides):
    base = {
        "recipeSchemaVersion": 1,
        "navn": "Testbrygg",
        "volum": 20.0,
        "effektivitet": 68,
        "malt": [{"id": "weyermann_pilsner", "mengde": 4.0}],
        "humle": [{"id": "east_kent_goldings", "gram": 20, "tid": 60}],
    }
    base.update(overrides)
    return base


def _envelope_tekst(payload, version=1, format_="kbhrecipe"):
    return json.dumps({
        "format": format_,
        "version": version,
        "exportedAt": "2026-09-01T00:00:00Z",
        "generator": "test",
        "recipe": payload,
    })


def _parse(payload_overrides=None, envelope_kwargs=None, malt_db=None, humle_db=None, gjaer_db=None):
    payload = _payload(**(payload_overrides or {}))
    tekst = _envelope_tekst(payload, **(envelope_kwargs or {}))
    return parse_kbhrecipe_json(
        tekst,
        malt_db if malt_db is not None else _MALT_DB,
        humle_db if humle_db is not None else _HUMLE_DB,
        gjaer_db if gjaer_db is not None else _GJAER_DB,
    )


def _forvent_avvist(kategori, payload_overrides=None, envelope_kwargs=None, tekst=None, **db_kwargs):
    """Kaller parseren og krever at den kaster UgyldigKbhrecipeForImport
    med nøyaktig `kategori` -- returnerer selve unntaket slik at testen
    kan inspisere `melding`/ekstra attributter (f.eks. unknown_malt)."""
    try:
        if tekst is not None:
            parse_kbhrecipe_json(
                tekst,
                db_kwargs.get("malt_db", _MALT_DB),
                db_kwargs.get("humle_db", _HUMLE_DB),
                db_kwargs.get("gjaer_db", _GJAER_DB),
            )
        else:
            _parse(payload_overrides, envelope_kwargs, **db_kwargs)
    except UgyldigKbhrecipeForImport as e:
        if e.kategori != kategori:
            raise AssertionError(f"forventet kategori {kategori!r}, fikk {e.kategori!r}: {e.melding}") from e
        return e
    raise AssertionError(f"forventet UgyldigKbhrecipeForImport (kategori {kategori!r}), men parsingen lyktes.")


# ─── 1-3: legacy V1-fixtures ────────────────────────────────────────────

class TestFixtureParsing(unittest.TestCase):
    def test_1_minimal_fixture_parses(self):
        res = parse_kbhrecipe_json(_last_fixture("minimal"), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        self.assertEqual(res["recipe"]["name"], "Testbrygg Minimal (syntetisk fixture)")
        self.assertEqual(res["recipe"]["process_profile"], None)

    def test_2_full_fixture_er_gyldig_historisk_evidence_men_avvises_for_import(self):
        # KBHR-020 -- en frosset legacy-fixture er historisk
        # compatibility-evidence (den beviser at Web/en tidligere writer
        # faktisk produserte denne teksten), IKKE en automatisk garanti
        # om at ENHVER fremtidig leser trygt kan importere den.
        # "full"-fixturens prosess (process_id="enkel_infusjon") har ETT
        # meskesteg (66C/60min "Hovedmesk"), mens Appens kanoniske
        # enkel_infusjon i dag har TO steg (også en mashout-fase,
        # 78C/5min) -- en REELL, bevist strukturell avvikelse (se PRI
        # 2C1-rapporten).
        #
        # PR #3 Chief review-historikk: et tidligere PR #3-fikseforsøk
        # (commit `ce4ab4c`, siden reversert) importerte denne typen
        # avvik losslessly som en "egendefinert" App-prosess (owner
        # decision option A). Ved re-review viste det seg at owner
        # faktisk hadde valgt **option B**: behold streng avvisning, og
        # dokumenter eksplisitt at App sin .kbhrecipe-prosessimport er
        # BEVISST safe-subset-only inntil en separat, senere avgrenset
        # oppgave lukker gapet losslessly (se
        # docs/development/CORE_KBHRECIPE_V1.md §13). Denne testen er
        # derfor tilbake til å bevise AVVISNING -- fixturen røres IKKE,
        # og process equality-checken i modules/kbh_import.py svekkes
        # IKKE for å få denne ene, kjente gamle filen til å bestå.
        e = _forvent_avvist(KATEGORI_UNSUPPORTED_PROCESS, tekst=_last_fixture("full"),
                             malt_db=_EKTE_MALT_DB, humle_db=_EKTE_HUMLE_DB, gjaer_db=_EKTE_GJAER_DB)
        self.assertEqual(e.kategori, KATEGORI_UNSUPPORTED_PROCESS)
        self.assertIn("enkel_infusjon", e.melding)

    def test_2b_full_fixture_uten_prosess_parses_ellers_korrekt(self):
        # Isolerer resten av "full"-fixturens innhold fra prosess-avviket
        # over: fjerner KUN `prosess` fra en kopi (fixturfilen på disk
        # røres aldri) og bekrefter at malt/humle/gjaerId/bryggerStil/vann
        # importeres korrekt -- se også test_11/test_12.
        raw = json.loads(_last_fixture("full"))
        del raw["recipe"]["prosess"]
        res = parse_kbhrecipe_json(json.dumps(raw), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        r = res["recipe"]
        self.assertEqual(r["name"], "Testbrygg Full (syntetisk fixture)")
        self.assertEqual(r["brygger_stil"], "Testbryggerens egen stil (syntetisk)")
        self.assertEqual(r["yeast"], "lalbrew_diamond_lager")
        self.assertEqual([m["id"] for m in r["malts"]], ["bohemian_pilsner_floor", "vienna"])
        self.assertEqual([h["id"] for h in r["hops"]], ["east_kent_goldings", "amarillo"])
        self.assertIsNotNone(r["water_source_profile"])
        self.assertIsNotNone(r["water_measurements"])

    def test_3_partial_water_fixture_parses(self):
        res = parse_kbhrecipe_json(_last_fixture("partial_water"), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        r = res["recipe"]
        self.assertEqual(r["name"], "Testbrygg Partial Water (syntetisk fixture)")
        self.assertIsNone(r["water_source_profile"])
        self.assertIsNotNone(r["water_measurements"])


# ─── 4-10: feltmapping ──────────────────────────────────────────────────

class TestFeltmapping(unittest.TestCase):
    def test_4_navn_mapping(self):
        res = _parse({"navn": "Mitt Brygg"})
        self.assertEqual(res["recipe"]["name"], "Mitt Brygg")

    def test_5_volum_mapping(self):
        res = _parse({"volum": 27.5})
        self.assertEqual(res["recipe"]["batch_size"], 27.5)

    def test_6_effektivitet_68_blir_068(self):
        res = _parse({"effektivitet": 68})
        self.assertEqual(res["recipe"]["efficiency"], 0.68)

    def test_7_malt_rows(self):
        res = _parse({"malt": [
            {"id": "weyermann_pilsner", "mengde": 4.0},
            {"id": "vienna", "mengde": 1.2},
        ]})
        self.assertEqual(res["recipe"]["malts"], [
            {"id": "weyermann_pilsner", "mengde": 4.0},
            {"id": "vienna", "mengde": 1.2},
        ])

    def test_8_hop_rows(self):
        res = _parse({"humle": [{"id": "east_kent_goldings", "gram": 15.0, "tid": 10}]})
        self.assertEqual(res["recipe"]["hops"], [{"id": "east_kent_goldings", "gram": 15.0, "tid": 10}])

    def test_9_gjaerid_mapping(self):
        res = _parse({"humle": [], "gjaerId": "safale_us_05"})
        self.assertEqual(res["recipe"]["yeast"], "safale_us_05")

    def test_9b_manglende_gjaerid_gir_none_ikke_default(self):
        res = _parse({"humle": []})
        self.assertIsNone(res["recipe"]["yeast"])

    def test_10_bryggerstil_mapping(self):
        res = _parse({"bryggerStil": "Husets egen IPA"})
        self.assertEqual(res["recipe"]["brygger_stil"], "Husets egen IPA")

    def test_10b_manglende_bryggerstil_gir_tom_streng(self):
        res = _parse({})
        self.assertEqual(res["recipe"]["brygger_stil"], "")


# ─── 11-12: prosess og vann (positive) ──────────────────────────────────

class TestProsessOgVannPositiv(unittest.TestCase):
    def test_11a_kjent_process_id_med_kanonisk_profil_godtas(self):
        kanonisk = hent_standardprofil("hochkurz")
        res = _parse({"prosess": kanonisk})
        self.assertEqual(res["recipe"]["process_profile"]["process_id"], "hochkurz")
        self.assertEqual(res["recipe"]["process_profile"]["mash_steps"], kanonisk["mash_steps"])

    def test_11b_egendefinert_med_egne_steg_godtas_uendret(self):
        egen = bygg_egendefinert_profil("Min egen prosess", [
            {"temperatur": 64.0, "varighet": 45, "stegtype": "infusjon", "kommentar": ""},
        ])
        res = _parse({"prosess": egen})
        self.assertEqual(res["recipe"]["process_profile"]["mash_steps"], egen["mash_steps"])

    def test_11c_manglende_prosess_gir_none(self):
        res = _parse({})
        self.assertIsNone(res["recipe"]["process_profile"])

    def test_12_water_fields_mapping(self):
        vann = {
            "kilde": {"water_id": "x", "ca": 20.0},
            "maal": {"target_id": "y", "ca_min": 50},
            "behandling": {"salter": [{"id": "gips", "gram": 4.0}]},
            "maalinger": {"maalt_mash_ph": 5.3},
        }
        res = _parse({"vann": vann})
        r = res["recipe"]
        self.assertEqual(r["water_source_profile"], vann["kilde"])
        self.assertEqual(r["water_target_profile"], vann["maal"])
        self.assertEqual(r["water_treatment"], vann["behandling"])
        self.assertEqual(r["water_measurements"], vann["maalinger"])

    def test_12b_deep_copy_ikke_samme_objekt(self):
        vann = {"kilde": {"ca": 20.0}}
        res = _parse({"vann": vann})
        self.assertIsNot(res["recipe"]["water_source_profile"], vann["kilde"])

    def test_12c_manglende_vann_gir_alle_none(self):
        res = _parse({})
        r = res["recipe"]
        self.assertIsNone(r["water_source_profile"])
        self.assertIsNone(r["water_target_profile"])
        self.assertIsNone(r["water_treatment"])
        self.assertIsNone(r["water_measurements"])


# ─── 13-15: passthrough og ingen beregnet state ─────────────────────────

class TestPassthroughOgIngenBeregnetState(unittest.TestCase):
    def test_13_web_metadata_havner_i_passthrough(self):
        res = _parse({
            "brygger": "Ola Nordmann", "bryggeri": "Kvernhaug",
            "notater": "Litt ekstra bittert denne gangen",
            "valgtStil": "21A American IPA",
        })
        p = res["passthrough"]
        self.assertEqual(p["brygger"], "Ola Nordmann")
        self.assertEqual(p["bryggeri"], "Kvernhaug")
        self.assertEqual(p["notater"], "Litt ekstra bittert denne gangen")
        self.assertEqual(p["valgtStil"], "21A American IPA")
        # KBHR-015 -- ingen mapping til brygger_stil.
        self.assertEqual(res["recipe"]["brygger_stil"], "")

    def test_14_ukjent_fremtidig_toppnivafelt_havner_i_passthrough(self):
        res = _parse({"fermentasjonsprofil": {"steg": [{"temp": 18, "dager": 7}]}})
        self.assertEqual(res["passthrough"]["fermentasjonsprofil"], {"steg": [{"temp": 18, "dager": 7}]})

    def test_15_stats_og_flavor_profile_blir_aldri_native_eller_passthrough(self):
        res = _parse({"stats": {"og": 1.05, "ibu": 30}, "flavor_profile": {"malt": 5}})
        self.assertNotIn("stats", res["recipe"])
        self.assertNotIn("flavor_profile", res["recipe"])
        self.assertNotIn("stats", res["passthrough"])
        self.assertNotIn("flavor_profile", res["passthrough"])

    def test_15b_recipeid_blir_aldri_native_eller_passthrough(self):
        res = _parse({"recipeId": "LOKAL-ID-SKAL-ALDRI-OVERLEVE"})
        self.assertNotIn("recipeId", res["recipe"])
        self.assertNotIn("recipeId", res["passthrough"])
        self.assertNotIn("LOKAL-ID-SKAL-ALDRI-OVERLEVE", json.dumps(res))


# ─── 16-19: envelope-avvisning ──────────────────────────────────────────

class TestEnvelopeNegativ(unittest.TestCase):
    def test_16_invalid_json(self):
        e = _forvent_avvist(KATEGORI_INVALID_JSON, tekst="{ ikke gyldig json")
        self.assertEqual(e.kategori, KATEGORI_INVALID_JSON)

    def test_17_feil_format(self):
        _forvent_avvist(KATEGORI_INVALID_ENVELOPE, envelope_kwargs={"format_": "noe-annet"})

    def test_18_envelope_version_ikke_1(self):
        for v in (2, 0, 0.5, -1):
            _forvent_avvist(KATEGORI_UNSUPPORTED_VERSION, envelope_kwargs={"version": v})

    def test_19_manglende_recipe(self):
        tekst = json.dumps({"format": "kbhrecipe", "version": 1, "exportedAt": "x", "generator": "y"})
        _forvent_avvist(KATEGORI_INVALID_ENVELOPE, tekst=tekst)

    def test_wrapperless_legacy_raa_json_avvises(self):
        # OPPGAVE B -- App-importereren gjenskaper IKKE Web sin
        # wrapperløse legacy-fallback (se modulens docstring/PRI 2C1-
        # rapporten punkt 4).
        tekst = json.dumps({"navn": "Gammel eksport uten wrapper", "malt": [], "humle": [], "volum": 20, "effektivitet": 75})
        _forvent_avvist(KATEGORI_INVALID_ENVELOPE, tekst=tekst)


# ─── 20-21: recipeSchemaVersion ──────────────────────────────────────────

class TestRecipeSchemaVersionNegativ(unittest.TestCase):
    def test_20_manglende_recipeschemaversion(self):
        payload = _payload()
        del payload["recipeSchemaVersion"]
        _forvent_avvist(KATEGORI_UNSUPPORTED_RECIPE_SCHEMA, tekst=_envelope_tekst(payload))

    def test_21_recipeschemaversion_ikke_1(self):
        for v in (2, 0, "1"):
            _forvent_avvist(KATEGORI_UNSUPPORTED_RECIPE_SCHEMA, payload_overrides={"recipeSchemaVersion": v})


# ─── 22-26: payload-feltvalidering ───────────────────────────────────────

class TestPayloadFeltNegativ(unittest.TestCase):
    def test_22_ugyldig_navn(self):
        for v in ("", "   ", None, 42):
            _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"navn": v})

    def test_23_ugyldig_volum(self):
        for v in (0, -5, "20", None):
            _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"volum": v})

    def test_24_ugyldig_effektivitet(self):
        for v in (0, -10, "68", None):
            _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"effektivitet": v})

    def test_25_malt_ikke_liste(self):
        _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"malt": {"id": "x"}})

    def test_26_humle_ikke_liste(self):
        _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"humle": "ikke-en-liste"})


# ─── 27-28: malformerte ingrediensrader ─────────────────────────────────

class TestMalformerteRader(unittest.TestCase):
    def test_27_malformert_malt_rad(self):
        for rad in ({"mengde": 4.0}, {"id": ""}, {"id": "weyermann_pilsner", "mengde": 0}, {"id": "weyermann_pilsner", "mengde": "fire"}, "ikke-et-objekt"):
            _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"malt": [rad]})

    def test_28_malformert_hop_rad(self):
        for rad in ({"gram": 20, "tid": 60}, {"id": "east_kent_goldings", "gram": -1, "tid": 60},
                    {"id": "east_kent_goldings", "gram": 20, "tid": -1}, {"id": "east_kent_goldings", "gram": "tjue", "tid": 60}):
            _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"humle": [rad]})


# ─── 29-32: ukjente kanoniske ID-er ──────────────────────────────────────

class TestUkjenteIder(unittest.TestCase):
    def test_29_ukjent_malt_id(self):
        e = _forvent_avvist(KATEGORI_UNKNOWN_INGREDIENT_IDS, payload_overrides={"malt": [{"id": "helt-ukjent-malt", "mengde": 4.0}]})
        self.assertEqual(e.unknown_malt, ["helt-ukjent-malt"])

    def test_30_ukjent_hop_id(self):
        e = _forvent_avvist(KATEGORI_UNKNOWN_INGREDIENT_IDS, payload_overrides={"humle": [{"id": "helt-ukjent-humle", "gram": 20, "tid": 60}]})
        self.assertEqual(e.unknown_hops, ["helt-ukjent-humle"])

    def test_31_ukjent_gjaer_id(self):
        e = _forvent_avvist(KATEGORI_UNKNOWN_INGREDIENT_IDS, payload_overrides={"humle": [], "gjaerId": "helt-ukjent-gjaer"})
        self.assertEqual(e.unknown_yeast, ["helt-ukjent-gjaer"])

    def test_32_flere_ukjente_rapporteres_samlet(self):
        e = _forvent_avvist(
            KATEGORI_UNKNOWN_INGREDIENT_IDS,
            payload_overrides={
                "malt": [{"id": "ukjent-malt-1", "mengde": 4.0}],
                "humle": [{"id": "ukjent-humle-1", "gram": 20, "tid": 60}],
                "gjaerId": "ukjent-gjaer-1",
            },
        )
        self.assertEqual(e.unknown_malt, ["ukjent-malt-1"])
        self.assertEqual(e.unknown_hops, ["ukjent-humle-1"])
        self.assertEqual(e.unknown_yeast, ["ukjent-gjaer-1"])
        self.assertIn("unknown malt", e.melding)
        self.assertIn("unknown hops", e.melding)
        self.assertIn("unknown yeast", e.melding)

    def test_ingen_fuzzy_matching_naer_treff_avvises_ogsaa(self):
        # "waymann_pilsner" (skrivefeil) ligner "weyermann_pilsner", men
        # skal IKKE fuzzy-matches -- avvist som ukjent, punktum.
        e = _forvent_avvist(KATEGORI_UNKNOWN_INGREDIENT_IDS, payload_overrides={"malt": [{"id": "waymann_pilsner", "mengde": 4.0}]})
        self.assertEqual(e.unknown_malt, ["waymann_pilsner"])


# ─── 33-37: custom/override-avvisning ────────────────────────────────────

class TestCustomOgOverrideAvvisning(unittest.TestCase):
    def test_33_custom_malt_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT, payload_overrides={
            "malt": [{"id": "egen_malt_1", "mengde": 0.5, "custom": {"navn": "Hjemmerøkt", "ebc": 30}}],
        })

    def test_34_custom_hop_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT, payload_overrides={
            "humle": [{"id": "egen_humle_1", "gram": 20, "tid": 5, "custom": {"navn": "Nabohumle", "alfa": 7.5}}],
        })

    def test_35_gjaercustom_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE, payload_overrides={
            "humle": [], "gjaerCustom": {"navn": "Gårdsgjær", "attenuation": 0.78},
        })

    def test_35b_tom_gjaercustom_avvises_ikke(self):
        res = _parse({"humle": [], "gjaerCustom": {}})
        self.assertIsNone(res["recipe"]["yeast"])

    def test_36_alfaoverride_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE, payload_overrides={
            "humle": [{"id": "east_kent_goldings", "gram": 20, "tid": 60, "alfaOverride": 6.5}],
        })

    def test_36b_alfaoverride_null_avvises_ikke(self):
        res = _parse({"humle": [{"id": "east_kent_goldings", "gram": 20, "tid": 60, "alfaOverride": None}]})
        self.assertEqual(res["recipe"]["hops"][0]["id"], "east_kent_goldings")

    def test_37_attenuationoverride_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE, payload_overrides={
            "humle": [], "attenuationOverride": 78,
        })

    def test_37b_attenuationoverride_null_avvises_ikke(self):
        res = _parse({"humle": [], "attenuationOverride": None})
        self.assertIsNone(res["recipe"]["yeast"])


# ─── 38-39: prosess-avvisning ─────────────────────────────────────────────

class TestProsessAvvisning(unittest.TestCase):
    def test_38_ukjent_process_id_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_PROCESS, payload_overrides={
            "prosess": {"process_id": "helt-ukjent-fremtidig-prosess", "mash_steps": []},
        })

    def test_39_kjent_process_id_med_avvikende_steg_avvises(self):
        # PR #3 Chief review-historikk: et tidligere fikseforsøk i denne
        # PR-en (commit `ce4ab4c`) gjorde dette til en POSITIV test
        # (owner decision option A -- lossless import som "egendefinert").
        # Ved re-review viste det seg owner faktisk hadde valgt option B
        # (behold streng avvisning, dokumenter safe-subset-only), og A
        # ble reversert. Denne testen er derfor tilbake til sin
        # opprinnelige form: en kjent standardprofil med avvikende
        # meskesteg AVVISES, uendret siden før PR #3.
        avvikende = hent_standardprofil("enkel_infusjon")
        avvikende["mash_steps"] = [{"temperatur": 64.0, "varighet": 45, "stegtype": "infusjon", "kommentar": "avvikende"}]
        _forvent_avvist(KATEGORI_UNSUPPORTED_PROCESS, payload_overrides={"prosess": avvikende})


# ─── 40: bool/NaN-edge cases ──────────────────────────────────────────────

class TestBoolNanEdgeCases(unittest.TestCase):
    def test_40a_bool_recipeschemaversion_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_RECIPE_SCHEMA, payload_overrides={"recipeSchemaVersion": True})

    def test_40b_bool_envelope_version_avvises(self):
        _forvent_avvist(KATEGORI_UNSUPPORTED_VERSION, envelope_kwargs={"version": True})

    def test_40c_bool_volum_avvises(self):
        _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={"volum": True})

    def test_40d_nan_i_raatekst_avvises_som_invalid_json(self):
        # json.loads() godtar NaN som Python-utvidelse med mindre den
        # eksplisitt avvises (se modules/kbh_import.py::_avvis_json_konstant).
        raatekst = '{"format":"kbhrecipe","version":1,"exportedAt":"x","generator":"y","recipe":{"recipeSchemaVersion":1,"navn":"X","volum":NaN,"effektivitet":68,"malt":[],"humle":[]}}'
        _forvent_avvist(KATEGORI_INVALID_JSON, tekst=raatekst)

    def test_40e_bool_alfaoverride_er_malformert_ikke_stille_override(self):
        _forvent_avvist(KATEGORI_INVALID_PAYLOAD, payload_overrides={
            "humle": [{"id": "east_kent_goldings", "gram": 20, "tid": 60, "alfaOverride": True}],
        })


# ─── Roundtrip: App native -> export -> import -> native ────────────────

class TestRoundtrip(unittest.TestCase):
    """Bruker den EKTE App-writeren (modules/kbh_contract.py) og den nye
    leseren sammen -- beviser lossless roundtrip for alle semantiske felt
    som skal overleve (stats/flavor_profile er lovlig fraværende/
    gjenskapes senere av App, se OPPGAVE I)."""

    def test_roundtrip_full_recipe_lossless(self):
        prosess = hent_standardprofil("hochkurz")  # kanonisk -- garantert import-godkjent
        original = bygg_recipe_object(
            navn="Roundtrip Test",
            batch_size=23.0,
            efficiency=0.68,
            malts=[
                {"id": "bohemian_pilsner_floor", "mengde": 4.0},
                {"id": "vienna", "mengde": 1.5},
            ],
            hops=[{"id": "east_kent_goldings", "gram": 40.0, "tid": 60}],
            yeast="lalbrew_diamond_lager",
            og=1.050, fg=1.012, abv=5.0, ibu=30, ebc=12, flavor_profile={"malt": 5},
            brygger_stil="Husets egen stil",
            process_profile=prosess,
            water_source_profile={"water_id": "x", "ca": 20.0},
            water_target_profile={"target_id": "y", "ca_min": 50},
            water_treatment={"salter": [{"id": "gips", "gram": 4.0}]},
            water_measurements={"maalt_mash_ph": 5.3},
        )

        konvolutt = bygg_kbhrecipe_konvolutt(original, "2026-09-01T00:00:00Z")
        tekst = json.dumps(konvolutt)

        importert = parse_kbhrecipe_json(tekst, _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        r = importert["recipe"]

        self.assertEqual(r["name"], original["name"])
        self.assertEqual(r["batch_size"], original["batch_size"])
        self.assertAlmostEqual(r["efficiency"], original["efficiency"], places=9)
        self.assertEqual(r["brygger_stil"], original["brygger_stil"])
        self.assertEqual(r["malts"], original["malts"])
        self.assertEqual(r["hops"], original["hops"])
        self.assertEqual(r["yeast"], original["yeast"])
        self.assertEqual(r["process_profile"]["process_id"], prosess["process_id"])
        self.assertEqual(r["process_profile"]["mash_steps"], prosess["mash_steps"])
        self.assertEqual(r["water_source_profile"], original["water_source_profile"])
        self.assertEqual(r["water_target_profile"], original["water_target_profile"])
        self.assertEqual(r["water_treatment"], original["water_treatment"])
        self.assertEqual(r["water_measurements"], original["water_measurements"])

        # stats/flavor_profile skal IKKE finnes i importresultatet -- de
        # eksporteres aldri i utgangspunktet (kbh_contract.py-whitelisten),
        # og ville uansett aldri blitt behandlet som kildedata (test 15).
        self.assertNotIn("stats", r)
        self.assertNotIn("flavor_profile", r)
        self.assertEqual(importert["passthrough"], {})

    def test_roundtrip_egendefinert_prosess_lossless(self):
        egen = bygg_egendefinert_profil("Min egen", [
            {"temperatur": 65.0, "varighet": 50, "stegtype": "infusjon", "kommentar": "test"},
        ])
        original = bygg_recipe_object(
            navn="Roundtrip Egendefinert", batch_size=20.0, efficiency=0.72,
            malts=[{"id": "weyermann_pilsner", "mengde": 4.0}], hops=[], yeast="safale_us_05",
            og=1.045, fg=1.010, abv=4.5, ibu=0, ebc=8, flavor_profile={},
            process_profile=egen,
        )
        konvolutt = bygg_kbhrecipe_konvolutt(original, "2026-09-01T00:00:00Z")
        importert = parse_kbhrecipe_json(json.dumps(konvolutt), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        self.assertEqual(importert["recipe"]["process_profile"]["mash_steps"], egen["mash_steps"])

    def test_roundtrip_minimal_uten_valgfrie_felt(self):
        original = bygg_recipe_object(
            navn="Roundtrip Minimal", batch_size=20.0, efficiency=0.75,
            malts=[{"id": "weyermann_pilsner", "mengde": 4.0}], hops=[], yeast=None,
            og=1.040, fg=1.010, abv=4.0, ibu=0, ebc=8, flavor_profile={},
        )
        # yeast=None -- App writer krever ikke yeast (gjaerId skrives kun
        # hvis truthy, se modules/kbh_contract.py).
        konvolutt = bygg_kbhrecipe_konvolutt(original, "2026-09-01T00:00:00Z")
        importert = parse_kbhrecipe_json(json.dumps(konvolutt), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB)
        r = importert["recipe"]
        self.assertIsNone(r["yeast"])
        self.assertIsNone(r["process_profile"])
        self.assertIsNone(r["water_source_profile"])
        self.assertEqual(r["brygger_stil"], "")


# ─── Full positiv import-case: writer -> augmentert payload -> reader ───

class TestFullPositivImportCase(unittest.TestCase):
    """QA-korreksjon (KBHR-020), OPPGAVE 2 -- ÉN samlet, positiv
    import-test som dekker alle feltgruppene samtidig (ikke bare
    isolert, ett og ett, slik resten av filen gjør). Bygget via den
    EKTE App-writeren (modules/kbh_contract.py) akkurat som
    TestRoundtrip over, men med payloaden deretter augmentert med
    metadata en ekte fremmed/Web-generert .kbhrecipe-fil kan inneholde
    (brygger/bryggeri/notater/valgtStil, §3) -- disse skrives ikke av
    App sin egen writer, men er lovlig V1-innhold enhver leser må
    bevare opakt (§6/KBHR-011/KBHR-014). Dette er derfor samtidig et
    writer->reader-kompatibilitetsbevis OG et passthrough-bevis, i én
    sammenhengende, realistisk fil."""

    def test_41_full_positiv_import_med_alle_feltgrupper_og_passthrough(self):
        prosess = hent_standardprofil("enkel_dekoksjon")  # kanonisk kjent profil
        original = bygg_recipe_object(
            navn="QA Full Positiv Import",
            batch_size=25.0,
            efficiency=0.71,
            malts=[
                {"id": "weyermann_pilsner", "mengde": 4.5},
                {"id": "vienna", "mengde": 1.0},
                {"id": "bohemian_pilsner_floor", "mengde": 0.5},
            ],
            hops=[
                {"id": "east_kent_goldings", "gram": 25.0, "tid": 60},
                {"id": "amarillo", "gram": 15.0, "tid": 10},
            ],
            yeast="saflager_w3470",
            og=1.052, fg=1.011, abv=5.4, ibu=28, ebc=9, flavor_profile={"malt": 4},
            brygger_stil="QA Testbryggeriets egen stil",
            process_profile=prosess,
            water_source_profile={"water_id": "oslo", "ca": 22.0},
            water_target_profile={"target_id": "pilsner", "ca_min": 50},
            water_treatment={"salter": [{"id": "gips", "gram": 3.0}]},
            water_measurements={"maalt_mash_ph": 5.4},
        )

        konvolutt = bygg_kbhrecipe_konvolutt(original, "2026-09-01T00:00:00Z")
        # Augmenter med metadata App sin egen writer ikke skriver, men
        # som en ekte, fremmed .kbhrecipe-fil (f.eks. Web-eksportert, så
        # senere håndredigert eller re-eksportert) lovlig kan inneholde
        # -- App-leseren skal bevare denne opakt, uendret (§6/§13).
        konvolutt["recipe"]["brygger"] = "Ola QA"
        konvolutt["recipe"]["bryggeri"] = "QA Bryggeri"
        konvolutt["recipe"]["notater"] = "Traff godt denne gangen"
        konvolutt["recipe"]["valgtStil"] = "5D Czech Pilsner"

        importert = parse_kbhrecipe_json(
            json.dumps(konvolutt), _EKTE_MALT_DB, _EKTE_HUMLE_DB, _EKTE_GJAER_DB,
        )
        r = importert["recipe"]

        self.assertEqual(r["name"], "QA Full Positiv Import")
        self.assertEqual(r["batch_size"], 25.0)
        self.assertAlmostEqual(r["efficiency"], 0.71, places=9)
        self.assertEqual(r["brygger_stil"], "QA Testbryggeriets egen stil")
        self.assertEqual(r["malts"], [
            {"id": "weyermann_pilsner", "mengde": 4.5},
            {"id": "vienna", "mengde": 1.0},
            {"id": "bohemian_pilsner_floor", "mengde": 0.5},
        ])
        self.assertEqual(r["hops"], [
            {"id": "east_kent_goldings", "gram": 25.0, "tid": 60},
            {"id": "amarillo", "gram": 15.0, "tid": 10},
        ])
        self.assertEqual(r["yeast"], "saflager_w3470")
        self.assertEqual(r["process_profile"]["process_id"], "enkel_dekoksjon")
        self.assertEqual(r["process_profile"]["mash_steps"], prosess["mash_steps"])
        self.assertEqual(r["water_source_profile"], {"water_id": "oslo", "ca": 22.0})
        self.assertEqual(r["water_target_profile"], {"target_id": "pilsner", "ca_min": 50})
        self.assertEqual(r["water_treatment"], {"salter": [{"id": "gips", "gram": 3.0}]})
        self.assertEqual(r["water_measurements"], {"maalt_mash_ph": 5.4})

        # Beregnet state skal aldri gjenoppstå som om det var kildedata.
        self.assertNotIn("stats", r)
        self.assertNotIn("flavor_profile", r)

        # Relevant passthrough-metadata bevart opakt, uendret.
        p = importert["passthrough"]
        self.assertEqual(p["brygger"], "Ola QA")
        self.assertEqual(p["bryggeri"], "QA Bryggeri")
        self.assertEqual(p["notater"], "Traff godt denne gangen")
        self.assertEqual(p["valgtStil"], "5D Czech Pilsner")
        # KBHR-015 -- valgtStil har INGEN native slot; ingen mapping til
        # brygger_stil (som fortsatt er writerens egen "QA Testbryggeriets
        # egen stil", uendret av valgtStil-passthrough-verdien).
        self.assertEqual(r["brygger_stil"], "QA Testbryggeriets egen stil")


if __name__ == "__main__":
    unittest.main()
