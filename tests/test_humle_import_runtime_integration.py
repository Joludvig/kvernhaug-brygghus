"""
Integrasjonstest: humle fra skanning -> matching -> pending review ->
masterdata -> "runtime" (simulert samme lasting som app.py gjør).

Bakgrunn: ui/import_panel.py og ui/review_panel.py pekte begge på en
IKKE-eksisterende fil, data/master_humle_v0_1.json, mens appen selv
(app.py::last_json_data("master_humle_v2.json")) alltid har lastet
data/master_humle_v2.json direkte. Konsekvens: humle-matching i
Import-panelet feilet stille (FileNotFoundError fanget av en bred
except), og en godkjent humle-review i Pending Review-panelet skrev til
en fil appen aldri leste -- endringen ble ALDRI synlig i appen.

Denne testen kjører HELE kjeden mot de virkelige, produksjonsfunksjonene
(modules/store_matcher.match_store_data_to_master og
ui/review_panel sine interne skrivefunksjoner) i en isolert
tempfile.TemporaryDirectory(), og bekrefter at begge veiene (automatisk
match OG manuell review-godkjenning) ender opp i den SAMME filen appen
faktisk laster -- aldri i den slettede/manglende v0_1-filen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

from modules.store_matcher import match_store_data_to_master


def _last_json(sti):
    with open(sti, encoding="utf-8") as f:
        return json.load(f)


def _last_master_humle_slik_som_app_py(data_mappe):
    """Speiler EKSAKT app.py sin egen last_json_data("master_humle_v2.json")
    -- samme filnavn, samme mappe-konvensjon (data/), samme
    "hopp over nøkler som starter med _"-oppførsel."""
    filsti = os.path.join(data_mappe, "master_humle_v2.json")
    with open(filsti, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


class TestHumleFraReviewTilAktivDatabase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)
        os.makedirs("data", exist_ok=True)
        os.makedirs("raw_data", exist_ok=True)

        self._master_humle_sti = "data/master_humle_v2.json"
        with open(self._master_humle_sti, "w", encoding="utf-8") as f:
            json.dump({
                "cascade_us": {
                    "display_name": "Cascade",
                    "kategori": "Dual",
                    "alfa_typisk": 6.0,
                    "aliases": ["Cascade", "Cascade US"],
                    "smakstags": ["sitrus", "grapefrukt"],
                    "butikk_match": {},
                },
            }, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        os.chdir(self._gammel_cwd)
        self._tmpdir.cleanup()

    def test_matchet_humle_skrives_direkte_til_filen_appen_laster(self):
        # === SKANNING (simulert: en allerede skrapet raw-fil) ===
        with open("raw_data/humle_raw.json", "w", encoding="utf-8") as f:
            json.dump([
                {"navn": "Cascade 2026 Humle Pellets - 100g", "butikk": "Vestbrygg",
                 "pris": 89.0, "url": "https://vestbrygg.no/cascade-pellets", "pakke_gram": 100},
            ], f, ensure_ascii=False, indent=2)

        # === MATCHING (samme funksjon/sti-par som
        # ui/import_panel.py sin "🧠 Kjør AI-normalisering"-knapp bruker
        # etter fiksen -- data/master_humle_v2.json, ikke v0_1) ===
        matched_n, unmatched_n = match_store_data_to_master(
            "raw_data/humle_raw.json", self._master_humle_sti,
            "raw_data/matched_hops.json", "raw_data/unmatched_hops.json",
        )
        self.assertEqual((matched_n, unmatched_n), (1, 0))

        # === RUNTIME (samme lasting som app.py gjør ved oppstart) ===
        runtime_db = _last_master_humle_slik_som_app_py("data")
        self.assertIn("cascade_us", runtime_db)
        self.assertEqual(runtime_db["cascade_us"]["butikk_match"]["vestbrygg"]["pris"], 89.0)
        self.assertEqual(
            runtime_db["cascade_us"]["butikk_match"]["vestbrygg"]["url"],
            "https://vestbrygg.no/cascade-pellets",
        )

    def test_umatchet_humle_review_godkjenning_blir_synlig_i_runtime(self):
        # Simulerer PENDING REVIEW-tilstanden direkte (som om skanning +
        # matching allerede har kjørt og lagt en helt ny humlesort i
        # unmatched-køen -- se ui/review_panel.py::_render_kategori).
        with open("raw_data/unmatched_hops.json", "w", encoding="utf-8") as f:
            json.dump([
                {"navn": "Splendour 2026", "butikk": "olbrygging",
                 "pris": 75.0, "url": "https://olbrygging.no/splendour", "status": "pending_review"},
            ], f, ensure_ascii=False, indent=2)

        import ui.review_panel as review_panel
        # Kjørende Streamlit-widgetflyt kan ikke drives uten en AppTest-
        # sesjon, men selve SKRIVE-funksjonen review-formen til slutt
        # kaller (_opprett_og_fjern, se _render_ny_humle) er ren Python --
        # dette er nøyaktig hva "Opprett i master"-knappen utfører.
        self.assertEqual(review_panel.MASTER_PATHS["humle"], self._master_humle_sti)

        ny_entry = {
            "display_name": "Splendour",
            "kategori": "Aroma",
            "alfa_typisk": 8.0,
            "aliases": ["Splendour 2026", "Splendour"],
            "smakstags": ["blomster", "urter"],
            "origin": "Australia",
            "butikk_match": {"olbrygging": {"pris": 75.0, "url": "https://olbrygging.no/splendour"}},
            "verified": True,
        }
        review_panel._opprett_og_fjern("humle", "splendour", ny_entry, 0)

        # === RUNTIME (samme lasting som app.py gjør ved oppstart) ===
        runtime_db = _last_master_humle_slik_som_app_py("data")
        self.assertIn("splendour", runtime_db)
        self.assertEqual(runtime_db["splendour"]["display_name"], "Splendour")

        # Fjernet fra pending-køen etter godkjenning.
        gjenvaerende_unmatched = _last_json("raw_data/unmatched_hops.json")
        self.assertEqual(gjenvaerende_unmatched, [])

        # Skrivingen skal ha gått via den atomiske masterdata-hjelperen:
        # en backup av den FORRIGE versjonen (med bare cascade_us) skal
        # finnes i data/.
        backupfiler = [f for f in os.listdir("data") if f.startswith("master_humle_v2.json.backup_")]
        self.assertEqual(len(backupfiler), 1)
        backup_innhold = _last_json(os.path.join("data", backupfiler[0]))
        self.assertNotIn("splendour", backup_innhold)
        self.assertIn("cascade_us", backup_innhold)

    def test_review_matching_mot_eksisterende_oppdaterer_samme_fil_appen_laster(self):
        # "🔗 Match eksisterende"-fanen -- se
        # ui/review_panel.py::_render_match_tab / _legg_til_alias_og_fjern.
        with open("raw_data/unmatched_hops.json", "w", encoding="utf-8") as f:
            json.dump([
                {"navn": "Cascade Import Spesialpakning", "butikk": "vestbrygg",
                 "pris": 99.0, "url": "https://vestbrygg.no/cascade-spesial", "status": "pending_review"},
            ], f, ensure_ascii=False, indent=2)

        import ui.review_panel as review_panel
        item = _last_json("raw_data/unmatched_hops.json")[0]
        review_panel._legg_til_alias_og_fjern("humle", "cascade_us", item, 0)

        runtime_db = _last_master_humle_slik_som_app_py("data")
        self.assertIn("Cascade Import Spesialpakning", runtime_db["cascade_us"]["aliases"])
        self.assertEqual(runtime_db["cascade_us"]["butikk_match"]["vestbrygg"]["pris"], 99.0)
        self.assertEqual(_last_json("raw_data/unmatched_hops.json"), [])


if __name__ == "__main__":
    unittest.main()
