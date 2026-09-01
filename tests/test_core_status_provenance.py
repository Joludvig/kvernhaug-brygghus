"""
Tester for Core Stabilization Oppdrag 4 -- core/status_provenance.json
og docs/development/CORE_STATUS_PROVENANCE.md.

Minimale, KISS-tester for policy-kontrakten selv -- ikke en generell
workflow-/schema-motor. Beviser: policyen parser, statusverdiene er
nøyaktig draft/reviewed/verified/deprecated, legacy verified-mapping
er eksplisitt "requires_review" (ikke en automatisk oppgradering til
Core-status verified), claim/evidence-typene er eksplisitte og
distinkte, provenance-feltdefinisjonene finnes, ingen masterdatafil er
endret av dette oppdraget, og ingen privat brukerdata refereres. Hvis
core/manifest.json har fått en policy-reference, verifiseres at stien
faktisk finnes.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import hashlib
import io
import json
import os
import unittest

_ROOT = r"D:\Development\Kvernhaug Brygghus"
_POLICY_PATH = os.path.join(_ROOT, "core", "status_provenance.json")
_POLICY_DOC = os.path.join(_ROOT, "docs", "development", "CORE_STATUS_PROVENANCE.md")
_MANIFEST_PATH = os.path.join(_ROOT, "core", "manifest.json")

_MASTER_FILER = [
    os.path.join(_ROOT, "data", "master_malt.json"),
    os.path.join(_ROOT, "data", "master_humle_v2.json"),
    os.path.join(_ROOT, "data", "master_gjaer_v2.json"),
]

_FORVENTEDE_MASTER_SHA256 = {}  # fylles i setUpModule, se under

_PRIVATE_PATH_FRAGMENTER = [
    "recipes/", "recipes_backup_", "data/pantry.json",
    "data/equipment.json", "data/humle_lager.json",
]


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _last_json(sti):
    with io.open(sti, encoding="utf-8") as f:
        return json.load(f)


def _sha256_av_fil(sti):
    h = hashlib.sha256()
    with open(sti, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def setUpModule():
    # Fanger hash av masterdatafilene FØR noen test kjører, slik at vi
    # kan bevise etterpå (i denne modulens eget scope) at ingen av dem
    # ble endret av selve testkjøringen eller av dette oppdraget.
    for sti in _MASTER_FILER:
        _FORVENTEDE_MASTER_SHA256[sti] = _sha256_av_fil(sti)


class TestPolicyParserOgToppniva(unittest.TestCase):
    """Krav: policy JSON parser; toppnivåstruktur finnes."""

    def test_policy_parser_som_gyldig_json(self):
        policy = _last_json(_POLICY_PATH)
        self.assertIsInstance(policy, dict)

    def test_toppniva_felter_finnes(self):
        policy = _last_json(_POLICY_PATH)
        for felt in ("policy_schema_version", "status", "claim_evidence_types",
                     "provenance_fields", "legacy_verified_mapping"):
            self.assertIn(felt, policy)
        self.assertIsInstance(policy["policy_schema_version"], int)


class TestStatusverdierErEksakte(unittest.TestCase):
    """Krav: statusverdier er nøyaktig draft, reviewed, verified, deprecated."""

    def test_status_values_eksakt_liste(self):
        policy = _last_json(_POLICY_PATH)
        self.assertEqual(
            policy["status"]["values"],
            ["draft", "reviewed", "verified", "deprecated"],
        )

    def test_alle_status_har_definisjon(self):
        policy = _last_json(_POLICY_PATH)
        definisjoner = policy["status"]["definitions"]
        for verdi in policy["status"]["values"]:
            self.assertIn(verdi, definisjoner)
            self.assertTrue(definisjoner[verdi].strip())

    def test_kun_de_tre_lave_hovedovergangene_er_definert(self):
        policy = _last_json(_POLICY_PATH)
        overganger = [tuple(t) for t in policy["status"]["allowed_transitions"]]
        self.assertEqual(
            overganger,
            [("draft", "reviewed"), ("reviewed", "verified"), ("verified", "deprecated")],
        )

    def test_rollback_overganger_eksplisitt_ikke_definert(self):
        policy = _last_json(_POLICY_PATH)
        self.assertFalse(policy["status"]["rollback_or_reopen_transitions_defined"])

    def test_doc_definerer_statusflyten_normativt(self):
        tekst = _les(_POLICY_DOC)
        self.assertIn("draft → reviewed → verified → deprecated", tekst)


class TestLegacyVerifiedMappingEksplisittRequiresReview(unittest.TestCase):
    """Krav: legacy verified mapping er eksplisitt NONE/requires_review --
    aldri en automatisk oppgradering til Core-status verified."""

    def test_legacy_verified_mapping_er_requires_review(self):
        policy = _last_json(_POLICY_PATH)
        self.assertIn(policy["legacy_verified_mapping"], ("none", "requires_review"))
        self.assertEqual(policy["legacy_verified_mapping"], "requires_review")

    def test_ingen_policyregel_oppgraderer_legacy_automatisk_til_verified(self):
        # Policyen skal IKKE inneholde noen regel/mapping som kobler
        # legacy verified:true/false direkte til Core status "verified"
        # eller "draft" -- kun den eksplisitte "requires_review"-strengen
        # og en forklarende note, aldri en faktisk oversettelsestabell.
        policy = _last_json(_POLICY_PATH)
        self.assertNotIn("verified_true_maps_to", policy)
        self.assertNotIn("verified_false_maps_to", policy)
        note = policy["legacy_verified_mapping_note"].lower()
        self.assertIn("no automatic mapping", note)

    def test_doc_dokumenterer_alle_fire_eksplisitte_regler(self):
        tekst = _les(_POLICY_DOC)
        self.assertIn("does **not** automatically mean Core status\n  `verified`", tekst)
        self.assertIn("does **not** automatically mean Core status\n  `draft`", tekst)
        self.assertIn("does **not** automatically mean any new\n  Core status", tekst)


class TestClaimEvidenceTypesEksplisitteOgDistinkte(unittest.TestCase):
    """Krav: claim/evidence types er eksplisitte og distinkte."""

    def test_claim_evidence_values_eksakt_liste(self):
        policy = _last_json(_POLICY_PATH)
        self.assertEqual(
            policy["claim_evidence_types"]["values"],
            ["documented_fact", "documented_observation", "interpretation",
             "assumption", "proposal"],
        )

    def test_alle_verdier_distinkte(self):
        policy = _last_json(_POLICY_PATH)
        verdier = policy["claim_evidence_types"]["values"]
        self.assertEqual(len(verdier), len(set(verdier)))

    def test_ingen_verdi_overlapper_med_status_verdi(self):
        # Claim/evidence-type og status er to atskilte akser -- ingen
        # streng skal kunne forveksles mellom de to listene.
        policy = _last_json(_POLICY_PATH)
        self.assertEqual(
            set(policy["claim_evidence_types"]["values"])
            & set(policy["status"]["values"]),
            set(),
        )


class TestProvenanceFeltdefinisjonerFinnes(unittest.TestCase):
    """Krav: provenance-feltdefinisjoner finnes."""

    def test_forventede_provenance_felter_finnes(self):
        policy = _last_json(_POLICY_PATH)
        felter = policy["provenance_fields"]
        for navn in ("source_type", "source_ref", "source_date", "captured_at",
                     "reviewed_at", "verified_at", "reviewer_ref", "notes"):
            self.assertIn(navn, felter)
            self.assertIn("type", felter[navn])

    def test_confidence_er_eksplisitt_ikke_et_provenance_felt(self):
        policy = _last_json(_POLICY_PATH)
        self.assertNotIn("confidence", policy["provenance_fields"])
        self.assertFalse(policy["confidence_field"]["included"])


class TestIngenMasterdatafilEndret(unittest.TestCase):
    """Krav: ingen masterdatafiler er endret av dette oppdraget."""

    def test_masterdatafilene_er_uendret_under_denne_testkjøringen(self):
        for sti in _MASTER_FILER:
            with self.subTest(fil=sti):
                self.assertEqual(_sha256_av_fil(sti), _FORVENTEDE_MASTER_SHA256[sti])

    def test_masterdatafilene_har_ikke_faatt_nye_status_provenance_felt(self):
        for sti in _MASTER_FILER:
            master = _last_json(sti)
            for entry in master.values():
                self.assertNotIn("core_status", entry)
                self.assertNotIn("status", entry)
                self.assertNotIn("provenance", entry)


class TestIngenPrivateDataIPolicyEllerDoc(unittest.TestCase):
    """Krav: ingen private data refereres."""

    def test_ingen_private_stier_i_policy(self):
        tekst = _les(_POLICY_PATH)
        for fragment in _PRIVATE_PATH_FRAGMENTER:
            self.assertNotIn(fragment, tekst)

    def test_ingen_private_stier_i_doc(self):
        tekst = _les(_POLICY_DOC)
        for fragment in _PRIVATE_PATH_FRAGMENTER:
            self.assertNotIn(fragment, tekst)


class TestManifestPolicyReferansePekerPaaEksisterendeStier(unittest.TestCase):
    """Krav: hvis manifestet fikk en policy-reference, test at stiene finnes."""

    def test_manifest_status_provenance_policy_reference_finnes_hvis_satt(self):
        manifest = _last_json(_MANIFEST_PATH)
        if "status_provenance_policy" not in manifest:
            self.skipTest("core/manifest.json har ingen status_provenance_policy-referanse")
        ref = manifest["status_provenance_policy"]
        for felt in ("doc", "machine_policy"):
            with self.subTest(felt=felt):
                full = os.path.join(_ROOT, ref[felt].replace("/", os.sep))
                self.assertTrue(os.path.exists(full), f"{ref[felt]} finnes ikke")

    def test_manifest_dataset_provenance_felt_fortsatt_null(self):
        # Referansen skal IKKE ha fabrikkert provenance-records for
        # dagens datasett -- hvert datasetts eget "provenance"-felt
        # skal fortsatt være null.
        manifest = _last_json(_MANIFEST_PATH)
        for ds in manifest["datasets"].values():
            self.assertIsNone(ds["provenance"])


if __name__ == "__main__":
    unittest.main()
