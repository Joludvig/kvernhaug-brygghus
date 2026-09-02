"""
Tester for Core Stabilization Oppdrag 3 -- core/manifest.json og
docs/development/CORE_VERSIONING.md.

Minimale, KISS-tester for manifestet/versjonskontrakten selv -- ikke en
generell schema-validator. Beviser: manifestet parser, påkrevd
toppnivåstruktur finnes, schema_version og data_version er atskilte
felter, canonical/artifact-stier faktisk finnes på disk, kjente stabile
master-IDer er urørt, genererte Web-artifacts er aldri klassifisert som
canonical, verified_at er aldri fabrikkert fra legacy verified-boolean,
og manifestet har ingen avhengighet til privat brukerdata.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import hashlib
import io
import json
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MANIFEST_PATH = os.path.join(_ROOT, "core", "manifest.json")
_VERSIONING_DOC = os.path.join(_ROOT, "docs", "development", "CORE_VERSIONING.md")

# Kjente, stabile master-IDer (samme som brukt som legacy fixture-utvalg
# i Oppdrag 2B) -- brukes kun som lette sanity-sjekker på at dette
# oppdraget ikke har rørt masterdata-IDene, ikke som en uttømmende sjekk.
_KJENTE_STABILE_IDER = {
    "malt": "bohemian_pilsner_floor",
    "humle": "amarillo",
    "gjaer": "saflager_w3470",
}

_PRIVATE_PATH_FRAGMENTER = [
    "recipes/", "recipes_backup_", "data/pantry.json",
    "data/equipment.json", "data/humle_lager.json",
]


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _last_manifest():
    with io.open(_MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _sha256_av_fil(sti):
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# Kun timestamp-formatet (ISO 8601, dato + klokkeslett + tidssone),
# ikke en fullverdig RFC-parser -- dette er en KISS-sjekk på at feltet
# faktisk er et tidspunkt og ikke bare en dato (YYYY-MM-DD).
_ISO8601_TIDSPUNKT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


class TestManifestParserOgToppniva(unittest.TestCase):
    """Krav: manifest JSON parser; required top-level structure/felter finnes."""

    def test_manifest_parser_som_gyldig_json(self):
        manifest = _last_manifest()
        self.assertIsInstance(manifest, dict)

    def test_toppniva_felter_finnes(self):
        manifest = _last_manifest()
        for felt in ("manifest_schema_version", "generated_at", "datasets"):
            self.assertIn(felt, manifest)
        self.assertIsInstance(manifest["manifest_schema_version"], int)
        self.assertIsInstance(manifest["datasets"], dict)

    def test_alle_tre_forventede_datasett_finnes(self):
        manifest = _last_manifest()
        self.assertEqual(set(manifest["datasets"].keys()), {"malt", "humle", "gjaer"})

    def test_generated_at_er_gyldig_iso8601_tidspunkt_ikke_bare_dato(self):
        # Toppnivå generated_at beskriver når MANIFESTET ble generert og
        # skal være et faktisk tidspunkt (dato + klokkeslett + UTC/
        # tidssone), ikke en bar dato -- se Oppdrag 3 QA-korreksjon.
        manifest = _last_manifest()
        verdi = manifest["generated_at"]
        self.assertIsInstance(verdi, str)
        self.assertRegex(verdi, _ISO8601_TIDSPUNKT)


class TestSchemaVersionOgDataVersionErAtskilte(unittest.TestCase):
    """Krav: schema_version og data_version er separate felter/konsepter."""

    def test_begge_felt_finnes_separat_per_datasett_og_er_heltall(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            with self.subTest(dataset=key):
                self.assertIn("schema_version", ds)
                self.assertIn("data_version", ds)
                self.assertIsInstance(ds["schema_version"], int)
                self.assertIsInstance(ds["data_version"], int)
                # To distinkte nøkler -- ikke samme felt under to navn.
                self.assertIsNot(ds["schema_version"], None)
                self.assertIsNot(ds["data_version"], None)

    def test_data_version_er_dokumentert_som_stabilization_baseline(self):
        manifest = _last_manifest()
        for ds in manifest["datasets"].values():
            self.assertEqual(ds["data_version"], 1)
            self.assertIn("stabilization baseline", ds.get("data_version_note", "").lower())

    def test_versioning_doc_definerer_begge_konseptene_atskilt(self):
        tekst = _les(_VERSIONING_DOC)
        self.assertIn("## 1. `schema_version`", tekst)
        self.assertIn("## 2. `data_version`", tekst)
        self.assertIn("independent counters", tekst)


class TestCanonicalOgArtifactStierFinnesPaaDisk(unittest.TestCase):
    """Krav: canonical dataset paths peker på eksisterende filer, og
    manifestets checksums er LIVE integritetsmetadata for den aktive
    Core-tilstanden -- de skal faktisk matche source_path/artifact.path
    slik de er på disk akkurat nå (i motsetning til
    tests/fixtures/legacy/, som fryser historisk evidens og bevisst
    IKKE følger noen levende kilde -- se det README-et)."""

    def test_source_path_finnes_for_alle_datasett(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            with self.subTest(dataset=key):
                full = os.path.join(_ROOT, ds["source_path"].replace("/", os.sep))
                self.assertTrue(os.path.exists(full), f"{ds['source_path']} finnes ikke")

    def test_artifact_paths_finnes_for_alle_datasett(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            for artifact in ds["artifacts"]:
                with self.subTest(dataset=key, artifact=artifact["path"]):
                    full = os.path.join(_ROOT, artifact["path"].replace("/", os.sep))
                    self.assertTrue(os.path.exists(full), f"{artifact['path']} finnes ikke")

    def test_checksum_er_velformet_sha256_hex(self):
        # Strukturell sjekk (velformet 64-tegns hex) for alle checksums.
        manifest = _last_manifest()
        for ds in manifest["datasets"].values():
            self.assertEqual(ds["checksum"]["algorithm"], "sha256")
            verdi = ds["checksum"]["value"]
            self.assertEqual(len(verdi), 64)
            int(verdi, 16)  # kaster hvis ikke gyldig hex
            for artifact in ds["artifacts"]:
                verdi = artifact["checksum"]["value"]
                self.assertEqual(len(verdi), 64)
                int(verdi, 16)

    def test_canonical_checksum_matcher_faktisk_source_fil_live(self):
        # NB: dette er MANIFESTETS egen live-integritetssjekk, ikke en
        # legacy-fixture-test. tests/fixtures/legacy/ fryser historisk
        # evidens og verifiseres bevisst MOT SEG SELV (se den README-en)
        # -- det aktive core/manifest.json beskriver derimot dagens
        # Core-tilstand, så checksummen SKAL følge kildefilen. Endres
        # data/master_*.json uten at manifestet oppdateres, skal denne
        # testen bli rød (ønsket drift-deteksjon). Se
        # docs/development/CORE_VERSIONING.md for regelen om at et
        # checksum-avvik ikke i seg selv er bevis på en faglig endring.
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            with self.subTest(dataset=key):
                full = os.path.join(_ROOT, ds["source_path"].replace("/", os.sep))
                faktisk = _sha256_av_fil(full)
                self.assertEqual(
                    faktisk, ds["checksum"]["value"],
                    f"Checksum i manifestet for '{key}' matcher ikke "
                    f"faktisk innhold i {ds['source_path']} -- manifest "
                    f"og fil er ute av sync, krever eksplisitt review."
                )

    def test_generated_artifact_checksum_matcher_faktisk_artifact_fil_live(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            for artifact in ds["artifacts"]:
                with self.subTest(dataset=key, artifact=artifact["path"]):
                    full = os.path.join(_ROOT, artifact["path"].replace("/", os.sep))
                    faktisk = _sha256_av_fil(full)
                    self.assertEqual(
                        faktisk, artifact["checksum"]["value"],
                        f"Checksum i manifestet for artifact "
                        f"'{artifact['path']}' (dataset '{key}') matcher "
                        f"ikke faktisk filinnhold -- manifest og artifact "
                        f"er ute av sync, krever eksplisitt review."
                    )


class TestStabileMasterIderPaavirkesIkke(unittest.TestCase):
    """Krav: stabile master-ID-er påvirkes ikke av dette oppdraget."""

    def test_kjente_stabile_ider_fortsatt_tilstede_i_master(self):
        manifest = _last_manifest()
        for key, forventet_id in _KJENTE_STABILE_IDER.items():
            sti = os.path.join(_ROOT, manifest["datasets"][key]["source_path"].replace("/", os.sep))
            with io.open(sti, encoding="utf-8") as f:
                master = json.load(f)
            self.assertIn(forventet_id, master, f"{forventet_id} mangler i {key}-master -- IDer skal ikke endres")

    def test_manifest_lister_ingen_enkelt_ingrediens_ider(self):
        # Manifestet opererer på DATASETT-nivå (malt/humle/gjaer), aldri
        # på enkelt-ingrediens-nivå -- det skal ikke inneholde/duplisere
        # noen av de faktiske stabile ingrediens-IDene.
        manifest = _last_manifest()
        tekst = json.dumps(manifest)
        for forventet_id in _KJENTE_STABILE_IDER.values():
            self.assertNotIn(forventet_id, tekst)


class TestGenererteArtifactsIkkeKlassifisertSomCanonical(unittest.TestCase):
    """Krav: generated Web artifacts er ikke klassifisert som canonical."""

    def test_datasett_er_canonical_artifacts_er_generated(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            with self.subTest(dataset=key):
                self.assertEqual(ds["type"], "canonical_dataset")
                for artifact in ds["artifacts"]:
                    self.assertEqual(artifact["type"], "generated_artifact")
                    self.assertNotEqual(artifact["type"], "canonical_dataset")

    def test_artifact_stier_peker_pa_web_data_ikke_pa_data_master(self):
        manifest = _last_manifest()
        for ds in manifest["datasets"].values():
            for artifact in ds["artifacts"]:
                self.assertTrue(artifact["path"].startswith("web/data/"))
            self.assertTrue(ds["source_path"].startswith("data/master_"))


class TestVerifiedAtIkkeFabrikkertFraLegacyBoolean(unittest.TestCase):
    """Krav: verified_at er ikke fabrikkert fra legacy verified boolean."""

    def test_verified_at_er_null_for_alle_datasett(self):
        manifest = _last_manifest()
        for key, ds in manifest["datasets"].items():
            with self.subTest(dataset=key):
                self.assertIsNone(ds["verified_at"])
                self.assertIn("legacy", ds.get("verified_at_note", "").lower())

    def test_versioning_doc_advarer_eksplisitt_mot_a_utlede_verified_at(self):
        tekst = _les(_VERSIONING_DOC)
        self.assertIn("must never be fabricated or backfilled", tekst)


class TestManifestIngenDependencyPaaPrivateData(unittest.TestCase):
    """Krav: manifest har ingen dependency på private brukerdata."""

    def test_ingen_private_stier_i_manifest(self):
        tekst = _les(_MANIFEST_PATH)
        for fragment in _PRIVATE_PATH_FRAGMENTER:
            self.assertNotIn(fragment, tekst)

    def test_ingen_private_stier_i_versioning_doc(self):
        tekst = _les(_VERSIONING_DOC)
        for fragment in _PRIVATE_PATH_FRAGMENTER:
            self.assertNotIn(fragment, tekst)


class TestProvenanceIkkeOverdesignet(unittest.TestCase):
    """Krav: provenance kan refereres, men detaljert schema kommer i
    Oppdrag 4 -- ikke overdesignet her."""

    def test_provenance_er_reservert_placeholder(self):
        manifest = _last_manifest()
        for ds in manifest["datasets"].values():
            self.assertIsNone(ds["provenance"])


if __name__ == "__main__":
    unittest.main()
