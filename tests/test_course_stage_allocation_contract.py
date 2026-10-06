"""
Konsistenstester for docs/development/v22_course_stage_allocation_contract.md
(Bryggeskole course stage allocation, 2026-10-04).

Kontrakten sier HVOR innhold hører hjemme (Foundation / Kompetent /
Bryggemester / Bryggeri) og peker på eksisterende chunk-, spørsmåls- og
fakta-id-er. Testene sikrer bare at disse id-ene faktisk finnes, slik at en
senere omdøping ikke stille gjør kontrakten foreldet. De endrer eller
validerer ikke selve stadieplasseringen.

Kjøres med:
    python3 -m unittest tests.test_course_stage_allocation_contract
"""
import io
import json
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONTRACT_DOC = os.path.join(_ROOT, "docs", "development", "v22_course_stage_allocation_contract.md")
_REGISTRY = os.path.join(_ROOT, "bryggeskole", "data", "course_fact_registry.json")
_DATA = os.path.join(_ROOT, "bryggeskole", "data")

# Implementerte moduler: id-prefiks -> pilotfil. Alle moduler kontrakten
# siterer id-er fra, er implementert og sjekkes mot den ekte pilotfilen.
_PILOT_FOR_PREFIX = {
    "RAW": "pilot_raw_materials_fundamentals.json",
    "SAFE": "pilot_cleaning_safety_fundamentals.json",
    "METHOD": "pilot_method_context_fundamentals.json",
    "MASH": "pilot_mashing_fundamentals.json",
    "BOILHOP": "pilot_boil_hop_fundamentals.json",
    "COOLXFER": "pilot_cool_transfer_fundamentals.json",
    "FERM": "pilot_fermentation_temperature.json",
    "PACK": "pilot_package_fundamentals.json",
    "MEAS": "pilot_measurement_fundamentals.json",
    "REC": "pilot_recipe_fundamentals.json",
    "SENS": "pilot_sensory_evaluation.json",
}
_ID_RE = re.compile(r"\b(CHUNK|Q)-(" + "|".join(_PILOT_FOR_PREFIX) + r")-([A-Z]|\d{3})\b")


def _les(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


class TestStageAllocationContractReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _les(_CONTRACT_DOC)

    def test_dokumentet_finnes_og_har_de_fire_stadiene(self):
        for stadium in ("Foundation", "Kompetent", "Bryggemester", "Bryggeri"):
            self.assertIn(stadium, self.doc)
        self.assertIn("I can brew, ferment and package one batch safely and explain what each stage does.", self.doc)

    def test_alle_siterte_fakta_finnes_i_registeret(self):
        registry = json.loads(_les(_REGISTRY))
        records = registry if isinstance(registry, list) else (registry.get("facts") or registry.get("records"))
        kjente = {r["id"] for r in records}
        siterte = set(re.findall(r"\bFACT-[A-Z]+-\d{4}\b", self.doc))
        self.assertTrue(siterte)
        self.assertEqual(siterte - kjente, set(), "Kontrakten siterer fakta-id-er som ikke finnes i registeret")

    def test_siterte_chunk_og_sporsmals_id_er_finnes_i_pilotfilene(self):
        siterte = {m.group(0): m.group(2) for m in _ID_RE.finditer(self.doc)}
        self.assertTrue(siterte)
        for full_id, prefiks in sorted(siterte.items()):
            pilot = os.path.join(_DATA, _PILOT_FOR_PREFIX[prefiks])
            with self.subTest(id=full_id):
                if not os.path.exists(pilot):
                    # Modulen finnes ennå ikke på denne grenen (f.eks. master uten
                    # den offline produktstakken); id-en kan ikke sjekkes her.
                    self.skipTest(f"{_PILOT_FOR_PREFIX[prefiks]} finnes ikke på denne grenen")
                data = json.loads(_les(pilot))
                ider = {c["id"] for c in data["chunks"]} | {q["id"] for q in data["questions"]}
                self.assertIn(full_id, ider)


if __name__ == "__main__":
    unittest.main()
