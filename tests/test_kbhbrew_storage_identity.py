"""
PRI 3B1 (issue #24) -- persistens-/identitetstester for
modules/kbhbrew_storage.py (docs/development/CORE_KBHBREW_V1.md).

Dekker (issue #24 Section 7 "Identity/persistence"):
  - lokal identitet/origin-semantikk matcher Active V1;
  - duplikat-origin overskriver/duplikatoppretter ALDRI stille;
  - svak recipe-lenke er ALDRI autoritativ historie;
  - ny Core V1-brew-lagring er uavhengig av legacy-flate loggfiler
    (modules/recipe_storage.py, recipes/_logs/).

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen (samme mønster
som tests/test_brewlog_logs_namespace.py).

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_storage_identity -b
"""
import json
import os
import tempfile
import unittest
from unittest import mock

from modules.recipe import bygg_recipe_object
import modules.recipe_storage as recipe_storage
import modules.kbhbrew_storage as kbhbrew_storage
from modules.kbhbrew import bygg_kbhbrew_konvolutt, bygg_ny_brew


def _recipe(navn="Identitetstest"):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    )


def _dbs():
    return (
        {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}},
        {},
        {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}},
    )


class _IsolertRecipeMappeTestCase(unittest.TestCase):
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

    def _mappe(self):
        return self._tmpdir.name

    def _kbhbrew_mappe(self):
        return os.path.join(self._mappe(), "_kbhbrew")

    def _kbhbrew_filer(self):
        mappe = self._kbhbrew_mappe()
        return set(os.listdir(mappe)) if os.path.isdir(mappe) else set()


class TestLocalIdentityMatchesActiveV1(_IsolertRecipeMappeTestCase):
    def test_new_brew_has_origin_equal_to_brew_id_and_active_status(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = kbhbrew_storage.opprett_og_lagre_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, None, {},
        )
        self.assertIsNotNone(brew)
        self.assertEqual(brew["originBrewId"], brew["brewId"])
        self.assertEqual(brew["status"], "active")
        self.assertIsNone(brew["parentBrewId"])
        self.assertIn(f"{brew['brewId']}.json", self._kbhbrew_filer())

    def test_weak_recipe_link_is_not_authoritative(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = kbhbrew_storage.opprett_og_lagre_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, None, {}, recipe_id="oppskrift_som_senere_slettes.json",
        )
        # The recipe file this brew "points to" is never actually created
        # here -- the brew must remain fully readable regardless.
        reloaded = kbhbrew_storage.hent_brew(brew["brewId"])
        self.assertEqual(reloaded["recipeId"], "oppskrift_som_senere_slettes.json")
        self.assertEqual(reloaded["snapshot"]["recipe"]["navn"], "Identitetstest")


class TestNewBrewStorageIndependentFromLegacyLogs(_IsolertRecipeMappeTestCase):
    def test_kbhbrew_storage_never_touches_logs_namespace(self):
        recipe_storage.lagre_oppskrift(_recipe("Delt Navn"))
        recipe_storage.lagre_logg_entry("Delt Navn", {"date": "2026-02-20", "note": "Legacy loggoppføring"})

        malt_db, humle_db, gjaer_db = _dbs()
        kbhbrew_storage.opprett_og_lagre_ny_brew(
            _recipe("Delt Navn"), malt_db, humle_db, gjaer_db, None, {}, recipe_id="delt_navn.json",
        )

        # Legacy logg uendret -- fortsatt nøyaktig én oppføring.
        legacy_logg = recipe_storage.hent_logg("Delt Navn")
        self.assertEqual(legacy_logg, [{"date": "2026-02-20", "note": "Legacy loggoppføring"}])

        logs_mappe = os.path.join(self._mappe(), "_logs")
        self.assertIn("delt_navn_logg.json", os.listdir(logs_mappe))
        # Og de to navnerommene er fysisk atskilt.
        self.assertTrue(os.path.isdir(self._kbhbrew_mappe()))
        self.assertNotIn("delt_navn_logg.json", self._kbhbrew_filer())

    def test_new_kbhbrew_storage_does_not_appear_as_a_recipe_or_a_legacy_log(self):
        malt_db, humle_db, gjaer_db = _dbs()
        kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe("Ensom"), malt_db, humle_db, gjaer_db, None, {})

        self.assertEqual(recipe_storage.hent_alle_oppskrifter(), {})
        self.assertEqual(recipe_storage.hent_logg("Ensom"), [])


class TestDuplicateOriginNeverOverwritesOrDuplicates(_IsolertRecipeMappeTestCase):
    def _foreign_konvolutt_tekst(self, origin_brew_id="brew-origin-fixed"):
        # Models a .kbhbrew file that arrived from elsewhere (a different
        # machine/export) -- built via the pure engine directly, WITHOUT
        # going through opprett_og_lagre_ny_brew(), so it is never itself
        # persisted as a pre-existing local brew here.
        malt_db, humle_db, gjaer_db = _dbs()
        brew = bygg_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, None, {},
            created_at="2026-03-01T00:00:00+00:00", brew_id=origin_brew_id,
        )
        envelope = bygg_kbhbrew_konvolutt(brew, "2026-03-01T00:00:00+00:00")
        return json.dumps(envelope)

    def test_first_import_succeeds_second_is_rejected_as_duplicate(self):
        tekst = self._foreign_konvolutt_tekst()

        forste = kbhbrew_storage.importer_kbhbrew(tekst)
        self.assertTrue(forste["ok"])
        self.assertEqual(len(self._kbhbrew_filer()), 1)

        andre = kbhbrew_storage.importer_kbhbrew(tekst)
        self.assertFalse(andre["ok"])
        self.assertTrue(andre["duplicate"])
        self.assertEqual(andre["originBrewId"], "brew-origin-fixed")
        # No new file was written for the rejected duplicate.
        self.assertEqual(len(self._kbhbrew_filer()), 1)

    def test_import_mints_a_fresh_local_brew_id_never_equal_to_origin_source_file(self):
        tekst = self._foreign_konvolutt_tekst(origin_brew_id="brew-original-local-id")
        resultat = kbhbrew_storage.importer_kbhbrew(tekst)
        self.assertTrue(resultat["ok"])
        self.assertNotEqual(resultat["brewId"], "brew-original-local-id")
        self.assertEqual(resultat["brew"]["originBrewId"], "brew-original-local-id")
        self.assertIsNone(resultat["brew"]["recipeId"])  # dropped on import, local-machine-scoped


class TestUpdateLayerNeverTouchesFrozenSnapshot(_IsolertRecipeMappeTestCase):
    def test_oppdater_brew_lag_updates_actuals_but_not_snapshot(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        original_snapshot = brew["snapshot"]

        oppdatert = kbhbrew_storage.oppdater_brew_lag(
            brew["brewId"], actuals={"og": 1.053, "fg": 1.011}, status="done",
        )
        self.assertEqual(oppdatert["actuals"], {"og": 1.053, "fg": 1.011})
        self.assertEqual(oppdatert["status"], "done")
        self.assertEqual(oppdatert["snapshot"], original_snapshot)

        reloaded = kbhbrew_storage.hent_brew(brew["brewId"])
        self.assertEqual(reloaded["snapshot"], original_snapshot)
        self.assertEqual(reloaded["actuals"]["og"], 1.053)

    def test_oppdater_brew_lag_unknown_brew_id_is_a_noop(self):
        self.assertIsNone(kbhbrew_storage.oppdater_brew_lag("does-not-exist", actuals={"og": 1.05}))


class TestUpdateLayerPreservesUnknownAndUntouchedKnownFields(_IsolertRecipeMappeTestCase):
    """Chief review (issue #24 round 2): oppdater_brew_lag() used to
    REPLACE a whole layer wholesale, so importing a brew that carries an
    unknown (future-V1 or foreign) field in one layer and then updating
    just one KNOWN field in that same layer silently destroyed the
    unknown field -- and any other known field the caller didn't
    re-supply. Reproduces exactly that "import -> update one known
    field -> export" sequence and proves both survive, for all three
    mutable layers (actuals/sensing/learning)."""

    def _importer_brew_med_ukjent_felt(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = bygg_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, None, {},
            created_at="2026-03-01T00:00:00+00:00", brew_id="brew-merge-origin",
        )
        brew["actuals"] = {"og": 1.050, "fg": 1.012, "notes": "Opprinnelig notat"}
        brew["sensing"] = {"judgment": "yes", "notes": "Opprinnelig smaksnotat"}
        brew["learning"] = {"whatWorked": "Meskeprofil", "nextTime": "Samme igjen"}
        envelope = bygg_kbhbrew_konvolutt(brew, "2026-03-01T00:00:00+00:00")
        # Simulate a foreign/future-version file: the writer above only
        # emits KNOWN fields, so an unknown field per layer is injected
        # directly into the wire dict here -- exactly what
        # parse_kbhbrew_json()'s passthrough capture must preserve (same
        # "hand-edited file" pattern as
        # TestForbiddenActualAbvNeverEmitted in
        # tests/test_kbhbrew_engine_readerwriter.py).
        envelope["brew"]["actuals"]["mashPh"] = 5.4
        envelope["brew"]["sensing"]["aromaNotes"] = "Fruktig"
        envelope["brew"]["learning"]["yeastPitchRateNotes"] = "Dobbel pakke"
        resultat = kbhbrew_storage.importer_kbhbrew(json.dumps(envelope))
        self.assertTrue(resultat["ok"])
        return resultat["brewId"]

    def test_updating_one_known_actuals_field_preserves_unknown_field_and_other_known_fields(self):
        brew_id = self._importer_brew_med_ukjent_felt()

        oppdatert = kbhbrew_storage.oppdater_brew_lag(brew_id, actuals={"fg": 1.010})

        self.assertEqual(oppdatert["actuals"]["fg"], 1.010)
        self.assertEqual(oppdatert["actuals"]["og"], 1.050)  # untouched known field survives
        self.assertEqual(oppdatert["actuals"]["notes"], "Opprinnelig notat")
        exported = kbhbrew_storage.eksporter_kbhbrew(brew_id)
        self.assertEqual(exported["brew"]["actuals"]["mashPh"], 5.4)  # unknown field survives export

    def test_updating_one_known_sensing_field_preserves_unknown_field_and_other_known_fields(self):
        brew_id = self._importer_brew_med_ukjent_felt()

        oppdatert = kbhbrew_storage.oppdater_brew_lag(brew_id, sensing={"judgment": "maybe"})

        self.assertEqual(oppdatert["sensing"]["judgment"], "maybe")
        self.assertEqual(oppdatert["sensing"]["notes"], "Opprinnelig smaksnotat")
        exported = kbhbrew_storage.eksporter_kbhbrew(brew_id)
        self.assertEqual(exported["brew"]["sensing"]["aromaNotes"], "Fruktig")

    def test_updating_one_known_learning_field_preserves_unknown_field_and_other_known_fields(self):
        brew_id = self._importer_brew_med_ukjent_felt()

        oppdatert = kbhbrew_storage.oppdater_brew_lag(brew_id, learning={"nextTime": "Prøv lavere kokehastighet"})

        self.assertEqual(oppdatert["learning"]["nextTime"], "Prøv lavere kokehastighet")
        self.assertEqual(oppdatert["learning"]["whatWorked"], "Meskeprofil")
        exported = kbhbrew_storage.eksporter_kbhbrew(brew_id)
        self.assertEqual(exported["brew"]["learning"]["yeastPitchRateNotes"], "Dobbel pakke")

    def test_two_sequential_updates_to_different_known_fields_both_survive(self):
        # A single wholesale-replace bug would also show up as the FIRST
        # update's known field getting lost on the SECOND update -- not
        # only as unknown-field loss. Covers that failure mode too.
        brew_id = self._importer_brew_med_ukjent_felt()

        kbhbrew_storage.oppdater_brew_lag(brew_id, actuals={"fg": 1.010})
        oppdatert = kbhbrew_storage.oppdater_brew_lag(brew_id, actuals={"volumeL": 21.0})

        self.assertEqual(oppdatert["actuals"]["fg"], 1.010)
        self.assertEqual(oppdatert["actuals"]["volumeL"], 21.0)
        self.assertEqual(oppdatert["actuals"]["og"], 1.050)
        exported = kbhbrew_storage.eksporter_kbhbrew(brew_id)
        self.assertEqual(exported["brew"]["actuals"]["mashPh"], 5.4)


class TestDemoModeGuardsWrites(_IsolertRecipeMappeTestCase):
    def test_opprett_og_lagre_ny_brew_is_a_noop_in_demo_mode(self):
        malt_db, humle_db, gjaer_db = _dbs()
        with mock.patch.object(kbhbrew_storage, "DEMO_MODE", True):
            resultat = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        self.assertIsNone(resultat)
        self.assertEqual(self._kbhbrew_filer(), set())

    def test_importer_kbhbrew_is_a_noop_write_in_demo_mode_but_still_validates(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        tekst = json.dumps(bygg_kbhbrew_konvolutt(brew, "2026-03-01T00:00:00+00:00"))
        antall_filer_foer = len(self._kbhbrew_filer())

        with mock.patch.object(kbhbrew_storage, "DEMO_MODE", True):
            resultat = kbhbrew_storage.importer_kbhbrew(tekst)
        self.assertFalse(resultat["ok"])
        self.assertTrue(resultat["demo_mode"])
        self.assertEqual(len(self._kbhbrew_filer()), antall_filer_foer)  # nothing new written

    def test_oppdater_brew_lag_is_a_noop_in_demo_mode(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        with mock.patch.object(kbhbrew_storage, "DEMO_MODE", True):
            resultat = kbhbrew_storage.oppdater_brew_lag(brew["brewId"], actuals={"og": 1.05})
        self.assertIsNone(resultat)
        reloaded = kbhbrew_storage.hent_brew(brew["brewId"])
        self.assertEqual(reloaded["actuals"], {})


class TestHentAlleBrewsAndManifestProvenance(_IsolertRecipeMappeTestCase):
    def test_hent_alle_brews_returns_map_keyed_by_local_brew_id(self):
        malt_db, humle_db, gjaer_db = _dbs()
        b1 = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe("A"), malt_db, humle_db, gjaer_db, None, {})
        b2 = kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe("B"), malt_db, humle_db, gjaer_db, None, {})
        alle = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(set(alle.keys()), {b1["brewId"], b2["brewId"]})

    def test_corrupt_kbhbrew_file_is_skipped_not_fatal(self):
        malt_db, humle_db, gjaer_db = _dbs()
        kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        os.makedirs(self._kbhbrew_mappe(), exist_ok=True)
        with open(os.path.join(self._kbhbrew_mappe(), "korrupt.json"), "w", encoding="utf-8") as f:
            f.write("{ikke gyldig json")
        # Should not raise -- the corrupt file is logged and skipped.
        alle = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(alle), 1)

    def test_les_manifest_datasets_reads_real_core_manifest_when_present(self):
        # core/manifest.json is repo-root-relative, independent of the
        # isolated recipes tmpdir -- proves App (unlike Web) can read it
        # directly without a build-pipeline change (Section 5.12).
        datasets = kbhbrew_storage._les_manifest_datasets()
        if datasets is not None:
            for navn in ("malt", "humle", "gjaer"):
                if navn in datasets:
                    self.assertIn("schema_version", datasets[navn])


if __name__ == "__main__":
    unittest.main()
