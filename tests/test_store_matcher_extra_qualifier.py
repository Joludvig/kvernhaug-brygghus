"""
Regresjonstester for Steg F8F: kvalifikatorsperren i
modules/store_matcher.py::match_product_to_master().

Bakgrunn (Steg F8D rotårsaksrapport): "1 Kg Spraymalt EXTRA Light
(4-5 ebc)" ble feilmatchet til master-ID-en spray_light_68_ebc
("Spraymalt Light (6-8 ebc)") med likhetsscore 0,821 — godt over
0,7-terskelen. Extra Light og Light er to ulike produkter (4-5 EBC mot
6-8 EBC). match_product_to_master() krever nå at det skrapede navnet og
det sammenlignede aliaset har nøyaktig samme sett med diskriminerende
kvalifikatorer (i denne runden: kun EXTRA/EKSTRA) før likhetsscore i
det hele tatt regnes ut.

Disse testene bruker utelukkende isolerte, syntetiske master-fixtures —
ingen ekte data/master_*.json eller raw_data/*.json leses eller skrives.
"""
import unittest

from modules.store_matcher import (
    match_product_to_master,
    _produktkvalifikatorer,
    _strip_size,
)


# Syntetisk master med akkurat samme struktur som det virkelige
# spray_light_68_ebc-oppslaget (kun aliases er relevante for matcheren).
_MASTER_LIGHT_ONLY = {
    "spray_light_68_ebc": {
        "display_name": "Spraymalt Light (6-8 EBC)",
        "aliases": [
            "Spraymalt Light (6-8 ebc)",
            "1 Kg Spraymalt Light (6-8 ebc)",
            "5 Kg Spraymalt Light (6-8 ebc)",
        ],
    },
}

# Samme som over, men med en tenkt fremtidig egen Extra Light-master i
# tillegg — brukes for å bevise at Extra Light KAN matches når en reell
# kandidat faktisk finnes, og at Light ikke krysser over til den.
_MASTER_LIGHT_OG_EXTRA_LIGHT = {
    **_MASTER_LIGHT_ONLY,
    "spray_extra_light_45_ebc": {
        "display_name": "Spraymalt Extra Light (4-5 EBC)",
        "aliases": [
            "Spraymalt Extra Light (4-5 ebc)",
            "1 Kg Spraymalt Extra Light (4-5 ebc)",
        ],
    },
}

# Speiler den ekte crystal_extra_dark-masteren (Steg F8F-analysen fant
# denne som eneste eksisterende EXTRA-kvalifiserte master i produksjons-
# dataene) — brukes for å bevise at regelen ikke er ny risiko, men
# allerede implisitt forventet av ekte data.
_MASTER_CRYSTAL = {
    "crystal": {
        "display_name": "Crystal Malt",
        "aliases": ["Crystal Malt", "Crystal 80", "Light Crystal"],
    },
    "crystal_extra_dark": {
        "display_name": "Extra Dark Crystal",
        "aliases": [
            "Extra Dark Crystal",
            "Crystal Extra Dark",
            "Crystal 240",
            "Dark Crystal Malt",
            "Extra Dark Crystal Malt",
        ],
    },
}


class Test1ProduktkvalifikatorerTokenisering(unittest.TestCase):
    """_produktkvalifikatorer() skal være ordbasert, aldri substrengbasert."""

    def test_extra_gir_extra_kvalifikator(self):
        self.assertEqual(_produktkvalifikatorer("Spraymalt Extra Light"), frozenset({"extra"}))

    def test_ekstra_normaliseres_til_samme_kvalifikator_som_extra(self):
        self.assertEqual(_produktkvalifikatorer("Spraymalt Ekstra Light"), frozenset({"extra"}))
        self.assertEqual(
            _produktkvalifikatorer("Spraymalt Extra Light"),
            _produktkvalifikatorer("Spraymalt Ekstra Light"),
        )

    def test_extract_regnes_ikke_som_extra(self):
        self.assertEqual(_produktkvalifikatorer("Malt Extract Light"), frozenset())
        self.assertEqual(_produktkvalifikatorer("Light Extract"), frozenset())

    def test_ekstrakt_regnes_ikke_som_ekstra(self):
        self.assertEqual(_produktkvalifikatorer("Ekstrakt Spraymalt"), frozenset())

    def test_navn_uten_kvalifikator_gir_tomt_sett(self):
        self.assertEqual(_produktkvalifikatorer("Spraymalt Light (6-8 ebc)"), frozenset())

    def test_ebc_tekst_pavirker_ikke_kvalifikatorkontrollen(self):
        self.assertEqual(
            _produktkvalifikatorer("1 Kg Spraymalt EXTRA Light (4-5 ebc)"),
            _produktkvalifikatorer("Spraymalt EXTRA Light"),
        )


class Test2ExtraLightMatcherIkkeLight(unittest.TestCase):
    """Kjernescenarioet fra Steg F8D: Extra Light skal ikke matches til Light."""

    def test_extra_light_matcher_ikke_til_light_master(self):
        navn = _strip_size("1 Kg Spraymalt EXTRA Light (4-5 ebc)")
        master_id, alias = match_product_to_master(navn, _MASTER_LIGHT_ONLY)
        self.assertIsNone(master_id)
        self.assertIsNone(alias)

    def test_ekstra_light_matcher_ikke_til_light_master(self):
        navn = _strip_size("1 Kg Spraymalt Ekstra Light (4-5 ebc)")
        master_id, alias = match_product_to_master(navn, _MASTER_LIGHT_ONLY)
        self.assertIsNone(master_id)

    def test_vanlig_light_matcher_fortsatt_som_for(self):
        navn = _strip_size("Spraymalt Light (6-8 ebc)")
        master_id, alias = match_product_to_master(navn, _MASTER_LIGHT_ONLY)
        self.assertEqual(master_id, "spray_light_68_ebc")

    def test_1kg_prefiks_pavirker_ikke_regelen(self):
        navn = _strip_size("1 Kg Spraymalt Light")
        master_id, _ = match_product_to_master(navn, _MASTER_LIGHT_ONLY)
        self.assertEqual(master_id, "spray_light_68_ebc")


class Test3ExtraLightKanMatchesTilEgenMaster(unittest.TestCase):
    """Når en reell Extra Light-master faktisk finnes, skal den kunne matches."""

    def test_extra_light_matcher_til_egen_extra_light_master(self):
        navn = _strip_size("1 Kg Spraymalt Extra Light (4-5 ebc)")
        master_id, alias = match_product_to_master(navn, _MASTER_LIGHT_OG_EXTRA_LIGHT)
        self.assertEqual(master_id, "spray_extra_light_45_ebc")

    def test_ekstra_light_matcher_til_egen_extra_light_master_via_synonym(self):
        navn = _strip_size("Spraymalt Ekstra Light (4-5 ebc)")
        master_id, _ = match_product_to_master(navn, _MASTER_LIGHT_OG_EXTRA_LIGHT)
        self.assertEqual(master_id, "spray_extra_light_45_ebc")

    def test_light_matcher_ikke_til_extra_light_master(self):
        navn = _strip_size("Spraymalt Light (6-8 ebc)")
        master_id, _ = match_product_to_master(navn, _MASTER_LIGHT_OG_EXTRA_LIGHT)
        self.assertEqual(master_id, "spray_light_68_ebc")
        self.assertNotEqual(master_id, "spray_extra_light_45_ebc")


class Test4AliasNivaHandtering(unittest.TestCase):
    """Kvalifikatorsjekken er per alias, ikke bare per canonical/display_name."""

    def test_alias_med_extra_tillater_match_selv_om_display_name_mangler_det(self):
        master = {
            "spray_extra_light_45_ebc": {
                "display_name": "Spraymalt Extra Light",
                "aliases": ["Spraymalt Extra Light (4-5 ebc)"],
            },
        }
        navn = _strip_size("Spraymalt Extra Light (4-5 ebc)")
        master_id, _ = match_product_to_master(navn, master)
        self.assertEqual(master_id, "spray_extra_light_45_ebc")

    def test_kandidat_med_blandede_aliases_matcher_riktig_alias(self):
        # crystal_extra_dark har både EXTRA-kvalifiserte aliases ("Extra
        # Dark Crystal") og ikke-kvalifiserte aliases ("Crystal 240",
        # "Dark Crystal Malt") — begge typer skal fortsatt kunne treffes
        # av navn med tilsvarende kvalifikator-signatur.
        navn_med_extra = _strip_size("Extra Dark Crystal Malt 25 kg")
        master_id, _ = match_product_to_master(navn_med_extra, _MASTER_CRYSTAL)
        self.assertEqual(master_id, "crystal_extra_dark")

        navn_uten_extra = _strip_size("Dark Crystal Malt 25 kg")
        master_id, _ = match_product_to_master(navn_uten_extra, _MASTER_CRYSTAL)
        self.assertEqual(master_id, "crystal_extra_dark")  # via alias "Dark Crystal Malt"


class Test5EksisterendeCrystalDataUpavirket(unittest.TestCase):
    """Regresjon mot den eneste ekte EXTRA-kvalifiserte masteren i produksjonsdata."""

    def test_crystal_malt_matcher_fortsatt_plain_crystal(self):
        navn = _strip_size("Crystal Malt 65")
        master_id, _ = match_product_to_master(navn, _MASTER_CRYSTAL)
        self.assertEqual(master_id, "crystal")

    def test_crystal_matcher_ikke_extra_dark_crystal(self):
        navn = _strip_size("Crystal 80")
        master_id, _ = match_product_to_master(navn, _MASTER_CRYSTAL)
        self.assertEqual(master_id, "crystal")
        self.assertNotEqual(master_id, "crystal_extra_dark")


if __name__ == "__main__":
    unittest.main()
